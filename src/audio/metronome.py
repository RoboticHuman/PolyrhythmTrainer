"""Metronome audio engine — generates and plays click sounds."""

import threading
import time
import numpy as np
import pygame


def generate_click(freq: float = 1000.0, duration_ms: int = 30,
                   sample_rate: int = 44100, volume: float = 0.5) -> pygame.mixer.Sound:
    """Generate a short click/tick sound as a pygame Sound object."""
    n_samples = int(sample_rate * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, n_samples, dtype=np.float32)

    # Sine wave with exponential decay
    wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 40) * volume

    # Convert to 16-bit stereo
    samples = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((samples, samples))

    return pygame.mixer.Sound(buffer=stereo.tobytes())


class Metronome:
    """Threaded metronome that plays clicks at beat positions.

    Uses a dedicated thread with perf_counter for precise scheduling.
    Tracks each beat by (cycle_num, layer_idx, beat_idx) to avoid replays.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._sounds: dict[int, pygame.mixer.Sound] = {}
        self._running = False
        self._thread: threading.Thread | None = None

        # Schedule: list of (phase, layer_index, beat_index) for one cycle
        self._schedule: list[tuple[float, int, int]] = []
        self._cycle_duration: float = 1.0
        self._start_time: float = 0.0

        # Callback for beat events (for visual sync)
        self.on_beat: callable = None  # (layer_index, beat_index, time) -> None

        self._generate_default_sounds()

    def _generate_default_sounds(self):
        """Create distinct click sounds for different layers."""
        self._sounds[0] = generate_click(freq=1200, duration_ms=25, volume=0.6)
        self._sounds[1] = generate_click(freq=800, duration_ms=30, volume=0.5)
        self._sounds[2] = generate_click(freq=600, duration_ms=35, volume=0.45)
        self._sounds[-1] = generate_click(freq=1500, duration_ms=20, volume=0.7)

    def get_sound(self, layer_index: int) -> pygame.mixer.Sound:
        if layer_index in self._sounds:
            return self._sounds[layer_index]
        return self._sounds.get(0)

    def set_schedule(self, schedule: list[tuple[float, int, int]], cycle_duration: float):
        self._schedule = sorted(schedule, key=lambda x: x[0])
        self._cycle_duration = cycle_duration

    def start(self, start_time: float):
        self._start_time = start_time
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _run(self):
        """Main metronome loop — runs in dedicated thread."""
        if not self._schedule or self._cycle_duration <= 0:
            return

        # Track which beats have been played: set of (cycle, layer, beat)
        played: set[tuple[int, int, int]] = set()

        while self._running:
            now = time.perf_counter()
            elapsed = now - self._start_time
            if elapsed < 0:
                time.sleep(0.001)
                continue

            cycle_num = int(elapsed / self._cycle_duration)
            phase = (elapsed % self._cycle_duration) / self._cycle_duration

            for sched_phase, layer_idx, beat_idx in self._schedule:
                if sched_phase > phase:
                    continue

                key = (cycle_num, layer_idx, beat_idx)
                if key in played:
                    continue

                # Only play if we're within 50ms of the scheduled time
                beat_time = self._start_time + cycle_num * self._cycle_duration + sched_phase * self._cycle_duration
                if now - beat_time > 0.05:
                    # We're too late, mark as played but don't sound
                    played.add(key)
                    continue

                sound = self.get_sound(layer_idx)
                sound.play()
                played.add(key)

                if self.on_beat:
                    try:
                        self.on_beat(layer_idx, beat_idx, now)
                    except Exception:
                        pass

            # Cleanup old entries to prevent unbounded growth
            if len(played) > 200:
                cutoff = cycle_num - 2
                played = {k for k in played if k[0] >= cutoff}

            time.sleep(0.001)
