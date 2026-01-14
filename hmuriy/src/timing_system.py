import time
import random
import math

class BotPersona:
    """
    Настройки 'характера' бота.
    motor_speed: множитель скорости мыши (БОЛЬШЕ = МЕДЛЕННЕЕ).
    think_factor: множитель времени раздумий (БОЛЬШЕ = МЕДЛЕННЕЕ).
    """
    # INSTANCE:
    # Был (0.75 / 0.30). 
    # Стал чуть медленнее (+15% к таймингам), чтобы не нарушать требование "не быстрее".
    # Остается "роботом", но с человеческим лагом.
    INSTANCE = {"name": "⚡ INSTANCE", "motor_speed": 0.80, "think_factor": 0.35}
    
    # NORMAL:
    # Был (0.90 / 0.50). 
    # Значительно замедлен для создания разрыва с INSTANCE. Похож на расслабленного игрока.
    NORMAL   = {"name": "👤 HUMAN",   "motor_speed": 1.10, "think_factor": 0.75}
    
    # TURTLE:
    # Был (1.10 / 0.75).
    # Стал очень медленным. Эмуляция новичка или человека, который пьет чай.
    # Дисперсия увеличена максимально.
    TURTLE   = {"name": "🐢 TURTLE",  "motor_speed": 1.55, "think_factor": 1.25}
    
class TimeManager:
    def __init__(self):
        # --- CONSTANTS ---
        # Лимит хода (оставил 15.0, но urgency сработает точнее)
        self.TURN_HARD_LIMIT = 7.0  
        
        self.turn_start_time = 0
        self.current_persona = BotPersona.NORMAL
        
        # Состояние текущего хода
        self.last_planning_state = "normal" 
        
        self.randomize_persona()

    def randomize_persona(self):
        """Случайный выбор личности на сессию."""
        roll = random.random()
        if roll < 0.20: self.current_persona = BotPersona.INSTANCE
        elif roll < 0.80: self.current_persona = BotPersona.NORMAL
        else: self.current_persona = BotPersona.TURTLE
        print(f"[TIMING] Persona initialized: {self.current_persona['name']}")

    def start_turn(self):
        """Сброс таймера начала хода."""
        self.turn_start_time = time.time()
        self.last_planning_state = "normal"

    def elapsed(self):
        return time.time() - self.turn_start_time

    def get_urgency_factor(self):
        """
        Коэффициент спешки (0.2...1.0).
        Корректирует скорость, если время хода подходит к концу.
        """
        left = self.TURN_HARD_LIMIT - self.elapsed()
        
        if left < 0.5: return 0.3  # PANIC MODE (очень быстро)
        if left < 3.0: return 0.6  # Hurry up (ускорение)
        # Увеличил порог "расслабленности" с 9.0 до 10.0, так как тайминги выросли
        if self.elapsed() > 5.0: return 0.8 
        return 1.0

    def heartbeat_sleep(self, seconds, label=""):
        """Безопасный сон с проверкой лимита времени."""
        urgency = self.get_urgency_factor()
        final_seconds = seconds * urgency
        final_seconds = max(0.01, final_seconds)
        
        end_time = time.time() + final_seconds
        while time.time() < end_time:
            # Прерываем сон, если осталось меньше 0.5 сек до кика сервера
            if self.elapsed() > self.TURN_HARD_LIMIT - 0.5:
                break
            time.sleep(0.02) 

    def _gaussian_delay(self, mu, sigma, mn, mx):
        val = random.gauss(mu, sigma)
        val = max(mn, min(val, mx))
        val *= self.current_persona["think_factor"]
        return val

    # --- 1. ПЛАНИРОВАНИЕ (PLANNING) ---
    
    def wait_planning(self, moves_count, is_complex_position=False):
        """Пауза перед началом хода (осмотр доски)."""
        # УВЕЛИЧЕНО +15%: (0.3, 0.6) -> (0.35, 0.70)
        base_lag = random.uniform(0.01, 0.33)
        
        think_time = 0.0
        state = "normal"

        if moves_count <= 1 and not is_complex_position:
            # Forced move
            # УВЕЛИЧЕНО: max 0.15 -> 0.18
            think_time = random.uniform(0.0, 0.18)
            state = "forced"
        elif is_complex_position:
            # Deep think
            # УВЕЛИЧЕНО: mu 2.0 -> 2.3, min 0.5 -> 0.6
            think_time = self._gaussian_delay(2.3, 0.9, 0.6, 4.5)
            state = "deep"
        else:
            # Normal think
            # УВЕЛИЧЕНО: mu 0.8 -> 0.95, range расширен
            think_time = self._gaussian_delay(0.95, 0.35, 0.25, 1.75)
            state = "normal"
        
        self.last_planning_state = state
        self.heartbeat_sleep(base_lag + think_time, f"Planning ({state})")
        return state

    # --- 2. МОТОРИКА (MOTORICS) ---

    def get_move_delay(self, distance, is_hit=False, is_bearoff=False, is_momentum=False):
        """Время самого движения мыши (Drag)."""
        if is_momentum:
            # УВЕЛИЧЕНО: (0.15, 0.28) -> (0.18, 0.32)
            return random.uniform(0.18, 0.32)

        # Закон Фиттса
        dist_factor = math.log2(distance + 1)
        base_speed = self.current_persona["motor_speed"]
        
        # Формула скорректирована на +15% (было 0.45 + 0.11)
        delay = (0.52 + (0.13 * dist_factor)) * base_speed
        delay *= random.uniform(0.95, 1.20)

        if is_hit: delay += 0.30       # Было 0.25
        if is_bearoff: delay *= 0.90   # Без изменений

        urgency = self.get_urgency_factor()
        # Минимальный порог поднят с 0.15 до 0.18
        return max(0.18, delay * urgency)

    def get_inter_move_delay(self, move_index, prev_was_hit=False):
        """
        Задержка МЕЖДУ движениями ("Затуп").
        """
        if move_index == 0: 
            return 0.0 
            
        urgency = self.get_urgency_factor()
        
        # 1. Базовая пауза
        # УВЕЛИЧЕНО: (0.35, 0.85) -> (0.40, 1.0)
        hesitation = random.uniform(0.40, 1.0)
        
        # 2. Эффект "Эээ... куда сходить"
        # Шанс тот же (40%), время увеличено: (0.6, 1.5) -> (0.7, 1.75)
        if random.random() < 0.40:
            hesitation += random.uniform(0.7, 1.75)
            
        # 3. После удара
        # УВЕЛИЧЕНО: (0.5, 0.9) -> (0.6, 1.05)
        if prev_was_hit:
            hesitation += random.uniform(0.6, 1.05)

        return hesitation * self.current_persona["think_factor"] * urgency

    def wait_pre_roll(self):
        # УВЕЛИЧЕНО: mu 0.5 -> 0.6
        delay = self._gaussian_delay(0.01, 0.02, 0.03, 0.04)
        self.heartbeat_sleep(delay, "Pre-Roll Shake")

    # --- 4. КУБ ---

    def wait_cube_decision(self, is_incoming):
        # Базовые константы увеличены
        base = 1.75 if is_incoming else 0.95  # Было 1.5 и 0.8
        
        if random.random() < 0.20:
            # Глубокое раздумье над кубом
            extra = self._gaussian_delay(3.5, 1.7, 1.2, 5.5)
            self.heartbeat_sleep(base + extra, "Cube Deep")
        else:
            # Быстрое решение
            quick = self._gaussian_delay(0.95, 0.35, 0.45, 1.75)
            self.heartbeat_sleep(base + quick, "Cube Quick")