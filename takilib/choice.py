from __future__ import annotations

from typing import Generic, TypeVar, List, Union, Iterable

import textwrap
from abc import ABC, abstractmethod
from enum import Enum, auto
import itertools as it

T = TypeVar('T')


class AskAgain(Exception):
    pass


class DisplayInfo(Exception):
    def __init__(self, info):
        self.info = info


class GameView:
    def __init__(self, game, player):
        self.game = game
        self.player = player

    def other_players(self):
        for p in it.islice(self.game.players_by_order(self.player), 1, None):
            yield (p.name, len(p.hand))

    def pile(self):
        return reversed(self.game.pile)

    def deck_length(self):
        return len(self.game.deck)

    def last_active(self):
        return self.game.pile.last_iter()

    def __str__(self):
        return '\n'.join([
            'other players: ' + ', '.join(f'{name} ({hand} cards)' for (name, hand) in self.other_players()),
            'cards played: ' + ', '.join(str(card) for card in self.pile()),
            'currently active card: ' + str(self.last_active()),
            str(self.deck_length()) + ' cards left in deck',
        ])


class Option(ABC, Generic[T]):
    class Kind(Enum):
        regular = auto()
        convenience = auto()
        confirm = auto()
        undo = auto()
        info = auto()
        none = auto()

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def __getitem__(self, item: str) -> T:
        pass

    @abstractmethod
    def get_kind(self) -> Option.Kind:
        pass


class StandardOption(Option[T]):
    def __init__(self, keys: Union[str, Iterable[str]], description: str, value: T,
                 kind: Option.Kind = Option.Kind.regular, case_sensitive=False):
        if isinstance(keys, str):
            keys = [keys]
        keys = frozenset(keys)
        self.keys = keys

        primary_key = next((k for k in self.keys if k), '')
        if '' in self.keys:
            primary_key = f'[{primary_key}]'
        self.primary_key = primary_key

        self.description = description
        self.value = value
        self.kind = kind
        self.case_sensitive = case_sensitive

    def get_kind(self):
        return self.kind

    def __getitem__(self, item: str) -> T:
        if not self.case_sensitive:
            item = item.lower()
        if item in self.keys:
            return self.value
        raise KeyError(item)

    def __str__(self):
        if not self.description:
            return self.primary_key
        prim = self.primary_key
        if prim != '[]':
            prim = '[' + prim + ']'
        return f'{prim}\t{self.description}'


class OptionGroup(Option[T], List[Option[T]]):
    def __init__(self, inline = False):
        super().__init__()
        self.kind = self.Kind.none
        self.inline = inline

    def append(self, option: Option[T]):
        if option.get_kind() == self.Kind.none:
            pass
        elif self.kind == self.Kind.none:
            self.kind = option.get_kind()
        elif self.kind != option.get_kind():
            raise ValueError('an option group must only have one kind')

        super().append(option)

    def get_kind(self):
        return self.kind

    def __str__(self):
        return '\n'.join(str(o) for o in self) + ('' if self.inline else '\n')

    def __getitem__(self, item):
        if isinstance(item, int):
            return super()[item]
        for p in self:
            try:
                return p[item]
            except KeyError:
                pass
        raise KeyError(item)


class NOption(Option[T]):
    def __init__(self, description):
        self.description = description

    def __str__(self):
        return f'><\t{self.description}'

    def __getitem__(self, item):
        raise KeyError(item)

    def get_kind(self):
        return self.Kind.none


class InfoOption(Option[T]):
    def __init__(self, info: GameView, inline):
        self.info = info
        self.inline = inline

    def __str__(self):
        if self.inline:
            return 'I'
        return '[I]\tinfo'

    def __getitem__(self, item):
        if item == 'I':
            raise DisplayInfo(self.info)
        raise KeyError

    def get_kind(self):
        return self.Kind.info


class Choice(OptionGroup[T]):
    def __init__(self, title: str, options=(), inline=False, info: GameView = None):
        super().__init__(inline)
        self.title = title
        self.info = info

        for o in options:
            self.append(o)

    def append(self, option: Option[T]):
        list.append(self, option)

    def get_kind(self):
        raise Exception("can't get king of top-level group")

    def __str__(self):
        if self.inline:
            return self.title + ' (' + '/'.join(str(p) for p in self) + '):'
        return self.title + '\n' + textwrap.indent(super().__str__(), '\t')

    def __iter__(self):
        yield from super().__iter__()
        if self.info:
            info_group = OptionGroup(inline=self.inline)
            info_group.append(InfoOption(self.info, inline=self.inline))
            yield info_group

    def set_info(self, game, player):
        self.info = GameView(game, player)
