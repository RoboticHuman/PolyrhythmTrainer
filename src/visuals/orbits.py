"""Circular orbit polyrhythm visualizer.

Concentric rings with dots orbiting at the same speed (1 revolution = 1 cycle).
Each ring has different numbers of evenly-spaced beat markers.
All dots align at the downbeat (12 o'clock). A 3:4 polyrhythm has:
  - Inner ring: 3 markers (0°, 120°, 240°)
  - Outer ring: 4 markers (0°, 90°, 180°, 270°)
The dot crosses each marker = a beat for that layer.
"""

import math
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, COLOR_PERFECT, COLOR_GOOD, COLOR_OK, COLOR_MISS,
    GRID_COLOR
)
from src.visuals.effects import (
    draw_aa_circle, bloom_pass, ParticleSystem
)
from src.engine.scoring import HitRating


class OrbitsVisualizer(BaseVisualizer):
    """Concentric orbit rings — each ring = one rhythmic layer."""

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem()
        self.cx = self.width // 2
        self.cy = self.height // 2
        self.max_radius = min(self.width, self.height) * 0.38

        # Per-marker flash: {(layer, beat_idx): (start_time, color)}
        self._marker_flashes: dict[tuple[int, int], tuple[float, tuple]] = {}
        # Ring pulse from metronome beats
        self._beat_pulses: dict[int, float] = {}

    def _get_ring_radius(self, layer_idx: int, total_layers: int) -> float:
        if total_layers <= 1:
            return self.max_radius * 0.6
        min_r = self.max_radius * 0.3
        max_r = self.max_radius * 0.9
        t = layer_idx / (total_layers - 1) if total_layers > 1 else 0.5
        return min_r + t * (max_r - min_r)

    def _rating_color(self, rating: str) -> tuple:
        return {
            HitRating.PERFECT: COLOR_PERFECT,
            HitRating.GOOD: COLOR_GOOD,
            HitRating.OK: COLOR_OK,
            HitRating.MISS: COLOR_MISS,
        }.get(rating, COLOR_MISS)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = self._rating_color(rating)

        # Find nearest marker and flash it
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

            # Particles at marker position
            total = len(self.layers)
            r = self._get_ring_radius(layer, total)
            angle = phases[best_bi] * math.pi * 2 - math.pi / 2
            px = self.cx + r * math.cos(angle)
            py = self.cy + r * math.sin(angle)
            count = {HitRating.PERFECT: 12, HitRating.GOOD: 8,
                     HitRating.OK: 5, HitRating.MISS: 3}.get(rating, 5)
            self.particles.emit(px, py, color, count=count, speed=100, life=0.5)

    def on_beat(self, layer: int, beat_idx: int):
        self._beat_pulses[layer] = time.perf_counter()

    def render(self):
        self.surface.fill(BG_DARK)
        now = time.perf_counter()
        dt = self.dt
        total_layers = len(self.layers)

        if total_layers == 0:
            return

        # Center dot
        draw_aa_circle(self.surface, GRID_COLOR, (self.cx, self.cy), 4)

        for li, layer_data in enumerate(self.layers):
            beats = layer_data["beats"]
            phases = layer_data["phases"]
            color = layer_data.get("color", LAYER_COLORS[li % len(LAYER_COLORS)])
            r = self._get_ring_radius(li, total_layers)
            ring_color = color[:3]
            dim_color = tuple(c // 3 for c in ring_color)

            # Ring with subtle pulse on metronome beat
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
                bx = self.cx + r * math.cos(angle)
                by = self.cy + r * math.sin(angle)

                is_accent = (bi == 0)
                base_size = 7 if is_accent else 5

                # Check marker hit flash
                marker_key = (li, bi)
                marker_flash_t = 0.0
                marker_flash_color = color
                if marker_key in self._marker_flashes:
                    ft, fc = self._marker_flashes[marker_key]
                    age = now - ft
                    if age < 0.3:
                        marker_flash_t = 1.0 - age / 0.3
                        marker_flash_color = fc
                    else:
                        del self._marker_flashes[marker_key]

                draw_size = base_size
                if marker_flash_t > 0:
                    draw_size += int(5 * marker_flash_t)

                glow_intensity = marker_flash_t
                if glow_intensity > 0:
                    glow_r = draw_size + 10
                    glow_alpha = int(70 * glow_intensity)
                    gc = marker_flash_color if marker_flash_t > 0 else color
                    gs = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(gs, (*gc[:3], glow_alpha),
                                       (glow_r + 2, glow_r + 2), glow_r)
                    self.surface.blit(gs,
                                      (int(bx) - glow_r - 2, int(by) - glow_r - 2),
                                      special_flags=pygame.BLEND_RGB_ADD)

                # Solid marker
                mc = marker_flash_color if marker_flash_t > 0.3 else (color if is_accent else dim_color)
                draw_aa_circle(self.surface, mc, (int(bx), int(by)), draw_size)

            # Orbiting dot (playhead)
            orbit_angle = self.cycle_phase * math.pi * 2 - math.pi / 2
            ox = self.cx + r * math.cos(orbit_angle)
            oy = self.cy + r * math.sin(orbit_angle)

            # Dot glow
            glow_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*color[:3], 50), (22, 22), 20)
            pygame.draw.circle(glow_surf, (*color[:3], 90), (22, 22), 12)
            self.surface.blit(glow_surf, (int(ox) - 22, int(oy) - 22),
                              special_flags=pygame.BLEND_RGB_ADD)

            # Solid dot (white core with colored edge)
            draw_aa_circle(self.surface, color, (int(ox), int(oy)), 8)
            draw_aa_circle(self.surface, (255, 255, 255), (int(ox), int(oy)), 4)

            # Layer label near first marker (outside ring)
            if total_layers > 1:
                label_angle = phases[0] * math.pi * 2 - math.pi / 2
                lx = self.cx + (r + 20) * math.cos(label_angle)
                ly = self.cy + (r + 20) * math.sin(label_angle)
                font = pygame.font.SysFont("consolas", 13, bold=True)
                label_surf = font.render(str(beats), True, color)
                self.surface.blit(label_surf,
                                  (int(lx) - label_surf.get_width() // 2,
                                   int(ly) - label_surf.get_height() // 2))

        # Particles
        self.particles.update(dt)
        self.particles.draw(self.surface)

        # Bloom
        bloom = bloom_pass(self.surface, scale=6)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
