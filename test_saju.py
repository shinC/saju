from saju_engine import SajuEngine

class ExpertPresenter:
    def __init__(self, engine):
        self.engine = engine
        self.h = {'甲':'갑','乙':'을','丙':'병','丁':'정','戊':'무','己':'기','庚':'경','辛':'신','壬':'임','癸':'계','子':'자','丑':'축','寅':'인','卯':'묘','辰':'진','巳':'사','午':'오','未':'미','申':'신','酉':'유','戌':'술','亥':'해'}
        self.sinsal_desc = {
            "화개살": "예술적 감수성과 성찰", "현침살": "예리한 분석과 전문 기술", "백호대살": "강력한 리더십과 추진력",
            "관귀학관": "관직/조직 내 학문적 성취", "태극귀인": "위기 시 귀인의 도움", "정록(록신)": "안정적인 자수성가",
            "홍염살": "다정한 매력과 외모", "도화살": "대중적 인기와 사교성", "천을귀인": "최고의 수호신"
        }

    def render(self, data):
        tr = data['current_trace']; p = data['pillars']
        
        # [PART 1] 정밀 만세력 데이터 테이블 (v28.3 복구본)
        print(f"\n사용자 정보: [생년월일: {data['birth']}] [성별: {'남' if data['gender']=='M' else '여'}]")
        print(f"▶ 현재 운세 ({tr['date']}): {tr['age']}세 / {tr['daeun']['start_age']}세 대운 [{tr['daeun']['ganzi']}]")
        print(f"▶ 오늘의 간지: [연운:{tr['seun']}] [월운:{tr['wolun']}] [일진:{tr['ilun']}]")
        print("="*145)
        print(f"구분    | 천간(십성)          | 지지(십성/12신살)               | 심층 길성 및 신살")
        print("-" * 145)
        labels = ["연주", "월주", "일주", "시주"]
        all_specials = []
        for i in range(4):
            pill = p[i]
            t_gan = f"{pill['gan']}({self.h[pill['gan']]})({pill['t_gan']:<4})"
            t_ji = f"{pill['ji']}({self.h[pill['ji']]})({pill['t_ji']:<4}) {pill['sinsal_12']:<8}"
            spec = ", ".join(pill['special']) if pill['special'] else "-"
            all_specials.extend(pill['special'])
            print(f"{labels[i]:<5} | {t_gan:<20} | {t_ji:<30} | {spec}")
        print("-" * 145)

        # [핵심] 요청하신 요약 정보 섹션 복구
        print(f"▶ 오행 분석 (점수): {data['scores']}")
        print(f"▶ 나의 오행: {data['me']}({self.h[data['me']]}) {data['me_elem']} | 신강약: {data['power']}점({data['status']}) | 용신: {data['yongsin']} | 대운수: {data['daeun_num']}")
        daeun_path_str = " -> ".join([f"[{d['start_age']}세 {d['ganzi']}]" for d in data['daeun_list']])
        print(f"▶ 100세 대운 경로: {daeun_path_str}")

        # [PART 2] 심층 신살 분석
        print(f"\n✨ 전문가의 신살 심층 해석")
        print("="*85)
        unique_specials = sorted(list(set(all_specials)))
        for s in unique_specials:
            print(f" ● {s:<10}: {self.sinsal_desc.get(s, '삶에 독특한 에너지를 부여합니다.')}")
        print("="*85)

        # [PART 3] 프리미엄 스토리텔링 리포트
        print(f"\n" + "═"*110 + "\n   반갑습니다. 30년 경력의 명리학 전문가가 귀하의 전 생애 운명을 정밀 분석해 드립니다.\n" + "═"*110)
        print(f"🔮 1. 타고난 본질: 귀하는 {data['me']}({self.h[data['me']]}) 일간으로 보석처럼 섬세하고 결단력이 있습니다.")
        print(f"   신강약 분석 결과 **'{data['status']}'**한 명식이며, **'{data['yongsin']}'** 기운이 들어올 때 크게 발복합니다.")
        print(f"\n📅 4. 실시간 분석: 현재 {tr['age']}세, {tr['wolun']}(무자)월을 지나고 있으며 귀인의 도움이 따르는 시기입니다.\n" + "═"*110 + "\n")

if __name__ == "__main__":
    engine = SajuEngine('manse_data.json', 'term_data.json')
    presenter = ExpertPresenter(engine)
    # 1981년생 테스트 케이스 (장성살 및 요약 정보 출력 검증)
    result = engine.analyze("1981-03-04 14:01", "M")
    presenter.render(result)