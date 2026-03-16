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
    samples = (np.clip(wave, -1, 1) * 32767).astype(np.int16)
    stereo = np.column_stack((samples, samples))
    return pygame.mixer.Sound(buffer=stereo.tobytes())


class HitSounds:
    """Pre-generated audio feedback sounds for hit ratings."""

    def __init__(self):
        # Perfect: bright two-tone chime
        self._sounds = {
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

    def play(self, rating: str):
        sound = self._sounds.get(rating)
        if sound:
            sound.play()
