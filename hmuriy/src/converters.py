import json
import traceback

class StateConverter:
    @staticmethod
    def extract_gnubg_input(payload, my_player_id):
        """
        Парсит payload и возвращает данные для GnuBG.
        Возвращает: board_data, match_data, dice, available_actions, is_reversed, active_player_id
        """
        try:
            data = payload.get("data", {})
            game_state = data.get("gameState", {})
            available_actions = payload.get("availableActions", []) # Get actions early

            # --- HELPER: Умный поиск по ключу ---
            def get_entity(key, default=None):
                if default is None: default = {}
                val = data.get(key)
                if val: return val
                val = game_state.get(key)
                if val: return val
                return default

            # --- 1. ИГРОКИ И НАПРАВЛЕНИЕ ---
            players_info = get_entity("players")
            players_states = get_entity("playersStates")
            
            opponent_id = None
            my_start_pos = 23
            idx_to_uid = {}

            for key, p_data in players_info.items():
                uid = p_data.get("userId")
                p_idx = p_data.get("seatIndex", p_data.get("index"))
                if p_idx is not None:
                    idx_to_uid[int(p_idx)] = uid

                if uid == my_player_id:
                    st = players_states.get(uid, {})
                    if "boardStartPosition" in st:
                        my_start_pos = st["boardStartPosition"]
                else:
                    opponent_id = uid

            reverse_me = (my_start_pos == 0)

            # --- 2. ДОСКА ---
            hero_checkers = [0] * 25
            opp_checkers = [0] * 25
            
            board_obj = get_entity("board")
            bar_counts = board_obj.get("barCounts", {})
            
            hero_checkers[0] = bar_counts.get(my_player_id, 0)
            opp_checkers[0] = bar_counts.get(opponent_id, 0)
            
            raw_points = board_obj.get("points", [])

            for pt in raw_points:
                num = pt.get("number")
                count = pt.get("checkersCount", 0)
                occupied_by = pt.get("occupiedBy")
                
                if not occupied_by or count == 0:
                    continue
                
                hero_view_idx = 0
                if reverse_me:
                    hero_view_idx = 25 - num
                else:
                    hero_view_idx = num

                if not (1 <= hero_view_idx <= 24):
                    continue

                if occupied_by == my_player_id:
                    hero_checkers[hero_view_idx] = count
                elif occupied_by == opponent_id:
                    opp_view_idx = 25 - hero_view_idx
                    opp_checkers[opp_view_idx] = count

            board_data = {
                "player_board": hero_checkers,
                "opponent_board": opp_checkers
            }

            # --- 3. МАТЧ ---
            cube_info = get_entity("doublingCube")
            cube_val = cube_info.get("value", 1)
            cube_holder = 3 
            
            if cube_val > 1:
                visual_states = get_entity("doublingCubeVisualStates", [])
                for vs in visual_states:
                    if vs.get("value") is True:
                        aid = vs.get("accountId")
                        if aid == my_player_id: cube_holder = 0
                        elif aid == opponent_id: cube_holder = 1
                        break
            
            match_data = {
                "match_length": 0,
                "score_player": 0,
                "score_opponent": 0,
                "cube_value": cube_val,
                "cube_holder": cube_holder,
                "crawford": False,
                "jacoby": True
            }

            # --- 4. ОПРЕДЕЛЕНИЕ АКТИВНОГО ИГРОКА ---
            current_turn = get_entity("currentTurn")
            active_player_id = None
            
            if "userId" in current_turn:
                active_player_id = current_turn["userId"]
            elif "playerIndex" in current_turn:
                active_player_id = idx_to_uid.get(current_turn["playerIndex"])

            # --- 5. КОСТИ (С ФИЛЬТРАЦИЕЙ) ---
            dice = [0, 0]
            
            # [FIX] Считаем, что это наши кости, ТОЛЬКО если:
            # 1. Точно наш ID в currentTurn
            # 2. ИЛИ (ID неизвестен, НО нам разрешено ходить 'MoveChecker')
            # 3. И при этом нам НЕ предлагают дабл (DoublingOffer), т.к. при дабле кости еще не брошены
            
            is_definitely_opp = (active_player_id and active_player_id != my_player_id)
            can_move = ("MoveChecker" in available_actions)
            can_double = ("DoublingOffer" in available_actions)

            should_extract_dice = False
            
            if not is_definitely_opp and not can_double:
                # Если нам можно ходить - берем кости смело
                if can_move:
                    should_extract_dice = True
                # Если ход вроде наш, но MoveChecker нет (анимация?), берем только если ID совпал
                elif active_player_id == my_player_id:
                     should_extract_dice = True

            if should_extract_dice:
                ct_dice = current_turn.get("dice")
                if ct_dice and isinstance(ct_dice, dict):
                    d1 = ct_dice.get("first", 0)
                    d2 = ct_dice.get("second", 0)
                    if d1 > 0:
                        dice = [d1, d2]
                
                # Фолбек (firstDiceRoll) используем только в самом начале игры
                if dice == [0, 0] and not can_move: 
                    fd = get_entity("firstDiceRoll")
                    if fd:
                        # Проверяем, не устарел ли firstDiceRoll
                        # Обычно он актуален только если cube_val == 1 и шашки на старте
                        dice = [fd.get("first", 0), fd.get("second", 0)]
            
            if sum(dice) > 0:
                 print(f"[CONVERTER] My Dice found: {dice}")

            return board_data, match_data, dice, available_actions, reverse_me, active_player_id

        except Exception as e:
            print("\n" + "!"*30)
            print(">>> CRITICAL PARSING ERROR <<<")
            print(f"EXCEPTION: {e}")
            traceback.print_exc()
            print("!"*30 + "\n")
            raise e