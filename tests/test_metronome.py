"""Test that the metronome fires the correct number of beats in real time.

These tests run the metronome in real time and are slow (~45s total).
Run with: uv run pytest -m realtime
"""

import time
import pytest
import pygame
from src.audio.metronome import Metronome
from src.engine.rhythm import PolyrhythmSession

pytestmark = pytest.mark.realtime


@pytest.fixture(scope="module", autouse=True)
def pygame_mixer():
    pygame.init()
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    yield
    pygame.quit()


PRESETS = [
    ("3:4", [3, 4], 4, 200),
    ("5:4", [5, 4], 4, 200),
    ("7:8", [7, 8], 8, 200),
    ("4/4", [4], 4, 200),
    ("5:4:3", [5, 4, 3], 4, 200),
    ("3:2", [3, 2], 2, 200),
]

N_CYCLES = 3


@pytest.mark.parametrize("name,layers_cfg,base,bpm", PRESETS,
                         ids=[p[0] for p in PRESETS])
def test_metronome_beat_count(name, layers_cfg, base, bpm):
    """Run metronome for N cycles and verify every beat fires exactly once."""
    session = PolyrhythmSession(bpm, layers_cfg, base)

    schedule = []
    for li, layer in enumerate(session.layers):
        for bi, phase in enumerate(layer.beat_phases):
            schedule.append((phase, li, bi))

    met = Metronome()
    met.set_schedule(schedule, session.cycle_duration)

    beats = []
    met.on_beat = lambda li, bi, t: beats.append((li, bi, t))

    start = time.perf_counter()
    met.start(start)
    time.sleep(session.cycle_duration * N_CYCLES - 0.02)
    met.stop()

    expected = sum(layers_cfg) * N_CYCLES
    assert len(beats) == expected, (
        f"{name}: expected {expected} beats, got {len(beats)}"
    )


@pytest.mark.parametrize("name,layers_cfg,base,bpm", PRESETS,
                         ids=[p[0] for p in PRESETS])
def test_metronome_beat_timing(name, layers_cfg, base, bpm):
    """Verify beats fire within 30ms of their expected time."""
    session = PolyrhythmSession(bpm, layers_cfg, base)

    schedule = []
    for li, layer in enumerate(session.layers):
        for bi, phase in enumerate(layer.beat_phases):
            schedule.append((phase, li, bi))

    met = Metronome()
    met.set_schedule(schedule, session.cycle_duration)

    beats = []
    met.on_beat = lambda li, bi, t: beats.append((li, bi, t))

    start = time.perf_counter()
    met.start(start)
    time.sleep(session.cycle_duration * N_CYCLES - 0.02)
    met.stop()

    # Check timing accuracy — find the nearest expected time for each beat
    for li, bi, t in beats:
        elapsed = t - start
        layer = session.layers[li]
        beat_offset = layer.beat_phases[bi] * session.cycle_duration
        # Find which cycle this beat belongs to
        cycle = round((elapsed - beat_offset) / session.cycle_duration)
        expected_time = start + cycle * session.cycle_duration + beat_offset
        deviation_ms = abs(t - expected_time) * 1000
        assert deviation_ms < 30, (
            f"{name} L{li}B{bi} cycle {cycle}: fired {deviation_ms:.1f}ms off (max 30ms)"
        )
