from typing import Iterable, Union

from functools import partial

from takilib.card import Card, Color, BreakPlusThreeCard
from takilib.stack import Hand
from takilib.choice import Choice, StandardOption, OptionGroup, NOption, Option, T, AskAgain, DisplayInfo
from takilib.message import Message

print_ = print
input_ = input

color_choice = Choice('Choose a color',
                      [StandardOption(c.value, '', c) for c in Color], inline=True)

use_breaker_choice_creator = partial(Choice, options=[StandardOption(['y', ''], '', True, kind=Option.Kind.regular),
                                                      StandardOption('n', '', False, kind=Option.Kind.regular)],
                                     inline=True)

confirm_choice_creator = partial(Choice, options=[StandardOption(['y', ''], '', True, kind=Option.Kind.confirm),
                                                  StandardOption('n', '', False, kind=Option.Kind.undo)],
                                 inline=True)


class Player:
    single_view = False
    msg_cache = None

    def print(self, message: Union[Message, str], **kwargs):
        if isinstance(message, str):
            message = Message(message, src=self, dst=(self,), **kwargs)

        if self.single_view and len(message.dst) > 1:
            if Player.msg_cache == message:
                return
            else:
                Player.msg_cache = message
        msg = message.msg
        if message.kind == Message.Kind.choice:
            assert len(message.dst) == 1, 'a choice should only have one recipient'
            if self.single_view:
                msg = self.name + ': ' + msg
        print_(msg)

    def input(self, choice: Choice[T], info=False) -> T:
        if info:
            choice.set_info(self.game, self)
        self.print(str(choice), kind=Message.Kind.choice)
        while True:
            response = input_('' if choice.inline else 'enter input:')
            try:
                return choice[response]
            except KeyError:
                self.print('bad input, enter again:', kind=Message.Kind.bad_input)
            except AskAgain:
                pass
            except DisplayInfo as di:
                self.print(str(di.info), kind=Message.Kind.info)

    def __init__(self, name, game, index: int, first_person=False):
        self.name = name
        self.game = game
        self.first_person = first_person
        self.index = index
        self.hand = Hand()

    def you(self, capital=True):
        if self.first_person:
            return 'You' if capital else 'you'
        return self.name

    def confirm(self, prompt):
        choice = confirm_choice_creator(prompt)
        return self.input(choice)

    def choose_color(self) -> Color:
        return self.input(color_choice, info=True)

    def place_on_taki(self, color: Color) -> Iterable[Card]:
        placeables = []
        rest = []
        for c in sorted(self.hand):
            if getattr(c, 'color', 'no color') in (color, 'no color'):
                placeables.append(c)
            else:
                rest.append(c)

        if not placeables:
            return []
        ret = []
        while placeables:
            choice = Choice('place cards for a ' + color._name_ + ' taki'
                            + (('(currently placing ' + ', '.join(str(c) for c in ret) + '):') if ret else ':'))
            placeable_option_group = OptionGroup()
            # todo rework this whole order (make it look like like pick_card)
            for i, card in enumerate(placeables):
                placeable_option_group.append(StandardOption(str(i), str(card), [card]))
            choice.append(placeable_option_group)
            if len(placeables) > 1:
                convenience_group = OptionGroup()
                convenience_group.append(ExcludeByIndOption('^', placeables, Option.Kind.convenience))
                convenience_group.append(StandardOption('A', 'all', placeables[:], kind=Option.Kind.convenience,
                                                        case_sensitive=True))
                choice.append(convenience_group)
            end_group = OptionGroup()
            end_group.append(ConfirmationOption.maybe(placeables, '', 'end taki', None, player=self))
            choice.append(end_group)
            if ret:
                choice.append(StandardOption('B', 'undo last', 'undo', kind=Option.Kind.undo,
                                             case_sensitive=True))  # todo singleton instead of 'undo'?

            noptions_group = OptionGroup()
            for card in rest:
                noptions_group.append(NOption(str(card)))
            choice.append(noptions_group)

            response = self.input(choice, info=True)
            if not response:
                break
            elif response == 'undo':
                c = ret.pop()
                placeables.append(c)
                placeables.sort()
            else:
                ret.extend(response)
                for r in response:  # todo is this too inefficient for A and ^?
                    placeables.remove(r)

        return ret

    def remove_card(self, card):
        self.hand.remove(card)

    def remove_cards(self, cards):
        for c in cards:
            self.remove_card(c)

    def draw(self, num=1):
        for _ in range(num):
            card = self.game.draw()
            self.hand.add(card)
            self.print(f'{self.you()} drew {card}', kind=Message.Kind.info)

        if num == 1:
            card_num = 'a card'
        else:
            card_num = str(num) + ' cards'
        self.game.msg(f'{self.name} drew {card_num}', exc_players=[self])

    def ask_breaker(self):
        candidate = next((c for c in self.hand if isinstance(c, BreakPlusThreeCard)), None)
        choice = use_breaker_choice_creator(f'{self.you()} have a +3 breaker, play it?')
        if candidate and self.input(choice, info=True):
            return candidate
        return None

    def pick_card(self, game):
        against = str(game.pile[-1])
        if not game.pile[-1].is_iter():
            against += ' [' + str(game.pile.last_iter()) + ']'
        choice = Choice(f'play a card (against {against}) [enter nothing to draw]:')
        cards_group = OptionGroup()
        cards_choice_ind = 0
        for card in sorted(self.hand):
            if card.can_play(game):
                cards_group.append(StandardOption(str(cards_choice_ind), str(card), card))
                cards_choice_ind += 1
            else:
                cards_group.append(NOption(str(card)))
        choice.append(cards_group)
        choice.append(ConfirmationOption.maybe(cards_choice_ind != 0, '', 'draw a card', None, player=self))
        return self.input(choice, info=True)


class ConfirmationOption(StandardOption):
    def __init__(self, *args, player: Player, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = player

    def __getitem__(self, item):
        ret = super().__getitem__(item)
        if not self.player.confirm(self.description):
            raise AskAgain
        return ret

    @classmethod
    def maybe(cls, predicate, *args, player, **kwargs):
        if predicate:
            return cls(*args, player=player, **kwargs)
        return StandardOption(*args, **kwargs)


class ExcludeByIndOption(Option[list]):
    def __init__(self, prefix: str, master_sequence: list, kind: Option.Kind):
        self.prefix = prefix
        self.master_sequence = master_sequence
        self.kind = kind

    def __str__(self):
        return f'[{self.prefix}X]\tall except X'

    def __getitem__(self, item: str):
        if not item.startswith(self.prefix):
            raise KeyError
        item = item[len(self.prefix):]
        try:
            item = int(item)
        except ValueError as e:
            raise KeyError from e
        if not 0 <= item < len(self.master_sequence):
            raise KeyError
        ret = self.master_sequence[:]
        ret.pop(item)
        return ret

    def get_kind(self):
        return self.kind


# for highlighting purposes
print: None
input: None
