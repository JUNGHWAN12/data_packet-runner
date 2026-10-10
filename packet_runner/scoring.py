"""점수 계산 (Arcade 비의존 — 단위 테스트 대상)."""

from dataclasses import dataclass

from . import config as C


@dataclass
class ScoreBoard:
    score: int = 0
    fragments: int = 0
    collisions: int = 0
    passed: int = 0
    tokens: int = 0
    lost_pool: int = 0   # 충돌·추락으로 실제로 깎였지만 아직 되찾지 못한 점수 ("유실 데이터")

    def add_fragment(self) -> int:
        self.fragments += 1
        self.score += C.SCORE_FRAGMENT
        return C.SCORE_FRAGMENT

    def add_pass(self) -> int:
        self.passed += 1
        self.score += C.SCORE_PASS
        return C.SCORE_PASS

    def penalize(self) -> int:
        """충돌·추락 감점. 점수는 0 아래로 내려가지 않고, 실제로 깎인 만큼만 유실 데이터에 쌓인다."""
        lost = min(C.SCORE_PENALTY, self.score)
        self.score -= lost
        self.lost_pool += lost
        self.collisions += 1
        return lost

    def use_token(self) -> tuple[int, bool]:
        """재전송 토큰. 유실 데이터 1회분(최대 30)을 되찾고, 없으면 보너스. (얻은 점수, 복구 여부)"""
        self.tokens += 1
        restored = min(C.SCORE_PENALTY, self.lost_pool)
        if restored > 0:
            self.lost_pool -= restored
            self.score += restored
            return restored, True
        self.score += C.SCORE_TOKEN_FALLBACK
        return C.SCORE_TOKEN_FALLBACK, False

    def arrive(self) -> int:
        self.score += C.SCORE_ARRIVAL
        return C.SCORE_ARRIVAL


def grade_for(score: int) -> str:
    for threshold, grade in C.GRADES:
        if score >= threshold:
            return grade
    return C.GRADES[-1][1]
