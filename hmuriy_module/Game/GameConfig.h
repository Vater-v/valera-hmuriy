#pragma once
#include <cstdint>

namespace Config {
    // --- [ NETWORK ] ---
    constexpr const char* SERVER_IP = "127.0.0.1";
    constexpr int SERVER_PORT = 11111;

    // --- [ ADDRESSES / RVAs ] ---
    // 1. Системные (Unity / System)
    constexpr uintptr_t RVA_UPDATE_FUNC = 0x5A80A84;
    constexpr uintptr_t RVA_SERIALIZE   = 0x5375EA0;
    constexpr uintptr_t RVA_DESERIALIZE = 0x5376614;

    // 2. Игровые (Backgammon)
    // Контроллер стаканчика (старый метод)
    constexpr uintptr_t RVA_CUP_CTOR    = 0x30568D4; 
    constexpr uintptr_t RVA_ROLL_METHOD = 0x3056A34; 

    // 3. Сеть (SocketBus / WebSocket) — НОВОЕ
    // Конструктор SocketBus (нужен, чтобы перехватить ссылку на экземпляр)
    // Token: 0x060000B3
    constexpr uintptr_t RVA_SOCKETBUS_CTOR = 0x5370B8C; 
    
    // Метод NativeWebSocket.WebSocket.SendText (отправка "чистого" текста)
    // Token: 0x0600005F
    constexpr uintptr_t RVA_WEBSOCKET_SENDTEXT = 0x327F690;

    // Смещения полей в классе SocketBus
    // private readonly IWebSocket _webSocket; // Token 0x04000075
    constexpr uintptr_t OFFSET_SOCKETBUS_WEBSOCKET = 0x48; 
    
    // private int _id; // Token 0x04000078
    constexpr uintptr_t OFFSET_SOCKETBUS_ID        = 0x5C; 
}