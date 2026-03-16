"""Visual effects: glow, bloom, scanlines, CRT filter, particles."""

import pygame
import numpy as np
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
        r = max(1, int(self.size * t))
        color = tuple(int(c * t) for c in self.color[:3])
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), r)


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


class CRTFilter:
    """Full-screen CRT post-processing effect.

    Applies scanlines, chromatic aberration, vignette, and barrel distortion.
    Pre-computes expensive lookup tables on init for fast per-frame application.
    Toggle on/off with .enabled attribute.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.enabled = False

        # Scanline overlay (pre-rendered)
        self._scanline_overlay = self._build_scanlines(width, height,
                                                        spacing=2, alpha=40)

        # Vignette overlay (pre-rendered)
        self._vignette = self._build_vignette(width, height, strength=0.15)

        # Barrel distortion map (pre-computed)
        self._warp_map = self._build_warp_map(width, height, strength=0.02)

    @staticmethod
    def _build_scanlines(w: int, h: int, spacing: int = 2,
                         alpha: int = 40) -> pygame.Surface:
        """Pre-render scanline overlay."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(0, h, spacing):
            pygame.draw.line(surf, (0, 0, 0, alpha), (0, y), (w, y))
        return surf

    @staticmethod
    def _build_vignette(w: int, h: int, strength: float = 0.15) -> pygame.Surface:
        """Pre-render radial vignette using numpy for smooth gradient."""
        cx, cy = w / 2, h / 2
        # Build distance array normalized so corners = 1.0
        y_arr, x_arr = np.mgrid[0:h, 0:w].astype(np.float32)
        dx = (x_arr - cx) / cx
        dy = (y_arr - cy) / cy
        dist = np.sqrt(dx * dx + dy * dy)  # 0 at center, ~1.4 at corners

        # Only darken beyond 70% of the way to the corner
        fade = np.clip((dist - 0.7) / 0.7, 0.0, 1.0)
        alpha = (fade * fade * 255 * strength).astype(np.uint8)

        # Build RGBA surface
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pixels = pygame.surfarray.pixels_alpha(surf)
        # surfarray is (w, h) transposed
        pixels[:] = alpha.T
        del pixels
        # Fill RGB with black
        rgb = pygame.surfarray.pixels3d(surf)
        rgb[:] = 0
        del rgb

        return surf

    @staticmethod
    def _build_warp_map(w: int, h: int, strength: float = 0.02) -> np.ndarray:
        """Pre-compute barrel distortion pixel mapping.

        Returns array of shape (h, w, 2) with source (x, y) for each dest pixel.
        """
        # Build at half res for speed, will be used to warp a half-res copy
        hw, hh = w // 2, h // 2
        cx, cy = hw / 2, hh / 2

        y_coords, x_coords = np.mgrid[0:hh, 0:hw].astype(np.float32)
        # Normalize to -1..1
        nx = (x_coords - cx) / cx
        ny = (y_coords - cy) / cy
        r2 = nx * nx + ny * ny
        # Barrel distortion
        factor = 1.0 + strength * r2
        src_x = (nx * factor * cx + cx).clip(0, hw - 1).astype(np.int32)
        src_y = (ny * factor * cy + cy).clip(0, hh - 1).astype(np.int32)

        return np.stack([src_x, src_y], axis=-1)

    def apply(self, surface: pygame.Surface):
        """Apply CRT effect to the surface in-place."""
        if not self.enabled:
            return

        w, h = self.width, self.height

        # --- Chromatic aberration ---
        # Shift red channel right, blue channel left by 2px
        pixels = pygame.surfarray.pixels3d(surface)  # (w, h, 3) — note: transposed
        shift = 2
        # Red channel: shift right (+x)
        pixels[shift:, :, 0] = pixels[:-shift, :, 0]
        pixels[:shift, :, 0] = 0
        # Blue channel: shift left (-x)
        pixels[:-shift, :, 2] = pixels[shift:, :, 2]
        pixels[-shift:, :, 2] = 0
        del pixels  # Release surface lock

        # --- Scanlines ---
        surface.blit(self._scanline_overlay, (0, 0))

        # --- Vignette ---
        surface.blit(self._vignette, (0, 0))
