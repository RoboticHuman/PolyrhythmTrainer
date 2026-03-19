"""Stats HUD overlay — toggleable real-time stats display."""

import pygame
from src.engine.scoring import SessionStats, HitRating
from src.visuals.colors import (
    TEXT_COLOR, TEXT_DIM, HUD_BG,
    COLOR_PERFECT, COLOR_GOOD, COLOR_OK, COLOR_MISS, CYAN, MAGENTA,
    NEON_GREEN, HOT_PINK, rating_color
)


class HUD:
    """Heads-up display for real-time session stats."""

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.visible = True
        self.font_large = None
        self.font_small = None
        self.font_tiny = None
        self._init_fonts()

        # Last hit flash
        self._last_rating = ""
        self._last_deviation = 0.0
        self._rating_display_time = 0.0

        # Cached panel surface
        self._panel = pygame.Surface((260, 260), pygame.SRCALPHA)
        self._panel.fill(HUD_BG)

    def _init_fonts(self):
        pygame.font.init()
        self.font_large = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 18)
        self.font_tiny = pygame.font.SysFont("consolas", 14)

    def toggle(self):
        self.visible = not self.visible

    def show_hit_rating(self, rating: str, deviation_ms: float, current_time: float):
        self._last_rating = rating
        self._last_deviation = deviation_ms
        self._rating_display_time = current_time

    def _rating_color(self, rating: str) -> tuple:
        return rating_color(rating)

    def render(self, stats: SessionStats, bpm: float, rhythm_desc: str,
               current_time: float, visual_mode: str, difficulty: str = ""):
        """Render the HUD overlay."""
        # Always show the big rating popup in center
        self._draw_rating_popup(current_time)

        if not self.visible:
            return

        w = self.surface.get_width()
        margin = 16
        y = margin

        # Background panel (pre-rendered)
        panel_w = 260
        panel_h = 260
        self.surface.blit(self._panel, (margin, margin))

        x = margin + 12
        y = margin + 10

        # BPM and rhythm
        self._draw_text(f"{bpm:.0f} BPM", x, y, self.font_large, CYAN)
        y += 32
        self._draw_text(rhythm_desc, x, y, self.font_small, MAGENTA)
        y += 24

        # Separator
        pygame.draw.line(self.surface, TEXT_DIM, (x, y), (x + panel_w - 30, y))
        y += 10

        # Accuracy
        acc_color = COLOR_PERFECT if stats.accuracy_pct >= 80 else (
            COLOR_GOOD if stats.accuracy_pct >= 60 else COLOR_OK)
        self._draw_text(f"Accuracy: {stats.accuracy_pct:.1f}%", x, y,
                        self.font_small, acc_color)
        y += 22

        # Average deviation
        dev = stats.avg_abs_deviation_ms
        self._draw_text(f"Avg dev: {dev:.1f}ms", x, y, self.font_small, TEXT_COLOR)
        y += 22

        # Streak
        self._draw_text(f"Streak: {stats.streak}  (Best: {stats.best_streak})",
                        x, y, self.font_small, TEXT_COLOR)
        y += 22

        # Score and combo
        self._draw_text(f"Score: {stats.score}", x, y, self.font_small, CYAN)
        y += 22

        combo_color = COLOR_PERFECT if stats.combo >= 20 else (
            COLOR_GOOD if stats.combo >= 10 else TEXT_COLOR)
        if stats.combo > 0:
            self._draw_text(f"Combo: {stats.combo}  x{stats.combo_multiplier:.1f}",
                            x, y, self.font_small, combo_color)
        y += 22

        # Hit breakdown
        self._draw_text(
            f"P:{stats.ratings[HitRating.PERFECT]}  "
            f"G:{stats.ratings[HitRating.GOOD]}  "
            f"O:{stats.ratings[HitRating.OK]}  "
            f"M:{stats.ratings[HitRating.MISS]}",
            x, y, self.font_tiny, TEXT_DIM
        )

        # Controls hint at bottom-right
        hints = [
            "D/F: Layer 0 (L hand)",
            "J/K: Layer 1 (R hand)",
            "Space: Layer 2",
            "Tab: Toggle stats",
            "V: Cycle visuals",
            "C: CRT filter",
            "M: Mute metronome",
            "H: Hit sounds",
            "N: Difficulty",
            "+/-: BPM",
            "[/]: Presets",
            "Esc: Quit",
        ]
        hy = self.surface.get_height() - margin - len(hints) * 16
        for hint in hints:
            self._draw_text(hint, w - margin - 180, hy, self.font_tiny, TEXT_DIM)
            hy += 16

        # Visual mode + difficulty indicator
        mode_str = f"[{visual_mode}]"
        if difficulty:
            diff_color = NEON_GREEN if difficulty == "relaxed" else HOT_PINK
            mode_str += f"  [{difficulty}]"
            self._draw_text(mode_str, w - margin - 260,
                            margin + 10, self.font_small, diff_color)
        else:
            self._draw_text(mode_str, w - margin - 180,
                            margin + 10, self.font_small, TEXT_DIM)

    def _draw_rating_popup(self, current_time: float):
        """Draw big rating text in center of screen on hit."""
        if not self._last_rating:
            return

        age = current_time - self._rating_display_time
        if age > 0.6:
            return

        # Fade out
        alpha = max(0, int(255 * (1 - age / 0.6)))
        color = self._rating_color(self._last_rating)

        label = self._last_rating.upper()
        dev_str = f"{self._last_deviation:+.0f}ms"

        # Render with alpha
        text_surf = self.font_large.render(label, True, color)
        text_surf.set_alpha(alpha)

        dev_surf = self.font_small.render(dev_str, True, color)
        dev_surf.set_alpha(alpha)

        cx = self.surface.get_width() // 2
        cy = self.surface.get_height() // 2

        # Slight upward drift
        drift = int(-20 * (age / 0.6))

        self.surface.blit(text_surf,
                          (cx - text_surf.get_width() // 2, cy - 30 + drift))
        self.surface.blit(dev_surf,
                          (cx - dev_surf.get_width() // 2, cy + 5 + drift))

    def _draw_text(self, text: str, x: int, y: int,
                   font: pygame.font.Font, color: tuple):
        surf = font.render(text, True, color)
        self.surface.blit(surf, (x, y))
