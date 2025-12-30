from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from typing import Optional
from datetime import datetime, timedelta  # 🔥 여기서 timedelta가 추가되어야 합니다.
import traceback
import os

# 엔진 및 브릿지 임포트
from saju_engine import SajuEngine 
from FortuneBridge import FortuneBridge

app = FastAPI(title="포스텔러 만세력 2.2")
templates = Jinja2Templates(directory="templates")

# 엔진 초기화
try:
    engine = SajuEngine("./data/manse_data.json", "./data/term_data.json")
    bridge = FortuneBridge("./data/ilju_data.json")
    print("✅ 엔진 로드 완료")
except Exception as e:
    traceback.print_exc()
    engine, bridge = None, None

HAN_MAP = {
    '甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기','庚':'경','辛':'신','壬':'임','癸':'계',
    '子':'자','丑':'축','寅':'인','卯':'묘','辰':'진','巳':'사','午':'오','未':'미','申':'신','酉':'유','戌':'술','亥':'해'
}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze_web", response_class=HTMLResponse)
async def analyze_web(
    request: Request,
    name: str = Form("아무개"),
    gender: str = Form(...),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    calendar_type: str = Form("양력"),
    location: str = Form("서울특별시, 대한민국"),
    use_yajas_i: bool = Form(False)
):
    try:
        # 1. 지역명 전처리 (예: "부산광역시, 대한민국" -> "부산")
        city_full = location.split(',')[0].strip() 
        city_key = city_full[:2] # 앞 두 글자만 추출 (서울, 부산, 대구 등)

        # 2. 엔진 분석 실행
        formatted_date = birth_date.replace("/", "-")
        birth_str = f"{formatted_date} {birth_time}"
        result = engine.analyze(birth_str, gender, city_key, use_yajas_i)

        # 3. 보정치 계산 (CITY_DATA 매칭)
        import saju_constants as sc
        # CITY_DATA에서 앞 두 글자로 경도 가져오기, 없으면 서울(126.97) 기준
        lng = sc.CITY_DATA.get(city_key, 126.97) 
        lng_diff = int(round((lng - 135) * 4)) # 경도 1도당 4분 차이

        # 4. 결과 페이지용 데이터 보강
        dt_obj = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        dt_corrected = dt_obj + timedelta(minutes=lng_diff)

        result.update({
            "name": name,
            "gender_str": "여자" if gender == "F" else "남자",
            "location_name": city_full, # 화면 표시용은 전체 이름 사용
            "solar_display": dt_obj.strftime("%Y/%m/%d %H:%M"),
            "corrected_display": dt_corrected.strftime("%Y/%m/%d %H:%M"),
            "lng_diff_str": f"{lng_diff}분" if lng_diff < 0 else f"+{lng_diff}분"
        })

        # 오행 컬러 및 태그 가공 (HTML 연동용)
        for p in result['pillars']:
            p['gan_elem'] = sc.ELEMENT_MAP.get(p['gan'])
            p['ji_elem'] = sc.ELEMENT_MAP.get(p['ji'])
        
        all_tags = []
        for v in result['interactions'].values(): all_tags.extend(v)
        result['display_tags'] = all_tags[:8]

        ilju_info = bridge.get_ilju_report(result['ilju'])
        
        return templates.TemplateResponse("result.html", {
            "request": request, "result": result, "ilju_info": ilju_info, "h": HAN_MAP
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("index.html", {"request": request, "error": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)