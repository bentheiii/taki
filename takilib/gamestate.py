from enum import Enum


class _GameState(str):
    pass


class _StakedState(_GameState):
    def __new__(cls, arg, stake):
        ret = super().__new__(cls, arg)
        ret.stake = stake
        return ret

    def __add__(self, other: int):
        return type(self)(self, self.stake + other)


class GameState:
    no_game = _GameState('no_game')
    normal = _GameState('normal')
    setup = _GameState('setup')
    skip = _GameState('skip')
    plus = _GameState('+')
    king = _GameState('king')
    plus_two = _StakedState('+2', 2)


assert GameState.plus_two == (GameState.plus_two + 2)
