import json
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks, Query, HTTPException
from pydantic import BaseModel
from datetime import datetime
from gs_service import gs_logger
import re

app = FastAPI(title="PPN Analytics API")

# Модель входящих данных (верхний уровень)
class LogPayload(BaseModel):
    ts: str
    dir: str
    msg: str  # Внутри этой строки лежит JSON с игрой


def process_game_data(payload: LogPayload, hero_id: str):
    """
    Фоновая задача: парсинг, расчет финансов и запись в таблицу.
    Версия 5.1: Разделение даты и времени, человеческий формат.
    """
    try:
        # 1. Распаковка "матрешки"
        inner_msg = {}
        raw_msg = payload.msg
        
        try:
            # Попытка 1: В лоб
            inner_msg = json.loads(raw_msg)
        except json.JSONDecodeError:
            # Попытка 2: Хирургия
            clean_msg = re.sub(r'[\n\r\t\f\v]', '', raw_msg)
            
            try:
                inner_msg = json.loads(clean_msg, strict=False)
            except json.JSONDecodeError:
                # Попытка 3: АМПУТАЦИЯ (для длинных описаний клубов)
                if '"description"' in clean_msg:
                    parts = clean_msg.rsplit(',"description"', 1)
                    cut_msg = parts[0]
                    
                    success = False
                    for i in range(1, 15):
                        candidate = cut_msg + ("}" * i)
                        try:
                            inner_msg = json.loads(candidate, strict=False)
                            print(f"🏥 [Surgery] Успешная ампутация description! Добавлено {i} скобок.")
                            success = True
                            break
                        except json.JSONDecodeError:
                            continue
                    
                    if not success:
                        print(f"❌ [FATAL] Ампутация не помогла.")
                        return
                else:
                    print(f"❌ [CRITICAL] JSON битый и без description.")
                    return

        # 2. Фильтр: нас интересует только конец игры
        if inner_msg.get("type") != "StageEvent":
            return
        
        event_payload = inner_msg.get("payload", {})
        if event_payload.get("name") != "GameFinished":
            return

        # 3. Извлекаем данные
        data = event_payload.get("data", {})
        variant = data.get("gameVariant")
        
        # Инфо о ставке и валюте
        stake_info = data.get("stake", {})
        currency = stake_info.get("amountType", "unknown") 
        
        # --- Определяем Кто есть Кто через GameResult ---
        game_result = data.get("gameResult", {})
        winner_obj = game_result.get("winner", {})
        loser_obj = game_result.get("loser", {})
        
        winner_id = winner_obj.get("user", {}).get("accountId") or winner_obj.get("user", {}).get("id")
        
        clean_hero_id = hero_id.strip()
        
        # Логика распределения ролей
        if str(winner_id) == clean_hero_id:
            # Герой выиграл
            is_win = True
            hero_data = winner_obj
            opp_data = loser_obj
        else:
            # Герой проиграл
            is_win = False
            hero_data = loser_obj
            opp_data = winner_obj
        
        # Данные Героя
        hero_name = hero_data.get("user", {}).get("username") or hero_data.get("accountInfo", {}).get("login", "Unknown")
        hero_club_name = hero_data.get("clubMemberProfile", {}).get("club", {}).get("title", "No Club")

        # Данные Оппонента
        opp_name = opp_data.get("user", {}).get("username") or opp_data.get("accountInfo", {}).get("login", "Unknown")
        opp_club_name = opp_data.get("clubMemberProfile", {}).get("club", {}).get("title", "No Club")

        # --- Финансы ---
        result_str = "WIN" if is_win else "LOSS"

        all_stakes = stake_info.get("stakesByPlayer", {})
        hero_stake = float(all_stakes.get(clean_hero_id, 0.0))
        
        net_bank = float(stake_info.get("netBankValue", 0.0))
        
        all_refunds = stake_info.get("netRefundsByPlayer", {}) or stake_info.get("refundsByPlayer", {})
        hero_refund = float(all_refunds.get(clean_hero_id, 0.0))

        # Чистый профит
        revenue = (net_bank if is_win else 0.0) + hero_refund
        raw_profit = revenue - hero_stake

        # --- Корректировка профита (-10%) ---
        adj_profit = raw_profit - (abs(raw_profit) * 0.10)

        # 4. Форматирование Даты и Времени
        try:
            # Парсим ISO строку (например: 2026-01-13T00:17:28.062182)
            dt_obj = datetime.fromisoformat(payload.ts)
            date_str = dt_obj.strftime("%d.%m.%y") # 13.01.26
            time_str = dt_obj.strftime("%H:%M")    # 00:17
        except Exception:
            # Фолбэк на текущее время, если парсинг сломался
            now = datetime.now()
            date_str = now.strftime("%d.%m.%y")
            time_str = now.strftime("%H:%M")

        # 5. Пишем в таблицу
        # Структура: Date | Time | Variant | Hero | Hero Club | Opponent | Opp Club | Currency | Result | Stake | Profit (Adj)
        row = [
            date_str,
            time_str,
            variant,
            hero_name,
            hero_club_name,
            opp_name,
            opp_club_name,
            currency,
            result_str,
            hero_stake,
            round(adj_profit, 2)
        ]
        
        gs_logger.append_log(row)
        print(f"✅ Logged: {date_str} {time_str} | {hero_name} vs {opp_name} | {result_str} | {round(adj_profit, 2)}")

    except Exception as e:
        print(f"❌ GLOBAL Error processing log: {e}")
        import traceback
        traceback.print_exc()


@app.post("/write-msg")
async def write_msg(
    request: Request,
    background_tasks: BackgroundTasks,
    player_id: str = Query(..., description="UUID нашего игрока (HERO, обязательно)")
):
    try:
        body = await request.json()
        
        print(f"\n--------------------------------------------------")
        print(f"📥 [INCOMING] /write-msg | Player: {player_id}")
        print(f"--------------------------------------------------\n")

        payload = LogPayload(**body)
        background_tasks.add_task(process_game_data, payload, player_id)
        
        return {"status": "ok", "msg": "processing"}
    except Exception as e:
        print(f"❌ Error in /write-msg: {e}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=5950, reload=True)