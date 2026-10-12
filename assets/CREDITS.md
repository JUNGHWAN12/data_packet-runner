# 에셋 출처와 라이선스

| 에셋 | 제작자 | 라이선스 | 사용 파일 | 변경 사항 |
|---|---|---|---|---|
| [Animated Runner Character](https://opengameart.org/content/animated-runner-character) | irmirx | **CC0** (CC-BY 3.0 / CC0 이중 라이선스 중 CC0 선택) | `source/runner_sheet.png` | 달리기·점프 프레임을 잘라 발 위치를 맞춤, 사격 동작은 사용하지 않음 |
| 러너 슬라이딩 동작 시트 (위 캐릭터 기반) | 프로젝트 팀 — **ChatGPT 이미지 생성 기능으로 만든 AI 생성 이미지** | CC0 캐릭터를 바탕으로 생성, OpenAI 이용약관에 따라 사용 | `source/runner_slide_sheet.webp` | 8프레임 중 5프레임(젖히기·눕기 2·일어서기 2) 사용, 0.44배 축소, 갈색 먼지 제거, 가장자리 정리 |
| 러너 2단 점프 공중제비 시트 (위 캐릭터 기반) | 프로젝트 팀 — **ChatGPT 이미지 생성 기능으로 만든 AI 생성 이미지** | CC0 캐릭터를 바탕으로 생성, OpenAI 이용약관에 따라 사용 | `source/runner_flip_sheet.png` | 8프레임 중 4프레임(박차기·웅크림 2·마무리) 사용, 0.37배 축소, 발밑 폭발은 별도 효과(`dj_burst.png`)로 분리, 주변 불꽃 제거 |
| [Warped City](https://ansimuz.itch.io/warped-city) | Luis Zuno (ansimuz) | **CC0** (`licenses/warped-city-public-license.pdf`, 음악은 별도 라이선스라 사용하지 않음) | `source/warped-city/` 배경 3장 | `near-buildings-bg.png`의 'BAR' 간판 글자를 'NET'으로 교체 |
| [Lucide](https://lucide.dev) 아이콘 (`traffic-cone`, `cloud-lightning`, `unplug`, `binary`, `refresh-cw`, `server`, `mail`, `triangle-alert`, `shield-check`, `magnet`, `fishing-hook`, `mail-warning`) | Lucide Contributors | **ISC** (`licenses/lucide-LICENSE.txt` — 함께 배포 필수) | `source/icons/` | 색 변경, 24px 래스터화 후 정수 배 확대(픽셀화), 발광 효과. 피싱 미끼는 `binary`(빨강)와 `fishing-hook`(노랑)을 합성 |
| [IBM Plex Sans KR](https://github.com/IBM/plex) 글꼴 (Regular·Bold) | IBM Corp. | **SIL OFL 1.1** (`licenses/ibm-plex-OFL.txt` — 함께 배포 필수, 예약 글꼴 이름 "Plex") | `fonts/IBMPlexSansKR-Regular.ttf`, `fonts/IBMPlexSansKR-Bold.ttf` (Google Fonts 저장소에서 받음) | 변경 없음 — 글자를 잘라 내는 등 파일을 고치면 OFL에 따라 "Plex"가 들어가지 않은 다른 이름으로 바꿔야 하므로 원본 그대로 쓴다 |

- `generated/` 폴더의 이미지는 `tools/build_assets.py`가 위 원본으로 만든 결과물이다.
- 출처 표기가 의무가 아닌 에셋(CC0)도 감사의 뜻으로 함께 적었다.
- AI 생성 이미지는 학교의 생성형 AI 사용 지침에 따라 **시작 화면 아래 크레딧 줄**에 “AI 생성 이미지 포함”을 표시하고, 부스 안내판에도 밝힌다.
