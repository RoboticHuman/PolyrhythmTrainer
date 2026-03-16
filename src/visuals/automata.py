"""Cellular automata visualizer.

1D elementary cellular automaton that scrolls upward.
A progress bar at the bottom shows cycle position with beat markers.
Each beat advances a new row. Hit accuracy colors the row and
influences the automaton rule — perfect play creates order, misses create chaos.
"""

import random
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, CYAN, MAGENTA, PURPLE,
    COLOR_PERFECT, COLOR_GOOD, COLOR_OK, COLOR_MISS
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.engine.scoring import HitRating


def apply_rule(left: int, center: int, right: int, rule: int) -> int:
    idx = (left << 2) | (center << 1) | right
    return (rule >> idx) & 1


class AutomataVisualizer(BaseVisualizer):
    """1D cellular automata that evolves with the beat."""

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()

        self.cell_size = 6
        self.cols = self.width // self.cell_size
        # Reserve bottom 60px for the beat timeline
        self.timeline_h = 60
        self.grid_h = self.height - self.timeline_h
        self.max_rows = self.grid_h // self.cell_size

        # Automata state
        self.rule = 110
        self.rows: list[list[int]] = []
        self.row_colors: list[tuple] = []
        self.row_alphas: list[float] = []

        self._seed_row()

        self._last_hit_rating = ""
        self._last_hit_color = CYAN

        # Per-marker flash: {(layer, beat_idx): (time, color)}
        self._marker_flashes: dict[tuple[int, int], tuple[float, tuple]] = {}

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

    def _rating_color(self, rating: str) -> tuple:
        return {
            HitRating.PERFECT: COLOR_PERFECT,
            HitRating.GOOD: COLOR_GOOD,
            HitRating.OK: COLOR_OK,
            HitRating.MISS: COLOR_MISS,
        }.get(rating, PURPLE)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        self._last_hit_rating = rating
        self._last_hit_color = self._rating_color(rating)

        # Accuracy influences the automaton rule
        if rating == HitRating.PERFECT:
            self.rule = random.choice([110, 90, 105, 150])
        elif rating == HitRating.GOOD:
            self.rule = random.choice([110, 30, 90])
        elif rating == HitRating.MISS:
            self.rule = random.choice([30, 45, 73, 89])

        # Inject energy into current row at a random position near center
        if self.rows:
            row = self.rows[-1]
            pos = random.randint(self.cols // 4, 3 * self.cols // 4)
            spread = max(2, int(self.cols * 0.05))
            for i in range(pos - spread, pos + spread):
                if 0 <= i < self.cols:
                    row[i] = 1

        # Flash the nearest marker on the timeline
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
            self._marker_flashes[(layer, best_bi)] = (time.perf_counter(), self._last_hit_color)

            # Particles from the marker position on the timeline
            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            total_layers = len(self.layers)
            if total_layers == 1:
                my = self.grid_h + self.timeline_h // 2
            else:
                my = self.grid_h + 15 + layer * (self.timeline_h - 30) // max(1, total_layers - 1)
            count = {HitRating.PERFECT: 14, HitRating.GOOD: 10,
                     HitRating.OK: 6, HitRating.MISS: 3}.get(rating, 5)
            self.particles.emit(mx, my, self._last_hit_color,
                                count=count, speed=120, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        color = LAYER_COLORS[layer % len(LAYER_COLORS)]
        if self._last_hit_rating:
            color = self._rating_color(self._last_hit_rating)
            self._last_hit_rating = ""
        self._advance(color)

    def _draw_automata(self):
        """Draw the automata grid, newest at bottom of grid area."""
        n_rows = len(self.rows)
        for ri in range(n_rows):
            row = self.rows[ri]
            color = self.row_colors[ri]

            # Fade: older rows dimmer
            age = n_rows - 1 - ri
            alpha = max(0.15, 1.0 - (age / max(1, self.max_rows)) * 0.7)

            # Y position: newest row at bottom of grid area
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
        """Draw a beat timeline at the bottom — big markers with glow and hit flash."""
        if not self.layers:
            return

        now = time.perf_counter()
        tl_top = self.grid_h
        tl_mid = tl_top + self.timeline_h // 2
        margin = 40

        # Background strip
        strip = pygame.Surface((self.width, self.timeline_h), pygame.SRCALPHA)
        strip.fill((12, 8, 20, 200))
        self.surface.blit(strip, (0, tl_top))

        # Separator line
        pygame.draw.line(self.surface, (40, 20, 60), (0, tl_top), (self.width, tl_top), 1)

        total_layers = len(self.layers)

        for li, layer_data in enumerate(self.layers):
            phases = layer_data["phases"]
            color = layer_data.get("color", LAYER_COLORS[li % len(LAYER_COLORS)])

            # Y position per layer within timeline
            if total_layers == 1:
                row_y = tl_mid
            else:
                row_y = tl_top + 15 + li * (self.timeline_h - 30) // max(1, total_layers - 1)

            # Track line
            dim = tuple(c // 4 for c in color[:3])
            pygame.draw.line(self.surface, dim, (margin, row_y), (self.width - margin, row_y), 2)

            # Beat markers
            for bi, phase in enumerate(phases):
                x = margin + int(phase * (self.width - 2 * margin))
                is_accent = (bi == 0)
                base_size = 10 if is_accent else 7

                # Check hit flash
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

                # Dynamic size
                draw_size = base_size
                if flash_t > 0:
                    draw_size += int(6 * flash_t)

                # Glow
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

                # Solid marker
                mc = flash_color if flash_t > 0.3 else (color if is_accent else dim)
                pygame.draw.circle(self.surface, mc, (x, row_y), draw_size)

            # Playhead on this track (bright, larger)
            px = margin + int(self.cycle_phase * (self.width - 2 * margin))
            pygame.draw.circle(self.surface, (255, 255, 255), (px, row_y), 6)
            pygame.draw.circle(self.surface, color, (px, row_y), 3)

        # Cycle progress bar at very bottom
        bar_y = self.height - 4
        bar_w = int((self.width - 2 * margin) * self.cycle_phase)
        pygame.draw.rect(self.surface, CYAN, (margin, bar_y, bar_w, 4))

    def render(self):
        self.surface.fill(BG_DARK)
        dt = self.dt

        self._draw_automata()
        self._draw_timeline()

        # Particles
        self.particles.update(dt)
        self.particles.draw(self.surface)

        # Bloom (lighter than others since automata is already busy)
        bloom = bloom_pass(self.surface, scale=8)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
