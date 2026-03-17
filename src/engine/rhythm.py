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

    Can be created with either:
      - beats (int): evenly spaced beats (e.g., 4 = quarter notes in 4/4)
      - phases (list[float]): custom beat positions 0.0-1.0 (e.g., [0, 0.286, 0.571] for 2+2+3 in 7/8)
    """

    def __init__(self, beats: int = 0, name: str = "", layer_index: int = 0,
                 phases: list[float] | None = None):
        self.layer_index = layer_index
        self.name = name or f"Layer {layer_index}"

        if phases is not None:
            # Custom beat positions
            self._beat_phases = sorted(phases)
            self.beats = len(self._beat_phases)
        else:
            # Evenly spaced
            self.beats = beats
            self._beat_phases = [i / beats for i in range(beats)] if beats > 0 else []

    @property
    def beat_phases(self) -> list[float]:
        """Normalized positions where this layer's beats fall (0.0 to 1.0)."""
        return self._beat_phases

    def nearest_beat_phase(self, phase: float) -> tuple[int, float]:
        """Find the nearest beat to a given cycle phase."""
        if not self._beat_phases:
            return (0, 1.0)

        best_idx = 0
        best_dist = 1.0

        for i, bp in enumerate(self._beat_phases):
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
        bpm: Tempo in beats per minute
        layers: List of RhythmLayer objects, or list of ints (for evenly spaced)
        base_beats: The reference beat count (defines what "one beat" means for BPM)
    """

    def __init__(self, bpm: float, layers: list, base_beats: int = 4):
        self.bpm = bpm
        self.base_beats = base_beats
        self.layers: list[RhythmLayer] = []

        for i, layer in enumerate(layers):
            if isinstance(layer, RhythmLayer):
                layer.layer_index = i
                self.layers.append(layer)
            else:
                # Integer — evenly spaced beats
                self.layers.append(RhythmLayer(beats=layer, layer_index=i))

    @property
    def cycle_duration(self) -> float:
        """Duration of one full cycle in seconds."""
        return (60.0 / self.bpm) * self.base_beats

    @property
    def total_subdivisions(self) -> int:
        """LCM of all layer beat counts — the finest grid."""
        if not self.layers:
            return 1
        return lcm_multi([l.beats for l in self.layers])

    def get_beat_times(self, layer_index: int) -> list[float]:
        if layer_index >= len(self.layers):
            return []
        return [p * self.cycle_duration for p in self.layers[layer_index].beat_phases]

    def get_all_beat_times(self) -> list[tuple[int, int, float]]:
        events = []
        for li, layer in enumerate(self.layers):
            for bi, phase in enumerate(layer.beat_phases):
                events.append((li, bi, phase * self.cycle_duration))
        events.sort(key=lambda e: e[2])
        return events

    def phase_to_time(self, phase: float) -> float:
        return phase * self.cycle_duration

    def time_to_phase(self, t: float) -> float:
        if self.cycle_duration == 0:
            return 0.0
        return (t % self.cycle_duration) / self.cycle_duration

    @property
    def description(self) -> str:
        return ":".join(str(l.beats) for l in self.layers)
