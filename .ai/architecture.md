# 시스템 아키텍처 (Architecture)

## 모듈 의존성 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                 │
│                    (FastAPI 웹 서버)                              │
│                                                                  │
│  Routes:                                                         │
│  - GET  /              → 만세력 입력                              │
│  - POST /analyze_web   → 만세력 결과                              │
│  - GET  /fortune       → 운세 입력                                │
│  - POST /fortune_web   → 운세 결과                                │
│  - GET  /api/*         → REST API                                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  SajuEngine      │ │ FortuneGenerator │ │ FortuneBridge    │
│  (saju_engine.py)│ │ (fortune_gen...)│  │ (FortuneBridge.py)│
│                  │ │                  │ │                  │
│  - 사주 4기둥 계산 │ │  - 운세 점수 계산 │ │  - 일주별 성격   │
│  - 오행/십성 분석 │ │  - 템플릿 조합   │ │  - 행운 아이템   │
│  - 대운/세운/월운 │ │  - 시드 기반 선택 │ │                  │
│  - 합/충/형/공망  │ │                  │ │                  │
└────────┬─────────┘ └────────┬─────────┘ └──────────────────┘
         │                    │
         ▼                    ▼
┌──────────────────┐ ┌──────────────────────────────────────────┐
│ saju_constants.py│ │         fortune_templates/                │
│                  │ │                                          │
│  - STEMS/BRANCHES│ │  overall.py  study.py   wealth.py       │
│  - ELEM_OF_STEM  │ │  love.py     marriage.py career.py      │
│  - SIBSUNG_TABLE │ │  business.py health.py  common.py       │
│  - SINSAL_*      │ │                                          │
│  - CITY_DATA     │ │  (~1,930개 템플릿)                         │
│  - DST_PERIODS   │ │                                          │
└────────┬─────────┘ └──────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                         data/                                  │
│                                                                │
│  manse_data.json   - 만세력 DB (1900-2100, 10MB)               │
│  term_data.json    - 절기 DB (1MB)                             │
│  ilju_data.json    - 60일주 데이터 (15KB)                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 핵심 클래스 설명

### SajuEngine (saju_engine.py)

사주 분석의 핵심 엔진. 약 1,400줄.

```python
class SajuEngine:
    def __init__(self, m_file, t_file):
        """만세력/절기 DB 로드"""
    
    def analyze(self, birth_str, gender, location, use_yajas_i, calendar_type, ...):
        """메인 분석 메서드 - 모든 정보 반환"""
    
    # 시간 관련
    def _parse_and_convert_to_solar(...)  # 음력→양력 변환
    def _get_historical_correction(...)    # 역사적 표준시 보정
    def _get_equation_of_time(...)         # 균시차 계산
    
    # 사주 계산
    def _get_year_pillar(...)              # 년주 계산
    def _get_month_pillar(...)             # 월주 계산 (절기 반영)
    def _get_day_pillar(...)               # 일주 계산
    def _get_hour_pillar(...)              # 시주 계산
    
    # 십성/오행 분석
    def _calculate_sibsung(...)            # 십성 계산
    def _calculate_element_scores(...)     # 오행 점수
    def _calculate_power(...)              # 신강약 판정
    
    # 운로 계산
    def _calculate_daeun(...)              # 대운 계산
    def _calculate_saeun(...)              # 세운 계산
    def get_yeonun_only(...)               # 연운 API
    def get_wolun_only(...)                # 월운 API
    
    # 상호작용
    def _find_interactions(...)            # 합/충/형/파/해/원진/공망
```

### FortuneGenerator (fortune_generator.py)

운세 생성기. 약 600줄.

```python
class FortuneGenerator:
    def __init__(self, fortune_bridge=None):
        """브릿지 연결 (행운 아이템용)"""
    
    def generate_daily_fortune(self, analysis, target_date, name, 
                                relationship_status, marriage_status):
        """오늘의 운세 생성 - 메인 메서드"""
        # 1. 시드 생성 (생년월일 + 날짜)
        # 2. 8개 분야별 점수 계산
        # 3. 레벨별 템플릿 선택
        # 4. 문장 조합 및 반환
    
    def _calculate_base_score(self, analysis, target_date):
        """합/충/형 기반 점수 계산"""
    
    def _get_level(self, score):
        """점수 → 레벨 변환"""
        # 80+ : excellent
        # 65+ : good
        # 50+ : average
        # 35+ : caution
        # else: difficult
    
    def _select_template(self, templates, seed):
        """시드 기반 템플릿 선택"""
```

### FortuneBridge (FortuneBridge.py)

일주별 데이터 브릿지. 약 100줄.

```python
class FortuneBridge:
    def __init__(self, ilju_file):
        """일주 데이터 로드"""
    
    def get_ilju_report(self, ilju):
        """일주 보고서 반환"""
        # title, mbti, lucky_color, lucky_number 등
    
    def get_lucky_items(self, ilju):
        """행운 아이템만 반환"""
```

---

## 데이터 흐름 (Data Flow)

### 만세력 분석 흐름
```
[사용자 입력]
    ↓
POST /analyze_web
    - birth_date: "1990/01/15"
    - birth_time: "14:30"
    - gender: "M"
    - location: "서울"
    ↓
[main.py]
    - 날짜 형식 정규화
    - engine.analyze() 호출
    ↓
[SajuEngine.analyze()]
    1. 음력→양력 변환 (필요시)
    2. 지역시 보정 (경도 기반)
    3. 역사적 표준시/DST 보정
    4. 년/월/일/시 4기둥 계산
    5. 십성/오행/신강약 분석
    6. 대운/세운/월운 계산
    7. 합/충/형/공망 탐지
    ↓
[결과 반환]
    - pillars, scores, power, daeun_list, interactions, ...
    ↓
[result.html 렌더링]
```

### 운세 생성 흐름
```
[사용자 입력]
    ↓
POST /fortune_web
    - (만세력과 동일 + relationship_status, marriage_status)
    ↓
[main.py]
    - engine.analyze() → 사주 분석
    - fortune_gen.generate_daily_fortune() → 운세 생성
    ↓
[FortuneGenerator]
    1. 시드 생성: hash(birth + target_date)
    2. 기본 점수 계산 (합/충/형 기반)
    3. 8개 분야별 점수 변동
    4. 레벨 결정 (excellent ~ difficult)
    5. 템플릿 선택 (시드 고정)
    6. 문장 조합
    ↓
[운세 JSON]
    {
        "date": "2026년 01월 21일",
        "overall_score": 75,
        "overall": "...",
        "study": "...",
        "wealth": "...",
        ...
        "lucky": {"color": "...", "number": "...", ...}
    }
    ↓
[fortune_result.html 렌더링]
```

---

## 템플릿 구조

### 레벨별 템플릿
```python
# fortune_templates/study.py

STUDY_EXCELLENT = [  # 80점 이상
    "오늘은 집중력이 최고조에 달하는 날이에요...",
    "머리가 맑고 기억력이 좋은 하루입니다...",
    # ... 15개
]

STUDY_GOOD = [...]      # 65-79점
STUDY_AVERAGE = [...]   # 50-64점
STUDY_CAUTION = [...]   # 35-49점
STUDY_DIFFICULT = [...]  # 34점 이하
```

### 십성별 템플릿
```python
STUDY_BY_SIBSUNG = {
    "비견": ["스터디 그룹 활동이 효과적...", ...],
    "식신": ["창의적 아이디어가 샘솟는...", ...],
    "정관": ["체계적인 학습이 잘 되는...", ...],
    # ... 10개 십성
}
```

### 상황별 템플릿
```python
STUDY_SITUATION = {
    "시험": ["시험 준비가 순조로워요...", ...],
    "자격증": ["자격증 공부에 집중하기 좋은...", ...],
    "어학": ["언어 학습 능력이 높아진...", ...],
}
```

---

## 파일별 책임 요약

| 파일 | 핵심 책임 | 수정 시 주의 |
|------|----------|-------------|
| `main.py` | 라우팅, 요청/응답 처리 | 엔진/제너레이터 호출만 |
| `saju_engine.py` | 사주 계산 로직 | 정확도 검증 필수 |
| `saju_constants.py` | 모든 상수 | 변경 시 전체 영향 |
| `fortune_generator.py` | 운세 생성 | 시드 로직 주의 |
| `fortune_templates/*.py` | 템플릿 문장 | 자연스러운 한국어 |
| `FortuneBridge.py` | 일주 데이터 | ilju_data.json 의존 |
