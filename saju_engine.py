import json
import math
from datetime import datetime, timedelta
import saju_constants as sc

class SajuEngine:
    def __init__(self, m_file, t_file):
        with open(m_file, 'r', encoding='utf-8') as f: self.m_db = json.load(f)
        with open(t_file, 'r', encoding='utf-8') as f: self.t_db = json.load(f)
        self.SIXTY_GANZI = [f"{sc.STEMS[i%10]}{sc.BRANCHES[i%12]}" for i in range(60)]

    # ==========================================================================
    # 1. 시간 및 력법 관련 유틸리티 (Calendar & Time Utils)
    # ==========================================================================
    def _parse_and_convert_to_solar(self, birth_str, calendar_type):
        """입력된 날짜를 파싱하고, 음력/윤달일 경우 양력으로 역산합니다."""
        dt_input = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        
        if calendar_type in ["음력", "음력(윤달)"]:
            i_y, i_m, i_d = dt_input.year, dt_input.month, dt_input.day
            is_leap = (calendar_type == "음력(윤달)")
            
            for s_key, data in self.m_db.items():
                if (data.get('ly') == i_y and data.get('lm') == i_m and 
                    data.get('ld') == i_d and data.get('ls') == is_leap):
                    solar_str = f"{s_key[:4]}-{s_key[4:6]}-{s_key[6:]} {dt_input.strftime('%H:%M')}"
                    return datetime.strptime(solar_str, "%Y-%m-%d %H:%M"), True
            return None, False # 데이터를 찾지 못함
        
        return dt_input, True

    def _get_historical_correction(self, dt):
        """역사적 표준시 및 서머타임 보정"""
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
        """균시차(Equation of Time) 계산"""
        day_of_year = dt.timetuple().tm_yday
        b = math.radians((360 / 365.25) * (day_of_year - 81))
        return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    def _get_jasi_type(self, dt):
        """자시 구간 판정 (야자시/조자시)"""
        if dt.hour == 23: return "YAJAS-I"
        if dt.hour == 0: return "JOJAS-I"
        return "NORMAL"

    def _get_solar_terms(self, dt_in):
        """절기 정보 조회"""
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
        """절기 경계 시각 보정 (연/월주 교체)"""
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

    # ==========================================================================
    # 2. 사주 핵심 분석 로직 (Core Saju Calculation)
    # ==========================================================================
    def _calculate_power(self, palja, me_hj):
        """신강약 점수 계산"""
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

    def _get_detailed_status(self, power):
        """신강약 8단계 세분화"""
        if power <= 15: return "극약(極弱)"
        elif power <= 30: return "태약(太弱)"
        elif power <= 43: return "신약(身弱)"
        elif power <= 49: return "중화신약(中和身弱)"
        elif power <= 56: return "중화신강(中和身强)"
        elif power <= 70: return "신강(身强)"
        elif power <= 85: return "태강(太强)"
        else: return "극왕(極旺)"

    def _get_yongsin_info(self, palja, power, me_hj_hanja):
        """용신(억부/조후) 분석"""
        targets = ['인성', '비겁'] if power <= 49 else ['식상', '재성', '관성']
        eokbu_type = "인성/비겁" if power <= 49 else "식상/재성/관성"
        
        hj_elements = ['木', '火', '土', '金', '水']
        hj_to_hg = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
        found_elements = [hj_to_hg[hj] for hj in hj_elements if sc.REL_MAP.get((me_hj_hanja, hj)) in targets]
        
        month_branch = palja[3]
        johoo_yongsin = "필요 없음 (중화)"
        if month_branch in ['亥', '子', '丑']: johoo_yongsin = "화(火) - 추운 계절이라 따뜻한 기운이 최우선입니다."
        elif month_branch in ['巳', '午', '未']: johoo_yongsin = "수(水) - 더운 계절이라 시원한 기운이 최우선입니다."
        elif month_branch in ['寅', '卯', '辰']: johoo_yongsin = "화(火) - 만물이 성장하도록 온기가 필요합니다."
        elif month_branch in ['申', '酉', '戌']: johoo_yongsin = "수(水) - 건조한 계절이라 적절한 수기가 필요합니다."

        return {"eokbu_elements": "/".join(found_elements or ["데이터 확인 필요"]), "eokbu_type": eokbu_type, "johoo": johoo_yongsin}

    def _investigate_sinsal(self, palja, me, me_hj):
        """신살, 길성, 십성 전수 조사"""
        year_ji, day_ji = palja[1], palja[5]
        start_idx_year = sc.BRANCHES.find(sc.SAMHAP_START_MAP[year_ji])
        start_idx_day = sc.BRANCHES.find(sc.SAMHAP_START_MAP[day_ji])
        ilju_idx = self.SIXTY_GANZI.index(palja[4] + palja[5])
        gongmang_jis = sc.GONGMANG_MAP[ilju_idx // 10]

        pillars = []
        for i in range(4):
            g, j = palja[i*2], palja[i*2+1]
            special = []
            # 12신살
            off_y, off_d = (sc.BRANCHES.find(j)-start_idx_year)%12, (sc.BRANCHES.find(j)-start_idx_day)%12
            s12_y, s12_d = sc.SINSAL_12_NAMES[off_y], sc.SINSAL_12_NAMES[off_d]
            special.append(s12_y)
            if s12_d != s12_y: special.append(f"{s12_d}(일)")
            
            # 기타 신살/귀인
            if j in gongmang_jis: special.append("공망(空亡)")
            if (g+j) in ["戊戌", "庚戌", "庚辰", "壬辰", "壬戌"]: special.append("괴강살")
            yangin_map = {"甲":"卯", "丙":"午", "戊":"午", "庚":"酉", "壬":"子"}
            if j == yangin_map.get(me): special.append("양인살")
            if g in sc.HYEONCHIM_CHARS or j in sc.HYEONCHIM_CHARS: special.append("현침살")
            if (g+j) in sc.BAEKHO_LIST: special.append("백호대살")
            if j in sc.TAEGEUK_MAP.get(me, []): special.append("태극귀인")
            if j == sc.HAKGWAN_MAP.get(me): special.append("관귀학관")
            if j == sc.HONGYEOM_MAP.get(me): special.append("홍염살")
            if j == sc.JEONGROK_MAP.get(me): special.append("정록(록신)")
            if j in sc.CHEONEUL_MAP.get(me, []): special.append("천을귀인")
            gwimun_map = {"子":"未", "丑":"午", "寅":"未", "卯":"申", "辰":"亥", "巳":"戌", "午":"丑", "未":"寅", "申":"卯", "酉":"寅", "戌":"巳", "亥":"辰"}
            if j == gwimun_map.get(palja[5]): special.append("귀문관살")

            # 십성(Ten Gods)
            t_gan = "본인" if i==2 else sc.TEN_GODS_MAP.get((sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[g])), sc.POLARITY_MAP[me]==sc.POLARITY_MAP[g]), "-")
            t_ji = sc.TEN_GODS_MAP.get((sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[j])), sc.POLARITY_MAP[me]==sc.POLARITY_MAP[j]), "-")
            
            pillars.append({"gan": g, "ji": j, "t_gan": t_gan, "t_ji": t_ji, "sinsal_12": s12_y, "special": sorted(list(set(special)))})
        return pillars

    # ==========================================================================
    # 3. 대운 및 환경 분석 (Luck & Environment Analysis)
    # ==========================================================================
    def _calculate_daeun(self, dt_in, yG, mG, gender, l_term, n_term):
        """대운수 및 경로 계산"""
        is_fwd = (gender == 'M' and sc.POLARITY_MAP[yG[0]] == '+') or (gender == 'F' and sc.POLARITY_MAP[yG[0]] == '-')
        target_term = n_term if is_fwd else l_term
        daeun_num = max(1, int(round(abs((target_term['dt_obj'] - dt_in).total_seconds() / 86400) / 3.0)))
        daeun_list = []
        curr_idx = self.SIXTY_GANZI.index(mG)
        for i in range(1, 12):
            curr_idx = (curr_idx + 1) % 60 if is_fwd else (curr_idx - 1) % 60
            daeun_list.append({"start_age": daeun_num + (i-1)*10, "ganzi": self.SIXTY_GANZI[curr_idx]})
        return daeun_num, daeun_list

    def _calculate_daeun_scores(self, daeun_list, yongsin_info, palja):
        """대운 점수 산출"""
        yong_elements = yongsin_info['eokbu_elements'].split('/')
        sangsaeng = {'목':'화', '화':'토', '토':'금', '금':'수', '수':'목'}
        huising = [sangsaeng.get(y) for y in yong_elements if y in sangsaeng]
        stem_hab = {'甲':'己', '己':'甲', '乙':'庚', '庚':'乙', '丙':'辛', '辛':'丙', '丁':'壬', '壬':'丁', '戊':'癸', '癸':'戊'}
        stem_chung = {'甲':'庚', '庚':'甲', '乙':'辛', '辛':'乙', '丙':'壬', '壬':'丙', '丁':'癸', '癸':'丁'}
        branch_hab = {'子':'丑', '丑':'子', '寅':'亥', '亥':'寅', '卯':'戌', '戌':'卯', '辰':'酉', '酉':'辰', '巳':'申', '申':'巳', '午':'未', '未':'午'}
        branch_chung = {'子':'午', '午':'子', '丑':'未', '未':'丑', '寅':'申', '申':'寅', '卯':'酉', '酉':'卯', '辰':'戌', '戌':'辰', '巳':'亥', '亥':'巳'}
        natal_stems, natal_branches = [palja[0], palja[2], palja[4], palja[6]], [palja[1], palja[3], palja[5], palja[7]]

        for d in daeun_list:
            d_gan, d_ji = d['ganzi'][0], d['ganzi'][1]
            gan_hj, ji_hj = sc.ELEMENT_MAP.get(d_gan), sc.ELEMENT_MAP.get(d_ji)
            score = 50 
            if gan_hj in yong_elements: score += 15
            elif gan_hj in huising: score += 7
            else: score -= 10
            if ji_hj in yong_elements: score += 35
            elif ji_hj in huising: score += 18
            else: score -= 20 
            is_ji_good, interaction_offset = (ji_hj in yong_elements or ji_hj in huising), 0
            for n_gan in natal_stems:
                if stem_hab.get(d_gan) == n_gan: interaction_offset += 5
                if stem_chung.get(d_gan) == n_gan: interaction_offset -= (1 if is_ji_good else 7)
            for n_ji in natal_branches:
                if branch_hab.get(d_ji) == n_ji: interaction_offset += 8
                if branch_chung.get(d_ji) == n_ji: interaction_offset -= (3 if is_ji_good else 12)
            d['score'] = max(0, min(100, int(score + interaction_offset)))
        return daeun_list

    def _analyze_wealth_and_career(self, pillars, power, yongsin_elements):
        """재물 및 커리어 성공 지수 분석"""
        all_ten_gods, all_specials = [], []
        for p in pillars:
            all_ten_gods.extend([p['t_gan'], p['t_ji']]); all_specials.extend(p['special'])
        
        wealth_score = 40 + (all_ten_gods.count('정재')+all_ten_gods.count('편재')) * (8 if power >= 50 else 4)
        if (all_ten_gods.count('식신')+all_ten_gods.count('상관')) > 0 and (all_ten_gods.count('정재')+all_ten_gods.count('편재')) > 0: wealth_score += 15
        if 40 <= power <= 65: wealth_score += 10
        elif power < 30 and (all_ten_gods.count('정재')+all_ten_gods.count('편재')) >= 3: wealth_score -= 15

        career_score = 40 + (all_ten_gods.count('정관')+all_ten_gods.count('편관')) * 10
        if (all_ten_gods.count('정관')+all_ten_gods.count('편관')) > 0 and (all_ten_gods.count('정인')+all_ten_gods.count('편인')) > 0: career_score += 15
        
        for s in ["천을귀인", "관귀학관", "태극귀인", "백호대살"]:
            if s in all_specials:
                if s == "관귀학관": career_score += 10
                elif s == "백호대살": career_score += 5
                else: wealth_score += 5; career_score += 5

        get_grade = lambda s: "S (최상)" if s >= 85 else "A (우수)" if s >= 70 else "B (보통)" if s >= 55 else "C (관리필요)"
        return {"wealth_score": min(100, wealth_score), "career_score": min(100, career_score), "wealth_grade": get_grade(wealth_score), "career_grade": get_grade(career_score)}

    def _analyze_interactions(self, palja):
        """원국 내 11가지 상호작용 분석"""
        B_KOR = {'子':'자','丑':'축','寅':'인','卯':'묘','辰':'진','巳':'사','午':'오','未':'미','申':'신','酉':'유','戌':'술','亥':'해'}
        STEM_HAB = {"甲己": "갑기합", "乙庚": "을경합", "丙辛": "병신합", "丁壬": "정임합", "戊癸": "무계합"}
        STEM_CHUNG = {"甲庚": "갑경충", "乙辛": "을신충", "丙壬": "병임충", "丁癸": "정계충"}
        B_HAB_6 = {"子丑": "자축육합", "寅亥": "인해육합", "卯戌": "묘술육합", "辰酉": "진유육합", "巳申": "사신육합", "午未": "오미육합"}
        B_SAMHAP = {"亥卯未": ("목국", "卯"), "寅午戌": ("화국", "午"), "巳酉丑": ("금국", "酉"), "申子辰": ("수국", "子")}
        B_BANGHAP = {"寅卯辰": "목국(방합)", "巳午未": "화국(방합)", "申酉戌": "금국(방합)", "亥子丑": "수국(방합)"}
        B_CHUNG = {"子午": "자오충", "丑未": "축미충", "寅申": "인신충", "卯酉": "묘유충", "辰戌": "진술충", "巳亥": "사해충"}
        B_HYUNG = {"寅巳": "인사형", "巳申": "사신형", "申寅": "신인형", "丑戌": "축술형", "戌未": "술미형", "未丑": "미축형", "子卯": "자묘형", "辰辰": "진진자형", "午午": "오오자형", "酉酉": "유유자형", "亥亥": "해해자형"}
        B_PA = {"子酉": "자유파", "卯午": "묘오파", "辰丑": "진축파", "未戌": "미술파", "寅亥": "인해파", "巳申": "사신파"}
        B_HAE = {"子未": "자미해", "丑午": "축오해", "寅巳": "인사해", "卯辰": "묘진해", "申亥": "신해해", "酉戌": "유술해"}
        B_WONJIN = {"子未": "자미원진", "丑午": "축오원진", "寅酉": "인유원진", "卯申": "묘신원진", "辰亥": "진해원진", "巳戌": "사술원진"}

        res = {k: [] for k in ["천간합", "천간충", "지지육합", "지지삼합", "지지방합", "지지충", "형", "파", "해", "원진", "공망"]}
        s_list, b_list = [palja[0], palja[2], palja[4], palja[6]], [palja[1], palja[3], palja[5], palja[7]]
        
        for i in range(4):
            for j in range(i+1, 4):
                ps, pb = "".join(sorted([s_list[i], s_list[j]])), "".join(sorted([b_list[i], b_list[j]]))
                if ps in STEM_HAB: res["천간합"].append(STEM_HAB[ps])
                if ps in STEM_CHUNG: res["천간충"].append(STEM_CHUNG[ps])
                if pb in B_HAB_6: res["지지육합"].append(B_HAB_6[pb])
                if pb in B_CHUNG: res["지지충"].append(B_CHUNG[pb])
                if pb in B_HYUNG: res["형"].append(B_HYUNG[pb])
                if pb in B_PA: res["파"].append(B_PA[pb])
                if pb in B_HAE: res["해"].append(B_HAE[pb])
                if pb in B_WONJIN: res["원진"].append(B_WONJIN[pb])

        for key, (val, king) in B_SAMHAP.items():
            match = [c for c in key if c in b_list]
            if len(set(match)) >= 3: res["지지삼합"].append(f"{val} 삼합({key})")
            elif len(set(match)) == 2 and king in b_list: res["지지삼합"].append(f"{''.join([B_KOR[c] for c in match])} 반합({val})")
        for key, val in B_BANGHAP.items():
            match = [c for c in key if c in b_list]
            if len(set(match)) >= 3: res["지지방합"].append(val)
            elif len(set(match)) == 2: res["지지방합"].append(f"{''.join([B_KOR[c] for c in match])} 반합")

        g_jis = sc.GONGMANG_MAP[self.SIXTY_GANZI.index(palja[4]+palja[5]) // 10]
        for i, b in enumerate(b_list):
            if b in g_jis: res["공망"].append(f"{['년지','월지','일지','시지'][i]} 공망({B_KOR.get(b, b)})")
        return {k: sorted(list(set(v))) for k, v in res.items()}

    # ==========================================================================
    # 4. 메인 분석 엔진 (Main Analysis Orchestrator)
    # ==========================================================================
    def analyze(self, birth_str, gender, location, use_yajas_i, calendar_type="양력"):
        # 1. 입력 전처리 및 양력 변환
        dt_raw, success = self._parse_and_convert_to_solar(birth_str, calendar_type)
        if not success: return {"error": f"입력 날짜({birth_str})를 찾을 수 없습니다."}
        
        # 2. 정밀 시간 보정 (지역 시차 - 반올림 적용)
        target_lng = sc.CITY_DATA.get(location, 126.97)
        lng_offset_display = int(round((target_lng - 135) * 4))
        dt_solar = dt_raw + timedelta(minutes=self._get_historical_correction(dt_raw) + lng_offset_display)
        
        # 3. 원국 생성 및 절기 보정
        jasi_type = self._get_jasi_type(dt_solar)
        fetch_dt = dt_solar + timedelta(hours=2) if (not use_yajas_i and jasi_type == "YAJAS-I") else dt_solar
        day_data = self.m_db.get(fetch_dt.strftime("%Y%m%d"))
        if not day_data: return {"error": "DB 데이터가 없습니다."}
        
        yG, mG = self._apply_solar_correction(dt_raw, day_data['yG'], day_data['mG'])
        dG = day_data['dG']
        h_idx = ((dt_solar.hour * 60 + dt_solar.minute + 60) // 120) % 12
        target_dG_for_hour = self.m_db.get((dt_solar + timedelta(hours=2)).strftime("%Y%m%d"))['dG'] if (use_yajas_i and jasi_type == "YAJAS-I") else day_data['dG']
        hG_gan = sc.STEMS[({ '甲':0,'己':0,'乙':2,'庚':2,'丙':4,'辛':4,'丁':6,'壬':6,'戊':8,'癸':8 }[target_dG_for_hour[0]] + h_idx) % 10]
        palja = [yG[0], yG[1], mG[0], mG[1], day_data['dG'][0], day_data['dG'][1], hG_gan, sc.BRANCHES[h_idx]]
        
        # 4. 심층 분석
        me_hj = sc.E_MAP_HJ.get(palja[4])
        scores, power = self._calculate_power(palja, me_hj)
        yongsin = self._get_yongsin_info(palja, power, me_hj)
        pillars = self._investigate_sinsal(palja, palja[4], me_hj)
        for p in pillars: p['gan_elem'], p['ji_elem'] = sc.ELEMENT_MAP[p['gan']], sc.ELEMENT_MAP[p['ji']]
        
        l_term, n_term = self._get_solar_terms(dt_raw)
        daeun_num, daeun_list = self._calculate_daeun(dt_raw, yG, mG, gender, l_term, n_term)
        daeun_list = self._calculate_daeun_scores(daeun_list, yongsin, palja)
        
        # 5. 운의 흐름 및 상호작용
        now = datetime.now()
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), "age": now.year - dt_raw.year + 1,
            "daeun": next((d for d in daeun_list if d['start_age'] <= (now.year - dt_raw.year + 1) < d['start_age'] + 10), daeun_list[0]),
            "seun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('yG', 'N/A'),
            "wolun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('mG', 'N/A'),
            "ilun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('dG', 'N/A')
        }
        interactions = self._analyze_interactions(palja)
        display_tags = []
        for v in interactions.values(): display_tags.extend(v)

        return {
            "solar_display": dt_raw.strftime("%Y/%m/%d %H:%M"),
            "calendar_type": calendar_type,
            "corrected_display": dt_solar.strftime("%Y/%m/%d %H:%M"),
            "lunar_display": f"{day_data['ly']}/{day_data['lm']:02d}/{day_data['ld']:02d} {dt_raw.strftime('%H:%M')}",
            "lunar_type": "윤" if day_data.get('ls') else "평",
            "lng_diff_str": f"{lng_offset_display:+d}분",
            "gender_str": "여자" if gender == "F" else "남자",
            "location_name": location,
            "display_tags": display_tags[:8],
            "pillars": pillars, "me": palja[4], "me_elem": sc.ELEMENT_MAP[palja[4]],
            "scores": scores, "power": power, "status": self._get_detailed_status(power),
            "yongsin_detail": yongsin, "wealth_analysis": self._analyze_wealth_and_career(pillars, power, yongsin['eokbu_elements']),
            "daeun_num": daeun_num, "daeun_list": daeun_list, "current_trace": current_trace,
            "interactions": interactions, "jasi_type": jasi_type, "birth": birth_str, "gender": gender, "ilju": palja[4]+palja[5]
        }