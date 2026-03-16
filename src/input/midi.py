"""MIDI input handler using mido."""

import time
import threading

try:
    import mido
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False


class MidiInput:
    """Handles MIDI input from controllers like the Arturia Keystep 37.

    Uses mido for MIDI message parsing and device access.
    Runs a listener thread to capture note-on events with precise timestamps.
    """

    def __init__(self):
        self._port = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._hit_buffer: list[tuple[int, float]] = []
        self._lock = threading.Lock()

        # Default: any note-on maps to layer 0
        # Can be customized: MIDI note number -> layer index
        self.note_to_layer: dict[int, int] = {}
        self.default_layer = 0

    @staticmethod
    def available() -> bool:
        return MIDI_AVAILABLE

    @staticmethod
    def list_devices() -> list[str]:
        if not MIDI_AVAILABLE:
            return []
        try:
            return mido.get_input_names()
        except Exception:
            return []

    def open(self, device_name: str | None = None) -> bool:
        """Open a MIDI input port.

        Args:
            device_name: Name of the MIDI device, or None to open first available.

        Returns:
            True if successfully opened.
        """
        if not MIDI_AVAILABLE:
            return False

        try:
            if device_name:
                self._port = mido.open_input(device_name)
            else:
                self._port = mido.open_input()
            return True
        except Exception:
            return False

    def start(self):
        """Start the MIDI listener thread."""
        if not self._port:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._port:
            self._port.close()
            self._port = None

    def _listen(self):
        """Background thread: read MIDI messages and buffer hits."""
        while self._running and self._port:
            try:
                for msg in self._port.iter_pending():
                    if msg.type == "note_on" and msg.velocity > 0:
                        ts = time.perf_counter()
                        layer = self.note_to_layer.get(msg.note, self.default_layer)
                        with self._lock:
                            self._hit_buffer.append((layer, ts))
            except Exception:
                pass
            time.sleep(0.001)  # 1ms poll

    def get_hits(self) -> list[tuple[int, float]]:
        """Drain and return buffered hits as (layer_index, timestamp)."""
        with self._lock:
            hits = self._hit_buffer[:]
            self._hit_buffer.clear()
        return hits

    def set_layer_mapping(self, mapping: dict[int, int]):
        """Set MIDI note -> layer mapping.

        Args:
            mapping: Dict of {midi_note_number: layer_index}
        """
        self.note_to_layer = mapping
