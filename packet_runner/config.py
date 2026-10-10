"""게임 전체에서 쓰는 상수. 난이도·점수·시간 조정은 이 파일만 바꾸면 된다."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
GENERATED = ASSETS / "generated"

TITLE = "데이터 패킷 러너"
SCREEN_W, SCREEN_H = 1920, 1080
# 보통·굵게 두 파일을 모두 등록해야 Arcade가 "Galmuri11" 이름을 찾는다
FONT_PATHS = [ASSETS / "fonts" / "Galmuri11.ttf", ASSETS / "fonts" / "Galmuri11-Bold.ttf"]
FONT_NAME = "Galmuri11"

# --- 시간(초) ---
GAME_TIME = 180.0
RESULT_TIME = 40.0
HINT_TIME = 6.0          # 게임 시작 직후 조작 안내를 보여 주는 시간
ARRIVAL_TIME = 2.0       # 서버 도착 연출
SPAWN_STOP_BEFORE = 4.5  # 종료 몇 초 전부터 장애물 생성을 멈출지

# --- 화면 배치 ---
GROUND_Y = 165           # 바닥 윗면 높이
PLAYER_X = 390           # 플레이어 발 중심 x (고정)
BG_SCALE = 5             # Warped City 배경 확대 배수 (정수 배여야 픽셀이 고르게 보임)
CHAR_SCALE = 1.5         # 러너 캐릭터 확대 배수

# --- 플레이어 물리 ---
GRAVITY = 3600.0
JUMP_VELOCITY = 1380.0   # 최고 높이 약 264px, 체공 약 0.77초
DOUBLE_JUMP_VELOCITY = 1300.0  # 공중에서 한 번 더 Space: 그 자리에서 약 235px 더 오름
FAST_FALL = 3.0          # 공중에서 ↓를 누르면 중력 배율
MIN_SLIDE = 0.25         # 슬라이딩 최소 유지 시간
COYOTE_TIME = 0.1        # 발판을 벗어난 직후에도 점프 허용
JUMP_BUFFER = 0.1        # 착지 직전 Space 입력을 기억
STAND_BOX = (44, 110)    # 판정 크기(폭, 높이) — 그림보다 작게 잡아 너그럽게
SLIDE_BOX = (80, 60)
FOOT_HALF = 12           # 이 폭만큼이라도 바닥에 걸쳐 있으면 떨어지지 않음
FALL_LIMIT = 210         # 바닥 아래로 이만큼 떨어지면 재전송(재배치)

# --- 속도: (시각, 속도 px/s) 사이를 선형 보간 ---
SPEED_KEYS = [(0, 450), (55, 450), (65, 600), (115, 600), (125, 720), (180, 720)]
ZONES = [
    (0, "로컬 네트워크"),
    (60, "혼잡한 네트워크"),
    (120, "목적지 서버 접근"),
]
ZONE_TINTS = [None, (255, 140, 40, 26), (200, 80, 255, 30)]

# --- 충돌 ---
HIT_SLOW = 0.6
HIT_SLOW_TIME = 1.0
INVINCIBLE_TIME = 1.5

# --- 점수 ---
SCORE_FRAGMENT = 10
SCORE_PASS = 20
SCORE_PENALTY = 30
SCORE_ARRIVAL = 300
SCORE_TOKEN_FALLBACK = 10
GRADES = [(7500, "S"), (5500, "A"), (3500, "B"), (0, "C")]   # 임시 기준 — 리허설 후 조정

# --- 장애물 ---
CONGESTION_BOX = (72, 100)       # 바닥 위 차지하는 범위 (폭, 높이) — 간격 계산용
# 실제 충돌은 원뿔 모양을 따라 3단으로: (아래, 위, 중심에서 좌우 반폭)
CONGESTION_TIERS = [(0, 36, 36), (36, 70, 25), (70, 98, 14)]
CLOUD_W = 105                    # 오류 구름 번개 영역 폭 (그림)
CLOUD_HIT_W = 76                 # 실제 충돌 폭 — 그림보다 좁게
CLOUD_BOTTOM = 102               # 바닥에서 오류 구름 판정 아래쪽까지
CLOUD_TOP = 700                  # 바닥에서 판정 위쪽까지 — 2단 점프로도 넘을 수 없도록 화면 위까지
SPIKE_BOX = (80, 300)            # 트래픽 폭주 (폭, 높이) — 한 번 점프로는 못 넘고 2단 점프로 넘음
SPIKE_HIT_W = 66                 # 실제 충돌 폭 — 그림(상자 74px)보다 좁게
GAP_TIME = 0.3                   # 바닥 틈 폭 = 속도 × GAP_TIME
ZONE_REST = [1.6, 1.2, 1.0]      # 패턴 사이 쉬는 시간(초)

# --- 색 ---
CYAN = (94, 242, 255)
RED = (255, 93, 115)
GREEN = (125, 255, 154)
YELLOW = (255, 224, 102)
PURPLE = (196, 155, 255)
WHITE = (235, 245, 255)
GROUND_DARK = (9, 14, 32)
