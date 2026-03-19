"""MIDI setup overlay — device dropdown and layer mapping."""

import math
import time
import pygame
import pygame.midi
from src.visuals.colors import (
    CYAN, MAGENTA, NEON_GREEN, YELLOW, HOT_PINK, TEXT_COLOR, TEXT_DIM
)
from src.config import LAYER_KEY_LABELS

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def midi_note_name(note: int) -> str:
    octave = (note // 12) - 1
    return f"{NOTE_NAMES[note % 12]}{octave}"


class Dropdown:
    """A clickable dropdown selector."""

    def __init__(self, x: int, y: int, w: int, h: int, font: pygame.font.Font,
                 color: tuple = CYAN):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.font = font
        self.color = color
        self.options: list[str] = []
        self.selected_idx = -1
        self.open = False
        self._hover_idx = -1

    @property
    def selected_text(self) -> str:
        if 0 <= self.selected_idx < len(self.options):
            return self.options[self.selected_idx]
        return ""

    def set_options(self, options: list[str], selected: int = -1):
        self.options = options
        self.selected_idx = selected
        self.open = False

    def draw_box(self, surface: pygame.Surface):
        x, y, w, h = self.x, self.y, self.w, self.h
        bg = (30, 25, 45) if self.open else (22, 18, 32)
        pygame.draw.rect(surface, bg, (x, y, w, h), border_radius=4)
        pygame.draw.rect(surface, self.color if self.open else (50, 42, 60),
                         (x, y, w, h), 1, border_radius=4)

        if self.selected_idx >= 0:
            text = self.font.render(self.selected_text, True, TEXT_COLOR)
        else:
            text = self.font.render("Select device...", True, TEXT_DIM)
        surface.blit(text, (x + 10, y + h // 2 - text.get_height() // 2))

        arrow_x = x + w - 20
        arrow_y = y + h // 2
        if self.open:
            pygame.draw.polygon(surface, self.color,
                                [(arrow_x, arrow_y + 3), (arrow_x - 5, arrow_y - 3),
                                 (arrow_x + 5, arrow_y - 3)])
        else:
            pygame.draw.polygon(surface, TEXT_DIM,
                                [(arrow_x, arrow_y - 3), (arrow_x - 5, arrow_y + 3),
                                 (arrow_x + 5, arrow_y + 3)])

    def draw_list(self, surface: pygame.Surface):
        if not self.open or not self.options:
            return
        x, y, w, h = self.x, self.y, self.w, self.h
        list_h = len(self.options) * 28 + 4
        list_y = y + h + 2

        pygame.draw.rect(surface, (8, 6, 12),
                         (x + 2, list_y + 2, w, list_h), border_radius=4)
        pygame.draw.rect(surface, (20, 16, 30),
                         (x, list_y, w, list_h), border_radius=4)
        pygame.draw.rect(surface, (50, 42, 60),
                         (x, list_y, w, list_h), 1, border_radius=4)

        for i, opt in enumerate(self.options):
            iy = list_y + 2 + i * 28
            is_hover = (i == self._hover_idx)
            is_sel = (i == self.selected_idx)

            if is_hover:
                pygame.draw.rect(surface, (35, 30, 55),
                                 (x + 2, iy, w - 4, 26), border_radius=3)

            tc = self.color if is_sel else (TEXT_COLOR if is_hover else TEXT_DIM)
            opt_surf = self.font.render(opt, True, tc)
            surface.blit(opt_surf, (x + 10, iy + 4))

            if is_sel:
                check = self.font.render("✓", True, NEON_GREEN)
                surface.blit(check, (x + w - 25, iy + 4))

    def handle_event(self, event: pygame.event.Event) -> int | None:
        x, y, w, h = self.x, self.y, self.w, self.h

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if x <= mx <= x + w and y <= my <= y + h:
                self.open = not self.open
                return None
            if self.open:
                list_y = y + h + 2
                for i in range(len(self.options)):
                    iy = list_y + 2 + i * 28
                    if x <= mx <= x + w and iy <= my <= iy + 26:
                        self.selected_idx = i
                        self.open = False
                        return i
                self.open = False

        elif event.type == pygame.MOUSEMOTION and self.open:
            mx, my = event.pos
            list_y = y + h + 2
            self._hover_idx = -1
            for i in range(len(self.options)):
                iy = list_y + 2 + i * 28
                if x <= mx <= x + w and iy <= my <= iy + 26:
                    self._hover_idx = i

        elif event.type == pygame.KEYDOWN and self.open:
            if event.key == pygame.K_UP:
                self._hover_idx = max(0, self._hover_idx - 1)
            elif event.key == pygame.K_DOWN:
                self._hover_idx = min(len(self.options) - 1, self._hover_idx + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if 0 <= self._hover_idx < len(self.options):
                    self.selected_idx = self._hover_idx
                    self.open = False
                    return self.selected_idx
            elif event.key == pygame.K_ESCAPE:
                self.open = False

        return None


class MidiSetup:
    """MIDI device selector and note-to-layer mapper.

    Uses only public MidiInput APIs — no private field access.
    """

    LAYER_COLORS = [CYAN, MAGENTA, NEON_GREEN]

    def __init__(self, surface: pygame.Surface, midi_input):
        self.surface = surface
        self.width = surface.get_width()
        self.height = surface.get_height()
        self.visible = False
        self.midi_input = midi_input

        self._font = pygame.font.SysFont("consolas", 13, bold=True)
        self._font_title = pygame.font.SysFont("consolas", 22, bold=True)
        self._font_small = pygame.font.SysFont("consolas", 11)
        self._font_note = pygame.font.SysFont("consolas", 16, bold=True)

        self._overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 180))

        panel_w = 480
        panel_h = 380
        self._px = (self.width - panel_w) // 2
        self._py = (self.height - panel_h) // 2
        self._pw = panel_w
        self._ph = panel_h

        self._dropdown = Dropdown(
            self._px + 20, self._py + 75, panel_w - 40, 30, self._font, CYAN
        )
        self._devices_raw: list[str] = []

        self._num_layers = 3
        self._layer_notes: dict[int, list[int]] = {0: [], 1: [], 2: []}
        self._listening_layer = -1
        self._selected_layer = 0
        self.connected_name = ""  # Track which device is connected

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self._listening_layer = -1
            self._dropdown.open = False
            self._refresh_devices()

    def _refresh_devices(self):
        """Rescan devices. Reconnects to tracked device if available."""
        # MUST stop listener before reiniting pygame.midi to avoid segfault
        self.midi_input.close()

        try:
            pygame.midi.quit()
            pygame.midi.init()
        except Exception:
            pass

        self._devices_raw = self.midi_input.list_devices()

        # Reconnect to tracked device
        new_sel = -1
        if self.connected_name and self.connected_name in self._devices_raw:
            if self.midi_input.open(self.connected_name):
                self.midi_input.start()
                new_sel = self._devices_raw.index(self.connected_name)
        elif self.connected_name:
            self.midi_input.disconnected = True

        self._dropdown.set_options(self._devices_raw, selected=new_sel)

    def _connect_device(self, device_name: str):
        """Connect to a MIDI device by name."""
        if self.midi_input.reconnect(device_name):
            self.connected_name = device_name

    def _apply_mapping(self):
        mapping = {}
        for layer, notes in self._layer_notes.items():
            for note in notes:
                mapping[note] = layer
        self.midi_input.set_layer_mapping(mapping)

    def _check_midi_input(self):
        if self._listening_layer < 0:
            return
        raw_notes = self.midi_input.get_raw_notes()
        if raw_notes:
            note = raw_notes[0]
            layer = self._listening_layer
            if note not in self._layer_notes[layer]:
                self._layer_notes[layer].append(note)
            self._apply_mapping()
            self._listening_layer = -1
            self.midi_input.get_hits()  # Drain so it doesn't trigger gameplay

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_i) and not self._dropdown.open:
                self.visible = False
                self._listening_layer = -1
                return True
            if self._listening_layer >= 0:
                if event.key == pygame.K_BACKSPACE:
                    self._listening_layer = -1
                return True
            if event.key == pygame.K_F5:
                self._refresh_devices()
                return True

        if self._dropdown.open:
            result = self._dropdown.handle_event(event)
            if result is not None and result < len(self._devices_raw):
                self._connect_device(self._devices_raw[result])
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            result = self._dropdown.handle_event(event)
            if result is not None and result < len(self._devices_raw):
                self._connect_device(self._devices_raw[result])
                return True
            if self._dropdown.open:
                return True

            mx, my = event.pos
            layer_y_start = self._py + 145
            for i in range(self._num_layers):
                ly = layer_y_start + i * 65
                if (self._px + 20 <= mx <= self._px + self._pw - 20 and
                        ly <= my <= ly + 58):
                    self._selected_layer = i
                    if mx > self._px + self._pw - 80:
                        self._layer_notes[i] = []
                        self._apply_mapping()
                    else:
                        self._listening_layer = i
                    return True

        elif event.type == pygame.MOUSEMOTION:
            self._dropdown.handle_event(event)

        return True

    def render(self):
        if not self.visible:
            return

        self._check_midi_input()

        self.surface.blit(self._overlay, (0, 0))

        px, py, pw, ph = self._px, self._py, self._pw, self._ph
        pygame.draw.rect(self.surface, (18, 14, 25), (px, py, pw, ph), border_radius=10)
        pygame.draw.rect(self.surface, (50, 40, 65), (px, py, pw, ph), 2, border_radius=10)

        title = self._font_title.render("MIDI SETTINGS", True, CYAN)
        self.surface.blit(title, (px + pw // 2 - title.get_width() // 2, py + 12))

        dev_label = self._font.render("Device  (F5 to refresh)", True, TEXT_COLOR)
        self.surface.blit(dev_label, (px + 20, py + 55))

        self._dropdown.draw_box(self.surface)

        # Connection status
        if self.midi_input.disconnected:
            status = self._font_small.render("● disconnected — turn on device and press F5", True, HOT_PINK)
            self.surface.blit(status, (px + pw - status.get_width() - 20, py + 57))
            self._dropdown.selected_idx = -1
        elif self.midi_input.connected:
            status = self._font_small.render("● connected", True, NEON_GREEN)
            self.surface.blit(status, (px + pw - status.get_width() - 20, py + 57))
        elif not self._devices_raw:
            status = self._font_small.render("No MIDI devices found", True, TEXT_DIM)
            self.surface.blit(status, (px + pw - status.get_width() - 20, py + 57))

        # Layer mapping section
        layer_label = self._font.render("Layer Mapping  (click to assign MIDI key)", True, TEXT_COLOR)
        self.surface.blit(layer_label, (px + 20, py + 122))

        layer_y = py + 145
        for i in range(self._num_layers):
            is_sel = (i == self._selected_layer)
            is_listening = (i == self._listening_layer)
            color = self.LAYER_COLORS[i % len(self.LAYER_COLORS)]

            if is_listening:
                pulse = (math.sin(time.perf_counter() * 6) + 1) / 2
                bg = (int(25 + 15 * pulse), int(22 + 12 * pulse), int(40 + 15 * pulse))
            elif is_sel:
                bg = (28, 24, 42)
            else:
                bg = (20, 16, 30)

            pygame.draw.rect(self.surface, bg,
                             (px + 20, layer_y, pw - 40, 58), border_radius=6)
            pygame.draw.rect(self.surface, color if is_sel else (35, 28, 45),
                             (px + 20, layer_y, pw - 40, 58), 1, border_radius=6)

            key_label = LAYER_KEY_LABELS.get(i, "")
            lbl = self._font.render(f"Layer {i}  ({key_label})", True, color)
            self.surface.blit(lbl, (px + 32, layer_y + 5))

            if is_listening:
                prompt = self._font_note.render("▶ Press a MIDI key...", True, YELLOW)
                self.surface.blit(prompt, (px + 32, layer_y + 28))
            else:
                notes = self._layer_notes.get(i, [])
                if notes:
                    note_str = "  ".join(midi_note_name(n) for n in notes)
                    note_surf = self._font_note.render(note_str, True, TEXT_COLOR)
                    self.surface.blit(note_surf, (px + 32, layer_y + 28))
                else:
                    empty = self._font_small.render("No MIDI notes — click to assign", True, (55, 48, 60))
                    self.surface.blit(empty, (px + 32, layer_y + 32))

            if self._layer_notes.get(i):
                clear_x = px + pw - 75
                clear_y = layer_y + 18
                pygame.draw.rect(self.surface, (50, 30, 35),
                                 (clear_x, clear_y, 45, 22), border_radius=4)
                pygame.draw.rect(self.surface, HOT_PINK,
                                 (clear_x, clear_y, 45, 22), 1, border_radius=4)
                clear_text = self._font_small.render("clear", True, HOT_PINK)
                self.surface.blit(clear_text,
                                  (clear_x + 22 - clear_text.get_width() // 2,
                                   clear_y + 11 - clear_text.get_height() // 2))

            layer_y += 65

        hint = self._font_small.render(
            "Click layer to assign  |  F5: refresh  |  I/Esc: close",
            True, TEXT_DIM
        )
        self.surface.blit(hint, (px + pw // 2 - hint.get_width() // 2, py + ph - 18))

        # Dropdown list on top of everything
        self._dropdown.draw_list(self.surface)
