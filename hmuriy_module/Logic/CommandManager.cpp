#include "CommandManager.h"
#include "../Utils/Logger.h"

using namespace std::chrono;

CommandManager& CommandManager::Instance() {
    static CommandManager instance;
    return instance;
}

void CommandManager::AddCommand(const std::string& payload) {
    std::lock_guard<std::mutex> lock(mtx);
    auto now = steady_clock::now();

    // 1. Проверка очереди (защита от мгновенного спама, пока очередь не разобрана)
    for (const auto& cmd : queue) {
        if (cmd.id == payload) {
            LOGW("CmdMgr: Ignored (Already in queue): %s", payload.c_str());
            return;
        }
    }

    // 2. DEBOUNCE (защита от повтора УЖЕ отправленной команды)
    // Если payload совпадает с прошлым И прошло меньше времени чем DEBOUNCE_MS (1.5 сек)
    auto elapsed = duration_cast<milliseconds>(now - lastExecutionTime).count();
    if (payload == lastExecutedPayload && elapsed < CmdConfig::DEBOUNCE_MS) {
        LOGW("CmdMgr: DEBOUNCE! Ignored duplicate command (elapsed: %lld ms)", elapsed);
        return;
    }

    GameCommand newCmd;
    newCmd.id = payload; 
    newCmd.executedLocally = false;
    newCmd.confirmedByServer = false;
    newCmd.retryCount = 0;
    newCmd.enqueueTime = now; // Запоминаем время добавления

    queue.push_back(newCmd);
    LOGI("CmdMgr: [+] Payload Enqueued. Waiting for delays...");
}

void CommandManager::AnalyzeGameResponse(const std::string& jsonResponse) {
    // В текущей логике валидация отключена
}

void CommandManager::ConfirmSuccess(const std::string& receivedSuccessMsg) {
    // ACK не используется
}

std::string CommandManager::ProcessQueue() {
    std::lock_guard<std::mutex> lock(mtx);

    if (queue.empty()) return "";

    auto now = steady_clock::now();
    GameCommand& current = queue.front();

    // === ПРОВЕРКА 1: Задержка "ПЕРЕД" (DELAY_BEFORE_MS) ===
    // Команда должна "полежать" в очереди минимум 300мс
    auto age = duration_cast<milliseconds>(now - current.enqueueTime).count();
    if (age < CmdConfig::DELAY_BEFORE_MS) {
        // Рано. Пусть еще полежит.
        return "";
    }

    // === ПРОВЕРКА 2: Задержка "МЕЖДУ" (DELAY_BETWEEN_MS) ===
    // Прошло ли 300мс с момента отправки ПРЕДЫДУЩЕГО пакета?
    auto timeSinceLastSend = duration_cast<milliseconds>(now - lastGlobalSendTime).count();
    if (timeSinceLastSend < CmdConfig::DELAY_BETWEEN_MS) {
        // Рано. Соблюдаем интервал между пакетами.
        return "";
    }

    // === ВСЕ ОК, ОТПРАВЛЯЕМ ===
    std::string payload = current.id;
    
    // Обновляем историю
    lastExecutedPayload = payload;
    lastExecutionTime = now;    // Для Debounce
    lastGlobalSendTime = now;   // Для интервала между пакетами

    // Удаляем из очереди
    queue.pop_front();
    
    // Лог для отладки таймингов
    LOGI("CmdMgr: >>> POP & SEND. (Age: %lld ms, Gap: %lld ms). Payload: %s", 
         age, timeSinceLastSend, payload.c_str());
    
    return payload;
}

void CommandManager::Clear() {
    std::lock_guard<std::mutex> lock(mtx);
    queue.clear();
    lastExecutedPayload = ""; 
    LOGW("CmdMgr: Queue flushed.");
}