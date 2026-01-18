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
import saju_constants as sc

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
    # CITY_DATA의 키값들만 뽑아서 리스트로 만듭니다.
    city_list = list(sc.CITY_DATA.keys())
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "cities": city_list  # [추가] 도시 목록 전달
    })
@app.post("/analyze_web", response_class=HTMLResponse)
async def analyze_web(
    request: Request,
    name: str = Form(...),
    gender: str = Form(...),
    birth_date: str = Form(...),
    birth_time: str = Form(...),
    calendar_type: str = Form(...),
    location: str = Form(...),
    use_yajas_i: bool = Form(...)
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
            use_yajas_i=use_yajas_i,
            calendar_type=calendar_type
        )
        if "error" in result:
            print(f"분석 실패: {result['error']}")
        else:
            print(f"분석 성공: {result['ilju']}")
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
        return templates.TemplateResponse("index.html", {
            "request": request,
            "cities": list(sc.CITY_DATA.keys()),  # 🔥 에러 페이지로 갈 때도 도시 목록을 다시 보내줘야 합니다.
            "error": f"분석 중 오류가 발생했습니다: {str(e)}"
        })
@app.get("/api/yeonun")
async def get_yeonun(
    birth_year: int,
    start_age: int,
    me_gan: str,
    me_hj: str
):
    """
    대운 클릭 시 해당 대운의 10년치 연운(세운) 데이터를 반환하는 API
    """
    if engine is None:
        raise HTTPException(status_code=500, detail="엔진이 로드되지 않았습니다.")

    try:
        # 엔진의 연운 전용 계산 메서드 호출
        yeonun_data = engine.get_yeonun_only(
            birth_year=birth_year,
            daeun_start_age=start_age,
            me_gan=me_gan,
            me_hj=me_hj
        )
        return yeonun_data  # JSON 형식으로 자동 반환
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/wolun")
async def get_wolun(
    target_year: int,
    me_gan: str,
    me_hj: str
):
    if engine is None:
        raise HTTPException(status_code=500, detail="엔진 미로드")
    try:
        wolun_data = engine.get_wolun_only(target_year, me_gan, me_hj)
        return wolun_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/calendar")
async def get_calendar(year: int, month: int):
    try:
        data = engine.get_month_calendar(year, month)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/re-analyze")
def re_analyze(request: Request):
    """
    Starlette/FastAPI의 기본 호출 방식에 맞춰 인자를 request 하나만 받습니다.
    모든 데이터는 request.query_params에서 직접 추출하여 인자 불일치 에러를 방지합니다.
    """
    try:
        # 1. URL 쿼리 파라미터에서 데이터 추출
        params = request.query_params
        birth = params.get('birth')
        gender = params.get('gender')
        location = params.get('location')
        
        # 체크박스 값은 문자열로 들어오므로 불린(Boolean)으로 변환합니다.
        use_hap = params.get('use_hap', 'false').lower() == 'true'
        use_johoo = params.get('use_johoo', 'false').lower() == 'true'
        
        print(f"보정 옵션 상태 -> 합: {use_hap}, 조후: {use_johoo}")  
        # 2. 필수 값이 누락되었는지 확인
        if not all([birth, gender, location]):
            return {"error": "필수 분석 정보(생년월일, 성별, 지역)가 누락되었습니다."}

        # 3. 엔진 분석 실행
        # 사용자님이 작성하신 analyze 함수 규격에 맞춰 인자를 전달합니다.
        result = engine.analyze(
            birth_str=birth, 
            gender=gender, 
            location=location, 
            use_yajas_i=True, 
            calendar_type="양력",
            use_hap_correction=use_hap, 
            use_johoo_correction=use_johoo
        )

        if "error" in result:
            return {"error": result["error"]}

        # 4. 프론트엔드 JS가 요구하는 형식으로 데이터 가공
        # 십성 비중 계산 시 딕셔너리 데이터를 안전하게 참조합니다.
        tengod_counts = {}
        tg_dict = result.get('tengod_analysis_dict', {})
        for k, v in tg_dict.items():
            # '-' 표시가 아닐 경우에만 비율 숫자를 추출합니다.
            tengod_counts[k] = float(v['ratio'].replace('%', '')) if v.get('ratio') != '-' else 0

        return {
            "scores": result["scores"],
            "power": result["power"],
            "status": result["status"],
            "representative_elem": result["representative_elem"],
            "representative_tendency": result["representative_tendency"],
            "forestellar_analysis": result["forestellar_analysis"],
            "relation_groups": result["relation_groups"],
            "tengod_counts": tengod_counts
        }

    except Exception as e:
        print(f"상세 에러 로그: {e}")
        return {"error": f"서버 내부 오류: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)