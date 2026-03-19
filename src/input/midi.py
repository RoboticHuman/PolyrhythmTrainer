"""MIDI input handler using pygame.midi."""

import time
import threading
import pygame
import pygame.midi


class MidiInput:
    """Handles MIDI input from controllers using pygame.midi.

    Thread-safe: all shared state accessed through the lock.
    Public properties expose state without leaking internals.
    """

    def __init__(self):
        self._input = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._hit_buffer: list[tuple[int, float]] = []
        self._raw_note_buffer: list[int] = []
        self._lock = threading.Lock()
        self._disconnected = False

        self.note_to_layer: dict[int, int] = {}
        self.default_layer = 0

    # --- Public properties ---

    @property
    def connected(self) -> bool:
        """True if a device is open and the listener is running."""
        return self._input is not None and self._running

    @property
    def disconnected(self) -> bool:
        return self._disconnected

    @disconnected.setter
    def disconnected(self, value: bool):
        self._disconnected = value

    # --- Device management ---

    @staticmethod
    def available() -> bool:
        try:
            if not pygame.midi.get_init():
                pygame.midi.init()
            return pygame.midi.get_count() > 0
        except Exception:
            return False

    @staticmethod
    def list_devices() -> list[str]:
        try:
            if not pygame.midi.get_init():
                pygame.midi.init()
            devices = []
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[2]:  # is_input
                    devices.append(info[1].decode("utf-8", errors="replace"))
            return devices
        except Exception:
            return []

    def open(self, device_name: str | None = None) -> bool:
        """Open a MIDI input device by name."""
        try:
            if not pygame.midi.get_init():
                pygame.midi.init()

            device_id = None
            for i in range(pygame.midi.get_count()):
                info = pygame.midi.get_device_info(i)
                if info[2]:
                    name = info[1].decode("utf-8", errors="replace")
                    if device_name is None or name == device_name:
                        device_id = i
                        break

            if device_id is None:
                return False

            self._input = pygame.midi.Input(device_id)
            self._disconnected = False
            return True
        except Exception:
            return False

    def start(self):
        """Start the listener thread."""
        if not self._input or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the listener thread. Device stays open."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def close(self):
        """Stop listener and close the MIDI device."""
        self.stop()
        if self._input:
            try:
                self._input.close()
            except Exception:
                pass
            self._input = None

    def reconnect(self, device_name: str) -> bool:
        """Full close → reinit → reopen → start cycle."""
        self.close()
        pygame.midi.quit()
        pygame.midi.init()
        if self.open(device_name):
            self.start()
            return True
        return False

    # --- Data access (thread-safe) ---

    def get_hits(self) -> list[tuple[int, float]]:
        with self._lock:
            hits = self._hit_buffer[:]
            self._hit_buffer.clear()
        return hits

    def get_raw_notes(self) -> list[int]:
        with self._lock:
            notes = self._raw_note_buffer[:]
            self._raw_note_buffer.clear()
        return notes

    def set_layer_mapping(self, mapping: dict[int, int]):
        with self._lock:
            self.note_to_layer = mapping

    # --- Listener thread ---

    def _listen(self):
        error_count = 0
        while self._running and self._input:
            try:
                if self._input.poll():
                    events = self._input.read(32)
                    ts = time.perf_counter()
                    error_count = 0
                    with self._lock:
                        mapping = self.note_to_layer
                    for event in events:
                        data = event[0]
                        status = data[0]
                        note = data[1]
                        velocity = data[2]
                        if 0x90 <= status <= 0x9F and velocity > 0:
                            layer = mapping.get(note, self.default_layer)
                            with self._lock:
                                self._hit_buffer.append((layer, ts))
                                self._raw_note_buffer.append(note)
                else:
                    error_count = 0
            except Exception:
                error_count += 1
                if error_count > 50:
                    self._disconnected = True
                    self._running = False
                    try:
                        self._input.close()
                    except Exception:
                        pass
                    self._input = None
                    return
            time.sleep(0.001)
