import json
import time
from .api_client import GnubgClient 
from .converters import StateConverter
from .decisions import DecisionMaker

class BotBrain:
    def __init__(self, player_id, api_url, timing_config=None):
        self.client = GnubgClient(api_url)
        self.logic = DecisionMaker(self.client) 
        self.my_id = player_id
        print(f"[*] BotBrain init for Player: {self.my_id}")

    def process(self, raw_msg):
        try:
            msg = json.loads(raw_msg)
            if not isinstance(msg, dict): return None
        except: return None

        msg_type = msg.get("type", "")
        payload = msg.get("payload", {})
        if not payload: return None
        
        event_name = payload.get("name", "")
        stage = payload.get("stage", "")
        game_state = payload.get("gameState", {})
        phase = game_state.get("phase", "")
        
        # Игнор простого передвижения шашек (анимации оппонента)
        if event_name in ["TurnCheckerMoved", "TurnCheckerMovedV2"]:
            return None
        
        available_actions = set(payload.get("availableActions", []))

        # --- 1. ПРИОРИТЕТНЫЕ СОБЫТИЯ (Сброс игры / Инициализация) ---
        is_new_game_event = (event_name in ["MatchStarted", "GameStarted"])
        is_stage_init = (msg_type == "StageChanged" and stage == "GamePlay" and phase == "INIT")

        if stage == "GamePlay" and (is_new_game_event or is_stage_init):
            print(f">>> [BRAIN] New Game Detected. Resetting...")
            self.logic.notify_new_game()
            self.logic.timer.heartbeat_sleep(10.0, "Warmup")
            if not available_actions: return None

        if stage == "GameInitiation" and "Accept" in available_actions:
            return self.logic.handle_game_initiation()

        if stage == "GamePlay" and event_name == "BankSplittingOffered":
            return self.logic.handle_bank_splitting()

        # --- 2. ПАРСИНГ СОСТОЯНИЯ ---
        active_turn_pid = None
        board, match, dice, actions_from_state, is_reversed = None, None, None, [], False

        try:
            board, match, dice, actions_from_state, is_reversed, active_turn_pid = \
                StateConverter.extract_gnubg_input(payload, self.my_id)
            
            is_definitely_opponent = (active_turn_pid and active_turn_pid != self.my_id)

            # Лечим кубики (если система их не прислала явно, но они есть в стейте)
            if (not dice or sum(dice) == 0) and not is_definitely_opponent and "DoublingOffer" not in available_actions:
                data_obj = payload.get("data", {})
                current_turn = data_obj.get("currentTurn")
                if not current_turn and "gameState" in data_obj:
                    current_turn = data_obj["gameState"].get("currentTurn")
                if current_turn and "dice" in current_turn:
                    raw_dice = current_turn["dice"]
                    if isinstance(raw_dice, dict):
                        d1, d2 = raw_dice.get("first", 0), raw_dice.get("second", 0)
                        if d1 > 0 or d2 > 0: dice = [d1, d2]
                    elif isinstance(raw_dice, list) and len(raw_dice) >= 2:
                        dice = raw_dice[:2]

            for a in actions_from_state: 
                available_actions.add(a)
            
        except Exception as e:
            # Если парсинг упал, но можно подтвердить ход - подтверждаем
            if "TurnCommit" in available_actions:
                return self.logic.handle_turn_confirm()
            return None

        # --- [FILTER] Если ход чужой, игнорируем свои кнопки (кроме ответа на дабл) ---
        if is_definitely_opponent:
            if "DoublingAccept" not in available_actions:
                return None
            else:
                # Очищаем лишнее, если вдруг сервер прислал
                if "RollDice" in available_actions: available_actions.remove("RollDice")
                if "MoveChecker" in available_actions: available_actions.remove("MoveChecker")

        # --- 3. ОБНОВЛЕНИЕ ЛИЧНОСТИ (на начало хода) ---
        if event_name in ["TurnStarted", "DiceRolled", "DoublingAccepted"]:
            self.logic.timer.randomize_persona()

        # --- 4. МАРШРУТИЗАЦИЯ ---
        
        # A. Ответ на чужой дабл
        if "DoublingAccept" in available_actions:
            return self.logic.handle_doubling_response(board, match)

        # B. Наш ход: Сначала думаем про ДАБЛ (если доступен)
        if "DoublingOffer" in available_actions:
            if event_name != "DoublingAccepted" and not is_definitely_opponent: 
                # Логика теперь внутри сама решит: если дабл не нужен -> кинет кубики
                decision = self.logic.handle_doubling_offer(
                    board, match, list(available_actions), dice, is_reversed
                )
                if decision: return decision

        # C. Наш ход: Бросок кубиков (если дабл не доступен или уже проверен)
        if (event_name == "TurnStarted" or event_name == "DoublingAccepted") and "RollDice" in available_actions:
            if not is_definitely_opponent:
                return self.logic.handle_rolling()

        # D. Наш ход: Передвижение
        if "MoveChecker" in available_actions:
            if dice and sum(dice) > 0:
                return self.logic.handle_movement(board, match, dice, is_reversed)
            else:
                return None

        return None