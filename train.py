import torch
import pydirectinput

from pathlib import Path

from agent import RLAgent
from biy_basic_model import BIYBasicModel
from biy_mock import MockBIYGame
from biy_game_base import BIYMove


if __name__ == '__main__':
    attempts = 20
    turns_per_attempt = 1000
    biy_path = Path('path\\to\\Baba Is You.exe')
    pydirectinput.PAUSE = 0.035
    ml_device = torch.device('cuda:0')
    # resource.setrlimit(resource.RLIMIT_STACK, (20 * 1024 * turns_per_attempt, 20 * 1024 * turns_per_attempt))

    biy_game = MockBIYGame(biy_path.parent)  # BIYGame(biy_path)
    all_moves = list(x for x in BIYMove if x != BIYMove.UNDO)
    state_cat_sizes = [None, None, biy_game.num_unit_types, 4]
    state_vec_len = sum(x if x is not None else 1 for x in state_cat_sizes)  # Categories are one-hot encoded; others are input as integers.
    model = BIYBasicModel(state_vec_len, all_moves, device=ml_device)
    agent = RLAgent(all_moves, BIYMove.UNDO, state_cat_sizes, model, ml_device)
    agent.env_feedback(biy_game.current_state, biy_game.game_won, biy_game.player_found)

    for attempt in range(attempts):
        for _ in range(turns_per_attempt):
            biy_game.make_move(agent.next_move(0.8 - attempt * 0.04))

            if biy_game.game_won:
                print('Game won!')
                break

            agent.env_feedback(biy_game.current_state, biy_game.game_won, biy_game.player_found)

        agent.update_model()
        agent.reset_level_state()
        biy_game.restart_level()
        agent.env_feedback(biy_game.current_state, biy_game.game_won, biy_game.player_found)
