"""Samurai duel visualizer.

Two samurai silhouettes face off on a moonlit bridge.
Each beat is a sword clash. Accuracy determines who wins the exchange.
Cherry blossom petals drift in the wind.
"""

import math
import random
import time
import pygame
from src.visuals.base import BaseVisualizer
from src.visuals.colors import (
    LAYER_COLORS, CYAN, MAGENTA, NEON_GREEN, HOT_PINK,
    YELLOW, ORANGE, rating_color
)
from src.visuals.effects import bloom_pass, ParticleSystem
from src.visuals.timeline import Timeline
from src.visuals.speechbubble import SpeechBubbleState
from src.engine.scoring import HitRating


# Scene colors
SKY_TOP = (8, 10, 25)
SKY_BOTTOM = (15, 18, 40)
MOON_COLOR = (220, 215, 200)
MOON_GLOW = (40, 38, 50)
BRIDGE_DARK = (20, 15, 12)
BRIDGE_RAIL = (30, 22, 18)
BRIDGE_PLANK = (25, 18, 14)
WATER_COLOR = (8, 12, 30)
WATER_REFLECT = (15, 20, 45)
SILHOUETTE = (5, 3, 8)
SWORD_COLOR = (180, 190, 200)
SWORD_FLASH = (255, 255, 240)
CLASH_COLOR = (255, 240, 180)

# Petal colors (cherry blossom)
PETAL_COLORS = [(220, 140, 160), (240, 160, 170), (200, 120, 140),
                (230, 150, 165), (210, 130, 150)]

# Speech pools
PLAYER_PERFECT = ["Hah!", "Too slow!", "...pathetic.", "Like water."]
PLAYER_GOOD = ["Hmph.", "Decent.", "Not bad."]
CPU_TAUNT = ["You hesitate.", "Weakness.", "Is that all?", "Predictable."]
CPU_SCARED = ["...!", "How?!", "Impossible!", "You've grown."]
CPU_HIT = ["Tch!", "Urgh!", "...well played."]


class Petal:
    """A cherry blossom petal drifting in wind."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = random.uniform(-20, -40)
        self.vy = random.uniform(10, 30)
        self.spin = random.uniform(-3, 3)
        self.angle = random.uniform(0, math.pi * 2)
        self.size = random.uniform(2, 4)
        self.color = random.choice(PETAL_COLORS)
        self.life = random.uniform(4, 8)

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.spin * dt
        # Wind gusts
        self.vx += math.sin(time.perf_counter() * 0.5 + self.y * 0.01) * dt * 5
        self.life -= dt
        return self.life > 0 and self.y < 800

    def draw(self, surface: pygame.Surface):
        alpha = min(1.0, self.life / 2.0)
        c = tuple(int(v * alpha) for v in self.color)
        x, y = int(self.x), int(self.y)
        s = self.size
        # Elongated petal shape
        dx = math.cos(self.angle) * s
        dy = math.sin(self.angle) * s
        pygame.draw.line(surface, c, (x - int(dx), y - int(dy)),
                         (x + int(dx), y + int(dy)), max(1, int(s * 0.7)))


class Samurai:
    """A samurai silhouette with sword poses."""

    def __init__(self, x: float, y: float, facing: int):
        self.base_x = x
        self.base_y = y
        self.facing = facing  # 1 = right, -1 = left

        self.pose = "ready"  # ready, slash, parry, hit, pushed, dodge
        self.pose_time = 0.0
        self.pose_duration = 0.3

        # Position offset from clashes
        self.push_x = 0.0

    def set_pose(self, pose: str, duration: float = 0.3):
        self.pose = pose
        self.pose_time = time.perf_counter()
        self.pose_duration = duration

    def _pose_t(self) -> float:
        elapsed = time.perf_counter() - self.pose_time
        t = min(1.0, elapsed / self.pose_duration) if self.pose_duration > 0 else 1.0
        if t >= 1.0 and self.pose not in ("ready",):
            self.pose = "ready"
        return t

    def draw(self, surface: pygame.Surface, beat_phase: float):
        t = self._pose_t()
        f = self.facing
        swing = math.sin(t * math.pi)

        sway = math.sin(beat_phase * math.pi * 2) * 1.5
        self.push_x *= 0.92

        cx = int(self.base_x + self.push_x)
        cy = int(self.base_y + sway)

        # Pose adjustments
        lean = 0
        sword_angle = f * 0.3  # Resting: katana angled forward slightly
        crouch = 0
        arm_reach = 0

        if self.pose == "slash":
            lean = int(f * 22 * swing)
            sword_angle = f * (-1.8 + 3.5 * min(1.0, t * 2.5))
            arm_reach = int(swing * 30)
            crouch = int(swing * 6)
        elif self.pose == "parry":
            sword_angle = f * -1.0
            arm_reach = 12
        elif self.pose == "hit":
            lean = int(-f * 15 * swing)
            crouch = int(swing * 8)
        elif self.pose == "pushed":
            lean = int(-f * 25 * swing)
            self.push_x -= f * 4 * swing
            crouch = int(swing * 5)
        elif self.pose == "dodge":
            crouch = int(swing * 15)
            lean = int(-f * 10 * swing)

        cx += lean
        cy += crouch

        # --- Hakama (wide pleated pants) ---
        # Wide flared shape from waist to feet
        waist_y = cy + 10
        hem_y = cy + 55
        waist_hw = 14  # Half-width at waist
        hem_hw = 28    # Half-width at hem (wide flare)

        hakama_pts = [
            (cx - waist_hw, waist_y),
            (cx + waist_hw, waist_y),
            (cx + hem_hw, hem_y),
            (cx + hem_hw // 3, hem_y + 3),  # Center dip
            (cx - hem_hw // 3, hem_y + 3),
            (cx - hem_hw, hem_y),
        ]
        pygame.draw.polygon(surface, SILHOUETTE, hakama_pts)

        # Hakama pleats (subtle vertical lines)
        edge = (10, 7, 14)
        for px_off in [-8, 0, 8]:
            pygame.draw.line(surface, edge,
                             (cx + px_off, waist_y + 3),
                             (cx + px_off, hem_y - 2), 1)

        # Feet (sandals peeking out)
        pygame.draw.ellipse(surface, SILHOUETTE,
                            (cx - hem_hw + 2, hem_y, 14, 5))
        pygame.draw.ellipse(surface, SILHOUETTE,
                            (cx + hem_hw - 16, hem_y, 14, 5))

        # --- Kimono top / torso ---
        shoulder_hw = 22  # Wide kimono shoulders
        torso_top = cy - 15
        kimono_pts = [
            (cx - shoulder_hw, torso_top),
            (cx + shoulder_hw, torso_top),
            (cx + waist_hw + 2, waist_y + 2),
            (cx - waist_hw - 2, waist_y + 2),
        ]
        pygame.draw.polygon(surface, SILHOUETTE, kimono_pts)

        # Kimono collar (V-shape neckline)
        neck_y = torso_top + 5
        pygame.draw.line(surface, edge, (cx - 3, neck_y), (cx - 8, waist_y - 5), 1)
        pygame.draw.line(surface, edge, (cx + 3, neck_y), (cx + 8, waist_y - 5), 1)

        # Obi (belt/sash at waist)
        obi_y = waist_y - 3
        pygame.draw.rect(surface, (8, 5, 12),
                         (cx - waist_hw - 1, obi_y, waist_hw * 2 + 2, 8),
                         border_radius=2)
        # Obi knot on the back
        pygame.draw.circle(surface, SILHOUETTE, (cx - f * 12, obi_y + 4), 5)

        # --- Back arm (tucked or at side) ---
        back_s = (cx - f * shoulder_hw + f * 3, torso_top + 8)
        back_elbow = (back_s[0] - f * 12, back_s[1] + 15)
        back_hand = (back_elbow[0] - f * 5, back_elbow[1] + 10)
        pygame.draw.line(surface, SILHOUETTE, back_s, back_elbow, 5)
        pygame.draw.line(surface, SILHOUETTE, back_elbow, back_hand, 4)

        # --- Sword arm ---
        sword_s = (cx + f * shoulder_hw - f * 3, torso_top + 8)
        s_elbow = (sword_s[0] + f * 15 + arm_reach // 2, sword_s[1] + 10)
        hand_x = s_elbow[0] + int(math.cos(sword_angle) * 16) + arm_reach * f // 2
        hand_y = s_elbow[1] + int(math.sin(sword_angle) * 16) - 5
        pygame.draw.line(surface, SILHOUETTE, sword_s, s_elbow, 5)
        pygame.draw.line(surface, SILHOUETTE, s_elbow, (hand_x, hand_y), 5)

        # --- Katana ---
        katana_len = 55
        tip_x = hand_x + int(math.cos(sword_angle) * katana_len)
        tip_y = hand_y + int(math.sin(sword_angle) * katana_len)

        # Blade (slight curve via intermediate point)
        mid_x = hand_x + int(math.cos(sword_angle) * katana_len * 0.5)
        mid_y = hand_y + int(math.sin(sword_angle) * katana_len * 0.5) - 3

        if self.pose == "slash" and t < 0.4:
            blade_color = SWORD_FLASH
            blade_w = 3
        else:
            blade_color = SWORD_COLOR
            blade_w = 2

        pygame.draw.line(surface, blade_color, (hand_x, hand_y), (mid_x, mid_y), blade_w)
        pygame.draw.line(surface, blade_color, (mid_x, mid_y), (tip_x, tip_y), blade_w)

        # Tsuba (hand guard — small circle)
        pygame.draw.circle(surface, (80, 70, 55), (hand_x, hand_y), 4)

        # Tsuka (handle wrap) — short line behind the guard
        handle_x = hand_x - int(math.cos(sword_angle) * 12)
        handle_y = hand_y - int(math.sin(sword_angle) * 12)
        pygame.draw.line(surface, (50, 40, 30), (hand_x, hand_y),
                         (handle_x, handle_y), 3)

        # Slash trail (arc effect on slash)
        if self.pose == "slash" and t < 0.5:
            trail_alpha = 1.0 - t / 0.5
            trail_color = (int(180 * trail_alpha), int(190 * trail_alpha), int(200 * trail_alpha))
            # Arc from raised to current position
            for i in range(3):
                trail_t = max(0, t - i * 0.05)
                tr_angle = f * (-1.8 + 3.5 * min(1.0, trail_t * 2.5))
                tr_tip_x = hand_x + int(math.cos(tr_angle) * katana_len)
                tr_tip_y = hand_y + int(math.sin(tr_angle) * katana_len)
                tr_mid_x = hand_x + int(math.cos(tr_angle) * katana_len * 0.6)
                tr_mid_y = hand_y + int(math.sin(tr_angle) * katana_len * 0.6) - 2
                a = max(0, trail_alpha - i * 0.25)
                tc = tuple(int(c * a) for c in trail_color)
                pygame.draw.line(surface, tc, (tr_mid_x, tr_mid_y), (tr_tip_x, tr_tip_y), 1)

        # --- Head ---
        head_r = 12
        head_y = torso_top - head_r + 3
        pygame.draw.circle(surface, SILHOUETTE, (cx, int(head_y)), head_r)

        # Chonmage (topknot hairstyle)
        # Shaved front, hair gathered on top
        tk_cx = cx
        tk_cy = int(head_y) - head_r + 4
        # Hair bun on top
        pygame.draw.ellipse(surface, SILHOUETTE,
                            (tk_cx - 6, tk_cy - 4, 12, 8))
        # Tail going backward
        tail_end_x = tk_cx - f * 12
        tail_end_y = tk_cy + 2
        pygame.draw.line(surface, SILHOUETTE, (tk_cx, tk_cy),
                         (tail_end_x, tail_end_y), 3)
        pygame.draw.circle(surface, SILHOUETTE, (tail_end_x, tail_end_y), 3)

        # Moon edge highlight (faint light from the right)
        highlight_side = 1  # Moon is on the right
        hx = cx + highlight_side * (head_r - 2)
        pygame.draw.arc(surface, (18, 16, 25),
                        (cx - head_r, int(head_y) - head_r, head_r * 2, head_r * 2),
                        -0.8, 0.8, 1)
        # Shoulder edge light
        pygame.draw.line(surface, (15, 13, 20),
                         (cx + highlight_side * shoulder_hw, torso_top),
                         (cx + highlight_side * (waist_hw + 2), waist_y), 1)

        return (hand_x, hand_y, tip_x, tip_y)


class SamuraiVisualizer(BaseVisualizer):

    def __init__(self, surface: pygame.Surface):
        super().__init__(surface)
        self.particles = ParticleSystem(max_particles=300)

        self.timeline_h = 60
        self.scene_h = self.height - self.timeline_h

        # Layout
        self.bridge_y = int(self.scene_h * 0.72)
        self.water_y = int(self.scene_h * 0.82)
        self.moon_x = int(self.width * 0.75)
        self.moon_y = int(self.scene_h * 0.18)
        self.moon_r = 45

        # Samurai
        gap = 80
        samurai_y = self.bridge_y - 50
        self.player = Samurai(self.width // 2 - gap, samurai_y, 1)
        self.cpu = Samurai(self.width // 2 + gap, samurai_y, -1)

        # Clash point (between them)
        self.clash_x = self.width // 2
        self.clash_y = samurai_y - 5

        # Clash flash
        self._clash_time = 0.0
        self._clash_intensity = 0.0

        # Cherry blossom petals
        self._petals: list[Petal] = []

        # Speech bubbles
        self._player_bubble = SpeechBubbleState()
        self._cpu_bubble = SpeechBubbleState()

        # Health system
        self._player_hp = 100.0
        self._player_max_hp = 100.0
        self._cpu_hp = 100.0
        self._cpu_max_hp = 100.0
        self._player_deaths = 0
        self._cpu_deaths = 0
        self._resurrect_time = 0.0

        # CPU state
        self._recent_good = 0
        self._recent_miss = 0
        self._beat_count = 0

        # Timeline
        self.timeline = Timeline(self.surface, self.timeline_h)
        self._label_font = pygame.font.SysFont("consolas", 12, bold=True)

    def on_beat(self, layer: int, beat_idx: int):
        self._beat_count += 1

        # Spawn petals
        for _ in range(random.randint(1, 3)):
            self._petals.append(Petal(
                random.randint(0, self.width + 50),
                random.randint(-20, int(self.scene_h * 0.3))
            ))

        # Decay counters
        if self._beat_count % 6 == 0:
            self._recent_good = max(0, self._recent_good - 1)
            self._recent_miss = max(0, self._recent_miss - 1)

        # CPU idle actions — attacks when player is struggling
        if self.cpu.pose == "ready":
            if self._recent_miss >= 3:
                self.cpu.set_pose("slash", 0.2)
                # CPU chip damage when taunting
                self._player_hp = max(0, self._player_hp - 3)
                if not self._cpu_bubble.active and random.random() < 0.25:
                    self._cpu_bubble.say(random.choice(CPU_TAUNT), 2.0)
            elif self._recent_good >= 5 and random.random() < 0.2:
                if not self._cpu_bubble.active:
                    self._cpu_bubble.say(random.choice(CPU_SCARED), 2.0)

        # CPU slowly heals when player is doing badly
        if self._recent_miss > self._recent_good:
            self._cpu_hp = min(self._cpu_max_hp, self._cpu_hp + 1)

        # Check player death from chip damage
        if self._player_hp <= 0:
            self._player_deaths += 1
            self._player_hp = self._player_max_hp
            self._resurrect_time = time.perf_counter()
            if not self._cpu_bubble.active:
                self._cpu_bubble.say("Pathetic.", 2.0)

    def on_hit(self, layer: int, rating: str, deviation_ms: float):
        color = rating_color(rating)
        is_good = rating in (HitRating.PERFECT, HitRating.GOOD)
        now = time.perf_counter()

        if is_good:
            self._recent_good += 1
        elif rating == HitRating.MISS:
            self._recent_miss += 1

        # Clash!
        self._clash_time = now

        # Damage values
        dmg_to_cpu = 0
        dmg_to_player = 0

        if rating == HitRating.PERFECT:
            self.player.set_pose("slash", 0.25)
            self.cpu.set_pose("pushed", 0.35)
            self._clash_intensity = 1.0
            dmg_to_cpu = 15

            self.particles.emit(self.clash_x, self.clash_y, CLASH_COLOR,
                                count=20, speed=250, life=0.5, size=4)
            self.particles.emit(self.clash_x, self.clash_y, SWORD_FLASH,
                                count=10, speed=180, life=0.3, size=2)

            if not self._player_bubble.active and random.random() < 0.3:
                self._player_bubble.say(random.choice(PLAYER_PERFECT), 1.8)
            if not self._cpu_bubble.active and random.random() < 0.4:
                self._cpu_bubble.say(random.choice(CPU_HIT), 1.5)

        elif rating == HitRating.GOOD:
            self.player.set_pose("slash", 0.25)
            self.cpu.set_pose("parry", 0.3)
            self._clash_intensity = 0.6
            dmg_to_cpu = 8

            self.particles.emit(self.clash_x, self.clash_y, SWORD_COLOR,
                                count=10, speed=150, life=0.3, size=3)

            if not self._player_bubble.active and random.random() < 0.2:
                self._player_bubble.say(random.choice(PLAYER_GOOD), 1.5)

        elif rating == HitRating.OK:
            self.player.set_pose("slash", 0.3)
            self.cpu.set_pose("parry", 0.25)
            self._clash_intensity = 0.3
            dmg_to_cpu = 3

            self.particles.emit(self.clash_x, self.clash_y, (120, 120, 130),
                                count=5, speed=80, life=0.2, size=2)

        else:  # MISS — CPU counter-attacks
            self.player.set_pose("hit", 0.35)
            self.cpu.set_pose("slash", 0.25)
            self._clash_intensity = 0.4
            dmg_to_player = 12

            self.particles.emit(self.clash_x - 30, self.clash_y, (150, 50, 50),
                                count=4, speed=60, life=0.2, size=2)

            if not self._cpu_bubble.active:
                self._cpu_bubble.say(random.choice(CPU_TAUNT), 1.8)

        # Apply damage
        self._cpu_hp = max(0, self._cpu_hp - dmg_to_cpu)
        self._player_hp = max(0, self._player_hp - dmg_to_player)

        # Check deaths
        if self._cpu_hp <= 0:
            self._cpu_deaths += 1
            self._cpu_hp = self._cpu_max_hp
            if not self._player_bubble.active:
                self._player_bubble.say("...it is done.", 2.5)
            # Big death burst
            self.particles.emit(int(self.cpu.base_x), int(self.cpu.base_y),
                                CLASH_COLOR, count=30, speed=200, life=0.6, size=4)

        if self._player_hp <= 0:
            self._player_deaths += 1
            self._player_hp = self._player_max_hp
            self._resurrect_time = now
            if not self._cpu_bubble.active:
                self._cpu_bubble.say("Weak.", 2.0)
            self.particles.emit(int(self.player.base_x), int(self.player.base_y),
                                (150, 50, 50), count=20, speed=150, life=0.5, size=3)

        # Timeline
        if layer < len(self.layers):
            phases = self.layers[layer]["phases"]
            best_bi = self._find_nearest_beat(phases, self.cycle_phase)
            self.timeline.flash_marker(layer, best_bi, color)
            margin = 40
            mx = margin + int(phases[best_bi] * (self.width - 2 * margin))
            my = self.timeline.row_y(layer, len(self.layers))
            self.particles.emit(mx, my, color, count=8, speed=100, life=0.4)

    def _draw_sky(self):
        """Gradient night sky."""
        for y in range(int(self.scene_h)):
            t = y / self.scene_h
            r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
            pygame.draw.line(self.surface, (r, g, b), (0, y), (self.width, y))

        # Stars
        rng = random.Random(42)
        for _ in range(60):
            sx = rng.randint(0, self.width)
            sy = rng.randint(0, int(self.scene_h * 0.6))
            brightness = rng.randint(60, 160)
            twinkle = int(brightness * (0.7 + 0.3 * math.sin(
                time.perf_counter() * rng.uniform(1, 4) + rng.uniform(0, 6))))
            pygame.draw.circle(self.surface, (twinkle, twinkle, twinkle + 10),
                               (sx, sy), 1)

    def _draw_moon(self):
        """Full moon with glow."""
        mx, my, mr = self.moon_x, self.moon_y, self.moon_r

        # Glow
        for r in range(mr + 40, mr, -3):
            alpha = int(15 * ((r - mr) / 40))
            pygame.draw.circle(self.surface, MOON_GLOW, (mx, my), r)

        # Moon face
        pygame.draw.circle(self.surface, MOON_COLOR, (mx, my), mr)
        # Craters (subtle)
        rng = random.Random(77)
        for _ in range(5):
            cx = mx + rng.randint(-mr + 10, mr - 10)
            cy = my + rng.randint(-mr + 10, mr - 10)
            cr = rng.randint(4, 10)
            pygame.draw.circle(self.surface, (200, 195, 185), (cx, cy), cr)

    def _draw_bridge(self):
        """Wooden bridge silhouette."""
        by = self.bridge_y

        # Bridge deck
        pygame.draw.rect(self.surface, BRIDGE_DARK,
                         (self.width * 0.1, by, self.width * 0.8, 15))

        # Planks
        for px in range(int(self.width * 0.1), int(self.width * 0.9), 20):
            pygame.draw.line(self.surface, BRIDGE_PLANK,
                             (px, by), (px, by + 14), 1)

        # Rails
        rail_h = 35
        for rx in [int(self.width * 0.12), int(self.width * 0.88)]:
            pygame.draw.line(self.surface, BRIDGE_RAIL,
                             (rx, by - rail_h), (rx, by), 4)
        pygame.draw.line(self.surface, BRIDGE_RAIL,
                         (int(self.width * 0.12), by - rail_h),
                         (int(self.width * 0.88), by - rail_h), 3)

        # Support posts
        for sx in range(int(self.width * 0.2), int(self.width * 0.85), 100):
            pygame.draw.line(self.surface, BRIDGE_DARK,
                             (sx, by + 15), (sx + 5, self.water_y), 5)
            pygame.draw.line(surface=self.surface, color=BRIDGE_DARK,
                             start_pos=(sx + 30, by + 15),
                             end_pos=(sx + 25, self.water_y), width=5)

    def _draw_water(self):
        """Water with moonlight reflection."""
        wy = self.water_y

        pygame.draw.rect(self.surface, WATER_COLOR,
                         (0, wy, self.width, self.scene_h - wy))

        # Moon reflection
        mx = self.moon_x
        reflect_y = wy + 10
        for i in range(15):
            ry = reflect_y + i * 4
            wobble = math.sin(time.perf_counter() * 2 + i * 0.5) * (3 + i)
            w = max(2, 30 - i * 2)
            brightness = max(0, 30 - i * 2)
            pygame.draw.line(self.surface, (brightness + 10, brightness + 10, brightness + 20),
                             (mx - w + int(wobble), ry),
                             (mx + w + int(wobble), ry), 1)

        # Ripples
        for rx in range(0, self.width, 80):
            rng = random.Random(rx)
            wobble = math.sin(time.perf_counter() * 1.5 + rx * 0.02) * 2
            ry = wy + 5 + int(wobble)
            pygame.draw.line(self.surface, WATER_REFLECT,
                             (rx, ry), (rx + rng.randint(15, 35), ry), 1)

    def _draw_clash_flash(self):
        """Flash at the clash point."""
        age = time.perf_counter() - self._clash_time
        if age > 0.2 or self._clash_intensity <= 0:
            return
        t = (1.0 - age / 0.2) * self._clash_intensity

        # Cross spark
        cx, cy = self.clash_x, self.clash_y
        length = int(25 * t)
        brightness = int(255 * t)
        c = (brightness, brightness, int(brightness * 0.8))

        for angle in [0, math.pi / 4, math.pi / 2, 3 * math.pi / 4]:
            dx = int(math.cos(angle) * length)
            dy = int(math.sin(angle) * length)
            pygame.draw.line(self.surface, c,
                             (cx - dx, cy - dy), (cx + dx, cy + dy), max(1, int(2 * t)))

    def _draw_health_bars(self):
        """Health bars at the top of the screen, fighting game style."""
        bar_w = 250
        bar_h = 14
        y = 18
        margin = 30

        # Player bar (left, fills right to left)
        px = margin
        player_pct = self._player_hp / self._player_max_hp
        # Background
        pygame.draw.rect(self.surface, (20, 15, 25),
                         (px, y, bar_w, bar_h), border_radius=3)
        # Fill
        fill_w = int(bar_w * player_pct)
        if player_pct > 0.5:
            bar_color = CYAN
        elif player_pct > 0.25:
            bar_color = YELLOW
        else:
            bar_color = (200, 50, 50)
        if fill_w > 0:
            pygame.draw.rect(self.surface, bar_color,
                             (px, y, fill_w, bar_h), border_radius=3)
        # Border
        pygame.draw.rect(self.surface, (60, 55, 70),
                         (px, y, bar_w, bar_h), 1, border_radius=3)
        # Label
        label = self._label_font.render(f"YOU  {int(self._player_hp)}", True, CYAN)
        self.surface.blit(label, (px + 5, y - 1))
        # Deaths
        if self._player_deaths > 0:
            deaths = self._label_font.render(f"Deaths: {self._player_deaths}", True, (120, 60, 60))
            self.surface.blit(deaths, (px, y + bar_h + 3))

        # CPU bar (right, fills left to right)
        cpu_x = self.width - margin - bar_w
        cpu_pct = self._cpu_hp / self._cpu_max_hp
        # Background
        pygame.draw.rect(self.surface, (20, 15, 25),
                         (cpu_x, y, bar_w, bar_h), border_radius=3)
        # Fill (from right)
        cpu_fill_w = int(bar_w * cpu_pct)
        if cpu_pct > 0.5:
            cpu_bar_color = HOT_PINK
        elif cpu_pct > 0.25:
            cpu_bar_color = YELLOW
        else:
            cpu_bar_color = (200, 50, 50)
        if cpu_fill_w > 0:
            pygame.draw.rect(self.surface, cpu_bar_color,
                             (cpu_x + bar_w - cpu_fill_w, y, cpu_fill_w, bar_h), border_radius=3)
        # Border
        pygame.draw.rect(self.surface, (60, 55, 70),
                         (cpu_x, y, bar_w, bar_h), 1, border_radius=3)
        # Label
        cpu_label = self._label_font.render(f"{int(self._cpu_hp)}  CPU", True, HOT_PINK)
        self.surface.blit(cpu_label, (cpu_x + bar_w - cpu_label.get_width() - 5, y - 1))
        # Kills
        if self._cpu_deaths > 0:
            kills = self._label_font.render(f"Kills: {self._cpu_deaths}", True, NEON_GREEN)
            self.surface.blit(kills, (cpu_x + bar_w - kills.get_width(), y + bar_h + 3))

        # VS in center
        vs = self._label_font.render("VS", True, (100, 90, 80))
        self.surface.blit(vs, (self.width // 2 - vs.get_width() // 2, y))

    def _draw_labels(self):
        you = self._label_font.render("YOU", True, CYAN)
        cpu = self._label_font.render("CPU", True, HOT_PINK)
        self.surface.blit(you, (int(self.player.base_x) - you.get_width() // 2,
                                 self.bridge_y + 18))
        self.surface.blit(cpu, (int(self.cpu.base_x) - cpu.get_width() // 2,
                                 self.bridge_y + 18))

    def _update_petals(self, dt: float):
        self._petals = [p for p in self._petals if p.update(dt)]
        # Cap
        if len(self._petals) > 80:
            self._petals = self._petals[-80:]

    def render(self):
        self._draw_sky()
        self._draw_moon()
        self._draw_water()
        self._draw_bridge()

        # Petals behind characters
        self._update_petals(self.dt)
        for p in self._petals:
            p.draw(self.surface)

        # Samurai
        self.player.draw(self.surface, self.cycle_phase)
        self.cpu.draw(self.surface, self.cycle_phase)

        # Clash flash
        self._draw_clash_flash()

        # Health bars (on top of scene)
        self._draw_health_bars()

        # Speech bubbles
        self._player_bubble.draw(self.surface,
                                  int(self.player.base_x),
                                  int(self.player.base_y) - 75)
        self._cpu_bubble.draw(self.surface,
                               int(self.cpu.base_x),
                               int(self.cpu.base_y) - 75)

        self._draw_labels()
        self.timeline.draw(self.layers, self.cycle_phase)

        self.particles.update(self.dt)
        self.particles.draw(self.surface)

        bloom = bloom_pass(self.surface, scale=5)
        self.surface.blit(bloom, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
