"""Polyrhythm Trainer — main entry point and game loop."""

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
from src.engine import records, progression
from src.input.keyboard import KeyboardInput
from src.input.midi import MidiInput
from src.audio.metronome import Metronome
from src.audio.hitsounds import HitSounds
from src.visuals.orbits import OrbitsVisualizer
from src.visuals.gameoflife import GameOfLifeVisualizer
from src.visuals.automata import AutomataVisualizer
from src.visuals.boxing import BoxingVisualizer
from src.visuals.blacksmith import BlacksmithVisualizer
from src.visuals.colors import LAYER_COLORS, BG_DARK
from src.visuals.effects import CRTFilter
from src.ui.hud import HUD
from src.ui.menu import MainMenu
from src.ui.results import ResultsScreen, calc_grade


# App states
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_COUNTDOWN = "countdown"
STATE_RESULTS = "results"


class App:
    """Main application — state machine driving menu, sessions, and results."""

    def __init__(self):
        pygame.init()
        pygame.mixer.pre_init(SAMPLE_RATE, -16, AUDIO_CHANNELS, AUDIO_BUFFER)
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.pygame_clock = pygame.time.Clock()

        # App state
        self.running = True
        self.state = STATE_MENU
        self.game_mode = "freeplay"  # freeplay, challenge, progression

        # Core
        self.bpm = DEFAULT_BPM
        self.current_preset_idx = 5
        self._load_preset(self.current_preset_idx)

        self.clock = Clock(self.bpm, self.session.base_beats)
        self.stats = SessionStats()
        self.keyboard_input = KeyboardInput()
        self.midi_input = MidiInput()
        self.metronome = Metronome(SAMPLE_RATE)
        self.hit_sounds = HitSounds()

        # Visuals
        self.visual_mode_idx = 0
        self.visualizers = [
            OrbitsVisualizer(self.screen),
            GameOfLifeVisualizer(self.screen),
            AutomataVisualizer(self.screen),
            BoxingVisualizer(self.screen),
            BlacksmithVisualizer(self.screen),
        ]
        self.crt = CRTFilter(SCREEN_WIDTH, SCREEN_HEIGHT)

        # UI screens
        self.hud = HUD(self.screen)
        self.menu = MainMenu(self.screen)
        self.results_screen = ResultsScreen(self.screen)

        # Hit detectors
        self.hit_detectors: list[HitDetector] = []
        self._beat_events: list[dict] = []
        self._hit_events: list[dict] = []
        self._session_start: float = 0.0

        # Challenge mode
        self._challenge_duration = 60
        self._challenge_start: float = 0.0
        self._challenge_bars = 0
        self._auto_ramp_bar = 0

        # Countdown
        self._countdown_start: float = 0.0

        # Results state
        self._results_new_best = False
        self._results_unlocks: list[int] = []
        self._results_bpm_reached = 0.0

        # Layer data cache
        self._cached_layer_data: list[dict] = []

        self._init_midi()

    def _load_preset(self, idx: int):
        name, layers, base = PRESETS[idx % len(PRESETS)]
        self.session = PolyrhythmSession(self.bpm, layers, base)
        self.preset_name = name

    def _init_midi(self):
        if not MidiInput.available():
            return
        devices = MidiInput.list_devices()
        if devices:
            self.midi_input.open(devices[0])

    def _build_schedule(self):
        self.session.bpm = self.bpm
        self.clock.bpm = self.bpm
        self.clock.beats_per_cycle = self.session.base_beats

        schedule = []
        for li, layer in enumerate(self.session.layers):
            for bi, phase in enumerate(layer.beat_phases):
                schedule.append((phase, li, bi))
        self.metronome.set_schedule(schedule, self.session.cycle_duration)

        self.hit_detectors = [
            HitDetector(self.session.cycle_duration, layer.beat_phases)
            for layer in self.session.layers
        ]
        self._cached_layer_data = [
            {
                "beats": layer.beats,
                "phases": layer.beat_phases,
                "color": LAYER_COLORS[i % len(LAYER_COLORS)],
                "name": layer.name,
            }
            for i, layer in enumerate(self.session.layers)
        ]

    def _rebuild_session(self):
        self.metronome.stop()
        self._build_schedule()
        now = time.perf_counter()
        self._session_start = now
        self.clock.restart()
        self.stats.reset()
        self.metronome.start(now)

    def _start_session(self):
        self.stats.reset()
        self._beat_events.clear()
        self._hit_events.clear()

        def on_beat(layer_idx, beat_idx, t):
            self._beat_events.append({
                "time": t, "layer": layer_idx, "beat_idx": beat_idx
            })
            viz = self.visualizers[self.visual_mode_idx]
            viz.on_beat(layer_idx, beat_idx)
            # Track bars for auto-ramp
            if layer_idx == 0 and beat_idx == 0:
                self._challenge_bars += 1

        self.metronome.on_beat = on_beat
        self._build_schedule()

        self._session_start = time.perf_counter()
        self._challenge_start = self._session_start
        self._challenge_bars = 0
        self._auto_ramp_bar = 0
        self._results_bpm_reached = self.bpm
        self.clock.start()
        self.metronome.start(self._session_start)
        self.midi_input.start()

    def _stop_session(self):
        self.metronome.stop()
        self.midi_input.stop()
        self.clock.stop()

    def _process_hit(self, layer_idx: int, hit_time: float):
        if layer_idx >= len(self.hit_detectors):
            layer_idx = 0
        if layer_idx >= len(self.hit_detectors):
            return

        result = self.hit_detectors[layer_idx].detect_hit(hit_time, self._session_start)
        if result is None:
            return

        rating, deviation_ms = result
        deviation_ms -= LATENCY_COMPENSATION_MS
        self.stats.record_hit(deviation_ms)
        self.hit_sounds.play(rating)

        viz = self.visualizers[self.visual_mode_idx]
        viz.on_hit(layer_idx, rating, deviation_ms)
        self.hud.show_hit_rating(rating, deviation_ms, time.perf_counter())

        self._hit_events.append({
            "time": hit_time, "layer": layer_idx,
            "rating": rating, "deviation": deviation_ms
        })

    def _check_auto_ramp(self):
        """In challenge mode, increase BPM every 8 bars if doing well."""
        if self.game_mode == "freeplay":
            return
        bars_per_ramp = 8
        if self._challenge_bars >= self._auto_ramp_bar + bars_per_ramp:
            self._auto_ramp_bar = self._challenge_bars
            if self.stats.accuracy_pct >= 80 and self.stats.total_hits > 0:
                self.bpm = min(MAX_BPM, self.bpm + 5)
                self._results_bpm_reached = max(self._results_bpm_reached, self.bpm)
                self._rebuild_session()

    def _check_challenge_end(self) -> bool:
        """Check if challenge time has expired."""
        if self.game_mode == "freeplay":
            return False
        elapsed = time.perf_counter() - self._challenge_start
        return elapsed >= self._challenge_duration

    def _end_challenge(self):
        """Transition to results screen."""
        self._stop_session()
        self._results_bpm_reached = max(self._results_bpm_reached, self.bpm)

        grade = calc_grade(self.stats.accuracy_pct)

        # Save record
        self._results_new_best = records.save_if_best(
            self.preset_name, self._challenge_duration,
            self.stats.score, self.stats.accuracy_pct,
            grade, self.stats.best_combo, self._results_bpm_reached
        )

        # Check progression unlocks
        self._results_unlocks = progression.record_grade(self.current_preset_idx, grade)

        self.state = STATE_RESULTS

    # --- Event handling per state ---

    def _handle_menu_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.menu.state == "main":
                    self.running = False
                else:
                    action = self.menu.handle_event(event)
                    if action == "start_freeplay":
                        self.game_mode = "freeplay"
                        self.bpm = self.menu.chosen_bpm
                        self.visual_mode_idx = self.menu.chosen_visual
                        self.current_preset_idx = self.menu.chosen_preset_idx
                        self._load_preset(self.current_preset_idx)
                        self.state = STATE_PLAYING
                        self._start_session()
                    elif action in ("start_challenge", "start_progression"):
                        self.game_mode = "challenge" if action == "start_challenge" else "progression"
                        self.bpm = self.menu.chosen_bpm
                        self.visual_mode_idx = self.menu.chosen_visual
                        self.current_preset_idx = self.menu.chosen_preset_idx
                        self._challenge_duration = self.menu.chosen_duration
                        self._load_preset(self.current_preset_idx)
                        # Start countdown
                        self._countdown_start = time.perf_counter()
                        self.state = STATE_COUNTDOWN

    def _handle_playing_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._stop_session()
                    self.menu.reset()
                    self.state = STATE_MENU
                elif event.key == pygame.K_TAB:
                    self.hud.toggle()
                elif event.key == pygame.K_v:
                    self.visual_mode_idx = (self.visual_mode_idx + 1) % len(self.visualizers)
                elif event.key == pygame.K_c:
                    self.crt.enabled = not self.crt.enabled
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    if self.game_mode == "freeplay":
                        self.bpm = min(MAX_BPM, self.bpm + 5)
                        self._rebuild_session()
                elif event.key == pygame.K_MINUS:
                    if self.game_mode == "freeplay":
                        self.bpm = max(MIN_BPM, self.bpm - 5)
                        self._rebuild_session()
                elif event.key == pygame.K_r:
                    self._stop_session()
                    self._start_session()
                elif self.game_mode == "freeplay":
                    if event.key == pygame.K_LEFTBRACKET:
                        self.current_preset_idx = (self.current_preset_idx - 1) % len(PRESETS)
                        self._stop_session()
                        self._load_preset(self.current_preset_idx)
                        self._start_session()
                    elif event.key == pygame.K_RIGHTBRACKET:
                        self.current_preset_idx = (self.current_preset_idx + 1) % len(PRESETS)
                        self._stop_session()
                        self._load_preset(self.current_preset_idx)
                        self._start_session()
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        preset_idx = event.key - pygame.K_1
                        if preset_idx < len(PRESETS):
                            self.current_preset_idx = preset_idx
                            self._stop_session()
                            self._load_preset(preset_idx)
                            self._start_session()

    def _handle_results_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.menu.reset()
                    self.state = STATE_MENU
                elif event.key == pygame.K_r:
                    # Retry
                    self._load_preset(self.current_preset_idx)
                    self.state = STATE_COUNTDOWN
                    self._countdown_start = time.perf_counter()

    # --- Rendering ---

    def _render_countdown(self):
        elapsed = time.perf_counter() - self._countdown_start
        remaining = 3 - int(elapsed)

        self.screen.fill(BG_DARK)
        font = pygame.font.SysFont("consolas", 120, bold=True)

        if remaining > 0:
            text = str(remaining)
            color = (LAYER_COLORS[0] if remaining == 3 else
                     LAYER_COLORS[1] if remaining == 2 else LAYER_COLORS[2])
        else:
            text = "GO!"
            color = (0, 255, 128)

        surf = font.render(text, True, color)
        cx = SCREEN_WIDTH // 2 - surf.get_width() // 2
        cy = SCREEN_HEIGHT // 2 - surf.get_height() // 2
        self.screen.blit(surf, (cx, cy))

        # Preset info
        info_font = pygame.font.SysFont("consolas", 20)
        info = info_font.render(
            f"{self.preset_name}  |  {self.bpm} BPM  |  {self._challenge_duration}s",
            True, (150, 150, 170)
        )
        self.screen.blit(info, (SCREEN_WIDTH // 2 - info.get_width() // 2,
                                 SCREEN_HEIGHT // 2 + 80))

        if elapsed >= 3.5:
            self.state = STATE_PLAYING
            self._start_session()

    def _render_session(self, dt: float, events: list[pygame.event.Event]):
        # Rhythm input
        hits = self.keyboard_input.process_events(events)
        for layer_idx, hit_time in hits:
            self._process_hit(layer_idx, hit_time)

        midi_hits = self.midi_input.get_hits()
        for layer_idx, hit_time in midi_hits:
            self._process_hit(layer_idx, hit_time)

        # Auto-ramp check
        self._check_auto_ramp()

        # Challenge end check
        if self._check_challenge_end():
            self._end_challenge()
            return

        # Visualizer
        cycle_phase = self.clock.cycle_phase()
        viz = self.visualizers[self.visual_mode_idx]
        viz.update_state(
            cycle_phase=cycle_phase, bpm=self.bpm,
            layers=self._cached_layer_data,
            hit_events=self._hit_events[-20:],
            beat_events=self._beat_events[-20:],
            dt=dt,
        )
        viz.render()

        # HUD — show timer in challenge mode
        mode_label = VISUAL_MODES[self.visual_mode_idx]
        if self.game_mode != "freeplay":
            remaining = max(0, self._challenge_duration - (time.perf_counter() - self._challenge_start))
            mode_label = f"{self.game_mode.upper()} {remaining:.0f}s"

        self.hud.render(
            stats=self.stats, bpm=self.bpm,
            rhythm_desc=f"{self.preset_name} ({self.session.description})",
            current_time=time.perf_counter(),
            visual_mode=mode_label,
        )

        self.crt.apply(self.screen)

        # Trim buffers
        if len(self._beat_events) > 50:
            self._beat_events = self._beat_events[-30:]
        if len(self._hit_events) > 50:
            self._hit_events = self._hit_events[-30:]

    def run(self):
        while self.running:
            dt = self.pygame_clock.tick(FPS) / 1000.0
            events = pygame.event.get()

            if self.state == STATE_MENU:
                self._handle_menu_events(events)
                if self.state == STATE_MENU:
                    self.menu.render()

            elif self.state == STATE_COUNTDOWN:
                # Allow quit during countdown
                for e in events:
                    if e.type == pygame.QUIT:
                        self.running = False
                    elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                        self.menu.reset()
                        self.state = STATE_MENU
                if self.state == STATE_COUNTDOWN:
                    self._render_countdown()

            elif self.state == STATE_PLAYING:
                self._handle_playing_events(events)
                if self.state == STATE_PLAYING:
                    self._render_session(dt, events)

            elif self.state == STATE_RESULTS:
                self._handle_results_events(events)
                if self.state == STATE_RESULTS:
                    # Render the last frame of the session underneath
                    self.results_screen.render(
                        self.stats, self.preset_name, self._results_bpm_reached,
                        self._challenge_duration, self._results_new_best,
                        self._results_unlocks,
                    )

            pygame.display.flip()

        self._stop_session()
        pygame.quit()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
