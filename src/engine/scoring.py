"""Hit detection and accuracy scoring."""

from src.config import PERFECT_WINDOW_MS, GOOD_WINDOW_MS, OK_WINDOW_MS, MISS_WINDOW_MS


class HitRating:
    PERFECT = "perfect"
    GOOD = "good"
    OK = "ok"
    MISS = "miss"


def rate_hit(deviation_ms: float) -> str:
    """Rate a hit based on absolute deviation in milliseconds."""
    abs_dev = abs(deviation_ms)
    if abs_dev <= PERFECT_WINDOW_MS:
        return HitRating.PERFECT
    elif abs_dev <= GOOD_WINDOW_MS:
        return HitRating.GOOD
    elif abs_dev <= OK_WINDOW_MS:
        return HitRating.OK
    else:
        return HitRating.MISS


class SessionStats:
    """Tracks scoring statistics for a practice session."""

    def __init__(self):
        self.reset()

    # Score points per rating
    SCORE_VALUES = {
        HitRating.PERFECT: 100,
        HitRating.GOOD: 50,
        HitRating.OK: 10,
        HitRating.MISS: 0,
    }

    def reset(self):
        self.total_hits = 0
        self.ratings = {
            HitRating.PERFECT: 0,
            HitRating.GOOD: 0,
            HitRating.OK: 0,
            HitRating.MISS: 0,
        }
        self.deviations: list[float] = []
        self.streak = 0
        self.best_streak = 0
        self.last_rating = ""
        self.last_deviation_ms = 0.0
        self.missed_beats = 0

        # Combo & score
        self.combo = 0
        self.best_combo = 0
        self.combo_multiplier = 1.0
        self.score = 0

    def record_hit(self, deviation_ms: float) -> str:
        """Record a hit and return its rating."""
        rating = rate_hit(deviation_ms)
        self.total_hits += 1
        self.ratings[rating] += 1
        self.deviations.append(deviation_ms)
        self.last_rating = rating
        self.last_deviation_ms = deviation_ms

        # Streak (perfect + good only)
        if rating in (HitRating.PERFECT, HitRating.GOOD):
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.streak = 0

        # Combo (perfect + good build, ok keeps but doesn't grow, miss resets)
        if rating in (HitRating.PERFECT, HitRating.GOOD):
            self.combo += 1
        elif rating == HitRating.OK:
            pass  # Combo holds but doesn't grow
        else:
            self.combo = 0
        self.best_combo = max(self.best_combo, self.combo)

        # Multiplier: 1.0x base, +0.1x per 5 combo hits, caps at 3.0x
        self.combo_multiplier = min(3.0, 1.0 + (self.combo // 5) * 0.1)

        # Score
        base_points = self.SCORE_VALUES.get(rating, 0)
        self.score += int(base_points * self.combo_multiplier)

        return rating

    def record_missed_beat(self):
        """A beat passed with no player input."""
        self.missed_beats += 1
        self.streak = 0
        self.combo = 0
        self.combo_multiplier = 1.0

    @property
    def accuracy_pct(self) -> float:
        """Percentage of hits that were Perfect or Good."""
        if self.total_hits == 0:
            return 0.0
        good_hits = self.ratings[HitRating.PERFECT] + self.ratings[HitRating.GOOD]
        return (good_hits / self.total_hits) * 100.0

    @property
    def avg_deviation_ms(self) -> float:
        """Average signed deviation in milliseconds."""
        if not self.deviations:
            return 0.0
        return sum(self.deviations) / len(self.deviations)

    @property
    def avg_abs_deviation_ms(self) -> float:
        """Average absolute deviation in milliseconds."""
        if not self.deviations:
            return 0.0
        return sum(abs(d) for d in self.deviations) / len(self.deviations)


class HitDetector:
    """Detects hits against expected beat positions.

    Works with cycle-based timing: given a hit time and the current cycle,
    finds the nearest expected beat and scores accuracy.
    """

    def __init__(self, cycle_duration: float, beat_phases: list[float]):
        self.cycle_duration = cycle_duration
        self.beat_phases = beat_phases  # Normalized 0.0-1.0
        self._last_scored_beats: set[tuple[int, int]] = set()  # (cycle, beat_idx)

    def update_rhythm(self, cycle_duration: float, beat_phases: list[float]):
        self.cycle_duration = cycle_duration
        self.beat_phases = beat_phases
        self._last_scored_beats.clear()

    def detect_hit(self, hit_time: float, session_start_time: float) -> tuple[str, float] | None:
        """Check a hit against expected beats.

        Args:
            hit_time: perf_counter timestamp of the hit
            session_start_time: perf_counter timestamp of session start

        Returns:
            (rating, deviation_ms) or None if too far from any beat
        """
        if not self.beat_phases or self.cycle_duration <= 0:
            return None

        elapsed = hit_time - session_start_time
        if elapsed < 0:
            # Hit before session started — treat as early hit on cycle 0 beat 0
            cycle_num = 0
            phase = 0.0
            elapsed = 0.0
        else:
            cycle_num = int(elapsed / self.cycle_duration)
            phase = (elapsed % self.cycle_duration) / self.cycle_duration

        # Find nearest beat
        best_idx = 0
        best_dist = 1.0
        for i, bp in enumerate(self.beat_phases):
            dist = phase - bp
            if dist > 0.5:
                dist -= 1.0
            elif dist < -0.5:
                dist += 1.0
            if abs(dist) < abs(best_dist):
                best_dist = dist
                best_idx = i

        # Convert phase distance to milliseconds
        deviation_ms = best_dist * self.cycle_duration * 1000.0

        # Check if within scoring window
        if abs(deviation_ms) > MISS_WINDOW_MS:
            return None

        # Prevent double-scoring the same beat
        # Determine which cycle the *beat* belongs to (not the hit).
        # If we hit early (best_dist < 0) and the nearest beat is beat 0,
        # and our phase is near the end of the cycle, the beat is in the next cycle.
        # If we hit late (best_dist > 0) and the nearest beat is the last beat,
        # and our phase is near the start of the cycle, the beat is in the previous cycle.
        score_cycle = cycle_num
        if best_dist < 0 and best_idx == 0 and phase > 0.5:
            score_cycle += 1
        elif best_dist > 0 and best_idx == len(self.beat_phases) - 1 and phase < 0.5:
            score_cycle -= 1
        beat_key = (score_cycle, best_idx)
        if beat_key in self._last_scored_beats:
            return None
        self._last_scored_beats.add(beat_key)

        # Cleanup old entries
        if len(self._last_scored_beats) > 100:
            cutoff = cycle_num - 2
            self._last_scored_beats = {
                k for k in self._last_scored_beats if k[0] >= cutoff
            }

        return (rate_hit(deviation_ms), deviation_ms)
