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
            return None, False
        
        return dt_input, True

    def _get_historical_correction(self, dt):
        """역사적 표준시 및 서머타임 보정 (sc.DST_PERIODS 참조)"""
        offset, ts = 0, dt.strftime("%Y%m%d%H%M")
        if "190804010000" <= ts <= "191112312359": offset += 30
        elif "195403210000" <= ts <= "196108092359": offset += 30
        for start, end in sc.DST_PERIODS:
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
        today_str, year_str = dt_in.strftime("%Y%m%d"), str(dt_in.year)
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
    # 2. 사주 핵심 연산 로직 (Core Saju Calculation)
    # ==========================================================================
    def _calculate_power(self, palja, me_hj):
        """신강약 점수 계산 (sc.POWER_WEIGHT_MAP 참조)"""
        scores = {elem: 0.0 for elem in sc.HJ_TO_HG.values()}
        power = 0
        
        # 1. 오행 기본 분포 계산 (순수하게 8글자 개수 비중)
        for char in palja:
            scores[sc.ELEMENT_MAP[char]] += 12.5 # 100 / 8 = 12.5
            
        # 2. 신강약 세력 계산 (가중치 적용)
        # sc.POWER_WEIGHT_MAP을 순회하므로 인덱스 실수가 원천 차단됩니다.
        for idx, weight in sc.POWER_WEIGHT_MAP:
            char = palja[idx]
            target_hj = sc.E_MAP_HJ[char]
            
            # 내가 나를 돕는 오행(비겁, 인성)인지 확인
            if sc.REL_MAP.get((me_hj, target_hj)) in sc.STRONG_ENERGY:
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
        """용신 분석 (sc.STRONG_ENERGY, sc.WINTER_BS 등 참조)"""
        targets = sc.STRONG_ENERGY if power <= 49 else sc.WEAK_ENERGY
        eokbu_type = "/".join(targets)
        found_elements = [sc.HJ_TO_HG[hj] for hj in sc.HJ_ELEMENTS if sc.REL_MAP.get((me_hj_hanja, hj)) in targets]
        
        mb, johoo = palja[3], "필요 없음 (중화)"
        if mb in sc.WINTER_BS: johoo = "화(火) - 추운 계절이라 따뜻한 기운이 최우선입니다."
        elif mb in sc.SUMMER_BS: johoo = "수(水) - 더운 계절이라 시원한 기운이 최우선입니다."
        elif mb in sc.SPRING_BS: johoo = "화(火) - 만물이 성장하도록 온기가 필요합니다."
        elif mb in sc.AUTUMN_BS: johoo = "수(水) - 건조한 계절이라 적절한 수기가 필요합니다."

        return {"eokbu_elements": "/".join(found_elements or ["데이터 확인 필요"]), "eokbu_type": eokbu_type, "johoo": johoo}
    
    def _investigate_sinsal(self, palja, me, me_hj):
        """모든 신살과 십성을 데이터 명세 기반으로 전수 조사합니다."""
        # 기초 데이터 준비
        y_ji, d_ji = palja[1], palja[5]
        start_y, start_d = sc.BRANCHES.find(sc.SAMHAP_START_MAP[y_ji]), sc.BRANCHES.find(sc.SAMHAP_START_MAP[d_ji])
        
        # 공망 데이터 추출
        ilju_name = palja[4] + palja[5]
        g_jis = sc.GONGMANG_MAP[self.SIXTY_GANZI.index(ilju_name) // 10]

        pillars = []
        for i in range(4):
            g, j, special = palja[i*2], palja[i*2+1], []
            ganzi = g + j
            
            # 1. 12신살 (년지/일지 기준 연산)
            s12_y = sc.SINSAL_12_NAMES[(sc.BRANCHES.find(j) - start_y) % 12]
            s12_d = sc.SINSAL_12_NAMES[(sc.BRANCHES.find(j) - start_d) % 12]
            special.append(s12_y)
            if s12_d != s12_y: special.append(f"{s12_d}(일)")
            
            # 2. 공망 체크 (sc.POSITIONS 참조)
            if j in g_jis: special.append(f"공망({sc.B_KOR.get(j, j)})")

            # 3. 간지 조합 규칙 순회 (괴강, 백호 등)
            for rule_list, name in sc.PILLAR_SINSAL_RULES:
                if ganzi in rule_list: special.append(name)

            # 4. 개별 글자 규칙 순회 (현침 등)
            for rule_list, name in sc.CHAR_SINSAL_RULES:
                if g in rule_list or j in rule_list: special.append(name)

            # 5. 일간(Me) 기준 매핑 규칙 순회 (양인, 귀인 등)
            for mapping, name, val_type in sc.ME_MAPPING_RULES:
                val = mapping.get(me)
                if (val_type == "single" and j == val) or (val_type == "list" and j in (val or [])):
                    special.append(name)

            # 6. 일지(Day Ji) 기준 매핑 규칙 순회 (귀문관살 등)
            for mapping, name, val_type in sc.DAY_JI_MAPPING_RULES:
                val = mapping.get(d_ji)
                if (val_type == "single" and j == val) or (val_type == "list" and j in (val or [])):
                    special.append(name)

            # 7. 십성(Ten Gods) 계산 - 별도 추상화된 헬퍼 사용
            t_gan = "본인" if i == 2 else self._get_ten_god(me, g, me_hj)
            t_ji = self._get_ten_god(me, j, me_hj)
            
            pillars.append({
                "gan": g, "ji": j, "t_gan": t_gan, "t_ji": t_ji, 
                "sinsal_12": s12_y, 
                "special": sorted(list(set(special)))
            })
        return pillars

    def _get_ten_god(self, me, target, me_hj):
        """십성 관계명을 구하는 데이터 매핑 헬퍼입니다."""
        rel = sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[target]))
        is_same = (sc.POLARITY_MAP[me] == sc.POLARITY_MAP[target])
        return sc.TEN_GODS_MAP.get((rel, is_same), "-")

    # ==========================================================================
    # 3. 대운 및 환경 분석 (Luck & Environment Analysis)
    # ==========================================================================
    def _calculate_daeun(self, dt_in, yG, mG, gender, l_term, n_term):
        """대운수 및 경로 계산"""
        is_fwd = (gender == 'M' and sc.POLARITY_MAP[yG[0]] == '+') or (gender == 'F' and sc.POLARITY_MAP[yG[0]] == '-')
        target_term = n_term if is_fwd else l_term
        daeun_num = max(1, int(round(abs((target_term['dt_obj'] - dt_in).total_seconds() / 86400) / 3.0)))
        daeun_list, curr_idx = [], self.SIXTY_GANZI.index(mG)
        for i in range(1, 12):
            curr_idx = (curr_idx + 1) % 60 if is_fwd else (curr_idx - 1) % 60
            daeun_list.append({"start_age": daeun_num + (i-1)*10, "ganzi": self.SIXTY_GANZI[curr_idx]})
        return daeun_num, daeun_list

    def _calculate_daeun_scores(self, daeun_list, yongsin_info, palja):
        """대운 점수 산출 (sc.DAEUN_WEIGHTS, sc.INTERACTION_SCORES 참조)"""
        yong = yongsin_info['eokbu_elements'].split('/')
        huising = [sc.SANGSAENG.get(y) for y in yong if y in sc.SANGSAENG]
        n_stems, n_branches = [palja[0], palja[2], palja[4], palja[6]], [palja[1], palja[3], palja[5], palja[7]]

        for d in daeun_list:
            dg, dj = d['ganzi'][0], d['ganzi'][1]
            ghj, jhj = sc.ELEMENT_MAP.get(dg), sc.ELEMENT_MAP.get(dj)
            
            score = sc.BASE_SCORE
            score += sc.DAEUN_WEIGHTS["yong_gan"] if ghj in yong else sc.DAEUN_WEIGHTS["hui_gan"] if ghj in huising else sc.DAEUN_WEIGHTS["bad_gan"]
            score += sc.DAEUN_WEIGHTS["yong_ji"] if jhj in yong else sc.DAEUN_WEIGHTS["hui_ji"] if jhj in huising else sc.DAEUN_WEIGHTS["bad_ji"]
            
            is_jg, offset = (jhj in yong or jhj in huising), 0
            for ns in n_stems:
                if sc.D_STEM_HAB.get(dg) == ns: offset += sc.INTERACTION_SCORES["stem_hab"]
                if sc.D_STEM_CHUNG.get(dg) == ns: offset += sc.INTERACTION_SCORES["stem_chung_good"] if is_jg else sc.INTERACTION_SCORES["stem_chung_bad"]
            for nb in n_branches:
                if sc.D_BRANCH_HAB.get(dj) == nb: offset += sc.INTERACTION_SCORES["branch_hab"]
                if sc.D_BRANCH_CHUNG.get(dj) == nb: offset += sc.INTERACTION_SCORES["branch_chung_good"] if is_jg else sc.INTERACTION_SCORES["branch_chung_bad"]
            d['score'] = max(0, min(100, int(score + offset)))
        return daeun_list

    def _analyze_wealth_and_career(self, pillars, power, yongsin_elements):
        """재물/커리어 성공 지수 분석 (sc.WEALTH_TEN_GODS 등 참조)"""
        atg, asp = [], []
        for p in pillars:
            atg.extend([p['t_gan'], p['t_ji']]); asp.extend(p['special'])
        
        w_count = sum(atg.count(tg) for tg in sc.WEALTH_TEN_GODS)
        s_count = sum(atg.count(tg) for tg in sc.OUTPUT_TEN_GODS)
        c_count = sum(atg.count(tg) for tg in sc.CAREER_TEN_GODS)
        i_count = sum(atg.count(tg) for tg in sc.INTEL_TEN_GODS)
        
        ws = 40 + w_count * (8 if power >= 50 else 4)
        if s_count > 0 and w_count > 0: ws += 15
        if 40 <= power <= 65: ws += 10
        elif power < 30 and w_count >= 3: ws -= 15

        cs = 40 + c_count * 10 + (15 if c_count > 0 and i_count > 0 else 0)
        
        for s in sc.SUCCESS_SPECIALS:
            if s in asp:
                if s == "관귀학관": cs += 10
                elif s == "백호대살": cs += 5
                elif s in ["천을귀인", "태극귀인"]: ws += 5; cs += 5

        get_grade = lambda s: "S (최상)" if s >= 85 else "A (우수)" if s >= 70 else "B (보통)" if s >= 55 else "C (관리필요)"
        return {"wealth_score": min(100, ws), "career_score": min(100, cs), "wealth_grade": get_grade(ws), "career_grade": get_grade(cs)}

    # ==========================================================================
    # 상호작용 분석 로직 (Interactions Analysis)
    # ==========================================================================
    def _analyze_interactions(self, palja):
        """원국 내 11가지 상호작용 분석을 총괄합니다."""
        res = {k: [] for k in sc.INTERACTION_KEYS}
        sl, bl = [palja[0], palja[2], palja[4], palja[6]], [palja[1], palja[3], palja[5], palja[7]]
        
        # 1. 쌍(Pairwise) 관계 분석 - 데이터 명세(sc.PAIRWISE_RULES) 기반 루프
        for i in range(4):
            for j in range(i + 1, 4):
                for key, mapping, target_type in sc.PAIRWISE_RULES:
                    target_list = sl if target_type == "stem" else bl
                    pair = "".join(sorted([target_list[i], target_list[j]]))
                    if pair in mapping:
                        res[key].append(mapping[pair])
        
        # 2. 그룹(Group) 관계 분석 - 보조 함수 호출
        self._check_group_interactions(bl, res)

        # 3. 공망 분석 - 상수의 위치 명칭(sc.POSITIONS) 참조
        ilju_name = palja[4] + palja[5]
        g_jis = sc.GONGMANG_MAP[self.SIXTY_GANZI.index(ilju_name) // 10]
        for i, b in enumerate(bl):
            if b in g_jis:
                res["공망"].append(f"{sc.POSITIONS[i]} 공망({sc.B_KOR.get(b, b)})")
                
        return {k: sorted(list(set(v))) for k, v in res.items()}

    def _check_group_interactions(self, bl, res):
        """삼합 및 방합 분석 로직을 별도로 관리합니다."""
        # 삼합/반합 체크
        for key, (val, king) in sc.B_SAMHAP.items():
            match = [c for c in key if c in bl]
            if len(set(match)) >= 3:
                res["지지삼합"].append(f"{val} 삼합({key})")
            elif len(set(match)) == 2 and king in bl:
                res["지지삼합"].append(f"{''.join([sc.B_KOR[c] for c in match])} 반합({val})")
        
        # 방합/반합 체크
        for key, val in sc.B_BANGHAP.items():
            match = [c for c in key if c in bl]
            if len(set(match)) >= 3:
                res["지지방합"].append(val)
            elif len(set(match)) == 2:
                res["지지방합"].append(f"{''.join([sc.B_KOR[c] for c in match])} 반합")

    # ==========================================================================
    # 4. 메인 분석 엔진 (Main Analysis Orchestrator)
    # ==========================================================================
    def analyze(self, birth_str, gender, location, use_yajas_i, calendar_type="양력"):
        # 1. 입력 전처리 및 양력 변환
        dt_raw, success = self._parse_and_convert_to_solar(birth_str, calendar_type)
        if not success: return {"error": f"입력 날짜({birth_str})를 찾을 수 없습니다."}
        
        # 2. 정밀 시간 보정 (지역 시차 - 반올림 적용)
        lng_off = int(round((sc.CITY_DATA.get(location, sc.DEFAULT_LNG) - 135) * 4))
        dt_solar = dt_raw + timedelta(minutes=self._get_historical_correction(dt_raw) + lng_off)
        
        # 3. 원국 생성 및 절기 보정
        jasi, fetch_dt = self._get_jasi_type(dt_solar), dt_solar
        if not use_yajas_i and jasi == "YAJAS-I": fetch_dt = dt_solar + timedelta(hours=2)
        day_data = self.m_db.get(fetch_dt.strftime("%Y%m%d"))
        if not day_data: return {"error": "DB 데이터가 없습니다."}
        
        yG, mG = self._apply_solar_correction(dt_raw, day_data['yG'], day_data['mG'])
        h_idx = ((dt_solar.hour * 60 + dt_solar.minute + 60) // 120) % 12
        target_dG = self.m_db.get((dt_solar + timedelta(hours=2)).strftime("%Y%m%d"))['dG'] if (use_yajas_i and jasi == "YAJAS-I") else day_data['dG']
        hG_gan = sc.STEMS[(sc.HG_START_IDX[target_dG[0]] + h_idx) % 10]
        palja = [yG[0], yG[1], mG[0], mG[1], day_data['dG'][0], day_data['dG'][1], hG_gan, sc.BRANCHES[h_idx]]
        
        # 4. 심층 분석
        me_hj = sc.E_MAP_HJ.get(palja[4])
        scores, power = self._calculate_power(palja, me_hj)
        yongsin, pillars = self._get_yongsin_info(palja, power, me_hj), self._investigate_sinsal(palja, palja[4], me_hj)
        for p in pillars: p['gan_elem'], p['ji_elem'] = sc.ELEMENT_MAP[p['gan']], sc.ELEMENT_MAP[p['ji']]
        
        l_term, n_term = self._get_solar_terms(dt_raw)
        daeun_num, daeun_list = self._calculate_daeun(dt_raw, yG, mG, gender, l_term, n_term)
        daeun_list = self._calculate_daeun_scores(daeun_list, yongsin, palja)
        
        # 5. 운의 흐름 및 상호작용
        now = datetime.now()
        curr_age = now.year - dt_raw.year + 1
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), "age": curr_age,
            "daeun": next((d for d in daeun_list if d['start_age'] <= curr_age < d['start_age'] + 10), daeun_list[0]),
            "seun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('yG', 'N/A'),
            "wolun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('mG', 'N/A'),
            "ilun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('dG', 'N/A')
        }
        interactions = self._analyze_interactions(palja)
        display_tags = [item for sublist in interactions.values() for item in sublist][:8]

        return {
            "solar_display": dt_raw.strftime("%Y/%m/%d %H:%M"), "calendar_type": calendar_type, "corrected_display": dt_solar.strftime("%Y/%m/%d %H:%M"),
            "lunar_display": f"{day_data['ly']}/{day_data['lm']:02d}/{day_data['ld']:02d} {dt_raw.strftime('%H:%M')}", "lunar_type": "윤" if day_data.get('ls') else "평",
            "lng_diff_str": f"{lng_off:+d}분", "gender_str": "여자" if gender == "F" else "남자", "location_name": location, "display_tags": display_tags,
            "pillars": pillars, "me": palja[4], "me_elem": sc.ELEMENT_MAP[palja[4]], "scores": scores, "power": power, "status": self._get_detailed_status(power),
            "yongsin_detail": yongsin, "wealth_analysis": self._analyze_wealth_and_career(pillars, power, yongsin['eokbu_elements']),
            "daeun_num": daeun_num, "daeun_list": daeun_list, "current_trace": current_trace, "interactions": interactions, "jasi_type": jasi, "birth": birth_str, "gender": gender, "ilju": palja[4]+palja[5]
        }