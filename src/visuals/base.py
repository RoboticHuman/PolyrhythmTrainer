"""Base class for visual renderers."""

import pygame
from src.visuals.colors import rating_color


class BaseVisualizer:
    """Abstract base for all visual modes.

    Subclasses implement render() to draw their specific visualization.
    All visualizers receive the same beat/timing/scoring data.
    """

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()

        # State updated each frame by the main loop
        self.cycle_phase: float = 0.0  # 0.0 to 1.0
        self.bpm: float = 120.0
        self.layers: list[dict] = []  # [{beats, phases, color, name}, ...]
        self.dt: float = 0.0

    def update_state(self, cycle_phase: float, bpm: float, layers: list[dict],
                     hit_events: list[dict], beat_events: list[dict], dt: float):
        """Update visualizer state. Called each frame before render()."""
        self.cycle_phase = cycle_phase
        self.bpm = bpm
        self.layers = layers
        self.dt = dt

    def render(self):
        """Draw the visualization. Override in subclasses."""
        raise NotImplementedError

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        """Called immediately when a hit is registered."""
        pass

    def on_beat(self, layer: int, beat_idx: int):
        """Called when a metronome beat plays."""
        pass

    @staticmethod
    def _find_nearest_beat(phases: list[float], cycle_phase: float) -> int:
        """Find the index of the nearest beat marker to the current phase."""
        best_bi = 0
        best_dist = 1.0
        for bi, phase in enumerate(phases):
            dist = abs(cycle_phase - phase)
            dist = min(dist, 1.0 - dist)
            if dist < best_dist:
                best_dist = dist
                best_bi = bi
        return best_bi
