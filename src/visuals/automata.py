"""Cellular automata visualizer.

1D elementary cellular automaton that scrolls upward.
Each beat advances a new row. Hit accuracy colors the row and
influences the automaton rule.
"""

import random
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, CYAN, PURPLE, rating_color
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.visuals.timeline import Timeline
from src.engine.scoring import HitRating


def apply_rule(left: int, center: int, right: int, rule: int) -> int:
    idx = (left << 2) | (center << 1) | right
    return (rule >> idx) & 1


class AutomataVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()

        self.cell_size = 6
        self.timeline_h = 60
        self.grid_h = self.height - self.timeline_h
        self.cols = self.width // self.cell_size
        self.max_rows = self.grid_h // self.cell_size

        self.rule = 110
        self.rows: list[list[int]] = []
        self.row_colors: list[tuple] = []
        self.row_alphas: list[float] = []

        self._seed_row()
        self._last_hit_rating = ""
        self._last_hit_color = CYAN

        self.timeline = Timeline(self.surface, self.timeline_h)

    def _seed_row(self):
        row = [0] * self.cols
        row[self.cols // 2] = 1
        for _ in range(3):
            row[random.randint(0, self.cols - 1)] = 1
        self.rows = [row]
        self.row_colors = [CYAN]
        self.row_alphas = [1.0]

    def _advance(self, color: tuple):
        if not self.rows:
            self._seed_row()
            return
        current = self.rows[-1]
        new_row = []
        for i in range(self.cols):
            left = current[(i - 1) % self.cols]
            center = current[i]
            right = current[(i + 1) % self.cols]
            new_row.append(apply_rule(left, center, right, self.rule))
        self.rows.append(new_row)
        self.row_colors.append(color)
        self.row_alphas.append(1.0)
        if len(self.rows) > self.max_rows:
            self.rows = self.rows[-self.max_rows:]
            self.row_colors = self.row_colors[-self.max_rows:]
            self.row_alphas = self.row_alphas[-self.max_rows:]

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        self._last_hit_rating = rating
        self._last_hit_color = rating_color(rating)

        if rating == HitRating.PERFECT:
            self.rule = random.choice([110, 90, 105, 150])
        elif rating == HitRating.GOOD:
            self.rule = random.choice([110, 30, 90])
        elif rating == HitRating.MISS:
            self.rule = random.choice([30, 45, 73, 89])

        if self.rows:
            row = self.rows[-1]
            pos = random.randint(self.cols // 4, 3 * self.cols // 4)
            spread = max(2, int(self.cols * 0.05))
            for i in range(pos - spread, pos + spread):
                if 0 <= i < self.cols:
                    row[i] = 1

        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self.timeline.flash_marker(layer, best_bi, self._last_hit_color)

            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self.timeline.row_y(layer, len(self.layers))
            self.particles.emit(mx, my, self._last_hit_color, count=10, speed=120, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        color = LAYER_COLORS[layer % len(LAYER_COLORS)]
        if self._last_hit_rating:
            color = rating_color(self._last_hit_rating)
            self._last_hit_rating = ""
        self._advance(color)

    def _draw_automata(self):
        n_rows = len(self.rows)
        for ri in range(n_rows):
            row = self.rows[ri]
            color = self.row_colors[ri]
            age = n_rows - 1 - ri
            alpha = max(0.15, 1.0 - (age / max(1, self.max_rows)) * 0.7)

            screen_row = self.max_rows - (n_rows - ri)
            if screen_row < 0:
                continue
            y = screen_row * self.cell_size

            for ci, cell in enumerate(row):
                if cell:
                    x = ci * self.cell_size
                    c = tuple(int(v * alpha) for v in color[:3])
                    pygame.draw.rect(self.surface, c,
                                     (x, y, self.cell_size - 1, self.cell_size - 1))

    def _draw_timeline(self):
        self.timeline.draw(self.layers, self.cycle_phase)

    def render(self):
        self.surface.fill(BG_DARK)
        self._draw_automata()
        self._draw_timeline()

        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        bloom = bloom_pass(self.surface, scale=8)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
