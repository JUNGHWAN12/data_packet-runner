"""플레이어: 움직임 계산(PlayerBody, Arcade 비의존)과 그림(PlayerSprite)을 분리한다.

충돌 판정은 그림이 아니라 상태(서기/슬라이딩)에 따라 정한 사각형으로 한다.
(Arcade 3은 texture를 바꿔도 hit box가 따라 바뀌지 않기 때문)
"""

from enum import Enum, auto

import arcade

from . import config as C


class Pose(Enum):
    RUN = auto()
    JUMP = auto()      # 공중(점프·낙하 모두)
    SLIDE = auto()


class PlayerBody:
    def __init__(self):
        self.feet_y = float(C.GROUND_Y)
        self.vy = 0.0
        self.pose = Pose.RUN
        self.on_ground = True
        self.down_held = False
        self.slide_time = 0.0
        self.coyote = 0.0
        self.jump_buffer = 0.0

    # --- 입력 ---
    def press_jump(self) -> None:
        self.jump_buffer = C.JUMP_BUFFER

    def press_down(self) -> None:
        self.down_held = True

    def release_down(self) -> None:
        self.down_held = False

    # --- 매 프레임 ---
    def update(self, dt: float, ground_below: bool) -> None:
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.coyote = C.COYOTE_TIME if self.on_ground else max(0.0, self.coyote - dt)

        if self.on_ground and not ground_below:
            self.on_ground = False          # 바닥 틈으로 걸어 들어감
            self.pose = Pose.JUMP

        if self.jump_buffer > 0 and (self.on_ground or self.coyote > 0):
            self.vy = C.JUMP_VELOCITY       # 슬라이딩 중에도 바로 점프
            self.on_ground = False
            self.coyote = self.jump_buffer = 0.0
            self.pose = Pose.JUMP

        if self.on_ground:
            if self.pose == Pose.SLIDE:
                self.slide_time += dt
                if not self.down_held and self.slide_time >= C.MIN_SLIDE:
                    self.pose = Pose.RUN
            elif self.down_held:
                self._start_slide()
            return

        gravity = C.GRAVITY * (C.FAST_FALL if self.down_held else 1.0)
        self.vy -= gravity * dt
        self.feet_y += self.vy * dt
        # 바닥 높이 근처에서 내려오는 중이고 발밑에 바닥이 있으면 착지 (틈 가장자리는 조금 너그럽게)
        if self.vy <= 0 and ground_below and C.GROUND_Y - 20 < self.feet_y <= C.GROUND_Y:
            self.feet_y = float(C.GROUND_Y)
            self.vy = 0.0
            self.on_ground = True
            if self.down_held:
                self._start_slide()
            else:
                self.pose = Pose.RUN

    def _start_slide(self) -> None:
        self.pose = Pose.SLIDE
        self.slide_time = 0.0

    def fell(self, ground_below: bool) -> bool:
        """틈에 빠졌는지: 충분히 떨어졌거나, 틈 아래로 들어간 채 바닥이 다시 발밑에 온 경우."""
        if self.on_ground:
            return False
        return self.feet_y < C.GROUND_Y - C.FALL_LIMIT or (ground_below and self.feet_y <= C.GROUND_Y - 20)

    def respawn(self) -> None:
        self.feet_y = float(C.GROUND_Y)
        self.vy = 0.0
        self.on_ground = True
        self.pose = Pose.SLIDE if self.down_held else Pose.RUN
        self.slide_time = 0.0

    def rect(self, x: float = C.PLAYER_X) -> arcade.Rect:
        w, h = C.SLIDE_BOX if self.pose == Pose.SLIDE else C.STAND_BOX
        return arcade.LBWH(x - w / 2, self.feet_y, w, h)


class PlayerSprite(arcade.Sprite):
    """PlayerBody 상태에 맞는 프레임을 보여 준다. 모든 프레임은 같은 캔버스, 발 = 맨 아래 줄."""

    RUN_FRAMES = [f"run_{i}" for i in range(6)]

    def __init__(self):
        folder = C.GENERATED / "runner"
        names = self.RUN_FRAMES + ["jump_up", "jump_down", "slide_0", "slide_1"]
        self.frames = {n: arcade.load_texture(folder / f"{n}.png") for n in names}
        super().__init__(self.frames["run_0"], scale=C.CHAR_SCALE)
        self.anim_time = 0.0
        self.center_x = C.PLAYER_X

    def sync(self, body: PlayerBody, dt: float, speed: float, invincible: float) -> None:
        self.anim_time += dt
        bob = 0
        if body.pose == Pose.JUMP:
            name = "jump_up" if body.vy > 0 else "jump_down"
        elif body.pose == Pose.SLIDE:
            name = "slide_0" if body.slide_time < 0.07 else "slide_1"
            bob = int(self.anim_time * 20) % 2       # 미끄러지는 느낌의 1px 흔들림
        else:
            fps = 12 * speed / 450
            name = self.RUN_FRAMES[int(self.anim_time * fps) % len(self.RUN_FRAMES)]
        self.texture = self.frames[name]
        self.center_x = C.PLAYER_X
        self.center_y = round(body.feet_y + self.height / 2) + bob
        # 무적 시간에는 깜빡임
        self.alpha = 90 if invincible > 0 and int(invincible * 12) % 2 == 0 else 255
