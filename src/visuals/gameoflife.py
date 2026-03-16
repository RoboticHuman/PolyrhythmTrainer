"""Conway's Game of Life visualizer.

A 2D Game of Life grid that advances one generation per beat.
Player hits inject live cells — perfect hits create gliders/structured patterns,
misses create random noise. The grid pulses and glows with the rhythm.
"""

import random
import time
import numpy as np
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, CYAN, PURPLE, rating_color
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.visuals.timeline import Timeline
from src.engine.scoring import HitRating

# Classic patterns to inject on good hits
GLIDER = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
LWSS = [(0, 1), (0, 3), (1, 4), (2, 0), (2, 4), (3, 1), (3, 2), (3, 3), (3, 4)]
R_PENTOMINO = [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)]
ACORN = [(0, 1), (1, 3), (2, 0), (2, 1), (2, 4), (2, 5), (2, 6)]
BLINKER = [(0, 0), (0, 1), (0, 2)]
BLOCK = [(0, 0), (0, 1), (1, 0), (1, 1)]

PATTERNS_BY_RATING = {
    HitRating.PERFECT: [GLIDER, LWSS, R_PENTOMINO, ACORN],
    HitRating.GOOD: [GLIDER, BLINKER, R_PENTOMINO],
    HitRating.OK: [BLINKER, BLOCK],
}


class GameOfLifeVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()

        self.cell_size = 6
        self.timeline_h = 60
        self.grid_h = self.height - self.timeline_h

        self.cols = self.width // self.cell_size
        self.rows = self.grid_h // self.cell_size

        # Game state
        self.grid = np.zeros((self.rows, self.cols), dtype=np.int8)
        self.age = np.zeros((self.rows, self.cols), dtype=np.int32)
        self.cell_colors = np.zeros((self.rows, self.cols, 3), dtype=np.uint8)

        self._generation = 0
        self._current_layer_color = CYAN
        self._beat_pulse_time = 0.0

        self.timeline = Timeline(self.surface, self.timeline_h)

        self._seed()

    def _seed(self):
        for _ in range(self.rows * self.cols // 8):
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            self.grid[r, c] = 1
            self.cell_colors[r, c] = CYAN

    def _step(self):
        n = np.zeros_like(self.grid)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                n += np.roll(np.roll(self.grid, dr, axis=0), dc, axis=1)

        birth = (self.grid == 0) & (n == 3)
        survive = (self.grid == 1) & ((n == 2) | (n == 3))
        new_grid = np.zeros_like(self.grid)
        new_grid[birth | survive] = 1

        self.age = np.where(survive, self.age + 1, 0)
        self.age[birth] = 1
        self.cell_colors[birth] = self._current_layer_color[:3]

        self.grid = new_grid
        self._generation += 1

    def _inject_pattern(self, pattern: list[tuple[int, int]], color: tuple):
        cr = random.randint(self.rows // 4, 3 * self.rows // 4)
        cc = random.randint(self.cols // 4, 3 * self.cols // 4)
        rot = random.randint(0, 3)
        for dr, dc in pattern:
            for _ in range(rot):
                dr, dc = dc, -dr
            r = (cr + dr) % self.rows
            c = (cc + dc) % self.cols
            self.grid[r, c] = 1
            self.age[r, c] = 1
            self.cell_colors[r, c] = color[:3]

    def _inject_noise(self, count: int, color: tuple):
        for _ in range(count):
            r = random.randint(0, self.rows - 1)
            c = random.randint(0, self.cols - 1)
            self.grid[r, c] = 1
            self.age[r, c] = 1
            self.cell_colors[r, c] = color[:3]

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = rating_color(rating)

        patterns = PATTERNS_BY_RATING.get(rating)
        if patterns:
            self._inject_pattern(random.choice(patterns), color)
            if rating == HitRating.PERFECT:
                self._inject_pattern(random.choice(patterns), color)
        else:
            self._inject_noise(15, color)

        if rating == HitRating.OK:
            self._inject_noise(5, color)

        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self.timeline.flash_marker(layer, best_bi, color)

            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self.timeline.row_y(layer, len(self.layers))
            self.particles.emit(mx, my, color, count=10, speed=120, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        self._current_layer_color = LAYER_COLORS[layer % len(LAYER_COLORS)]
        self._step()
        self._beat_pulse_time = time.perf_counter()

        if np.sum(self.grid) < (self.rows * self.cols * 0.02):
            self._inject_noise(20, self._current_layer_color)
            self._inject_pattern(random.choice(PATTERNS_BY_RATING[HitRating.PERFECT]),
                                 self._current_layer_color)

    def _draw_grid(self):
        beat_age = time.perf_counter() - self._beat_pulse_time
        pulse_boost = max(0.0, 1.0 - beat_age / 0.1) * 0.3 if beat_age < 0.1 else 0.0

        alive_r, alive_c = np.where(self.grid == 1)
        for idx in range(len(alive_r)):
            r, c = alive_r[idx], alive_c[idx]
            y = r * self.cell_size
            if y >= self.grid_h:
                continue
            x = c * self.cell_size
            age = self.age[r, c]
            base = self.cell_colors[r, c]
            b = min(1.0, max(0.3, 1.0 - (age / 80.0) * 0.6) + pulse_boost)
            pygame.draw.rect(self.surface, (min(255, int(base[0]*b)),
                                             min(255, int(base[1]*b)),
                                             min(255, int(base[2]*b))),
                             (x, y, self.cell_size - 1, self.cell_size - 1))

    def _draw_timeline(self):
        self.timeline.draw(self.layers, self.cycle_phase)

    def render(self):
        self.surface.fill(BG_DARK)
        self._draw_grid()
        self._draw_timeline()

        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        bloom = bloom_pass(self.surface, scale=8)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
