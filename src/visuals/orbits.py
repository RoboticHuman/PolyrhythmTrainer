"""Circular orbit polyrhythm visualizer.

Concentric rings with dots orbiting at the same speed (1 revolution = 1 cycle).
Each ring has different numbers of evenly-spaced beat markers.
The dot crosses each marker = a beat for that layer.
"""

import math
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, GRID_COLOR, TEXT_DIM, rating_color
)
from src.config import LAYER_KEY_LABELS
from src.visuals.effects import draw_aa_circle, bloom_pass, ParticleSystem


class OrbitsVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()
        self.cx = self.width // 2
        self.cy = self.height // 2
        self.max_radius = min(self.width, self.height) * 0.38

        self._marker_flashes: dict[tuple[int, int], tuple[float, tuple]] = {}
        self._beat_pulses: dict[int, float] = {}

        # Cached surfaces and fonts
        self._label_font = pygame.font.SysFont("consolas", 13, bold=True)
        self._dot_glow = pygame.Surface((44, 44), pygame.SRCALPHA)

    def _get_ring_radius(self, layer_idx: int, total_layers: int) -> float:
        if total_layers <= 1:
            return self.max_radius * 0.6
        min_r = self.max_radius * 0.3
        max_r = self.max_radius * 0.9
        t = layer_idx / (total_layers - 1) if total_layers > 1 else 0.5
        return min_r + t * (max_r - min_r)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = rating_color(rating)
        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self._marker_flashes[(layer, best_bi)] = (time.perf_counter(), color)

            total = len(self.layers)
            r = self._get_ring_radius(layer, total)
            angle = phases[best_bi] * math.pi * 2 - math.pi / 2
            px = self.cx + r * math.cos(angle)
            py = self.cy + r * math.sin(angle)
            self.particles.emit(px, py, color, count=10, speed=100, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        self._beat_pulses[layer] = time.perf_counter()

    def render(self):
        self.surface.fill(BG_DARK)
        now = time.perf_counter()
        dt = self.dt
        total_layers = len(self.layers)
        if total_layers == 0:
            return

        draw_aa_circle(self.surface, GRID_COLOR, (self.cx, self.cy), 4)

        for li, layer_data in enumerate(self.layers):
            beats = layer_data["beats"]
            phases = layer_data["phases"]
            color = layer_data.get("color", LAYER_COLORS[li % len(LAYER_COLORS)])
            r = self._get_ring_radius(li, total_layers)
            dim_color = tuple(c // 3 for c in color[:3])

            # Ring with beat pulse
            pulse_expand = 0
            if li in self._beat_pulses:
                age = now - self._beat_pulses[li]
                if age < 0.1:
                    pulse_expand = int(3 * (1 - age / 0.1))
            pygame.draw.circle(self.surface, dim_color,
                               (self.cx, self.cy), int(r) + pulse_expand, 1)

            # Beat markers
            for bi, phase in enumerate(phases):
                angle = phase * math.pi * 2 - math.pi / 2
                bx = int(self.cx + r * math.cos(angle))
                by = int(self.cy + r * math.sin(angle))

                accents = layer_data.get("accents", [])
                is_accent = accents[bi] if bi < len(accents) else (bi == 0)
                draw_size = 8 if is_accent else 5

                # Hit flash
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
                    draw_size += int(5 * flash_t)
                    glow_r = draw_size + 10
                    glow_alpha = int(70 * flash_t)
                    gs = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*flash_color[:3], glow_alpha),
                                       (glow_r + 2, glow_r + 2), glow_r)
                    self.surface.blit(gs, (bx - glow_r - 2, by - glow_r - 2),
                                      special_flags=pygame.BLEND_RGB_ADD)

                mc = flash_color if flash_t > 0.3 else (color if is_accent else dim_color)
                draw_aa_circle(self.surface, mc, (bx, by), draw_size)

            # Orbiting dot
            orbit_angle = self.cycle_phase * math.pi * 2 - math.pi / 2
            ox = int(self.cx + r * math.cos(orbit_angle))
            oy = int(self.cy + r * math.sin(orbit_angle))

            # Reuse glow surface
            self._dot_glow.fill((0, 0, 0, 0))
            pygame.draw.circle(self._dot_glow, (*color[:3], 50), (22, 22), 20)
            pygame.draw.circle(self._dot_glow, (*color[:3], 90), (22, 22), 12)
            self.surface.blit(self._dot_glow, (ox - 22, oy - 22),
                              special_flags=pygame.BLEND_RGB_ADD)

            draw_aa_circle(self.surface, color, (ox, oy), 8)
            draw_aa_circle(self.surface, (255, 255, 255), (ox, oy), 4)

            # Layer label with key hint
            label_angle = phases[0] * math.pi * 2 - math.pi / 2
            lx = int(self.cx + (r + 22) * math.cos(label_angle))
            ly = int(self.cy + (r + 22) * math.sin(label_angle))
            key_label = LAYER_KEY_LABELS.get(li, "")
            label_text = f"{beats} [{key_label}]" if key_label else str(beats)
            label_surf = self._label_font.render(label_text, True, color)
            self.surface.blit(label_surf,
                                  (lx - label_surf.get_width() // 2,
                                   ly - label_surf.get_height() // 2))

        self.particles.update(dt)
        self.particles.draw(self.surface)

        bloom = bloom_pass(self.surface, scale=6)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
