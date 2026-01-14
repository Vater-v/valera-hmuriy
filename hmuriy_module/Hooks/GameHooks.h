#pragma once
#include <cstdint>

namespace GameHooks {
    // Инициализация хуков. Вызывается из потока инициализации
    void Install(uintptr_t baseAddress);
}