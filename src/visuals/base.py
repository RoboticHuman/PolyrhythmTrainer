"""Base class for visual renderers."""

import pygame
from src.engine.scoring import HitRating


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
        self.active_layer: int = 0  # Which layer the player is hitting

        # Recent hit events for visual feedback
        self.hit_events: list[dict] = []  # [{time, layer, rating, deviation}, ...]

        # Beat events from metronome (for flash/pulse)
        self.beat_events: list[dict] = []  # [{time, layer, beat_idx}, ...]

    def update_state(self, cycle_phase: float, bpm: float, layers: list[dict],
                     hit_events: list[dict], beat_events: list[dict], dt: float):
        """Update visualizer state. Called each frame before render()."""
        self.cycle_phase = cycle_phase
        self.bpm = bpm
        self.layers = layers
        self.hit_events = hit_events
        self.beat_events = beat_events
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
    def rating_to_alpha(rating: str) -> int:
        """Convert rating to glow intensity."""
        return {
            HitRating.PERFECT: 255,
            HitRating.GOOD: 200,
            HitRating.OK: 140,
            HitRating.MISS: 80,
        }.get(rating, 60)
