cmake_minimum_required(VERSION 3.10.2)

project("ValeraHmuriy")
add_compile_options(-Wno-deprecated-declarations)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Создаем библиотеку с именем hmuriy
add_library(
	hmuriy
	SHARED
	main.cpp
	Game/GameConfig.h
	Hooks/GameHooks.cpp
	Logic/CommandManager.cpp
	Network/Client.cpp
	Utils/MemoryUtils
	Utils/And64InlineHook.cpp
)

# ВАЖНО: Убираем префикс "lib", чтобы файл назывался "hmuriy.so", а не "libhmuriy.so"
set_target_properties(hmuriy PROPERTIES PREFIX "")

find_library(
        log-lib
        log
)

target_link_libraries(
        hmuriy
        ${log-lib}
)