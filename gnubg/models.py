# models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class BoardData(BaseModel):
    """
    Board state.
    Arrays of 25 ints: index 0 = Bar, 1-24 = Points.
    """
    player_board: List[int] = Field(..., min_length=25, max_length=25, description="Player checkers (Hero). 0=Bar, 1-24=Points")
    opponent_board: List[int] = Field(..., min_length=25, max_length=25, description="Opponent checkers. 0=Bar, 1-24=Points")

class MatchData(BaseModel):
    match_length: int = Field(0, description="0 = Money Game")
    score_player: int = 0
    score_opponent: int = 0
    cube_value: int = 1
    # 0=Player, 1=Opponent, 3=Center
    cube_holder: int = 3
    crawford: bool = False
    jacoby: bool = False

class HintRequest(BaseModel):
    board: BoardData
    match: MatchData
    # Dice. e.g. [5, 2]. For double decision pass [0, 0].
    dice: List[int] = Field(..., min_length=2, max_length=2)
    # Flag: if True, double is offered TO us, we decide Take/Pass.
    double_offered: bool = False

class AtomicMove(BaseModel):
    from_pt: int = Field(..., alias="from")
    to_pt: int = Field(..., alias="to")

class HintResponse(BaseModel):
    status: Literal["ok", "error"]
    pos_id: str
    match_id: str

    # Move decision
    best_move_raw: Optional[str] = None       # "24/20 13/8"
    best_move_atomic: List[AtomicMove] = []   # Detailed: [{'from': 24, 'to': 20}, ...]
    best_move_reduced: List[AtomicMove] = []  # Reduced: [{'from': 24, 'to': 16}]

    # Cube decision
    cube_action: str  # "no_double", "double_pass", "take", "pass"
    cube_text: str    # Readable text

    error_msg: Optional[str] = None