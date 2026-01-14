#include "GameHooks.h"
#include "../Utils/Logger.h"
#include "../Utils/And64InlineHook.hpp"
#include "../Logic/CommandManager.h"
#include "../Network/Client.h"
#include "../Utils/StringUtils.h"
#include "../Game/GameConfig.h"

#include <string>
#include <sstream>
#include <iomanip> // Для std::put_time, std::setw
#include <chrono>  // Для времени
#include <ctime>   // Для gmtime
#include <dlfcn.h> // Для dlsym
#include <deque>   // Для очереди сообщений

// =============================================================
// ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
// =============================================================

void* g_CupControllerInstance = nullptr;
void* g_SocketBusInstance = nullptr;    

// --- Очередь отправки (Smart Debounce / Burst Mode) ---
std::deque<std::string> g_SendQueue;
std::chrono::steady_clock::time_point g_LastSendTime = std::chrono::steady_clock::now();

// --- Настройки Burst Mode (Взрывной серии) ---
// Разрешаем отправить до 8 пакетов почти мгновенно.
// Это покрывает большинство игровых ситуаций (активный ход).
const int BURST_LIMIT = 8; 
int g_CurrentBurstCount = 0;
std::chrono::steady_clock::time_point g_LastBurstResetTime = std::chrono::steady_clock::now();

// Задержки
const int DELAY_FAST_MS = 40;   // 40мс - быстрая отправка (в пределах лимита)
const int DELAY_SLOW_MS = 350;  // 350мс - защита от спама (если лимит превышен)
const int BURST_RESET_MS = 1200; // Сброс счетчика серии через 1.2 сек тишины

// =============================================================
// ОПРЕДЕЛЕНИЕ ТИПОВ ФУНКЦИЙ
// =============================================================

// --- Unity ---
void (*orig_Update)(void* instance);
void* (*orig_SerializeObject)(void* value);
void* (*orig_DeserializeObject)(void* str, void* type, void* settings);

// --- Backgammon ---
typedef void (*CupController_Ctor_t)(void* instance, void* board, void* cmd);
CupController_Ctor_t orig_CupController_Ctor = nullptr;
typedef void (*CupController_Roll_t)(void* instance);
CupController_Roll_t func_CupController_Roll = nullptr;

// --- Network ---
typedef void (*SocketBus_Ctor_t)(void* instance, void* webSocket, void* queue, void* signal, bool log);
SocketBus_Ctor_t orig_SocketBus_Ctor = nullptr;

typedef void* (*WebSocket_SendText_t)(void* instance, void* message);
WebSocket_SendText_t func_SendText = nullptr;

// il2cpp string creation
typedef void* (*il2cpp_string_new_t)(const char* str);
il2cpp_string_new_t func_il2cpp_string_new = nullptr;

// =============================================================
// ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
// =============================================================

struct Il2CppString {
    void* klass;
    void* monitor;
    int32_t length;       
    char16_t chars[0];    
};

std::string ReadIl2CppString(void* ptr) {
    if (!ptr) return "";
    Il2CppString* il2cppStr = (Il2CppString*)ptr;
    if (il2cppStr->length <= 0) return "";
    
    std::string s;
    for(int i=0; i<il2cppStr->length; i++) {
        s += (char)il2cppStr->chars[i];
    }
    return s;
}

void* CreateIl2CppString(const char* str) {
    if (func_il2cpp_string_new) {
        return func_il2cpp_string_new(str);
    }
    return nullptr;
}

// Генерация времени в формате: 2026-01-10T13:43:35.630385Z
std::string GetCurrentTimeISO8601() {
    using namespace std::chrono;
    
    // Получаем текущее время
    auto now = system_clock::now();
    auto now_c = system_clock::to_time_t(now);
    
    // Вычисляем микросекунды
    auto duration = now.time_since_epoch();
    auto micros = duration_cast<microseconds>(duration) % 1000000;

    // Конвертируем в структуру времени (UTC)
    std::tm tm_buf;
    gmtime_r(&now_c, &tm_buf); // gmtime_r потокобезопасна

    char buffer[32];
    // Форматируем дату и время до секунд
    std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", &tm_buf);

    // Собираем полную строку с микросекундами и Z
    std::stringstream ss;
    ss << buffer << "." << std::setfill('0') << std::setw(6) << micros.count() << "Z";
    
    return ss.str();
}

// =============================================================
// ЛОГИКА ОТПРАВКИ JSON
// =============================================================

void SendDirectJson(const char* innerPayload) {
    // 1. Проверки
    if (g_SocketBusInstance == nullptr) {
        LOGE("SendDirectJson: No SocketBus instance! (Wait for game connection)");
        NetworkClient::Instance().SendToast("Error: No SocketBus!");
        return;
    }
    if (func_SendText == nullptr) {
        LOGE("SendDirectJson: SendText function pointer is null!");
        return;
    }

    // 2. Получаем указатель на WebSocket (поле offset 0x48)
    void* webSocketInstance = *(void**)((uintptr_t)g_SocketBusInstance + Config::OFFSET_SOCKETBUS_WEBSOCKET);
    if (webSocketInstance == nullptr) {
        LOGE("SendDirectJson: WebSocket field is null!");
        return;
    }

    // 3. Работаем с ID сообщения (поле offset 0x5C)
    // Читаем текущий ID из памяти игры
    int* pIdCounter = (int*)((uintptr_t)g_SocketBusInstance + Config::OFFSET_SOCKETBUS_ID);
    
    // Инкрементируем (мы как бы "занимаем" следующий слот)
    *pIdCounter = *pIdCounter + 1;
    int currentId = *pIdCounter;

    // 4. Генерируем время (оно будет актуальным на момент фактической отправки)
    std::string timestamp = GetCurrentTimeISO8601();

    // 5. Собираем ПОЛНЫЙ пакет
    std::stringstream ss;
    ss << "{\"id\":" << currentId 
       << ",\"time\":\"" << timestamp << "\""
       << ",\"type\":\"StageAction\"" 
       << ",\"payload\":" << innerPayload << "}";

    std::string fullPacket = ss.str();

    // 6. Конвертируем в C# строку
    void* il2cppStr = CreateIl2CppString(fullPacket.c_str());
    if (!il2cppStr) {
        LOGE("SendDirectJson: Failed to create string");
        return;
    }

    // 7. Отправляем через WebSocket.SendText
    LOGW("GameHooks: >>> SENDING PACKET ID [%d]: %s", currentId, fullPacket.c_str());
    func_SendText(webSocketInstance, il2cppStr);
}

// =============================================================
// ХУКИ
// =============================================================

// Хук конструктора SocketBus: ловим instance
void H_SocketBus_Ctor(void* instance, void* webSocket, void* queue, void* signal, bool log) {
    g_SocketBusInstance = instance;
    LOGI("GameHooks: Captured SocketBus instance: %p", instance);
    
    if (orig_SocketBus_Ctor) {
        orig_SocketBus_Ctor(instance, webSocket, queue, signal, log);
    }
}

// ОСНОВНОЙ ЦИКЛ (UPDATE) - SMART BURST LOGIC
void H_Update(void* instance) {
    if (orig_Update) orig_Update(instance);

    // 1. Забираем ВСЕ команды из CommandManager
    // Мы НЕ проверяем дубликаты здесь, как и требовалось.
    while(true) {
        std::string jsonPayload = CommandManager::Instance().ProcessQueue();
        if (jsonPayload.empty()) break;
        
        LOGI("[MainThread] Queuing API Payload: %s", jsonPayload.c_str());
        g_SendQueue.push_back(jsonPayload);
    }

    // 2. Обработка очереди с умной задержкой
    if (!g_SendQueue.empty()) {
        auto now = std::chrono::steady_clock::now();
        
        // А. Проверяем, сколько времени прошло с последнего сброса серии
        // Если была пауза > 1.2 сек, считаем, что игрок начал новую серию действий
        auto timeSinceBurstReset = std::chrono::duration_cast<std::chrono::milliseconds>(now - g_LastBurstResetTime).count();
        if (timeSinceBurstReset > BURST_RESET_MS) {
            g_CurrentBurstCount = 0; // Сброс счетчика
            g_LastBurstResetTime = now;
        }

        // Б. Определяем задержку
        // Если количество действий в серии меньше 8 -> задержка 40мс
        // Если больше 8 -> включаем троттлинг 350мс
        int currentRequiredDelay = (g_CurrentBurstCount < BURST_LIMIT) ? DELAY_FAST_MS : DELAY_SLOW_MS;

        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - g_LastSendTime).count();

        if (elapsed >= currentRequiredDelay) {
            // Время пришло
            std::string payloadToSend = g_SendQueue.front();
            g_SendQueue.pop_front();

            // Отправляем
            SendDirectJson(payloadToSend.c_str());

            // Обновляем состояние
            g_LastSendTime = now;
            g_LastBurstResetTime = now; // Сбрасываем таймер простоя, так как мы активны
            g_CurrentBurstCount++;      // Увеличиваем счетчик серии
        }
    }
}

// Логгирование исходящего JSON (сериализация)
void* H_SerializeObject(void* value) {
    void* res = orig_SerializeObject(value);
    if (res) {
        std::string s = ReadIl2CppString(res);
        if (!Utils::IsSpamOrIgnored(s)) {
            if (NetworkClient::Instance().IsConnected()) {
                NetworkClient::Instance().SendRaw("OUT: " + Utils::SmartMinify(s));
            }
        }
    }
    return res;
}

// Логгирование входящего JSON (десериализация)
void* H_DeserializeObject(void* str, void* type, void* settings) {
    if (str) {
         std::string s = ReadIl2CppString(str);
         if (!Utils::IsSpamOrIgnored(s)) {
             if (NetworkClient::Instance().IsConnected()) {
                NetworkClient::Instance().SendRaw("IN: " + Utils::SmartMinify(s));
            }
         }
    }
    return orig_DeserializeObject(str, type, settings);
}

// Хук стаканчика
void H_CupController_Ctor(void* instance, void* board, void* cmd) {
    g_CupControllerInstance = instance;
    if (orig_CupController_Ctor) orig_CupController_Ctor(instance, board, cmd);
}

// =============================================================
// УСТАНОВКА
// =============================================================

void GameHooks::Install(uintptr_t baseAddress) {
    LOGI("GameHooks: Initialization started...");

    // 1. Ищем функцию создания строк
    void* libHandle = dlopen("libil2cpp.so", RTLD_NOW);
    if (libHandle) {
        func_il2cpp_string_new = (il2cpp_string_new_t)dlsym(libHandle, "il2cpp_string_new");
        if (func_il2cpp_string_new) LOGI("GameHooks: Found il2cpp_string_new");
        else LOGE("GameHooks: Failed to find il2cpp_string_new");
    }

    // 2. Ставим хуки
    A64HookFunction((void*)(baseAddress + Config::RVA_UPDATE_FUNC), (void*)H_Update, (void**)&orig_Update);
    A64HookFunction((void*)(baseAddress + Config::RVA_SERIALIZE), (void*)H_SerializeObject, (void**)&orig_SerializeObject);
    A64HookFunction((void*)(baseAddress + Config::RVA_DESERIALIZE), (void*)H_DeserializeObject, (void**)&orig_DeserializeObject);
    
    A64HookFunction((void*)(baseAddress + Config::RVA_CUP_CTOR), (void*)H_CupController_Ctor, (void**)&orig_CupController_Ctor);
    A64HookFunction((void*)(baseAddress + Config::RVA_SOCKETBUS_CTOR), (void*)H_SocketBus_Ctor, (void**)&orig_SocketBus_Ctor);

    // 3. Сохраняем адреса для прямых вызовов
    func_CupController_Roll = (CupController_Roll_t)(baseAddress + Config::RVA_ROLL_METHOD);
    func_SendText = (WebSocket_SendText_t)(baseAddress + Config::RVA_WEBSOCKET_SENDTEXT);

    LOGI("GameHooks: Hooks installed with Burst Queue System (Limit: 8).");
}