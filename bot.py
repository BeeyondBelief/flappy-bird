import functools
import pathlib
from collections.abc import Callable
import pygame
import neat

from bob import Bird, Game, BalloonSpawner


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
    net.run(functools.partial(_q_learning_game, game), 50)


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
    max_balloons = 5
    spawner = BalloonSpawner(max_balloons)
    game.add_spawner(spawner)
    running = True
    while running:
        if len(birds_mapping) == 0:
            break
        game.tick()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                game.stop = True
        game.update()

        balloons_posses = [0] * max_balloons * 2
        sprites = spawner.balloons.sprites()
        for i in range(0, len(sprites), 2):
            balloons_posses[i] = sprites[i].rect.x / game.width
            balloons_posses[i + 1] = sprites[i].rect.y / game.height

        for (bird, genome, net) in birds_mapping.values():
            genome.fitness += 0.1
            if net.activate((bird.rect.y, *balloons_posses))[0] > 0.5:
                bird.jump()

        remove_birds = []
        for i, (bird, genome, _) in birds_mapping.items():
            if game.bird_collide_with_any(bird):
                genome.fitness -= 1
                remove_birds.append(i)
                bird.kill()
            if bird.score_change:
                genome.fitness += 5
        for i in remove_birds:
            del birds_mapping[i]

        pygame.display.update()


if __name__ == '__main__':
    run_for_q_learning(Game(screen=pygame.display.set_mode((600, 700)), framerate=120))