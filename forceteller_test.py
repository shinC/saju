#!/usr/bin/env python3
"""
포스텔러 만세력 자동 테스트 및 비교 프로그램
- Playwright로 포스텔러 사이트 자동 테스트
- SQLite DB에 결과 저장
- 내 SajuEngine 결과와 비교

실행 방법:
  .venv/bin/python forceteller_test.py
  또는
  source .venv/bin/activate && python forceteller_test.py
"""

import asyncio
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser

# 내 엔진 임포트
from saju_engine import SajuEngine


class ForceTellerTester:
    """포스텔러 자동 테스트 클래스"""
    
    DB_PATH = "./data/forceteller_test.db"
    
    def __init__(self):
        self.engine = SajuEngine("./data/manse_data.json", "./data/term_data.json")
        self._init_db()
    
    def _init_db(self):
        """SQLite DB 초기화"""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        # 테스트 결과 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_no INTEGER,
                test_date TEXT,
                input_date TEXT,
                input_time TEXT,
                gender TEXT,
                location TEXT,
                test_purpose TEXT,
                
                -- 포스텔러 결과
                ft_year_pillar TEXT,
                ft_month_pillar TEXT,
                ft_day_pillar TEXT,
                ft_hour_pillar TEXT,
                ft_correction_minutes INTEGER,
                ft_summer_time_minutes INTEGER,
                ft_zodiac TEXT,
                
                -- 오행 분포 (기본)
                ft_wood REAL,
                ft_fire REAL,
                ft_earth REAL,
                ft_metal REAL,
                ft_water REAL,
                
                -- 오행 분포 (합+조후 보정)
                ft_wood_adj REAL,
                ft_fire_adj REAL,
                ft_earth_adj REAL,
                ft_metal_adj REAL,
                ft_water_adj REAL,
                
                -- 십성 분포 (기본)
                ft_bigyeon REAL,
                ft_geobje REAL,
                ft_siksin REAL,
                ft_sanggwan REAL,
                ft_pyeonjae REAL,
                ft_jeongjae REAL,
                ft_pyeongwan REAL,
                ft_jeonggwan REAL,
                ft_pyeonin REAL,
                ft_jeongin REAL,
                
                -- 신강/신약
                ft_strength TEXT,
                ft_strength_adj TEXT,
                
                -- 용신
                ft_yongsin TEXT,
                ft_yongsin_adj TEXT,
                
                -- 신살
                ft_sinsal TEXT,
                
                -- 내 엔진 결과
                my_year_pillar TEXT,
                my_month_pillar TEXT,
                my_day_pillar TEXT,
                my_hour_pillar TEXT,
                
                my_wood REAL,
                my_fire REAL,
                my_earth REAL,
                my_metal REAL,
                my_water REAL,
                
                my_strength TEXT,
                my_yongsin TEXT,
                
                -- 비교 결과
                pillar_match INTEGER,
                element_diff_max REAL,
                strength_match INTEGER,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def run_single_test(self, browser: Browser, test_case: dict) -> dict:
        """단일 테스트 케이스 실행"""
        page = await browser.new_page()
        result = {"test_no": test_case["no"], "input": test_case}
        
        try:
            # 1. 포스텔러 사이트 접속
            await page.goto("https://pro.forceteller.com/", timeout=60000)
            await page.wait_for_selector("button:has-text('시작하기')", timeout=30000)
            await page.click("button:has-text('시작하기')")
            await page.wait_for_url("**/profile/edit", timeout=30000)
            
            # 2. 폼 입력
            # 이름
            await page.fill("input[placeholder*='12글자']", f"테스트{test_case['no']}")
            
            # 성별 (레이블 클릭으로 라디오 선택)
            gender_label = "남자" if test_case["gender"] == "M" else "여자"
            await page.locator("label").filter(has_text=gender_label).click()
            
            # 날짜/시간
            date_str = test_case["date"].replace("-", "/")
            await page.locator("input[placeholder*='04/06']").fill(date_str)
            await page.locator("input[placeholder*='19:00']").fill(test_case["time"])
            
            # 도시 검색 (readonly 필드이므로 검색 버튼 클릭 후 모달에서 입력)
            # 도시 그룹 내의 버튼 클릭
            city_button = page.get_by_role("group").filter(has_text="도시").get_by_role("button")
            await city_button.click(timeout=10000)
            await page.wait_for_selector("input[placeholder*='시군구']", timeout=10000)
            await page.fill("input[placeholder*='시군구']", test_case["location"])
            await page.press("input[placeholder*='시군구']", "Enter")
            await asyncio.sleep(0.5)  # 검색 결과 로딩 대기
            # 결과 목록에서 첫 번째 대한민국 항목 클릭
            await page.locator("li").filter(has_text="대한민국").first.click(timeout=10000)
            
            # 3. 만세력 보러가기
            await page.wait_for_selector("button:has-text('만세력 보러가기'):not([disabled])", timeout=10000)
            await page.click("button:has-text('만세력 보러가기')")
            
            # 확인 페이지 (요소로 확인 - URL 패턴이 불안정할 수 있음)
            try:
                await page.wait_for_url("**/profile/confirm", timeout=10000)
            except:
                # URL이 변경 안됐을 경우 요소로 확인
                await page.wait_for_selector("text=입력하신 프로필을 확인해주세요", timeout=30000)
            
            # 보정 정보 추출
            # 형식 1: "KST기준 -32분"
            # 형식 2: "입력하신 지역 정보에 따라 -32분을 보정합니다."
            result["correction_minutes"] = 0
            try:
                page_text = await page.content()
                import re
                # KST 기준 형식 먼저 시도
                match = re.search(r'KST기준\s*(-?\d+)분', page_text)
                if match:
                    result["correction_minutes"] = int(match.group(1))
                else:
                    # 보정합니다 형식 시도
                    match = re.search(r'(-?\d+)분을?\s*보정', page_text)
                    if match:
                        result["correction_minutes"] = int(match.group(1))
            except:
                pass
            
            # 서머타임 정보 (있을 경우)
            result["summer_time_minutes"] = 0
            try:
                page_text = await page.content()
                if "서머타임" in page_text:
                    import re
                    # 서머타임 관련 분 추출
                    match = re.search(r'서머타임[^-\d]*(-?\d+)분', page_text)
                    if match:
                        result["summer_time_minutes"] = int(match.group(1))
            except:
                pass
            
            # 확인 페이지에서 만세력 보러가기 클릭 (재시도 로직 강화)
            max_retries = 3
            result_page_loaded = False
            
            for i in range(max_retries):
                try:
                    # 팝업이 가리고 있을 수 있으므로 제거 시도
                    await page.evaluate("""
                        () => {
                            document.querySelectorAll('.MuiDialog-root, .MuiModal-root, [role="presentation"]').forEach(el => el.remove());
                        }
                    """)
                    
                    # 버튼 클릭 시도
                    btn = page.locator("button:has-text('만세력 보러가기')")
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click(timeout=5000)
                    
                    # 결과 페이지 진입 확인
                    try:
                        await page.wait_for_url("**/result", timeout=8000)
                        result_page_loaded = True
                        break
                    except:
                        # 테이블이 보이면 성공으로 간주
                        if await page.locator("table").count() > 0:
                            result_page_loaded = True
                            break
                    
                    if i < max_retries - 1:
                        print(f"  [INFO] 결과 페이지 이동 대기/재시도 중... ({i+1}/{max_retries})")
                        await asyncio.sleep(2)
                        
                except Exception as e:
                    print(f"  [WARN] 페이지 이동 재시도 중 에러: {e}")
                    await asyncio.sleep(1)
            
            # 최종 확인 (타임아웃 60초로 연장)
            if not result_page_loaded:
                try:
                    await page.wait_for_url("**/result", timeout=60000)
                except:
                    # URL 변경 안되면 요소로 확인
                    await page.wait_for_selector("table", timeout=60000)
            await asyncio.sleep(2)
            
            # 핵심 콘텐츠 로딩 확인 - "오행과 십성 분석" 텍스트가 나타나야 함
            content_loaded = False
            try:
                ohaeng_section = page.get_by_text("오행과 십성 분석")
                await ohaeng_section.wait_for(timeout=15000)
                content_loaded = True
            except:
                print(f"  [WARN] 페이지 콘텐츠가 완전히 로드되지 않음 - 스킵합니다")
                await page.screenshot(path=f"./data/debug_test_{test_case['no']}_content_fail.png")
                result["error"] = "콘텐츠 로딩 실패 (오행과 십성 분석 섹션 없음)"
                result["forceteller"] = {}
                await page.close()
                return result
            
            # 반복적으로 다이얼로그 닫기 시도 (최대 10회)
            for attempt in range(10):
                # 다이얼로그가 있는지 확인
                dialog = page.locator(".MuiDialog-root, .MuiModal-root")
                if await dialog.count() == 0:
                    break
                
                # ESC 키로 닫기 시도
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
                
                # 그래도 있으면 JavaScript로 제거
                if await dialog.count() > 0:
                    await page.evaluate("""
                        () => {
                            document.querySelectorAll('.MuiDialog-root, .MuiModal-root, [role="presentation"]').forEach(el => el.remove());
                            document.querySelectorAll('[aria-hidden="true"]').forEach(el => el.removeAttribute('aria-hidden'));
                        }
                    """)
                    await asyncio.sleep(0.3)
            
            await asyncio.sleep(0.5)
            
            # 4. 메타 데이터 스크래핑 (사주팔자, 띠, 보정, 신살 - 체크박스 영향 없음)
            meta_result = await self._scrape_result(page)
            
            # 기본 상태 (둘 다 OFF) 데이터 스크래핑
            base_result = await self._scrape_full_result(page)
            result["forceteller"] = {**meta_result, **base_result}
            
            async def close_popups():
                for _ in range(5):
                    dialog = page.locator(".MuiDialog-root, .MuiModal-root")
                    if await dialog.count() == 0:
                        break
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.2)
                    if await dialog.count() > 0:
                        await page.evaluate("""
                            () => {
                                document.querySelectorAll('.MuiDialog-root, .MuiModal-root, [role="presentation"]').forEach(el => el.remove());
                            }
                        """)
                        await asyncio.sleep(0.2)
            
            async def force_remove_popups():
                await page.evaluate('''
                    () => {
                        document.querySelectorAll(".MuiDialog-root, .MuiModal-root, [role='presentation']").forEach(el => el.remove());
                        document.querySelectorAll("[aria-hidden='true']").forEach(el => el.removeAttribute("aria-hidden"));
                        document.body.style.overflow = "auto";
                    }
                ''')
                await asyncio.sleep(0.3)
            
            async def click_hap_checkbox():
                try:
                    await force_remove_popups()
                    hap_label = page.get_by_text("합에 따른 오행 변화 적용")
                    if await hap_label.count() > 0:
                        await hap_label.locator("..").click(force=True, timeout=5000)
                    else:
                        hap_checkbox = page.locator("[data-test-id='hap-adjust']")
                        if await hap_checkbox.count() > 0:
                            await hap_checkbox.click(force=True, timeout=5000)
                        else:
                            raise Exception("합 체크박스 요소를 찾을 수 없음")
                    return True
                except Exception as e:
                    print(f"  [WARN] 합 체크박스 클릭 실패: {e}")
                    return False
            
            async def click_johoo_checkbox():
                try:
                    await force_remove_popups()
                    johoo_label = page.get_by_text("조후와 궁성 보정값 적용")
                    if await johoo_label.count() > 0:
                        await johoo_label.locator("..").click(force=True, timeout=5000)
                    else:
                        johoo_checkbox = page.locator("[data-test-id='johu-adjust']")
                        if await johoo_checkbox.count() > 0:
                            await johoo_checkbox.click(force=True, timeout=5000)
                        else:
                            raise Exception("조후 체크박스 요소를 찾을 수 없음")
                    return True
                except Exception as e:
                    print(f"  [WARN] 조후 체크박스 클릭 실패: {e}")
                    return False
            
            await close_popups()
            
            # 5. 합만 ON (hap)
            if await click_hap_checkbox():
                print("  [INFO] 합에 따른 오행 변화 적용 체크됨")
            await asyncio.sleep(1.5)
            # await page.screenshot(path=f"./data/debug_test_{test_case['no']}_step1_hap.png")
            await close_popups()
            result["forceteller_hap"] = await self._scrape_full_result(page)
            
            # 6. 둘 다 ON (adj) - 합 ON 상태에서 조후 추가
            if await click_johoo_checkbox():
                print("  [INFO] 조후와 궁성 보정값 적용 체크됨")
            await asyncio.sleep(1.5)
            # await page.screenshot(path=f"./data/debug_test_{test_case['no']}_step2_both.png")
            await close_popups()
            result["forceteller_adj"] = await self._scrape_full_result(page)
            
            # 7. 조후만 ON (johoo) - 합 OFF
            if await click_hap_checkbox():
                print("  [INFO] 합 체크 해제됨")
            await asyncio.sleep(1.5)
            # await page.screenshot(path=f"./data/debug_test_{test_case['no']}_step3_johoo.png")
            await close_popups()
            result["forceteller_johoo"] = await self._scrape_full_result(page)
            
            # 디버그 스크린샷
            await page.screenshot(path=f"./data/debug_test_{test_case['no']}_final.png")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"[ERROR] Test #{test_case['no']}: {e}")
            # 에러 시 스크린샷 저장
            try:
                await page.screenshot(path=f"./data/debug_test_{test_case['no']}_error.png")
            except:
                pass
        
        finally:
            await page.close()
        
        return result
    
    async def _scrape_result(self, page: Page) -> dict:
        """기본 메타 결과 스크래핑 (사주팔자, 띠, 보정, 신살 - 체크박스 영향 없음)"""
        import re
        data = {}
        
        data["correction_minutes"] = 0
        data["summer_time_minutes"] = 0
        try:
            page_text = await page.content()
            match = re.search(r'지역시\s*(-?\d+)분', page_text)
            if match:
                data["correction_minutes"] = int(match.group(1))
            match = re.search(r'서머타임\s*(-?\d+)분', page_text)
            if match:
                data["summer_time_minutes"] = int(match.group(1))
        except:
            pass
        
        data["zodiac"] = ""
        colors = ["하얀", "검은", "붉은", "푸른", "노란"]
        for color in colors:
            try:
                els = page.locator(f"*:has-text('({color}')")
                for i in range(await els.count()):
                    text = await els.nth(i).text_content(timeout=2000)
                    if text:
                        match = re.search(rf'([가-힣]{{2}})\(({color}\s*[가-힣]+)\)', text)
                        if match:
                            data["zodiac"] = f"{match.group(1)}({match.group(2)})"
                            break
                if data["zodiac"]:
                    break
            except:
                pass
        
        pillars = {"년주": "", "월주": "", "일주": "", "시주": ""}
        label_to_pillar = {"생년": "년주", "생월": "월주", "생일": "일주", "생시": "시주"}
        
        for label, pillar_key in label_to_pillar.items():
            try:
                header = page.locator(f"div[class*='_sGridHeader_']:has-text('{label}')")
                if await header.count() > 0:
                    column = header.locator("xpath=parent::div")
                    ganji_els = column.locator("div[class*='_간지_']")
                    if await ganji_els.count() >= 2:
                        cheongan = await ganji_els.nth(0).text_content(timeout=2000)
                        jiji = await ganji_els.nth(1).text_content(timeout=2000)
                        cheongan_char = cheongan.strip()[0] if cheongan and len(cheongan.strip()) >= 1 else ""
                        jiji_char = jiji.strip()[0] if jiji and len(jiji.strip()) >= 1 else ""
                        pillars[pillar_key] = cheongan_char + jiji_char
            except Exception as e:
                print(f"  [DEBUG] Pillar extraction error for {label}: {e}")
        data["pillars"] = pillars
        
        try:
            sinsal_section = page.locator("p").filter(has_text="신살과 길성")
            sinsal_list = sinsal_section.locator("xpath=following-sibling::p").first
            text = await sinsal_list.text_content(timeout=5000)
            data["sinsal"] = text.strip() if text else ""
        except:
            data["sinsal"] = ""
        
        return data
    
    async def _scrape_full_result(self, page: Page) -> dict:
        """체크박스 조합별 전체 결과 스크래핑 (오행, 십성, 신강, 용신)"""
        data = {}
        
        elements = {}
        elem_map = {"목(木)": "목", "화(火)": "화", "토(土)": "토", "금(金)": "금", "수(水)": "수"}
        for elem, key in elem_map.items():
            try:
                cell = page.locator(f"td:has-text('{elem}')").first
                row = cell.locator("xpath=ancestor::tr")
                cells = row.locator("td")
                if await cells.count() >= 2:
                    value_text = await cells.nth(1).text_content(timeout=3000)
                    pct = self._extract_percentage(value_text or "")
                    elements[key] = pct
            except:
                elements[key] = 0.0
        data["elements"] = elements
        
        ten_gods = {}
        tg_map = {
            "비견(比肩)": "비견", "겁재(劫財)": "겁재", "식신(食神)": "식신", 
            "상관(傷官)": "상관", "편재(偏財)": "편재", "정재(正財)": "정재",
            "편관(偏官)": "편관", "정관(正官)": "정관", "편인(偏印)": "편인", 
            "정인(正印)": "정인"
        }
        for tg_full, tg_short in tg_map.items():
            try:
                cell = page.locator(f"td:has-text('{tg_full}')").first
                row = cell.locator("xpath=ancestor::tr")
                cells = row.locator("td")
                if await cells.count() >= 2:
                    value_text = await cells.nth(1).text_content(timeout=3000)
                    if value_text and value_text.strip() != "-":
                        pct = self._extract_percentage(value_text)
                        ten_gods[tg_short] = pct
                    else:
                        ten_gods[tg_short] = 0.0
            except:
                ten_gods[tg_short] = 0.0
        data["ten_gods"] = ten_gods
        
        data["strength"] = ""
        strength_keywords = ["중화신강", "중화신약", "신강", "신약", "태강", "태약", "극왕", "극약"]
        try:
            page_text = await page.content()
            for kw in strength_keywords:
                if kw in page_text:
                    data["strength"] = kw
                    break
        except:
            pass
        
        yongsin_list = []
        try:
            guardian_div = page.locator("[data-test-id='guardian']")
            if await guardian_div.count() > 0:
                yongsin_els = guardian_div.locator("p")
                for i in range(await yongsin_els.count()):
                    text = await yongsin_els.nth(i).text_content(timeout=2000)
                    if text:
                        yongsin_list.append(text.strip())
        except Exception as e:
            print(f"  [DEBUG] Yongsin extraction error: {e}")
        data["yongsin"] = ", ".join(yongsin_list) if yongsin_list else ""
        
        return data
    
    def _extract_minutes(self, text: str) -> int:
        """텍스트에서 분 추출 (예: '-32분' -> -32)"""
        import re
        match = re.search(r'(-?\d+)분', text or "")
        return int(match.group(1)) if match else 0
    
    def _extract_percentage(self, text: str) -> float:
        """텍스트에서 퍼센트 추출 (예: '37.5% 과다' -> 37.5)"""
        import re
        match = re.search(r'(\d+\.?\d*)%', text or "")
        return float(match.group(1)) if match else 0.0
    
    def _process_engine_result(self, result: dict) -> dict:
        """엔진 결과에서 필요한 데이터 추출 (오행, 십성, 신강, 용신, 기둥)"""
        if "error" in result: 
            print(f"  [DEBUG] Engine Error: {result['error']}")
            return {"error": result["error"]}
        
        # 기둥 추출
        pillars_data = result.get("pillars", [])
        pillars_list = []
        for i in range(4):
            if i < len(pillars_data):
                pillar = pillars_data[i]
                if isinstance(pillar, dict):
                    gan = pillar.get("gan", "")
                    ji = pillar.get("ji", "")
                    pillars_list.append(str(gan) + str(ji))
                else:
                    pillars_list.append("")
            else:
                pillars_list.append("")
        
        # 용신 추출
        yongsin_info = result.get("yongsin_detail") # yongsin_info -> yongsin_detail
        if isinstance(yongsin_info, dict):
            main_yongsin = yongsin_info.get("main_yongsin", "")
        else:
            main_yongsin = ""
            
        # 십성 추출
        ten_gods = result.get("tengod_analysis_dict", {}) # tengod_dict_raw -> tengod_analysis_dict
        
        return {
            "pillars": pillars_list,
            "elements": result.get("scores", {}),
            "ten_gods": ten_gods,
            "strength": result.get("status", ""),
            "power": result.get("power", 0),
            "yongsin": main_yongsin
        }
    
    def run_my_engine(self, test_case: dict) -> dict:
        """내 엔진으로 동일 케이스 4가지 조합 실행"""
        birth_str = f"{test_case['date']} {test_case['time']}"
        gender = "M" if test_case["gender"] == "M" else "F"
        
        base_args = {
            "birth_str": birth_str,
            "gender": gender,
            "location": test_case["location"],
            "use_yajas_i": True,
            "calendar_type": "양력"
        }
        
        results = {}
        
        # 1. 기본 (둘 다 False)
        # 주의: saju_engine analyze는 딕셔너리를 반환해야 함
        res_base = self.engine.analyze(**base_args, use_hap_correction=False, use_johoo_correction=False)
        # 디버그: 결과 키 출력
        if "error" in res_base:
            print(f"  [DEBUG] Engine Error: {res_base['error']}")
        else:
            print(f"  [DEBUG] Engine Result Keys: {list(res_base.keys())}")
            if "scores" in res_base:
                print(f"  [DEBUG] Scores: {res_base['scores']}")
            
        results["base"] = self._process_engine_result(res_base)
        
        # 2. 합만 (hap=True)
        res_hap = self.engine.analyze(**base_args, use_hap_correction=True, use_johoo_correction=False)
        results["hap"] = self._process_engine_result(res_hap)
        
        # 3. 조후만 (johoo=True)
        res_johoo = self.engine.analyze(**base_args, use_hap_correction=False, use_johoo_correction=True)
        results["johoo"] = self._process_engine_result(res_johoo)
        
        # 4. 둘 다 (adj=True, True)
        res_adj = self.engine.analyze(**base_args, use_hap_correction=True, use_johoo_correction=True)
        results["adj"] = self._process_engine_result(res_adj)
        
        return results
    
    def compare_results(self, ft_result: dict, my_result: dict) -> dict:
        """포스텔러 결과와 내 엔진 결과 비교 (기본 설정 기준)"""
        comparison = {
            "pillar_match": True,
            "element_diff_max": 0.0,
            "strength_match": False,
            "differences": []
        }
        
        # 기본(base) 결과끼리 비교
        ft_base = ft_result.get("forceteller", {})
        my_base = my_result.get("base", {})
        
        # 오행 비교
        ft_elements = ft_base.get("elements", {})
        my_elements = my_base.get("elements", {})
        
        elem_map = {"목": "목", "화": "화", "토": "토", "금": "금", "수": "수"}
        for k, v in ft_elements.items():
            my_val = my_elements.get(elem_map.get(k, k), 0)
            diff = abs(v - my_val)
            if diff > comparison["element_diff_max"]:
                comparison["element_diff_max"] = diff
            if diff > 1.0:
                comparison["differences"].append(f"오행 {k}: FT={v}%, MY={my_val}%")
        
        # 신강/신약 비교
        ft_strength = ft_base.get("strength", "")
        my_strength = my_base.get("strength", "")
        if ft_strength and my_strength:
            comparison["strength_match"] = ft_strength in my_strength or my_strength in ft_strength
        
        return comparison
    
    def save_to_db(self, result: dict, my_result: dict, comparison: dict):
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()
        
        test_case = result.get("input", {})
        ft_meta = result.get("forceteller", {})
        ft_base = result.get("forceteller", {})
        ft_hap = result.get("forceteller_hap", {})
        ft_johoo = result.get("forceteller_johoo", {})
        ft_adj = result.get("forceteller_adj", {})
        ft_pillars = ft_meta.get("pillars", {})
        
        # 내 엔진 결과
        my_base = my_result.get("base", {})
        my_hap = my_result.get("hap", {})
        my_johoo = my_result.get("johoo", {})
        my_adj = my_result.get("adj", {})
        my_pillars = my_base.get("pillars", ["", "", "", ""])
        
        def get_elem(d, key): return d.get("elements", {}).get(key, 0)
        def get_tg(d, key): 
            val = d.get("ten_gods", {}).get(key, 0)
            if isinstance(val, dict): return val.get("count", 0)
            return val
        
        cursor.execute("""
            INSERT INTO test_results (
                test_no, test_date, input_date, input_time, gender, location, test_purpose,
                ft_year_pillar, ft_month_pillar, ft_day_pillar, ft_hour_pillar,
                ft_correction_minutes, ft_summer_time_minutes, ft_zodiac,
                
                ft_wood, ft_fire, ft_earth, ft_metal, ft_water,
                ft_wood_hap, ft_fire_hap, ft_earth_hap, ft_metal_hap, ft_water_hap,
                ft_wood_johoo, ft_fire_johoo, ft_earth_johoo, ft_metal_johoo, ft_water_johoo,
                ft_wood_adj, ft_fire_adj, ft_earth_adj, ft_metal_adj, ft_water_adj,
                
                ft_bigyeon, ft_geobje, ft_siksin, ft_sanggwan, ft_pyeonjae,
                ft_jeongjae, ft_pyeongwan, ft_jeonggwan, ft_pyeonin, ft_jeongin,
                
                ft_bigyeon_hap, ft_geobje_hap, ft_siksin_hap, ft_sanggwan_hap, ft_pyeonjae_hap,
                ft_jeongjae_hap, ft_pyeongwan_hap, ft_jeonggwan_hap, ft_pyeonin_hap, ft_jeongin_hap,
                
                ft_bigyeon_johoo, ft_geobje_johoo, ft_siksin_johoo, ft_sanggwan_johoo, ft_pyeonjae_johoo,
                ft_jeongjae_johoo, ft_pyeongwan_johoo, ft_jeonggwan_johoo, ft_pyeonin_johoo, ft_jeongin_johoo,
                
                ft_bigyeon_adj, ft_geobje_adj, ft_siksin_adj, ft_sanggwan_adj, ft_pyeonjae_adj,
                ft_jeongjae_adj, ft_pyeongwan_adj, ft_jeonggwan_adj, ft_pyeonin_adj, ft_jeongin_adj,
                
                ft_strength, ft_strength_hap, ft_strength_johoo, ft_strength_adj,
                ft_yongsin, ft_yongsin_hap, ft_yongsin_johoo, ft_yongsin_adj,
                ft_sinsal,
                
                my_year_pillar, my_month_pillar, my_day_pillar, my_hour_pillar,
                
                my_wood, my_fire, my_earth, my_metal, my_water,
                my_wood_hap, my_fire_hap, my_earth_hap, my_metal_hap, my_water_hap,
                my_wood_johoo, my_fire_johoo, my_earth_johoo, my_metal_johoo, my_water_johoo,
                my_wood_adj, my_fire_adj, my_earth_adj, my_metal_adj, my_water_adj,
                
                my_bigyeon, my_geobje, my_siksin, my_sanggwan, my_pyeonjae,
                my_jeongjae, my_pyeongwan, my_jeonggwan, my_pyeonin, my_jeongin,
                
                my_bigyeon_hap, my_geobje_hap, my_siksin_hap, my_sanggwan_hap, my_pyeonjae_hap,
                my_jeongjae_hap, my_pyeongwan_hap, my_jeonggwan_hap, my_pyeonin_hap, my_jeongin_hap,
                
                my_bigyeon_johoo, my_geobje_johoo, my_siksin_johoo, my_sanggwan_johoo, my_pyeonjae_johoo,
                my_jeongjae_johoo, my_pyeongwan_johoo, my_jeonggwan_johoo, my_pyeonin_johoo, my_jeongin_johoo,
                
                my_bigyeon_adj, my_geobje_adj, my_siksin_adj, my_sanggwan_adj, my_pyeonjae_adj,
                my_jeongjae_adj, my_pyeongwan_adj, my_jeonggwan_adj, my_pyeonin_adj, my_jeongin_adj,
                
                my_strength, my_yongsin,
                my_strength_hap, my_yongsin_hap,
                my_strength_johoo, my_yongsin_johoo,
                my_strength_adj, my_yongsin_adj,
                
                pillar_match, element_diff_max, strength_match
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?,
                
                ?, ?, ?, ?,
                
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,

                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,

                ?, ?, ?
            )
        """, (
            test_case.get("no"), datetime.now().strftime("%Y-%m-%d %H:%M"),
            test_case.get("date"), test_case.get("time"), test_case.get("gender"),
            test_case.get("location"), test_case.get("purpose"),
            
            ft_pillars.get("년주"), ft_pillars.get("월주"), ft_pillars.get("일주"), ft_pillars.get("시주"),
            ft_meta.get("correction_minutes"), ft_meta.get("summer_time_minutes"), ft_meta.get("zodiac"),
            
            get_elem(ft_base, "목"), get_elem(ft_base, "화"), get_elem(ft_base, "토"), get_elem(ft_base, "금"), get_elem(ft_base, "수"),
            get_elem(ft_hap, "목"), get_elem(ft_hap, "화"), get_elem(ft_hap, "토"), get_elem(ft_hap, "금"), get_elem(ft_hap, "수"),
            get_elem(ft_johoo, "목"), get_elem(ft_johoo, "화"), get_elem(ft_johoo, "토"), get_elem(ft_johoo, "금"), get_elem(ft_johoo, "수"),
            get_elem(ft_adj, "목"), get_elem(ft_adj, "화"), get_elem(ft_adj, "토"), get_elem(ft_adj, "금"), get_elem(ft_adj, "수"),
            
            get_tg(ft_base, "비견"), get_tg(ft_base, "겁재"), get_tg(ft_base, "식신"), get_tg(ft_base, "상관"), get_tg(ft_base, "편재"),
            get_tg(ft_base, "정재"), get_tg(ft_base, "편관"), get_tg(ft_base, "정관"), get_tg(ft_base, "편인"), get_tg(ft_base, "정인"),
            
            get_tg(ft_hap, "비견"), get_tg(ft_hap, "겁재"), get_tg(ft_hap, "식신"), get_tg(ft_hap, "상관"), get_tg(ft_hap, "편재"),
            get_tg(ft_hap, "정재"), get_tg(ft_hap, "편관"), get_tg(ft_hap, "정관"), get_tg(ft_hap, "편인"), get_tg(ft_hap, "정인"),
            
            get_tg(ft_johoo, "비견"), get_tg(ft_johoo, "겁재"), get_tg(ft_johoo, "식신"), get_tg(ft_johoo, "상관"), get_tg(ft_johoo, "편재"),
            get_tg(ft_johoo, "정재"), get_tg(ft_johoo, "편관"), get_tg(ft_johoo, "정관"), get_tg(ft_johoo, "편인"), get_tg(ft_johoo, "정인"),
            
            get_tg(ft_adj, "비견"), get_tg(ft_adj, "겁재"), get_tg(ft_adj, "식신"), get_tg(ft_adj, "상관"), get_tg(ft_adj, "편재"),
            get_tg(ft_adj, "정재"), get_tg(ft_adj, "편관"), get_tg(ft_adj, "정관"), get_tg(ft_adj, "편인"), get_tg(ft_adj, "정인"),
            
            ft_base.get("strength"), ft_hap.get("strength"), ft_johoo.get("strength"), ft_adj.get("strength"),
            ft_base.get("yongsin"), ft_hap.get("yongsin"), ft_johoo.get("yongsin"), ft_adj.get("yongsin"),
            ft_meta.get("sinsal"),
            
            # 내 엔진 데이터
            my_pillars[0], my_pillars[1], my_pillars[2], my_pillars[3],
            
            get_elem(my_base, "목"), get_elem(my_base, "화"), get_elem(my_base, "토"), get_elem(my_base, "금"), get_elem(my_base, "수"),
            get_elem(my_hap, "목"), get_elem(my_hap, "화"), get_elem(my_hap, "토"), get_elem(my_hap, "금"), get_elem(my_hap, "수"),
            get_elem(my_johoo, "목"), get_elem(my_johoo, "화"), get_elem(my_johoo, "토"), get_elem(my_johoo, "금"), get_elem(my_johoo, "수"),
            get_elem(my_adj, "목"), get_elem(my_adj, "화"), get_elem(my_adj, "토"), get_elem(my_adj, "금"), get_elem(my_adj, "수"),
            
            get_tg(my_base, "비견"), get_tg(my_base, "겁재"), get_tg(my_base, "식신"), get_tg(my_base, "상관"), get_tg(my_base, "편재"),
            get_tg(my_base, "정재"), get_tg(my_base, "편관"), get_tg(my_base, "정관"), get_tg(my_base, "편인"), get_tg(my_base, "정인"),
            
            get_tg(my_hap, "비견"), get_tg(my_hap, "겁재"), get_tg(my_hap, "식신"), get_tg(my_hap, "상관"), get_tg(my_hap, "편재"),
            get_tg(my_hap, "정재"), get_tg(my_hap, "편관"), get_tg(my_hap, "정관"), get_tg(my_hap, "편인"), get_tg(my_hap, "정인"),
            
            get_tg(my_johoo, "비견"), get_tg(my_johoo, "겁재"), get_tg(my_johoo, "식신"), get_tg(my_johoo, "상관"), get_tg(my_johoo, "편재"),
            get_tg(my_johoo, "정재"), get_tg(my_johoo, "편관"), get_tg(my_johoo, "정관"), get_tg(my_johoo, "편인"), get_tg(my_johoo, "정인"),
            
            get_tg(my_adj, "비견"), get_tg(my_adj, "겁재"), get_tg(my_adj, "식신"), get_tg(my_adj, "상관"), get_tg(my_adj, "편재"),
            get_tg(my_adj, "정재"), get_tg(my_adj, "편관"), get_tg(my_adj, "정관"), get_tg(my_adj, "편인"), get_tg(my_adj, "정인"),
            
            my_base.get("strength"), my_base.get("yongsin"),
            my_hap.get("strength"), my_hap.get("yongsin"),
            my_johoo.get("strength"), my_johoo.get("yongsin"),
            my_adj.get("strength"), my_adj.get("yongsin"),
            
            comparison["pillar_match"], comparison["element_diff_max"], comparison["strength_match"]
        ))
        
        conn.commit()
        conn.close()
    
    async def run_all_tests(self, test_cases: list):
        """모든 테스트 케이스 실행"""
        async with async_playwright() as p:
            # OrbStack/Docker 환경에서는 headless=True 필수
            # slow_mo로 안정성 향상
            browser = await p.chromium.launch(
                headless=True,
                slow_mo=100,  # 각 액션 사이에 100ms 대기
                args=['--no-sandbox', '--disable-dev-shm-usage']  # Docker/컨테이너 환경용
            )
            
            for tc in test_cases:
                print(f"\n[TEST #{tc['no']}] {tc['date']} {tc['time']} / {tc['gender']} / {tc['location']}")
                print(f"  목적: {tc['purpose']}")
                
                # 포스텔러 테스트
                ft_result = await self.run_single_test(browser, tc)
                
                if "error" in ft_result:
                    print(f"  [ERROR] {ft_result['error']}")
                    continue
                
                # 내 엔진 테스트
                my_result = self.run_my_engine(tc)
                
                # 비교
                comparison = self.compare_results(ft_result, my_result)
                
                # DB 저장
                self.save_to_db(ft_result, my_result, comparison)
                
                # 결과 출력
                print(f"  [FT] 오행: {ft_result.get('forceteller', {}).get('elements', {})}")
                print(f"  [MY] 오행: {my_result.get('base', {}).get('elements', {})}")
                print(f"  [비교] 최대 오행 차이: {comparison['element_diff_max']:.1f}%")
                print(f"  [비교] 신강/신약 일치: {'O' if comparison['strength_match'] else 'X'}")
                
                if comparison["differences"]:
                    for diff in comparison["differences"]:
                        print(f"    - {diff}")
                
                await asyncio.sleep(2)  # 서버 부하 방지
            
            await browser.close()
        
        print(f"\n완료! 결과가 {self.DB_PATH}에 저장되었습니다.")


# 테스트 케이스 데이터
TEST_CASES = [
    {"no": 1, "date": "1990-02-04", "time": "11:14", "gender": "M", "location": "서울", "purpose": "입춘 절입 (연주 변경 경계)"},
    {"no": 2, "date": "1988-05-15", "time": "10:30", "gender": "F", "location": "서울", "purpose": "80년대 썸머타임 적용"},
    {"no": 3, "date": "2026-01-25", "time": "23:40", "gender": "M", "location": "서울", "purpose": "야자시 (일주 유지, 시주 다음날)"},
    {"no": 4, "date": "2026-01-26", "time": "00:20", "gender": "F", "location": "서울", "purpose": "조자시 (일주/시주 모두 변경)"},
    {"no": 5, "date": "1954-03-21", "time": "12:00", "gender": "M", "location": "서울", "purpose": "127.5도 표준시 적용기"},
    {"no": 6, "date": "2023-04-10", "time": "15:00", "gender": "F", "location": "서울", "purpose": "윤달(윤2월) 대운수 산출"},
    {"no": 7, "date": "2024-10-20", "time": "11:31", "gender": "M", "location": "서울", "purpose": "동경 135도 시차 보정 (사시/오시)"},
    {"no": 8, "date": "2024-08-07", "time": "09:09", "gender": "F", "location": "서울", "purpose": "입추 절입 (분 단위 월주 변경)"},
    {"no": 9, "date": "2024-12-21", "time": "18:20", "gender": "M", "location": "서울", "purpose": "동지 (학파별 세수 변경 옵션)"},
    {"no": 10, "date": "2025-02-03", "time": "23:10", "gender": "F", "location": "서울", "purpose": "2025년 입춘 절입 시점"},
    {"no": 11, "date": "1951-07-15", "time": "12:00", "gender": "M", "location": "서울", "purpose": "6.25 전쟁 중 썸머타임 적용"},
    {"no": 12, "date": "1912-01-01", "time": "00:00", "gender": "F", "location": "서울", "purpose": "대한제국→일본 표준시 전환기"},
    {"no": 13, "date": "2025-07-24", "time": "10:00", "gender": "M", "location": "서울", "purpose": "윤달(윤6월) 끝자락 절입 처리"},
    {"no": 14, "date": "2025-01-05", "time": "11:55", "gender": "F", "location": "서울", "purpose": "소한 절입 (월건 변경)"},
    {"no": 15, "date": "1961-08-10", "time": "00:00", "gender": "M", "location": "서울", "purpose": "표준시 재설정(135도 복귀)"},
    {"no": 16, "date": "2026-05-05", "time": "00:31", "gender": "F", "location": "서울", "purpose": "자시 경계(23:32 시작 여부)"},
    {"no": 17, "date": "2025-12-31", "time": "23:45", "gender": "M", "location": "서울", "purpose": "연말연시 야자시 적용"},
    {"no": 18, "date": "1987-05-10", "time": "10:00", "gender": "F", "location": "서울", "purpose": "87년 썸머타임 및 대운 순역"},
    {"no": 19, "date": "2024-06-21", "time": "05:51", "gender": "M", "location": "서울", "purpose": "하지(夏至) 절입 및 월주 기운"},
    {"no": 20, "date": "1948-06-01", "time": "12:00", "gender": "F", "location": "서울", "purpose": "대한민국 정부 수립기 첫 썸머타임"},
    {"no": 21, "date": "2024-06-21", "time": "11:40", "gender": "M", "location": "인천", "purpose": "서부 경도 보정 (사시 유지 확인)"},
    {"no": 22, "date": "2024-06-21", "time": "11:15", "gender": "F", "location": "포항", "purpose": "동부 경도 보정 (오시 진입 확인)"},
    {"no": 23, "date": "2025-03-10", "time": "14:30", "gender": "M", "location": "서귀포", "purpose": "남부 최서단 경도 및 대운 역행"},
    {"no": 24, "date": "2025-02-03", "time": "23:11", "gender": "F", "location": "속초", "purpose": "북동부 입춘 절입 및 대운 순행"},
    {"no": 25, "date": "2026-01-25", "time": "23:35", "gender": "M", "location": "목포", "purpose": "전남 지역 야자시 시작점 체크"},
    {"no": 26, "date": "2024-08-07", "time": "09:10", "gender": "F", "location": "대구", "purpose": "경북 지역 입추 절입 시각 보정"},
    {"no": 27, "date": "1955-07-05", "time": "10:30", "gender": "M", "location": "부산", "purpose": "50년대 표준시+썸머타임+부산 경도"},
    {"no": 28, "date": "2024-12-21", "time": "18:25", "gender": "F", "location": "청주", "purpose": "중부 내륙 동지 절입 시차"},
    {"no": 29, "date": "2024-05-05", "time": "11:10", "gender": "M", "location": "울릉도", "purpose": "최동단 경도 (일본시와 최소 시차)"},
    {"no": 30, "date": "2024-10-10", "time": "15:30", "gender": "F", "location": "전주", "purpose": "전북 지역 신시(申時) 보정 검증"},
]


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="포스텔러 만세력 자동 테스트")
    parser.add_argument("--start", type=int, default=1, help="시작 테스트 번호")
    parser.add_argument("--end", type=int, default=30, help="종료 테스트 번호")
    parser.add_argument("--single", type=int, help="단일 테스트 번호")
    args = parser.parse_args()
    
    tester = ForceTellerTester()
    
    if args.single:
        cases = [tc for tc in TEST_CASES if tc["no"] == args.single]
    else:
        cases = [tc for tc in TEST_CASES if args.start <= tc["no"] <= args.end]
    
    print(f"테스트 대상: {len(cases)}개 케이스")
    asyncio.run(tester.run_all_tests(cases))


if __name__ == "__main__":
    main()
