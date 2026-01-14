# main.py
import uvicorn
from fastapi import FastAPI, HTTPException
from models import HintRequest, HintResponse
import logic
from visualizer import print_console_debug

app = FastAPI(title="Gnubg API", version="2.1")

@app.post("/get-optimal-move", response_model=HintResponse)
def get_optimal_move(req: HintRequest):
    """
    Endpoint for optimal checker play.
    """
    try:
        # 1. Generate ID
        pid, mid = logic.get_ids(
            req.board.player_board,
            req.board.opponent_board,
            req.match,
            req.dice,
            double_offered=False
        )

        # 2. Run GNUbg (now with 3-ply and multi-thread)
        raw_out = logic.run_gnubg(pid, mid)

        if "ERROR" in raw_out:
            print(f"GNUbg Critical Error:\n{raw_out}")
            raise HTTPException(status_code=500, detail=raw_out)

        # 3. Parse
        mv_str, atomic, reduced, c_act, c_txt = logic.parse_output(raw_out, receiving_double=False)

        response = HintResponse(
            status="ok",
            pos_id=pid,
            match_id=mid,
            best_move_raw=mv_str,
            best_move_atomic=atomic,
            best_move_reduced=reduced,
            cube_action=c_act,
            cube_text=c_txt
        )

        # === LOGGING ===
        print_console_debug(req, response, decision_type="move", gnubg_output=raw_out)
        # ===============

        return response
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/get-double-decision", response_model=HintResponse)
def get_double_decision(req: HintRequest):
    """
    Endpoint for cube decisions.
    """
    try:
        sim_match = req.match.copy()

        if req.double_offered:
            # === WE ARE BEING DOUBLED ===
            # Swap boards
            p_board_sim = req.board.opponent_board
            o_board_sim = req.board.player_board

            # Swap scores
            sim_match.score_player = req.match.score_opponent
            sim_match.score_opponent = req.match.score_player

            # Swap cube owner
            if req.match.cube_holder == 0:
                sim_match.cube_holder = 1
            elif req.match.cube_holder == 1:
                sim_match.cube_holder = 0

            use_double_flag = False

        else:
            # === WE ARE THINKING OF DOUBLING ===
            p_board_sim = req.board.player_board
            o_board_sim = req.board.opponent_board
            use_double_flag = False

        pid, mid = logic.get_ids(
            p_board_sim,
            o_board_sim,
            sim_match,
            [0, 0],
            double_offered=use_double_flag
        )

        raw_out = logic.run_gnubg(pid, mid)

        if "ERROR" in raw_out:
            print(f"GNUbg Critical Error:\n{raw_out}")
            raise HTTPException(status_code=500, detail=raw_out)

        _, _, _, c_act, c_txt = logic.parse_output(raw_out, receiving_double=req.double_offered)

        response = HintResponse(
            status="ok",
            pos_id=pid,
            match_id=mid,
            best_move_raw=None,
            cube_action=c_act,
            cube_text=c_txt
        )

        print_console_debug(req, response, decision_type="double", gnubg_output=raw_out)

        return response
    except Exception as e:
        print(f"ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5007)