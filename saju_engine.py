import json
import math
from datetime import datetime, timedelta
import saju_constants as sc

class SajuEngine:
    def __init__(self, m_file, t_file):
        with open(m_file, 'r', encoding='utf-8') as f: self.m_db = json.load(f)
        with open(t_file, 'r', encoding='utf-8') as f: self.t_db = json.load(f)
        self.SIXTY_GANZI = [f"{sc.STEMS[i%10]}{sc.BRANCHES[i%12]}" for i in range(60)]
    def _get_historical_correction(self, dt):
        """[Priority 2] 역사적 표준시 및 서머타임 보정 로직 (유지)"""
        offset = 0
        ts = dt.strftime("%Y%m%d%H%M")
        if "190804010000" <= ts <= "191112312359": offset += 30
        elif "195403210000" <= ts <= "196108092359": offset += 30
        dst_periods = [
            ("194806010000", "194809130000"), ("194904030000", "194909110000"),
            ("195004010000", "195009100000"), ("195105060000", "195109090000"),
            ("195505050000", "195509090000"), ("195605200000", "195609300000"),
            ("195705050000", "195709220000"), ("195805040000", "195809210000"),
            ("195905030000", "195909200000"), ("196005010000", "196009180000"),
            ("198705100200", "198710110300"), ("198805080200", "198810090300")
        ]
        for start, end in dst_periods:
            if start <= ts <= end:
                offset -= 60
                break
        return offset

    def _get_equation_of_time(self, dt):
        """[Priority 3] 균시차(Equation of Time) 보정 로직 (유지)"""
        day_of_year = dt.timetuple().tm_yday
        b = math.radians((360 / 365.25) * (day_of_year - 81))
        eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
        return eot

    def _get_jasi_type(self, dt):
        """
        [Priority 4 추가] 자시 구간 판정 메소드
        - YAJAS-I (야자시): 23:00 ~ 00:00
        - JOJAS-I (조자시): 00:00 ~ 01:00
        - NORMAL: 그 외 시간
        """
        hour = dt.hour
        if hour == 23: return "YAJAS-I"
        if hour == 0: return "JOJAS-I"
        return "NORMAL"

    def _get_solar_terms(self, dt_in):
        """[절기 연산] 로직 (유지)"""
        year_terms = []
        for y in [dt_in.year-1, dt_in.year, dt_in.year+1]:
            if str(y) in self.t_db:
                for t in self.t_db[str(y)]:
                    t['dt_obj'] = datetime.strptime(t['datetime'], "%Y-%m-%dT%H:%M")
                    year_terms.append(t)
        year_terms.sort(key=lambda x: x['dt_obj'])
        m_terms = [t for t in year_terms if t['isMonthChange']]
        l_term = next((t for t in reversed(m_terms) if t['dt_obj'] <= dt_in), m_terms[0])
        n_term = next((t for t in m_terms if t['dt_obj'] > dt_in), m_terms[-1])
        return l_term, n_term

    def _apply_solar_correction(self, dt_in, yG, mG):
        """[Priority 1] 절기 시각 정밀 교정 (유지)"""
        today_str = dt_in.strftime("%Y%m%d")
        year_str = str(dt_in.year)
        term_today = next((t for t in self.t_db.get(year_str, []) 
                          if t['date'] == today_str and t['isMonthChange']), None)
        if term_today:
            term_dt = datetime.strptime(term_today['datetime'], "%Y-%m-%dT%H:%M")
            if dt_in < term_dt:
                mG = self.SIXTY_GANZI[(self.SIXTY_GANZI.index(mG) - 1) % 60]
                if term_today['monthIndex'] == 1:
                    yG = self.SIXTY_GANZI[(self.SIXTY_GANZI.index(yG) - 1) % 60]
        return yG, mG

    def _calculate_power(self, palja, me_hj):
        """[가중치 기반 신강약] (유지)"""
        scores = {'목': 0.0, '화': 0.0, '토': 0.0, '금': 0.0, '수': 0.0}
        power = 0
        target_indices = [(0, 11), (1, 11), (2, 11), (3, 30), (5, 15), (6, 11), (7, 11)] 
        for char in palja:
            scores[sc.ELEMENT_MAP[char]] += 12.5
        for idx, weight in target_indices:
            char = palja[idx]
            rel = sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[char]))
            if rel in ['비겁', '인성']:
                power += weight
        return scores, power

    def _investigate_sinsal(self, palja, me, me_hj):
        """[Priority 6] 신살/길성 전수 조사 확장 버전"""
        # 1. 12신살 기준점 (년지 기준 & 일지 기준)
        year_ji = palja[1]
        day_ji = palja[5]
        
        # 삼합 시작 글자 찾기 (년지 기준/일지 기준)
        start_idx_year = sc.BRANCHES.find(sc.SAMHAP_START_MAP[year_ji])
        start_idx_day = sc.BRANCHES.find(sc.SAMHAP_START_MAP[day_ji])

        # 2. 공망(空亡) 계산 (일주 기준)
        # 일주가 60갑자 중 몇 번째인지 찾아 공망 지지 2개를 가져옴
        ilju_name = palja[4] + palja[5]
        ilju_idx = self.SIXTY_GANZI.index(ilju_name)
        gongmang_jis = sc.GONGMANG_MAP[ilju_idx // 10] # 갑자순~갑인순 매핑

        pillars = []
        for i in range(4):
            g, j = palja[i*2], palja[i*2+1]
            special = []

            # --- [A] 12신살 (년지 vs 일지 통합) ---
            off_y = (sc.BRANCHES.find(j) - start_idx_year) % 12
            off_d = (sc.BRANCHES.find(j) - start_idx_day) % 12
            s12_y = sc.SINSAL_12_NAMES[off_y]
            s12_d = sc.SINSAL_12_NAMES[off_d]
            
            # 년지 기준 신살은 기본 포함
            special.append(s12_y)
            # 일지 기준 신살이 다를 경우 추가 (예: 도화살(일))
            if s12_d != s12_y:
                special.append(f"{s12_d}(일)")

            # --- [B] 공망(空亡) 체크 ---
            if j in gongmang_jis:
                special.append("공망(空亡)")

            # --- [C] 특수 강성 신살 (괴강, 양인, 백호) ---
            if (g+j) in ["戊戌", "庚戌", "庚辰", "壬辰", "壬戌"]:
                special.append("괴강살")
            
            # 양인살 (일간 기준 강한 칼날)
            yangin_map = {"甲":"卯", "丙":"午", "戊":"午", "庚":"酉", "壬":"子"}
            if j == yangin_map.get(me):
                special.append("양인살")

            # --- [D] 기존 길성 및 귀인 ---
            if g in sc.HYEONCHIM_CHARS or j in sc.HYEONCHIM_CHARS: special.append("현침살")
            if (g+j) in sc.BAEKHO_LIST: special.append("백호대살")
            if j in sc.TAEGEUK_MAP.get(me, []): special.append("태극귀인")
            if j == sc.HAKGWAN_MAP.get(me): special.append("관귀학관")
            if j == sc.HONGYEOM_MAP.get(me): special.append("홍염살")
            if j == sc.JEONGROK_MAP.get(me): special.append("정록(록신)")
            if j in sc.CHEONEUL_MAP.get(me, []): special.append("천을귀인")
            
            # 귀문관살 (예민함, 천재성)
            gwimun_map = {"子":"未", "丑":"午", "寅":"未", "卯":"申", "辰":"亥", "巳":"戌", "午":"丑", "未":"寅", "申":"卯", "酉":"寅", "戌":"巳", "亥":"辰"}
            if j == gwimun_map.get(palja[5]): # 일지와 대조
                special.append("귀문관살")

            # --- [E] 십성(Ten Gods) 계산 ---
            t_gan = "본인" if i==2 else sc.TEN_GODS_MAP.get((sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[g])), sc.POLARITY_MAP[me]==sc.POLARITY_MAP[g]), "-")
            t_ji = sc.TEN_GODS_MAP.get((sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[j])), sc.POLARITY_MAP[me]==sc.POLARITY_MAP[j]), "-")
            
            pillars.append({
                "gan": g, "ji": j, "t_gan": t_gan, "t_ji": t_ji, 
                "sinsal_12": s12_y, 
                "special": sorted(list(set(special)))
            })
        return pillars

    def _calculate_daeun(self, dt_in, yG, mG, gender, l_term, n_term):
        """[대운수 및 경로 계산] (유지)"""
        is_fwd = (gender == 'M' and sc.POLARITY_MAP[yG[0]] == '+') or (gender == 'F' and sc.POLARITY_MAP[yG[0]] == '-')
        target_term = n_term if is_fwd else l_term
        daeun_num = int(round(abs((target_term['dt_obj'] - dt_in).total_seconds() / 86400) / 3.0))
        if daeun_num == 0: daeun_num = 1
        daeun_list = []
        curr_idx = self.SIXTY_GANZI.index(mG)
        for i in range(1, 12):
            curr_idx = (curr_idx + 1) % 60 if is_fwd else (curr_idx - 1) % 60
            daeun_list.append({"start_age": daeun_num + (i-1)*10, "ganzi": self.SIXTY_GANZI[curr_idx]})
        return daeun_num, daeun_list

    def _get_detailed_status(self, power):
        """
        [Priority 5 추가] 신강약 8단계 세분화 로직
        - power 점수(0~100)를 기반으로 명리학적 상태 반환
        """
        if power <= 15: return "극약(極弱)"
        elif power <= 30: return "태약(太弱)"
        elif power <= 43: return "신약(身弱)"
        elif power <= 49: return "중화신약(中和身弱)"
        elif power <= 56: return "중화신강(中和身强)"
        elif power <= 70: return "신강(身强)"
        elif power <= 85: return "태강(太强)"
        else: return "극왕(極旺)"

    def _get_yongsin_info(self, palja, power, me_hj_hanja):
        """
        [v1.5.3 최종] 한자 기반 정밀 연산 로직
        me_hj_hanja: '木', '火' 등 한자 오행이 들어와야 함
        """
        if power <= 49:
            eokbu_type = "인성/비겁"
            targets = ['인성', '비겁']
        else:
            eokbu_type = "식상/재성/관성"
            targets = ['식상', '재성', '관성']
            
        hj_elements = ['木', '火', '土', '金', '水']
        hj_to_hg = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
        
        found_elements = []
        for target_hj in hj_elements:
            rel = sc.REL_MAP.get((me_hj_hanja, target_hj))
            if rel and rel in targets:
                found_elements.append(hj_to_hg[target_hj])
        
        if not found_elements:
            print(f"⚠️ 경고: 용신 추출 실패 (입력값: {me_hj_hanja}, 타입: {eokbu_type})")
            found_elements = ["데이터 확인 필요"]
        
        month_branch = palja[3]
        johoo_yongsin = "필요 없음 (중화)"
        if month_branch in ['亥', '子', '丑']: johoo_yongsin = "화(火) - 추운 계절이라 따뜻한 기운이 최우선입니다."
        elif month_branch in ['巳', '午', '未']: johoo_yongsin = "수(水) - 더운 계절이라 시원한 기운이 최우선입니다."
        elif month_branch in ['寅', '卯', '辰']: johoo_yongsin = "화(火) - 만물이 성장하도록 온기가 필요합니다."
        elif month_branch in ['申', '酉', '戌']: johoo_yongsin = "수(水) - 건조한 계절이라 적절한 수기가 필요합니다."

        return {
            "eokbu_elements": "/".join(found_elements),
            "eokbu_type": eokbu_type,
            "johoo": johoo_yongsin
        }

    def _calculate_daeun_scores(self, daeun_list, yongsin_info, palja):
        """[기존 로직 유지]"""
        yong_elements = yongsin_info['eokbu_elements'].split('/')
        sangsaeng = {'목':'화', '화':'토', '토':'금', '금':'수', '수':'목'}
        huising = [sangsaeng.get(y) for y in yong_elements if y in sangsaeng]
        
        stem_hab = {'甲':'己', '己':'甲', '乙':'庚', '庚':'乙', '丙':'辛', '辛':'丙', '丁':'壬', '壬':'丁', '戊':'癸', '癸':'戊'}
        stem_chung = {'甲':'庚', '庚':'甲', '乙':'辛', '辛':'乙', '丙':'壬', '壬':'丙', '丁':'癸', '癸':'丁'}
        branch_hab = {'子':'丑', '丑':'子', '寅':'亥', '亥':'寅', '卯':'戌', '戌':'卯', '辰':'酉', '酉':'辰', '巳':'申', '申':'巳', '午':'未', '未':'午'}
        branch_chung = {'子':'午', '午':'子', '丑':'未', '未':'丑', '寅':'申', '申':'寅', '卯':'酉', '酉':'卯', '辰':'戌', '戌':'辰', '巳':'亥', '亥':'巳'}

        natal_stems = [palja[0], palja[2], palja[4], palja[6]]
        natal_branches = [palja[1], palja[3], palja[5], palja[7]]

        for d in daeun_list:
            d_gan, d_ji = d['ganzi'][0], d['ganzi'][1]
            gan_hj, ji_hj = sc.ELEMENT_MAP.get(d_gan), sc.ELEMENT_MAP.get(d_ji)
            score = 50 
            if gan_hj in yong_elements: score += 15
            elif gan_hj in huising: score += 7
            elif gan_hj in ['목', '화', '토', '금', '수']: score -= 10 
            if ji_hj in yong_elements: score += 35
            elif ji_hj in huising: score += 18
            else: score -= 20 
            is_ji_good = (ji_hj in yong_elements or ji_hj in huising)
            interaction_offset = 0
            for n_gan in natal_stems:
                if stem_hab.get(d_gan) == n_gan: interaction_offset += 5
                if stem_chung.get(d_gan) == n_gan:
                    penalty = 7
                    if is_ji_good: penalty = 1 
                    interaction_offset -= penalty
            for n_ji in natal_branches:
                if branch_hab.get(d_ji) == n_ji: interaction_offset += 8
                if branch_chung.get(d_ji) == n_ji:
                    penalty = 12
                    if is_ji_good: penalty = 3
                    interaction_offset -= penalty
            d['score'] = max(0, min(100, int(score + interaction_offset)))
        return daeun_list

    # --------------------------------------------------------------------------
    # [NEW Task 3] 재물운 및 커리어 성공 지수 분석 (Phase 1 완성)
    # --------------------------------------------------------------------------
    def _analyze_wealth_and_career(self, pillars, power, yongsin_elements):
        """재물/커리어 점수 산출 및 등급화"""
        # 1. 십성 데이터 수집
        all_ten_gods = []
        all_specials = []
        for p in pillars:
            all_ten_gods.extend([p['t_gan'], p['t_ji']])
            all_specials.extend(p['special'])
        
        # 2. 재물운(Wealth) 분석
        wealth_score = 40  # 기본 점수
        j_count = all_ten_gods.count('정재') + all_ten_gods.count('편재')
        s_count = all_ten_gods.count('식신') + all_ten_gods.count('상관')
        
        # 재성이 있고 신강할 때 (득재 가능성)
        if power >= 50: wealth_score += (j_count * 8)
        else: wealth_score += (j_count * 4) # 신약할 경우 재다신약 우려
            
        # 식상생재 구조 (식상이 재성을 생함)
        if s_count > 0 and j_count > 0: wealth_score += 15
        
        # 신강약 보정
        if 40 <= power <= 65: wealth_score += 10 # 중화권 보너스
        elif power < 30 and j_count >= 3: wealth_score -= 15 # 재다신약 감점

        # 3. 커리어(Career) 분석
        career_score = 40 # 기본 점수
        g_count = all_ten_gods.count('정관') + all_ten_gods.count('편관')
        i_count = all_ten_gods.count('정인') + all_ten_gods.count('편인')
        
        career_score += (g_count * 10)
        # 관인상생 (관성과 인성이 함께 있음)
        if g_count > 0 and i_count > 0: career_score += 15
        
        # 4. 신살/귀인 가산점
        if "천을귀인" in all_specials: wealth_score += 5; career_score += 5
        if "관귀학관" in all_specials: career_score += 10
        if "태극귀인" in all_specials: wealth_score += 5
        if "백호대살" in all_specials: career_score += 5 # 추진력

        # 등급 결정
        def get_grade(s):
            if s >= 85: return "S (최상)"
            elif s >= 70: return "A (우수)"
            elif s >= 55: return "B (보통)"
            else: return "C (관리필요)"

        return {
            "wealth_score": min(100, wealth_score),
            "career_score": min(100, career_score),
            "wealth_grade": get_grade(wealth_score),
            "career_grade": get_grade(career_score)
        }
    # --------------------------------------------------------------------------
    # [NEW Task] 사주 원국 내 11가지 상호작용 분석 (합, 충, 형, 파, 해, 원진, 공망)
    # --------------------------------------------------------------------------
    def _analyze_interactions(self, palja):
        """
        [v2.2] 11가지 관계 분석 및 한글화 출력 엔진 (ValueError 수정 버전)
        """
        # 지지 한자 -> 한글 변환 맵
        B_HAN_TO_KOR = {
            '子': '자', '丑': '축', '寅': '인', '卯': '묘', '辰': '진', '巳': '사',
            '午': '오', '未': '미', '申': '신', '酉': '유', '戌': '술', '亥': '해'
        }

        # 1. 기초 데이터 정의
        STEM_HAB = {"甲己": "갑기합", "乙庚": "을경합", "丙辛": "병신합", "丁壬": "정임합", "戊癸": "무계합"}
        STEM_CHUNG = {"甲庚": "갑경충", "乙辛": "을신충", "丙壬": "병임충", "丁癸": "정계충"}
        B_HAB_6 = {"子丑": "자축육합", "寅亥": "인해육합", "卯戌": "묘술육합", "辰酉": "진유육합", "巳申": "사신육합", "午未": "오미육합"}
        
        # [수정] 모든 튜플의 개수를 (명칭, 왕지) 2개로 통일했습니다.
        B_SAMHAP = {
            "亥卯未": ("목국", "卯"), 
            "寅午戌": ("화국", "午"), 
            "巳酉丑": ("금국", "酉"), 
            "申子辰": ("수국", "子")
        }
        
        B_BANGHAP = {"寅卯辰": "목국(방합)", "巳午未": "화국(방합)", "申酉戌": "금국(방합)", "亥子丑": "수국(방합)"}
        B_CHUNG = {"子午": "자오충", "丑未": "축미충", "寅申": "인신충", "卯酉": "묘유충", "辰戌": "진술충", "巳亥": "사해충"}
        B_HYUNG = {"寅巳": "인사형", "巳申": "사신형", "申寅": "신인형", "丑戌": "축술형", "戌未": "술미형", "未丑": "미축형", 
                   "子卯": "자묘형", "辰辰": "진진자형", "午午": "오오자형", "酉酉": "유유자형", "亥亥": "해해자형"}
        B_PA = {"子酉": "자유파", "卯午": "묘오파", "辰丑": "진축파", "未戌": "미술파", "寅亥": "인해파", "巳申": "사신파"}
        B_HAE = {"子未": "자미해", "丑午": "축오해", "寅巳": "인사해", "卯辰": "묘진해", "申亥": "신해해", "酉戌": "유술해"}
        B_WONJIN = {"子未": "자미원진", "丑午": "축오원진", "寅酉": "인유원진", "卯申": "묘신원진", "辰亥": "진해원진", "巳戌": "사술원진"}

        results = {
            "천간합": [], "천간충": [], "지지육합": [], "지지삼합": [], 
            "지지방합": [], "지지충": [], "형": [], "파": [], 
            "해": [], "원진": [], "공망": []
        }

        s_list = [palja[0], palja[2], palja[4], palja[6]]
        b_list = [palja[1], palja[3], palja[5], palja[7]]
        
        # 2. 천간 관계
        for i in range(4):
            for j in range(i + 1, 4):
                pair = "".join(sorted([s_list[i], s_list[j]]))
                if pair in STEM_HAB: results["천간합"].append(STEM_HAB[pair])
                if pair in STEM_CHUNG: results["천간충"].append(STEM_CHUNG[pair])
        
        # 3. 지지 2글자 관계
        for i in range(4):
            for j in range(i + 1, 4):
                pair = "".join(sorted([b_list[i], b_list[j]]))
                if pair in B_HAB_6: results["지지육합"].append(B_HAB_6[pair])
                if pair in B_CHUNG: results["지지충"].append(B_CHUNG[pair])
                if pair in B_HYUNG: results["형"].append(B_HYUNG[pair])
                if pair in B_PA: results["파"].append(B_PA[pair])
                if pair in B_HAE: results["해"].append(B_HAE[pair])
                if pair in B_WONJIN: results["원진"].append(B_WONJIN[pair])
        
        # 4. 삼합 및 방합 (반합 로직)
        for key, (val, king) in B_SAMHAP.items():
            match_chars = [c for c in key if c in b_list]
            if len(set(match_chars)) >= 3:
                results["지지삼합"].append(f"{val} 삼합({key})")
            elif len(set(match_chars)) == 2 and king in b_list:
                kor_pair = "".join([B_HAN_TO_KOR[c] for c in key if c in b_list])
                results["지지삼합"].append(f"{kor_pair} 반합({val})")

        for key, val in B_BANGHAP.items():
            match_chars = [c for c in key if c in b_list]
            if len(set(match_chars)) >= 3:
                results["지지방합"].append(f"{val}")
            elif len(set(match_chars)) == 2:
                kor_pair = "".join([B_HAN_TO_KOR[c] for c in key if c in b_list])
                results["지지방합"].append(f"{kor_pair} 반합")

        # 5. 공망
        ilju_idx = self.SIXTY_GANZI.index(palja[4] + palja[5])
        gongmang_jis = sc.GONGMANG_MAP[ilju_idx // 10]
        for i, b_char in enumerate(b_list):
            if b_char in gongmang_jis:
                pos = ["년지", "월지", "일지", "시지"][i]
                results["공망"].append(f"{pos} 공망({B_HAN_TO_KOR.get(b_char, b_char)})")

        for k in results:
            results[k] = sorted(list(set(results[k])))

        return results

    def analyze(self, birth_str, gender, location, use_yajas_i, calendar_type="양력"):
        """
        메인 분석 오케스트레이터 (v2.4 전국 시·군 정밀 보정 버전)
        - sc.CITY_DATA의 전체 키값과 1:1 매칭하여 정밀한 지역 보정을 수행합니다.
        """
        # 1. 입력 시각 파싱
        # 1. 입력 시각 파싱
        dt_input = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        input_time = dt_input.strftime("%H:%M")
       
        # 2. 음력 또는 음력(윤달)일 경우 양력 날짜 역산
        if calendar_type in ["음력", "음력(윤달)"]:
            i_y, i_m, i_d = dt_input.year, dt_input.month, dt_input.day
            
            # 🔥 "음력(윤달)" 문자열이 들어오면 윤달(ls=True)로 검색
            is_leap_input = (calendar_type == "음력(윤달)")
            
            found_solar_key = None
            for s_key, data in self.m_db.items():
                if (data.get('ly') == i_y and 
                    data.get('lm') == i_m and 
                    data.get('ld') == i_d and 
                    data.get('ls') == is_leap_input):
                    found_solar_key = s_key
                    break
            
            if not found_solar_key:
                # 에러 메시지도 사용자 선택 값에 맞춰 출력
                return {"error": f"입력하신 {calendar_type} 날짜({i_y}/{i_m}/{i_d})를 찾을 수 없습니다."}
            
            # 찾은 양력 날짜로 분석용 birth_str 재조립
            birth_str = f"{found_solar_key[:4]}-{found_solar_key[4:6]}-{found_solar_key[6:]} {input_time}"
            dt_raw = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        else:
            # "양력"이거나 값이 없을 경우 (디폴트)
            dt_raw = dt_input
        
        # 2. 전국 시·군 정밀 경도 매칭 (Exact Match)
        # 이제 [:2]를 하지 않고 사용자가 선택한 전체 명칭(예: "경기도 수원시")을 직접 찾습니다.
        target_lng = sc.CITY_DATA.get(location, 126.97) # 매칭 실패 시 서울 기본값
        
        # [정밀 연산] 실제 물리적 시차 계산 (소수점 유지)
        lng_offset_exact = (target_lng - 135) * 4
        # [UI용] 화면 표시를 위한 반올림 정수 시차 (-32, -24 등)
        lng_offset_display = int(round(lng_offset_exact))
        
        # 3. 시간 보정 연산 (역사적 표준시 + 균시차 + 정밀 지역 오프셋)
        hist_offset = self._get_historical_correction(dt_raw)
        dt_ref = dt_raw + timedelta(minutes=hist_offset)
        #eot_offset = self._get_equation_of_time(dt_ref)
        
        # 엔진 연산은 초 단위까지 정확한 dt_true_solar를 사용합니다.
        #dt_true_solar = dt_ref + timedelta(minutes=lng_offset_exact)
        dt_true_solar = dt_ref + timedelta(minutes=lng_offset_display)
        
        # 4. 분석 수행 (야자시/조자시 및 절기 보정)
        jasi_type = self._get_jasi_type(dt_true_solar)
        fetch_dt = dt_true_solar
        if not use_yajas_i and jasi_type == "YAJAS-I":
            fetch_dt = dt_true_solar + timedelta(hours=2)
            
        day_key = fetch_dt.strftime("%Y%m%d")
        day_data = self.m_db.get(day_key)
        if not day_data: return {"error": f"Data not found for {day_key}"}
        
        # --- [음력 데이터 처리: ly, lm, ld, ls 반영] ---
        ly, lm, ld = day_data.get('ly'), day_data.get('lm'), day_data.get('ld')
        ls = day_data.get('ls', False) 
        birth_time_str = dt_raw.strftime("%H:%M")
        
        if ly and lm and ld:
            lunar_display = f"{ly}/{lm:02d}/{ld:02d} {birth_time_str}"
            lunar_type = "윤" if ls else "평"
        else:
            lunar_display = "정보 없음"
            lunar_type = "평"
        # ----------------------------------------------

        yG, mG, dG = day_data['yG'], day_data['mG'], day_data['dG']
        yG, mG = self._apply_solar_correction(dt_raw, yG, mG)
        
        me = dG[0]
        me_hj_hanja = sc.E_MAP_HJ.get(me)
        
        # 시주(時柱) 연산
        h_idx = ((dt_true_solar.hour * 60 + dt_true_solar.minute + 60) // 120) % 12
        target_dG_for_hour = dG
        if use_yajas_i and jasi_type == "YAJAS-I":
            next_day_key = (dt_true_solar + timedelta(hours=2)).strftime("%Y%m%d")
            next_day_data = self.m_db.get(next_day_key)
            if next_day_data: target_dG_for_hour = next_day_data['dG']
        
        hG_gan = sc.STEMS[({ '甲':0,'己':0,'乙':2,'庚':2,'丙':4,'辛':4,'丁':6,'壬':6,'戊':8,'癸':8 }[target_dG_for_hour[0]] + h_idx) % 10]
        hG = hG_gan + sc.BRANCHES[h_idx]
        
        palja = [yG[0], yG[1], mG[0], mG[1], dG[0], dG[1], hG[0], hG[1]]
        
        # 5. 각종 분석 수행
        scores, power = self._calculate_power(palja, me_hj_hanja)
        detailed_status = self._get_detailed_status(power)
        yongsin_info = self._get_yongsin_info(palja, power, me_hj_hanja)
        pillars = self._investigate_sinsal(palja, me, me_hj_hanja)
        
        for p in pillars:
            p['gan_elem'] = sc.ELEMENT_MAP.get(p['gan'])
            p['ji_elem'] = sc.ELEMENT_MAP.get(p['ji'])
            
        l_term, n_term = self._get_solar_terms(dt_raw)
        daeun_num, daeun_list = self._calculate_daeun(dt_raw, yG, mG, gender, l_term, n_term)
        daeun_list = self._calculate_daeun_scores(daeun_list, yongsin_info, palja)
        
        # 6. 현재 운의 흐름 (current_trace)
        now = datetime.now()
        current_age = now.year - dt_raw.year + 1
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), 
            "age": current_age,
            "daeun": next((d for d in daeun_list if d['start_age'] <= current_age < d['start_age'] + 10), daeun_list[0]),
            "seun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('yG', 'N/A'),
            "wolun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('mG', 'N/A'),
            "ilun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('dG', 'N/A')
        }

        wealth_career = self._analyze_wealth_and_career(pillars, power, yongsin_info['eokbu_elements'])
        interactions = self._analyze_interactions(palja)
        
        display_tags = []
        for v in interactions.values(): display_tags.extend(v)

        # 7. 최종 데이터 반환
        return {
            "solar_display": dt_raw.strftime("%Y/%m/%d %H:%M"),
            "calendar_type" : calendar_type,
            "corrected_display": dt_true_solar.strftime("%Y/%m/%d %H:%M"),
            "lunar_display": lunar_display,
            "lunar_type": lunar_type,
            "lng_diff_str": f"{lng_offset_display}분" if lng_offset_display < 0 else f"+{lng_offset_display}분",
            "gender_str": "여자" if gender == "F" else "남자",
            "location_name": location, # 사용자가 선택한 전체 지역명 그대로 반환
            "display_tags": display_tags[:8],
            "birth": birth_str, 
            "gender": gender, 
            "pillars": pillars, 
            "ilju": pillars[2]['gan'] + pillars[2]['ji'],
            "me": me, 
            "me_elem": sc.ELEMENT_MAP[me],
            "scores": scores, 
            "power": power, 
            "status": detailed_status,
            "yongsin_detail": yongsin_info,
            "wealth_analysis": wealth_career,
            "daeun_num": daeun_num, 
            "daeun_list": daeun_list,
            "current_trace": current_trace,
            "interactions": interactions,
            "jasi_type": jasi_type
        }