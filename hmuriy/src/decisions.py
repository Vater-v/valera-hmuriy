import json
import itertools
import re
import uuid
import random
from timing_system import TimeManager

class DecisionMaker:
    def __init__(self, api_client):
        self.client = api_client
        self.timer = TimeManager()
        self.last_cube_hash = None  # Память для предотвращения двойного анализа

    def _response_simple(self, hint_text, api_payload=None):
        msg = f"HINT: {hint_text}"
        if api_payload:
            json_str = json.dumps(api_payload)
            msg += f"\nAPI: {json_str}"
        return msg

    def notify_new_game(self):
        print("\n>>> [DECISION] 🎲 NEW GAME DETECTED! Resetting logic...")
        self.last_cube_hash = None
        self.timer.randomize_persona()

    # --- HANDLERS ---

    def handle_game_initiation(self):
        delay = random.uniform(0.3, 5.0)
        self.timer.heartbeat_sleep(delay, f"Accepting Game in {delay:.2f}s")
        payload = {"stage": "GameInitiation", "action": "Accept"}
        return self._response_simple("Game Accepted", payload)

    def handle_bank_splitting(self):
        delay = random.uniform(2.0, 7.0)
        print(f">>> [DECISION] Bank Split offered. Rejecting in {delay:.2f}s...")
        self.timer.heartbeat_sleep(delay, "Rejecting Split")
        payload = {"stage": "GamePlay", "action": "BankSplittingReject"}
        return self._response_simple("REJECT BANK SPLIT", payload)

    def _get_stable_state_id(self, board, match):
        """
        Генерирует уникальный ID состояния. 
        sort_keys=True гарантирует, что {a:1, b:2} и {b:2, a:1} дадут одинаковую строку.
        """
        return json.dumps({
            "b": board,
            "m": match
        }, sort_keys=True)

    def handle_doubling_offer(self, board, match, actions, dice, is_reversed):
        # 1. Генерируем стабильный хеш состояния
        current_hash = self._get_stable_state_id(board, match)
        
        # 2. ПРОВЕРКА КЭША (DEBOUNCE)
        # Если мы уже анализировали эту позицию и решили "НЕ УДВАИВАТЬ",
        # мы сразу пытаемся перейти к броску или ходу, не дергая API.
        if self.last_cube_hash == current_hash:
            # print(">>> [DECISION] Skipping duplicate cube check (State Cache Hit).") # Можно раскомментировать для отладки
            if "RollDice" in actions:
                return self.handle_rolling()
            if "MoveChecker" in actions and dice and sum(dice) > 0:
                return self.handle_movement(board, match, dice, is_reversed)
            return None

        # 3. Запоминаем текущую позицию ПЕРЕД тяжелым анализом
        self.last_cube_hash = current_hash

        # 4. Анализ
        self.timer.start_turn()
        print(">>> [DECISION] Considering Doubling...")
        self.timer.wait_cube_decision(is_incoming=False)
        
        decision = self.client.get_double_decision(board, match, double_offered=False)
        
        # Fallback при ошибке API
        if not decision or decision.get("status") != "ok":
            print(">>> [ERR] API Cube Error. Skipping to Roll.")
            if "RollDice" in actions: return self.handle_rolling()
            return None

        action = decision.get("cube_action", "no_double")
        text = decision.get("cube_text", "")
        
        # 5. Решение: УДВАИВАТЬ
        if "double" in action and "no" not in action:
            self.timer.heartbeat_sleep(0.5, "Click Double")
            # СБРАСЫВАЕМ хеш, так как после нашего дабла состояние матча изменится (cube_value/holder),
            # и мы хотим, чтобы новая позиция (если дабл отклонят/примут) считалась новой.
            self.last_cube_hash = None 
            payload = {"stage": "GamePlay", "action": "DoublingOffer"}
            return self._response_simple(f"Double ({text})", payload)
        
        # 6. Решение: НЕ УДВАИВАТЬ
        print(f">>> [DECISION] Cube decision: NO DOUBLE ({text}). Passing to Action...")
        
        # Сразу пытаемся сделать следующее действие, чтобы не ждать следующего тика сервера
        if "RollDice" in actions:
            return self.handle_rolling()
            
        if "MoveChecker" in actions and dice and sum(dice) > 0:
            return self.handle_movement(board, match, dice, is_reversed)
            
        return None

    def handle_doubling_response(self, board, match):
        self.timer.start_turn()
        print(">>> [DECISION] Opponent Doubles. Analyzing...")
        self.timer.wait_cube_decision(is_incoming=True)

        decision = self.client.get_double_decision(board, match, double_offered=True)

        if not decision or decision.get("status") != "ok":
            payload = {"stage": "GamePlay", "action": "DoublingAccept"}
            return self._response_simple("ACCEPT (Fallback)", payload)

        action = decision.get("cube_action", "take") 
        text = decision.get("cube_text", "")

        if action == "pass":
            self.timer.heartbeat_sleep(0.8, "Reluctant Pass")
            payload = {"stage": "GamePlay", "action": "DoublingReject"}
            return self._response_simple(f"REJECT / PASS ({text})", payload)
        else:
            payload = {"stage": "GamePlay", "action": "DoublingAccept"}
            return self._response_simple(f"ACCEPT / TAKE ({text})", payload)

    def handle_rolling(self):
        self.timer.start_turn()
        self.timer.wait_pre_roll()
        payload = {"stage": "GamePlay", "action": "RollDice"}
        return self._response_simple("Roll Dice", payload)

    def handle_turn_confirm(self):
         # Заглушка на случай ошибок
         return None

    # --- MOVEMENT CORE ---

    def handle_movement(self, board, match, dice, is_reversed):
        print(f">>> [DECISION] Dice: {dice}. Start sequence...")
        self.timer.start_turn() 

        sequence = []
        
        # 1. API Request
        resp = self.client.get_optimal_move(board, match, dice)
        print("Api response ok")
        
        # 2. Planning Phase
        raw_reduced = []
        is_complex = False
        if resp and resp.get("status") == "ok":
            raw_reduced = resp.get("best_move_reduced", [])
            my_bar = board.get("player_board", [])
            opp_bar = board.get("opponent_board", [])
            # Проверка сложности позиции для таймингов
            if len(my_bar) > 18 and len(opp_bar) > 18 and sum(my_bar[0:18]) > 0 and sum(opp_bar[0:18]) > 0:
                is_complex = True
            if len(raw_reduced) > 4: 
                is_complex = True
        
        self.timer.wait_planning(
            moves_count=1 if len(raw_reduced) == 0 else len(raw_reduced), 
            is_complex_position=is_complex
        )

        if not raw_reduced:
             return self._response_simple("No move found (Wait/Pass)")

        pending_moves = self._expand_moves(raw_reduced)
        print("planning ok")

        # Simulation Setup
        current_dice = list(dice)
        if len(current_dice) == 2 and current_dice[0] == current_dice[1]:
            current_dice = [current_dice[0]] * 4 
        current_dice.sort(reverse=True)

        temp_my_board = list(board.get("player_board") or board.get("board", []))
        if len(temp_my_board) < 26: temp_my_board.extend([0] * (26 - len(temp_my_board)))
        temp_opp_board = list(board.get("opponent_board", []))
        
        last_destination = -1
        moves_executed_count = 0 
        was_previous_hit = False 

        # 3. Execution Phase
        while pending_moves:
            progress_made = False
            moves_to_remove = []
            
            # Приоритет хода с бара (25)
            pending_moves.sort(key=lambda m: 0 if m['from'] == 25 else 1)

            for m in pending_moves:
                final_from = m['from']
                final_to = m['to']
                
                if final_from != 25 and temp_my_board[final_from] <= 0: continue
                
                path = self._find_path(final_from, final_to, current_dice, temp_opp_board)
                
                if path:
                    for step in path:
                        d = step[2]
                        if d in current_dice: current_dice.remove(d)
                        elif current_dice: current_dice.pop(0)

                    for (p_from, p_to, p_die) in path:
                        print('execute ok')
                        
                        # --- TIMING CALCULATION ---
                        distance = abs(p_from - p_to)
                        is_bearoff = (p_to == 0)
                        
                        will_hit = False
                        if p_to > 0:
                            opp_idx = 25 - p_to
                            if 1 <= opp_idx <= 24 and len(temp_opp_board) > opp_idx and temp_opp_board[opp_idx] == 1:
                                will_hit = True

                        is_momentum = (p_from == last_destination) and (p_from != 25)

                        move_drag_time = self.timer.get_move_delay(
                            distance, 
                            is_hit=will_hit, 
                            is_bearoff=is_bearoff, 
                            is_momentum=is_momentum
                        )
                        
                        hesitation_time = 0.0
                        if not is_momentum:
                            hesitation_time = self.timer.get_inter_move_delay(
                                move_index=moves_executed_count, 
                                prev_was_hit=was_previous_hit
                            )
                        
                        total_wait = hesitation_time + move_drag_time
                        sequence.append({'type': 'wait', 'seconds': total_wait})
                        
                        last_destination = p_to
                        was_previous_hit = will_hit
                        if not is_momentum:
                            moves_executed_count += 1
                        # ---------------------------

                        move_type = "MOVE"
                        if will_hit:
                            temp_opp_board[25 - p_to] = 0
                            move_type = "ENTER_HIT" if p_from == 25 else "HIT"
                        else:
                            move_type = "ENTER_MOVE" if p_from == 25 else "MOVE"
                        if p_to == 0: move_type = "BEAR_OFF"
                        
                        if p_from != 25: temp_my_board[p_from] -= 1
                        if p_to > 0: temp_my_board[p_to] += 1

                        s_from = (25 - p_from) if is_reversed and p_from != 25 else p_from
                        s_to = (25 - p_to) if is_reversed and p_to != 0 else p_to
                        if p_from == 25: s_from = None
                        if p_to == 0: s_to = None

                        packet = {
                            "stage": "GamePlay",
                            "action": "MoveCheckerV2", 
                            "data": {
                                "moves": [{
                                    "from": s_from,
                                    "to": s_to,
                                    "die": int(p_die),
                                    "type": move_type
                                }]
                            },
                            "nonce": str(uuid.uuid4())
                        }
                        
                        hint_str = f"{p_from}{'💥' if will_hit else '➡'}{p_to}"
                        sequence.append({'type': 'send', 'payload': packet, 'hint': hint_str})

                    moves_to_remove.append(m)
                    progress_made = True
                    break 
            
            if progress_made:
                for rm in moves_to_remove:
                    try: pending_moves.remove(rm)
                    except ValueError: pass
            else:
                break

        if not sequence:
            return self._response_simple("No legal moves found")
            
        return sequence

    def _expand_moves(self, raw_moves):
        expanded = []
        if not raw_moves: return []
        if not isinstance(raw_moves, list): raw_moves = [raw_moves]
        for item in raw_moves:
            if isinstance(item, dict):
                count = item.get('count', 1)
                m_from = item.get('from')
                m_to = item.get('to')
                for _ in range(count):
                    expanded.append({"from": m_from, "to": m_to})
            elif isinstance(item, str):
                matches = re.finditer(r"(\d+|bar)\/(\d+|off|0)(?:\((\d+)\))?", item.lower())
                for match in matches:
                    s_from = match.group(1)
                    s_to = match.group(2)
                    s_count = match.group(3)
                    final_from = 25 if s_from == 'bar' else int(s_from)
                    final_to = 0 if s_to in ['off', '0'] else int(s_to)
                    count = int(s_count) if s_count else 1
                    for _ in range(count): expanded.append({"from": final_from, "to": final_to})
        return expanded

    def _find_path(self, start, end, available_dice, opp_board):
        dist_needed = start - end
        if dist_needed in available_dice: return [(start, end, dist_needed)]
        if end == 0:
            valid_dice = sorted([d for d in available_dice if d > dist_needed])
            if valid_dice: return [(start, 0, valid_dice[0])]
        for r in range(2, len(available_dice) + 1):
            unique_combos = set(itertools.permutations(available_dice, r))
            for dice_combo in unique_combos:
                if end != 0 and sum(dice_combo) != dist_needed: continue
                if end == 0 and sum(dice_combo) < dist_needed: continue
                path = []
                curr = start
                valid_combo = True
                temp_path_board = list(opp_board)
                for die in dice_combo:
                    next_pos = curr - die
                    if next_pos < 0:
                        if end == 0: next_pos = 0
                        else: valid_combo = False; break
                    is_blocked = False
                    if next_pos > 0:
                        opp_idx = 25 - next_pos
                        if 1 <= opp_idx <= 24 and temp_path_board[opp_idx] >= 2: is_blocked = True
                    if is_blocked: valid_combo = False; break
                    path.append((curr, next_pos, die))
                    if next_pos > 0:
                         opp_idx = 25 - next_pos
                         if 1 <= opp_idx <= 24 and temp_path_board[opp_idx] == 1: temp_path_board[opp_idx] = 0 
                    curr = next_pos
                    if curr == end: break
                if valid_combo and curr == end: return path
        if end == 0 and available_dice:
            best_die = max(available_dice)
            if best_die >= dist_needed: return [(start, 0, best_die)]
            if sum(available_dice) < dist_needed: return [(start, 0, best_die)]
        return None