import subprocess
from pathlib import Path
from time import sleep

import pydirectinput
import torch

from biy_game_base import BIYGameBase, BIYMove


class BIYRemoteGame(BIYGameBase):
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
                num_unit_types = int(item_parts[1])
                break

        super().__init__(num_unit_types)

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
        pydirectinput.press(BIYRemoteGame.moves_to_keys[move])

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
