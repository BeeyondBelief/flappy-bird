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
        self.score = 0

    def update(self, game: 'Game'):
        self.velocity += GRAVITY
        self.rect.y += self.velocity

        if self.velocity > 0:
            self.image = bird_upflap_img
        elif self.velocity == 0:
            self.image = bird_img
        else:
            self.image = bird_downflap_img

        for balloon in game.balloons:
            if balloon.check_passed(self):
                self.score += 1
        game.screen.blit(self.image, self.rect)

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
        game.screen.blit(self.image, self.rect)

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
        game.screen.blit(self.image, self.rect)


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
        game.screen.blit(self.image, self.rect)


class Score(pygame.sprite.Sprite, UpdateByGame):
    def __init__(self, x, y):
        super().__init__()
        self.value = 0
        self.font = pygame.font.Font(None, 36)
        self.x = x
        self.y = y

    def increase(self) -> None:
        self.value += 1

    def update(self, game: 'Game') -> None:
        score_text = self.font.render("Score: " + str(self.value), True, (0, 0, 0))
        game.screen.blit(score_text, (self.x - score_text.get_width() // 2, self.y))


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.grounds: pygame.sprite.Group[Ground | Ceiling] = pygame.sprite.Group()
        self.balloons: pygame.sprite.Group[Balloon] = pygame.sprite.Group()
        self.clock = pygame.time.Clock()
        self.stop = False
        self.grounds.add(
            Ground(SCREEN_WIDTH, GROUND_HEIGHT),
            Ceiling(SCREEN_WIDTH, CEILING_HEIGHT)
        )
        self.updated_by_game: list[UpdateByGame] = [self.grounds, self.balloons]

    def attach_to_game(self, obj: UpdateByGame) -> None:
        self.updated_by_game.append(obj)

    def bird_collide_with_any(self, bird: Bird) -> bool:
        if bird.collide_with_any([self.balloons, self.grounds]):
            return True
        return False

    def update(self):
        self.screen.blit(background, background.get_rect())
        if pygame.time.get_ticks() % BALLOON_SPAWN_RATE == 0:
            self.spawn_balloon()
        for upd in self.updated_by_game:
            upd.update(self)

    def is_position_valid(self, new_balloon_position, existing_balloons, min_distance):
        new_x, new_y = new_balloon_position
        for balloon in existing_balloons:
            balloon_x, balloon_y = balloon.rect.centerx, balloon.rect.centery
            if (new_x - balloon_x < min_distance) and (abs(new_y - balloon_y) < min_distance):
                return False
        return True

    def spawn_balloon(self) -> None:
        if len(self.balloons) > 5:
            return
        balloon_radius = BALLOON_WIDTH // 2
        min_distance = balloon_radius * 3

        tries = 10
        while tries:
            balloon_center_x = SCREEN_WIDTH + balloon_radius
            balloon_center_y = random.randint(balloon_radius, SCREEN_HEIGHT - balloon_radius)
            new_balloon_position = (balloon_center_x, balloon_center_y)
            if self.is_position_valid(new_balloon_position, self.balloons, min_distance):
                break
            tries -= 1
        else:
            return

        # Calculate the position of the balloon
        balloon_position = (balloon_center_x, balloon_center_y)
        balloon = Balloon(balloon_position)
        self.balloons.add(balloon)

    def reset(self):
        if self.stop:
            raise SystemExit()
        self.grounds = pygame.sprite.Group()
        self.balloons = pygame.sprite.Group()
        self.clock = pygame.time.Clock()
        self.stop = False
        self.grounds.add(
            Ground(SCREEN_WIDTH, GROUND_HEIGHT),
            Ceiling(SCREEN_WIDTH, CEILING_HEIGHT)
        )
        self.updated_by_game = [self.grounds, self.balloons]


def run_once_for_player(game: 'Game', tick: int = 60):
    running = True
    score = Score(SCREEN_WIDTH - 100, SCREEN_HEIGHT - 50)
    bird = Bird()
    game.attach_to_game(bird)
    game.attach_to_game(score)
    while running:
        game.clock.tick(tick)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.stop = True
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bird.jump()
        game.update()
        score.value = bird.score
        if game.bird_collide_with_any(bird):
            running = False
        pygame.display.update()


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game = Game(screen)

    while True:
        run_once_for_player(game, tick=60)
        game.reset()


if __name__ == '__main__':
    main()
