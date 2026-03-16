"""Visual effects: glow, bloom, scanlines, particles."""

import pygame
import math
from src.visuals.colors import BLOOM_SCALE, GLOW_ALPHA, BG_DARK


def create_glow_surface(width: int, height: int, color: tuple, radius: int,
                        intensity: int = 80) -> pygame.Surface:
    """Create a soft circular glow surface."""
    size = radius * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2

    for r in range(radius, 0, -2):
        alpha = int(intensity * (r / radius))
        c = (*color[:3], min(255, alpha))
        pygame.draw.circle(surf, c, (center, center), r)

    return surf


def bloom_pass(surface: pygame.Surface, scale: int = BLOOM_SCALE) -> pygame.Surface:
    """Simple bloom: downscale, upscale, return for additive blitting."""
    w, h = surface.get_size()
    small_w, small_h = max(1, w // scale), max(1, h // scale)

    small = pygame.transform.smoothscale(surface, (small_w, small_h))
    bloomed = pygame.transform.smoothscale(small, (w, h))
    bloomed.set_alpha(GLOW_ALPHA)
    return bloomed


def draw_scanlines(surface: pygame.Surface, spacing: int = 3, alpha: int = 30):
    """Draw CRT-style scanline overlay."""
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for y in range(0, surface.get_height(), spacing):
        pygame.draw.line(overlay, (0, 0, 0, alpha), (0, y), (surface.get_width(), y))
    surface.blit(overlay, (0, 0))


def draw_aa_circle(surface: pygame.Surface, color: tuple, center: tuple[int, int],
                   radius: int, width: int = 0):
    """Draw an anti-aliased circle using gfxdraw."""
    try:
        import pygame.gfxdraw
        x, y = int(center[0]), int(center[1])
        r = int(radius)
        if r <= 0:
            return
        if width == 0:
            pygame.gfxdraw.aacircle(surface, x, y, r, color)
            pygame.gfxdraw.filled_circle(surface, x, y, r, color)
        else:
            pygame.gfxdraw.aacircle(surface, x, y, r, color)
    except (ImportError, OverflowError, ValueError):
        pygame.draw.circle(surface, color, center, radius, width)


class Particle:
    """A simple particle for hit feedback effects."""

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: tuple, life: float = 0.5, size: float = 3.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt: float) -> bool:
        """Update particle. Returns False when dead."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.vx *= 0.97
        self.vy *= 0.97
        return self.life > 0

    def draw(self, surface: pygame.Surface):
        t = max(0, self.life / self.max_life)
        alpha = int(255 * t)
        r = max(1, int(self.size * t))
        color = (*self.color[:3], alpha)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (r, r), r)
        surface.blit(s, (int(self.x) - r, int(self.y) - r))


class ParticleSystem:
    """Manages a collection of particles."""

    def __init__(self, max_particles: int = 200):
        self.particles: list[Particle] = []
        self.max_particles = max_particles

    def emit(self, x: float, y: float, color: tuple, count: int = 8,
             speed: float = 150, life: float = 0.4, size: float = 3.0):
        """Emit particles in a burst pattern."""
        import random
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(speed * 0.3, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            p = Particle(x, y, vx, vy, color,
                         life=random.uniform(life * 0.5, life),
                         size=random.uniform(size * 0.5, size))
            self.particles.append(p)

        # Trim if over limit
        if len(self.particles) > self.max_particles:
            self.particles = self.particles[-self.max_particles:]

    def update(self, dt: float):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface: pygame.Surface):
        for p in self.particles:
            p.draw(surface)
