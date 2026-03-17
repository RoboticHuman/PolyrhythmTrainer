"""Test that all beats are correctly detected across all presets with simulated jitter."""

import random
import pytest
from src.engine.rhythm import PolyrhythmSession
from src.engine.scoring import HitDetector, SessionStats
from src.config import set_difficulty


@pytest.fixture(autouse=True)
def strict_difficulty():
    """Tests use strict windows for deterministic results."""
    set_difficulty("strict")
    yield
    set_difficulty("strict")


PRESETS = [
    ("3:4", [3, 4], 4, 120),
    ("5:4", [5, 4], 4, 120),
    ("7:8", [7, 8], 8, 100),
    ("4/4", [4], 4, 140),
    ("5:4:3", [5, 4, 3], 4, 90),
    ("3:2", [3, 2], 2, 120),
    ("7:4", [7, 4], 4, 80),
]

N_CYCLES = 4


def _make_test_cases():
    """Generate (name, layer_beats, base, bpm, layer_idx) for each layer of each preset."""
    cases = []
    for name, layers, base, bpm in PRESETS:
        for li in range(len(layers)):
            cases.append((name, layers, base, bpm, li))
    return cases


@pytest.mark.parametrize("name,layers,base,bpm,layer_idx", _make_test_cases(),
                         ids=[f"{p[0]}_L{p[4]}" for p in _make_test_cases()])
def test_all_beats_detected(name, layers, base, bpm, layer_idx):
    """Simulate a player hitting every beat with random jitter (±30ms).

    Every hit within ±30ms of the expected beat should be detected and scored.
    """
    random.seed(42 + layer_idx)
    session = PolyrhythmSession(bpm, layers, base)
    layer = session.layers[layer_idx]
    stats = SessionStats()
    detector = HitDetector(session.cycle_duration, layer.beat_phases)

    expected_times = []
    for cycle in range(N_CYCLES):
        for bi, phase in enumerate(layer.beat_phases):
            expected_times.append(cycle * session.cycle_duration + phase * session.cycle_duration)

    for exp_t in expected_times:
        jitter = random.uniform(-30, 30) / 1000.0
        result = detector.detect_hit(exp_t + jitter, 0.0)
        if result:
            stats.record_hit(result[1])
        else:
            stats.record_missed_beat()

    total = len(expected_times)
    assert stats.total_hits == total, (
        f"{name} layer {layer_idx} ({layer.beats} beats): "
        f"detected {stats.total_hits}/{total}, missed {stats.missed_beats}"
    )


def test_off_beat_hits_rejected():
    """Hits that are far from any beat should return None."""
    session = PolyrhythmSession(120, [4], 4)
    detector = HitDetector(session.cycle_duration, session.layers[0].beat_phases)

    # Beat positions at 0.0, 0.5, 1.0, 1.5s in a 2.0s cycle
    # Hit at 0.3s is far from any beat
    result = detector.detect_hit(0.3, 0.0)
    assert result is None


def test_scoring_windows():
    """Verify correct rating assignment at window boundaries."""
    from src.engine.scoring import rate_hit, HitRating

    assert rate_hit(5) == HitRating.PERFECT
    assert rate_hit(19) == HitRating.PERFECT
    assert rate_hit(21) == HitRating.GOOD
    assert rate_hit(49) == HitRating.GOOD
    assert rate_hit(51) == HitRating.OK
    assert rate_hit(99) == HitRating.OK
    assert rate_hit(101) == HitRating.MISS
