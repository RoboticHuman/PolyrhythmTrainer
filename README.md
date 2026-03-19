# Polyrhythm Trainer

A rhythm and polyrhythm training tool with multiple visual modes, challenge scoring, and progressive difficulty. Built with Python and Pygame.

## Requirements

- **Python 3.14+**
- **uv** (Python package manager) — [install instructions](https://docs.astral.sh/uv/getting-started/installation/)
- **Windows/macOS/Linux** (tested on Windows 11)
- **Optional:** MIDI controller (e.g., Arturia Keystep 37) for input

## Quick Start

```bash
# Clone and enter the project
git clone https://github.com/RoboticHuman/PolyrhythmTrainer.git
cd PolyrhythmTrainer

# Install dependencies
uv sync

# Run the app
uv run python -m src.main
```

## Controls

### Rhythm Input
| Key | Action |
|-----|--------|
| D / F | Hit Layer 0 (left hand) |
| J / K | Hit Layer 1 (right hand) |
| Space | Hit Layer 2 (3-layer presets) |

### Session Controls
| Key | Action |
|-----|--------|
| Tab | Toggle stats HUD |
| V | Cycle visual mode |
| C | Toggle CRT filter |
| H | Toggle hit sound mode (granular/uniform) |
| N | Toggle difficulty (relaxed/strict) |
| +/- | Adjust BPM |
| [ / ] | Cycle presets |
| 1-9 | Jump to preset |
| R | Restart session |
| Esc | Back to menu / Quit |

### Menu Navigation
| Key | Action |
|-----|--------|
| Up/Down | Select option |
| Left/Right | Adjust BPM (in preset selector) |
| Enter/Space | Confirm selection |
| V | Change visual mode (in preset selector) |
| Esc | Back / Quit |

## Game Modes

- **Freeplay** — Infinite practice with no timer or score
- **Challenge** — Timed rounds (30/60/90s) with scoring, auto BPM ramp, and letter grades (S/A/B/C/D)
- **Progression** — Unlock harder rhythms by earning grades on easier ones (5 tiers)
- **Surprise Me!** — Random preset, straight into freeplay

## Visual Modes

1. **Orbits** — Concentric rings with beat markers
2. **Game of Life** — Conway's GoL that evolves with the beat
3. **Automata** — 1D cellular automaton scrolling upward
4. **Boxing** — Two fighters in a ring with referee, coaches, and crowd
5. **Blacksmith** — Silhouette forge scene with sparks, customers, and speech bubbles
6. **Dance Battle** — Disco dance-off with crowd, moderator, and CPU opponent AI

## Presets (30 rhythms)

Ordered by difficulty across 5 tiers:

| Tier | Examples |
|------|----------|
| Easy | 3:2, 2:3, 5/4 (3+2) |
| Medium | 3:4, 7/8 (2+2+3), Bossa Nova, Afro-Cuban 6/8, Rumba Clave |
| Hard | 5:4, 9/8 (2+2+2+3), Taksim 10/8, grouped polyrhythms |
| Very Hard | 7:4, 7:8, 11/8, 13/8 |
| Expert | 5:4:3, 3:4:5, 7:5:3 (3 simultaneous layers) |

## Difficulty Modes

| Mode | Perfect | Good | OK | Miss |
|------|---------|------|----|------|
| Relaxed (default) | ±40ms | ±100ms | ±180ms | ±250ms |
| Strict | ±20ms | ±50ms | ±100ms | ±150ms |

## Project Structure

```
PolyrhythmTrainer/
├── src/
│   ├── main.py          # Entry point, game loop, state machine
│   ├── config.py        # Presets, difficulty, constants
│   ├── engine/          # Timing, rhythm math, scoring, progression
│   ├── input/           # Keyboard and MIDI input handlers
│   ├── audio/           # Metronome, hit sounds, wavetable synthesis
│   ├── visuals/         # Visual modes and shared components
│   └── ui/              # HUD, menus, results, sound designer
├── tests/               # Automated tests
├── data/                # User saves (gitignored)
└── pyproject.toml       # Project config and dependencies
```

## Running Tests

```bash
# Fast tests only (default) — ~0.1s
uv run pytest tests/ -v

# Include real-time metronome tests — ~45s
uv run pytest tests/ -v -m ""

# Only real-time tests
uv run pytest tests/ -v -m realtime
```

## MIDI Setup

The app auto-detects MIDI devices on startup. To use a controller:

1. Connect your MIDI controller before launching
2. The first available device is opened automatically
3. All note-on events map to Layer 0 by default
4. Custom note-to-layer mapping can be configured in `src/input/midi.py`

Note: `mido` is installed but the rtmidi backend requires a C++ compiler for the port driver. Keyboard input works without any extra setup.

## Adding a New Preset

In `src/config.py`, add a `Preset` object to the `PRESETS` list:

```python
# Even polyrhythm (e.g. 3 against 4)
Preset(
    id="my_poly",             # Unique string ID (stable, never changes)
    name="My Rhythm",         # Display name
    layers=[3, 4],            # int = evenly spaced beats per layer
    base_beats=4,             # Reference for BPM (4 = quarter note, 8 = eighth)
    category="poly",          # For menu color coding
    tier=TIER_MEDIUM,         # Difficulty tier (controls progression unlocking)
)
```

For grouped rhythms, use `_grouping()` — this creates ALL subdivisions with accents on grouping starts:

```python
# 7/8 with 2+2+3 accent pattern = 7 beats, accents on 0, 2, 4
Preset(
    id="odd_7_8_custom",
    name="7/8 (3+2+2)",
    layers=[_grouping([3, 2, 2])],  # All 7 subdivisions, accents on group starts
    base_beats=8,
    category="odd",
    tier=TIER_MEDIUM,
)

# Grouped layer against an even layer
Preset(
    id="pg_7_8v4",
    name="7/8 (2+2+3) vs 4",
    layers=[_grouping([2, 2, 3]), 4],  # Layer 0: grouped, Layer 1: even
    base_beats=8,
    category="poly-grouped",
    tier=TIER_HARD,
)
```

Tiers and progression update automatically — no index management needed.

## Adding a New Visual Mode

1. Create `src/visuals/mymode.py` with a class extending `BaseVisualizer`
2. Implement `render()`, `on_hit()`, `on_beat()`
3. Use `Timeline` component for the beat bar at the bottom
4. Add to `VISUAL_MODES` in `config.py`
5. Import and add to `self.visualizers` list in `main.py`
