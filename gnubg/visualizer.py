# visualizer.py
from models import HintRequest, HintResponse

def print_console_debug(req: HintRequest, result: HintResponse, decision_type: str = "move", gnubg_output: str = None):
    """
    Prints visualization, decision details, and raw logs to console.
    """
    p_board = req.board.player_board
    o_board = req.board.opponent_board

    C_RESET = "\033[0m"
    C_HERO = "\033[92m"  # Green
    C_OPP = "\033[91m"   # Red
    C_WARN = "\033[93m"  # Yellow
    C_BOLD = "\033[1m"
    C_BLUE = "\033[94m"
    C_GRAY = "\033[90m"

    print(f"\n{C_BOLD}{'='*60}{C_RESET}")
    print(f"{C_BLUE}>>> NEW REQUEST: {decision_type.upper()}{C_RESET}")

    p_total = sum(p_board)
    o_total = sum(o_board)

    if p_total < 15 or o_total < 15:
        print(f"{C_WARN}WARNING: Checkers count mismatch!{C_RESET}")
        print(f"Hero On Board: {p_total} (Off/Bar calculated: {15-p_total})")
        print(f"Opp  On Board: {o_total} (Off/Bar calculated: {15-o_total})")
        if o_total == 0:
            print(f"{C_WARN}>>> Opponent board is EMPTY (all zeros). Check your JSON request!{C_RESET}")

    m = req.match
    print(f"Match: {m.score_player}-{m.score_opponent} (to {m.match_length}) | Cube: {m.cube_value} (Holder: {m.cube_holder})")
    if decision_type == "move":
        print(f"Dice: {req.dice}")
    else:
        print(f"Double Offered: {req.double_offered}")

    board_vis = ["  "] * 25

    for i in range(1, 25):
        p_count = p_board[i]
        o_count = o_board[25 - i]

        if p_count > 0:
            val = f"{C_HERO}X{p_count if p_count > 1 else ''}{C_RESET}"
            board_vis[i] = val.center(5)
        elif o_count > 0:
            val = f"{C_OPP}O{o_count if o_count > 1 else ''}{C_RESET}"
            board_vis[i] = val.center(5)
        else:
            board_vis[i] = "  .  "

    p_bar = p_board[0]
    o_bar = o_board[0]

    p_off = 15 - p_total
    o_off = 15 - o_total

    print("-" * 65)
    print(f" Bar: Hero={C_HERO}{p_bar}{C_RESET} | Opp={C_OPP}{o_bar}{C_RESET}")
    print("-" * 65)

    top_indices = range(13, 25)
    row_str = "|" + "|".join([board_vis[i] for i in top_indices]) + "|"
    print(f"13-24: {row_str}")

    bot_indices = range(12, 0, -1)
    row_str = "|" + "|".join([board_vis[i] for i in bot_indices]) + "|"
    print(f"12-01: {row_str}")

    print("-" * 65)
    off_comment_p = "(WIN?)" if p_off == 15 else ""
    off_comment_o = "(EMPTY DATA?)" if o_off == 15 and "O" not in str(board_vis) else ""

    print(f" Off: Hero={C_HERO}{p_off}{C_RESET} {off_comment_p}| Opp={C_OPP}{o_off}{C_RESET} {off_comment_o}")

    print(f"\n{C_BOLD}DECISION:{C_RESET}")
    if decision_type == "move":
        print(f"Raw Move: {result.best_move_raw}")
        print(f"Parsed:   {result.best_move_reduced}")
        print(f"Cube:     {result.cube_text} ({result.cube_action})")
    else:
        print(f"Action:   {result.cube_text} ({result.cube_action})")

    if gnubg_output:
        print(f"\n{C_BOLD}--- GNUbg RAW OUTPUT (START) ---{C_RESET}")
        print(f"{C_GRAY}{gnubg_output.strip()}{C_RESET}")
        print(f"{C_BOLD}--- GNUbg RAW OUTPUT (END) ---{C_RESET}")

    print(f"{C_BOLD}{'='*60}{C_RESET}\n")