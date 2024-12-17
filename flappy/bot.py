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
        self._p.add_reporter(neat.StdOutReporter(show_species_detail=False))

    def replay_with_genome(self, game: Game, genome_dump: pathlib.Path):
        spawner = self._spawn_balloon_spawner(game)
        bird = self._spawn_bird(game)
        net = neat.nn.FeedForwardNetwork.create(pickle.load(genome_dump.open('rb')), self.config)

        def on_game_tick():
            if self._is_bird_need_jump(game, bird, spawner.get_balloon_coordinates(), net):
                bird.jump()
            if game.bird_collide_with_any(bird):
                bird.kill()
                return True

        self._game_loop(game, on_game_tick)

    def run_learning(self, game: Game, dump: pathlib.Path, times: int = 100) -> None:
        each_dump = functools.partial(self._dump_each_generation, dump, 100)
        self._p.run(functools.partial(self._q_learning_game, game, each_dump), times)
        self._dump_best_genome(dump)

    def _dump_best_genome(self, dump_path: pathlib.Path) -> None:
        with open(dump_path.as_posix(), 'wb') as f:
            pickle.dump(self._p.best_genome, f)

    def _dump_each_generation(self, dump_path: pathlib.Path, generation_step: int = 100):
        if (self._p.generation+1) % generation_step == 0:
            self._dump_best_genome(dump_path)

    def _q_learning_game(self, game: Game, dump: Callable[..., None],
                         gens: list[tuple[int, neat.DefaultGenome]],
                         config: neat.Config) -> None:
        dump()
        game.reset()
        birds_mapping: dict[int, tuple[Bird, neat.DefaultGenome, neat.nn.FeedForwardNetwork]] = {
            gen_id: (
                self._spawn_bird(game),
                setattr(genome_, 'fitness', 0) or genome_,
                neat.nn.FeedForwardNetwork.create(genome_, config)
            ) for gen_id, genome_ in gens
        }
        spawner = self._spawn_balloon_spawner(game)
        random.seed(random.randint(0, 10))
        def on_game_tick():
            balloons_posses = spawner.get_balloon_coordinates()
            for key in list(birds_mapping.keys()):
                bird, genome, net = birds_mapping[key]
                genome.fitness += 0.01

                if bird.score_change:
                    genome.fitness += 10

                if self._is_bird_need_jump(game, bird, balloons_posses, net):
                    if bird.last_jump_y == bird.rect.y:
                        genome.fitness -= 2
                    bird.jump()

                if game.bird_collide_with_any(bird):
                    genome.fitness -= 5
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
    def _is_bird_need_jump(game: Game, bird: Bird,
                           balloon_coordinates: list[tuple[float, float]],
                           net: neat.nn.FeedForwardNetwork) -> bool:
        bird_x_normal = bird.rect.x / game.width
        bird_y_normal = bird.rect.y / game.height

        # # x, y, distance
        # nearest = {
        #     'above': (1.0, 0, 1.0),
        #     'below': (1.0, 1.0, 1.0),
        #     'front': (1.0, 1.0, 1.0)
        # }
        # for x, y in balloon_coordinates:
        #     if (x + bird.rect.width / game.width) < bird_x_normal:
        #         continue
        #     distance = math.sqrt((bird_y_normal - y) ** 2 + (bird_x_normal - x) ** 2)
        #     above = nearest['above']
        #     below = nearest['below']
        #     front = nearest['front']
        #     if distance > above[2] and distance > below[2] and distance > front[2]:
        #         continue
        #     if bird_y_normal > y > above[1]:
        #         nearest['above'] = (x, y, distance)
        #     elif bird_y_normal < y < below[1]:
        #         nearest['below'] = (x, y, distance)
        #     elif y + above[1] > bird_y_normal > y - below[1]:
        #         nearest['front'] = (x, y, distance)

        # input_params = (
        #     bird_y_normal,
        #     bird.velocity,
        #     bird.score,
        #     *nearest['above'],
        #     *nearest['front'],
        #     *nearest['below'],
        # )
        with_distance = []
        for x, y in balloon_coordinates:
            with_distance.extend([x, y,
                                  math.sqrt((bird_y_normal - y) ** 2 + (bird_x_normal - x) ** 2)])
        input_params = (
            bird_y_normal,
            bird.velocity,
            bird.score,
            *with_distance
        )
        if net.activate(input_params)[0] > 0.5:
            return True
        return False


def main():
    render_screen = True
    if render_screen:
        screen = pygame.display.set_mode((600, 700))
    else:
        screen = pygame.display.set_mode((600, 700), flags=pygame.HIDDEN)

    game = Game(screen=screen, framerate=60)
    net = Net(render_screen=render_screen)
    net.enable_reporter()
    dump_path = pathlib.Path('dump.obj')

    net.run_learning(game, dump_path, 1000)
    #net.replay_with_genome(game, dump_path)


if __name__ == '__main__':
    main()
