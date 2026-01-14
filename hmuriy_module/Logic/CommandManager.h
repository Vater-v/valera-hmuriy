#pragma once

#include <string>
#include <deque>
#include <mutex>
#include <chrono>
#include <memory>

// Конфигурация
namespace CmdConfig {
    const int RETRY_INTERVAL_MS = 2000;
    const int MAX_RETRIES = 3;
    
    // Защита от дребезга (игнор дублей)
    const int DEBOUNCE_MS = 350; 
    
    // === НОВЫЕ ЗАДЕРЖКИ ===
    const int DELAY_BEFORE_MS = 300; // Минимальная задержка "ПЕРЕД" отправкой (возраст команды)
    const int DELAY_BETWEEN_MS = 300; // Минимальная пауза "МЕЖДУ" отправками
}

struct GameCommand {
    std::string id;             
    bool executedLocally;       
    bool confirmedByServer;     
    int retryCount;             
    std::chrono::steady_clock::time_point enqueueTime; // Время добавления в очередь
};

class CommandManager {
private:
    std::deque<GameCommand> queue;
    std::mutex mtx;

    // --- DEBOUNCE & THROTTLE ---
    std::string lastExecutedPayload;
    std::chrono::steady_clock::time_point lastExecutionTime;  // Когда была последняя такая же команда (для debounce)
    std::chrono::steady_clock::time_point lastGlobalSendTime; // Когда мы физически отправили любой пакет (для паузы между)

    // Singleton
    CommandManager() = default;
    ~CommandManager() = default;

public:
    CommandManager(const CommandManager&) = delete;
    void operator=(const CommandManager&) = delete;
    static CommandManager& Instance();

    void AddCommand(const std::string& cmdId);
    void ConfirmSuccess(const std::string& receivedSuccessMsg);
    void AnalyzeGameResponse(const std::string& jsonResponse);
    
    // Возвращает команду только если прошли все таймеры
    std::string ProcessQueue();
    
    void Clear();
};