import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

try:
    from forceteller_test import ForceTellerTester, TEST_CASES
except ImportError:
    # If running from a different directory
    sys.path.append("/Users/taeheonshin/dev/python/saju")
    from forceteller_test import ForceTellerTester, TEST_CASES

MD_PATH = "/Users/taeheonshin/dev/python/saju/.ai/forceteller.md"

def format_percentage(val):
    return f"{val}%" if isinstance(val, (int, float)) else val

def format_result_to_md(test_case, ft_result, my_result):
    lines = []
    
    # Header
    lines.append(f"## 테스트 케이스 #{test_case['no']}")
    lines.append(f"- **테스트 일시**: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"- **입력 데이터**: {test_case['date']} {test_case['time']} (양력), {'남자' if test_case['gender']=='M' else '여자'}, {test_case['location']}")
    lines.append(f"- **테스트 목적**: {test_case['purpose']}")
    lines.append("")
    
    # Forceteller Result Section
    lines.append("### 포스텔러 결과")
    lines.append("")
    
    # 1. Basic Info
    ft_base = ft_result.get("forceteller", {})
    ft_meta = ft_result.get("forceteller", {}) # Meta is mixed in
    
    lines.append("#### 기본 정보")
    lines.append(f"- 띠: {ft_meta.get('zodiac', '미수집')}")
    lines.append(f"- 지역시 보정: {ft_meta.get('correction_minutes', 0)}분")
    lines.append(f"- 서머타임 보정: {ft_meta.get('summer_time_minutes', 0)}분")
    lines.append("")
    
    # 2. Pillars (Saju Palja)
    pillars = ft_meta.get("pillars", {})
    lines.append("#### 사주팔자")
    lines.append("| 주 | 간지 |")
    lines.append("|---|------|")
    lines.append(f"| 년주 | {pillars.get('년주', '')} |")
    lines.append(f"| 월주 | {pillars.get('월주', '')} |")
    lines.append(f"| 일주 | {pillars.get('일주', '')} |")
    lines.append(f"| 시주 | {pillars.get('시주', '')} |")
    lines.append("")
    
    # 3. Elements (Base)
    lines.append("#### 오행 분포 (합/조후 보정 없음)")
    lines.append("| 오행 | 비율 |")
    lines.append("|------|------|")
    elements = ft_base.get("elements", {})
    for elem in ["목", "화", "토", "금", "수"]:
        lines.append(f"| {elem} | {format_percentage(elements.get(elem, 0))} |")
    lines.append("")
    
    # 4. Ten Gods (Base)
    lines.append("#### 십성 분포 (합/조후 보정 없음)")
    lines.append("| 십성 | 비율 |")
    lines.append("|------|------|")
    ten_gods = ft_base.get("ten_gods", {})
    for tg in ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]:
        lines.append(f"| {tg} | {format_percentage(ten_gods.get(tg, 0))} |")
    lines.append("")
    
    # 5. Strength & Yongsin (Base)
    lines.append("#### 신강/신약 & 용신 (합/조후 보정 없음)")
    lines.append(f"- 신강/신약: **{ft_base.get('strength', '')}**")
    lines.append(f"- 용신: **{ft_base.get('yongsin', '')}**")
    lines.append("")
    
    # 6. Sinsal
    lines.append("#### 신살과 길성")
    lines.append(f"- {ft_meta.get('sinsal', '')}")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # 7. Adjusted Results (Both ON)
    ft_adj = ft_result.get("forceteller_adj", {})
    if ft_adj:
        lines.append("### 합/조후 보정 적용 결과")
        lines.append("")
        
        lines.append("#### 오행 분포 (합+조후 보정 적용)")
        lines.append("| 오행 | 비율 |")
        lines.append("|------|------|")
        elements_adj = ft_adj.get("elements", {})
        for elem in ["목", "화", "토", "금", "수"]:
            lines.append(f"| {elem} | {format_percentage(elements_adj.get(elem, 0))} |")
        lines.append("")
        
        lines.append("#### 십성 분포 (합+조후 보정 적용)")
        lines.append("| 십성 | 비율 |")
        lines.append("|------|------|")
        ten_gods_adj = ft_adj.get("ten_gods", {})
        for tg in ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]:
            lines.append(f"| {tg} | {format_percentage(ten_gods_adj.get(tg, 0))} |")
        lines.append("")
        
        lines.append("#### 신강/신약 & 용신 (합+조후 보정 적용)")
        lines.append(f"- 신강/신약: **{ft_adj.get('strength', '')}**")
        lines.append(f"- 용신: **{ft_adj.get('yongsin', '')}**")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)

async def run_batch():
    start_case = 28
    end_case = 30
    
    print(f"Starting test cases {start_case} to {end_case}...")
    
    # Filter cases
    cases = [tc for tc in TEST_CASES if start_case <= tc["no"] <= end_case]
    
    tester = ForceTellerTester()
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, slow_mo=100)
        
        for tc in cases:
            print(f"Running Test #{tc['no']}...")
            try:
                # Run Test
                ft_result = await tester.run_single_test(browser, tc)
                
                if "error" in ft_result:
                    print(f"Error in Test #{tc['no']}: {ft_result['error']}")
                    continue
                
                # Run Local Engine (Optional for MD generation but good for completeness/DB)
                my_result = tester.run_my_engine(tc)
                
                # Format Output
                md_content = format_result_to_md(tc, ft_result, my_result)
                
                # Append to File
                with open(MD_PATH, "a", encoding="utf-8") as f:
                    f.write(md_content + "\n")
                
                print(f"Saved Test #{tc['no']} to {MD_PATH}")
                
            except Exception as e:
                print(f"Exception in Test #{tc['no']}: {e}")
                import traceback
                traceback.print_exc()
                
            await asyncio.sleep(2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_batch())
