import neat

from bob import *

generation = 0  # note that the first generation of the birds is 0 because index starts from zero. XD
max_gen = 50  # the maximum number of generation to run
prob_threshold_to_jump = 0.8  # the probability threshold to activate the bird to jump
failed_punishment = 10  # the amount of fitness decrease after collision


class Bot:
    models = []
    genomes = []
    birds = []
    generation = 0
    max_score = -1

    def __init__(self, game: Game):
        self.game = game
        self.birds.append(game.bird)
        self.grounds = game.grounds
        self.balloons = game.balloons

    def __next__(self):
        self.generation += 1
        self.score = 0
        for genome_id, genome in self.genomes:  # for each genome
            self.birds.append(Bird(genome_id))  # create a bird and append the bird in the list
            genome.fitness = 0  # start with fitness of 0
            self.genomes.append(genome)  # append the genome in the list
            model = neat.nn.FeedForwardNetwork.create(genome, config="neatcfg.txt")
            self.models.append(model)  # append the neural network in the list

    def check_bot(self):
        if self.score >= self.max_score or len(self.birds) == 0:
            self.game.stop = True

    def on_fail(self, index):
        self.models.pop(index)
        self.genomes.pop(index)
        self.birds.pop(index)

    def train_step(self):
        for index, bird in self.birds:
            bird.update()
            dx1 = bird.rect.x