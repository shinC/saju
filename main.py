from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from typing import Optional
from datetime import datetime, timedelta 
import traceback
import os

# 엔진 및 브릿지 임포트
from saju_engine import SajuEngine 
from FortuneBridge import FortuneBridge

app = FastAPI(title="포스텔러 만세력 2.2")
templates = Jinja2Templates(directory="templates")

# 엔진 초기화
try:
    # 경로 및 파일명은 사용자 환경에 맞게 유지
    engine = SajuEngine("./data/manse_data.json", "./data/term_data.json")
    bridge = FortuneBridge("./data/ilju_data.json")
    print("✅ 엔진 및 브릿지 로드 완료")
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
    if engine is None:
        raise HTTPException(status_code=500, detail="엔진 미로드 상태입니다.")

    try:
        # 1. 엔진 호출을 위한 날짜 형식 정규화 (YYYY/MM/DD -> YYYY-MM-DD)
        formatted_date = birth_date.replace("/", "-")
        birth_str = f"{formatted_date} {birth_time}"

        # 2. 엔진 분석 실행 
        # 이제 지역명 전처리, 정밀 보정(round 반영), 오행/태그 가공, 
        # Display용 문자열 생성은 모두 엔진 내부에서 수행됩니다.
        result = engine.analyze(
            birth_str=birth_str, 
            gender=gender, 
            location=location, 
            use_yajas_i=use_yajas_i
        )

        # 3. 엔진이 모르는 사용자 '이름' 정보만 결과에 추가
        result['name'] = name

        # 4. 브릿지 데이터 보강 (MBTI, 일주 타이틀 등)
        ilju_info = bridge.get_ilju_report(result['ilju'])
        
        # 5. 가공 없이 결과 페이지로 데이터 전달
        return templates.TemplateResponse("result.html", {
            "request": request, 
            "result": result,    # 엔진이 생성한 display_tags, corrected_display 등을 그대로 사용
            "ilju_info": ilju_info, 
            "h": HAN_MAP
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "error": f"분석 중 오류가 발생했습니다: {str(e)}"
        })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)