import random
from abc import ABC, abstractmethod

import pygame

# Game variables
SCREEN_WIDTH, SCREEN_HEIGHT = 600, 700
GROUND_HEIGHT = 25
CEILING_HEIGHT = 25
BALLOON_WIDTH = 100
BIRD_JUMP = 11
GRAVITY = 0.85
BALLOON_SPEED = 4
BALLOON_SPAWN_RATE = 20

# Load images
bird_img = pygame.image.load('assets/sprites/bluebird-midflap.png')
bird_upflap_img = pygame.image.load('assets/sprites/bluebird-upflap.png')
bird_downflap_img = pygame.image.load('assets/sprites/bluebird-downflap.png')
green_balloon_img = pygame.image.load('assets/sprites/balloon-green.png')
red_balloon_img = pygame.image.load('assets/sprites/balloon-red.png')
background = pygame.image.load('assets/sprites/background-night.png')
ground_image = pygame.image.load('assets/sprites/base.png')
space_image = pygame.image.load('assets/sprites/space.png')

ground_image = pygame.transform.scale(ground_image, (SCREEN_WIDTH*2, ground_image.get_height()))
space_image = pygame.transform.scale(space_image, (SCREEN_WIDTH*2, space_image.get_height()))
background = pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))



class UpdateByGame(ABC):

    @abstractmethod
    def update(self, game: 'Game') -> None: ...


class Bird(pygame.sprite.Sprite, UpdateByGame):
    def __init__(self, id: int = 0):
        super().__init__()
        self.image = bird_img
        self.rect = self.image.get_rect(center=(100, SCREEN_HEIGHT // 2))
        self.velocity = 0
        self.id = id

    def update(self, game: 'Game'):
        self.velocity += GRAVITY
        self.rect.y += self.velocity

        if self.velocity > 0:
            self.image = bird_upflap_img
        elif self.velocity == 0:
            self.image = bird_img
        else:
            self.image = bird_downflap_img

    def jump(self):
        self.velocity = -BIRD_JUMP

    def collide_with_any(self, groups: list[pygame.sprite.Group]) -> bool:
        for group in groups:
            if pygame.sprite.spritecollide(self, group, False):
                return True
        return False


class Balloon(pygame.sprite.Sprite, UpdateByGame):
    def __init__(self, position):
        super().__init__()
        self.image = green_balloon_img
        self._balloon_jitter = random.randint(1, 2)
        if BALLOON_SPEED + self._balloon_jitter > BALLOON_SPEED + 1:
            self.image = red_balloon_img
        self.rect = self.image.get_rect(midtop=position)
        scale = 0.9
        self.rect.width *= scale
        self.rect.height *= scale
        self._passed = False

    def update(self, game: 'Game'):
        self.rect.x -= BALLOON_SPEED + self._balloon_jitter
        if self.rect.right < 0:
            self.kill()

    def check_passed(self, bird: Bird) -> bool:
        if self.rect.right < bird.rect.left and not self._passed:
            self._passed = True
            return True
        return False


class Ground(pygame.sprite.Sprite):
    def __init__(self, width: float, height: float):
        super().__init__()
        self.image = pygame.Surface((width * 2, height))
        self.image.blit(ground_image, ground_image.get_rect())
        self.rect = self.image.get_rect()
        self.rect[0] = 0
        self.rect[1] = SCREEN_HEIGHT - GROUND_HEIGHT

    def update(self, game: 'Game'):
        self.rect.x -= BALLOON_SPEED
        if self.rect.right <= SCREEN_WIDTH:
            self.rect.left = 0


class Ceiling(pygame.sprite.Sprite):
    def __init__(self, width: float, height: float):
        super().__init__()
        self.image = pygame.Surface((width * 2, height))
        self.image.blit(space_image, space_image.get_rect())
        self.rect = self.image.get_rect()
        self.rect[0] = 0
        self.rect[1] = 0

    def update(self, game: 'Game'):
        self.rect.x -= BALLOON_SPEED
        if self.rect.right <= SCREEN_WIDTH:
            self.rect.left = 0


class Score(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.value = 0
        self.font = pygame.font.Font(None, 36)
        self.x = x
        self.y = y

    def increase(self):
        self.value += 1

    def update(self, game: 'Game'):
        score_text = self.font.render("Score: " + str(self.value), True, (0, 0, 0))
        game.screen.blit(score_text, (self.x - score_text.get_width() // 2, self.y))


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.grounds = pygame.sprite.Group()
        self.score = Score(SCREEN_WIDTH - 100, SCREEN_HEIGHT - 50)
        self.bird = Bird()
        self.balloons = pygame.sprite.Group()
        self.clock = pygame.time.Clock()
        self.stop = False

        self.grounds.add(
            Ground(SCREEN_WIDTH, GROUND_HEIGHT),
            Ceiling(SCREEN_WIDTH, CEILING_HEIGHT)
        )

    def bird_collide_with_any(self) -> bool:
        if self.bird.collide_with_any([self.balloons, self.grounds]):
            return True
        return False

    def update_score(self):
        for balloon in self.balloons:
            if balloon.check_passed(self.bird):
                self.score.increase()

    def update(self):
        self.screen.blit(background, background.get_rect())
        if pygame.time.get_ticks() % BALLOON_SPAWN_RATE == 0 and len(self.balloons) < 10:
            balloon_position = random.randint(10, SCREEN_HEIGHT-80)
            balloon = Balloon((SCREEN_WIDTH + BALLOON_WIDTH // 2, balloon_position))
            self.balloons.add(balloon)
        for upd in (self.bird, self.grounds, self.balloons, self.score):
            upd.update(self)
        for blt in (self.bird, *self.grounds.sprites(), *self.balloons.sprites()):
            self.screen.blit(blt.image, blt.rect)

    def reset(self):
        if self.stop:
            raise SystemExit()
        self.grounds = pygame.sprite.Group()
        self.score = Score(SCREEN_WIDTH - 100, SCREEN_HEIGHT - 50)
        self.bird = Bird()
        self.balloons = pygame.sprite.Group()
        self.clock = pygame.time.Clock()

        self.grounds.add(
            Ground(SCREEN_WIDTH, GROUND_HEIGHT),
            Ceiling(SCREEN_WIDTH, CEILING_HEIGHT)
        )


def run_once(game: 'Game', tick: int = 60):
    running = True
    while running:
        game.clock.tick(tick)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.stop = True
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game.bird.jump()
        game.update_score()
        game.update()
        if game.bird_collide_with_any():
            running = False
        pygame.display.update()


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game = Game(screen)

    while True:
        run_once(game, tick=60)
        game.reset()


if __name__ == '__main__':
    main()
