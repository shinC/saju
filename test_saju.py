import json
from datetime import datetime, timedelta
from saju_engine import SajuEngine 
from FortuneBridge import FortuneBridge

class ExpertPresenter:
    def __init__(self, engine, bridge):
        self.engine = engine
        self.bridge = bridge 
        self.h = {'甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기','庚':'경','辛':'신','壬':'임','癸':'계','子':'자','丑':'축','寅':'인','卯':'묘','辰':'진','巳':'사','午':'오','未':'미','申':'신','酉':'유','戌':'술','亥':'해'}
        self.sinsal_desc = {
            "화개살": "예술적 감수성과 성찰", "현침살": "예리한 분석과 전문 기술", "백호대살": "강력한 리더십과 추진력",
            "관귀학관": "관직/조직 내 학문적 성취", "태극귀인": "위기 시 귀인의 도움", "정록(록신)": "안정적인 자수성가",
            "홍염살": "다정한 매력과 외모", "도화살": "대중적 인기와 사교성", "천을귀인": "최고의 수호신",
            "장성살": "조직의 중심이자 리더의 기운", "역마살": "변화와 이동을 통한 발전"
        }

    def render(self, data):
        tr = data['current_trace']
        p = data['pillars']
        yd = data['yongsin_detail']
        dl = data['daeun_list']
        # [NEW 데이터 추출] 엔진에서 추가한 재물/커리어 분석 데이터
        wa = data.get('wealth_analysis', {})
        
        ilju_info = self.bridge.get_ilju_report(data['ilju'])
        lucky_info = self.bridge.get_lucky_report(yd['eokbu_elements'])

        # [PART 1] 정밀 만세력 데이터 테이블
        print(f"\n" + "═"*145)
        print(f" 🔮 {ilju_info['title']} - [{data['ilju']}] {ilju_info['mbti']} 유형의 정밀 분석 리포트")
        print("═"*145)
        print(f"사용자 정보: [생년월일: {data['birth']}] [성별: {'남' if data['gender']=='M' else '여'}]")
        print(f"▶ 현재 운세 ({tr['date']}): {tr['age']}세 / {tr['daeun']['start_age']}세 대운 [{tr['daeun']['ganzi']}] (점수: {tr['daeun'].get('score', '-')})")
        print(f"▶ 오늘의 간지: [연운:{tr['seun']}] [월운:{tr['wolun']}] [일진:{tr['ilun']}]")
        print("="*145)
        print(f"구분    | 천간(십성)          | 지지(십성/12신살)               | 심층 길성 및 신살")
        print("-" * 145)
        
        labels = ["연주", "월주", "일주", "시주"]
        all_specials = []
        for i in range(4):
            pill = p[i]
            gan_h = f"{pill['gan']}({self.h[pill['gan']]})"
            ji_h = f"{pill['ji']}({self.h[pill['ji']]})"
            t_gan = f"{gan_h}({pill['t_gan']:<4})"
            t_ji = f"{ji_h}({pill['t_ji']:<4}) {pill['sinsal_12']:<8}"
            spec = ", ".join(pill['special']) if pill['special'] else "-"
            all_specials.extend(pill['special'])
            print(f"{labels[i]:<5} | {t_gan:<20} | {t_ji:<30} | {spec}")
        print("-" * 145)

        # [기존] 요약 정보 섹션
        print(f"▶ 오행 분석 (점수): {data['scores']}")
        me_h = f"{data['me']}({self.h[data['me']]})"
        yongsin_display = f"{yd['eokbu_elements']} ({yd['eokbu_type']})"
        print(f"▶ 나의 본질: {me_h} {data['me_elem']} | 신강약 지수: {data['power']}점 | 상태: **{data['status']}**")
        print(f"▶ 억부 용신: {yongsin_display} | 조후 용신: {yd['johoo']}")
        
        daeun_path_str = " -> ".join([f"[{d['start_age']}세 {d['ganzi']}({d.get('score', 0)}점)]" for d in dl])
        print(f"▶ 100세 대운 경로: {daeun_path_str}")

        # [기존] 행운의 아이템 및 성격 키워드 섹션
        print(f"\n🍀 나를 돕는 행운의 에너지 (Lucky Items)")
        print(f" └ 행운의 컬러: {lucky_info['color']} | 숫자: {lucky_info['number']} | 방향: {lucky_info['direction']}")
        print(f" └ 추천 아이템: {lucky_info['item']}")
        
        print(f"\n🧠 성격 본캐 분석 (Personality MBTI)")
        print(f" └ 키워드: {', '.join(ilju_info['tags'])}")
        print(f" └ 상세: {ilju_info['description']}")

        # [NEW] 재물 및 커리어 성공 지수 섹션 (추가됨)
        if wa:
            print(f"\n💰 재물 및 직업 성공 지수 (Wealth & Success)")
            w_bar = "●" * (wa['wealth_score'] // 10) + "○" * (10 - (wa['wealth_score'] // 10))
            c_bar = "●" * (wa['career_score'] // 10) + "○" * (10 - (wa['career_score'] // 10))
            print(f" └ 평생 재물운: {wa['wealth_grade']:<10} | 점수: {wa['wealth_score']:>3}점 | {w_bar}")
            print(f" └ 커리어 등급: {wa['career_grade']:<10} | 점수: {wa['career_score']:>3}점 | {c_bar}")

        # [기존] PART 2: 심층 신살 분석
        print(f"\n✨ 전문가의 신살 심층 해석")
        print("="*85)
        unique_specials = sorted(list(set(all_specials)))
        for s in unique_specials:
            print(f" ● {s:<10}: {self.sinsal_desc.get(s, '삶에 독특한 에너지를 부여합니다.')}")
        print("="*85)

        # [기존] PART 4: 인생 운세 리듬
        print(f"\n📈 인생 운세 리듬 (대운별 점수 분석)")
        print("="*85)
        for d in dl:
            score = d.get('score', 0)
            bar = "★" * (score // 10) + "☆" * (10 - (score // 10))
            current_tag = " <--- [현재 대운]" if d['start_age'] <= tr['age'] < d['start_age'] + 10 else ""
            print(f" {d['start_age']:>3}세 ~ | {d['ganzi']}운 : {score:>3}점 | {bar}{current_tag}")
        print("="*85)

        # [기존] PART 3: 프리미엄 스토리텔링 리포트
        print(f"\n" + "═"*110 + "\n   반갑습니다. 20년 경력의 명리학 전문가가 귀하의 전 생애 운명을 정밀 분석해 드립니다.\n" + "═"*110)
        print(f"🔮 1. 타고난 본질: 귀하는 {me_h} 일간으로 해당 오행의 특성을 깊게 간직하고 있습니다.")
        print(f"   분석 결과 귀하는 **'{data['status']}'**한 에너지를 가지고 있으며, **'{yd['eokbu_elements']}'** 기운이 올 때 발복합니다.")
        
        curr_score = tr['daeun'].get('score', 0)
        advice = "준비하며 때를 기다려야 하는 시기입니다."
        if curr_score >= 80: advice = "인생의 황금기입니다. 적극적으로 도전하세요!"
        elif curr_score >= 60: advice = "순탄한 흐름입니다. 내실을 다지기 좋습니다."
        
        print(f"🔮 2. 대운 분석: 현재 대운 점수는 **{curr_score}점**으로, {advice}")
        
        # [NEW] 재물운 등급에 따른 스토리텔링 한 줄 추가
        print(f"🔮 3. 자산 잠재력: 귀하의 재물운 등급은 **'{wa.get('wealth_grade', 'B')}'**형으로, 전략적인 자산 관리가 성공의 핵심입니다.")

        wolun_h = f"{tr['wolun']}({self.h[tr['wolun'][0]]}{self.h[tr['wolun'][1]]})"
        print(f"\n📅 4. 실시간 분석: 현재 {tr['age']}세, {wolun_h}월을 지나고 있으며 기운의 흐름이 변화하는 시기입니다.\n" + "═"*110 + "\n")
        print(f"샤주팔자 { data['interactions']}")

if __name__ == "__main__":
    engine = SajuEngine('manse_data.json', 'term_data.json')
    bridge = FortuneBridge('ilju_data.json') 
    presenter = ExpertPresenter(engine, bridge)
    
    print("시스템: SajuEngine v1.9 및 통합 분석(재물운 포함)을 시작합니다...")
    
    # 분석 실행 (사용자님의 생년월일 기준)
    test_result = engine.analyze("1954-10-05 16:01", "W", location='서울')

    # 결과 출력
    presenter.render(test_result)