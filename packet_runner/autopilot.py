"""자동 플레이 (python main.py --autoplay).

패턴이 실제로 피할 수 있는지 끝까지 돌려 확인하는 용도이고, 나중에 부스 대기 화면(데모)으로도 쓸 수 있다.
"""

from . import config as C
from . import patterns as P


class Autopilot:
    def control(self, body, world, speed: float) -> None:
        x = C.PLAYER_X
        want_down = False
        for o in world.obstacles:
            if o.right_x < x - C.SLIDE_BOX[0]:
                continue
            ahead = o.left_x - x
            if o.kind == P.CLOUD:
                if ahead < speed * 0.3 + C.SLIDE_BOX[0] / 2:
                    want_down = True
            elif o.kind == P.SPIKE:
                # 미리 뛰고, 올라가는 힘이 줄어들 때 한 번 더
                if body.on_ground and 0 < ahead - C.STAND_BOX[0] / 2 < speed * 0.45:
                    body.press_jump()
                elif (not body.on_ground and body.air_jumps > 0 and body.vy < 300
                      and ahead - C.STAND_BOX[0] / 2 < speed * 0.45 and o.right_x > x - C.STAND_BOX[0]):
                    body.press_jump()
            elif body.on_ground and 0 < ahead - C.STAND_BOX[0] / 2 < speed * 0.12 + 10:
                body.press_jump()
        for gap in world.gaps:
            ahead = gap.left_x - x
            if not gap.repaired and body.on_ground and 0 < ahead < speed * 0.08 + 4:
                body.press_jump()
        if want_down:
            body.press_down()
        else:
            body.release_down()
