#pragma once
#include <cstdint>

// Функция для получения базового адреса загруженной библиотеки по имени
uintptr_t get_lib_addr(const char* lib_name);