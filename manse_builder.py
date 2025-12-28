import json
from datetime import datetime, timedelta
from korean_lunar_calendar import KoreanLunarCalendar

# ==========================================
# 1. 명리학 상수 및 60갑자 정의
# ==========================================
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
    년주와 월 인덱스(1:입춘~12:소한)를 기반으로 월간지 산출 (월두법)
    month_idx: 1(인), 2(묘), 3(진), 4(사), 5(오), 6(미), 7(신), 8(유), 9(술), 10(해), 11(자), 12(축)
    """
    year_stem_idx = year_ganzi_idx % 10
    # 월두법 공식: (년산 * 2 + 2) % 10 이 인월(1)의 천간
    start_stem_idx = (year_stem_idx * 2 + 2) % 10
    m_stem = STEMS[(start_stem_idx + month_idx - 1) % 10]
    m_branch = BRANCHES[(month_idx + 1) % 12] # 인(寅)은 인덱스 2
    return SIXTY_GANZI[get_ganzi_idx(m_stem, m_branch)]

# ==========================================
# 2. 절기 데이터 로드 및 전처리
# ==========================================
def load_terms():
    with open('term_data.json', 'r', encoding='utf-8') as f:
        term_db = json.load(f)
    
    all_terms = []
    for y in sorted(term_db.keys()):
        for t in term_db[y]:
            if t['isMonthChange']:
                t['dt_obj'] = datetime.strptime(t['datetime'], "%Y-%m-%dT%H:%M")
                all_terms.append(t)
    return sorted(all_terms, key=lambda x: x['dt_obj'])

# ==========================================
# 3. 통합 만세력 DB 빌더
# ==========================================
def build_final_manse_db(start_year=1900, end_year=2100):
    all_terms = load_terms()
    manse_db = {}
    lunar = KoreanLunarCalendar()
    
    # [기준점] 1900년 1월 1일은 갑술(甲戌)일 (인덱스 10)
    curr_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    day_ganzi_ptr = 10 
    
    term_ptr = 0
    print(f"🚀 {start_year}~{end_year} 통합 만세력(절기+음력) 빌드 시작...")

    while curr_date <= end_date:
        # A. 음력 정보 추출 (정보성 데이터)
        lunar.setSolarDate(curr_date.year, curr_date.month, curr_date.day)
        
        # B. 명리학적 절기 판정 (00:00:01 기준)
        # 당일 자정 시점에 이미 와 있는 절기를 찾습니다.
        check_dt = curr_date.replace(hour=0, minute=0, second=1)
        while term_ptr + 1 < len(all_terms) and all_terms[term_ptr + 1]['dt_obj'] <= check_dt:
            term_ptr += 1
        
        latest_term = all_terms[term_ptr]
        m_idx = latest_term['monthIndex']
        
        # C. 연주(yG) 결정 (입춘 기준 연도 판정)
        # 현재 적용 중인 절기의 연도가 명리적 기준 연도입니다.
        saju_year = int(latest_term['date'][:4])
        
        # [예외 케이스] 양력 1월인데 아직 입춘 전이면 작년 연도 적용
        if m_idx >= 11 and curr_date.month <= 2:
            saju_year -= 1
        # [예외 케이스] 양력 12월인데 이미 입춘이 왔다면(매우 희귀) 내년 연도 적용
        elif m_idx == 1 and curr_date.month == 12:
            saju_year += 1

        y_idx = (saju_year - 4) % 60
        yG = SIXTY_GANZI[y_idx]
        
        # D. 월주(mG) 결정 (절기 인덱스 기준)
        mG = get_month_ganzi(y_idx, m_idx)
        
        # E. 일주(dG) 결정 (60갑자 무한 순환)
        dG = SIXTY_GANZI[day_ganzi_ptr % 60]
        
        # F. 데이터 통합
        date_key = curr_date.strftime("%Y%m%d")
        manse_db[date_key] = {
            "ly": lunar.lunarYear,
            "lm": lunar.lunarMonth,
            "ld": lunar.lunarDay,
            "ls": lunar.isIntercalation,
            "yG": yG,
            "mG": mG,
            "dG": dG
        }
        
        if curr_date.day == 1 and curr_date.month == 1:
            print(f"📊 {curr_date.year}년 진행 중...")

        curr_date += timedelta(days=1)
        day_ganzi_ptr += 1

    return manse_db

if __name__ == "__main__":
    final_db = build_final_manse_db()
    with open("manse_data_v2.json", "w", encoding="utf-8") as f:
        json.dump(final_db, f, ensure_ascii=False, indent=2)
    print("\n✅ [성공] 절기 기반 정밀 manse_data.json이 생성되었습니다!")