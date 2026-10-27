"""점수 계산 (Arcade 비의존 — 단위 테스트 대상)."""

from dataclasses import dataclass, field

from . import config as C


@dataclass
class ScoreBoard:
    score: int = 0
    fragments: int = 0
    collisions: int = 0
    passed: int = 0
    tokens: int = 0
    lost_pool: int = 0   # 충돌·추락으로 실제로 깎였지만 아직 되찾지 못한 점수 ("유실 데이터")
    phished: int = 0     # 가짜 데이터(피싱 미끼)에 걸린 횟수
    phish_avoided: int = 0
    blocked: int = 0     # 방화벽 실드가 막아 낸 횟수
    letters: int = 0     # 모은 PACKET 글자 수
    bonus: bool = False  # 보너스 타임을 열었는지
    hits: dict = field(default_factory=dict)   # 장애물 종류별로 부딪힌 횟수 (결과 화면의 "가장 많이 부딪힌 것")

    def add_fragment(self) -> int:
        self.fragments += 1
        self.score += C.SCORE_FRAGMENT
        return C.SCORE_FRAGMENT

    def add_pass(self) -> int:
        self.passed += 1
        self.score += C.SCORE_PASS
        return C.SCORE_PASS

    def penalize(self, kind: str = "") -> int:
        """충돌·추락 감점. 점수는 0 아래로 내려가지 않고, 실제로 깎인 만큼만 유실 데이터에 쌓인다."""
        self._count_hit(kind)
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

    def take_phish(self) -> int:
        """피싱 미끼를 먹음. 충돌과 달리 패킷 손실로 세지 않고, 재전송 토큰으로도 되찾을 수 없다."""
        lost = min(C.PHISH_PENALTY, self.score)
        self.score -= lost
        self.phished += 1
        self._count_hit("phish")
        return lost

    def avoid_phish(self) -> int:
        self.phish_avoided += 1
        self.score += C.PHISH_AVOID_BONUS
        return C.PHISH_AVOID_BONUS

    def _count_hit(self, kind: str) -> None:
        if kind:
            kind = "missile" if kind.startswith("missile") else kind
            self.hits[kind] = self.hits.get(kind, 0) + 1

    def most_hit(self) -> str | None:
        """가장 많이 부딪힌 장애물 종류. 하나도 안 부딪혔으면 None."""
        if not self.hits:
            return None
        return max(self.hits, key=lambda kind: self.hits[kind])

    def arrive(self) -> int:
        self.score += C.SCORE_ARRIVAL
        return C.SCORE_ARRIVAL


def grade_for(score: int) -> str:
    for threshold, grade in C.GRADES:
        if score >= threshold:
            return grade
    return C.GRADES[-1][1]
