"""Main menu — Freeplay, Challenge, Progression mode selection."""

import math
import time
import pygame
import random as _random
from src.config import PRESETS, VISUAL_MODES, SURPRISE_POOL
from src.visuals.colors import (
    BG_DARK, CYAN, MAGENTA, NEON_GREEN, YELLOW, HOT_PINK, PURPLE,
    TEXT_COLOR, TEXT_DIM
)
from src.engine.progression import (
    get_unlocked_preset_indices, get_preset_tier, TIERS
)


class MainMenu:
    """Main menu with mode selection and configuration."""

    # Menu states
    STATE_MAIN = "main"
    STATE_PRESET = "preset"
    STATE_DURATION = "duration"

    DURATIONS = [30, 60, 90]

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()

        self._font_title = pygame.font.SysFont("consolas", 48, bold=True)
        self._font_large = pygame.font.SysFont("consolas", 24, bold=True)
        self._font_med = pygame.font.SysFont("consolas", 18)
        self._font_small = pygame.font.SysFont("consolas", 14)

        # Menu state
        self.state = self.STATE_MAIN
        self.selected = 0
        self.mode = ""  # "freeplay", "challenge", "progression"

        # Configuration (output)
        self.chosen_preset_idx = 0  # default 3:2
        self.chosen_bpm = 120
        self.chosen_duration = 60
        self.chosen_visual = 0

        # Main menu options
        self._main_options = [
            ("Freeplay", "Infinite practice — no timer, no score", CYAN),
            ("Challenge", "Timed rounds with scoring and grades", MAGENTA),
            ("Progression", "Unlock harder rhythms by mastering easier ones", NEON_GREEN),
            ("Surprise Me!", "Random preset — test your adaptability", YELLOW),
        ]

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Handle a key event. Returns action string or None.

        Actions: 'start_freeplay', 'start_challenge', 'start_progression', None
        """
        if event.type != pygame.KEYDOWN:
            return None

        if self.state == self.STATE_MAIN:
            return self._handle_main(event)
        elif self.state == self.STATE_PRESET:
            return self._handle_preset(event)
        elif self.state == self.STATE_DURATION:
            return self._handle_duration(event)
        return None

    def _handle_main(self, event: pygame.event.Event) -> str | None:
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self._main_options)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self._main_options)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            modes = ["freeplay", "challenge", "progression", "surprise"]
            self.mode = modes[self.selected]
            if self.mode == "surprise":
                # Pick a random preset and go straight to freeplay
                self.chosen_preset_idx = _random.choice(SURPRISE_POOL)
                self.mode = "freeplay"
                return "start_freeplay"
            self.state = self.STATE_PRESET
            self.selected = self.chosen_preset_idx
        return None

    def _handle_preset(self, event: pygame.event.Event) -> str | None:
        unlocked = get_unlocked_preset_indices()

        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(PRESETS)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(PRESETS)
        elif event.key == pygame.K_LEFT:
            self.chosen_bpm = max(40, self.chosen_bpm - 5)
        elif event.key == pygame.K_RIGHT:
            self.chosen_bpm = min(300, self.chosen_bpm + 5)
        elif event.key == pygame.K_v:
            self.chosen_visual = (self.chosen_visual + 1) % len(VISUAL_MODES)
        elif event.key == pygame.K_ESCAPE:
            self.state = self.STATE_MAIN
            self.selected = 0
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            # Check if preset is unlocked (in progression mode)
            if self.mode == "progression" and self.selected not in unlocked:
                return None  # Can't select locked preset
            self.chosen_preset_idx = self.selected
            if self.mode == "freeplay":
                return "start_freeplay"
            elif self.mode in ("challenge", "progression"):
                self.state = self.STATE_DURATION
                self.selected = 1  # Default 60s
        return None

    def _handle_duration(self, event: pygame.event.Event) -> str | None:
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.DURATIONS)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self.DURATIONS)
        elif event.key == pygame.K_ESCAPE:
            self.state = self.STATE_PRESET
            self.selected = self.chosen_preset_idx
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.chosen_duration = self.DURATIONS[self.selected]
            action = "start_challenge" if self.mode == "challenge" else "start_progression"
            return action
        return None

    def reset(self):
        """Return to main menu."""
        self.state = self.STATE_MAIN
        self.selected = 0

    def render(self):
        self.surface.fill(BG_DARK)

        if self.state == self.STATE_MAIN:
            self._render_main()
        elif self.state == self.STATE_PRESET:
            self._render_preset()
        elif self.state == self.STATE_DURATION:
            self._render_duration()

    def _render_main(self):
        cx = self.width // 2
        y = 100

        # Animated title
        t = time.perf_counter()
        title_text = "POLYRHYTHM TRAINER"
        title = self._font_title.render(title_text, True, CYAN)
        # Slight pulse
        scale = 1.0 + math.sin(t * 2) * 0.02
        tw = int(title.get_width() * scale)
        th = int(title.get_height() * scale)
        title_scaled = pygame.transform.scale(title, (tw, th))
        self.surface.blit(title_scaled, (cx - tw // 2, y))
        y += 100

        # Subtitle
        sub = self._font_small.render("Master rhythm. Feel the polyrhythm.", True, TEXT_DIM)
        self.surface.blit(sub, (cx - sub.get_width() // 2, y))
        y += 60

        # Options
        for i, (label, desc, color) in enumerate(self._main_options):
            is_sel = (i == self.selected)
            # Selection indicator
            if is_sel:
                indicator_x = cx - 180
                pygame.draw.polygon(self.surface, color,
                                    [(indicator_x, y + 12), (indicator_x + 10, y + 6),
                                     (indicator_x + 10, y + 18)])

            label_color = color if is_sel else TEXT_DIM
            label_surf = self._font_large.render(label, True, label_color)
            self.surface.blit(label_surf, (cx - 160, y))

            desc_surf = self._font_small.render(desc, True, TEXT_DIM if not is_sel else TEXT_COLOR)
            self.surface.blit(desc_surf, (cx - 160, y + 28))
            y += 65

        # Controls
        controls = self._font_small.render(
            "Up/Down: Select  |  Enter: Confirm  |  Esc: Quit", True, TEXT_DIM
        )
        self.surface.blit(controls, (cx - controls.get_width() // 2, self.height - 40))

    def _render_preset(self):
        cx = self.width // 2
        y = 40

        # Header
        mode_labels = {"freeplay": "FREEPLAY", "challenge": "CHALLENGE", "progression": "PROGRESSION"}
        mode_colors = {"freeplay": CYAN, "challenge": MAGENTA, "progression": NEON_GREEN}
        header = self._font_large.render(
            f"{mode_labels.get(self.mode, '')} — Select Preset", True,
            mode_colors.get(self.mode, CYAN)
        )
        self.surface.blit(header, (cx - header.get_width() // 2, y))
        y += 50

        # BPM and visual mode
        config_text = f"BPM: {self.chosen_bpm}  (Left/Right)   |   Visual: {VISUAL_MODES[self.chosen_visual]}  (V)"
        config = self._font_small.render(config_text, True, TEXT_COLOR)
        self.surface.blit(config, (cx - config.get_width() // 2, y))
        y += 35

        # Preset list
        unlocked = get_unlocked_preset_indices()

        # Show a scrolling window of presets
        visible = 10
        start = max(0, self.selected - visible // 2)
        start = min(start, max(0, len(PRESETS) - visible))

        # Category colors
        cat_colors = {
            "basics": (100, 100, 120), "odd": (120, 100, 80),
            "poly": CYAN, "poly-grouped": MAGENTA,
            "advanced": HOT_PINK, "world": YELLOW,
        }

        for i in range(start, min(start + visible, len(PRESETS))):
            preset = PRESETS[i]
            name = preset[0]
            category = preset[3] if len(preset) > 3 else ""
            is_sel = (i == self.selected)
            is_locked = (self.mode == "progression" and i not in unlocked)
            tier = get_preset_tier(i)
            tier_str = f"T{tier}" if tier else ""
            cat_tag = f"[{category}]" if category else ""

            if is_locked:
                label = f"  {tier_str}  {name} [LOCKED]"
                color = (50, 40, 50)
            else:
                label = f"  {tier_str}  {name}"
                cat_c = cat_colors.get(category, TEXT_COLOR)
                color = cat_c if is_sel else TEXT_COLOR

            if is_sel:
                # Highlight bar
                bar_color = (30, 20, 40) if is_locked else (20, 30, 50)
                pygame.draw.rect(self.surface, bar_color,
                                 (cx - 200, y - 2, 400, 26), border_radius=4)
                # Arrow
                pygame.draw.polygon(self.surface, color,
                                    [(cx - 195, y + 10), (cx - 188, y + 5), (cx - 188, y + 15)])

            surf = self._font_med.render(label, True, color)
            self.surface.blit(surf, (cx - 180, y))
            y += 28

        # Controls
        controls = self._font_small.render(
            "Up/Down: Select  |  Left/Right: BPM  |  V: Visual  |  Enter: Start  |  Esc: Back",
            True, TEXT_DIM
        )
        self.surface.blit(controls, (cx - controls.get_width() // 2, self.height - 40))

    def _render_duration(self):
        cx = self.width // 2
        y = 150

        header = self._font_large.render("Select Duration", True, MAGENTA)
        self.surface.blit(header, (cx - header.get_width() // 2, y))
        y += 60

        preset_name = PRESETS[self.chosen_preset_idx][0]
        info = self._font_med.render(
            f"{preset_name}  |  {self.chosen_bpm} BPM", True, TEXT_COLOR
        )
        self.surface.blit(info, (cx - info.get_width() // 2, y))
        y += 50

        for i, dur in enumerate(self.DURATIONS):
            is_sel = (i == self.selected)
            label = f"{dur} seconds"
            color = CYAN if is_sel else TEXT_DIM

            if is_sel:
                pygame.draw.rect(self.surface, (20, 30, 50),
                                 (cx - 100, y - 4, 200, 32), border_radius=6)
                pygame.draw.polygon(self.surface, color,
                                    [(cx - 95, y + 10), (cx - 88, y + 5), (cx - 88, y + 15)])

            surf = self._font_large.render(label, True, color)
            self.surface.blit(surf, (cx - surf.get_width() // 2, y))
            y += 50

        controls = self._font_small.render(
            "Up/Down: Select  |  Enter: Start  |  Esc: Back", True, TEXT_DIM
        )
        self.surface.blit(controls, (cx - controls.get_width() // 2, self.height - 40))
