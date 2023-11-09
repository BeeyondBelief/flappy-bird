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


class UpdateSpriteGame(pygame.sprite.Sprite, UpdateByGame, ABC):
    pass


class UpdateGroupByGame(pygame.sprite.Group, UpdateByGame):
    def add(self, *sprites: UpdateSpriteGame) -> None:
        super().add(*sprites)

    def update(self, game: 'Game') -> None:
        super().update(game)


class Bird(UpdateSpriteGame):
    def __init__(self, position: tuple[float, float]):
        super().__init__()
        self.image = bird_img
        self.rect = self.image.get_rect(center=position)
        self.velocity = 0
        self.score = 0
        self.score_change = 0

    def update(self, game: 'Game'):
        self.velocity += GRAVITY
        self.rect.y += self.velocity

        if self.velocity > 0:
            self.image = bird_upflap_img
        elif self.velocity == 0:
            self.image = bird_img
        else:
            self.image = bird_downflap_img

        self.score_change = game.bird_fly_balloons_count_diff(self)
        self.score += self.score_change
        game.screen.blit(self.image, self.rect)

    def jump(self):
        self.velocity = -BIRD_JUMP

    def collide_with_any(self, groups: list[pygame.sprite.Group]) -> bool:
        for group in groups:
            if pygame.sprite.spritecollide(self, group, False):
                return True
        return False


class Balloon(UpdateSpriteGame):
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


class Ground(UpdateSpriteGame):
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


class Ceiling(UpdateSpriteGame):
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


class Score(UpdateSpriteGame):
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


class BalloonSpawner(UpdateByGame):
    def __init__(self, max_balloons_in_screen: int):
        self.balloons = UpdateGroupByGame()
        self.max_balloons_in_screen = max_balloons_in_screen
        self.balloon_radius = BALLOON_WIDTH // 2
        self.balloon_spawn_right = SCREEN_WIDTH + self.balloon_radius
        self.balloon_spawn_top = CEILING_HEIGHT + self.balloon_radius
        self.balloon_spawn_bottom = SCREEN_HEIGHT - GROUND_HEIGHT - self.balloon_radius

    @property
    def group(self) -> pygame.sprite.Group:
        return self.balloons

    def bird_fly_balloons_diff(self, bird: Bird) -> int:
        count = 0
        for b in self.balloons:
            if b.check_passed(bird):
                count += 1
        return count

    def update(self, game: 'Game') -> None:
        self.balloons.update(game)
        if (pygame.time.get_ticks() % BALLOON_SPAWN_RATE == 0
                and len(self.balloons) < self.max_balloons_in_screen):
            self.spawn_balloon()

    def spawn_balloon(self) -> None:
        min_distance = self.balloon_radius * 3

        tries = 10
        while tries:
            balloon_center_y = random.randint(self.balloon_spawn_top, self.balloon_spawn_bottom)
            new_balloon_position = (self.balloon_spawn_right, balloon_center_y)
            if self._is_balloon_radius_free(new_balloon_position, min_distance):
                break
            tries -= 1
        else:
            return
        self.balloons.add(Balloon((self.balloon_spawn_right, balloon_center_y)))

    def _is_balloon_radius_free(self, new_balloon_position: tuple[int, int], free_radius: float):
        new_x, new_y = new_balloon_position
        for balloon in self.balloons:
            balloon_x, balloon_y = balloon.rect.centerx, balloon.rect.centery
            if (new_x - balloon_x < free_radius) and (abs(new_y - balloon_y) < free_radius):
                return False
        return True


class Game:
    def __init__(self, screen: pygame.surface.Surface, framerate: float):
        self.screen = screen
        self.framerate = framerate
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.grounds = UpdateGroupByGame()
        self.clock = pygame.time.Clock()
        self.exit = False
        self.grounds.add(
            Ground(SCREEN_WIDTH, GROUND_HEIGHT),
            Ceiling(SCREEN_WIDTH, CEILING_HEIGHT)
        )
        self.updated_by_game: list[UpdateByGame] = [self.grounds]
        self.spawners: list[BalloonSpawner] = []

    def tick(self) -> list[pygame.event.Event]:
        self.clock.tick(self.framerate)
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.exit = True
        self.update()
        return events

    def attach_to_game(self, obj: UpdateByGame) -> None:
        self.updated_by_game.append(obj)

    def add_spawner(self, spawner: BalloonSpawner):
        self.spawners.append(spawner)
        self.attach_to_game(spawner)

    def bird_collide_with_any(self, bird: Bird) -> bool:
        if bird.collide_with_any([self.grounds, *[x.group for x in self.spawners]]):
            return True
        return False

    def bird_fly_balloons_count_diff(self, bird: Bird) -> int:
        count = 0
        for spawner in self.spawners:
            count += spawner.bird_fly_balloons_diff(bird)
        return count

    def update(self):
        self.screen.blit(background, background.get_rect())
        for upd in self.updated_by_game:
            upd.update(self)

    def reset(self):
        if self.exit:
            raise SystemExit()
        self.exit = False
        self.updated_by_game: list[UpdateByGame] = [self.grounds]
        self.spawners = []


def run_once_for_player(game: 'Game'):
    running = True
    score = Score(SCREEN_WIDTH * 0.85, SCREEN_HEIGHT - GROUND_HEIGHT * 2)
    bird = Bird((SCREEN_WIDTH * 0.2, SCREEN_HEIGHT // 3))
    game.add_spawner(BalloonSpawner(5))
    game.attach_to_game(bird)
    game.attach_to_game(score)
    while running:
        for event in game.tick():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bird.jump()
        score.value = bird.score
        if game.bird_collide_with_any(bird):
            bird.kill()
            running = False
        pygame.display.update()


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game = Game(screen, framerate=60)

    while True:
        run_once_for_player(game)
        game.reset()


if __name__ == '__main__':
    main()
