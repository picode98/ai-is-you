import torch
import pydirectinput

import enum
import subprocess
from time import sleep
from pathlib import Path

from model import RLModel


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
        self.player_found, self.current_state = self._input_state_tensor()
        print('Game load complete.')

    def _input_state_tensor(self):
        while True:
            this_line = self.proc_handle.stdout.readline().decode('utf8')
            item_parts = this_line.split(':', maxsplit=2)
            if len(item_parts) == 3 and item_parts[0] == 'unit_map':
                return (item_parts[1] == '1'), torch.tensor([[int(val) for val in unit.split(',')] for unit in item_parts[2].split(';')],
                                    dtype=torch.int64)

    def make_move(self, move: BIYMove) -> torch.Tensor:
        pydirectinput.press(BIYGame.moves_to_keys[move])

        self.player_found, self.current_state = self._input_state_tensor()
        return self.current_state

    def __del__(self):
        self.proc_handle.kill()


if __name__ == '__main__':
    biy_path = Path('path\\to\\Baba Is You.exe')
    pydirectinput.PAUSE = 0.035

    model = RLModel(set(BIYMove).difference([BIYMove.UNDO]), BIYMove.UNDO)
    biy_game = BIYGame(biy_path)
    model.env_feedback(biy_game.current_state, biy_game.player_found)

    for _ in range(1000):
        biy_game.make_move(model.next_move())
        model.env_feedback(biy_game.current_state, biy_game.player_found)
