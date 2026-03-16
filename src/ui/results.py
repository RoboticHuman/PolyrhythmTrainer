"""Results screen overlay shown after a challenge ends."""

import pygame
from src.engine.scoring import SessionStats, HitRating
from src.visuals.colors import (
    CYAN, MAGENTA, NEON_GREEN, YELLOW, HOT_PINK, TEXT_COLOR, TEXT_DIM
)

GRADE_COLORS = {
    "S": CYAN,
    "A": NEON_GREEN,
    "B": YELLOW,
    "C": (200, 150, 50),
    "D": HOT_PINK,
}


def calc_grade(accuracy: float) -> str:
    if accuracy >= 95:
        return "S"
    elif accuracy >= 85:
        return "A"
    elif accuracy >= 70:
        return "B"
    elif accuracy >= 50:
        return "C"
    else:
        return "D"


class ResultsScreen:
    """Full-screen results overlay after a challenge."""

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()
        self._font_huge = pygame.font.SysFont("consolas", 72, bold=True)
        self._font_large = pygame.font.SysFont("consolas", 28, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 20)
        self._font_small = pygame.font.SysFont("consolas", 14)
        self._overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

    def render(self, stats: SessionStats, preset_name: str, bpm_reached: float,
               duration: int, is_new_best: bool, unlocks: list[int]):
        """Draw the results screen overlay."""
        # Darken background
        self._overlay.fill((0, 0, 0, 180))
        self.surface.blit(self._overlay, (0, 0))

        cx = self.width // 2
        y = 80

        # Title
        title = self._font_large.render("CHALLENGE COMPLETE", True, MAGENTA)
        self.surface.blit(title, (cx - title.get_width() // 2, y))
        y += 50

        # Grade
        grade = calc_grade(stats.accuracy_pct)
        grade_color = GRADE_COLORS.get(grade, TEXT_COLOR)
        grade_surf = self._font_huge.render(grade, True, grade_color)
        self.surface.blit(grade_surf, (cx - grade_surf.get_width() // 2, y))
        y += 90

        # Preset and BPM
        info = self._font_med.render(
            f"{preset_name}  |  {bpm_reached:.0f} BPM  |  {duration}s",
            True, TEXT_COLOR
        )
        self.surface.blit(info, (cx - info.get_width() // 2, y))
        y += 40

        # Separator
        pygame.draw.line(self.surface, TEXT_DIM, (cx - 150, y), (cx + 150, y))
        y += 20

        # Stats
        stats_lines = [
            (f"Score: {stats.score}", CYAN),
            (f"Accuracy: {stats.accuracy_pct:.1f}%", grade_color),
            (f"Best Combo: {stats.best_combo}  (x{min(3.0, 1.0 + stats.best_combo // 5 * 0.1):.1f})", TEXT_COLOR),
            (f"Perfect: {stats.ratings[HitRating.PERFECT]}  Good: {stats.ratings[HitRating.GOOD]}  "
             f"OK: {stats.ratings[HitRating.OK]}  Miss: {stats.ratings[HitRating.MISS]}", TEXT_DIM),
            (f"Avg Deviation: {stats.avg_abs_deviation_ms:.1f}ms", TEXT_DIM),
        ]
        for text, color in stats_lines:
            surf = self._font_med.render(text, True, color)
            self.surface.blit(surf, (cx - surf.get_width() // 2, y))
            y += 30

        # New best banner
        if is_new_best:
            y += 10
            best_surf = self._font_large.render("NEW PERSONAL BEST!", True, YELLOW)
            self.surface.blit(best_surf, (cx - best_surf.get_width() // 2, y))
            y += 40

        # Unlock notifications
        if unlocks:
            y += 5
            for tier_num in unlocks:
                unlock_text = f"TIER {tier_num} UNLOCKED!"
                unlock_surf = self._font_large.render(unlock_text, True, NEON_GREEN)
                self.surface.blit(unlock_surf, (cx - unlock_surf.get_width() // 2, y))
                y += 35

        # Controls
        y = self.height - 60
        controls = self._font_small.render(
            "R: Retry  |  Esc: Back to Menu", True, TEXT_DIM
        )
        self.surface.blit(controls, (cx - controls.get_width() // 2, y))
