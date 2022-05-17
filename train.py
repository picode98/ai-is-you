import torch
import pydirectinput

import enum
import subprocess
from time import sleep
from pathlib import Path

from agent import RLAgent
from biy_basic_model import BIYBasicModel


class BIYMove(enum.IntEnum):
    LEFT = 0
    UP = 1
    RIGHT = 2
    DOWN = 3
    WAIT = 4
    UNDO = 5


class BIYGame:
    moves_to_keys = {BIYMove.LEFT: 'left', BIYMove.UP: 'up', BIYMove.RIGHT: 'right', BIYMove.DOWN: 'down',
                     BIYMove.WAIT: 'space', BIYMove.UNDO: 'z'}

    def __init__(self, biy_path: Path):
        self.proc_handle = subprocess.Popen([biy_path], cwd=biy_path.parent, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print('Waiting for game to start...')
        sleep(5.0)

        while True:
            this_line = self.proc_handle.stdout.readline().decode('utf8')
            item_parts = this_line.split(':', maxsplit=2)
            if len(item_parts) == 2 and item_parts[0] == 'cfg':
                self.num_unit_types = int(item_parts[1])
                break

        pydirectinput.press('space')  # dismiss intro credits
        print('Waiting for intro credit transition...')
        sleep(2.0)
        pydirectinput.press('space')  # continue playing
        print('Waiting for map to load...')
        sleep(15.0)
        self._input_state_tensor()  # map is technically a level; read and discard state output
        pydirectinput.press('space')  # enter last level (for now)
        print('Waiting for level to load...')
        sleep(10.0)
        self.player_found, self.game_won, self.current_state = self._input_state_tensor()
        print('Game load complete.')

    def _input_state_tensor(self):
        level_win = False
        while True:
            this_line = self.proc_handle.stdout.readline().decode('utf8').strip()
            item_parts = this_line.split(':', maxsplit=2)
            if len(item_parts) == 3 and item_parts[0] == 'unit_map':
                return (item_parts[1] == '1'), level_win, torch.tensor([[int(val) for val in unit.split(',')] for unit in item_parts[2].split(';')],
                                    dtype=torch.int64)
            elif this_line == 'level_win':
                level_win = True

    def make_move(self, move: BIYMove) -> torch.Tensor:
        pydirectinput.press(BIYGame.moves_to_keys[move])

        self.player_found, self.game_won, self.current_state = self._input_state_tensor()
        return self.current_state

    def restart_level(self):
        if self.game_won:
            sleep(10.0)
            self._input_state_tensor()  # map is technically a level; read and discard state output
            pydirectinput.press('space')
            sleep(8.0)
        else:
            pydirectinput.press('r')
            sleep(3.0)
            self._input_state_tensor()  # discard input from turn_end hook

        self.player_found, self.game_won, self.current_state = self._input_state_tensor()

    def __del__(self):
        self.proc_handle.kill()


if __name__ == '__main__':
    attempts = 20
    turns_per_attempt = 1000
    biy_path = Path('path\\to\\Baba Is You.exe')
    pydirectinput.PAUSE = 0.035
    ml_device = torch.device('cuda:0')
    # resource.setrlimit(resource.RLIMIT_STACK, (20 * 1024 * turns_per_attempt, 20 * 1024 * turns_per_attempt))

    biy_game = BIYGame(biy_path)
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
