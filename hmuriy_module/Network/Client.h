#pragma once

#include <string>
#include <queue>
#include <mutex>
#include <pthread.h>

class NetworkClient {
private:
    int sock = -1;
    bool isRunning = true;
    pthread_t netThreadId;

    // Очередь на отправку
    std::queue<std::string> sendQueue;
    std::mutex queueMutex;

    // Буфер для входящих данных (склейка пакетов)
    std::string incomingBuffer;

    NetworkClient();
    
    bool sendData(const std::string& data);
    void run();
    static void* thread_entry(void* instance);
    void enqueueMessage(std::string msg);
    
    // Парсинг входящих данных
    void processIncomingData(char* buffer, int length);
    void handlePacket(const std::string& packet);

public:
    NetworkClient(const NetworkClient&) = delete;
    void operator=(const NetworkClient&) = delete;
    static NetworkClient& Instance();

    void Start();
    
    // Проверка состояния сокета (для оптимизации хуков)
    bool IsConnected() const { return sock != -1; }

    void SendToast(const std::string& text);
    void SendHint(const std::string& text);
    void SendRaw(const std::string& text);
};
