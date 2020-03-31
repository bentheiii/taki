from takilib import Game, Player, card, stack
import random

seed = None
if not seed:
    seed = random.randint(0, 2 ** 32)
    print(f'seed is {seed}')
random.seed(seed)

Player.single_view = True
game = Game(2)

for i in range(2):
    game.add_player()

game.setup_game()
while True:
    if not game.next_turn():
        break
