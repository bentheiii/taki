from abc import ABC, abstractmethod
from enum import Enum
import itertools as it
from functools import total_ordering

from takilib.gamestate import GameState
from takilib.__util__ import *


class Color(Enum):
    Red = 'r'
    Green = 'g'
    Blue = 'b'
    Yellow = 'y'

class Card(ABC):
    def can_play(self, game):
        return game.state == GameState.normal

    @abstractmethod
    def on_play(self, game, player):
        game.register_played(self, player)
        if player:
            cards_left = 'cards' if len(player.hand)>1 else 'card'
            game.msg(f'{player.name} played {self} ({len(player.hand)} {cards_left} left)', exc_players=[player])
            game.msg(f'{player.you()} played {self}', inc_players=[player])

    @abstractmethod
    def __str__(self):
        pass

    def __iter__(self):
        """
        if the card has a sign and color, yield them here, in that order, otherwise return an empty iterator
        """
        yield from ()

    def is_iter(self):
        try:
            s, c = self
        except ValueError:
            return False
        return s, c

    @abstractmethod
    def order_token(self) -> tuple:
        pass

    def __lt__(self, other: 'Card'):
        return (self.order_token(), id(self)) < (other.order_token(), id(other))

    def __le__(self, other: 'Card'):
        return (self.order_token(), id(self)) <= (other.order_token(), id(other))

    def __gt__(self, other: 'Card'):
        return (self.order_token(), id(self)) > (other.order_token(), id(other))

    def __ge__(self, other: 'Card'):
        return (self.order_token(), id(self)) >= (other.order_token(), id(other))


class ColoredCard(Card, ABC):
    def __init__(self, color: Color):
        Card.__init__(self)
        self.color = color

    def on_play(self, game, player):
        super().on_play(game, player)
        game.active_color = self.color

    def can_play(self, game):
        return Card.can_play(self, game) and game.active_color == self.color


class SignedCard(Card, ABC):
    def __init__(self, sign: str):
        Card.__init__(self)
        self.sign = sign

    def on_play(self, game, player):
        super().on_play(game, player)
        game.active_sign = self.sign

    def can_play(self, game):
        return Card.can_play(self, game) and game.active_sign == self.sign


class StandardCard(ColoredCard, SignedCard):
    def __init__(self, sign, color):
        ColoredCard.__init__(self, color)
        SignedCard.__init__(self, sign)

    def can_play(self, game):
        return ColoredCard.can_play(self, game) or SignedCard.can_play(self, game)

    def __str__(self):
        if len(self.sign) == 1:
            return self.sign + self.color.value
        return self.sign + ' ' + self.color.value

    def __iter__(self):
        yield from (self.sign, self.color)

    def order_token(self):
        return self.color.value, self.sign


class StopCard(StandardCard):
    def __init__(self, color):
        super().__init__('stop', color)

    def on_play(self, game, player):
        super().on_play(game, player)
        game.state = GameState.skip


class TwoPlusCard(StandardCard):
    def __init__(self, color):
        super().__init__('+2', color)

    def can_play(self, game):
        return super().can_play(game) or game.state == GameState.plus_two

    def on_play(self, game, player):
        super().on_play(game, player)
        if player:
            if game.state == GameState.plus_two:
                game.state = game.state+2
            else:
                assert game.state == GameState.normal
                game.state = GameState.plus_two

    def order_token(self):
        return self.color.value, 'z1+2'


class FlipOrderCard(StandardCard):
    def __init__(self, color):
        super().__init__('<=>', color)

    def on_play(self, game, player):
        super().on_play(game, player)
        if game.state != GameState.setup:
            game.order *= -1

    def order_token(self):
        return self.color.value, 'z0<=>'


class ChangeColorCard(Card):
    def __init__(self):
        super().__init__()
        self.assigned_color = None

    def on_play(self, game, player):
        super().on_play(game, player)
        self.assigned_color = game.active_color = player.choose_color()
        game.msg('color changed to ' + self.assigned_color._name_)
        game.active_sign = None

    def __str__(self):
        if self.assigned_color:
            return 'change color (to ' + self.assigned_color._name_ + ')'
        return 'change color'

    def __iter__(self):
        if self.assigned_color:
            yield from (None, self.assigned_color)
        else:
            yield from super().__iter__()

    def order_token(self):
        return 'zzz', 'z3changecolor'


def _taki(card, game, player, color):
    to_place = player.place_on_taki(color)
    if to_place:
        game.msg(f'{player.name} dropped {len(to_place)} cards: ' + ', '.join(str(c) for c in to_place))
        player.remove_cards(to_place[:-1])
        game.pile.extend(to_place[:-1])
        game.msg('closed TAKI')
        to_place[-1].on_play(game, player)
    else:
        game.msg('closed TAKI')


class TakiCard(StandardCard):
    def __init__(self, color):
        super().__init__('TAKI', color)

    def on_play(self, game, player):
        super().on_play(game, player)
        if player:
            _taki(self, game, player, self.color)

    def order_token(self):
        return self.color.value, 'z1taki'


class SuperTakiCard(SignedCard):
    def __init__(self):
        super().__init__('TAKI')
        self.assigned_color = None

    def can_play(self, game):
        return Card.can_play(self, game)

    def on_play(self, game, player):
        prev_sign = game.active_sign
        prev_color = game.active_color
        super().on_play(game, player)
        if prev_sign == 'TAKI' or prev_color is eq_to_all:
            self.assigned_color = player.choose_color()
            game.msg('color changed to ' + self.assigned_color._name_)
        else:
            self.assigned_color = game.active_color
            game.msg('SUPER TAKI is ' + self.assigned_color._name_)
        game.active_color = self.assigned_color
        _taki(self, game, player, self.assigned_color)

    def __str__(self):
        if self.assigned_color:
            return 'SUPER TAKI (' + self.assigned_color._name_ + ')'
        return 'SUPER TAKI'

    def __iter__(self):
        if self.assigned_color:
            yield from ('TAKI', self.assigned_color)
        else:
            yield from super().__iter__()

    def order_token(self):
        return 'zzz', 'z3supertaki'


class PlusCard(StandardCard):
    def __init__(self, color):
        super().__init__('+', color)

    def on_play(self, game, player):
        super().on_play(game, player)
        game.state = GameState.plus

    def order_token(self):
        return self.color.value, 'z0plus'


class KingCard(Card):
    def can_play(self, game):
        return True

    def on_play(self, game, player):
        super().on_play(game, player)
        game.active_sign = game.active_color = eq_to_all
        game.state = GameState.king

    def __str__(self):
        return 'king'

    def order_token(self):
        return 'zzz', 'z3king'


class PlusThreeCard(Card):
    def on_play(self, game, player):
        super().on_play(game, player)

        for p in it.islice(game.players_by_order(start=player), 1, None):
            breaker = p.ask_breaker()
            if breaker:
                game.msg(f'{p.name} broke the +3!')
                game.register_played(breaker, p)
                player.draw(3)
                break
        else:
            for p in it.islice(game.players_by_order(start=player), 1, None):
                p.draw(3)

        game.active_sign, game.active_color = game.last_iter_card()

    def __str__(self):
        return '+3'

    def order_token(self):
        return 'zzz', 'z3plus3'


class BreakPlusThreeCard(Card):
    def on_play(self, game, player):
        super().on_play(game, player)

        player.draw(3)

        game.active_sign, game.active_color = game.last_iter_card()

    def __str__(self):
        return '#3'

    def order_token(self):
        return 'zzz', 'z0break3'
