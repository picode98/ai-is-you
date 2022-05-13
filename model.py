from typing import Set, Dict, Hashable, List, Optional

import torch
import numpy as np

from utils import IntTensorMap


class RLModel:
    def __init__(self, move_set: Set, undo_move):
        self.all_moves = list(move_set)
        self.undo_move = undo_move
        self.bel_state: Optional[torch.Tensor] = None
        self.player_found = None
        self.previous_actions: IntTensorMap = IntTensorMap()
        self.next_move_num: int = 0
        self.checkpoints: List[int] = []
        self.revert_target_move: Optional[int] = None
        self.revert_depth: int = 1

    def explore_move(self):
        existing_count_map: Dict[Hashable, int] = self.previous_actions.get(self.bel_state)

        if existing_count_map is None:
            p_map = None
        else:
            max_val = max(existing_count_map.values())
            p_map = torch.softmax(max_val - torch.tensor(list(existing_count_map.values()), dtype=torch.float), dim=0).numpy()

        return self.all_moves[np.random.choice(np.arange(len(self.all_moves)), 1, p=p_map)[0]]

    def env_feedback(self, new_bel_state: torch.Tensor, player_found: bool):
        self.bel_state = new_bel_state
        self.player_found = player_found

    def _pop_move(self):
        self.next_move_num -= 1
        if len(self.checkpoints) > 0 and self.next_move_num <= self.checkpoints[-1]:
            self.checkpoints.pop()

    def next_move(self):
        if not self.player_found or self.revert_target_move is not None:
            self._pop_move()

            if self.revert_target_move is not None and self.next_move_num <= self.revert_target_move:
                self.revert_target_move = None

            return self.undo_move

        existing_count_map: Dict[Hashable, int] = self.previous_actions.get(self.bel_state)

        if existing_count_map is not None and len(self.checkpoints) > 0 and self.next_move_num - self.checkpoints[-1] >= 50:
            self.revert_target_move = self.checkpoints[-self.revert_depth] if self.revert_depth <= len(self.checkpoints) else 0
            self._pop_move()
            self.revert_depth += 1
            return self.undo_move


        move = self.explore_move()
        if existing_count_map is None:
            self.previous_actions[self.bel_state] = {mv: int(mv == move) for mv in self.all_moves}
            self.checkpoints.append(self.next_move_num)
        else:
            existing_count_map[move] += 1

        self.next_move_num += 1
        return move
