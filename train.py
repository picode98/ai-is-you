import torch
import pydirectinput
from tqdm import tqdm

from pathlib import Path
from sys import stderr

from agent import RLAgent
from biy_basic_model import BIYBasicModel
from biy_mock import MockBIYGame
from biy_game_base import BIYMove


if __name__ == '__main__':
    attempts = 100
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

    rand_prob = 0.8
    for attempt in tqdm(range(attempts), desc='Training model...'):
        for _ in range(turns_per_attempt):
            biy_game.make_move(agent.next_move(0.8))

            if biy_game.game_won:
                print('\tGame won!')
                break

            agent.env_feedback(biy_game.current_state, biy_game.game_won, biy_game.player_found)

        avg_loss = agent.update_model()
        print(f'\tAttempt {attempt}: avg. loss: {avg_loss}, rand_prob={rand_prob}', file=stderr)

        if biy_game.game_won:
            rand_prob = max(rand_prob / 2.0, 0.005)
        else:
            rand_prob = min(rand_prob * 1.15, 0.8)

        agent.reset_level_state()
        biy_game.restart_level()
        agent.env_feedback(biy_game.current_state, biy_game.game_won, biy_game.player_found)
