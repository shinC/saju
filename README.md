# 사주 만세력 앱 (Saju Fortune App)

포스텔러/점신 스타일의 사주풀이 상용 앱입니다.

## Quick Start

```bash
# 가상환경 활성화
source .venv/bin/activate

# 서버 실행
python main.py

# 접속
# 만세력: http://localhost:8000
# 운세:   http://localhost:8000/fortune
```

## 주요 기능

| 기능 | 경로 | 설명 |
|------|------|------|
| 만세력 | `/` | 사주 4기둥 분석, 오행/십성, 대운/세운/월운 |
| 오늘의 운세 | `/fortune` | 8개 분야별 템플릿 기반 운세 생성 |
| 일진 달력 | 결과 페이지 내 | 월별 일진 및 절기 정보 |

## 프로젝트 구조

```
saju/
├── main.py                 # FastAPI 웹서버 (진입점)
├── saju_engine.py          # 핵심 사주 계산 엔진 (1,400+ lines)
├── saju_constants.py       # 상수 정의 (오행, 십성, 신살, 도시 등)
├── fortune_generator.py    # 운세 생성기 클래스
├── FortuneBridge.py        # 일주별 성격/행운아이템 브릿지
│
├── fortune_templates/      # 운세 템플릿 (~1,930개)
│   ├── overall.py         # 총운
│   ├── study.py           # 학업운
│   ├── wealth.py          # 재물운
│   ├── love.py            # 연애운
│   ├── marriage.py        # 결혼운
│   ├── career.py          # 직업운
│   ├── business.py        # 사업운
│   ├── health.py          # 건강운
│   └── common.py          # 공통 (인사말, 행운아이템 등)
│
├── templates/              # Jinja2 HTML 템플릿
│   ├── index.html         # 만세력 입력 페이지
│   ├── result.html        # 만세력 결과 페이지
│   ├── fortune_input.html # 운세 입력 페이지
│   └── fortune_result.html# 운세 결과 페이지
│
├── data/                   # 데이터 파일
│   ├── manse_data.json    # 만세력 DB (1900-2100)
│   ├── term_data.json     # 절기 DB
│   └── ilju_data.json     # 60일주 데이터
│
├── .ai/                    # AI 에이전트용 문서
│   ├── project.md         # 프로젝트 컨텍스트
│   ├── architecture.md    # 시스템 아키텍처
│   └── api.md             # API 레퍼런스
│
└── (유틸리티)
    ├── cal.py             # 달력 유틸
    ├── manse_builder.py   # 만세력 DB 빌더
    ├── term_skyfield.py   # 절기 계산 (Skyfield)
    └── test_saju.py       # 테스트
```

## 기술 스택

- **Backend**: Python 3.14, FastAPI, Uvicorn
- **Frontend**: Jinja2 + Tailwind CSS (CDN)
- **Data**: JSON 파일 기반 (DB 없음)

## AI 에이전트 안내

이 프로젝트 작업 시 `.ai/` 폴더의 문서를 먼저 참조하세요:
- `.ai/project.md` - 전체 맥락과 설계 원칙
- `.ai/architecture.md` - 모듈별 역할과 데이터 흐름
- `.ai/api.md` - API 엔드포인트 상세

## License

Private - All rights reserved
