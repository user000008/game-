"""
SURVIVOR — Space Shooter
PyGame • Python 3
Controls: Arrow keys = move • Space / auto-fire = shoot • ESC = quit
"""

import pygame
import random
import sys
import math

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 800, 600
FPS = 60

BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
RED        = (220, 40, 40)
GREEN      = (40, 220, 40)
YELLOW     = (250, 240, 30)
CYAN       = (30, 240, 250)
ORANGE     = (250, 130, 30)
MAGENTA    = (240, 40, 200)

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SURVIVOR — Space Shooter")
clock = pygame.time.Clock()

# Auto-fire timer
AUTO_FIRE_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(AUTO_FIRE_EVENT, 120)  # ~8 shots/sec

# Fonts
FONT       = pygame.font.SysFont("Courier", 24)
BIG_FONT   = pygame.font.SysFont("Courier", 48, bold=True)
TITLE_FONT = pygame.font.SysFont("Courier", 72, bold=True)

# ---------------------------------------------------------------------------
# Helper: tiny synth beep (no external sound files required)
# ---------------------------------------------------------------------------
def _beep(frequency, duration=0.08, volume=0.15):
    try:
        pygame.mixer.frequency = 44100
        n = int(44100 * duration)
        buf = pygame.sndarray.make_sound(
            (pygame.numpyg.zeros((n, 2), pygame.numpyg.float32))
        )
    except Exception:
        return


_shoot_fx  = None
_explosion  = None
try:
    import numpy as np
    _shoot_fx = np.sin(2 * np.pi * 880 * np.arange(0, 0.06, 1/44100)).astype(np.float32)
    _explosion = np.random.normal(0, 0.2, (44100//4, 2)).astype(np.float32)
except Exception:
    pass

def _play_shoot():
    if _shoot_fx is not None:
        try:
            s = pygame.sndarray.make_sound(_shoot_fx)
            s.set_volume(0.12)
            s.play()
        except Exception:
            pass

def _play_explosion():
    if _explosion is not None:
        try:
            s = pygame.sndarray.make_sound(_explosion)
            s.set_volume(0.25)
            s.play()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Stars (parallax background)
# ---------------------------------------------------------------------------
class Star(pygame.sprite.Sprite):
    def __init__(self, layer=1):
        super().__init__()
        size = random.randint(1, 3) * layer
        self.image = pygame.Surface((max(1, size), max(1, size)))
        self.image.fill((min(255, 180 + layer * 20),
                         min(255, 180 + layer * 20),
                         min(255, 200 + layer * 10)))
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, WIDTH)
        self.rect.y = random.randint(-HEIGHT, 0)
        self.speed = random.uniform(0.3 * layer, 1.5 * layer)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > HEIGHT + 10:
            self.rect.x = random.randint(0, WIDTH)
            self.rect.y = random.randint(-20, -5)


# ---------------------------------------------------------------------------
# Player ship
# ---------------------------------------------------------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        size = 34
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        # sleek triangular ship
        pts = [(size//2, 2), (size-6, size-4), (size//2, size-10), (6, size-4)]
        pygame.draw.polygon(self.image, CYAN, pts, 0)
        pygame.draw.polygon(self.image, (20, 180, 200), pts, 2)
        pygame.draw.polygon(self.image, WHITE, [(size//2, 2), (size//2, size-10)], 2)
        # cockpit glow
        pygame.draw.circle(self.image, (120, 250, 255),
                           (size//2, size//2 - 2), 4)
        self.rect = self.image.get_rect()
        self.rect.centerx = WIDTH // 2
        self.rect.bottom = HEIGHT - 24
        self.speed = 6
        self.cooldown = 0

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.rect.y += self.speed

        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

        if self.cooldown > 0:
            self.cooldown -= 1

    def shoot(self):
        if self.cooldown == 0:
            bullet = Bullet(self.rect.centerx, self.rect.top)
            all_sprites.add(bullet)
            bullets.add(bullet)
            self.cooldown = 9
            _play_shoot()
            # muzzle flash particles
            for _ in range(4):
                p = Particle(
                    self.rect.centerx + random.randint(-4, 4),
                    self.rect.top,
                    random.randint(-1, 1), random.randint(-5, -2),
                    CYAN, 12
                )
                all_sprites.add(p)
                particles.add(p)


# ---------------------------------------------------------------------------
# Enemy ship
# ---------------------------------------------------------------------------
class Enemy(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        size = random.randint(22, 42)
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        color = random.choice([RED, ORANGE, YELLOW])
        # jagged alien shape
        pts = [(size//2, 0), (0, size-2), (size-3, size-8),
               (size//2, size-3), (3, size-8)]
        pygame.draw.polygon(self.image, color, pts, 0)
        pygame.draw.polygon(self.image, WHITE, pts, 2)
        eye_size = max(3, size//8)
        pygame.draw.circle(self.image, (255, 255, 120), (size//2, size//4), eye_size)
        pygame.draw.circle(self.image, BLACK, (size//2, size//4), max(1, eye_size-1))
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, WIDTH - size)
        self.rect.y = random.randint(-120, -40)
        self.speedy = random.randint(2, 6)
        self.speedx = random.randint(-2, 2)

    def update(self):
        self.rect.y += self.speedy
        self.rect.x += self.speedx
        if random.random() < 0.01:
            self.speedx = random.randint(-2, 2)
        if self.rect.top > HEIGHT + 40:
            self.rect.x = random.randint(0, WIDTH - self.rect.width)
            self.rect.y = random.randint(-120, -50)
            self.speedy = random.randint(2, 7)


# ---------------------------------------------------------------------------
# Bullet
# ---------------------------------------------------------------------------
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        w, h = 5, 14
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.line(self.image, YELLOW, (w//2, 0), (w//2, h), 2)
        pygame.draw.line(self.image, WHITE, (w//2, h-2), (w//2, h), 2)
        pygame.draw.circle(self.image, (255, 255, 200), (w//2, h//2), 2)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.bottom = y
        self.speed = -11

    def update(self):
        self.rect.y += self.speed
        if self.rect.bottom < 0:
            self.kill()


# ---------------------------------------------------------------------------
# Particle (explosions / trails)
# ---------------------------------------------------------------------------
class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy, color, life, size=4):
        super().__init__()
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        r, g, b = color
        pygame.draw.circle(self.image, (r, g, b), (size//2, size//2), size//2)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.vx = vx
        self.vy = vy
        self.life = life
        self.maxlife = life
        self.gravity = 0.08

    def update(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.vy += self.gravity
        self.life -= 1
        alpha = int(255 * self.life / self.maxlife)
        self.image.fill((*self.image.get_at((0, 0))[:3], alpha))
        if self.life <= 0 or self.rect.bottom > HEIGHT + 20:
            self.kill()


# ---------------------------------------------------------------------------
# Explosion burst helper
# ---------------------------------------------------------------------------
def burst_explosion(x, y, color, count=18, speed=6, life=28):
    for _ in range(count):
        angle = random.uniform(0, 2 * 3.14159)
        spd = random.uniform(1, speed)
        vx = mathcos(angle) * spd if 'mathcos' in globals() else spd * (random.random() - 0.5)
        vy = math.cos(angle) * spd if 'mathcos' in globals() else spd * (random.random() - 0.5)
        # simpler: use random directions
        vx = random.uniform(-speed, speed)
        vy = random.uniform(-speed, speed)
        p = Particle(x, y, vx, vy, color, life,
                     size=random.randint(2, 5))
        all_sprites.add(p)
        particles.add(p)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------
all_sprites  = pygame.sprite.Group()
bullets      = pygame.sprite.Group()
enemies      = pygame.sprite.Group()
particles    = pygame.sprite.Group()
stars        = pygame.sprite.Group()

for _ in range(120):
    stars.add(Star(layer=random.randint(1, 3)))

player = Player()
all_sprites.add(player)

# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
score       = 0
high_score  = 0
gameover    = False
intro       = True
playing     = False
wave        = 1
wave_timer  = 0
multiplier  = 1

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    # ---- events ----
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            if intro:
                intro = False
                playing = True
                continue

            if gameover:
                # restart
                gameover = False
                intro = False
                playing = True
                score = 0
                wave = 1
                multiplier = 1
                all_sprites.empty()
                bullets.empty()
                enemies.empty()
                particles.empty()
                all_sprites.add(player)
                player.rect.centerx = WIDTH // 2
                player.rect.bottom  = HEIGHT - 24
                for _ in range(120):
                    stars.add(Star(layer=random.randint(1, 3)))
                continue

            if playing:
                if event.key == pygame.K_SPACE:
                    player.shoot()

        elif event.type == AUTO_FIRE_EVENT and playing and not gameover:
            player.shoot()

    if intro:
        # ---- intro screen ----
        screen.fill(BLACK)
        # draw dim stars
        stars.update()
        stars.draw(screen)

        # title
        txt = TITLE_FONT.render("SURVIVOR", True, CYAN)
        shadow = TITLE_FONT.render("SURVIVOR", True, (0, 40, 50))
        sx = WIDTH//2 - txt.get_width()//2
        sy = 140
        screen.blit(shadow, (sx+3, sy+3))
        screen.blit(txt, (sx, sy))

        # subtitle
        st = FONT.render("SPACE SHOOTER", True, WHITE)
        screen.blit(st, (WIDTH//2 - st.get_width()//2, 200))

        # instructions panel
        panel = pygame.Surface((440, 150), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 160))
        screen.blit(panel, (WIDTH//2 - 220, 250))

        instructions = [
            ("← → ↑ ↓ / WASD", "move ship"),
            ("Space / auto-fire", "shoot"),
            ("Survive", "dodge enemy fire"),
            ("ESC", "quit"),
        ]
        for i, (key, desc) in enumerate(instructions):
            ky = FONT.render(key, True, YELLOW)
            ds = FONT.render(desc, True, (200, 200, 200))
            screen.blit(ky, (WIDTH//2 - 200, 262 + i*30))
            screen.blit(ds, (WIDTH//2 - 40, 262 + i*30))

        start_txt = BIG_FONT.render("PRESS ANY KEY", True, (120, 255, 255))
        screen.blit(start_txt, (WIDTH//2 - start_txt.get_width()//2, 440))

        # pulsing effect
        pulse = (128 + int(127 * math.sin(pygame.time.get_ticks()/200))) / 255
        screen.blit(start_txt, (WIDTH//2 - start_txt.get_width()//2,
                                440 + int(8 * math.sin(pygame.time.get_ticks()/300))))

        # version / credit
        cred = FONT.render("v2024 • built with PyGame", True, (100, 100, 100))
        screen.blit(cred, (WIDTH - cred.get_width() - 12, HEIGHT - 30))

        pygame.display.flip()
        continue

    if gameover:
        # ---- still draw background + particles while game over message builds ----
        screen.fill(BLACK)
        stars.update()
        stars.draw(screen)
        particles.update()
        particles.draw(screen)
        pygame.display.flip()
        continue

    if playing:
        # ---- spawn enemies (wave scaling) ----
        base_rate = 0.015 + wave * 0.004
        if random.random() < base_rate:
            enemy = Enemy()
            all_sprites.add(enemy)
            enemies.add(enemy)

        # ---- update ----
        all_sprites.update()
        particles.update()
        stars.update()

        # clamp bullets to top (already killed)
        # ---- collisions: bullet hits enemy ----
        hits = pygame.sprite.groupcollide(enemies, bullets, True, True)
        for hit in hits:
            base_pts = random.randint(10, 20) * multiplier
            if random.random() < 0.15:
                base_pts *= 3  # rare bonus enemy
                multiplier += 1
            score += base_pts
            _play_explosion()
            burst_explosion(hit.rect.centerx, hit.rect.centery,
                            random.choice([RED, ORANGE, YELLOW, MAGENTA]),
                            count=22, speed=7, life=30)
            wave_timer += 1
            if wave_timer > 15:
                wave += 1
                wave_timer = 0

        # ---- collisions: enemy hits player ----
        if not gameover:
            hits2 = pygame.sprite.spritecollide(player, enemies, True)
            for hit in hits2:
                gameover = True
                playing = False
                _play_explosion()
                burst_explosion(player.rect.centerx, player.rect.centery,
                                RED, count=40, speed=9, life=40)
                if score > high_score:
                    high_score = score

        # ---- drawing ----
        screen.fill(BLACK)
        stars.draw(screen)
        particles.draw(screen)
        all_sprites.draw(screen)

        # HUD
        sc_txt = FONT.render(f"SCORE  {score}", True, WHITE)
        screen.blit(sc_txt, (14, 12))

        hi_txt = FONT.render(f"HI  {high_score}", True, (150, 150, 150))
        screen.blit(hi_txt, (14, 38))

        wave_txt = FONT.render(f"WAVE {wave}", True, YELLOW)
        screen.blit(wave_txt, (WIDTH - wave_txt.get_width() - 14, 12))

        if multiplier > 1:
            mult_txt = FONT.render(f"×{multiplier}", True, CYAN)
            screen.blit(mult_txt, (WIDTH - mult_txt.get_width() - 14, 36))

        # escape hint
        eh = FONT.render("ESC = quit", True, (80, 80, 80))
        screen.blit(eh, (WIDTH - eh.get_width() - 14, HEIGHT - 22))

        pygame.display.flip()

        if gameover:
            # draw game over overlay after flip so last frame shows
            screen.fill((0, 0, 0, 180))
            go_title = BIG_FONT.render("GAME OVER", True, RED)
            screen.blit(go_title,
                        (WIDTH//2 - go_title.get_width()//2,
                         HEIGHT//2 - 80))
            go_score = FONT.render(f"SCORE: {score}", True, WHITE)
            screen.blit(go_score,
                        (WIDTH//2 - go_score.get_width()//2,
                         HEIGHT//2 - 10))
            if score >= high_score:
                new_hi = FONT.render("★ NEW HIGH SCORE ★", True, YELLOW)
                screen.blit(new_hi,
                            (WIDTH//2 - new_hi.get_width()//2,
                             HEIGHT//2 + 34))
            restart_txt = FONT.render("Press any key to restart • ESC to quit",
                                      True, (180, 180, 180))
            screen.blit(restart_txt,
                        (WIDTH//2 - restart_txt.get_width()//2,
                         HEIGHT//2 + 90))
            pygame.display.flip()

# ---------------------------------------------------------------------------
pygame.quit()
sys.exit()
