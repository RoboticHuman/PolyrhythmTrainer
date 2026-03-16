"""Synthwave grid visualizer.

Retro neon perspective grid scrolling toward the viewer.
Beat markers scroll from the horizon toward a hit zone at the bottom.
Like a rhythm game — hit when the marker reaches the line.
"""

import math
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, CYAN, MAGENTA,
    COLOR_PERFECT, COLOR_GOOD, COLOR_OK, COLOR_MISS, GRID_BRIGHT
)
from src.visuals.effects import bloom_pass, draw_scanlines, ParticleSystem
from src.engine.scoring import HitRating


class SynthwaveVisualizer(BaseVisualizer):
    """Perspective grid with beat markers scrolling toward a hit zone."""

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()

        # Perspective layout
        self.horizon_y = self.height * 0.35
        self.vanishing_x = self.width // 2
        self.ground_bottom = self.height

        # Grid scroll
        self.n_vertical_lines = 20

        # Hit zone — the line at the bottom where you should hit
        self.hit_zone_depth = 0.95

        # Per-marker flash: {(layer, beat_idx): (time, color)}
        self._marker_flashes: dict[tuple[int, int], tuple[float, tuple]] = {}

        # Sun
        self.sun_y = int(self.horizon_y - 60)
        self.sun_radius = 50

    def _rating_color(self, rating: str) -> tuple:
        return {
            HitRating.PERFECT: COLOR_PERFECT,
            HitRating.GOOD: COLOR_GOOD,
            HitRating.OK: COLOR_OK,
            HitRating.MISS: COLOR_MISS,
        }.get(rating, COLOR_MISS)

    def _project_y(self, depth: float) -> int:
        """depth 0=horizon, 1=bottom of screen."""
        t = depth ** 1.5
        return int(self.horizon_y + t * (self.ground_bottom - self.horizon_y))

    def _project_x(self, x_offset: float, depth: float) -> int:
        """x_offset in -1 to 1, depth 0-1."""
        y = self._project_y(depth)
        spread = (y - self.horizon_y) / max(1, self.ground_bottom - self.horizon_y)
        return int(self.vanishing_x + x_offset * spread * self.width * 0.8)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = self._rating_color(rating)

        # Find which beat marker is closest to the hit zone
        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = 0
            best_dist = 1.0
            for bi, phase in enumerate(phases):
                dist = abs(self.cycle_phase - phase)
                dist = min(dist, 1.0 - dist)
                if dist < best_dist:
                    best_dist = dist
                    best_bi = bi
            self._marker_flashes[(layer, best_bi)] = (time.perf_counter(), color)

        # Particles along the hit zone line
        hit_y = self._project_y(self.hit_zone_depth)
        x = self.vanishing_x
        count = {HitRating.PERFECT: 12, HitRating.GOOD: 8,
                 HitRating.OK: 4, HitRating.MISS: 2}.get(rating, 4)
        self.particles.emit(x, hit_y, color, count=count, speed=150, life=0.4, size=3)

    def on_beat(self, layer: int, beat_idx: int):
        pass

    def _draw_sky(self):
        """Gradient sky + striped sun."""
        for y in range(int(self.horizon_y)):
            t = y / max(1, self.horizon_y)
            r = int(8 + t * 20)
            g = int(4 + t * 8)
            b = int(40 + t * 30)
            pygame.draw.line(self.surface, (r, g, b), (0, y), (self.width, y))

        # Striped sun
        sun_cx = self.vanishing_x
        for i in range(self.sun_radius, 0, -1):
            t = i / self.sun_radius
            stripe = (i // 4) % 2
            if stripe and i < self.sun_radius * 0.8:
                continue
            r = int(255 * t)
            g = int(80 * t)
            b = int(180 * (1 - t))
            pygame.draw.circle(self.surface, (r, g, b), (sun_cx, self.sun_y), i)

    def _draw_grid(self):
        """Perspective grid on the ground plane."""
        n = self.n_vertical_lines
        for i in range(n + 1):
            x_offset = (i / n) * 2 - 1
            top_x = self.vanishing_x
            bot_x = self._project_x(x_offset, 1.0)
            color = GRID_BRIGHT if i == n // 2 else (40, 20, 60)
            pygame.draw.line(self.surface, color,
                             (top_x, int(self.horizon_y)), (bot_x, self.ground_bottom), 1)

        # Horizontal grid lines — scroll with cycle phase
        n_horiz = 20
        for i in range(n_horiz):
            depth = (i / n_horiz + self.cycle_phase * 0.15) % 1.0
            y = self._project_y(depth)
            if y < self.horizon_y or y > self.ground_bottom:
                continue
            brightness = int(20 + 40 * (depth ** 1.5))
            color = (brightness // 2, brightness // 4, brightness)
            left_x = self._project_x(-1.0, depth)
            right_x = self._project_x(1.0, depth)
            pygame.draw.line(self.surface, color, (left_x, y), (right_x, y), 1)

    def _draw_beat_markers(self):
        """Beat markers scroll from horizon toward the hit zone."""
        if not self.layers:
            return

        now = time.perf_counter()
        total_layers = len(self.layers)

        for li, layer_data in enumerate(self.layers):
            phases = layer_data["phases"]
            color = layer_data.get("color", LAYER_COLORS[li % len(LAYER_COLORS)])

            # Horizontal offset per layer so markers don't overlap
            if total_layers > 1:
                x_spread = 0.5
                x_center = -x_spread / 2 + (li / (total_layers - 1)) * x_spread
            else:
                x_center = 0.0

            for bi, phase in enumerate(phases):
                # Distance ahead in the cycle (0 = right on it, 1 = full cycle away)
                dist = phase - self.cycle_phase
                if dist < -0.05:
                    dist += 1.0

                # Map cycle distance to depth: 0 (just passed) → near bottom, 1 (far) → horizon
                # Beats that are about to hit are at high depth (near bottom)
                depth = 1.0 - dist
                if depth < 0.05 or depth > 1.0:
                    continue

                y = self._project_y(depth)
                if y < self.horizon_y:
                    continue

                # Width narrows per layer to separate them
                half_w = 0.3
                left_x = self._project_x(x_center - half_w, depth)
                right_x = self._project_x(x_center + half_w, depth)

                # Brightness based on proximity to hit zone
                proximity = depth
                line_color = tuple(min(255, int(c * (0.3 + 0.7 * proximity))) for c in color[:3])
                thickness = 1 + int(2 * proximity)

                pygame.draw.line(self.surface, line_color, (left_x, y), (right_x, y), thickness)

                # Check flash
                marker_key = (li, bi)
                if marker_key in self._marker_flashes:
                    ft, fc = self._marker_flashes[marker_key]
                    age = now - ft
                    if age < 0.3:
                        flash_t = 1.0 - age / 0.3
                        glow_h = int(8 * flash_t)
                        glow_alpha = int(50 * flash_t)
                        glow_surf = pygame.Surface((right_x - left_x + 20, glow_h * 2), pygame.SRCALPHA)
                        glow_surf.fill((*fc[:3], glow_alpha))
                        self.surface.blit(glow_surf, (left_x - 10, y - glow_h),
                                          special_flags=pygame.BLEND_RGB_ADD)
                    else:
                        del self._marker_flashes[marker_key]

                # Glow when very close to hit zone
                if proximity > 0.85:
                    glow_t = (proximity - 0.85) / 0.15
                    glow_alpha = int(40 * glow_t)
                    glow_surf = pygame.Surface((right_x - left_x + 20, 10), pygame.SRCALPHA)
                    glow_surf.fill((*color[:3], glow_alpha))
                    self.surface.blit(glow_surf, (left_x - 10, y - 5),
                                      special_flags=pygame.BLEND_RGB_ADD)

    def _draw_hit_zone(self):
        """The line where you should hit."""
        y = self._project_y(self.hit_zone_depth)
        left = self._project_x(-0.8, self.hit_zone_depth)
        right = self._project_x(0.8, self.hit_zone_depth)

        pulse = (math.sin(time.perf_counter() * 3) + 1) / 2
        brightness = int(150 + 60 * pulse)
        pygame.draw.line(self.surface, (brightness, brightness, brightness),
                         (left, y), (right, y), 2)

    def render(self):
        self.surface.fill(BG_DARK)
        dt = self.dt

        self._draw_sky()
        self._draw_grid()
        self._draw_beat_markers()
        self._draw_hit_zone()

        # Particles
        self.particles.update(dt)
        self.particles.draw(self.surface)

        # Scanlines
        draw_scanlines(self.surface, spacing=3, alpha=15)

        # Bloom
        bloom = bloom_pass(self.surface, scale=6)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
