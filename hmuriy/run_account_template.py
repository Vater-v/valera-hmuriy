import sys
import os

# Добавляем пути, чтобы Python находил модуль src, 
# независимо от того, запускаете вы файл из корня или из папки
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'src'))

# Импортируем только сервер
try:
    from src.server import GameServer
except ImportError:
    # Фолбек, если структура папок плоская (все файлы в одной куче)
    from server import GameServer

# --- КОНФИГУРАЦИЯ ЗАПУСКА ---

# 1. Сетевые настройки (Бот слушает игру)
BOT_PORT = 5006

# 2. Идентификация
PLAYER_ID = "a2b773f0-bde4-4c45-b59f-be026800c3ae"

# 3. Настройки API (Куда стучаться за ходами)
GNUBG_API_URL = "http://127.0.0.1:5007" 

# 4. Логирование
LOG_FILE = "raw_traffic_account1.jsonl"

if __name__ == "__main__":
    print(f"--- LAUNCHING BOT FOR {PLAYER_ID} ---")
    print(f"[*] API URL: {GNUBG_API_URL}")
    print(f"[*] PORT:    {BOT_PORT}")
    
    # Инициализация сервера без старого конфига timing_config
    server = GameServer(
        port=BOT_PORT,
        player_id=PLAYER_ID,
        api_url=GNUBG_API_URL,
        log_file=LOG_FILE
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")