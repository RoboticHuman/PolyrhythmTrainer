"""Conway's Game of Life visualizer.

A 2D Game of Life grid that advances one generation per beat.
Player hits inject live cells — perfect hits create gliders/structured patterns,
misses create random noise. The grid pulses and glows with the rhythm.
"""

import math
import random
import time
import numpy as np
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, CYAN, MAGENTA, PURPLE,
    COLOR_PERFECT, COLOR_GOOD, COLOR_OK, COLOR_MISS
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.engine.scoring import HitRating


# Classic patterns to inject on good hits
GLIDER = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
LWSS = [(0, 1), (0, 3), (1, 4), (2, 0), (2, 4), (3, 1), (3, 2), (3, 3), (3, 4)]
R_PENTOMINO = [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]
ACORN = [(0, 1), (1, 3), (2, 0), (2, 1), (2, 4), (2, 5), (2, 6)]
BLINKER = [(0, 0), (0, 1), (0, 2)]
BLOCK = [(0, 0), (0, 1), (1, 0), (1, 1)]

PERFECT_PATTERNS = [GLIDER, LWSS, R_PENTOMINO, ACORN]
GOOD_PATTERNS = [GLIDER, BLINKER, R_PENTOMINO]
OK_PATTERNS = [BLINKER, BLOCK]


class GameOfLifeVisualizer(BaseVisualizer):
    """2D Game of Life that evolves with the beat."""

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()

        self.cell_size = 6
        # Reserve bottom for timeline
        self.timeline_h = 60
        self.grid_h = self.height - self.timeline_h

        self.cols = self.width // self.cell_size
        self.rows = self.grid_h // self.cell_size

        # Game state — use numpy for fast generation stepping
        self.grid = np.zeros((self.rows, self.cols), dtype=np.int8)
        # Age grid — tracks how long each cell has been alive (for color)
        self.age = np.zeros((self.rows, self.cols), dtype=np.int32)
        # Color per cell — set when cell is born
        self.cell_colors = np.zeros((self.rows, self.cols, 3), dtype=np.uint8)

        self._generation = 0
        self._current_layer_color = CYAN

        # Seed with some initial life
        self._seed()

        # Beat pulse effect
        self._beat_pulse = 0.0
        self._beat_pulse_time = 0.0

        # Per-marker flash for timeline
        self._marker_flashes: dict[tuple[int, int], tuple[float, tuple]] = {}

    def _seed(self):
        """Scatter some initial random cells."""
        for _ in range(self.rows * self.cols // 8):
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            self.grid[r, c] = 1
            self.cell_colors[r, c] = CYAN

    def _step(self):
        """Advance one Game of Life generation."""
        # Count neighbors using numpy roll
        n = np.zeros_like(self.grid)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                n += np.roll(np.roll(self.grid, dr, axis=0), dc, axis=1)

        # Rules: birth on 3 neighbors, survive on 2-3
        birth = (self.grid == 0) & (n == 3)
        survive = (self.grid == 1) & ((n == 2) | (n == 3))
        new_grid = np.zeros_like(self.grid)
        new_grid[birth | survive] = 1

        # Update age: increment for surviving, reset for new births
        new_age = np.where(survive, self.age + 1, 0)
        new_age[birth] = 1

        # Color new births with current layer color
        color = self._current_layer_color
        self.cell_colors[birth] = color[:3]

        self.grid = new_grid
        self.age = new_age
        self._generation += 1

    def _inject_pattern(self, pattern: list[tuple[int, int]], color: tuple,
                        center_r: int | None = None, center_c: int | None = None):
        """Inject a pattern into the grid at a position."""
        if center_r is None:
            center_r = random.randint(self.rows // 4, 3 * self.rows // 4)
        if center_c is None:
            center_c = random.randint(self.cols // 4, 3 * self.cols // 4)

        # Random rotation (0, 90, 180, 270)
        rot = random.randint(0, 3)
        for dr, dc in pattern:
            for _ in range(rot):
                dr, dc = dc, -dr
            r = (center_r + dr) % self.rows
            c = (center_c + dc) % self.cols
            self.grid[r, c] = 1
            self.age[r, c] = 1
            self.cell_colors[r, c] = color[:3]

    def _inject_noise(self, count: int, color: tuple):
        """Inject random scattered cells."""
        for _ in range(count):
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            self.grid[r, c] = 1
            self.age[r, c] = 1
            self.cell_colors[r, c] = color[:3]

    def _rating_color(self, rating: str) -> tuple:
        return {
            HitRating.PERFECT: COLOR_PERFECT,
            HitRating.GOOD: COLOR_GOOD,
            HitRating.OK: COLOR_OK,
            HitRating.MISS: COLOR_MISS,
        }.get(rating, PURPLE)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = self._rating_color(rating)

        # Inject patterns based on accuracy
        if rating == HitRating.PERFECT:
            pattern = random.choice(PERFECT_PATTERNS)
            self._inject_pattern(pattern, color)
            self._inject_pattern(random.choice(PERFECT_PATTERNS), color)
        elif rating == HitRating.GOOD:
            self._inject_pattern(random.choice(GOOD_PATTERNS), color)
        elif rating == HitRating.OK:
            self._inject_pattern(random.choice(OK_PATTERNS), color)
            self._inject_noise(5, color)
        else:
            self._inject_noise(15, color)

        # Timeline marker flash
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

            # Particles from timeline
            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            total_layers = len(self.layers)
            if total_layers == 1:
                my = self.grid_h + self.timeline_h // 2
            else:
                my = self.grid_h + 15 + layer * (self.timeline_h - 30) // max(1, total_layers - 1)
            count = {HitRating.PERFECT: 14, HitRating.GOOD: 10,
                     HitRating.OK: 6, HitRating.MISS: 3}.get(rating, 5)
            self.particles.emit(mx, my, color, count=count, speed=120, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        self._current_layer_color = LAYER_COLORS[layer % len(LAYER_COLORS)]
        self._step()
        self._beat_pulse_time = time.perf_counter()

        # If grid is getting sparse, add some life
        alive = np.sum(self.grid)
        if alive < (self.rows * self.cols * 0.02):
            self._inject_noise(20, self._current_layer_color)
            self._inject_pattern(random.choice(PERFECT_PATTERNS), self._current_layer_color)

    def _draw_grid(self):
        """Draw the Game of Life grid."""
        now = time.perf_counter()

        # Beat pulse — briefly brighten everything
        beat_age = now - self._beat_pulse_time
        pulse_boost = max(0.0, 1.0 - beat_age / 0.1) * 0.3 if beat_age < 0.1 else 0.0

        # Find all alive cells and draw them
        alive_r, alive_c = np.where(self.grid == 1)

        for idx in range(len(alive_r)):
            r = alive_r[idx]
            c = alive_c[idx]
            x = c * self.cell_size
            y = r * self.cell_size

            if y >= self.grid_h:
                continue

            # Color fades with age
            age = self.age[r, c]
            base_color = self.cell_colors[r, c]
            brightness = max(0.3, 1.0 - (age / 80.0) * 0.6) + pulse_boost
            brightness = min(1.0, brightness)

            cr = min(255, int(base_color[0] * brightness))
            cg = min(255, int(base_color[1] * brightness))
            cb = min(255, int(base_color[2] * brightness))

            pygame.draw.rect(self.surface, (cr, cg, cb),
                             (x, y, self.cell_size - 1, self.cell_size - 1))

    def _draw_timeline(self):
        """Beat timeline at the bottom with big markers."""
        if not self.layers:
            return

        now = time.perf_counter()
        tl_top = self.grid_h
        tl_mid = tl_top + self.timeline_h // 2
        margin = 40

        # Background
        strip = pygame.Surface((self.width, self.timeline_h), pygame.SRCALPHA)
        strip.fill((12, 8, 20, 200))
        self.surface.blit(strip, (0, tl_top))
        pygame.draw.line(self.surface, (40, 20, 60), (0, tl_top), (self.width, tl_top), 1)

        total_layers = len(self.layers)

        for li, layer_data in enumerate(self.layers):
            phases = layer_data["phases"]
            color = layer_data.get("color", LAYER_COLORS[li % len(LAYER_COLORS)])

            if total_layers == 1:
                row_y = tl_mid
            else:
                row_y = tl_top + 15 + li * (self.timeline_h - 30) // max(1, total_layers - 1)

            # Track line
            dim = tuple(c // 4 for c in color[:3])
            pygame.draw.line(self.surface, dim, (margin, row_y), (self.width - margin, row_y), 2)

            # Markers
            for bi, phase in enumerate(phases):
                x = margin + int(phase * (self.width - 2 * margin))
                is_accent = (bi == 0)
                base_size = 10 if is_accent else 7

                marker_key = (li, bi)
                flash_t = 0.0
                flash_color = color
                if marker_key in self._marker_flashes:
                    ft, fc = self._marker_flashes[marker_key]
                    age = now - ft
                    if age < 0.3:
                        flash_t = 1.0 - age / 0.3
                        flash_color = fc
                    else:
                        del self._marker_flashes[marker_key]

                draw_size = base_size
                if flash_t > 0:
                    draw_size += int(6 * flash_t)

                glow_intensity = flash_t
                if glow_intensity > 0:
                    glow_r = draw_size + 14
                    glow_alpha = int(80 * glow_intensity)
                    gc = flash_color if flash_t > 0 else color
                    gs = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*gc[:3], glow_alpha),
                                       (glow_r + 2, glow_r + 2), glow_r)
                    self.surface.blit(gs, (x - glow_r - 2, row_y - glow_r - 2),
                                      special_flags=pygame.BLEND_RGB_ADD)

                mc = flash_color if flash_t > 0.3 else (color if is_accent else dim)
                pygame.draw.circle(self.surface, mc, (x, row_y), draw_size)

            # Playhead
            px = margin + int(self.cycle_phase * (self.width - 2 * margin))
            pygame.draw.circle(self.surface, (255, 255, 255), (px, row_y), 6)
            pygame.draw.circle(self.surface, color, (px, row_y), 3)

        # Progress bar
        bar_y = self.height - 4
        bar_w = int((self.width - 2 * margin) * self.cycle_phase)
        pygame.draw.rect(self.surface, CYAN, (margin, bar_y, bar_w, 4))

    def render(self):
        self.surface.fill(BG_DARK)
        dt = self.dt

        self._draw_grid()
        self._draw_timeline()

        # Particles
        self.particles.update(dt)
        self.particles.draw(self.surface)

        # Bloom
        bloom = bloom_pass(self.surface, scale=8)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
