#pragma once
#include <string>
#include <cctype>

namespace Utils {

    // JSON Minifier: убирает пробелы/переносы вне кавычек
    inline std::string SmartMinify(const std::string& input) {
        if (input.empty()) return "";
        
        // Резервируем память, чтобы избежать лишних аллокаций
        std::string output;
        output.reserve(input.length()); 
        
        bool insideQuotes = false;
        
        for (size_t i = 0; i < input.length(); ++i) {
            char c = input[i];
            
            // Обработка кавычек (с учетом экранирования)
            if (c == '"' && (i == 0 || input[i - 1] != '\\')) {
                insideQuotes = !insideQuotes;
            }
            
            if (insideQuotes) {
                // Внутри кавычек сохраняем всё, но экранируем спецсимволы, если нужно
                // (В исходной строке они уже экранированы, но на всякий случай просто копируем)
                output += c;
            } else {
                // Вне кавычек пропускаем пробельные символы
                if (!std::isspace(static_cast<unsigned char>(c))) {
                    output += c;
                }
            }
        }
        return output;
    }

    // Проверка на спам и мусорные пакеты
    inline bool IsSpamOrIgnored(const std::string& content) {
        // 1. Лимиты по длине
        if (content.length() < 40 || content.length() > 200000) {
            return true;
        }

        // 2. Ключевые слова спама
        if (content.find("\"verbose_localised_name\"") != std::string::npos) return true;
        if (content.find("\"keys\":{\"APIError") != std::string::npos) return true;
        // Добавь сюда другие фильтры, если нужно
        
        return false;
    }
}