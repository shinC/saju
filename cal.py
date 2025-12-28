import json
import os
from korean_lunar_calendar import KoreanLunarCalendar

def generate_manse_db(start_year, end_year):
    calendar = KoreanLunarCalendar()
    manse_db = {}
    
    print(f"🚀 {start_year}년부터 {end_year}년까지 데이터 추출을 시작합니다.")

    total_count = 0
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            for day in range(1, 32):
                # 1. 날짜 설정 시도
                if not calendar.setSolarDate(year, month, day):
                    continue
                
                try:
                    # 2. 간지 문자열 가져오기
                    ganji_str = calendar.getChineseGapJaString()
                    if not ganji_str:
                        continue
                        
                    ganji_list = ganji_str.split()
                    
                    # 3. 데이터 조립 (isIntercalation에서 () 제거함)
                    date_key = f"{year}{month:02d}{day:02d}"
                    manse_db[date_key] = {
                        "ly": calendar.lunarYear,
                        "lm": calendar.lunarMonth,
                        "ld": calendar.lunarDay,
                        "ls": calendar.isIntercalation, # ()를 제거하여 변수로 접근
                        "yG": ganji_list[0][:2],
                        "mG": ganji_list[1][:2],
                        "dG": ganji_list[2][:2]
                    }
                    total_count += 1
                except Exception as e:
                    print(f"❌ {year}-{month}-{day} 오류 발생: {e}")
                    continue
        
        if year % 10 == 0:
            print(f"📊 {year}년 완료... (현재 누적 데이터: {total_count}건)")

    # 4. 파일 저장
    file_path = os.path.join(os.getcwd(), 'manse_data.json')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(manse_db, f, ensure_ascii=False)

    print("-" * 50)
    print(f"✅ 추출 완료!")
    print(f"📂 저장 경로: {file_path}")
    print(f"🔢 총 데이터 개수: {total_count}개")
    print("-" * 50)

# 실행
generate_manse_db(1900, 2100)