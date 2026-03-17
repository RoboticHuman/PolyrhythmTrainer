"""Personal best records — save/load high scores per preset+duration."""

import json
import os

RECORDS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "records.json")


def _load_all() -> dict:
    try:
        with open(RECORDS_PATH, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_all(data: dict):
    os.makedirs(os.path.dirname(RECORDS_PATH), exist_ok=True)
    with open(RECORDS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _record_key(preset_id: str, duration: int) -> str:
    return f"{preset_id}_{duration}s"


def get_best(preset_id: str, duration: int) -> dict | None:
    """Get personal best for a preset+duration. Returns dict or None."""
    data = _load_all()
    return data.get(_record_key(preset_id, duration))


def save_if_best(preset_id: str, duration: int, score: int,
                 accuracy: float, grade: str, best_combo: int, bpm_reached: float) -> bool:
    """Save record if it beats the current best. Returns True if new best."""
    data = _load_all()
    key = _record_key(preset_id, duration)
    current = data.get(key)

    if current and current.get("score", 0) >= score:
        return False

    data[key] = {
        "score": score,
        "accuracy": round(accuracy, 1),
        "grade": grade,
        "best_combo": best_combo,
        "bpm_reached": round(bpm_reached, 1),
    }
    _save_all(data)
    return True
