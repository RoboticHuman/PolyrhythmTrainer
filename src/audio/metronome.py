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

    # Fade-in (1ms attack) to avoid initial pop
    attack_samples = max(1, int(sample_rate * 0.001))
    fade_in = np.linspace(0, 1, attack_samples, dtype=np.float32)
    wave[:attack_samples] *= fade_in

    # Fade-out (1ms release) to avoid end-of-sample click
    release_samples = max(1, int(sample_rate * 0.001))
    fade_out = np.linspace(1, 0, release_samples, dtype=np.float32)
    wave[-release_samples:] *= fade_out

    # Clip to prevent distortion when sounds overlap
    wave = np.clip(wave, -0.95, 0.95)

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
        self._accent_sounds: dict[int, pygame.mixer.Sound] = {}
        self.muted = False
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
        """Create distinct click sounds for different layers + accent variants."""
        # Normal beats per layer (soft)
        self._sounds[0] = generate_click(freq=1200, duration_ms=25, volume=0.35)
        self._sounds[1] = generate_click(freq=800, duration_ms=30, volume=0.3)
        self._sounds[2] = generate_click(freq=600, duration_ms=35, volume=0.25)
        # Accented beats per layer (clear but not harsh)
        self._accent_sounds[0] = generate_click(freq=1500, duration_ms=20, volume=0.55)
        self._accent_sounds[1] = generate_click(freq=1000, duration_ms=25, volume=0.45)
        self._accent_sounds[2] = generate_click(freq=800, duration_ms=28, volume=0.4)

    def get_sound(self, layer_index: int, accent: bool = False) -> pygame.mixer.Sound:
        sounds = self._accent_sounds if accent else self._sounds
        if layer_index in sounds:
            return sounds[layer_index]
        return sounds.get(0, self._sounds.get(0))

    def set_schedule(self, schedule: list[tuple[float, int, int, bool]], cycle_duration: float):
        """Schedule format: (phase, layer_idx, beat_idx, is_accent)."""
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

            for sched_entry in self._schedule:
                sched_phase, layer_idx, beat_idx = sched_entry[0], sched_entry[1], sched_entry[2]
                is_accent = sched_entry[3] if len(sched_entry) > 3 else (beat_idx == 0)
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

                if not self.muted:
                    sound = self.get_sound(layer_idx, accent=is_accent)
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
