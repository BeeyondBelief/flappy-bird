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
    def __init__(self):
        self.config = self._load_config(pathlib.Path(__file__).parent / 'feedforward.conf')
        self._p = neat.Population(self.config)

    def enable_reporter(self):
        self._p.add_reporter(neat.StdOutReporter(show_species_detail=True))
        self._p.add_reporter(neat.StatisticsReporter())

    def run(self, fittness_func: Callable[[list[tuple[int, neat.DefaultGenome]]], neat.Config],
            times: int = 0):
        return self._p.run(fittness_func, times)

    @staticmethod
    def _load_config(path: pathlib.Path) -> neat.Config:
        return neat.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet,
                           neat.DefaultStagnation, path)


def run_for_q_learning(game: Game) -> None:
    net = Net()
    net.enable_reporter()
    best = net.run(functools.partial(_q_learning_game, game), None)
    with open('dump.obj', 'wb') as f:
        pickle.dump(best, f)


def _q_learning_game(game: Game, gens: list[tuple[int, neat.DefaultGenome]], config: neat.Config) -> None:
    game.reset()
    birds_mapping: dict[int, tuple[Bird, neat.DefaultGenome, neat.nn.FeedForwardNetwork]] = {}
    for genome_id, genome in gens:
        birds_mapping[genome_id] = (
            Bird((game.width * 0.2, game.height // 3)),
            genome,
            neat.nn.FeedForwardNetwork.create(genome, config)
        )
        game.attach_to_game(birds_mapping[genome_id][0])
        genome.fitness = 0
    spawner = BalloonSpawner(max_balloons_in_screen=5)
    game.add_spawner(spawner)
    while len(birds_mapping) > 0:
        game.tick()

        balloons_posses = get_balloon_coordinates(spawner)
        remove_birds = []
        for i, (bird, genome, net) in birds_mapping.items():
            genome.fitness += 0.1

            if bird.score_change:
                genome.fitness += 10

            bird_do_action_by_net(game, bird, balloons_posses, net)

            if game.bird_collide_with_any(bird):
                genome.fitness -= 1
                remove_birds.append(i)
                bird.kill()
        for i in remove_birds:
            del birds_mapping[i]
        pygame.display.update()
    random.seed(None)


def replay_with_genome(game: Game, genome: neat.DefaultGenome, config: neat.Config):
    max_balloons = 5
    spawner = BalloonSpawner(max_balloons)
    game.add_spawner(spawner)
    bird = Bird((game.width * 0.2, game.height // 3))
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    game.attach_to_game(bird)
    running = True
    while running:
        for event in game.tick():
            if event.type == pygame.QUIT:
                running = False

        balloons_posses = get_balloon_coordinates(spawner)
        bird_do_action_by_net(game, bird, balloons_posses, net)

        if game.bird_collide_with_any(bird):
            bird.kill()
            running = False
        pygame.display.update()


def bird_do_action_by_net(game: Game, bird: Bird, balloon_coordinates: list[tuple[float, float]],
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


def get_balloon_coordinates(spawner: BalloonSpawner) -> list[tuple[float, float]]:
    balloons_posses = [(-1.0, -1.0)] * spawner.max_balloons_in_screen
    sprites = spawner.balloons.sprites()
    for i in range(0, len(sprites)):
        x = abs(sprites[i].rect.x / spawner.balloon_spawn_right)
        y = abs(sprites[i].rect.y / spawner.balloon_spawn_bottom)
        balloons_posses[i] = x, y
    return balloons_posses


if __name__ == '__main__':
    game = Game(screen=pygame.display.set_mode((600, 700)), framerate=60)
    # run_for_q_learning(game)
    replay_with_genome(game, pickle.load(open(pathlib.Path(__file__).parent / 'dump.obj', 'rb')),
                       Net._load_config(pathlib.Path(__file__).parent / 'feedforward.conf'))
