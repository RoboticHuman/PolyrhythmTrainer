"""Blacksmith visualizer — silhouette style.

A blacksmith silhouette hammers an anvil against a warm glowing forge.
All characters and objects are dark silhouettes backlit by the forge glow.
Only sparks, hot metal, and embers are bright. Atmospheric and stylized.
"""

import math
import random
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    ORANGE, YELLOW, rating_color
)
from src.visuals.effects import bloom_pass, ParticleSystem, Particle
from src.visuals.timeline import Timeline
from src.engine.scoring import HitRating


# Silhouette colors — near-black with slight warm tint
SILHOUETTE = (12, 8, 6)
SILHOUETTE_EDGE = (25, 18, 12)  # Slight edge highlight from forge light
GROUND = (8, 5, 3)

# Forge glow palette
GLOW_DIM = (60, 20, 5)
GLOW_MED = (140, 50, 10)
GLOW_BRIGHT = (220, 100, 20)
GLOW_HOT = (255, 180, 60)
GLOW_WHITE = (255, 230, 180)

# Ember/spark colors
EMBER_COLORS = [(255, 200, 50), (255, 140, 20), (255, 100, 10), (255, 60, 5)]
METAL_COLORS = [
    (80, 80, 90),      # cold
    (160, 60, 20),     # warm
    (220, 100, 30),    # hot
    (255, 180, 60),    # very hot
    (255, 230, 180),   # white hot
]


def _warm_color(base: tuple, heat: float) -> tuple:
    """Tint a color warmer based on heat 0-1."""
    r = min(255, int(base[0] + heat * 40))
    g = min(255, int(base[1] + heat * 15))
    b = min(255, int(base[2] + heat * 5))
    return (r, g, b)


class BlacksmithVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem(max_particles=500)

        self.timeline_h = 60
        self.scene_h = self.height - self.timeline_h

        # Layout — forge on the right, anvil center-right, smith center
        self.forge_cx = int(self.width * 0.72)
        self.forge_cy = int(self.scene_h * 0.68)
        self.anvil_x = int(self.width * 0.50)
        self.anvil_y = int(self.scene_h * 0.72)
        self.smith_x = int(self.width * 0.38)
        self.smith_y = int(self.scene_h * 0.52)
        self.ground_y = int(self.scene_h * 0.82)

        # Metal heat: 0 = cold, 1 = white hot
        self.metal_heat = 0.5

        # Forge glow radius pulses with beat
        self.forge_glow_base = int(self.width * 0.35)

        # Hammer state
        self.hammer_angle = 0.0  # degrees, 0 = resting, negative = raised
        self.hammer_state = "idle"
        self.hammer_time = 0.0
        self.hammer_duration = 0.3

        # Strike flash on the metal
        self._strike_flash = 0.0  # 0-1, decays quickly
        self._strike_flash_time = 0.0

        # Screen shake
        self._shake_time = 0.0
        self._shake_intensity = 0.0

        # Pre-generate ember positions for the forge
        self._embers = []
        for _ in range(35):
            self._embers.append({
                "ox": random.uniform(-35, 35),
                "oy": random.uniform(-20, 15),
                "speed": random.uniform(15, 50),
                "drift": random.uniform(-15, 15),
                "phase": random.uniform(0, math.pi * 2),
                "size": random.uniform(1.5, 3.5),
            })

        # --- Weapons on wall display ---
        self._weapons = self._generate_weapons()

        # --- Door and customers ---
        # Door should be person-sized: about 1.3x a customer's height
        # Customer is ~70px tall, so door ~90px tall, ~40px wide
        self.door_h = 95
        self.door_w = 42
        self.door_x = int(self.width * 0.08)
        self.door_y = self.ground_y - self.door_h  # Bottom flush with floor
        self.door_open = 0.0  # 0 = closed, 1 = fully open
        self.door_target = 0.0
        self._door_light_alpha = 0.0

        # Customer queue — silhouette figures that walk in/out
        self._customers: list[dict] = []
        self._next_customer_beat = 8  # spawn a customer every N beats
        self._beat_count = 0

        # Timeline
        self.timeline = Timeline(self.surface, self.timeline_h)
        self.timeline.bar_color = ORANGE
        self._label_font = pygame.font.SysFont("consolas", 12, bold=True)

    def _generate_weapons(self) -> list[dict]:
        """Generate silhouette weapon shapes for wall display."""
        weapons = []
        wall_left = int(self.width * 0.15)
        wall_right = int(self.width * 0.55)
        wall_y_base = int(self.scene_h * 0.15)

        rng = random.Random(99)
        x = wall_left
        while x < wall_right:
            kind = rng.choice(["sword", "axe", "dagger", "shield", "hammer"])
            weapons.append({"kind": kind, "x": x, "y": wall_y_base + rng.randint(-10, 10)})
            x += rng.randint(50, 80)
        return weapons

    def _draw_weapons(self):
        """Draw weapon silhouettes on the back wall."""
        for w in self._weapons:
            x, y = w["x"], w["y"]
            kind = w["kind"]
            # All drawn as dark silhouettes with slight edge highlight
            if kind == "sword":
                # Blade
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x, y), (x, y + 55), 3)
                # Guard
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x - 8, y + 42), (x + 8, y + 42), 3)
                # Pommel
                pygame.draw.circle(self.surface, SILHOUETTE_EDGE, (x, y + 55), 3)
                # Blade tip
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x, y), (x, y - 2), 2)
            elif kind == "axe":
                # Handle
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x, y), (x, y + 50), 3)
                # Axe head
                head = [(x - 12, y + 2), (x + 2, y - 5), (x + 2, y + 15), (x - 12, y + 12)]
                pygame.draw.polygon(self.surface, SILHOUETTE_EDGE, head)
            elif kind == "dagger":
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x, y), (x, y + 30), 2)
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x - 5, y + 22), (x + 5, y + 22), 2)
                pygame.draw.circle(self.surface, SILHOUETTE_EDGE, (x, y + 30), 2)
            elif kind == "shield":
                pygame.draw.ellipse(self.surface, SILHOUETTE_EDGE,
                                    (x - 12, y, 24, 30), 2)
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x, y + 5), (x, y + 25), 2)
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x - 8, y + 15), (x + 8, y + 15), 2)
            elif kind == "hammer":
                pygame.draw.line(self.surface, SILHOUETTE_EDGE, (x, y + 5), (x, y + 45), 3)
                pygame.draw.rect(self.surface, SILHOUETTE_EDGE, (x - 8, y, 16, 10))
            # Mounting nail
            pygame.draw.circle(self.surface, (30, 22, 16), (x, y + 25 if kind != "dagger" else y + 15), 2)

    # Speech bubble text pools
    BUBBLE_PERFECT = [
        "Incredible!", "Masterwork!", "Beautiful!", "Wow!",
        "Amazing craft!", "Take my gold!", "Stunning!",
    ]
    BUBBLE_GOOD = [
        "Nice work!", "Looking good!", "Ooh, shiny!", "Not bad!",
        "I like it!", "Great stuff!",
    ]
    BUBBLE_OK = [
        "Hmm, okay...", "Getting there", "Keep going!", "Not sure...",
        "Interesting...",
    ]
    BUBBLE_MISS = [
        "Yikes!", "Careful!", "That's dangerous!", "Oh no!",
        "Watch out!", "My ears!!", "Oof...",
    ]

    def _spawn_customer(self):
        """Spawn a customer silhouette that walks in from the door."""
        self._customers.append({
            "x": float(self.door_x),
            "y": float(self.ground_y),
            "target_x": float(self.anvil_x - random.randint(60, 120)),
            "speed": random.uniform(40, 70),
            "state": "entering",  # entering, waiting, leaving
            "wait_time": 0.0,
            "wait_duration": random.uniform(3.0, 6.0),
            "height": random.uniform(0.8, 1.1),
            "bubble_text": "",
            "bubble_time": 0.0,
        })
        # Open the door
        self.door_target = 1.0

    def _update_customers(self, dt: float):
        """Move customers through their walk cycle."""
        active = []
        any_inside = False

        for c in self._customers:
            if c["state"] == "entering":
                c["x"] += c["speed"] * dt
                if c["x"] >= c["target_x"]:
                    c["x"] = c["target_x"]
                    c["state"] = "waiting"
                    c["wait_time"] = time.perf_counter()
                any_inside = True
            elif c["state"] == "waiting":
                elapsed = time.perf_counter() - c["wait_time"]
                if elapsed > c["wait_duration"]:
                    c["state"] = "leaving"
                any_inside = True
            elif c["state"] == "leaving":
                c["x"] -= c["speed"] * dt
                if c["x"] <= self.door_x - 20:
                    continue  # Remove
                if c["x"] < self.door_x + 30:
                    self.door_target = 1.0  # Open door to leave
                any_inside = True
            active.append(c)

        self._customers = active

        # Close door when no one is near it
        near_door = any(abs(c["x"] - self.door_x) < 60 for c in self._customers)
        if not near_door:
            self.door_target = 0.0

        # Smoothly animate door
        self.door_open += (self.door_target - self.door_open) * min(1.0, dt * 5)

    def _draw_customer(self, c: dict, beat_phase: float):
        """Draw a customer as a silhouette figure."""
        x = int(c["x"])
        y = int(c["y"])
        h = c["height"]
        # Walking bob
        if c["state"] != "waiting":
            bob = math.sin(time.perf_counter() * 8) * 2
        else:
            bob = math.sin(beat_phase * math.pi * 2) * 1.5
        y += int(bob)

        head_r = int(10 * h)
        body_h = int(35 * h)
        leg_h = int(25 * h)

        # Legs
        stride = 0
        if c["state"] == "entering":
            stride = int(math.sin(time.perf_counter() * 8) * 6)
        elif c["state"] == "leaving":
            stride = int(math.sin(time.perf_counter() * 8) * 6)

        pygame.draw.line(self.surface, SILHOUETTE,
                         (x - 5, y - leg_h), (x - 5 - stride, y), 5)
        pygame.draw.line(self.surface, SILHOUETTE,
                         (x + 5, y - leg_h), (x + 5 + stride, y), 5)
        # Body
        pygame.draw.rect(self.surface, SILHOUETTE,
                         (x - int(10 * h), y - leg_h - body_h,
                          int(20 * h), body_h), border_radius=4)
        # Head
        head_y = y - leg_h - body_h - head_r + 3
        pygame.draw.circle(self.surface, SILHOUETTE, (x, head_y), head_r)

        # If near door and door is open, they catch some door light on their edge
        if abs(x - self.door_x) < 80 and self.door_open > 0.3:
            light_side = -1 if x > self.door_x else 1
            edge_x = x + light_side * int(10 * h)
            pygame.draw.line(self.surface, (40, 35, 25),
                             (edge_x, head_y - head_r), (edge_x, y - leg_h), 1)

        # Speech bubble
        bubble_age = time.perf_counter() - c["bubble_time"]
        if c["bubble_text"] and bubble_age < 2.0:
            self._draw_bubble(self.surface, x, head_y - head_r - 8, c["bubble_text"], bubble_age)

    def _draw_bubble(self, surface: pygame.Surface, x: int, y: int,
                     text: str, age: float):
        """Draw a speech bubble above a character."""
        # Fade in quickly, hold, fade out
        if age < 0.1:
            alpha = age / 0.1
        elif age < 1.6:
            alpha = 1.0
        else:
            alpha = max(0.0, 1.0 - (age - 1.6) / 0.4)

        # Float upward slightly over time
        y -= int(age * 8)

        text_surf = self._label_font.render(text, True, (220, 210, 190))
        tw, th = text_surf.get_size()
        pad_x, pad_y = 8, 5
        bw = tw + pad_x * 2
        bh = th + pad_y * 2

        # Bubble background
        bubble = pygame.Surface((bw, bh + 6), pygame.SRCALPHA)
        bg_alpha = int(180 * alpha)
        pygame.draw.rect(bubble, (20, 15, 12, bg_alpha),
                         (0, 0, bw, bh), border_radius=6)
        pygame.draw.rect(bubble, (60, 50, 35, bg_alpha),
                         (0, 0, bw, bh), 1, border_radius=6)
        # Little triangle pointer
        tri_x = bw // 2
        pygame.draw.polygon(bubble, (20, 15, 12, bg_alpha),
                            [(tri_x - 4, bh), (tri_x + 4, bh), (tri_x, bh + 5)])

        # Blit bubble and text
        bx = x - bw // 2
        by_pos = y - bh - 5
        surface.blit(bubble, (bx, by_pos))

        text_surf.set_alpha(int(255 * alpha))
        surface.blit(text_surf, (bx + pad_x, by_pos + pad_y))

    def _draw_door_and_light(self):
        """Draw the shop door and light shaft when open."""
        dx, dy = self.door_x, self.door_y
        dw, dh = self.door_w, self.door_h

        # Door frame (always visible)
        pygame.draw.rect(self.surface, SILHOUETTE_EDGE,
                         (dx - 3, dy - 3, dw + 6, dh + 6), 2)

        # Doorway — when open, shows bright exterior light
        if self.door_open > 0.02:
            open_w = int(dw * self.door_open)

            # Bright rectangle (the outside world)
            brightness = self.door_open
            ext_color = (
                min(255, int(180 * brightness)),
                min(255, int(160 * brightness)),
                min(255, int(120 * brightness))
            )
            pygame.draw.rect(self.surface, ext_color,
                             (dx, dy, open_w, dh))

            # Light shaft — trapezoid of light spilling into the room
            shaft_reach = int(self.width * 0.35 * self.door_open)
            shaft_alpha = int(25 * self.door_open)

            shaft_surf = pygame.Surface((self.width, self.scene_h), pygame.SRCALPHA)
            shaft_pts = [
                (dx + open_w, dy),
                (dx + open_w + shaft_reach, dy - 20),
                (dx + open_w + shaft_reach, self.ground_y + 10),
                (dx + open_w, dy + dh),
            ]
            pygame.draw.polygon(shaft_surf, (200, 180, 130, shaft_alpha), shaft_pts)
            self.surface.blit(shaft_surf, (0, 0))

            # Light edge on the smith if shaft reaches them
            if dx + open_w + shaft_reach > self.smith_x - 30:
                # Illuminate left edge of smith slightly
                self._door_light_alpha = min(1.0, self.door_open * 0.6)
            else:
                self._door_light_alpha = 0.0
        else:
            self._door_light_alpha = 0.0
            # Closed door — dark rectangle
            pygame.draw.rect(self.surface, SILHOUETTE, (dx, dy, dw, dh))

        # Door panel (hinged on left, swings open)
        if self.door_open > 0.02:
            door_panel_w = max(2, int(dw * (1 - self.door_open) * 0.5))
            pygame.draw.rect(self.surface, SILHOUETTE,
                             (dx + int(dw * self.door_open) - door_panel_w, dy,
                              door_panel_w, dh))

    def _draw_smith_door_light(self):
        """Draw door light illuminating the smith's left side."""
        if self._door_light_alpha < 0.05:
            return

        bx = self.smith_x
        by = self.smith_y
        a = self._door_light_alpha
        light_color = (
            min(255, int(60 * a)),
            min(255, int(50 * a)),
            min(255, int(30 * a))
        )

        # Edge highlight on left side of body
        body_h = 45
        pygame.draw.line(self.surface, light_color,
                         (bx - 20, by - body_h // 2 + 15),
                         (bx - 15, by + body_h // 2 + 5), 2)
        # Left arm
        pygame.draw.line(self.surface, light_color,
                         (bx - 22, by - 5),
                         (bx - 30, by + 20), 1)
        # Head left edge
        head_y = by - body_h // 2 + 15 - 14
        pygame.draw.arc(self.surface, light_color,
                        (bx - 14, int(head_y) - 14, 28, 28),
                        1.5, 3.5, 2)

    def _set_hammer(self, state: str, duration: float = 0.25):
        self.hammer_state = state
        self.hammer_time = time.perf_counter()
        self.hammer_duration = duration

    def _hammer_t(self) -> float:
        elapsed = time.perf_counter() - self.hammer_time
        t = min(1.0, elapsed / self.hammer_duration) if self.hammer_duration > 0 else 1.0
        if t >= 1.0 and self.hammer_state != "idle":
            self.hammer_state = "idle"
        return t

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = rating_color(rating)
        now = time.perf_counter()

        sx = self.anvil_x + 15
        sy = self.anvil_y - 8

        if rating == HitRating.PERFECT:
            self._set_hammer("strike", 0.2)
            self.metal_heat = min(1.0, self.metal_heat + 0.15)
            self._strike_flash = 1.0
            self._strike_flash_time = now
            self._shake_intensity = 5
            self._shake_time = now
            # Big spark shower
            for _ in range(30):
                angle = random.uniform(-math.pi, 0)  # Upward hemisphere
                speed = random.uniform(100, 350)
                self.particles.particles.append(Particle(
                    sx + random.uniform(-8, 8), sy + random.uniform(-5, 3),
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    random.choice(EMBER_COLORS),
                    life=random.uniform(0.4, 1.0),
                    size=random.uniform(2, 5)
                ))

        elif rating == HitRating.GOOD:
            self._set_hammer("strike", 0.22)
            self.metal_heat = min(1.0, self.metal_heat + 0.08)
            self._strike_flash = 0.7
            self._strike_flash_time = now
            self._shake_intensity = 3
            self._shake_time = now
            for _ in range(15):
                angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
                speed = random.uniform(80, 220)
                self.particles.particles.append(Particle(
                    sx + random.uniform(-5, 5), sy,
                    math.cos(angle) * speed, math.sin(angle) * speed,
                    random.choice(EMBER_COLORS),
                    life=random.uniform(0.3, 0.7),
                    size=random.uniform(1.5, 3.5)
                ))

        elif rating == HitRating.OK:
            self._set_hammer("strike", 0.25)
            self.metal_heat = min(1.0, self.metal_heat + 0.03)
            self._strike_flash = 0.4
            self._strike_flash_time = now
            self._shake_intensity = 1.5
            self._shake_time = now
            self.particles.emit(sx, sy, (200, 100, 30), count=6, speed=120, life=0.3, size=2)

        else:
            self._set_hammer("miss", 0.35)
            self.particles.emit(sx + 20, sy + 5, (120, 120, 130), count=3, speed=60, life=0.2, size=1.5)

        # Customer speech bubbles — pick a random waiting customer to react
        waiting = [c for c in self._customers if c["state"] == "waiting"]
        if waiting:
            # Don't spam — only if no one is already talking
            talking = [c for c in waiting if now - c["bubble_time"] < 2.0]
            if not talking:
                speaker = random.choice(waiting)
                if rating == HitRating.PERFECT:
                    speaker["bubble_text"] = random.choice(self.BUBBLE_PERFECT)
                elif rating == HitRating.GOOD:
                    speaker["bubble_text"] = random.choice(self.BUBBLE_GOOD)
                elif rating == HitRating.OK:
                    speaker["bubble_text"] = random.choice(self.BUBBLE_OK)
                else:
                    speaker["bubble_text"] = random.choice(self.BUBBLE_MISS)
                speaker["bubble_time"] = now

        # Timeline
        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self.timeline.flash_marker(layer, best_bi, color)
            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self.timeline.row_y(layer, len(self.layers))
            self.particles.emit(mx, my, color, count=8, speed=100, life=0.4)

    def on_beat(self, layer: int, beat_idx: int):
        self.metal_heat = max(0.1, self.metal_heat - 0.025)
        self._beat_count += 1

        # Spawn a customer periodically
        if self._beat_count % self._next_customer_beat == 0 and len(self._customers) < 3:
            self._spawn_customer()
            self._next_customer_beat = random.randint(12, 24)

    # --- Drawing ---

    def _draw_background(self):
        """Nearly invisible stone wall — only hinted at in darkness.

        The bricks are drawn extremely dark so they're barely perceptible.
        The forge glow and door light are what actually illuminate the scene.
        """
        rng = random.Random(77)
        for row in range(0, self.ground_y, 25):
            offset = 15 if (row // 25) % 2 else 0
            for col in range(offset, self.width, 50):
                shade = rng.randint(-2, 2)
                # Very dark — just enough to hint at texture
                c = (8 + shade, 6 + shade, 5 + shade)
                pygame.draw.rect(self.surface, c, (col, row, 48, 23))
                pygame.draw.rect(self.surface, (6, 4, 3), (col, row, 48, 23), 1)

    def _draw_forge_glow(self, beat_phase: float):
        """Radial gradient glow emanating from the forge — the main light source."""
        pulse = (math.sin(beat_phase * math.pi * 2) + 1) / 2
        heat_boost = self.metal_heat * 0.3

        # Multiple concentric gradient circles for smooth falloff
        cx, cy = self.forge_cx, self.forge_cy
        max_r = self.forge_glow_base + int(pulse * 30 + heat_boost * 40)

        layers = [
            (max_r, (int(15 + heat_boost * 20), int(5 + heat_boost * 8), 2)),
            (int(max_r * 0.7), (int(35 + pulse * 15 + heat_boost * 40), int(12 + heat_boost * 12), 3)),
            (int(max_r * 0.45), (int(60 + pulse * 25 + heat_boost * 60), int(20 + heat_boost * 20), 5)),
            (int(max_r * 0.25), (int(90 + pulse * 30 + heat_boost * 80), int(35 + heat_boost * 25), 8)),
            (int(max_r * 0.12), (int(140 + pulse * 40), int(55 + pulse * 15), 10)),
        ]

        for radius, color in layers:
            if radius <= 0:
                continue
            color = tuple(min(255, c) for c in color)
            pygame.draw.circle(self.surface, color, (cx, cy), radius)

    def _draw_forge_structure(self):
        """Forge as a dark silhouette with glowing interior."""
        fx, fy = self.forge_cx, self.forge_cy

        # Chimney hood silhouette
        hood = [
            (fx - 55, fy - 10), (fx + 55, fy - 10),
            (fx + 35, fy - 90), (fx - 35, fy - 90),
        ]
        pygame.draw.polygon(self.surface, SILHOUETTE, hood)

        # Chimney
        pygame.draw.rect(self.surface, SILHOUETTE,
                         (fx - 20, fy - 150, 40, 65))

        # Forge basin silhouette
        basin = [
            (fx - 45, fy - 10), (fx + 45, fy - 10),
            (fx + 50, fy + 30), (fx - 50, fy + 30),
        ]
        pygame.draw.polygon(self.surface, SILHOUETTE, basin)

        # Legs — extend to ground
        leg_h = self.ground_y - (fy + 30)
        pygame.draw.rect(self.surface, SILHOUETTE,
                         (fx - 45, fy + 30, 12, leg_h))
        pygame.draw.rect(self.surface, SILHOUETTE,
                         (fx + 33, fy + 30, 12, leg_h))

        # Glowing coals inside (visible opening)
        coal_rect = pygame.Rect(fx - 30, fy - 5, 60, 25)
        heat = self.metal_heat
        pulse = (math.sin(time.perf_counter() * 3) + 1) / 2
        cr = min(255, int(150 + heat * 80 + pulse * 25))
        cg = min(255, int(40 + heat * 40 + pulse * 15))
        cb = min(255, int(5 + pulse * 5))
        pygame.draw.rect(self.surface, (cr, cg, cb), coal_rect, border_radius=4)

        # Individual coal lumps
        rng = random.Random(42)
        for _ in range(12):
            cx = fx + rng.randint(-25, 25)
            cy = fy + rng.randint(0, 18)
            cr2 = min(255, int(rng.randint(80, 160) + heat * 60 + pulse * rng.randint(10, 40)))
            cg2 = min(255, int(rng.randint(20, 50) + heat * 20))
            pygame.draw.circle(self.surface, (cr2, cg2, 5), (cx, cy), rng.randint(3, 6))

    def _draw_rising_embers(self):
        """Embers float up from the forge."""
        now = time.perf_counter()
        fx, fy = self.forge_cx, self.forge_cy

        for ember in self._embers:
            # Rise and drift
            cycle = (now * ember["speed"]) % 120
            ex = fx + ember["ox"] + math.sin(now * 1.5 + ember["phase"]) * ember["drift"]
            ey = fy - 10 - cycle

            if ey < fy - 120:
                continue

            # Fade as they rise
            life = max(0.0, min(1.0, 1.0 - cycle / 120))
            brightness = life * (0.7 + 0.3 * math.sin(now * 8 + ember["phase"]))
            c = random.Random(int(ember["phase"] * 1000)).choice(EMBER_COLORS)
            color = tuple(max(0, min(255, int(v * brightness))) for v in c)
            size = max(1, int(ember["size"] * life))

            pygame.draw.circle(self.surface, color, (int(ex), int(ey)), size)

    def _draw_anvil(self):
        """Anvil as a dark silhouette with glowing hot metal on top."""
        ax, ay = self.anvil_x, self.anvil_y

        # Anvil stand (tree stump)
        stump_points = [
            (ax - 22, ay + 8), (ax + 22, ay + 8),
            (ax + 25, self.ground_y), (ax - 25, self.ground_y),
        ]
        pygame.draw.polygon(self.surface, SILHOUETTE, stump_points)

        # Anvil body
        body = [(ax - 28, ay + 8), (ax + 28, ay + 8),
                (ax + 25, ay - 8), (ax - 25, ay - 8)]
        pygame.draw.polygon(self.surface, SILHOUETTE, body)

        # Anvil face (top)
        pygame.draw.rect(self.surface, SILHOUETTE_EDGE,
                         (ax - 28, ay - 10, 56, 5))

        # Horn
        horn = [(ax + 28, ay - 3), (ax + 50, ay + 2), (ax + 28, ay + 6)]
        pygame.draw.polygon(self.surface, SILHOUETTE, horn)

        # Slight edge highlight from forge light (right side)
        pygame.draw.line(self.surface, SILHOUETTE_EDGE,
                         (ax + 28, ay - 8), (ax + 28, ay + 8), 1)

        # Hot metal piece on top
        heat = self.metal_heat
        if heat < 0.2:
            mc = METAL_COLORS[0]
        elif heat < 0.4:
            mc = METAL_COLORS[1]
        elif heat < 0.6:
            mc = METAL_COLORS[2]
        elif heat < 0.8:
            mc = METAL_COLORS[3]
        else:
            mc = METAL_COLORS[4]

        # Strike flash — bright white-hot flash on impact
        flash_age = time.perf_counter() - self._strike_flash_time
        flash_t = 0.0
        if flash_age < 0.15 and self._strike_flash > 0:
            flash_t = (1.0 - flash_age / 0.15) * self._strike_flash

        # Metal bar — boosted toward white during flash
        if flash_t > 0:
            flash_mc = (
                min(255, int(mc[0] + (255 - mc[0]) * flash_t)),
                min(255, int(mc[1] + (230 - mc[1]) * flash_t)),
                min(255, int(mc[2] + (180 - mc[2]) * flash_t)),
            )
        else:
            flash_mc = mc
        pygame.draw.rect(self.surface, flash_mc,
                         (ax - 15, ay - 17, 30, 9), border_radius=2)

        # Metal glow halo — bigger and brighter during flash
        glow_heat = max(heat, flash_t)
        if glow_heat > 0.2:
            glow_r = int(15 + glow_heat * 25 + flash_t * 20)
            gc = (min(255, int(flash_mc[0] * 0.4 + flash_t * 80)),
                  min(255, int(flash_mc[1] * 0.3 + flash_t * 40)),
                  min(255, int(flash_mc[2] * 0.15 + flash_t * 15)))
            pygame.draw.circle(self.surface, gc, (ax, ay - 12), glow_r)

    def _draw_smith_silhouette(self, beat_phase: float):
        """The blacksmith as a detailed silhouette."""
        t = self._hammer_t()
        breath = math.sin(beat_phase * math.pi * 2) * 2

        bx = self.smith_x
        by = self.smith_y + breath

        # Compute hammer angle
        if self.hammer_state == "strike":
            # Fast swing: raised → down
            swing = min(1.0, t * 3)
            self.hammer_angle = -75 + 95 * swing
            if t > 0.33:
                # Bounce back slightly
                self.hammer_angle = 20 - 15 * ((t - 0.33) / 0.67)
        elif self.hammer_state == "miss":
            swing = min(1.0, t * 2.5)
            self.hammer_angle = -75 + 115 * swing
            if t > 0.4:
                self.hammer_angle = 40 - 45 * ((t - 0.4) / 0.6)
        elif self.hammer_state == "idle":
            self.hammer_angle *= 0.85

        # Body proportions
        head_r = 14
        torso_h = 45
        hip_y = by + torso_h // 2 + 5

        # --- Legs ---
        left_foot = (bx - 12, self.ground_y)
        right_foot = (bx + 10, self.ground_y)
        pygame.draw.line(self.surface, SILHOUETTE, (bx - 8, hip_y), left_foot, 8)
        pygame.draw.line(self.surface, SILHOUETTE, (bx + 6, hip_y), right_foot, 8)

        # Boot shapes
        pygame.draw.ellipse(self.surface, SILHOUETTE,
                            (left_foot[0] - 6, left_foot[1] - 4, 16, 8))
        pygame.draw.ellipse(self.surface, SILHOUETTE,
                            (right_foot[0] - 6, right_foot[1] - 4, 16, 8))

        # --- Torso ---
        # Broad shoulders, tapered waist
        torso = [
            (bx - 20, by - 10),  # left shoulder
            (bx + 22, by - 10),  # right shoulder
            (bx + 15, hip_y),    # right hip
            (bx - 12, hip_y),    # left hip
        ]
        pygame.draw.polygon(self.surface, SILHOUETTE, torso)

        # Apron edge highlight
        pygame.draw.line(self.surface, SILHOUETTE_EDGE,
                         (bx - 10, by + 5), (bx - 8, hip_y), 1)
        pygame.draw.line(self.surface, SILHOUETTE_EDGE,
                         (bx + 12, by + 5), (bx + 10, hip_y), 1)

        # --- Left arm (holding tongs that grip the metal) ---
        metal_cx = self.anvil_x
        metal_cy = self.anvil_y - 13  # Center of the metal bar

        # Hand grips tongs just left of the metal
        l_hand = (metal_cx - 25, metal_cy + 5)
        l_elbow = (bx - 22, by + 20)
        l_shoulder = (bx - 18, by - 5)
        pygame.draw.line(self.surface, SILHOUETTE, l_shoulder, l_elbow, 7)
        pygame.draw.line(self.surface, SILHOUETTE, l_elbow, l_hand, 6)

        # Tongs — two prongs that converge onto the metal
        tong_tip_top = (metal_cx, metal_cy - 5)
        tong_tip_bot = (metal_cx, metal_cy + 5)
        pygame.draw.line(self.surface, SILHOUETTE_EDGE, l_hand, tong_tip_top, 3)
        pygame.draw.line(self.surface, SILHOUETTE_EDGE, l_hand, tong_tip_bot, 3)
        # Tong jaws gripping the metal (small horizontal lines)
        pygame.draw.line(self.surface, SILHOUETTE_EDGE,
                         tong_tip_top, (metal_cx + 8, metal_cy - 4), 2)
        pygame.draw.line(self.surface, SILHOUETTE_EDGE,
                         tong_tip_bot, (metal_cx + 8, metal_cy + 4), 2)

        # --- Right arm + hammer ---
        # The hammer head must land on the metal when at strike angle.
        # We work backwards: place the hammer head target, then solve the arm.
        r_shoulder = (bx + 20, by - 5)
        angle_rad = math.radians(self.hammer_angle)
        handle_len = 45

        # At rest/strike (angle ~5°), the hammer head should be on the metal.
        # When raised (angle ~ -75°), it's above and behind.
        # Compute hammer head position from angle, anchored so angle=5° hits the metal.
        # We'll place the hand so that hand + handle reaches the anvil at strike.
        strike_target = (self.anvil_x + 5, self.anvil_y - 18)

        # Blend between "aimed at metal" (during strike) and "free swing" (raised)
        # When hammer_angle is near 0-20°, snap to target. When raised, use angle chain.
        strike_blend = max(0.0, min(1.0, (self.hammer_angle + 10) / 30))  # 0 when raised, 1 at strike

        # Free-swing hand position (angle-driven from shoulder)
        free_elbow = (
            r_shoulder[0] + int(math.sin(angle_rad * 0.5) * 25),
            r_shoulder[1] - int(math.cos(angle_rad * 0.5) * 20) + 15
        )
        free_hand = (
            free_elbow[0] + int(math.sin(angle_rad) * 22),
            free_elbow[1] - int(math.cos(angle_rad) * 22)
        )

        # Target hand position (so handle_end lands on the metal)
        target_hand = (
            strike_target[0] - int(math.sin(math.radians(5)) * handle_len),
            strike_target[1] + int(math.cos(math.radians(5)) * handle_len)
        )

        # Blend
        r_hand = (
            int(free_hand[0] + (target_hand[0] - free_hand[0]) * strike_blend),
            int(free_hand[1] + (target_hand[1] - free_hand[1]) * strike_blend),
        )
        # Elbow in between shoulder and hand
        r_elbow = (
            (r_shoulder[0] + r_hand[0]) // 2 + int((1 - strike_blend) * math.sin(angle_rad * 0.5) * 10),
            (r_shoulder[1] + r_hand[1]) // 2 - 10
        )

        pygame.draw.line(self.surface, SILHOUETTE, r_shoulder, r_elbow, 7)
        pygame.draw.line(self.surface, SILHOUETTE, r_elbow, r_hand, 6)

        # Hammer handle — aim toward target when striking, use angle when raised
        if strike_blend > 0.5:
            handle_end = strike_target
        else:
            handle_end = (
                r_hand[0] + int(math.sin(angle_rad) * handle_len),
                r_hand[1] - int(math.cos(angle_rad) * handle_len)
            )
        pygame.draw.line(self.surface, SILHOUETTE, r_hand, handle_end, 5)

        # Hammer head
        hx, hy = handle_end
        # Compute angle from hand to head for rotation
        dx = hx - r_hand[0]
        dy = hy - r_hand[1]
        head_angle = math.atan2(dx, -dy) if (dx != 0 or dy != 0) else angle_rad
        perp_x = math.cos(head_angle)
        perp_y = math.sin(head_angle)
        hw, hh = 12, 8
        head_pts = [
            (hx - perp_x * hw + math.sin(head_angle) * hh,
             hy - perp_y * hw - math.cos(head_angle) * hh),
            (hx + perp_x * hw + math.sin(head_angle) * hh,
             hy + perp_y * hw - math.cos(head_angle) * hh),
            (hx + perp_x * hw - math.sin(head_angle) * hh,
             hy + perp_y * hw + math.cos(head_angle) * hh),
            (hx - perp_x * hw - math.sin(head_angle) * hh,
             hy - perp_y * hw + math.cos(head_angle) * hh),
        ]
        pygame.draw.polygon(self.surface, SILHOUETTE, head_pts)
        pygame.draw.polygon(self.surface, SILHOUETTE_EDGE, head_pts, 1)

        # --- Head ---
        head_y = by - torso_h // 2 - head_r + 15
        pygame.draw.circle(self.surface, SILHOUETTE, (bx + 2, int(head_y)), head_r)

        # Slight forge-side edge light on head and shoulder
        pygame.draw.arc(self.surface, SILHOUETTE_EDGE,
                        (bx + 2 - head_r, int(head_y) - head_r,
                         head_r * 2, head_r * 2),
                        -0.5, 1.2, 2)

    def _draw_ground(self):
        """Dark ground plane."""
        pygame.draw.rect(self.surface, GROUND,
                         (0, self.ground_y, self.width, self.scene_h - self.ground_y))
        # Ground edge highlight from forge
        glow_width = 200
        gcx = self.forge_cx
        for i in range(glow_width):
            t = 1.0 - (i / glow_width)
            c = (int(30 * t * self.metal_heat), int(8 * t), 0)
            x = gcx - glow_width // 2 + i
            if 0 <= x < self.width:
                pygame.draw.line(self.surface, c,
                                 (x, self.ground_y), (x, self.ground_y + 3))

    def _get_shake(self) -> tuple[int, int]:
        age = time.perf_counter() - self._shake_time
        if age > 0.12 or self._shake_intensity <= 0:
            return (0, 0)
        t = 1.0 - age / 0.12
        s = self._shake_intensity * t
        return (int(random.uniform(-s, s)), int(random.uniform(-s, s)))

    def _draw_timeline(self):
        self.timeline.draw(self.layers, self.cycle_phase)

    def render(self):
        self.surface.fill((5, 3, 2))

        # Update customers
        self._update_customers(self.dt)

        # Screen shake
        sx, sy = self._get_shake()

        # Draw order: glow → background → weapons → door/light → ground →
        #             forge → embers → anvil → customers → smith → door light on smith
        self._draw_forge_glow(self.cycle_phase)
        self._draw_background()
        self._draw_weapons()
        self._draw_door_and_light()
        self._draw_ground()
        self._draw_forge_structure()
        self._draw_rising_embers()
        self._draw_anvil()

        # Customers behind the smith
        for c in self._customers:
            self._draw_customer(c, self.cycle_phase)

        self._draw_smith_silhouette(self.cycle_phase)
        self._draw_smith_door_light()

        self._draw_timeline()

        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        # Bloom
        bloom = bloom_pass(self.surface, scale=4)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # Apply shake last
        if sx != 0 or sy != 0:
            temp = self.surface.copy()
            self.surface.fill((5, 3, 2))
            self.surface.blit(temp, (sx, sy))
