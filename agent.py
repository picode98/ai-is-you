from __future__ import annotations
from typing import Dict, Hashable, List, Optional, Tuple, Any, NamedTuple

import torch
import torch.nn.functional
import numpy as np

from utils import IntTensorMap


class StateTreeNode(NamedTuple):
    state: torch.Tensor
    action: Any
    reward: float
    parent: Optional[StateTreeNode]
    children: List[StateTreeNode]


class RLAgent:
    def __init__(self, move_list: List, undo_move, state_cat_sizes: List[Optional[int]], ml_model: torch.nn.Module, model_input_device: Optional[torch.device] = None):
        self.all_moves = move_list
        self.undo_move = undo_move
        self.bel_state: Optional[torch.Tensor] = None
        self.player_found = None
        self.previous_action_counts: IntTensorMap = IntTensorMap()
        self.next_move_num: int = 0
        self.checkpoints: List[int] = []
        self.revert_target_move: Optional[int] = None
        self.revert_depth: int = 1
        self.last_move = None
        self.state_tree_root: Optional[StateTreeNode] = None
        self.current_state_node: Optional[StateTreeNode] = None
        self.replay_buffer: List[Tuple[torch.Tensor, Any, float]] = []  # (state, action, reward) tuples

        self.state_cat_sizes = state_cat_sizes
        self.ml_model = ml_model
        self.model_input_device = model_input_device
        self.ml_loss = torch.nn.MSELoss()
        self.ml_optimizer = torch.optim.Adam(self.ml_model.parameters(), lr=0.01)

    def explore_move(self):
        existing_count_map: Dict[Hashable, int] = self.previous_action_counts.get(self.bel_state)

        if existing_count_map is None:
            p_map = None
        else:
            max_val = max(existing_count_map.values())
            p_map = torch.softmax(max_val - torch.tensor(list(existing_count_map.values()), dtype=torch.float), dim=0).numpy()

        return self.all_moves[np.random.choice(np.arange(len(self.all_moves)), 1, p=p_map)[0]]

    @torch.no_grad()
    def model_move(self):
        sa_tuples = [self._enc_state_action(self.bel_state, action) for action in self.all_moves]
        input_batch_states = torch.nn.utils.rnn.pack_sequence([enc_state for enc_state, enc_action in sa_tuples], enforce_sorted=False)
        input_batch_actions = torch.stack([enc_action for enc_state, enc_action in sa_tuples])

        if self.model_input_device is not None:
            input_batch_states, input_batch_actions = input_batch_states.to(self.model_input_device), \
                                                      input_batch_actions.to(self.model_input_device)

        pred_values = self.ml_model.forward(input_batch_states, input_batch_actions)
        return self.all_moves[torch.argmax(pred_values).item()]

    def _reward_for(self, state: torch.Tensor, player_found: bool, win_state: bool):
        if win_state:
            return 0
        elif not player_found:
            return -100
        else:
            return -1

    def env_feedback(self, new_bel_state: torch.Tensor, game_won: bool, player_found: bool):
        assert len(new_bel_state.shape) == 2 and new_bel_state.shape[1] == len(self.state_cat_sizes)
        this_reward = self._reward_for(new_bel_state, player_found, game_won)

        if self.last_move is None:
            self.current_state_node = self.state_tree_root = StateTreeNode(new_bel_state, None, 0.0, None, [])
        elif self.last_move == self.undo_move:
            assert self.current_state_node is not None
            self.current_state_node = self.current_state_node.parent
        else:
            new_node = StateTreeNode(state=new_bel_state, action=self.last_move, reward=this_reward,
                                     parent=self.current_state_node, children=[])
            self.current_state_node.children.append(new_node)
            self.current_state_node = new_node

        self.bel_state = new_bel_state
        self.player_found = player_found

    def _pop_move(self):
        self.next_move_num -= 1
        if len(self.checkpoints) > 0 and self.next_move_num <= self.checkpoints[-1]:
            self.checkpoints.pop()

    def next_move(self, explore_prob=0.25):
        if not self.player_found or self.revert_target_move is not None:
            self._pop_move()

            if self.revert_target_move is not None and self.next_move_num <= self.revert_target_move:
                self.revert_target_move = None

            self.last_move = self.undo_move
            return self.undo_move

        existing_count_map: Dict[Hashable, int] = self.previous_action_counts.get(self.bel_state)

        if existing_count_map is not None and len(self.checkpoints) > 0 and self.next_move_num - self.checkpoints[-1] >= 50:
            self.revert_target_move = self.checkpoints[-self.revert_depth] if self.revert_depth <= len(self.checkpoints) else 0
            self._pop_move()
            self.revert_depth += 1
            self.last_move = self.undo_move
            return self.undo_move

        move = self.explore_move() if np.random.rand() <= explore_prob else self.model_move()
        if existing_count_map is None:
            self.previous_action_counts[self.bel_state] = {mv: int(mv == move) for mv in self.all_moves}
            self.checkpoints.append(self.next_move_num)
        else:
            existing_count_map[move] += 1

        self.next_move_num += 1
        self.last_move = move
        return move

    def _calc_future_reward(self, root_node: StateTreeNode):
        # This would be cleaner as a recursive function, but the trees can be deeper than the recursion limit.
        result_stack = [(root_node, [])]

        while True:
            current_root, current_results = result_stack[-1]
            if len(current_results) >= len(current_root.children):
                max_future_reward = 0.0 if len(current_root.children) == 0 else max(current_results)
                self.replay_buffer.append((current_root.state, current_root.action, max_future_reward))
                result_stack.pop()

                if len(result_stack) > 0:
                    # print(f'Pop: {current_root.reward} + {max_future_reward}')
                    result_stack[-1][1].append(current_root.reward + max_future_reward)
                else:
                    break
            else:
                # print(f'Push: child {len(current_results)} of {len(current_root.children)}')
                result_stack.append((current_root.children[len(current_results)], []))

    def _enc_state_action(self, state: torch.Tensor, action):
        input_components = [(torch.nn.functional.one_hot(state[:, col], num_classes=cat_size) if cat_size is not None
                             else torch.reshape(state[:, col], (-1, 1)))
                            for col, cat_size in zip(range(state.shape[1]), self.state_cat_sizes)]
        return torch.concat(input_components, dim=1), torch.nn.functional.one_hot(torch.tensor([int(action)], dtype=torch.long),
                                                            num_classes=len(self.all_moves))

    def update_model(self, batch_size: int = 500):
        assert self.state_tree_root is not None

        self._calc_future_reward(self.state_tree_root)

        sa_tuples = [self._enc_state_action(state, action) for state, action, _ in self.replay_buffer if action is not None]
        actual_rewards = torch.tensor([reward for _, action, reward in self.replay_buffer if action is not None],
                                      dtype=torch.float, device=self.model_input_device)

        for start_idx in range(0, len(sa_tuples), batch_size):
            self.ml_optimizer.zero_grad()
            input_batch_states = torch.nn.utils.rnn.pack_sequence(
                [enc_state for enc_state, enc_action in sa_tuples[start_idx:start_idx + batch_size + 1]], enforce_sorted=False)
            input_batch_actions = torch.stack(
                [enc_action for enc_state, enc_action in sa_tuples[start_idx:start_idx + batch_size + 1]])
            if self.model_input_device is not None:
                input_batch_states, input_batch_actions = input_batch_states.to(self.model_input_device), \
                                                          input_batch_actions.to(self.model_input_device)

            pred_rewards = self.ml_model.forward(input_batch_states, input_batch_actions)
            loss: torch.Tensor = self.ml_loss(pred_rewards, actual_rewards[start_idx:start_idx + batch_size + 1])
            loss.backward()
            self.ml_optimizer.step()

    def reset_level_state(self):
        self.current_state_node = self.state_tree_root = None
        self.last_move = None
        self.next_move_num = 0
        self.checkpoints.clear()
        self.revert_target_move = None
        self.revert_depth = 1
        self.bel_state = self.player_found = None
