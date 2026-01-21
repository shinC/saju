# API 레퍼런스 (API Reference)

## 개요

FastAPI 기반 REST API + 웹 페이지 라우트

**Base URL**: `http://localhost:8000`

---

## 웹 페이지 라우트

### 만세력

| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | 만세력 입력 페이지 |
| POST | `/analyze_web` | 만세력 결과 페이지 |

### 오늘의 운세

| Method | Path | 설명 |
|--------|------|------|
| GET | `/fortune` | 운세 입력 페이지 |
| POST | `/fortune_web` | 운세 결과 페이지 |

---

## REST API 엔드포인트

### 1. 오늘의 운세 API

```
GET /api/daily-fortune
```

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `birth` | string | ✅ | 생년월일시 `YYYY-MM-DD HH:MM` |
| `gender` | string | ✅ | 성별 `M` / `F` |
| `location` | string | ✅ | 출생 지역 (예: `서울`) |
| `name` | string | ❌ | 사용자 이름 (기본값: `회원`) |
| `relationship_status` | string | ❌ | 연애 상태 `single` / `couple` |
| `marriage_status` | string | ❌ | 결혼 상태 `single` / `married` |
| `calendar_type` | string | ❌ | `양력` / `음력` / `음력(윤달)` |
| `target_date` | string | ❌ | 운세 날짜 `YYYY-MM-DD` (기본값: 오늘) |

**Example Request:**
```bash
curl "http://localhost:8000/api/daily-fortune?birth=1990-01-15%2014:30&gender=M&location=서울&name=홍길동"
```

**Example Response:**
```json
{
  "date": "2026년 01월 21일 수요일",
  "name": "홍길동",
  "overall_score": 75,
  "greeting": "상쾌한 아침이에요! 오늘 하루도 기분 좋게 시작해보세요.",
  "overall": "오늘은 전반적으로 순조로운 하루가 될 것 같아요...",
  "study": "집중력이 좋은 날입니다. 새로운 것을 배우기에 적합해요.",
  "wealth": "재물운이 안정적입니다. 큰 지출은 피하는 게 좋겠어요.",
  "love": "좋은 인연을 만날 수 있는 기운이 있어요.",
  "marriage": "가정에 평화로운 기운이 흐르는 날입니다.",
  "career": "업무가 순조롭게 진행될 것 같아요.",
  "business": "새로운 기회를 모색하기 좋은 시기입니다.",
  "health": "활력이 넘치는 하루입니다. 가벼운 운동을 추천해요.",
  "lucky": {
    "color": "초록색",
    "number": "3, 8",
    "direction": "동쪽",
    "item": "식물"
  },
  "time_advice": "오전에 중요한 일을 처리하세요. 오후는 휴식을 취하기 좋습니다.",
  "closing": "오늘도 좋은 하루 되세요!",
  "scores": {
    "overall": 75,
    "study": 72,
    "wealth": 78,
    "love": 68,
    "marriage": 70,
    "career": 74,
    "business": 71,
    "health": 76
  }
}
```

---

### 2. 연운 API

```
GET /api/yeonun
```

대운 클릭 시 해당 대운의 10년치 연운(세운) 데이터 반환.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `birth_year` | int | ✅ | 출생 연도 |
| `start_age` | int | ✅ | 대운 시작 나이 |
| `me_gan` | string | ✅ | 일간 (예: `甲`) |
| `me_hj` | string | ✅ | 일간 한자 |

**Example Request:**
```bash
curl "http://localhost:8000/api/yeonun?birth_year=1990&start_age=32&me_gan=甲&me_hj=甲"
```

**Example Response:**
```json
[
  {
    "year": 2022,
    "ganzi": "壬寅",
    "gan": "壬",
    "gan_kor": "임",
    "gan_elem": "수",
    "ji": "寅",
    "ji_kor": "인",
    "ji_elem": "목",
    "t_gan": "편인",
    "t_ji": "편인",
    "unseong": "장생"
  },
  // ... 9개 더
]
```

---

### 3. 월운 API

```
GET /api/wolun
```

특정 연도의 12개월 월운 데이터 반환.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `target_year` | int | ✅ | 대상 연도 |
| `me_gan` | string | ✅ | 일간 |
| `me_hj` | string | ✅ | 일간 한자 |

**Example Request:**
```bash
curl "http://localhost:8000/api/wolun?target_year=2026&me_gan=甲&me_hj=甲"
```

**Example Response:**
```json
[
  {
    "month": 1,
    "ganzi": "己丑",
    "gan_kor": "기",
    "gan_elem": "토",
    "ji_kor": "축",
    "ji_elem": "토",
    "t_gan": "정재",
    "t_ji": "정재",
    "unseong": "묘"
  },
  // ... 11개 더
]
```

---

### 4. 달력 API

```
GET /api/calendar
```

특정 월의 일진 달력 데이터 반환.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `year` | int | ✅ | 연도 |
| `month` | int | ✅ | 월 (1-12) |

**Example Request:**
```bash
curl "http://localhost:8000/api/calendar?year=2026&month=1"
```

**Example Response:**
```json
{
  "year": 2026,
  "month": 1,
  "first_weekday": 4,
  "saju_header": "을사년 무자~기축월",
  "days": [
    {
      "day": 1,
      "ganzi_hj": "甲子",
      "ganzi_kor": "갑자",
      "lunar": "11.12",
      "is_today": false,
      "term_name": null,
      "term_time": null
    },
    // ... 30개 더
  ]
}
```

---

### 5. 재분석 API

```
GET /api/re-analyze
```

오행/십성 분석 옵션 변경 시 재계산.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `birth` | string | ✅ | 생년월일시 |
| `gender` | string | ✅ | 성별 |
| `location` | string | ✅ | 출생 지역 |
| `use_hap` | string | ❌ | 합 보정 적용 `true`/`false` |
| `use_johoo` | string | ❌ | 조후 보정 적용 `true`/`false` |

**Example Response:**
```json
{
  "scores": {"목": 2.5, "화": 3.0, "토": 1.0, "금": 2.0, "수": 1.5},
  "power": 55,
  "status": "신강",
  "representative_elem": "화",
  "representative_tendency": "정관",
  "forestellar_analysis": [...],
  "relation_groups": [...],
  "tengod_counts": {...}
}
```

---

## 에러 응답

모든 API는 에러 발생 시 다음 형식 반환:

```json
{
  "detail": "에러 메시지"
}
```

**HTTP Status Codes:**
- `400`: 잘못된 요청 (파라미터 오류)
- `500`: 서버 내부 오류 (엔진 미로드 등)

---

## 웹 폼 파라미터

### POST /analyze_web (만세력)

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | ✅ | 이름 |
| `gender` | string | ✅ | `M` / `F` |
| `birth_date` | string | ✅ | `YYYY/MM/DD` |
| `birth_time` | string | ✅ | `HH:MM` |
| `calendar_type` | string | ✅ | `양력` / `음력` / `음력(윤달)` |
| `location` | string | ✅ | 도시명 |
| `use_yajas_i` | boolean | ✅ | 야자시/조자시 적용 |

### POST /fortune_web (운세)

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | ❌ | 이름 (기본값: `회원`) |
| `gender` | string | ✅ | `M` / `F` |
| `birth_date` | string | ✅ | `YYYY/MM/DD` |
| `birth_time` | string | ✅ | `HH:MM` |
| `calendar_type` | string | ✅ | `양력` / `음력` / `음력(윤달)` |
| `location` | string | ✅ | 도시명 |
| `relationship_status` | string | ❌ | `single` / `couple` |
| `marriage_status` | string | ❌ | `single` / `married` |
