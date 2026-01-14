import socket
import threading
import json
import time
import datetime
import requests
from .brain import BotBrain

class GameServer:
    def __init__(self, port, player_id, api_url, timing_config=None, log_file="traffic.jsonl"):
        self.HOST = '0.0.0.0'
        self.PORT = port
        self.PLAYER_ID = player_id
        self.API_URL = api_url
        self.LOG_FILE = log_file
        
        # Настройки аналитики
        self.ANALYTICS_URL = "http://localhost:5950/write-msg"
        
        self.timing_config = timing_config 
        self.current_client = None
        self.lock = threading.Lock()
        self.running = True

    # --- [ANALYTICS] МЕТОДЫ ОТПРАВКИ ---

    def _send_analytics_background(self, log_entry):
        """Отправляет лог в аналитику в фоновом потоке с отладкой."""
        def task():
            try:
                # API требует player_id в query параметрах
                params = {"player_id": self.PLAYER_ID}
                
                print(f">>> [ANALYTICS] Sending report to {self.ANALYTICS_URL}...")
                
                # Тело запроса — это JSON объект лога
                response = requests.post(
                    self.ANALYTICS_URL, 
                    params=params, 
                    json=log_entry, 
                    timeout=5.0 
                )
                
                # ПРОВЕРКА ОТВЕТА
                if response.status_code == 200:
                    print(f"✅ [ANALYTICS SUCCESS] Report accepted. Code: 200")
                else:
                    # Если ошибка (422 Unprocessable Entity, 500 Internal Error и т.д.)
                    print(f"🔥 [ANALYTICS FAIL] Status: {response.status_code}")
                    print(f"   Response Body: {response.text}")
                    
            except Exception as e:
                print(f"🔥 [ANALYTICS CONNECTION ERROR] {e}")

        # Запускаем поток как daemon (закроется вместе с основным процессом)
        threading.Thread(target=task, daemon=True).start()

    def _check_and_send_analytics(self, direction, raw_data, log_entry):
        """
        Упрощенная проверка: если в строке есть 'GameFinished', сразу отправляем.
        Никакого парсинга JSON, никакой валидации структуры.
        """
        if direction != "IN":
            return

        # ПРОСТЕЙШАЯ ПРОВЕРКА НА ВХОЖДЕНИЕ ПОДСТРОКИ
        if "GameFinished" in raw_data:
            print(f">>> [ANALYTICS] 💰 GameFinished detected (substring check)! Sending report...")
            self._send_analytics_background(log_entry)

    # ---------------------------------------------

    def log_raw(self, direction, data):
        # Удаляем переносы строк для красивого лога в файл
        clean_msg = data.replace("\n", " | ")
        
        entry = {
            "ts": datetime.datetime.now().isoformat(),
            "dir": direction,
            "msg": data  # Отправляем оригинальный JSON/строку
        }
        
        # [ANALYTICS] Проверка и отправка (теперь просто по наличию слова)
        self._check_and_send_analytics(direction, data, entry)
        
        # Лог в файл
        file_entry = entry.copy()
        file_entry["msg"] = clean_msg
        
        with self.lock:
            try:
                with open(self.LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(file_entry, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"[ERR] Log error: {e}")

    def send_raw(self, text):
        if self.current_client:
            try:
                msg = text + "\n"
                self.current_client.sendall(msg.encode('utf-8'))
                self.log_raw("OUT", text)
            except Exception as e:
                print(f"[ERR] Send error: {e}")

    def process_bot_response(self, response):
        if not response: return

        if isinstance(response, list):
            print(f">>> [SEQ] Start Sequence ({len(response)} steps)")
            for step in response:
                if not isinstance(step, dict): continue
                action_type = step.get('type')
                
                if action_type == 'wait':
                    sec = step.get('seconds', 0.1)
                    time.sleep(sec)
                
                elif action_type == 'send':
                    payload = step.get('payload')
                    hint = step.get('hint', '')
                    msg_str = ""
                    if hint: msg_str += f"HINT: {hint}"
                    if payload:
                        if hint: msg_str += "\n"
                        msg_str += f"API: {json.dumps(payload)}"
                    print(f"   [SEQ] >> Send: {hint}")
                    self.send_raw(msg_str)
            print(">>> [SEQ] Finished")
            return

        if isinstance(response, str):
            self.send_raw(response)

    def handle_client(self, conn, addr):
        print(f"\n[+] CLIENT CONNECTED: {addr} (Port {self.PORT})")
        self.current_client = conn

        try:
            bot = BotBrain(self.PLAYER_ID, self.API_URL, self.timing_config)
            print(f"[*] BotBrain initialized for ID: {self.PLAYER_ID}")
        except Exception as e:
            print(f"[ERR] Init failed: {e}")
            import traceback
            traceback.print_exc()
            conn.close()
            return
        
        buffer = ""
        try:
            while True:
                data = conn.recv(4096)
                if not data: break
                
                buffer += data.decode('utf-8', errors='ignore')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    if not line: continue
                    
                    self.log_raw("IN", line)

                    try:
                        response = bot.process(line)
                        self.process_bot_response(response)
                    except Exception as e:
                        print(f"[ERR] Process error: {e}")
                        import traceback
                        traceback.print_exc()

        except Exception as e:
            print(f"[ERR] Connection error: {e}")
        finally:
            print(f"[-] DISCONNECT: {addr}")
            if self.current_client == conn:
                self.current_client = None
            conn.close()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((self.HOST, self.PORT))
        except OSError as e:
            print(f"ERROR: Port {self.PORT} is busy! {e}")
            return

        server.listen(1)
        print(f"==========================================")
        print(f"[*] SERVER LISTENING ON PORT {self.PORT}")
        print(f"[*] PLAYER ID: {self.PLAYER_ID}")
        print(f"[*] LOG FILE:  {self.LOG_FILE}")
        print(f"[*] ANALYTICS: {self.ANALYTICS_URL}")
        print(f"==========================================")
        
        t = threading.Thread(target=self._listen_loop, args=(server,), daemon=True)
        t.start()
        
        try:
            while True:
                cmd = input() 
                if cmd:
                    cmd = cmd.replace("\\n", "\n")
                    self.send_raw(cmd)
        except KeyboardInterrupt:
            print("\nExit.")

    def _listen_loop(self, server_socket):
        while self.running:
            conn, addr = server_socket.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()