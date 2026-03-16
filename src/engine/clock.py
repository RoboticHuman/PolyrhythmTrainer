"""High-resolution timing engine using time.perf_counter()."""

import time


class Clock:
    """Precision beat clock for rhythm tracking.

    Tracks elapsed time, current beat position, and phase within the beat cycle.
    Uses time.perf_counter() for sub-millisecond accuracy.
    """

    def __init__(self, bpm: float = 120.0, beats_per_cycle: int = 4):
        self.bpm = bpm
        self.beats_per_cycle = beats_per_cycle
        self._start_time: float = 0.0
        self._running = False
        self._pause_elapsed: float = 0.0

    @property
    def beat_duration(self) -> float:
        """Duration of one beat in seconds."""
        return 60.0 / self.bpm

    @property
    def cycle_duration(self) -> float:
        """Duration of one full cycle in seconds."""
        return self.beat_duration * self.beats_per_cycle

    def start(self):
        self._start_time = time.perf_counter()
        self._pause_elapsed = 0.0
        self._running = True

    def restart(self):
        """Restart the clock from now, preserving settings."""
        self.start()

    def stop(self):
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def elapsed(self) -> float:
        """Total elapsed time in seconds since start."""
        if not self._running:
            return self._pause_elapsed
        return time.perf_counter() - self._start_time

    def beat_position(self) -> float:
        """Current position in beats (continuous float). Beat 0.0 is the start."""
        return self.elapsed() / self.beat_duration

    def cycle_phase(self) -> float:
        """Phase within the current cycle, 0.0 to 1.0."""
        if self.cycle_duration == 0:
            return 0.0
        return (self.elapsed() % self.cycle_duration) / self.cycle_duration

    def beat_phase(self) -> float:
        """Phase within the current beat, 0.0 to 1.0."""
        if self.beat_duration == 0:
            return 0.0
        return (self.elapsed() % self.beat_duration) / self.beat_duration

    def current_beat_in_cycle(self) -> int:
        """Which beat we're on within the cycle (0-indexed)."""
        return int(self.beat_position() % self.beats_per_cycle)

    def cycle_count(self) -> int:
        """How many full cycles have completed."""
        return int(self.elapsed() / self.cycle_duration) if self.cycle_duration > 0 else 0

    def set_bpm(self, bpm: float):
        """Change BPM without resetting the clock."""
        self.bpm = max(1.0, bpm)

    def time_to_next_beat(self) -> float:
        """Seconds until the next beat."""
        return self.beat_duration * (1.0 - self.beat_phase())

    def timestamp(self) -> float:
        """Get current high-resolution timestamp (for input events)."""
        return time.perf_counter()
