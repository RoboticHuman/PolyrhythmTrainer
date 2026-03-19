"""Settings overlay — wavetable sound designer with draggable waveform points."""

import json
import math
import os
import pygame
from src.visuals.colors import (
    CYAN, NEON_GREEN, YELLOW, HOT_PINK, TEXT_COLOR, TEXT_DIM
)

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "sound_settings.json")


class WaveControl:
    """Interactive wavetable editor.

    Click and drag on the waveform to paint custom wave shapes.
    Left/Right arrows adjust frequency, PgUp/PgDn adjust volume.
    R resets to sine.
    """

    N_POINTS = 64

    def __init__(self, x: int, y: int, w: int, h: int, label: str,
                 freq: float, min_freq: float, max_freq: float,
                 vol: float, min_vol: float, max_vol: float,
                 color: tuple):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.label = label
        self.freq = freq
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.vol = vol
        self.min_vol = min_vol
        self.max_vol = max_vol
        self.color = color
        self.selected = False

        self.points = [math.sin(i / self.N_POINTS * math.pi * 2)
                       for i in range(self.N_POINTS)]

        self._dragging = False
        self._hovering_point = -1

    def _wave_area(self) -> tuple[int, int, int, int]:
        return (self.x + 8, self.y + 18, self.w - 16, self.h - 24)

    def _point_screen_pos(self, idx: int) -> tuple[int, int]:
        wx, wy, ww, wh = self._wave_area()
        mid_y = wy + wh // 2
        px = wx + int(idx / self.N_POINTS * ww)
        py = mid_y - int(self.points[idx] * wh * 0.4 * self.vol_normalized)
        return (px, py)

    def _find_nearest_point(self, mx: int, my: int, max_dist: int = 15) -> int:
        best = -1
        best_d = max_dist
        for i in range(self.N_POINTS):
            px, py = self._point_screen_pos(i)
            d = math.sqrt((mx - px) ** 2 + (my - py) ** 2)
            if d < best_d:
                best_d = d
                best = i
        return best

    @property
    def freq_normalized(self) -> float:
        return (self.freq - self.min_freq) / max(1, self.max_freq - self.min_freq)

    @property
    def vol_normalized(self) -> float:
        return max(0.01, (self.vol - self.min_vol) / max(0.001, self.max_vol - self.min_vol))

    def get_wavetable(self) -> list[float]:
        return self.points[:]

    def reset_sine(self):
        self.points = [math.sin(i / self.N_POINTS * math.pi * 2)
                       for i in range(self.N_POINTS)]

    def _set_point_at(self, mx: int, my: int):
        wx, wy, ww, wh = self._wave_area()
        mid_y = wy + wh // 2
        amp = wh * 0.4 * self.vol_normalized
        if ww <= 0 or amp <= 0:
            return
        t = (mx - wx) / ww
        idx = max(0, min(self.N_POINTS - 1, int(t * self.N_POINTS)))
        val = max(-1.0, min(1.0, -(my - mid_y) / amp))
        self.points[idx] = val

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        x, y, w, h = self.x, self.y, self.w, self.h
        wx, wy, ww, wh = self._wave_area()
        mid_y = wy + wh // 2

        bg = (35, 28, 50) if self.selected else (22, 18, 32)
        pygame.draw.rect(surface, bg, (x, y, w, h), border_radius=6)
        border = self.color if self.selected else (40, 32, 50)
        pygame.draw.rect(surface, border, (x, y, w, h), 1, border_radius=6)

        label_c = self.color if self.selected else TEXT_DIM
        label_surf = font.render(self.label, True, label_c)
        surface.blit(label_surf, (x + 8, y + 2))

        val_text = f"{int(self.freq)}Hz  {int(self.vol * 100)}%"
        val_surf = font.render(val_text, True, TEXT_COLOR)
        surface.blit(val_surf, (x + w - val_surf.get_width() - 8, y + 2))

        # Center line
        pygame.draw.line(surface, (30, 25, 40), (wx, mid_y), (wx + ww, mid_y), 1)

        # Waveform curve
        amp = wh * 0.4 * self.vol_normalized
        r = min(255, int(self.color[0] * (0.5 + 0.5 * self.vol_normalized)))
        g = min(255, int(self.color[1] * (0.5 + 0.5 * self.vol_normalized)))
        b = min(255, int(self.color[2] * (0.4 + 0.6 * self.vol_normalized)))
        wave_color = (r, g, b)

        prev_sx, prev_sy = wx, mid_y
        for px in range(ww):
            t = px / ww * self.N_POINTS
            idx = int(t) % self.N_POINTS
            next_idx = (idx + 1) % self.N_POINTS
            frac = t - int(t)
            val = self.points[idx] * (1 - frac) + self.points[next_idx] * frac
            sx = wx + px
            sy = mid_y - int(val * amp)
            pygame.draw.line(surface, wave_color, (prev_sx, prev_sy), (sx, sy), 2)
            prev_sx, prev_sy = sx, sy

        # Control point dots (every 2nd)
        for i in range(0, self.N_POINTS, 2):
            ppx, ppy = self._point_screen_pos(i)
            is_hover = (i == self._hovering_point)
            pr = 4 if is_hover else 2
            pc = tuple(min(255, c + 60) for c in self.color) if is_hover else tuple(c // 2 for c in self.color)
            pygame.draw.circle(surface, pc, (ppx, ppy), pr)

        if self.selected and not self._dragging:
            hint = font.render("draw on wave  |  R: reset", True, (50, 45, 65))
            surface.blit(hint, (wx + ww // 2 - hint.get_width() // 2, wy + wh - 10))

    def handle_event(self, event: pygame.event.Event) -> bool:
        wx, wy, ww, wh = self._wave_area()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if not (wx <= mx <= wx + ww and wy <= my <= wy + wh):
                return False
            self._dragging = True
            self._set_point_at(mx, my)
            return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if self._dragging:
                self._dragging = False
                return True

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if wx <= mx <= wx + ww and wy <= my <= wy + wh:
                self._hovering_point = self._find_nearest_point(mx, my, max_dist=15)
            else:
                self._hovering_point = -1
            if self._dragging:
                self._set_point_at(mx, my)
                return True

        return False

    def adjust_freq(self, delta: float):
        self.freq = max(self.min_freq, min(self.max_freq, self.freq + delta))

    def adjust_vol(self, delta: float):
        self.vol = max(self.min_vol, min(self.max_vol, self.vol + delta))


class SettingsOverlay:
    """Full-screen settings overlay with wavetable sound designer.
    Changes apply immediately as you adjust — no apply button needed.
    """

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()
        self.visible = False

        self._font = pygame.font.SysFont("consolas", 12, bold=True)
        self._font_title = pygame.font.SysFont("consolas", 22, bold=True)
        self._font_small = pygame.font.SysFont("consolas", 11)

        self._overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 180))

        panel_w = 540
        panel_h = 400
        self._panel_x = (self.width - panel_w) // 2
        self._panel_y = (self.height - panel_h) // 2
        self._panel_w = panel_w
        self._panel_h = panel_h

        ctrl_w = panel_w - 40
        ctrl_h = 100
        ctrl_x = self._panel_x + 20
        y = self._panel_y + 50

        self._selected = 0
        self.controls: list[WaveControl] = [
            WaveControl(ctrl_x, y, ctrl_w, ctrl_h,
                        "Metronome Click",
                        freq=1200, min_freq=200, max_freq=3000,
                        vol=0.35, min_vol=0.0, max_vol=1.0,
                        color=CYAN),
            WaveControl(ctrl_x, y + ctrl_h + 8, ctrl_w, ctrl_h,
                        "Accent Click",
                        freq=1500, min_freq=400, max_freq=4000,
                        vol=0.55, min_vol=0.0, max_vol=1.0,
                        color=YELLOW),
            WaveControl(ctrl_x, y + (ctrl_h + 8) * 2, ctrl_w, ctrl_h,
                        "Hit Feedback",
                        freq=2000, min_freq=300, max_freq=4000,
                        vol=0.35, min_vol=0.0, max_vol=1.0,
                        color=NEON_GREEN),
        ]
        self.controls[0].selected = True

        # Store defaults for reset
        self._defaults = [
            {"freq": c.freq, "vol": c.vol, "points": c.points[:]}
            for c in self.controls
        ]

        # Load saved settings if they exist
        self._load()

    def _save(self):
        """Persist current settings to disk."""
        data = []
        for ctrl in self.controls:
            data.append({
                "freq": ctrl.freq,
                "vol": ctrl.vol,
                "points": ctrl.points,
            })
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w") as f:
            json.dump(data, f)

    def _load(self):
        """Load saved settings from disk."""
        try:
            with open(SETTINGS_PATH, "r") as f:
                data = json.load(f)
            for i, ctrl in enumerate(self.controls):
                if i < len(data):
                    ctrl.freq = data[i].get("freq", ctrl.freq)
                    ctrl.vol = data[i].get("vol", ctrl.vol)
                    saved_points = data[i].get("points")
                    if saved_points and len(saved_points) == ctrl.N_POINTS:
                        ctrl.points = saved_points
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def reset_defaults(self):
        """Reset all controls to factory defaults."""
        for i, ctrl in enumerate(self.controls):
            d = self._defaults[i]
            ctrl.freq = d["freq"]
            ctrl.vol = d["vol"]
            ctrl.points = d["points"][:]
        # Delete saved file
        try:
            os.remove(SETTINGS_PATH)
        except FileNotFoundError:
            pass

    def toggle(self):
        self.visible = not self.visible
        if not self.visible:
            self._save()

    def get_values(self) -> dict:
        return {
            "click_freq": self.controls[0].freq,
            "click_vol": self.controls[0].vol,
            "click_wave": self.controls[0].get_wavetable(),
            "accent_freq": self.controls[1].freq,
            "accent_vol": self.controls[1].vol,
            "accent_wave": self.controls[1].get_wavetable(),
            "hit_freq": self.controls[2].freq,
            "hit_vol": self.controls[2].vol,
            "hit_wave": self.controls[2].get_wavetable(),
        }

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.visible = False
                self._save()
                return True
            elif event.key == pygame.K_d:
                self.reset_defaults()
                return True
            elif event.key == pygame.K_UP:
                self.controls[self._selected].selected = False
                self._selected = (self._selected - 1) % len(self.controls)
                self.controls[self._selected].selected = True
                return True
            elif event.key == pygame.K_DOWN:
                self.controls[self._selected].selected = False
                self._selected = (self._selected + 1) % len(self.controls)
                self.controls[self._selected].selected = True
                return True
            elif event.key == pygame.K_LEFT:
                self.controls[self._selected].adjust_freq(-50)
                return True
            elif event.key == pygame.K_RIGHT:
                self.controls[self._selected].adjust_freq(50)
                return True
            elif event.key == pygame.K_PAGEUP:
                self.controls[self._selected].adjust_vol(0.05)
                return True
            elif event.key == pygame.K_PAGEDOWN:
                self.controls[self._selected].adjust_vol(-0.05)
                return True
            elif event.key == pygame.K_r:
                self.controls[self._selected].reset_sine()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            for i, ctrl in enumerate(self.controls):
                if ctrl.handle_event(event):
                    self.controls[self._selected].selected = False
                    self._selected = i
                    ctrl.selected = True
                    return True

        elif event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            for ctrl in self.controls:
                if ctrl.handle_event(event):
                    return True

        return True  # Consume all events when open

    def render(self):
        if not self.visible:
            return

        self.surface.blit(self._overlay, (0, 0))

        px, py, pw, ph = self._panel_x, self._panel_y, self._panel_w, self._panel_h
        pygame.draw.rect(self.surface, (18, 14, 25), (px, py, pw, ph), border_radius=10)
        pygame.draw.rect(self.surface, (50, 40, 65), (px, py, pw, ph), 2, border_radius=10)

        title = self._font_title.render("SOUND DESIGNER", True, CYAN)
        self.surface.blit(title, (px + pw // 2 - title.get_width() // 2, py + 15))

        for ctrl in self.controls:
            ctrl.draw(self.surface, self._font)

        hint = self._font_small.render(
            "Draw wave  |  \u2190\u2192 freq  PgUp/Dn vol  |  R: reset wave  D: defaults  |  P/Esc: close",
            True, TEXT_DIM
        )
        self.surface.blit(hint, (px + pw // 2 - hint.get_width() // 2, py + ph - 18))
