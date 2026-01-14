#include "Client.h"
#include "../Utils/Logger.h"
#include "../Logic/CommandManager.h"
#include "../Game/GameConfig.h"
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <string.h>
#include <errno.h>
#include <sstream>

NetworkClient::NetworkClient() : sock(-1), isRunning(true) {}

NetworkClient& NetworkClient::Instance() {
    static NetworkClient instance;
    return instance;
}

void NetworkClient::Start() {
    pthread_create(&netThreadId, NULL, thread_entry, this);
}

void* NetworkClient::thread_entry(void* instance) {
    ((NetworkClient*)instance)->run();
    return NULL;
}

bool NetworkClient::sendData(const std::string& data) {
    if (sock == -1) return false;
    ssize_t sent = send(sock, data.c_str(), data.length(), MSG_NOSIGNAL);
    if (sent < 0) {
        LOGE("Net: Send failed: %s", strerror(errno));
        return false;
    }
    return true;
}

void NetworkClient::enqueueMessage(std::string msg) {
    if (msg.empty()) return;
    if (msg.back() != '\n') msg += "\n";

    std::lock_guard<std::mutex> lock(queueMutex);
    if (sendQueue.size() > 100) sendQueue.pop(); 
    sendQueue.push(msg);
}

void NetworkClient::SendToast(const std::string& text) { enqueueMessage("TOAST: " + text); }
void NetworkClient::SendHint(const std::string& text) { enqueueMessage("HINT: " + text); }
void NetworkClient::SendRaw(const std::string& text) { enqueueMessage(text); }

// --- ОБРАБОТКА ВХОДЯЩИХ ПАКЕТОВ ---

void NetworkClient::handlePacket(const std::string& packet) {
    std::string cleanPacket = packet;
    if (!cleanPacket.empty() && cleanPacket.back() == '\r') {
        cleanPacket.pop_back();
    }
    if (cleanPacket.empty()) return;

    // Логируем входящее (для дебага)
    LOGD("RX: %s", cleanPacket.c_str());

    // Ищем префикс "API: "
    const std::string apiPrefix = "API: ";
    if (cleanPacket.rfind(apiPrefix, 0) == 0) {
        // Отрезаем "API: " и берем всё остальное как JSON
        std::string jsonPayload = cleanPacket.substr(apiPrefix.length());

        LOGD(">>> API PAYLOAD RECEIVED: %s", jsonPayload.c_str());
        
        // Добавляем этот JSON в очередь команд.
        // GameHooks в MainThread заберет его и отправит в SendDirectJson.
        CommandManager::Instance().AddCommand(jsonPayload);
        return;
    }
}

void NetworkClient::processIncomingData(char* buffer, int length) {
    incomingBuffer.append(buffer, length);

    size_t pos = 0;
    while ((pos = incomingBuffer.find('\n')) != std::string::npos) {
        std::string packet = incomingBuffer.substr(0, pos);
        handlePacket(packet);
        incomingBuffer.erase(0, pos + 1);
    }
}

void NetworkClient::run() {
    LOGD("Network Thread Started");

    while (isRunning) {
        if (sock == -1) {
            sock = socket(AF_INET, SOCK_STREAM, 0);
            struct sockaddr_in server;
            server.sin_addr.s_addr = inet_addr(Config::SERVER_IP);
            server.sin_family = AF_INET;
            server.sin_port = htons(Config::SERVER_PORT);

            if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
                close(sock);
                sock = -1;
                sleep(2); 
                continue;
            }
            LOGD(">>> Connected to Python Server <<<");
            CommandManager::Instance().Clear(); 
        }

        {
            std::lock_guard<std::mutex> lock(queueMutex);
            while (!sendQueue.empty()) {
                if (sendData(sendQueue.front())) {
                    sendQueue.pop();
                } else {
                    close(sock);
                    sock = -1;
                    break; 
                }
            }
        }
        
        if (sock == -1) continue;

        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(sock, &readfds);
        struct timeval timeout = {0, 50000}; 

        int activity = select(sock + 1, &readfds, NULL, NULL, &timeout);

        if (activity > 0 && FD_ISSET(sock, &readfds)) {
            char buffer[4096];
            memset(buffer, 0, sizeof(buffer));
            int read_size = recv(sock, buffer, sizeof(buffer) - 1, 0);

            if (read_size > 0) {
                processIncomingData(buffer, read_size);
            } else {
                LOGE("Server disconnected");
                close(sock);
                sock = -1;
            }
        }
        usleep(10000); 
    }
}