"""Polyrhythm math and beat scheduling."""

from math import gcd


def lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b)


def lcm_multi(values: list[int]) -> int:
    result = values[0]
    for v in values[1:]:
        result = lcm(result, v)
    return result


class RhythmLayer:
    """One rhythmic layer within a polyrhythm.

    Args:
        beats: Number of beats this layer plays per cycle (e.g., 3 in 3:4)
        name: Display name for this layer
        layer_index: Index for color/sound assignment
    """

    def __init__(self, beats: int, name: str = "", layer_index: int = 0):
        self.beats = beats
        self.name = name or f"Layer {layer_index}"
        self.layer_index = layer_index
        self._beat_phases: list[float] = []
        self._recompute_phases()

    def _recompute_phases(self):
        """Compute normalized beat positions (0.0 to 1.0) within a cycle."""
        if self.beats <= 0:
            self._beat_phases = []
            return
        self._beat_phases = [i / self.beats for i in range(self.beats)]

    @property
    def beat_phases(self) -> list[float]:
        """Normalized positions where this layer's beats fall (0.0 to 1.0)."""
        return self._beat_phases

    def nearest_beat_phase(self, phase: float) -> tuple[int, float]:
        """Find the nearest beat to a given cycle phase.

        Returns:
            (beat_index, signed_distance) where distance is negative if before beat,
            positive if after. Distance is in fraction of cycle (0.0-1.0).
        """
        if not self._beat_phases:
            return (0, 1.0)

        best_idx = 0
        best_dist = 1.0

        for i, bp in enumerate(self._beat_phases):
            # Circular distance (wrapping around 1.0)
            dist = phase - bp
            if dist > 0.5:
                dist -= 1.0
            elif dist < -0.5:
                dist += 1.0

            if abs(dist) < abs(best_dist):
                best_dist = dist
                best_idx = i

        return (best_idx, best_dist)


class PolyrhythmSession:
    """Manages multiple rhythmic layers playing simultaneously.

    Args:
        bpm: Tempo in beats per minute (refers to the base_beats layer)
        layers: List of beat counts for each layer
        base_beats: The reference beat count (defines what "one beat" means for BPM)
    """

    def __init__(self, bpm: float, layers: list[int], base_beats: int = 4):
        self.bpm = bpm
        self.base_beats = base_beats
        self.layers: list[RhythmLayer] = []

        for i, beats in enumerate(layers):
            self.layers.append(RhythmLayer(beats, layer_index=i))

    @property
    def cycle_duration(self) -> float:
        """Duration of one full cycle in seconds."""
        # One cycle = base_beats worth of beats at the given BPM
        return (60.0 / self.bpm) * self.base_beats

    @property
    def total_subdivisions(self) -> int:
        """LCM of all layer beat counts — the finest grid."""
        if not self.layers:
            return 1
        return lcm_multi([l.beats for l in self.layers])

    def get_beat_times(self, layer_index: int) -> list[float]:
        """Get absolute beat times (in seconds) for one cycle of a layer."""
        if layer_index >= len(self.layers):
            return []
        layer = self.layers[layer_index]
        return [p * self.cycle_duration for p in layer.beat_phases]

    def get_all_beat_times(self) -> list[tuple[int, int, float]]:
        """Get all beat events across all layers for one cycle.

        Returns list of (layer_index, beat_index, time_in_seconds), sorted by time.
        """
        events = []
        for li, layer in enumerate(self.layers):
            for bi, phase in enumerate(layer.beat_phases):
                events.append((li, bi, phase * self.cycle_duration))
        events.sort(key=lambda e: e[2])
        return events

    def phase_to_time(self, phase: float) -> float:
        """Convert a cycle phase (0.0–1.0) to seconds."""
        return phase * self.cycle_duration

    def time_to_phase(self, t: float) -> float:
        """Convert elapsed time to cycle phase (wrapping)."""
        if self.cycle_duration == 0:
            return 0.0
        return (t % self.cycle_duration) / self.cycle_duration

    @property
    def description(self) -> str:
        """Human-readable description like '3:4' or '5:4:3'."""
        return ":".join(str(l.beats) for l in self.layers)
