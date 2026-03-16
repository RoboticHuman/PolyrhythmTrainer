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

        self._marker_flashes: dict[tuple[int, int], tuple[float, tuple]] = {}

        # Cached timeline background
        self._timeline_strip = pygame.Surface((self.width, self.timeline_h), pygame.SRCALPHA)
        self._timeline_strip.fill((12, 8, 20, 200))

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
            self._marker_flashes[(layer, best_bi)] = (time.perf_counter(), self._last_hit_color)

            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self._timeline_row_y(layer)
            self.particles.emit(mx, my, self._last_hit_color, count=10, speed=120, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        color = LAYER_COLORS[layer % len(LAYER_COLORS)]
        if self._last_hit_rating:
            color = rating_color(self._last_hit_rating)
            self._last_hit_rating = ""
        self._advance(color)

    def _timeline_row_y(self, layer_idx: int) -> int:
        tl_top = self.grid_h
        total = len(self.layers)
        if total <= 1:
            return tl_top + self.timeline_h // 2
        return tl_top + 15 + layer_idx * (self.timeline_h - 30) // max(1, total - 1)

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
        if not self.layers:
            return

        now = time.perf_counter()
        tl_top = self.grid_h
        margin = 40

        self.surface.blit(self._timeline_strip, (0, tl_top))
        pygame.draw.line(self.surface, (40, 20, 60), (0, tl_top), (self.width, tl_top), 1)

        for li, layer_data in enumerate(self.layers):
            phases = layer_data["phases"]
            color = layer_data.get("color", LAYER_COLORS[li % len(LAYER_COLORS)])
            row_y = self._timeline_row_y(li)
            dim = tuple(c // 4 for c in color[:3])

            pygame.draw.line(self.surface, dim, (margin, row_y), (self.width - margin, row_y), 2)

            for bi, phase in enumerate(phases):
                x = margin + int(phase * (self.width - 2 * margin))
                is_accent = (bi == 0)
                draw_size = 10 if is_accent else 7

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

                if flash_t > 0:
                    draw_size += int(6 * flash_t)
                    glow_r = draw_size + 14
                    glow_alpha = int(80 * flash_t)
                    gs = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*flash_color[:3], glow_alpha),
                                       (glow_r + 2, glow_r + 2), glow_r)
                    self.surface.blit(gs, (x - glow_r - 2, row_y - glow_r - 2),
                                      special_flags=pygame.BLEND_RGB_ADD)

                mc = flash_color if flash_t > 0.3 else (color if is_accent else dim)
                pygame.draw.circle(self.surface, mc, (x, row_y), draw_size)

            px = margin + int(self.cycle_phase * (self.width - 2 * margin))
            pygame.draw.circle(self.surface, (255, 255, 255), (px, row_y), 6)
            pygame.draw.circle(self.surface, color, (px, row_y), 3)

        bar_y = self.height - 4
        bar_w = int((self.width - 2 * margin) * self.cycle_phase)
        pygame.draw.rect(self.surface, CYAN, (margin, bar_y, bar_w, 4))

    def render(self):
        self.surface.fill(BG_DARK)
        self._draw_automata()
        self._draw_timeline()

        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        bloom = bloom_pass(self.surface, scale=8)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
