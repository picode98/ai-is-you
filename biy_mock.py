from typing import Dict, Tuple

import torch
from lupa import LuaRuntime

from pathlib import Path
import glob
import configparser

from biy_game_base import BIYGameBase, BIYMove


class MockBIYGame(BIYGameBase):
    moves_to_keys = {BIYMove.LEFT: 'left', BIYMove.UP: 'up', BIYMove.RIGHT: 'right', BIYMove.DOWN: 'down',
                     BIYMove.WAIT: 'idle', BIYMove.UNDO: 'undo'}

    def _get_state(self):
        unit_map_table = self._mock_get_unit_map_lua()
        return torch.tensor([list(sub_table.values()) for sub_table in unit_map_table.values()], dtype=torch.long)

    def make_move(self, move: BIYMove) -> torch.Tensor:
        if move == BIYMove.UNDO:
            self.lua_env.execute('undostate(true)')
            self.lua_env.execute('mock_undo()')
        else:
            self.lua_env.execute('mock_undo_checkpoint()')
            self.lua_env.execute('undostate(false)')
            self._mock_command_lua(self.moves_to_keys[move])

        self.lua_env.execute('findplayer()')
        self.lua_env.execute('block()')
        self.current_state = self._get_state()
        self.player_found = bool(self.lua_env.eval('1 - generaldata2.values[NOPLAYER]'))

        return self.current_state

    def restart_level(self):
        self._mock_command_lua('restart')
        self.lua_env.execute('mock_clearunits()')
        self.lua_env.execute('mock_undobuffer = {}')

        for unit in self.level_orig_units:
            self._mock_addunit_lua(*unit)

        self.lua_env.execute('findplayer()')
        self.make_move(BIYMove.WAIT)  # first move populates rules and other data structures

        self.current_state = self._get_state()
        self.player_found = True
        self.game_won = False

    def _MF_alert_mock(self, msg: str):
        self.logs.append(msg)

    def _MF_setfile_mock(self, key: str, path: str):
        self._MF_mock_files[key] = (path, configparser.ConfigParser())
        self._MF_mock_files[key][1].read(self.biy_base_folder / path)

    def _MF_read_mock(self, file_key: str, group: str, item: str):
        if file_key not in self._MF_mock_files:
            return ''

        file_name, parser = self._MF_mock_files[file_key]
        return parser.get(group, item, fallback='')

    def _MF_store_mock(self, file_key: str, group: str, item: str, value: str):
        pass

    def _MF_win_mock(self):
        self.game_won = True

    def __init__(self, biy_base_folder: Path):
        self.level_orig_units =[(1001, 'object021', 5, 7, 0, 0),  # text_keke
                                (1002, 'object036', 5, 8, 0, 0),  # text_is
                                (1003, 'object058', 5, 9, 0, 0),  # text_you
                                (1004, 'object022', 7, 7, 0, 0),  # text_flag
                                (1005, 'object036', 7, 8, 0, 0),  # text_is
                                (1006, 'object045', 7, 9, 0, 0),  # text_win
                                (1007, 'object001', 9, 9, 0, 0),  # keke
                                (1008, 'object023', 2, 3, 0, 0)   # flag
        ]

        self.biy_base_folder = biy_base_folder
        script_paths = [biy_base_folder / 'Data/values.lua', biy_base_folder / 'Data/constants.lua', Path('./biy_mock_support.lua')] + \
            [Path(path) for path in glob.glob(str(biy_base_folder / 'Data/*.lua')) if not (path.endswith('values.lua') or path.endswith('constants.lua'))] + \
            [Path(path) for path in glob.glob(str(biy_base_folder / 'Data/Editor/*.lua'))]

        self.logs = []
        self._MF_mock_files: Dict[str, Tuple[str, configparser.ConfigParser]] = dict()

        self.lua_env = LuaRuntime()
        self.lua_env.globals()['MF_alert'] = lambda msg: self._MF_alert_mock(msg)
        self.lua_env.globals()['MF_setfile'] = lambda key, path: self._MF_setfile_mock(key, path)
        self.lua_env.globals()['MF_read'] = lambda file_key, group, item: self._MF_read_mock(file_key, group, item)
        self.lua_env.globals()['MF_store'] = lambda file_key, group, item, value: self._MF_store_mock(file_key, group, item, value)
        self.lua_env.globals()['MF_win'] = lambda: self._MF_win_mock()

        for this_path in script_paths:
            with open(this_path, 'r', encoding='utf8', errors='ignore') as this_file:
                file_text = this_file.read()
                self.lua_env.execute(file_text)

        super().__init__(self.lua_env.eval('num_tiles'))

        self.lua_env.execute("init(1, 15, 15, 1, 0, 0, 'generaldata', 'generaldata2', 'generaldata3',"
                             "'generaldata4', 'generaldata5', 'spritedata', 'vardata', 100, 100)")
        self.lua_env.execute('worldinit()')
        self.lua_env.execute("setupmenu('editor', 'editor2', 'editor3', 'editor4', 'selector', 'placer')")
        self.lua_env.execute('undostate(false)')
        # self.lua_env.execute('mock_postload()')
        print(list(self.lua_env.eval('generaldata.strings')))
        self._mock_addunit_lua = self.lua_env.eval('mock_addunit')
        self._mock_command_lua = self.lua_env.eval('command')
        self._mock_get_unit_map_lua = self.lua_env.eval('get_unit_map')

        for unit in self.level_orig_units:
            self._mock_addunit_lua(*unit)

        self.lua_env.execute('findplayer()')
        self.make_move(BIYMove.WAIT)  # first move populates rules and other data structures
