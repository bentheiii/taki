from typing import List, Union

import random

from takilib.message import Message
from takilib.gamestate import GameState
from takilib.stack import Deck, Pile
from takilib.player import Player


class Game:
    def __init__(self, deck: Union[Deck, int] = 1):
        self.players: List[Player] = []
        if isinstance(deck, int):
            deck = Deck.standard_deck(times=deck)
        self.deck = deck
        self.pile = Pile()
        self.order = None
        self.state: GameState = GameState.no_game
        self.active_color = self.active_sign = ...
        self.next_player_index = None

    def add_player(self, name=..., type_=Player, **kwargs):
        assert self.state == GameState.no_game, 'can\'t add players mid-game'
        if name is ...:
            name = 'Player ' + str(len(self.players) + 1)
        player = type_(name, self, index=len(self.players), **kwargs)
        self.players.append(player)
        self.msg('new player: ' + player.name)
        return player

    def msg(self, msg, inc_players=..., exc_players=...):
        if inc_players is not ...:
            if exc_players is not ...:
                raise Exception('can\'t call msg with both players and excluded filled')
            players = inc_players
        elif exc_players is not ...:
            players = [p for p in self.players if p not in exc_players]
        else:
            players = self.players

        message = Message(msg, src=None, dst=players, kind=Message.Kind.info)
        for p in players:
            p.print(message)

    def setup_game(self, cards_per_player=8):
        assert self.state == GameState.no_game, 'a game is already in progress'
        self.state = GameState.setup
        for _ in range(cards_per_player):
            for player in self.players:
                player.draw(1)
        self.msg('all players have hands')

        if self.pile:
            self.deck.extend(self.pile)
            self.pile.clear()
        while not self.pile.has_iter():
            if not self.deck:
                raise Exception('no starter cards in the deck!')
            card = self.deck.pop()
            self.pile.append(card)
            if card.is_iter():
                self.msg('starter card: ' + str(card))
                break
            else:
                self.msg('invalid starter: ' + str(card))
        card = self.pile.last_iter()
        card.on_play(self, None)  # an iter card should function when player is None
        assert ... not in (self.active_color, self.active_sign)

        self.next_player_index = random.randint(0, len(self.players) - 1)
        self.msg('starting player ' + self.next_player.name)
        self.order = random.choice([-1, 1])
        self.msg('turn order: ' + ('normal' if self.order == 1 else 'reversed'))
        self.state = GameState.normal

    @property
    def next_player(self):
        return self.players[self.next_player_index]

    def normalize_next_ind(self, n: int = ...):
        if n is ...:
            self.next_player_index = self.normalize_next_ind(self.next_player_index)
        else:
            if n < 0:
                n += len(self.players)
            if n >= 0:
                n -= len(self.players)
            return n

    def register_played(self, card, player: Player):
        assert (self.state == GameState.setup) == (player is None)
        if player:
            player.hand.remove(card)
        self.pile.append(card)

    def last_iter_card(self):
        return self.pile.last_iter()

    def players_by_order(self, start: Player):
        yield start
        i = start.index
        while True:
            i = self.normalize_next_ind(i + self.order)
            p = self.players[i]
            if p == start:
                break
            yield p

    def next_turn(self):
        if self.state == GameState.normal or self.state == GameState.plus_two:
            selection = self.next_player.pick_card(self)
            if selection is None:
                amount = 1
                if self.state == GameState.plus_two:
                    amount = self.state.stake
                self.next_player.draw(amount)
                self.state = GameState.normal
            else:
                selection.on_play(self, self.next_player)
        elif self.state == GameState.skip:
            self.msg(self.next_player.name + ' skipped')
            self.state = GameState.normal
        else:
            raise Exception('invalid state ' + repr(self.state))

        if self.state != GameState.plus and self.state != GameState.plus_two:
            winners = []
            for p in self.players:
                if not p.hand:
                    winners.append(p)
            if len(winners) == 1:
                self.msg('Winner: ' + winners[0].name)
                return False
            if winners:
                self.msg('Tie between: ' + ', '.join(w.name for w in winners))
                return False

        if self.state != GameState.plus and self.state != GameState.king:
            self.next_player_index += self.order
            self.normalize_next_ind()
        else:
            self.state = GameState.normal
        return True

    def draw(self):
        if not self.deck:
            self.msg('reloading deck')
            new_cards = self.pile.pop_disposable()
            self.deck.extend(new_cards)
            self.deck.shuffle()
        return self.deck.pop()
