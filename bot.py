import functools
import math
import pathlib
import pickle
import random
from collections.abc import Callable

import neat
import pygame

from flappy import BalloonSpawner, Bird, Game


class Bot:
    def __init__(self, game: Game):
        self.game = game
        self.models = []
        self.genomes = []
        self.generation = 0
        self.max_score = -1
        self.birds: list[Bird] = []

    def __next__(self):
        self.generation += 1
        self.score = 0
        for genome_id, genome in self.genomes:  # for each genome
            self.birds.append(Bird(genome_id))  # create a bird and append the bird in the list
            genome.fitness = 0  # start with fitness of 0
            self.genomes.append(genome)  # append the genome in the list
            model = neat.nn.FeedForwardNetwork.create(genome, config="neatcfg.txt")
            self.models.append(model)  # append the neural network in the list


class Net:
    def __init__(self, render_screen: bool = True):
        self.config = self._load_config(pathlib.Path(__file__).parent / 'feedforward.conf')
        self.max_balloons = 5
        self.render_screen = render_screen
        self._p = neat.Population(self.config)

    def enable_reporter(self):
        self._p.add_reporter(neat.StdOutReporter(show_species_detail=True))
        self._p.add_reporter(neat.StatisticsReporter())

    def replay_with_genome(self, game: Game, genome_dump: pathlib.Path):
        spawner = self._spawn_balloon_spawner(game)
        bird = self._spawn_bird(game)
        net = neat.nn.FeedForwardNetwork.create(pickle.load(genome_dump.open('rb')), self.config)

        def on_game_tick():
            self._bird_do_action_by_net(game, bird, spawner.get_balloon_coordinates(), net)
            if game.bird_collide_with_any(bird):
                bird.kill()
                return True

        self._game_loop(game, on_game_tick)

    def run_learning(self, game: Game, dump: pathlib.Path, times: int = 100) -> None:
        best = self._p.run(functools.partial(self._q_learning_game, game), times)
        with open(dump.as_posix(), 'wb') as f:
            pickle.dump(best, f)

    def _q_learning_game(self, game: Game, gens: list[tuple[int, neat.DefaultGenome]],
                         config: neat.Config) -> None:
        game.reset()
        birds_mapping: dict[int, tuple[Bird, neat.DefaultGenome, neat.nn.FeedForwardNetwork]] = {
            gen_id: (
                self._spawn_bird(game),
                setattr(genome_, 'fitness', 0) or genome_,
                neat.nn.FeedForwardNetwork.create(genome_, config)
            ) for gen_id, genome_ in gens
        }
        spawner = self._spawn_balloon_spawner(game)

        def on_game_tick():
            balloons_posses = spawner.get_balloon_coordinates()
            for key in list(birds_mapping.keys()):
                bird, genome, net = birds_mapping[key]
                genome.fitness += 0.1

                if bird.score_change:
                    genome.fitness += 10

                self._bird_do_action_by_net(game, bird, balloons_posses, net)

                if game.bird_collide_with_any(bird):
                    genome.fitness -= 1
                    bird.kill()
                    del birds_mapping[key]
            return len(birds_mapping) == 0

        self._game_loop(game, on_game_tick)

    def _game_loop(self, game: Game, game_tick_action: Callable[[], bool]):
        running = True
        while running:
            for event in game.tick():
                if event.type == pygame.QUIT:
                    running = False

            if game_tick_action():
                running = False
            if self.render_screen:
                pygame.display.update()

    def _spawn_balloon_spawner(self, game: Game) -> BalloonSpawner:
        spawner = BalloonSpawner(max_balloons_in_screen=self.max_balloons)
        game.add_spawner(spawner)
        return spawner

    @staticmethod
    def _spawn_bird(game: Game) -> Bird:
        bird = Bird((game.width * 0.2, game.height // 3))
        game.attach_to_game(bird)
        return bird

    @staticmethod
    def _load_config(path: pathlib.Path) -> neat.Config:
        return neat.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet,
                           neat.DefaultStagnation, path)

    @staticmethod
    def _bird_do_action_by_net(game: Game, bird: Bird,
                               balloon_coordinates: list[tuple[float, float]],
                               net: neat.nn.FeedForwardNetwork) -> None:
        bird_x = bird.rect.x / game.width
        bird_y = bird.rect.y / game.height
        closest_above = float('+inf')
        closest_above_y = -1
        closest_below = float('+inf')
        closest_below_y = 1
        closest_front = float('+inf')

        closest_3_coords = [1, -1, -1, -1, 1, 1]
        for x, y in balloon_coordinates:
            if x < bird_x:
                continue
            distance = math.sqrt((bird_y - y) ** 2 + (bird_x - x) ** 2)
            if distance < closest_above and bird_y > y > closest_above_y:
                closest_above = distance
                closest_above_y = y
                closest_3_coords[0] = x
                closest_3_coords[1] = y
            elif distance < closest_below and (bird_y < y < closest_below_y):
                closest_below = distance
                closest_below_y = y
                closest_3_coords[4] = x
                closest_3_coords[5] = y
            elif distance < closest_front and y + closest_above > bird_y > y - closest_below_y:
                closest_front = distance
                closest_3_coords[2] = x
                closest_3_coords[3] = y
        if net.activate((game.height - bird_y, bird_y, bird.velocity, *closest_3_coords))[0] > 0.5:
            bird.jump()


def main():
    render_screen = False

    if render_screen:
        screen = pygame.display.set_mode((600, 700))
    else:
        screen = pygame.display.set_mode((600, 700), flags=pygame.HIDDEN)

    game = Game(screen=screen, framerate=360)
    net = Net(render_screen=render_screen)
    net.enable_reporter()
    dump_path = pathlib.Path('dump.obj')

    net.run_learning(game, dump_path)
    # net.replay_with_genome(game, dump_path)


if __name__ == '__main__':
    main()
