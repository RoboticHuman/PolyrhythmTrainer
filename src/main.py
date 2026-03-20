"""Polyrhythm Trainer — main entry point and game loop."""

import time
import pygame

from src.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE,
    SAMPLE_RATE, AUDIO_BUFFER, AUDIO_CHANNELS,
    DEFAULT_BPM, MIN_BPM, MAX_BPM, VISUAL_MODES, PRESETS,
    PRESET_INDEX_BY_ID, DEFAULT_PRESET_ID,
    LATENCY_COMPENSATION_MS,
    DIFFICULTY_MODES, DEFAULT_DIFFICULTY, set_difficulty,
    SECTION_RANGES, get_section_for_index,
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
from src.visuals.dancebattle import DanceBattleVisualizer
from src.visuals.cashier import CashierVisualizer
from src.visuals.samurai import SamuraiVisualizer
from src.visuals.colors import LAYER_COLORS, BG_DARK
from src.visuals.effects import CRTFilter
from src.ui.hud import HUD
from src.ui.menu import MainMenu
from src.ui.results import ResultsScreen, calc_grade
from src.ui.settings import SettingsOverlay
from src.ui.midi_setup import MidiSetup


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
        self.game_mode = "freeplay"
        self.difficulty = DEFAULT_DIFFICULTY
        self._difficulty_keys = list(DIFFICULTY_MODES.keys())

        # Core
        self.bpm = DEFAULT_BPM
        self.current_preset_idx = PRESET_INDEX_BY_ID.get(DEFAULT_PRESET_ID, 0)
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
            DanceBattleVisualizer(self.screen),
            CashierVisualizer(self.screen),
            SamuraiVisualizer(self.screen),
        ]
        self.crt = CRTFilter(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.crt.enabled = True

        # UI screens
        self.hud = HUD(self.screen)
        self.menu = MainMenu(self.screen)
        self.results_screen = ResultsScreen(self.screen)
        self.settings = SettingsOverlay(self.screen)
        self.midi_setup = MidiSetup(self.screen, self.midi_input)
        self._apply_settings()  # Apply saved/default sound settings on startup

        # Cached fonts for countdown
        self._countdown_font = pygame.font.SysFont("consolas", 120, bold=True)
        self._countdown_info_font = pygame.font.SysFont("consolas", 20)

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
        from src.engine.rhythm import RhythmLayer
        preset = PRESETS[idx % len(PRESETS)]
        rhythm_layers = []
        for ld in preset.layers:
            if isinstance(ld, dict):
                # Grouped rhythm: has phases + accents
                rhythm_layers.append(RhythmLayer(
                    phases=ld["phases"], accents=ld["accents"]
                ))
            elif isinstance(ld, int):
                # Evenly spaced beats
                rhythm_layers.append(RhythmLayer(beats=ld))
            else:
                # Legacy: list of floats (custom phases, no accents)
                rhythm_layers.append(RhythmLayer(phases=ld))
        self.session = PolyrhythmSession(self.bpm, rhythm_layers, preset.base_beats)
        self.preset_name = preset.name
        self.preset_id = preset.id
        sec_idx = get_section_for_index(idx)
        self.preset_section = SECTION_RANGES[sec_idx][2]

    def _init_midi(self):
        if not MidiInput.available():
            return
        devices = MidiInput.list_devices()
        if devices:
            if self.midi_input.open(devices[0]):
                self.midi_input.start()
                self.midi_setup.connected_name = devices[0]

    def _build_schedule(self):
        self.session.bpm = self.bpm
        self.clock.bpm = self.bpm
        self.clock.beats_per_cycle = self.session.base_beats

        schedule = []
        for li, layer in enumerate(self.session.layers):
            for bi, phase in enumerate(layer.beat_phases):
                is_accent = layer.is_accent(bi)
                schedule.append((phase, li, bi, is_accent))
        self.metronome.set_schedule(schedule, self.session.cycle_duration)

        lcm_grid = self.session.total_subdivisions
        sub_phases = [round(i / lcm_grid, 6) for i in range(lcm_grid)]
        self.metronome.set_subdivision_schedule(sub_phases)

        self.hit_detectors = [
            HitDetector(self.session.cycle_duration, layer.beat_phases)
            for layer in self.session.layers
        ]
        lcm_phases = [i / lcm_grid for i in range(lcm_grid)]
        self._cached_layer_data = [
            {
                "beats": layer.beats,
                "phases": layer.beat_phases,
                "accents": layer.accents,
                "color": LAYER_COLORS[i % len(LAYER_COLORS)],
                "name": layer.name,
                "lcm_phases": lcm_phases,
            }
            for i, layer in enumerate(self.session.layers)
        ]

    def _rebuild_session(self):
        """Update BPM/schedule without resetting position or stats."""
        self.metronome.stop()
        self._build_schedule()
        # Restart metronome from current time but keep session start and stats
        self.metronome.start(self._session_start)

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

    def _change_preset(self, idx: int):
        """Switch to a different preset (stop, load, restart)."""
        self.current_preset_idx = idx
        self._stop_session()
        self._load_preset(idx)
        self._start_session()

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
            self.preset_id, self._challenge_duration,
            self.stats.score, self.stats.accuracy_pct,
            grade, self.stats.best_combo, self._results_bpm_reached
        )

        # Check progression unlocks
        self._results_unlocks = progression.record_grade(self.preset_id, grade)

        self.state = STATE_RESULTS

    # --- Event handling per state ---

    def _handle_menu_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and self.menu.state == MainMenu.STATE_MAIN:
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

    def _apply_settings(self):
        """Apply current settings values to audio systems, using custom wavetables."""
        vals = self.settings.get_values()
        from src.engine.scoring import HitRating

        def _generate_custom(freq: float, duration_ms: int, volume: float,
                             wavetable: list[float], decay: float = 40) -> pygame.mixer.Sound:
            """Generate a sound using a custom wavetable shape."""
            import numpy as np
            n = int(44100 * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, n, dtype=np.float32)
            # Use wavetable: map time to table position based on frequency
            table = np.array(wavetable, dtype=np.float32)
            table_len = len(table)
            indices = (t * freq * table_len) % table_len
            idx_floor = indices.astype(np.int32) % table_len
            idx_ceil = (idx_floor + 1) % table_len
            frac = indices - indices.astype(np.int32)
            wave = (table[idx_floor] * (1 - frac) + table[idx_ceil] * frac)
            wave *= np.exp(-t * decay) * volume
            # Fade in/out
            attack = max(1, int(44100 * 0.001))
            wave[:attack] *= np.linspace(0, 1, attack, dtype=np.float32)
            release = max(1, int(44100 * 0.001))
            wave[-release:] *= np.linspace(1, 0, release, dtype=np.float32)
            wave = np.clip(wave, -0.95, 0.95)
            samples = (wave * 32767).astype(np.int16)
            stereo = np.column_stack((samples, samples))
            return pygame.mixer.Sound(buffer=stereo.tobytes())

        # Metronome clicks with custom wavetable
        cf, cv, cw = vals["click_freq"], vals["click_vol"], vals["click_wave"]
        self.metronome._sounds[0] = _generate_custom(cf, 25, cv, cw)
        self.metronome._sounds[1] = _generate_custom(cf * 0.67, 30, cv * 0.85, cw)
        self.metronome._sounds[2] = _generate_custom(cf * 0.5, 35, cv * 0.7, cw)

        # Accent clicks
        af, av, aw = vals["accent_freq"], vals["accent_vol"], vals["accent_wave"]
        self.metronome._accent_sounds[0] = _generate_custom(af, 20, av, aw)
        self.metronome._accent_sounds[1] = _generate_custom(af * 0.67, 25, av * 0.85, aw)
        self.metronome._accent_sounds[2] = _generate_custom(af * 0.5, 28, av * 0.7, aw)

        # Hit sounds
        hf, hv, hw = vals["hit_freq"], vals["hit_vol"], vals["hit_wave"]
        self.hit_sounds._granular[HitRating.PERFECT] = _generate_custom(hf, 60, hv, hw, decay=25)
        self.hit_sounds._granular[HitRating.GOOD] = _generate_custom(hf * 0.75, 50, hv * 0.85, hw, decay=30)
        self.hit_sounds._granular[HitRating.OK] = _generate_custom(hf * 0.3, 40, hv * 0.7, hw, decay=50)
        self.hit_sounds._granular[HitRating.MISS] = _generate_custom(hf * 0.1, 70, hv * 0.6, hw, decay=20)
        self.hit_sounds._uniform_sound = _generate_custom(hf * 0.5, 35, hv, hw, decay=35)

    def _handle_playing_events(self, events: list[pygame.event.Event]):
        # If MIDI setup overlay is open, route events there
        if self.midi_setup.visible:
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                self.midi_setup.handle_event(event)
            return

        # If settings overlay is open, route events there
        if self.settings.visible:
            changed = False
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                if self.settings.handle_event(event):
                    changed = True
            if changed:
                self._apply_settings()
            return

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.settings.toggle()
                    return
                elif event.key == pygame.K_i:
                    self.midi_setup.toggle()
                    return
                elif event.key == pygame.K_ESCAPE:
                    self._stop_session()
                    self.menu.reset()
                    self.state = STATE_MENU
                elif event.key == pygame.K_TAB:
                    self.hud.toggle()
                elif event.key == pygame.K_v:
                    self.visual_mode_idx = (self.visual_mode_idx + 1) % len(self.visualizers)
                elif event.key == pygame.K_c:
                    self.crt.enabled = not self.crt.enabled
                elif event.key == pygame.K_h:
                    self.hit_sounds.toggle_mode()
                elif event.key == pygame.K_m:
                    self.metronome.muted = not self.metronome.muted
                elif event.key == pygame.K_s:
                    self.metronome.subdivisions_muted = not self.metronome.subdivisions_muted
                elif event.key == pygame.K_n:
                    idx = self._difficulty_keys.index(self.difficulty)
                    idx = (idx + 1) % len(self._difficulty_keys)
                    self.difficulty = self._difficulty_keys[idx]
                    set_difficulty(self.difficulty)
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
                    if event.key == pygame.K_BACKSLASH:
                        cur_sec = get_section_for_index(self.current_preset_idx)
                        next_sec = (cur_sec + 1) % len(SECTION_RANGES)
                        self._change_preset(SECTION_RANGES[next_sec][0])
                    elif event.key == pygame.K_LEFTBRACKET:
                        sec_start, sec_end, _ = SECTION_RANGES[get_section_for_index(self.current_preset_idx)]
                        new_idx = self.current_preset_idx - 1
                        if new_idx < sec_start:
                            new_idx = sec_end - 1
                        self._change_preset(new_idx)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        sec_start, sec_end, _ = SECTION_RANGES[get_section_for_index(self.current_preset_idx)]
                        new_idx = self.current_preset_idx + 1
                        if new_idx >= sec_end:
                            new_idx = sec_start
                        self._change_preset(new_idx)
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        sec_start, sec_end, _ = SECTION_RANGES[get_section_for_index(self.current_preset_idx)]
                        offset = event.key - pygame.K_1
                        preset_idx = sec_start + offset
                        if preset_idx < sec_end:
                            self._change_preset(preset_idx)

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

        if remaining > 0:
            text = str(remaining)
            color = (LAYER_COLORS[0] if remaining == 3 else
                     LAYER_COLORS[1] if remaining == 2 else LAYER_COLORS[2])
        else:
            text = "GO!"
            color = (0, 255, 128)

        surf = self._countdown_font.render(text, True, color)
        cx = SCREEN_WIDTH // 2 - surf.get_width() // 2
        cy = SCREEN_HEIGHT // 2 - surf.get_height() // 2
        self.screen.blit(surf, (cx, cy))

        info = self._countdown_info_font.render(
            f"{self.preset_name}  |  {self.bpm} BPM  |  {self._challenge_duration}s",
            True, (150, 150, 170)
        )
        self.screen.blit(info, (SCREEN_WIDTH // 2 - info.get_width() // 2,
                                 SCREEN_HEIGHT // 2 + 80))

        if elapsed >= 3.5:
            self.state = STATE_PLAYING
            self._start_session()

    def _render_session(self, dt: float, events: list[pygame.event.Event]):
        # Skip input processing when an overlay is open
        if not self.settings.visible and not self.midi_setup.visible:
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
            rhythm_desc=f"{self.preset_section} > {self.preset_name}",
            current_time=time.perf_counter(),
            visual_mode=mode_label,
            difficulty=self.difficulty,
        )

        self.crt.apply(self.screen)

        # Overlays (on top of everything)
        self.settings.render()
        self.midi_setup.render()

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
        self.midi_input.close()
        pygame.quit()


def main():
    app = App()
    app.run()


if __name__ == "__main__":
    main()
