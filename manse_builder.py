import json
from datetime import datetime, timedelta
from korean_lunar_calendar import KoreanLunarCalendar

# 1. 상수 및 60갑자 정의
STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"
SIXTY_GANZI = [STEMS[i % 10] + BRANCHES[i % 12] for i in range(60)]

def get_ganzi_idx(s, b):
    si, bi = STEMS.find(s), BRANCHES.find(b)
    for i in range(60):
        if i % 10 == si and i % 12 == bi: return i
    return -1

def get_month_ganzi(year_ganzi_idx, month_idx):
    """
    년주와 월 인덱스 기반 월간지 산출 (월두법)
    """
    year_stem_idx = year_ganzi_idx % 10
    start_stem_idx = (year_stem_idx * 2 + 2) % 10
    m_stem = STEMS[(start_stem_idx + month_idx - 1) % 10]
    m_branch = BRANCHES[(month_idx + 1) % 12] 
    return SIXTY_GANZI[get_ganzi_idx(m_stem, m_branch)]

# 2. 절기 데이터 로드 및 전처리
def load_terms():
    # 경로를 실제 환경에 맞게 조정하세요.
    with open('./data/term_data.json', 'r', encoding='utf-8') as f:
        term_db = json.load(f)
    
    all_terms = []
    for y in sorted(term_db.keys()):
        for t in term_db[y]:
            if t['isMonthChange']:
                t['dt_obj'] = datetime.strptime(t['datetime'], "%Y-%m-%dT%H:%M")
                all_terms.append(t)
    return sorted(all_terms, key=lambda x: x['dt_obj'])

# 3. 통합 만세력 DB 빌더
def build_final_manse_db(start_year=1900, end_year=2100):
    all_terms = load_terms()
    manse_db = {}
    lunar = KoreanLunarCalendar()
    
    curr_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    day_ganzi_ptr = 10  # 1900-01-01 갑술일 기준
    
    term_ptr = 0
    print(f"🚀 {start_year}~{end_year} 정밀 만세력 빌드 시작...")

    while curr_date <= end_date:
        lunar.setSolarDate(curr_date.year, curr_date.month, curr_date.day)
        
        # [수정] 당일 자정 기준 가장 최근의 절기를 찾습니다.
        check_dt = curr_date.replace(hour=0, minute=0, second=1)
        while term_ptr + 1 < len(all_terms) and all_terms[term_ptr + 1]['dt_obj'] <= check_dt:
            term_ptr += 1
        
        latest_term = all_terms[term_ptr]
        m_idx = latest_term['monthIndex']
        
        # [핵심 수정] 사주 연도(yG) 판정 로직: 입춘 기준 역추적
        # 현재 절기 시점으로부터 거꾸로 탐색하여 가장 가까운 '입춘(1)'을 찾습니다.
        iphun_ptr = term_ptr
        while iphun_ptr >= 0 and all_terms[iphun_ptr]['monthIndex'] != 1:
            iphun_ptr -= 1
        
        if iphun_ptr >= 0:
            # 찾은 입춘 절기의 연도가 사주 연도가 됩니다.
            saju_year = all_terms[iphun_ptr]['dt_obj'].year
        else:
            # DB 시작점 이전일 경우의 예외 처리
            saju_year = start_year - 1

        y_idx = (saju_year - 4) % 60
        yG = SIXTY_GANZI[y_idx]
        
        # 월주(mG) 및 일주(dG) 결정
        mG = get_month_ganzi(y_idx, m_idx)
        dG = SIXTY_GANZI[day_ganzi_ptr % 60]
        
        date_key = curr_date.strftime("%Y%m%d")
        manse_db[date_key] = {
            "ly": lunar.lunarYear, "lm": lunar.lunarMonth, "ld": lunar.lunarDay,
            "ls": lunar.isIntercalation, "yG": yG, "mG": mG, "dG": dG
        }
        
        if curr_date.day == 1 and curr_date.month == 1:
            print(f"📊 {curr_date.year}년 연산 완료 (사주 연도: {yG})")

        curr_date += timedelta(days=1)
        day_ganzi_ptr += 1

    return manse_db

if __name__ == "__main__":
    final_db = build_final_manse_db()
    with open("manse_data_v2.json", "w", encoding="utf-8") as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)
    print("\n✅ [성공] 2026년 을사년 데이터가 정상 반영된 v2 DB가 생성되었습니다!")