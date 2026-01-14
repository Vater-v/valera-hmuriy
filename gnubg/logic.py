# logic.py
import subprocess
import os
import re
import math
import base64
from typing import List, Dict, Tuple
from pathlib import Path

current_dir = Path(__file__).resolve().parent
# Adjust path if necessary
gnubg_path = current_dir.parent / "gnubg_engine" / "gnubg"

# Path to executable
GNUBG_PATH = str(gnubg_path)
TIMEOUT = 60.0  # Increased timeout slightly as 3-ply analysis takes longer

# Configuration Constants
THREADS = 16
CACHE_SIZE = 65536  # Set a large cache (size in entries or appropriate unit for gnubg)

# --- 1. GENERATE ID (Synthesis P1 + P2) ---

def _bits_to_bytes_le(bits: str, byte_count: int = None) -> bytes:
    """Packs bit string into bytes (Little-Endian bits within byte)."""
    if byte_count:
        target_len = byte_count * 8
        if len(bits) < target_len:
            bits += '0' * (target_len - len(bits))
        bits = bits[:target_len]
    else:
        rem = len(bits) % 8
        if rem: bits += '0' * (8 - rem)

    out = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i:i+8]
        val = 0
        for idx, bit_char in enumerate(chunk):
            if bit_char == '1':
                val |= (1 << idx)
        out.append(val)
    return bytes(out)

def _int_to_bits(val: int, width: int) -> str:
    return "".join(['1' if (val >> i) & 1 else '0' for i in range(width)])

def get_ids(
    p_board: List[int], o_board: List[int],
    match: object, dice: List[int], double_offered: bool
) -> Tuple[str, str]:

    # --- POSITION ID ---
    def encode_checkers(arr):
        s = ""
        for i in range(1, 25): s += "1" * arr[i] + "0"
        s += "1" * arr[0] + "0"
        return s

    raw_pid_bits = encode_checkers(o_board) + encode_checkers(p_board)
    pid_bytes = _bits_to_bytes_le(raw_pid_bits, byte_count=10) # 80 bits
    pid = base64.b64encode(pid_bytes).decode('ascii').rstrip('=')

    # --- MATCH ID ---
    on_roll_val = 1 if double_offered else 0
    turn_owner_val = 0 # We always take action in this API

    log2 = int(math.log2(match.cube_value)) if match.cube_value >= 1 else 0

    own_map = {0: 0, 1: 1, 3: 3}
    own_bits = own_map.get(match.cube_holder, 3)

    d1 = dice[0] if dice else 0
    d2 = dice[1] if len(dice) > 1 else 0

    mbits = (
        _int_to_bits(log2, 4) +
        _int_to_bits(own_bits, 2) +
        _int_to_bits(on_roll_val, 1) +
        _int_to_bits(1 if match.crawford else 0, 1) +
        _int_to_bits(1, 3) + # GameState=Playing
        _int_to_bits(turn_owner_val, 1) +
        _int_to_bits(1 if double_offered else 0, 1) +
        _int_to_bits(0, 2) + # Resign
        _int_to_bits(d1, 3) +
        _int_to_bits(d2, 3) +
        _int_to_bits(match.match_length, 15) +
        _int_to_bits(match.score_player, 15) +
        _int_to_bits(match.score_opponent, 15) +
        _int_to_bits(1 if not match.jacoby else 0, 1)
    )

    mid_bytes = _bits_to_bytes_le(mbits, byte_count=9)
    mid = base64.b64encode(mid_bytes).decode('ascii').rstrip('=')

    return pid, mid

# --- 2. EXECUTION AND PARSING ---

def run_gnubg(pid: str, mid: str) -> str:
    """
    Constructs the script with high-performance settings and specific ply depth,
    then executes GNUbg.
    """
    commands = [
        # 1. Performance Settings
        f"set threads {THREADS}",
        f"set cache {CACHE_SIZE}",
        
        # 2. Evaluation Settings (Applied EVERY time before hint)
        "set evaluation chequerplay evaluation plies 3",
        "set evaluation cubedecision evaluation plies 3",
        
        # 3. Game State
        f"set matchid {mid}",
        f"set board {pid}",
        
        # 4. Action
        "hint 1", # Execute analysis
        "exit"
    ]
    
    script = "\n".join(commands) + "\n"

    try:
        proc = subprocess.run(
            [GNUBG_PATH, "-t", "-q"],
            input=script,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=TIMEOUT,
            errors='replace'
        )
        return proc.stdout
    except Exception as e:
        return f"ERROR: {e}"

# Regex for parsing moves
_MOVE_ISLAND_RE = re.compile(
    r"((?:"
    r"\b(?:bar|off|\d{1,2})\*?"
    r"(?:/(?:bar|off|\d{1,2})\*?)+"
    r"(?:\(\d+\))?"
    r"\s*"
    r")+)", re.IGNORECASE
)

_PROPER_CUBE_RE = re.compile(r"proper cube action:\s*(?P<action>.+?)(?:\((?P<pct>[\d.,]+)%\))?\s*$", re.IGNORECASE)

def _expand_chain_token(token: str) -> List[Dict[str, int]]:
    token = token.strip()
    cnt = 1
    m = re.search(r"\((\d+)\)$", token)
    if m:
        cnt = int(m.group(1))
        token = token[:m.start()]

    parts = token.split('/')
    if len(parts) < 2: return []

    clean_pts = []
    for p in parts:
        p = p.replace('*', '').lower()
        if p == 'bar': val = 25
        elif p == 'off': val = 0
        else: val = int(p)
        clean_pts.append(val)

    segments = []
    for i in range(len(clean_pts) - 1):
        segments.append({'from': clean_pts[i], 'to': clean_pts[i+1]})

    final = []
    for _ in range(cnt):
        final.extend(segments)
    return final

def _reduce_turn_path(atomic: List[Dict[str, int]]) -> List[Dict[str, int]]:
    if not atomic: return []
    moves = [m.copy() for m in atomic]
    reduced = []

    while moves:
        dests = {m['to'] for m in moves}
        start_node = None
        for m in moves:
            if m['from'] not in dests:
                start_node = m
                break

        if not start_node:
            start_node = moves[0]

        moves.remove(start_node)
        curr_f, curr_t = start_node['from'], start_node['to']

        while True:
            next_node = None
            for m in moves:
                if m['from'] == curr_t:
                    next_node = m
                    break
            if next_node:
                moves.remove(next_node)
                curr_t = next_node['to']
            else:
                break
        reduced.append({'from': curr_f, 'to': curr_t})

    reduced.sort(key=lambda x: (x['from'], x['to']), reverse=True)
    return reduced

def parse_output(raw: str, receiving_double: bool):
    lines = raw.splitlines()

    # 1. Parsing Move
    move_str = None
    for line in lines:
        if "Eq.:" in line:
            left = line.split("Eq.:")[0]
            m = _MOVE_ISLAND_RE.search(left)
            if m:
                move_str = m.group(1).strip()
                break

    atomic = []
    reduced = []
    if move_str:
        tokens = move_str.split()
        for t in tokens:
            atomic.extend(_expand_chain_token(t))
        reduced = _reduce_turn_path(atomic)

    # 2. Parsing Cube
    c_act = "unknown"
    c_txt = "Unknown"

    m_prop = _PROPER_CUBE_RE.search(raw)
    action_raw = ""
    if m_prop:
        action_raw = m_prop.group("action").lower()
    else:
        action_raw = raw.lower()

    if receiving_double:
        if "beaver" in action_raw:
            c_act, c_txt = "take", "Beaver (Take)"
        elif "take" in action_raw or "accept" in action_raw:
             c_act, c_txt = "take", "Take"
        elif "no double" in action_raw or "no redouble" in action_raw:
             c_act, c_txt = "take", "Take (Opponent Error)"
        elif "pass" in action_raw or "drop" in action_raw:
             c_act, c_txt = "pass", "Pass"
        else:
             c_act, c_txt = "take", "Take (Unclear)"

    else:
        if "no double" in action_raw or "no redouble" in action_raw:
            c_act, c_txt = "no_double", "No Double"
        elif "double, pass" in action_raw:
            c_act, c_txt = "double_pass", "Double / Pass"
        elif "double, take" in action_raw:
            c_act, c_txt = "double_take", "Double / Take"
        elif "redouble, pass" in action_raw:
             c_act, c_txt = "double_pass", "Redouble / Pass"
        elif "redouble, take" in action_raw:
             c_act, c_txt = "double_take", "Redouble / Take"
        elif "beaver" in action_raw:
             c_act, c_txt = "beaver", "Beaver"
        else:
             if "double" in action_raw and "no" not in action_raw:
                 c_act, c_txt = "double_take", "Double (Generic)"
             else:
                 c_act, c_txt = "no_double", "No Double (Default)"

    return move_str, atomic, reduced, c_act, c_txt