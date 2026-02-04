#!/usr/bin/env python3
"""
디버그용: 포스텔러 결과 페이지 HTML 구조 분석
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_scrape():
    """테스트 케이스 2번으로 페이지 구조 분석"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            slow_mo=100,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = await browser.new_page()
        
        try:
            # 1. 사이트 접속
            print("1. 사이트 접속...")
            await page.goto("https://pro.forceteller.com/", timeout=60000)
            await page.wait_for_selector("button:has-text('시작하기')", timeout=30000)
            await page.click("button:has-text('시작하기')")
            await page.wait_for_url("**/profile/edit", timeout=30000)
            
            # 2. 폼 입력 (테스트 2: 1988-05-15 10:30 여자 서울)
            print("2. 폼 입력...")
            await page.fill("input[placeholder*='12글자']", "테스트2")
            await page.locator("label").filter(has_text="여자").click()
            await page.locator("input[placeholder*='04/06']").fill("1988/05/15")
            await page.locator("input[placeholder*='19:00']").fill("10:30")
            
            city_button = page.get_by_role("group").filter(has_text="도시").get_by_role("button")
            await city_button.click(timeout=10000)
            await page.wait_for_selector("input[placeholder*='시군구']", timeout=10000)
            await page.fill("input[placeholder*='시군구']", "서울")
            await page.press("input[placeholder*='시군구']", "Enter")
            await asyncio.sleep(0.5)
            await page.locator("li").filter(has_text="대한민국").first.click(timeout=10000)
            
            # 3. 만세력 보러가기
            print("3. 만세력 보러가기...")
            await page.wait_for_selector("button:has-text('만세력 보러가기'):not([disabled])", timeout=10000)
            await page.click("button:has-text('만세력 보러가기')")
            
            # 확인 페이지 (요소로 확인 - URL이 변경되지 않을 수 있음)
            await page.wait_for_selector("text=입력하신 프로필을 확인해주세요", timeout=30000)
            print("\n=== 확인 페이지 전체 텍스트 ===")
            confirm_text = await page.locator("body").text_content()
            print(confirm_text[:2000] if confirm_text else "없음")
            
            # 보정 정보 캡처
            print("\n--- 보정 정보 ---")
            correction_els = page.locator("div:has-text('보정'), p:has-text('보정')")
            for i in range(await correction_els.count()):
                text = await correction_els.nth(i).text_content()
                if text and ("분" in text or "서머타임" in text):
                    print(f"  {text[:100]}")
            
            # 확인 페이지에서 만세력 보러가기 클릭 (결과 페이지로 이동)
            await page.click("button:has-text('만세력 보러가기')")
            
            # 결과 페이지 (URL 또는 요소로 확인)
            print("4. 결과 페이지 대기...")
            # 페이지 로딩 대기 - URL 체크 또는 특정 요소
            await asyncio.sleep(3)
            current_url = page.url
            print(f"  현재 URL: {current_url}")
            
            # 스크린샷 먼저 저장
            await page.screenshot(path="./data/debug_after_confirm.png", full_page=True)
            print("  스크린샷 저장: ./data/debug_after_confirm.png")
            
            # 결과 페이지 로딩 대기 (여러 셀렉터 시도)
            try:
                await page.wait_for_selector("table", timeout=30000)
            except:
                pass
            
            await asyncio.sleep(2)
            
            for attempt in range(10):
                dialog = page.locator(".MuiDialog-root, .MuiModal-root")
                if await dialog.count() == 0:
                    break
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.3)
                if await dialog.count() > 0:
                    await page.evaluate("""
                        () => {
                            document.querySelectorAll('.MuiDialog-root, .MuiModal-root, [role="presentation"]').forEach(el => el.remove());
                            document.querySelectorAll('[aria-hidden="true"]').forEach(el => el.removeAttribute('aria-hidden'));
                        }
                    """)
                    await asyncio.sleep(0.3)
            
            await asyncio.sleep(1)
            
            # 4. 결과 페이지 분석
            print("\n=== 결과 페이지 분석 ===")
            
            # 스크린샷 저장
            await page.screenshot(path="./data/debug_result_page.png", full_page=True)
            print("스크린샷 저장: ./data/debug_result_page.png")
            
            # 전체 HTML 저장
            html = await page.content()
            with open("./data/debug_result_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML 저장: ./data/debug_result_page.html")
            
            # 주요 요소 텍스트 출력
            print("\n--- 띠 관련 텍스트 (하얀, 검은, 붉은, 푸른, 노란 포함) ---")
            colors = ["하얀", "검은", "붉은", "푸른", "노란"]
            for color in colors:
                els = page.locator(f"*:has-text('{color}')")
                count = await els.count()
                if count > 0:
                    for i in range(min(count, 3)):
                        text = await els.nth(i).text_content()
                        if text and len(text) < 100:
                            print(f"  [{color}] {text[:80]}")
            
            print("\n--- 사주팔자 테이블 (생년/월/일/시) ---")
            # 테이블 구조 분석
            tables = page.locator("table")
            table_count = await tables.count()
            print(f"테이블 개수: {table_count}")
            
            for i in range(min(table_count, 5)):
                table = tables.nth(i)
                text = await table.text_content()
                if text and ("생년" in text or "목(" in text or "비견" in text):
                    print(f"\n테이블 {i}:")
                    rows = table.locator("tr")
                    row_count = await rows.count()
                    for j in range(min(row_count, 10)):
                        row_text = await rows.nth(j).text_content()
                        print(f"  Row {j}: {row_text[:100] if row_text else ''}")
            
            print("\n--- 신강/신약 관련 텍스트 ---")
            keywords = ["신강", "신약", "중화", "태강", "태약", "극왕", "극약"]
            for kw in keywords:
                els = page.locator(f"*:has-text('{kw}')")
                count = await els.count()
                if count > 0:
                    for i in range(min(count, 2)):
                        text = await els.nth(i).text_content()
                        if text and "한 사주" in text:
                            print(f"  [{kw}] {text[:100]}")
                            break
            
            print("\n--- 용신 관련 텍스트 ---")
            yongsin_keywords = ["용신", "조후", "억부"]
            for kw in yongsin_keywords:
                els = page.locator(f"*:has-text('{kw}')")
                count = await els.count()
                if count > 0:
                    for i in range(min(count, 3)):
                        text = await els.nth(i).text_content()
                        if text and len(text) < 100:
                            print(f"  [{kw}] {text}")
            
            print("\n--- 체크박스 관련 ---")
            checkboxes = page.locator("input[type='checkbox'], [role='checkbox']")
            checkbox_count = await checkboxes.count()
            print(f"체크박스 개수: {checkbox_count}")
            
            # 합에 따른 오행 변화 적용 텍스트 찾기
            hap_text = page.get_by_text("합에 따른 오행 변화 적용")
            if await hap_text.count() > 0:
                parent = hap_text.locator("xpath=..")
                parent_html = await parent.evaluate("el => el.outerHTML")
                print(f"합 체크박스 부모 HTML: {parent_html[:300]}")
            
            # 조후와 궁성 보정값 적용 텍스트 찾기
            johu_text = page.get_by_text("조후와 궁성 보정값 적용")
            if await johu_text.count() > 0:
                parent = johu_text.locator("xpath=..")
                parent_html = await parent.evaluate("el => el.outerHTML")
                print(f"조후 체크박스 부모 HTML: {parent_html[:300]}")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path="./data/debug_error.png", full_page=True)
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape())
