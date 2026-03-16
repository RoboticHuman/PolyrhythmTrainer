"""Polyrhythm Trainer — main entry point and game loop."""

import sys
import time
import pygame

from src.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE,
    SAMPLE_RATE, AUDIO_BUFFER, AUDIO_CHANNELS,
    DEFAULT_BPM, MIN_BPM, MAX_BPM, VISUAL_MODES, PRESETS,
    LATENCY_COMPENSATION_MS
)
from src.engine.clock import Clock
from src.engine.rhythm import PolyrhythmSession
from src.engine.scoring import SessionStats, HitDetector
from src.input.keyboard import KeyboardInput
from src.input.midi import MidiInput
from src.audio.metronome import Metronome
from src.visuals.orbits import OrbitsVisualizer
from src.visuals.gameoflife import GameOfLifeVisualizer
from src.visuals.automata import AutomataVisualizer
from src.visuals.colors import LAYER_COLORS, BG_DARK
from src.ui.hud import HUD


class App:
    """Main application — manages the game loop and all subsystems."""

    def __init__(self):
        pygame.init()
        pygame.mixer.pre_init(SAMPLE_RATE, -16, AUDIO_CHANNELS, AUDIO_BUFFER)
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.pygame_clock = pygame.time.Clock()

        # Core state
        self.running = True
        self.bpm = DEFAULT_BPM
        self.current_preset_idx = 5  # 3:4 by default
        self._load_preset(self.current_preset_idx)

        # Subsystems
        self.clock = Clock(self.bpm, self.session.base_beats)
        self.stats = SessionStats()
        self.keyboard_input = KeyboardInput()
        self.midi_input = MidiInput()
        self.metronome = Metronome(SAMPLE_RATE)
        self.hud = HUD(self.screen)

        # Visual modes
        self.visual_mode_idx = 0
        self.visualizers = [
            OrbitsVisualizer(self.screen),
            GameOfLifeVisualizer(self.screen),
            AutomataVisualizer(self.screen),
        ]

        # Hit detectors per layer
        self.hit_detectors: list[HitDetector] = []

        # Beat event buffer for visuals
        self._beat_events: list[dict] = []
        self._hit_events: list[dict] = []

        # Session timing
        self._session_start: float = 0.0

        # Try to open MIDI
        self._init_midi()

    def _load_preset(self, idx: int):
        """Load a polyrhythm preset."""
        name, layers, base = PRESETS[idx % len(PRESETS)]
        self.session = PolyrhythmSession(self.bpm, layers, base)
        self.preset_name = name

    def _init_midi(self):
        """Attempt to open the first available MIDI device."""
        if not MidiInput.available():
            print("MIDI: mido not available (install with 'uv add mido[ports-rtmidi]' for MIDI support)")
            return

        devices = MidiInput.list_devices()
        if devices:
            print(f"MIDI devices found: {devices}")
            if self.midi_input.open(devices[0]):
                print(f"MIDI: Opened '{devices[0]}'")
            else:
                print("MIDI: Failed to open device")
        else:
            print("MIDI: No devices found (keyboard input active)")

    def _rebuild_session(self):
        """Rebuild session state after BPM or preset change (while running)."""
        self.session.bpm = self.bpm
        self.clock.bpm = self.bpm
        self.clock.beats_per_cycle = self.session.base_beats

        # Restart metronome with fresh time reference
        self.metronome.stop()

        schedule = []
        for li, layer in enumerate(self.session.layers):
            for bi, phase in enumerate(layer.beat_phases):
                schedule.append((phase, li, bi))
        self.metronome.set_schedule(schedule, self.session.cycle_duration)

        now = time.perf_counter()
        self._session_start = now
        self.clock._start_time = now
        self.stats.reset()
        self.metronome.start(now)

        # Rebuild hit detectors
        self.hit_detectors = []
        for layer in self.session.layers:
            detector = HitDetector(self.session.cycle_duration, layer.beat_phases)
            self.hit_detectors.append(detector)

    def _start_session(self):
        """Start/restart the practice session."""
        self.stats.reset()
        self._beat_events.clear()
        self._hit_events.clear()

        # Set callback before building session (rebuild starts the metronome)
        def on_beat(layer_idx, beat_idx, t):
            self._beat_events.append({
                "time": t, "layer": layer_idx, "beat_idx": beat_idx
            })
            viz = self.visualizers[self.visual_mode_idx]
            viz.on_beat(layer_idx, beat_idx)

        self.metronome.on_beat = on_beat

        # Build schedule and hit detectors (does NOT start metronome)
        self.session.bpm = self.bpm
        self.clock.bpm = self.bpm
        self.clock.beats_per_cycle = self.session.base_beats

        schedule = []
        for li, layer in enumerate(self.session.layers):
            for bi, phase in enumerate(layer.beat_phases):
                schedule.append((phase, li, bi))
        self.metronome.set_schedule(schedule, self.session.cycle_duration)

        self.hit_detectors = []
        for layer in self.session.layers:
            detector = HitDetector(self.session.cycle_duration, layer.beat_phases)
            self.hit_detectors.append(detector)

        # Start everything from now
        self._session_start = time.perf_counter()
        self.clock.start()
        self.metronome.start(self._session_start)
        self.midi_input.start()

    def _stop_session(self):
        self.metronome.stop()
        self.midi_input.stop()
        self.clock.stop()

    def _process_hit(self, layer_idx: int, hit_time: float):
        """Score a hit and notify visuals."""
        if layer_idx >= len(self.hit_detectors):
            # If only one layer, map all hits to layer 0
            layer_idx = 0

        if layer_idx >= len(self.hit_detectors):
            return

        result = self.hit_detectors[layer_idx].detect_hit(hit_time, self._session_start)
        if result is None:
            return

        rating, deviation_ms = result
        # Apply latency compensation
        deviation_ms -= LATENCY_COMPENSATION_MS

        self.stats.record_hit(deviation_ms)

        # Notify visuals
        viz = self.visualizers[self.visual_mode_idx]
        viz.on_hit(layer_idx, rating, deviation_ms)

        # HUD popup
        self.hud.show_hit_rating(rating, deviation_ms, time.perf_counter())

        self._hit_events.append({
            "time": hit_time, "layer": layer_idx,
            "rating": rating, "deviation": deviation_ms
        })

    def _handle_events(self, events: list[pygame.event.Event]):
        """Handle UI events (non-rhythm keys)."""
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_TAB:
                    self.hud.toggle()
                elif event.key == pygame.K_v:
                    self.visual_mode_idx = (self.visual_mode_idx + 1) % len(self.visualizers)
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self.bpm = min(MAX_BPM, self.bpm + 5)
                    self._rebuild_session()
                elif event.key == pygame.K_MINUS:
                    self.bpm = max(MIN_BPM, self.bpm - 5)
                    self._rebuild_session()
                elif event.key == pygame.K_r:
                    self._stop_session()
                    self._start_session()
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    preset_idx = event.key - pygame.K_1
                    if preset_idx < len(PRESETS):
                        self.current_preset_idx = preset_idx
                        self._stop_session()
                        self._load_preset(preset_idx)
                        self._start_session()

    def _build_layer_data(self) -> list[dict]:
        """Build layer data dicts for the visualizer."""
        data = []
        for i, layer in enumerate(self.session.layers):
            data.append({
                "beats": layer.beats,
                "phases": layer.beat_phases,
                "color": LAYER_COLORS[i % len(LAYER_COLORS)],
                "name": layer.name,
            })
        return data

    def run(self):
        """Main game loop."""
        self._start_session()

        while self.running:
            dt = self.pygame_clock.tick(FPS) / 1000.0

            # Input
            events = pygame.event.get()
            self._handle_events(events)

            # Keyboard rhythm hits
            hits = self.keyboard_input.process_events(events)
            for layer_idx, hit_time in hits:
                self._process_hit(layer_idx, hit_time)

            # MIDI rhythm hits
            midi_hits = self.midi_input.get_hits()
            for layer_idx, hit_time in midi_hits:
                self._process_hit(layer_idx, hit_time)

            # Update visualizer state
            cycle_phase = self.clock.cycle_phase()
            viz = self.visualizers[self.visual_mode_idx]
            viz.update_state(
                cycle_phase=cycle_phase,
                bpm=self.bpm,
                layers=self._build_layer_data(),
                hit_events=self._hit_events[-20:],
                beat_events=self._beat_events[-20:],
                dt=dt,
            )

            # Render
            viz.render()

            # HUD
            self.hud.render(
                stats=self.stats,
                bpm=self.bpm,
                rhythm_desc=f"{self.preset_name} ({self.session.description})",
                current_time=time.perf_counter(),
                visual_mode=VISUAL_MODES[self.visual_mode_idx],
            )

            pygame.display.flip()

            # Trim event buffers
            if len(self._beat_events) > 50:
                self._beat_events = self._beat_events[-30:]
            if len(self._hit_events) > 50:
                self._hit_events = self._hit_events[-30:]

        self._stop_session()
        pygame.quit()


def main():
    print("=== Polyrhythm Trainer ===")
    print("Controls:")
    print("  Space/F/J  — Hit rhythm layers 0/1/2")
    print("  Tab        — Toggle stats HUD")
    print("  V          — Cycle visual mode")
    print("  +/-        — Adjust BPM")
    print("  1-9        — Select preset")
    print("  R          — Restart session")
    print("  Esc        — Quit")
    print()

    app = App()
    app.run()


if __name__ == "__main__":
    main()
