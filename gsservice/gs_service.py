import gspread
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_NAME = "Botting"
SHEET_NAME = "Nards"

class GoogleSheetLogger:
    def __init__(self):
        self.gc = None
        self.sheet = None
        self._connect()

    def _connect(self):
        """Авторизация и подключение к таблице"""
        try:
            self.gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
            sh = self.gc.open(SPREADSHEET_NAME)
            
            try:
                self.sheet = sh.worksheet(SHEET_NAME)
            except gspread.WorksheetNotFound:
                self.sheet = sh.add_worksheet(title=SHEET_NAME, rows=1000, cols=20)
            
            self._ensure_headers()
            print("✅ Подключено к Google Sheets")
        except Exception as e:
            print(f"⚠️ Ошибка подключения к таблице: {e}")

    def _ensure_headers(self):
        """Создает шапку, если таблица пустая"""
        if not self.sheet: return
        try:
            if not self.sheet.row_values(1):
                headers = [
                    "Date",          # dd.mm.yy
                    "Time",          # hh:mm
                    "Variant", 
                    "Hero Name", 
                    "Hero Club", 
                    "Opponent Name", 
                    "Opponent Club", 
                    "Currency",      
                    "Result", 
                    "Stake", 
                    "Profit (Adj -10%)"
                ]
                self.sheet.append_row(headers)
        except:
            pass

    def append_log(self, row_data: list):
        """Пишет строку. При ошибке пробует переподключиться."""
        try:
            self.sheet.append_row(row_data)
        except Exception:
            print("🔄 Реконнект к Google Sheets...")
            self._connect()
            try:
                self.sheet.append_row(row_data)
            except Exception as e:
                print(f"❌ Не удалось записать лог: {e}")

gs_logger = GoogleSheetLogger()