"""Hit feedback sounds — distinct audio cues for each accuracy rating."""

import numpy as np
import pygame
from src.engine.scoring import HitRating


def _generate_tone(freq: float, duration_ms: int, volume: float,
                   decay: float = 40, harmonics: list[tuple[float, float]] | None = None,
                   sample_rate: int = 44100) -> pygame.mixer.Sound:
    """Generate a tone with optional harmonics."""
    n = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n, dtype=np.float32)
    wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * decay) * volume
    if harmonics:
        for h_freq, h_vol in harmonics:
            wave += np.sin(2 * np.pi * h_freq * t) * np.exp(-t * decay * 1.2) * h_vol

    # Fade-in (1ms) to avoid pop
    attack = max(1, int(sample_rate * 0.001))
    wave[:attack] *= np.linspace(0, 1, attack, dtype=np.float32)

    # Fade-out (1ms) to avoid end click
    release = max(1, int(sample_rate * 0.001))
    wave[-release:] *= np.linspace(1, 0, release, dtype=np.float32)

    samples = (np.clip(wave, -0.95, 0.95) * 32767).astype(np.int16)
    stereo = np.column_stack((samples, samples))
    return pygame.mixer.Sound(buffer=stereo.tobytes())


class HitSounds:
    """Pre-generated audio feedback sounds for hit ratings.

    Two modes:
      - granular: distinct sound per rating (chime/tap/buzz)
      - uniform: same clean click for any hit
    Toggle with .toggle_mode()
    """

    MODE_GRANULAR = "granular"
    MODE_UNIFORM = "uniform"

    def __init__(self):
        self.mode = self.MODE_GRANULAR

        # Granular: 4 distinct sounds per rating
        self._granular = {
            HitRating.PERFECT: _generate_tone(
                2000, 60, 0.35, decay=25,
                harmonics=[(3000, 0.15), (4000, 0.08)]
            ),
            HitRating.GOOD: _generate_tone(
                1500, 50, 0.3, decay=30,
                harmonics=[(2200, 0.1)]
            ),
            HitRating.OK: _generate_tone(
                600, 40, 0.25, decay=50
            ),
            HitRating.MISS: _generate_tone(
                200, 70, 0.2, decay=20,
                harmonics=[(250, 0.15), (150, 0.1)]
            ),
        }

        # Uniform: one clean click for any hit
        self._uniform_sound = _generate_tone(
            1000, 35, 0.35, decay=35,
            harmonics=[(1500, 0.08)]
        )

    def toggle_mode(self):
        if self.mode == self.MODE_GRANULAR:
            self.mode = self.MODE_UNIFORM
        else:
            self.mode = self.MODE_GRANULAR

    def play(self, rating: str):
        if self.mode == self.MODE_UNIFORM:
            self._uniform_sound.play()
        else:
            sound = self._granular.get(rating)
            if sound:
                sound.play()
