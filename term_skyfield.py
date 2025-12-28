import json
import numpy as np
from datetime import timezone, timedelta
from skyfield.api import load
from skyfield import almanac

# ==========================================
# 1. 환경 설정
# ==========================================
ts = load.timescale()
# de440s.bsp는 1849~2150년까지 커버하며 de440보다 가볍습니다.
eph = load('de440s.bsp') 
sun = eph['sun']
earth = eph['earth']

KST = timezone(timedelta(hours=9))

SOLAR_TERM_KR = [
    "춘분", "청명", "곡우", "입하", "소만", "망종",
    "하지", "소서", "대서", "입추", "처서", "백로",
    "추분", "한로", "상강", "입동", "소설", "대설",
    "동지", "소한", "대한", "입춘", "우수", "경칩"
]

MONTH_INDEX = {
    "입춘": 1, "경칩": 2, "청명": 3, "입하": 4, "망종": 5, "소서": 6,
    "입추": 7, "백로": 8, "한로": 9, "입동": 10, "대설": 11, "소한": 12
}

# ==========================================
# 2. 절기 판정 함수 (핵심 보정 반영)
# ==========================================
def solar_term_index(t):
    astrometric = earth.at(t).observe(sun)
    apparent = astrometric.apparent()
    
    # 🔥 [중요] epoch=t 를 추가하여 '현재 시점의 춘분점(Equinox of Date)'을 기준으로 계산합니다.
    # 이 한 줄이 8시간의 오차를 잡아줍니다.
    _, lon, _ = apparent.ecliptic_latlon(epoch=t)

    deg = np.asarray(lon.degrees) % 360
    return ((deg + 1e-9) // 15).astype(int) % 24

# 🔑 사용자님의 5일 안전 마진 원칙
solar_term_index.step_days = 5.0

# ==========================================
# 3. 연도별 절기 생성
# ==========================================
def generate_terms_for_year(year):
    t0 = ts.utc(year, 1, 1)
    t1 = ts.utc(year + 1, 1, 1)

    # Skyfield의 고성능 탐색 알고리즘
    times, events = almanac.find_discrete(t0, t1, solar_term_index)

    result = []
    for t, idx in zip(times, events):
        dt_kst = t.utc_datetime().astimezone(KST)

        if dt_kst.year != year:
            continue

        term_name = SOLAR_TERM_KR[int(idx)]

        # 검증용 실제 황경 재계산 (동일하게 epoch=t 적용)
        ast = earth.at(t).observe(sun).apparent()
        _, lon, _ = ast.ecliptic_latlon(epoch=t)
        deg = float(lon.degrees % 360)

        result.append({
            "term": term_name,
            "date": dt_kst.strftime("%Y%m%d"),
            "time": dt_kst.strftime("%H:%M"),
            "datetime": dt_kst.strftime("%Y-%m-%dT%H:%M"),
            "solarIndex": int(idx),
            "degree": round(deg, 6),
            "isMonthChange": term_name in MONTH_INDEX,
            "monthIndex": MONTH_INDEX.get(term_name)
        })

    # 시간순 정렬 (입춘이 처음에 오도록)
    result.sort(key=lambda x: x["datetime"])
    return result

# ==========================================
# 4. 전체 DB 생성
# ==========================================
if __name__ == "__main__":
    print("🚀 [최종 보정본] Skyfield 절기 DB 생성 시작 (1900~2100)")
    db = {}

    # 1900년부터 2100년까지 루프
    for year in range(1900, 2101):
        db[str(year)] = generate_terms_for_year(year)
        if year % 20 == 0:
            print(f"📊 {year}년 데이터 생성 완료...")

    with open("term_data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("\n✅ term_data.json 생성 완료!")
    print("💡 2024년 입춘 확인: 2월 4일 17:27 (KST)로 나오면 성공입니다.")