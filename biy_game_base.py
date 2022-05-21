import enum
from abc import ABC
from typing import Optional

import torch


class BIYMove(enum.IntEnum):
    LEFT = 0
    UP = 1
    RIGHT = 2
    DOWN = 3
    WAIT = 4
    UNDO = 5


class BIYGameBase(ABC):
    def __init__(self, num_unit_types: int):
        self.player_found: bool = True
        self.game_won: bool = False
        self.current_state: Optional[torch.Tensor] = None
        self.num_unit_types: int = num_unit_types

    def make_move(self, move: BIYMove) -> torch.Tensor:
        return NotImplemented

    def restart_level(self):
        return NotImplemented
