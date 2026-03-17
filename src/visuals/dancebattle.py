"""Dance battle visualizer.

Two dancers on a disco floor in a dance battle. A crowd watches.
A disco ball spins overhead. QTE-style arrow prompts appear in circles
above each dancer. Hit accuracy determines if they nail or fumble the move.
"""

import math
import random
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    BG_DARK, LAYER_COLORS, CYAN, MAGENTA, NEON_GREEN, HOT_PINK,
    YELLOW, ORANGE, PURPLE, rating_color, TEXT_DIM
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.visuals.timeline import Timeline
from src.visuals.speechbubble import SpeechBubbleState
from src.engine.scoring import HitRating


# Colors
FLOOR_DARK = (20, 15, 30)
FLOOR_TILE_A = (30, 20, 45)
FLOOR_TILE_B = (25, 18, 38)
WALL_COLOR = (15, 10, 22)
DISCO_CHROME = (200, 200, 210)
SPOTLIGHT_COLORS = [CYAN, MAGENTA, YELLOW, NEON_GREEN, HOT_PINK, ORANGE]

# Arrow directions
ARROWS = ["up", "down", "left", "right"]


# Speech pools
CPU_TAUNT_LINES = [
    "Is that all?", "Too slow!", "My turn!", "Watch this!",
    "You call that dancing?", "Yawn...", "Come on!", "Boring!",
]
CPU_SCARED_LINES = [
    "Wait, what?!", "Oh no...", "How?!", "Not bad...",
    "Lucky shot!", "Okay okay!", "Chill!!", "Help!",
]
CPU_SHOWOFF_LINES = [
    "Check THIS out!", "Easy!", "I'm on fire!", "Unstoppable!",
]
CPU_GRUDGING_RESPECT = [
    "Okay, not bad...", "Lucky.", "Hmph.", "Fine, that was decent.",
]
CPU_DISMISSIVE = [
    "Meh.", "Is that it?", "I've seen better.", "Whatever.",
    "Try harder.", "Cute.",
]

MODERATOR_PERFECT_LINES = [
    "INCREDIBLE MOVE!", "FLAWLESS!", "THE CROWD GOES WILD!",
    "UNBELIEVABLE!", "WHAT A HIT!", "PERFECTION!",
]
MODERATOR_GOOD_LINES = [
    "Nice one!", "Solid move!", "Keep it up!", "Great flow!",
]
MODERATOR_MISS_LINES = [
    "Oof, tough break!", "Ohhh, so close!", "That's gotta hurt!",
    "Shake it off!", "Come on, you got this!",
]
MODERATOR_HYPE_LINES = [
    "WHO'S GONNA WIN?!", "THE BATTLE HEATS UP!", "LET'S GOOO!",
    "ROUND AND ROUND!", "SHOW ME WHAT YOU GOT!",
    "THE FLOOR IS ON FIRE!", "THIS IS ELECTRIC!",
]

CROWD_POSITIVE = [
    "Wooo!", "Yeah!!", "Go go go!", "Sick moves!", "OMG!",
    "LETS GO!", "Wow!!", "Fire!!", "Amazing!",
]
CROWD_NEGATIVE = [
    "Boooo!", "Come on!", "Yikes...", "Oof!", "Not great...",
    "Do better!", "Meh...",
]
CROWD_HYPE = [
    "FIGHT!", "Dance! Dance!", "This is crazy!", "I love this!",
    "Best night ever!", "Who's winning?!", "So good!",
]


class Dancer:
    """A stick-figure dancer with pose states."""

    def __init__(self, x: float, y: float, color: tuple, facing: int):
        self.base_x = x
        self.base_y = y
        self.color = color
        self.facing = facing  # 1=right, -1=left

        self.pose = "idle"  # idle, up, down, left, right, fail
        self.pose_time = 0.0
        self.pose_duration = 0.4

    def set_pose(self, pose: str, duration: float = 0.4):
        self.pose = pose
        self.pose_time = time.perf_counter()
        self.pose_duration = duration

    def _pose_t(self) -> float:
        elapsed = time.perf_counter() - self.pose_time
        t = min(1.0, elapsed / self.pose_duration) if self.pose_duration > 0 else 1.0
        if t >= 1.0:
            self.pose = "idle"
        return t

    def draw(self, surface: pygame.Surface, beat_phase: float):
        t = self._pose_t()
        f = self.facing
        bob = math.sin(beat_phase * math.pi * 2) * 4

        cx = int(self.base_x)
        cy = int(self.base_y + bob)

        head_r = 12
        body_h = 36
        hip_y = cy + body_h // 2

        # Pose offsets
        arm_l_angle = 0.0  # radians from down
        arm_r_angle = 0.0
        leg_spread = 0
        head_offset_x = 0
        lean = 0

        swing = math.sin(t * math.pi)

        if self.pose == "up":
            arm_l_angle = -2.5 * swing
            arm_r_angle = -2.5 * swing
            cy -= int(8 * swing)
        elif self.pose == "down":
            cy += int(12 * swing)
            leg_spread = int(10 * swing)
        elif self.pose == "left":
            arm_l_angle = -2.0 * swing
            lean = int(-12 * swing)
            head_offset_x = int(-6 * swing)
        elif self.pose == "right":
            arm_r_angle = -2.0 * swing
            lean = int(12 * swing)
            head_offset_x = int(6 * swing)
        elif self.pose == "fail":
            lean = int(15 * swing * f)
            cy += int(5 * swing)
            arm_l_angle = 0.5 * swing
            arm_r_angle = -0.8 * swing
        elif self.pose == "taunt":
            # Cocky wave — one arm up waving, leaning toward opponent
            arm_r_angle = -2.8 * (0.5 + 0.5 * math.sin(time.perf_counter() * 10))
            lean = int(8 * f)
            head_offset_x = int(4 * f)
        elif self.pose == "showoff":
            # Spinning / wide arms
            spin = math.sin(time.perf_counter() * 8)
            arm_l_angle = -2.0 + spin * 0.5
            arm_r_angle = -2.0 - spin * 0.5
            lean = int(spin * 10)
            leg_spread = int(abs(spin) * 8)
        elif self.pose == "scared":
            # Cowering — arms up defensively, leaning back
            arm_l_angle = -2.2
            arm_r_angle = -2.2
            lean = int(-10 * f)
            cy += int(6 * (0.5 + 0.5 * math.sin(time.perf_counter() * 12)))
        elif self.pose == "groove":
            # Auto-dancing — rhythmic side-to-side
            beat_swing = math.sin(beat_phase * math.pi * 2)
            arm_l_angle = -1.5 * beat_swing
            arm_r_angle = 1.5 * beat_swing
            lean = int(beat_swing * 10)
            leg_spread = int(abs(beat_swing) * 6)
            head_offset_x = int(beat_swing * 4)

        cx += lean

        # Shadow on floor
        shadow_w = 20 + abs(lean)
        pygame.draw.ellipse(surface, (10, 8, 15),
                            (cx - shadow_w // 2, int(self.base_y + body_h // 2 + 25),
                             shadow_w, 6))

        # Legs
        foot_l = (cx - 8 - leg_spread, hip_y + 28)
        foot_r = (cx + 8 + leg_spread, hip_y + 28)
        pygame.draw.line(surface, self.color, (cx - 5, hip_y), foot_l, 4)
        pygame.draw.line(surface, self.color, (cx + 5, hip_y), foot_r, 4)

        # Body
        pygame.draw.line(surface, self.color, (cx, cy - 5), (cx, hip_y), 5)

        # Arms
        shoulder_y = cy
        arm_len = 22
        # Left arm
        la_x = cx - int(math.sin(arm_l_angle) * arm_len) - 8
        la_y = shoulder_y - int(math.cos(arm_l_angle) * arm_len) + 15
        pygame.draw.line(surface, self.color, (cx - 8, shoulder_y), (la_x, la_y), 4)
        # Right arm
        ra_x = cx + int(math.sin(arm_r_angle) * arm_len) + 8
        ra_y = shoulder_y - int(math.cos(arm_r_angle) * arm_len) + 15
        pygame.draw.line(surface, self.color, (cx + 8, shoulder_y), (ra_x, ra_y), 4)

        # Head
        head_y = cy - body_h // 2 + 5
        pygame.draw.circle(surface, self.color,
                           (cx + head_offset_x, int(head_y)), head_r)

        # Cap / hair accent
        pygame.draw.arc(surface, (min(255, self.color[0] + 40),
                                   min(255, self.color[1] + 40),
                                   min(255, self.color[2] + 40)),
                        (cx + head_offset_x - head_r, int(head_y) - head_r,
                         head_r * 2, head_r * 2),
                        0.3, 2.8, 3)


class DanceBattleVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem(max_particles=300)

        self.timeline_h = 60
        self.scene_h = self.height - self.timeline_h

        # Layout
        self.floor_y = int(self.scene_h * 0.65)
        self.cx = self.width // 2

        # Dancers
        dancer_gap = 120
        self.dancer_l = Dancer(self.cx - dancer_gap, self.floor_y - 30, CYAN, 1)
        self.dancer_r = Dancer(self.cx + dancer_gap, self.floor_y - 30, HOT_PINK, -1)

        # Disco ball
        self.disco_x = self.cx
        self.disco_y = int(self.scene_h * 0.12)
        self.disco_r = 20

        # Spotlight rotation
        self._spotlight_angle = 0.0

        # Crowd (silhouette heads along the back and sides)
        self._crowd = self._generate_crowd()

        # Floor tiles
        self.tile_size = 40
        self.n_tiles_x = self.width // self.tile_size + 2
        self.n_tiles_y = (self.scene_h - self.floor_y + 40) // self.tile_size + 2

        # Floor tile colors — some light up on beats
        self._lit_tiles: list[tuple[int, int, tuple, float]] = []

        # Arrow queue for upcoming beats
        self._pending_arrows: dict[int, str] = {}  # layer -> direction

        # Moderator — stands between dancers at the back
        self._moderator_x = self.cx
        self._moderator_y = self.floor_y - 65
        self._moderator_bubble = SpeechBubbleState()

        # Dancer speech bubbles
        self._dancer_l_bubble = SpeechBubbleState()
        self._dancer_r_bubble = SpeechBubbleState()

        # Crowd speech bubbles — pick random crowd members to talk
        # Each crowd member gets a bubble state
        for c in self._crowd:
            c["bubble"] = SpeechBubbleState()

        # Beat tracking
        self._beat_count = 0

        # CPU dancer AI state
        self._cpu_mood = "groove"  # groove, taunt, showoff, scared
        self._last_player_hit_time = 0.0
        self._player_recent_hits = 0  # good hits in last 8 beats
        self._player_recent_misses = 0  # misses in last 8 beats
        self._cpu_taunt_time = 0.0  # when CPU last taunted
        self._cpu_mood_time = 0.0

        # Timeline
        self.timeline = Timeline(self.surface, self.timeline_h)

        # Cached font
        self._label_font = pygame.font.SysFont("consolas", 12, bold=True)

    def _generate_crowd(self) -> list[dict]:
        crowd = []
        # Back row
        for x in range(30, self.width - 30, 25):
            y = self.floor_y - 70 + random.randint(-5, 5)
            color = random.choice([(50, 40, 60), (60, 45, 70), (45, 35, 55),
                                    (55, 50, 65), (65, 45, 75)])
            size = random.randint(7, 10)
            crowd.append({"x": x, "y": y, "color": color, "size": size,
                          "phase": random.uniform(0, math.pi * 2)})

        # Side clusters
        for x in range(20, 100, 22):
            y = self.floor_y - 20 + random.randint(-5, 5)
            crowd.append({"x": x, "y": y, "color": (55, 45, 65),
                          "size": random.randint(8, 11),
                          "phase": random.uniform(0, math.pi * 2)})
        for x in range(self.width - 100, self.width - 20, 22):
            y = self.floor_y - 20 + random.randint(-5, 5)
            crowd.append({"x": x, "y": y, "color": (55, 45, 65),
                          "size": random.randint(8, 11),
                          "phase": random.uniform(0, math.pi * 2)})

        return crowd

    def _update_cpu_mood(self):
        """Decide CPU dancer's mood based on player performance."""
        now = time.perf_counter()
        idle_time = now - self._last_player_hit_time

        # Player hasn't hit anything in a while — CPU taunts
        if idle_time > 3.0:
            self._cpu_mood = "taunt"
        # Player is messing up — CPU shows off
        elif self._player_recent_misses > self._player_recent_hits:
            self._cpu_mood = "showoff"
        # Player is doing great — CPU gets scared
        elif self._player_recent_hits >= 6:
            self._cpu_mood = "scared"
        # Normal — CPU just grooves
        else:
            self._cpu_mood = "groove"

    def on_beat(self, layer: int, beat_idx: int):
        self._beat_count += 1

        # Decay recent counters every 8 beats
        if self._beat_count % 8 == 0:
            self._player_recent_hits = max(0, self._player_recent_hits - 2)
            self._player_recent_misses = max(0, self._player_recent_misses - 2)

        # Queue an arrow direction for each layer
        direction = random.choice(ARROWS)
        self._pending_arrows[layer] = direction

        # Light up random floor tiles
        for _ in range(3):
            tx = random.randint(0, self.n_tiles_x - 1)
            ty = random.randint(0, self.n_tiles_y - 1)
            color = random.choice(SPOTLIGHT_COLORS)
            self._lit_tiles.append((tx, ty, color, time.perf_counter()))

        # CPU dancer behavior on each beat
        self._update_cpu_mood()

        # CPU always does something on beats — pose depends on mood
        if self.dancer_r.pose == "idle" or self.dancer_r._pose_t() >= 0.9:
            if self._cpu_mood == "taunt":
                self.dancer_r.set_pose("taunt", 0.6)
                if not self._dancer_r_bubble.active and random.random() < 0.3:
                    self._dancer_r_bubble.say(random.choice(CPU_TAUNT_LINES), 1.5)
            elif self._cpu_mood == "showoff":
                self.dancer_r.set_pose(random.choice(["showoff", "up", "down", "left", "right"]), 0.35)
                pass
                if not self._dancer_r_bubble.active and random.random() < 0.25:
                    self._dancer_r_bubble.say(random.choice(CPU_SHOWOFF_LINES), 1.5)
            elif self._cpu_mood == "scared":
                self.dancer_r.set_pose("scared", 0.5)
                if not self._dancer_r_bubble.active and random.random() < 0.3:
                    self._dancer_r_bubble.say(random.choice(CPU_SCARED_LINES), 1.5)
            else:
                self.dancer_r.set_pose("groove", 0.5)

        # Moderator hype — every 12 beats, or randomly
        if self._beat_count % 12 == 0 and not self._moderator_bubble.active:
            self._moderator_bubble.say(random.choice(MODERATOR_HYPE_LINES), 2.5)

        # Random crowd chatter every few beats
        if random.random() < 0.15:
            talkers = [c for c in self._crowd if not c["bubble"].active]
            if talkers:
                c = random.choice(talkers)
                c["bubble"].say(random.choice(CROWD_HYPE), 2.0)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = rating_color(rating)
        is_good = rating in (HitRating.PERFECT, HitRating.GOOD)

        # Track player performance
        self._last_player_hit_time = time.perf_counter()
        if is_good:
            self._player_recent_hits += 1
        elif rating == HitRating.MISS:
            self._player_recent_misses += 1

        # Get the pending arrow direction
        direction = self._pending_arrows.pop(layer, random.choice(ARROWS))

        # Player dancer performs the move or fails
        if layer == 0 or len(self.layers) == 1:
            if is_good:
                self.dancer_l.set_pose(direction, 0.35)
            elif rating == HitRating.OK:
                self.dancer_l.set_pose(direction, 0.4)
            else:
                self.dancer_l.set_pose("fail", 0.4)

            px, py = self.dancer_l.base_x, self.dancer_l.base_y - 20
            count = {HitRating.PERFECT: 15, HitRating.GOOD: 8,
                     HitRating.OK: 4, HitRating.MISS: 2}.get(rating, 4)
            self.particles.emit(px, py, color, count=count, speed=150, life=0.4)

        if layer == 1:
            if is_good:
                self.dancer_r.set_pose(direction, 0.35)
            elif rating == HitRating.OK:
                self.dancer_r.set_pose(direction, 0.4)
            else:
                self.dancer_r.set_pose("fail", 0.4)

            px, py = self.dancer_r.base_x, self.dancer_r.base_y - 20
            count = {HitRating.PERFECT: 15, HitRating.GOOD: 8,
                     HitRating.OK: 4, HitRating.MISS: 2}.get(rating, 4)
            self.particles.emit(px, py, color, count=count, speed=150, life=0.4)

        # CPU immediate reaction to player hits
        if (layer == 0 or len(self.layers) == 1) and not self._dancer_r_bubble.active:
            if rating == HitRating.PERFECT:
                if self._player_recent_hits >= 6:
                    self.dancer_r.set_pose("scared", 0.3)
                    self._dancer_r_bubble.say(random.choice(CPU_SCARED_LINES), 1.5)
                elif self._player_recent_hits >= 3:
                    self.dancer_r.set_pose("scared", 0.3)
                    self._dancer_r_bubble.say(random.choice(CPU_GRUDGING_RESPECT), 1.5)
                elif random.random() < 0.3:
                    self._dancer_r_bubble.say(random.choice(CPU_GRUDGING_RESPECT), 1.2)
            elif rating == HitRating.GOOD:
                if random.random() < 0.25:
                    self._dancer_r_bubble.say(random.choice(CPU_DISMISSIVE), 1.2)
            elif rating == HitRating.OK:
                if random.random() < 0.3:
                    self._dancer_r_bubble.say(random.choice(CPU_DISMISSIVE), 1.2)
            elif rating == HitRating.MISS:
                self.dancer_r.set_pose("taunt", 0.4)
                self._dancer_r_bubble.say(random.choice(CPU_TAUNT_LINES), 1.5)

        # Moderator commentary on hits
        if not self._moderator_bubble.active:
            if rating == HitRating.PERFECT:
                self._moderator_bubble.say(random.choice(MODERATOR_PERFECT_LINES), 2.0)
            elif rating == HitRating.GOOD and random.random() < 0.4:
                self._moderator_bubble.say(random.choice(MODERATOR_GOOD_LINES), 1.8)
            elif rating == HitRating.MISS and random.random() < 0.5:
                self._moderator_bubble.say(random.choice(MODERATOR_MISS_LINES), 2.0)

        # Crowd reacts to big moments
        if rating == HitRating.PERFECT or rating == HitRating.MISS:
            pool = CROWD_POSITIVE if is_good else CROWD_NEGATIVE
            talkers = [c for c in self._crowd if not c["bubble"].active]
            for c in random.sample(talkers, min(3, len(talkers))):
                c["bubble"].say(random.choice(pool), 1.8)

        # Timeline
        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self.timeline.flash_marker(layer, best_bi, color)
            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self.timeline.row_y(layer, len(self.layers))
            self.particles.emit(mx, my, color, count=8, speed=100, life=0.4)

        # Light up tiles on good hits
        if is_good:
            for _ in range(5):
                tx = random.randint(0, self.n_tiles_x - 1)
                ty = random.randint(0, self.n_tiles_y - 1)
                self._lit_tiles.append((tx, ty, color, time.perf_counter()))

    def _draw_background(self):
        """Dark club walls."""
        self.surface.fill(WALL_COLOR)
        # Gradient toward floor
        for y in range(int(self.scene_h * 0.3), self.floor_y):
            t = (y - self.scene_h * 0.3) / max(1, self.floor_y - self.scene_h * 0.3)
            r = int(15 + t * 10)
            g = int(10 + t * 8)
            b = int(22 + t * 15)
            pygame.draw.line(self.surface, (r, g, b), (0, y), (self.width, y))

    def _draw_floor(self):
        """Checkered dance floor with lit tiles."""
        now = time.perf_counter()

        for ty in range(self.n_tiles_y):
            for tx in range(self.n_tiles_x):
                px = tx * self.tile_size
                py = self.floor_y + ty * self.tile_size

                if py > self.scene_h:
                    continue

                base = FLOOR_TILE_A if (tx + ty) % 2 == 0 else FLOOR_TILE_B
                color = base

                # Check if lit
                for ltx, lty, lc, lt in self._lit_tiles:
                    if ltx == tx and lty == ty:
                        age = now - lt
                        if age < 0.5:
                            t = 1.0 - age / 0.5
                            color = (min(255, base[0] + int(lc[0] * t * 0.4)),
                                     min(255, base[1] + int(lc[1] * t * 0.4)),
                                     min(255, base[2] + int(lc[2] * t * 0.4)))

                pygame.draw.rect(self.surface, color,
                                 (px, py, self.tile_size - 1, self.tile_size - 1))

        # Cleanup old lit tiles
        self._lit_tiles = [(tx, ty, c, t) for tx, ty, c, t in self._lit_tiles
                           if now - t < 0.5]

    def _draw_disco_ball(self, beat_phase: float):
        """Spinning disco ball with light rays."""
        bx, by = self.disco_x, self.disco_y

        # String
        pygame.draw.line(self.surface, (80, 80, 80), (bx, 0), (bx, by - self.disco_r), 1)

        # Ball
        pygame.draw.circle(self.surface, DISCO_CHROME, (bx, by), self.disco_r)

        # Facets (rotating pattern)
        angle_offset = time.perf_counter() * 2
        for i in range(8):
            angle = angle_offset + i * math.pi / 4
            fx = bx + int(self.disco_r * 0.6 * math.cos(angle))
            fy = by + int(self.disco_r * 0.6 * math.sin(angle))
            facet_bright = int(180 + 60 * math.sin(angle + angle_offset * 3))
            pygame.draw.circle(self.surface, (facet_bright, facet_bright, facet_bright + 10),
                               (fx, fy), 4)

        # Highlight
        pygame.draw.circle(self.surface, (240, 240, 250),
                           (bx - 5, by - 5), 6)

        # Light rays
        self._spotlight_angle = time.perf_counter() * 1.5
        n_rays = 6
        for i in range(n_rays):
            ray_angle = self._spotlight_angle + i * math.pi * 2 / n_rays
            ray_len = 200 + math.sin(time.perf_counter() * 3 + i) * 50
            rx = bx + int(math.cos(ray_angle) * ray_len)
            ry = by + int(math.sin(ray_angle) * abs(ray_len) * 0.7)

            ray_color = SPOTLIGHT_COLORS[i % len(SPOTLIGHT_COLORS)]
            dim = tuple(max(0, c // 6) for c in ray_color)

            pygame.draw.line(self.surface, dim, (bx, by), (rx, ry), 2)

    def _draw_crowd(self, beat_phase: float):
        """Crowd silhouettes bobbing to the beat, with speech bubbles."""
        for c in self._crowd:
            bounce = math.sin(beat_phase * math.pi * 2 + c["phase"]) * 3
            x, y = int(c["x"]), int(c["y"] + bounce)
            s = c["size"]

            # Head
            pygame.draw.circle(self.surface, c["color"], (x, y - s), s)
            # Body hint
            pygame.draw.rect(self.surface, c["color"],
                             (x - s // 2, y - s // 2, s, s + 3))

            # Speech bubble
            c["bubble"].draw(self.surface, x, y - s * 2 - 5)

    def _draw_labels(self):
        """P1/P2 labels under dancers."""
        label_l = self._label_font.render("P1 (YOU)", True, CYAN)
        label_r = self._label_font.render("P2", True, HOT_PINK)
        self.surface.blit(label_l, (int(self.dancer_l.base_x) - label_l.get_width() // 2,
                                     self.floor_y + 2))
        self.surface.blit(label_r, (int(self.dancer_r.base_x) - label_r.get_width() // 2,
                                     self.floor_y + 2))

    def _draw_vs(self):
        """VS text between dancers."""
        font = self._label_font
        vs = font.render("VS", True, YELLOW)
        self.surface.blit(vs, (self.cx - vs.get_width() // 2,
                                self.floor_y - 40))

    def _draw_moderator(self, beat_phase: float):
        """Moderator figure at the back center, with a microphone."""
        mx, my = self._moderator_x, self._moderator_y
        bob = math.sin(beat_phase * math.pi * 2) * 2

        # Body silhouette (slightly bigger, stands out)
        cx, cy = mx, int(my + bob)
        color = (80, 70, 100)  # Brighter than crowd

        # Legs
        pygame.draw.line(self.surface, color, (cx - 5, cy + 15), (cx - 7, cy + 30), 4)
        pygame.draw.line(self.surface, color, (cx + 5, cy + 15), (cx + 7, cy + 30), 4)
        # Body
        pygame.draw.rect(self.surface, color, (cx - 10, cy - 10, 20, 28), border_radius=4)
        # Head
        pygame.draw.circle(self.surface, color, (cx, cy - 18), 10)
        # Mic arm (right arm extended with mic)
        mic_x = cx + 15
        mic_y = cy - 8
        pygame.draw.line(self.surface, color, (cx + 8, cy - 2), (mic_x, mic_y), 3)
        pygame.draw.circle(self.surface, (120, 110, 130), (mic_x + 3, mic_y - 2), 4)

        # Moderator speech bubble
        self._moderator_bubble.draw(self.surface, cx, cy - 32,
                                     text_color=(255, 255, 200))

    def render(self):
        self._draw_background()
        self._draw_floor()
        self._draw_crowd(self.cycle_phase)
        self._draw_disco_ball(self.cycle_phase)

        # Moderator behind dancers
        self._draw_moderator(self.cycle_phase)

        # Dancers
        self.dancer_l.draw(self.surface, self.cycle_phase)
        self.dancer_r.draw(self.surface, self.cycle_phase)

        # Dancer speech bubbles
        self._dancer_l_bubble.draw(self.surface,
                                    int(self.dancer_l.base_x),
                                    int(self.dancer_l.base_y) - 65,
                                    text_color=CYAN)
        self._dancer_r_bubble.draw(self.surface,
                                    int(self.dancer_r.base_x),
                                    int(self.dancer_r.base_y) - 65,
                                    text_color=HOT_PINK)

        self._draw_labels()
        self._draw_vs()

        # Timeline
        self.timeline.draw(self.layers, self.cycle_phase)

        # Particles
        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        # Bloom
        bloom = bloom_pass(self.surface, scale=6)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
