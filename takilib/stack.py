from typing import List, Set
import random

from takilib.card import Card, Color, StandardCard, \
    FlipOrderCard, StopCard, PlusCard, TwoPlusCard, TakiCard, \
    PlusThreeCard, BreakPlusThreeCard, SuperTakiCard, KingCard, ChangeColorCard


class Deck(List[Card]):
    def shuffle(self):
        random.shuffle(self)

    @classmethod
    def standard_deck(cls, shuffle=True, times=1):
        ret = cls()
        for _ in range(times):
            for color in Color:
                for sign in ('1', '3', '4', '5', '6', '7', '8', '9'):
                    ret.append(StandardCard(sign, color))
                for kind in (FlipOrderCard, StopCard, PlusCard, TwoPlusCard, TakiCard):
                    ret.append(kind(color))
            for kind in (PlusThreeCard, BreakPlusThreeCard, SuperTakiCard, KingCard, ChangeColorCard, ChangeColorCard):
                # change color appears twice
                ret.append(kind())

        if shuffle:
            ret.shuffle()
        return ret


class Hand(Set[Card]):
    pass


class Pile(List[Card]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_iter = None, None

    def append(self, card: Card):
        super().append(card)
        if card.is_iter():
            self._last_iter = (card, len(self) - 1)

    def extend(self, iterable):
        for i in iterable:
            self.append(i)

    def pop_disposable(self):
        if not self.has_iter():
            raise Exception('no colored cards were placed!')
        last_card, ind = self._last_iter
        ret = self[:ind]
        super().__delitem__(slice(0,ind))
        assert self[0] is last_card
        self._last_iter = last_card, 0
        return ret

    def has_iter(self):
        return self._last_iter[0] is not None

    def last_iter(self):
        return self._last_iter[0]

    def clear(self):
        super().clear()
        self._last_iter = None, None

    def pop(self, index: int = ...):
        raise NotImplemented

    def remove(self, object):
        raise NotImplemented

    def __delitem__(self, key):
        raise NotImplemented
