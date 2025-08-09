import math
import os
import random
import sys
from dataclasses import dataclass

# Sound support
import pygame.mixer

# Attempt to import pygame with a helpful error if missing
try:
    import pygame
except Exception as exc:  # pragma: no cover
    print("This game requires pygame. Install with: pip install -r requirements.txt", file=sys.stderr)
    raise

from sound_manager import SoundManager


# -----------------------------
# Configuration
# -----------------------------
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 360
FPS = 60
BACKGROUND_COLOR = (255, 255, 255)
FOREGROUND_COLOR = (34, 34, 34)
SKY_COLOR = (245, 245, 245)
GROUND_Y = int(WINDOW_HEIGHT * 0.78)

# Dino dimensions and physics
DINO_RUN_WIDTH = 44
DINO_RUN_HEIGHT = 47
DINO_DUCK_WIDTH = 59
DINO_DUCK_HEIGHT = 30
DINO_X = 72
JUMP_VELOCITY = -640.0  # px/sec upward
GRAVITY = 2000.0        # px/sec^2 downward

# World speed
BASE_SPEED = 360.0      # px/sec
SPEED_PER_100_SCORE = 60.0
MAX_SPEED = 780.0

# Obstacle spawn
MIN_SPAWN_GAP = 320     # px
MAX_SPAWN_GAP = 640     # px

# Pterodactyl parameters (optional airborne obstacle)
ENABLE_PTERODACTYL = True
PTERO_HEIGHTS = [GROUND_Y - 90, GROUND_Y - 140]

# Clouds
CLOUD_Y_RANGE = (40, 140)
CLOUD_SPEED = 60.0


@dataclass
class Rectangle:
    x: float
    y: float
    width: float
    height: float

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), int(self.width), int(self.height))


class Dinosaur:
    def __init__(self, sound: "SoundManager") -> None:
        self.is_jumping: bool = False
        self.is_ducking: bool = False
        self.vertical_velocity: float = 0.0
        self.run_bounds = Rectangle(DINO_X, GROUND_Y - DINO_RUN_HEIGHT, DINO_RUN_WIDTH, DINO_RUN_HEIGHT)
        self.duck_bounds = Rectangle(DINO_X, GROUND_Y - DINO_DUCK_HEIGHT, DINO_DUCK_WIDTH, DINO_DUCK_HEIGHT)
        # Animation
        self.frames = []
        self.frame_idx = 0
        self.frame_timer = 0.0
        self.frame_interval = 0.04  # seconds per frame (~25 FPS)
        self._load_frames()
        # Sound
        self.sound = sound
        self._run_sound_playing = False
        self._was_ducking = False

    def _load_frames(self):
        frames_dir = os.path.join(os.path.dirname(__file__), "dino_frames")
        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
        for fname in frame_files:
            img = pygame.image.load(os.path.join(frames_dir, fname)).convert_alpha()
            self.frames.append(img)
        if not self.frames:
            raise RuntimeError("No dino frames found in dino_frames/")

    @property
    def bounds(self) -> Rectangle:
        return self.duck_bounds if self.is_ducking and not self.is_jumping else self.run_bounds

    def start_jump(self) -> None:
        if not self.is_jumping:
            self.is_jumping = True
            self.is_ducking = False
            self.vertical_velocity = JUMP_VELOCITY
            # Play jump sound
            self.sound.play("jump")

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> None:
        # Duck only when on ground
        new_duck = bool(keys[pygame.K_DOWN]) and not self.is_jumping
        if new_duck and not self._was_ducking:
            self.sound.play("duck")
        self.is_ducking = new_duck
        self._was_ducking = self.is_ducking

        # Play running sound if on ground and not ducking or jumping
        on_ground = not self.is_jumping and not self.is_ducking
        if on_ground:
            if not self._run_sound_playing:
                self.sound.start_run_loop()
                self._run_sound_playing = True
        else:
            if self._run_sound_playing:
                self.sound.stop_run_loop()
                self._run_sound_playing = False

        # Apply jump physics
        if self.is_jumping:
            self.vertical_velocity += GRAVITY * dt
            self.run_bounds.y += self.vertical_velocity * dt
            # Ground collision
            if self.run_bounds.y >= GROUND_Y - DINO_RUN_HEIGHT:
                self.run_bounds.y = GROUND_Y - DINO_RUN_HEIGHT
                self.is_jumping = False
                self.vertical_velocity = 0.0
                self.sound.play("land")

    def draw(self, surface: pygame.Surface) -> None:
        # Animate
        self.frame_timer += 1 / FPS
        if self.frame_timer >= self.frame_interval:
            self.frame_timer = 0.0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        w, h = int(self.bounds.width), int(self.bounds.height)
        sprite = pygame.transform.smoothscale(self.frames[self.frame_idx], (w, h))

        # Draw drop shadow
        shadow = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), (w*0.08, h*0.82, w*0.85, h*0.22))
        surface.blit(shadow, (int(self.bounds.x), int(self.bounds.y) + int(h*0.12)))

        # Draw white outline (stroke)
        outline = pygame.Surface((w+6, h+6), pygame.SRCALPHA)
        outline.blit(sprite, (3, 3))
        mask = pygame.mask.from_surface(sprite)
        outline_mask = mask.outline()
        if outline_mask:
            pygame.draw.polygon(outline, (255,255,255,220), [(x+3, y+3) for x, y in outline_mask], width=5)
        surface.blit(outline, (int(self.bounds.x)-3, int(self.bounds.y)-3))

        # Draw dino sprite on top
        surface.blit(sprite, (int(self.bounds.x), int(self.bounds.y)))


class Cactus:
    def __init__(self, speed: float) -> None:
        # Randomize size similar to Chrome's small and large cacti
        kind = random.choice(["small", "large", "double", "triple"])  # adds width variance
        if kind == "small":
            width, height = 18, 36
        elif kind == "large":
            width, height = 28, 56
        elif kind == "double":
            width, height = 38, 46
        else:  # triple
            width, height = 52, 44
        self.bounds = Rectangle(WINDOW_WIDTH + 12, GROUND_Y - height, width, height)
        self.speed = speed

    def update(self, dt: float, speed: float) -> None:
        self.speed = speed
        self.bounds.x -= self.speed * dt

    def is_offscreen(self) -> bool:
        return self.bounds.x + self.bounds.width < 0

    def draw(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, FOREGROUND_COLOR, self.bounds.rect, border_radius=2)


class Pterodactyl:
    def __init__(self, speed: float) -> None:
        self.y = random.choice(PTERO_HEIGHTS)
        self.bounds = Rectangle(WINDOW_WIDTH + 12, self.y - 22, 46, 22)
        self.speed = speed * 1.05
        self.wing_timer = 0.0
        self.wing_state = 0

    def update(self, dt: float, speed: float) -> None:
        self.speed = max(speed * 1.05, BASE_SPEED)
        self.bounds.x -= self.speed * dt
        self.wing_timer += dt
        if self.wing_timer >= 0.18:
            self.wing_timer = 0.0
            self.wing_state = 1 - self.wing_state

    def is_offscreen(self) -> bool:
        return self.bounds.x + self.bounds.width < 0

    def draw(self, surface: pygame.Surface) -> None:
        # Simple flapping: draw two triangles up/down
        rect = self.bounds.rect
        body = pygame.Rect(rect.x + 8, rect.y + 6, rect.width - 16, rect.height - 12)
        pygame.draw.rect(surface, FOREGROUND_COLOR, body, border_radius=2)
        if self.wing_state == 0:
            # Wings up
            pygame.draw.polygon(surface, FOREGROUND_COLOR, [(rect.x, rect.centery), (rect.x + 14, rect.y), (rect.x + 14, rect.y + 6)])
            pygame.draw.polygon(surface, FOREGROUND_COLOR, [(rect.right, rect.centery), (rect.right - 14, rect.y), (rect.right - 14, rect.y + 6)])
        else:
            # Wings down
            pygame.draw.polygon(surface, FOREGROUND_COLOR, [(rect.x, rect.centery), (rect.x + 14, rect.bottom), (rect.x + 14, rect.bottom - 6)])
            pygame.draw.polygon(surface, FOREGROUND_COLOR, [(rect.right, rect.centery), (rect.right - 14, rect.bottom), (rect.right - 14, rect.bottom - 6)])


class Cloud:
    def __init__(self) -> None:
        y = random.randint(*CLOUD_Y_RANGE)
        width = random.randint(40, 72)
        height = random.randint(18, 26)
        self.bounds = Rectangle(WINDOW_WIDTH + random.randint(0, 280), y, width, height)
        self.speed = CLOUD_SPEED * random.uniform(0.8, 1.2)

    def update(self, dt: float) -> None:
        self.bounds.x -= self.speed * dt

    def is_offscreen(self) -> bool:
        return self.bounds.x + self.bounds.width < 0

    def draw(self, surface: pygame.Surface) -> None:
        rect = self.bounds.rect
        pygame.draw.ellipse(surface, (230, 230, 230), rect)
        pygame.draw.ellipse(surface, (220, 220, 220), rect.inflate(-8, -6))


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
        pygame.mixer.set_num_channels(8)
        pygame.display.set_caption("Dino Runner (Python)")
        self.surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 18, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 28, bold=True)
        self.sound = SoundManager()
        self.sound.start_music()
        self.reset()

    def reset(self) -> None:
        self.dino = Dinosaur(self.sound)
        self.obstacles: list[object] = []
        self.clouds: list[Cloud] = [Cloud() for _ in range(3)]
        self.spawn_distance_remaining: float = random.randint(MIN_SPAWN_GAP, MAX_SPAWN_GAP)
        self.score: int = 0
        self.high_score: int = 0
        self.game_over: bool = False
        self.time_since_game_over: float = 0.0
        self.speed: float = BASE_SPEED
        self.next_milestone: int = 100

    def compute_speed(self) -> float:
        target = min(BASE_SPEED + (self.score // 100) * SPEED_PER_100_SCORE, MAX_SPEED)
        # Ease changes slightly for smoother feel
        self.speed = self.speed + (target - self.speed) * 0.08
        return self.speed

    def spawn_obstacle(self) -> None:
        speed = self.compute_speed()
        # Weighted choice: mostly cacti, occasional pterodactyl
        spawn_roll = random.random()
        if ENABLE_PTERODACTYL and self.score > 400 and spawn_roll < 0.18:
            self.obstacles.append(Pterodactyl(speed))
        else:
            self.obstacles.append(Cactus(speed))
        self.spawn_distance_remaining = random.randint(MIN_SPAWN_GAP, MAX_SPAWN_GAP)
        self.sound.play("spawn")

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()

        if not self.game_over:
            # Input
            if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and not self.dino.is_jumping:
                self.dino.start_jump()

            # Entities
            self.dino.update(dt, keys)

            # World speed and score
            speed = self.compute_speed()
            self.score += int(60 * dt)  # roughly +60 per second
            if self.score >= self.next_milestone:
                self.sound.play("milestone")
                self.next_milestone += 100

            # Spawn logic progresses with distance
            self.spawn_distance_remaining -= speed * dt
            if self.spawn_distance_remaining <= 0:
                self.spawn_obstacle()

            # Update obstacles
            for obs in list(self.obstacles):
                if isinstance(obs, Cactus) or isinstance(obs, Pterodactyl):
                    obs.update(dt, speed)
                if isinstance(obs, Cloud):  # currently clouds are separate list
                    obs.update(dt)
            # Remove offscreen obstacles
            self.obstacles = [o for o in self.obstacles if not (hasattr(o, 'is_offscreen') and o.is_offscreen())]

            # Clouds
            for cloud in list(self.clouds):
                cloud.update(dt)
                if cloud.is_offscreen():
                    self.clouds.remove(cloud)
            # Maintain a few clouds
            while len(self.clouds) < 3:
                self.clouds.append(Cloud())

            # Collision
            dino_rect = self.dino.bounds.rect
            for obs in self.obstacles:
                if hasattr(obs, 'bounds') and dino_rect.colliderect(obs.bounds.rect):
                    self.game_over = True
                    self.time_since_game_over = 0.0
                    self.high_score = max(self.high_score, self.score)
                    self.sound.on_game_over()
                    break
        else:
            self.time_since_game_over += dt

        # Global inputs (work also when game over)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit(0)
                if self.game_over and event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_UP):
                    self.sound.play("restart")
                    self.reset()

    def draw(self) -> None:
        self.surface.fill(BACKGROUND_COLOR)

        # Sky tint
        pygame.draw.rect(self.surface, SKY_COLOR, pygame.Rect(0, 0, WINDOW_WIDTH, int(WINDOW_HEIGHT * 0.65)))

        # Clouds
        for cloud in self.clouds:
            cloud.draw(self.surface)

        # Ground line
        pygame.draw.line(self.surface, FOREGROUND_COLOR, (0, GROUND_Y), (WINDOW_WIDTH, GROUND_Y), width=2)

        # Obstacles
        for obs in self.obstacles:
            if hasattr(obs, 'draw'):
                obs.draw(self.surface)

        # Dino
        self.dino.draw(self.surface)

        # Score
        score_text = f"Score: {self.score:05d}"
        score_surf = self.font.render(score_text, True, FOREGROUND_COLOR)
        self.surface.blit(score_surf, (WINDOW_WIDTH - score_surf.get_width() - 12, 12))

        if self.high_score > 0:
            hs_text = f"HI: {self.high_score:05d}"
            hs_surf = self.font.render(hs_text, True, FOREGROUND_COLOR)
            self.surface.blit(hs_surf, (WINDOW_WIDTH - score_surf.get_width() - hs_surf.get_width() - 28, 12))

        # Game over overlay
        if self.game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 220))
            self.surface.blit(overlay, (0, 0))
            title = self.big_font.render("GAME OVER", True, FOREGROUND_COLOR)
            hint = self.font.render("Press R to Restart", True, FOREGROUND_COLOR)
            self.surface.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, WINDOW_HEIGHT // 2 - 40))
            self.surface.blit(hint, (WINDOW_WIDTH // 2 - hint.get_width() // 2, WINDOW_HEIGHT // 2 + 2))

        pygame.display.flip()

    def run(self) -> None:
        while True:
            dt_ms = self.clock.tick(FPS)
            dt = dt_ms / 1000.0
            self.update(dt)
            self.draw()


def main() -> None:
    # Hint if DISPLAY is missing (common in headless servers)
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        print("Warning: No DISPLAY detected. On headless Linux, run with: xvfb-run -s '-screen 0 1024x768x24' python dino_runner.py", file=sys.stderr)
    Game().run()


if __name__ == "__main__":
    main()