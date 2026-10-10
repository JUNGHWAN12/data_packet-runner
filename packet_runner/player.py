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
        self.air_jumps = 1            # 공중에서 쓸 수 있는 추가 점프 (착지하면 다시 1)
        self.double_jumped = False    # 이번 프레임에 2단 점프했는지 (효과 표시용)

    # --- 입력 ---
    def press_jump(self) -> None:
        self.jump_buffer = C.JUMP_BUFFER

    def press_down(self) -> None:
        self.down_held = True

    def release_down(self) -> None:
        self.down_held = False

    # --- 매 프레임 ---
    def update(self, dt: float, ground_below: bool, ceiling: bool = False, cloud_ahead: bool = False) -> None:
        """ceiling: 머리 위에 오류 구름이 있어 지금 일어서면 부딪히는 상태.
        cloud_ahead: 지금 점프하면 착지 전에 오류 구름에 닿는 상태."""
        self.double_jumped = False
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.coyote = C.COYOTE_TIME if self.on_ground else max(0.0, self.coyote - dt)

        if self.on_ground and not ground_below:
            self.on_ground = False          # 바닥 틈으로 걸어 들어감
            self.pose = Pose.JUMP

        # 구름 아래(또는 바로 앞)에서 슬라이딩 중이면 점프 입력은 구름을 지날 때까지 보류 (연타해도 부딪히지 않음)
        stuck_under = (ceiling or cloud_ahead) and self.pose == Pose.SLIDE
        if self.jump_buffer > 0 and (self.on_ground or self.coyote > 0) and not stuck_under:
            self.vy = C.JUMP_VELOCITY       # 슬라이딩 중에도 바로 점프
            self.on_ground = False
            self.coyote = self.jump_buffer = 0.0
            self.pose = Pose.JUMP
        elif self.jump_buffer > 0 and not self.on_ground and self.air_jumps > 0 and not self._about_to_land(ground_below):
            self.vy = C.DOUBLE_JUMP_VELOCITY  # 2단 점프 (착지 직전 입력은 착지 후 점프로 남겨 둔다)
            self.air_jumps -= 1
            self.jump_buffer = 0.0
            self.double_jumped = True

        if self.on_ground:
            if self.pose == Pose.SLIDE:
                self.slide_time += dt
                if not self.down_held and self.slide_time >= C.MIN_SLIDE and not ceiling:
                    self.pose = Pose.RUN        # 구름 아래에서는 ↓를 떼도 계속 미끄러짐
            elif self.down_held:
                self._start_slide()
            return

        gravity = C.GRAVITY * (C.FAST_FALL if self.down_held else 1.0)
        prev_feet = self.feet_y
        self.vy -= gravity * dt
        self.feet_y += self.vy * dt
        # 이번 프레임에 바닥 높이를 위에서 지나쳤으면 착지 (빨리 떨어질 때 한 프레임에 수십 px씩 내려와도
        # 바닥을 뚫지 않도록). 틈 가장자리는 20px까지 너그럽게 봐준다.
        if self.vy <= 0 and ground_below and prev_feet > C.GROUND_Y - 20 and self.feet_y <= C.GROUND_Y:
            self.feet_y = float(C.GROUND_Y)
            self.vy = 0.0
            self.on_ground = True
            self.air_jumps = 1
            if self.down_held:
                self._start_slide()
            else:
                self.pose = Pose.RUN

    def _about_to_land(self, ground_below: bool) -> bool:
        return ground_below and self.vy < 0 and self.feet_y - C.GROUND_Y < 25

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
        self.air_jumps = 1
        self.pose = Pose.SLIDE if self.down_held else Pose.RUN
        self.slide_time = 0.0

    def rect(self, x: float = C.PLAYER_X) -> arcade.Rect:
        w, h = C.SLIDE_BOX if self.pose == Pose.SLIDE else C.STAND_BOX
        return arcade.LBWH(x - w / 2, self.feet_y, w, h)


class PlayerSprite(arcade.Sprite):
    """PlayerBody 상태에 맞는 프레임을 보여 준다. 모든 프레임은 같은 캔버스, 발 = 맨 아래 줄."""

    RUN_FRAMES = [f"run_{i}" for i in range(6)]
    SLIDE_FRAMES = ["slide_in", "slide_0", "slide_1", "slide_out_0", "slide_out_1"]
    SLIDE_IN = (0.05, 0.11)   # slide_in → slide_0 → slide_1(유지)로 넘어가는 시각
    SLIDE_OUT = 0.12          # 일어서는 동작 시간 (slide_out_0 → slide_out_1)

    def __init__(self):
        folder = C.GENERATED / "runner"
        names = self.RUN_FRAMES + ["jump_up", "jump_down"] + self.SLIDE_FRAMES
        self.frames = {n: arcade.load_texture(folder / f"{n}.png") for n in names}
        super().__init__(self.frames["run_0"], scale=C.CHAR_SCALE)
        self.anim_time = 0.0
        self.run_phase = 0.0      # 달리기 프레임 진행도 (속도에 맞춰 조금씩 쌓는다)
        self.prev_pose = Pose.RUN
        self.slide_out = 0.0
        self.center_x = C.PLAYER_X

    def sync(self, body: PlayerBody, dt: float, speed: float, invincible: float) -> None:
        self.anim_time += dt
        bob = 0
        if body.pose == Pose.JUMP:
            name = "jump_up" if body.vy > 0 else "jump_down"
            self.slide_out = 0.0
        elif body.pose == Pose.SLIDE:
            if body.slide_time < self.SLIDE_IN[0]:
                name = "slide_in"
            elif body.slide_time < self.SLIDE_IN[1]:
                name = "slide_0"
            else:
                name = "slide_1"
                bob = int(self.anim_time * 20) % 2   # 미끄러지는 느낌의 1px 흔들림
        else:
            if self.prev_pose == Pose.SLIDE:
                self.slide_out = self.SLIDE_OUT     # 슬라이딩에서 일어서는 동작
            if self.slide_out > 0:
                name = "slide_out_0" if self.slide_out > self.SLIDE_OUT / 2 else "slide_out_1"
                self.slide_out -= dt
            else:
                # 속도가 바뀌어도(충돌 감속 후 회복 등) 프레임이 튀지 않도록 진행도를 누적한다.
                # anim_time × fps로 계산하면 fps가 변할 때 프레임이 순식간에 여러 장 넘어간다.
                self.run_phase += dt * 12 * speed / 450
                name = self.RUN_FRAMES[int(self.run_phase) % len(self.RUN_FRAMES)]
        self.prev_pose = body.pose
        self.texture = self.frames[name]
        self.center_x = C.PLAYER_X
        self.center_y = round(body.feet_y + self.height / 2) + bob
        # 무적 시간에는 깜빡임
        self.alpha = 90 if invincible > 0 and int(invincible * 12) % 2 == 0 else 255
