"""Reusable speech bubble rendering and state management."""

import time
import pygame


# Shared font — initialized lazily
_bubble_font: pygame.font.Font | None = None


def _get_font() -> pygame.font.Font:
    global _bubble_font
    if _bubble_font is None:
        _bubble_font = pygame.font.SysFont("consolas", 12, bold=True)
    return _bubble_font


def draw_speech_bubble(surface: pygame.Surface, x: int, y: int,
                       text: str, age: float, duration: float = 2.0,
                       text_color: tuple = (220, 210, 190),
                       bg_color: tuple = (20, 15, 12),
                       border_color: tuple = (60, 50, 35)):
    """Draw a speech bubble with fade in/out and upward drift.

    Args:
        surface: Target surface
        x, y: Anchor position (bottom of bubble, above character head)
        text: What to say
        age: Seconds since bubble was triggered
        duration: Total bubble lifetime
        text_color: Text RGB
        bg_color: Background RGB (alpha is computed from age)
        border_color: Border RGB
    """
    if age > duration or age < 0:
        return

    # Fade: quick in, hold, fade out
    fade_in = 0.1
    fade_out = 0.4
    hold_end = duration - fade_out

    if age < fade_in:
        alpha = age / fade_in
    elif age < hold_end:
        alpha = 1.0
    else:
        alpha = max(0.0, 1.0 - (age - hold_end) / fade_out)

    if alpha <= 0:
        return

    # Drift upward
    y -= int(age * 6)

    font = _get_font()
    text_surf = font.render(text, True, text_color)
    tw, th = text_surf.get_size()
    pad_x, pad_y = 8, 4
    bw = tw + pad_x * 2
    bh = th + pad_y * 2

    bg_alpha = int(180 * alpha)

    bubble = pygame.Surface((bw, bh + 6), pygame.SRCALPHA)
    pygame.draw.rect(bubble, (*bg_color, bg_alpha),
                     (0, 0, bw, bh), border_radius=6)
    pygame.draw.rect(bubble, (*border_color, bg_alpha),
                     (0, 0, bw, bh), 1, border_radius=6)
    # Triangle pointer
    tri_x = bw // 2
    pygame.draw.polygon(bubble, (*bg_color, bg_alpha),
                        [(tri_x - 4, bh), (tri_x + 4, bh), (tri_x, bh + 5)])

    bx = x - bw // 2
    by = y - bh - 5
    surface.blit(bubble, (bx, by))

    text_surf.set_alpha(int(255 * alpha))
    surface.blit(text_surf, (bx + pad_x, by + pad_y))


class SpeechBubbleState:
    """Tracks a speech bubble's text and timing for a character."""

    def __init__(self):
        self.text = ""
        self.time = 0.0
        self.duration = 2.0

    def say(self, text: str, duration: float = 2.0):
        self.text = text
        self.time = time.perf_counter()
        self.duration = duration

    @property
    def active(self) -> bool:
        return self.text != "" and (time.perf_counter() - self.time) < self.duration

    @property
    def age(self) -> float:
        return time.perf_counter() - self.time

    def draw(self, surface: pygame.Surface, x: int, y: int, **kwargs):
        if self.active:
            draw_speech_bubble(surface, x, y, self.text, self.age,
                               self.duration, **kwargs)
