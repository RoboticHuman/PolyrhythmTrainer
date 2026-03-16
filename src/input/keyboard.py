"""Keyboard input handler for rhythm hits."""

import time
import pygame
from src.config import KEYBOARD_LAYER_KEYS


class KeyboardInput:
    """Handles keyboard input for rhythm practice.

    Maps keys to rhythm layers and timestamps hits with perf_counter.
    """

    def __init__(self):
        # Key name -> layer index
        self.key_map: dict[int, int] = {}
        self._setup_default_mapping()

    def _setup_default_mapping(self):
        """Map pygame key constants to layer indices."""
        name_to_key = {
            "space": pygame.K_SPACE,
            "f": pygame.K_f,
            "j": pygame.K_j,
            "d": pygame.K_d,
            "k": pygame.K_k,
        }
        for name, layer in KEYBOARD_LAYER_KEYS.items():
            if name in name_to_key:
                self.key_map[name_to_key[name]] = layer

    def process_events(self, events: list[pygame.event.Event]) -> list[tuple[int, float]]:
        """Process pygame events and return timestamped hits.

        Returns:
            List of (layer_index, perf_counter_timestamp) for each hit detected.
        """
        hits = []
        now = time.perf_counter()

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in self.key_map:
                    layer = self.key_map[event.key]
                    hits.append((layer, now))

        return hits
