"""Shared beat timeline component drawn at the bottom of visualizers.

Shows per-layer tracks with beat markers, playhead, hit flashes, key labels, and a progress bar.
"""

import time
import pygame
from src.visuals.colors import LAYER_COLORS, CYAN, TEXT_DIM
from src.config import LAYER_KEY_LABELS


class Timeline:
    """Reusable beat timeline drawn at the bottom of the screen."""

    def __init__(self, surface: pygame.Surface, timeline_h: int = 60):
        self.surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()
        self.timeline_h = timeline_h
        self.top_y = self.height - timeline_h
        self.margin = 40

        # Pre-rendered background strip
        self._strip = pygame.Surface((self.width, self.timeline_h), pygame.SRCALPHA)
        self._strip.fill((12, 8, 20, 200))

        # Per-marker flash: {(layer, beat_idx): (time, color)}
        self.marker_flashes: dict[tuple[int, int], tuple[float, tuple]] = {}

        # Accent color for the progress bar (can be overridden per visualizer)
        self.bar_color = CYAN

        # Cached font for key labels
        self._font = pygame.font.SysFont("consolas", 11, bold=True)

    def row_y(self, layer_idx: int, total_layers: int) -> int:
        """Y position for a layer's track line."""
        if total_layers <= 1:
            return self.top_y + self.timeline_h // 2
        return self.top_y + 15 + layer_idx * (self.timeline_h - 30) // max(1, total_layers - 1)

    def flash_marker(self, layer: int, beat_idx: int, color: tuple):
        """Trigger a hit flash on a specific marker."""
        self.marker_flashes[(layer, beat_idx)] = (time.perf_counter(), color)

    def draw(self, layers: list[dict], cycle_phase: float):
        """Draw the full timeline."""
        if not layers:
            return

        now = time.perf_counter()
        margin = self.margin

        # Background
        self.surface.blit(self._strip, (0, self.top_y))
        pygame.draw.line(self.surface, (40, 20, 60),
                         (0, self.top_y), (self.width, self.top_y), 1)

        total_layers = len(layers)

        for li, layer_data in enumerate(layers):
            phases = layer_data["phases"]
            color = layer_data.get("color", LAYER_COLORS[li % len(LAYER_COLORS)])
            ry = self.row_y(li, total_layers)
            dim = tuple(c // 4 for c in color[:3])

            # Track line
            pygame.draw.line(self.surface, dim,
                             (margin, ry), (self.width - margin, ry), 2)

            # Key label on the left
            key_label = LAYER_KEY_LABELS.get(li, "")
            if key_label:
                label_surf = self._font.render(key_label, True, color)
                self.surface.blit(label_surf,
                                  (4, ry - label_surf.get_height() // 2))

            # Beat markers
            for bi, phase in enumerate(phases):
                x = margin + int(phase * (self.width - 2 * margin))
                is_accent = (bi == 0)
                draw_size = 10 if is_accent else 7

                # Check hit flash
                marker_key = (li, bi)
                flash_t = 0.0
                flash_color = color
                if marker_key in self.marker_flashes:
                    ft, fc = self.marker_flashes[marker_key]
                    age = now - ft
                    if age < 0.3:
                        flash_t = 1.0 - age / 0.3
                        flash_color = fc
                    else:
                        del self.marker_flashes[marker_key]

                if flash_t > 0:
                    draw_size += int(6 * flash_t)
                    glow_r = draw_size + 8
                    glow_color = tuple(int(c * flash_t * 0.4) for c in flash_color[:3])
                    pygame.draw.circle(self.surface, glow_color, (x, ry), glow_r)

                mc = flash_color if flash_t > 0.3 else (color if is_accent else dim)
                pygame.draw.circle(self.surface, mc, (x, ry), draw_size)

            # Playhead
            px = margin + int(cycle_phase * (self.width - 2 * margin))
            pygame.draw.circle(self.surface, (255, 255, 255), (px, ry), 6)
            pygame.draw.circle(self.surface, color, (px, ry), 3)

        # Progress bar
        bar_y = self.height - 4
        bar_w = int((self.width - 2 * margin) * cycle_phase)
        pygame.draw.rect(self.surface, self.bar_color, (margin, bar_y, bar_w, 4))
