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

    def _get_next_ganzi(self, ganzi):
        """상수를 사용하여 간지를 다음 순번으로 계산합니다 (예: 己酉 -> 庚戌)"""
        s_idx = sc.STEMS.index(ganzi[0])
        b_idx = sc.BRANCHES.index(ganzi[1])
        return sc.STEMS[(s_idx + 1) % 10] + sc.BRANCHES[(b_idx + 1) % 12]

    def _apply_solar_correction(self, dt_raw, yG, mG):
        """절기 입입 시각을 정밀 비교하여 월건을 보정합니다."""
        l_term_data, _ = self._get_solar_terms(dt_raw)
        
        # _get_solar_terms에서 생성한 dt_obj(datetime 객체)를 안전하게 추출
        if isinstance(l_term_data, dict):
            l_term_dt = l_term_data.get('dt_obj') or l_term_data.get('dt')
        else:
            l_term_dt = l_term_data

        # 생시가 입절 시각보다 같거나 늦으면 다음 달로 보정
        if dt_raw >= l_term_dt:
            # 월별 지지 매핑 (10월 한로 이후는 반드시 '戌')
            month_to_branch_idx = {2:2, 3:3, 4:4, 5:5, 6:6, 7:7, 8:8, 9:9, 10:10, 11:11, 12:0, 1:1}
            expected_b = sc.BRANCHES[month_to_branch_idx.get(l_term_dt.month, 0)]
            
            if mG[1] != expected_b:
                mG = self._get_next_ganzi(mG)
                
        return yG, mG
    

    # ==========================================================================
    # 2. 사주 핵심 연산 로직 (Core Saju Calculation)
    # ==========================================================================
    def _calculate_power(self, palja, me_hj):
        """포스텔러 스타일: 8글자 단순 개수 중심(각 12.5%) 점수 계산"""
        scores = {"목": 0.0, "화": 0.0, "토": 0.0, "금": 0.0, "수": 0.0}
        
        # 1. 오행 분포: 8글자 각각 12.5%씩 배분
        for char in palja:
            elem = sc.ELEMENT_MAP[char]
            scores[elem] += 12.5
            
        # 2. 신강약 세력: 나를 돕는 글자 개수 x 12.5
        power = 0
        for char in palja:
            target_hj = sc.E_MAP_HJ[char]
            if sc.REL_MAP.get((me_hj, target_hj)) in sc.STRONG_ENERGY:
                power += 12.5
                
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
        """용신 분석"""
        targets = sc.STRONG_ENERGY if power <= 49 else sc.WEAK_ENERGY
        eokbu_type = "/".join(targets)
        
        needed_elements = [sc.HJ_TO_HG[hj] for hj in sc.HJ_ELEMENTS if sc.REL_MAP.get((me_hj_hanja, hj)) in targets]
        present_hj = set(sc.E_MAP_HJ[c] for c in palja)
        existing_yongsin = [sc.HJ_TO_HG[hj] for hj in present_hj if sc.REL_MAP.get((me_hj_hanja, hj)) in targets]
        
        mb, johoo = palja[3], "필요 없음 (중화)"
        if mb in sc.WINTER_BS: johoo = "화(火) - 추운 계절이라 따뜻한 기운이 최우선입니다."
        elif mb in sc.SUMMER_BS: johoo = "수(水) - 더운 계절이라 시원한 기운이 최우선입니다."
        elif mb in sc.SPRING_BS: johoo = "화(火) - 만물이 성장하도록 온기가 필요합니다."
        elif mb in sc.AUTUMN_BS: johoo = "수(水) - 건조한 계절이라 적절한 수기가 필요합니다."

        return {
            "eokbu_elements": "/".join(needed_elements),
            "actual_yongsin": "/".join(existing_yongsin) if existing_yongsin else "원국 내 없음 (운에서 보완 필요)",
            "eokbu_type": eokbu_type, 
            "johoo": johoo
        }
    
    def _get_ten_god(self, me, target, me_hj):
        """체용 변화가 적용된 FUNCTIONAL_POLARITY를 참조하여 십성을 계산합니다."""
        rel = sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[target]))
        is_same = (sc.FUNCTIONAL_POLARITY[me] == sc.FUNCTIONAL_POLARITY[target])
        return sc.TEN_GODS_MAP.get((rel, is_same), "-")

    def _investigate_sinsal(self, palja, me, me_hj):
        """기존 코드를 유지하며 상세 표 출력용 필드를 추가합니다."""
        y_ji, d_ji = palja[1], palja[5]
        start_y, start_d = sc.BRANCHES.find(sc.SAMHAP_START_MAP[y_ji]), sc.BRANCHES.find(sc.SAMHAP_START_MAP[d_ji])
        ilju_name = palja[4] + palja[5]

        pillars = []
        for i in range(4):
            g, j, special = palja[i*2], palja[i*2+1], []
            s12_y = sc.SINSAL_12_NAMES[(sc.BRANCHES.find(j) - start_y) % 12]
            s12_d = sc.SINSAL_12_NAMES[(sc.BRANCHES.find(j) - start_d) % 12]
            special.append(s12_y)
            if s12_d != s12_y: special.append(f"{s12_d}(일)")
            
            sinsal_table_gan, sinsal_table_ji = [], [s12_y]
            if s12_d != s12_y: sinsal_table_ji.append(f"{s12_d}(일)")

            for mapping, name, m_type in sc.ME_MAPPING_RULES:
                val = mapping.get(me)
                if val:
                    if (m_type == "single" and j == val) or (m_type == "list" and j in val):
                        if name not in special: special.append(name)
                        sinsal_table_ji.append(name)

            if (g + j) in sc.BAEKHO_LIST:
                if "백호대살" not in special: special.append("백호대살"); sinsal_table_gan.append("백호대살")
            if g in sc.HYEONCHIM_CHARS:
                if "현침살" not in special: special.append("현침살"); sinsal_table_gan.append("현침살")
            if j in sc.HYEONCHIM_CHARS:
                if "현침살" not in special: special.append("현침살"); sinsal_table_ji.append("현침살")

            gan_pol_str = "+" if sc.FUNCTIONAL_POLARITY[g] else "-"
            ji_pol_str = "+" if sc.FUNCTIONAL_POLARITY[j] else "-"
            
            pillars.append({
                "gan": g, "gan_kor": sc.B_KOR[g], "gan_elem": sc.ELEMENT_MAP[g], "gan_pol": gan_pol_str,
                "ji": j, "ji_kor": sc.B_KOR[j], "ji_elem": sc.ELEMENT_MAP[j], "ji_pol": ji_pol_str,
                "t_gan": "본인" if i == 2 else self._get_ten_god(me, g, me_hj),
                "t_ji": self._get_ten_god(me, j, me_hj),
                "jijangan": sc.JIJANGAN_MAP.get(j, "-"),
                "unseong": sc.UNSEONG_MAP.get(me, {}).get(j, "-"),
                "sinsal_12": s12_y,
                "special": sorted(list(set(special))),
                "sinsal_table_gan": sorted(list(set(sinsal_table_gan))),
                "sinsal_table_ji": sorted(list(set(sinsal_table_ji)))
            })
        return pillars

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
        """대운 점수 산출"""
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
        """재물/커리어 성공 지수 분석"""
        atg, asp = [], []
        for p in pillars: atg.extend([p['t_gan'], p['t_ji']]); asp.extend(p['special'])
        
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

    def _analyze_interactions(self, palja):
        """인덱스를 년(0), 월(1), 일(2), 시(3) 순서로 고정하여 화면과 동기화합니다."""
        res = {k: [] for k in sc.INTERACTION_KEYS}
        sl = [palja[0], palja[2], palja[4], palja[6]]
        bl = [palja[1], palja[3], palja[5], palja[7]]
        
        for i in range(4):
            for j in range(i + 1, 4):
                for key, mapping, target_type in sc.PAIRWISE_RULES:
                    target_list = sl if target_type == "stem" else bl
                    pair = "".join(sorted([target_list[i], target_list[j]]))
                    if pair in mapping: res[key].append({"name": mapping[pair], "subs": [i, j]})
        
        self._check_group_interactions(bl, res)
        ilju_name = palja[4] + palja[5]
        g_jis = sc.GONGMANG_MAP[self.SIXTY_GANZI.index(ilju_name) // 10]
        for i, b in enumerate(bl):
            if b in g_jis: res["공망"].append({"name": f"{sc.POSITIONS[i]} 공망({sc.B_KOR.get(b, b)})", "subs": [i]})

        unique_res = {}
        for k, v in res.items():
            seen, unique_list = set(), []
            for item in v:
                if item["name"] not in seen: unique_list.append(item); seen.add(item["name"])
            unique_res[k] = sorted(unique_list, key=lambda x: x["name"])
        return unique_res

    def _check_group_interactions(self, bl, res):
        """삼합/방합 분석"""
        for key, (val, king) in sc.B_SAMHAP.items():
            match_indices = [idx for idx, b in enumerate(bl) if b in key]
            if len(set(match_indices)) >= 3: res["지지삼합"].append({"name": f"{val} 삼합", "subs": match_indices})
            elif len(set(match_indices)) == 2 and king in bl:
                chars = "".join([sc.B_KOR.get(bl[idx], bl[idx]) for idx in match_indices])
                res["지지삼합"].append({"name": f"{chars} 반합({val})", "subs": match_indices})
        for key, val in sc.B_BANGHAP.items():
            match_indices = [idx for idx, b in enumerate(bl) if b in key]
            if len(set(match_indices)) >= 3: res["지지방합"].append({"name": val, "subs": match_indices})
            elif len(set(match_indices)) == 2:
                chars = "".join([sc.B_KOR.get(bl[idx], bl[idx]) for idx in match_indices])
                res["지지방합"].append({"name": f"{chars} 반합", "subs": match_indices})

    def _get_element_status(self, scores):
        """오행 상태 진단"""
        results = {}
        for hj in sc.HJ_ELEMENTS:
            kor_name = sc.HJ_TO_HG.get(hj)
            if not kor_name: continue
            val = scores.get(kor_name, 0.0)
            results[kor_name] = {
                "hanja": hj, "score": f"{val:.1f}%",
                "status": "과다" if val >= 45 else "발달" if val >= 25 else "부족" if val == 0 else "적정"
            }
        return results

    def _get_tengod_distribution(self, pillars):
        """포스텔러 스타일: 8글자 위치별 십성 비중 계산 (각 12.5%)"""
        tg_list = ["비견", "겁재", "식신", "상관", "편재", "정재", "편관", "정관", "편인", "정인"]
        counts = {tg: 0 for tg in tg_list}
        
        for p in pillars:
            # 천간 십성 (본인은 비견으로 처리)
            tg_gan = "비견" if p['t_gan'] == "본인" else p['t_gan']
            if tg_gan in counts: counts[tg_gan] += 1
            # 지지 십성
            tg_ji = p['t_ji']
            if tg_ji in counts: counts[tg_ji] += 1
            
        return {tg: {"count": counts[tg], "ratio": f"{(counts[tg] * 12.5):.1f}%" if counts[tg] > 0 else "-"} for tg in tg_list}
    
    def _get_combined_analysis(self, scores, me_elem, pillars):
        """포스텔러 스타일: 오행(목~수)을 고정하고 십성을 그에 맞춰 배치합니다."""
        elements = ["목", "화", "토", "금", "수"]
        # 십성 쌍 정의 (나와의 거리 순서: 0:비겁, 1:식상, 2:재성, 3:관성, 4:인성)
        tg_pairs = [
            ("비견", "겁재"), # 0: 비겁
            ("식신", "상관"), # 1: 식상
            ("편재", "정재"), # 2: 재성
            ("편관", "정관"), # 3: 관성
            ("편인", "정인")  # 4: 인성
        ]
        
        # 8글자에서 십성 개수 집계
        tg_counts = {tg: 0 for pair in tg_pairs for tg in pair}
        for p in pillars:
            for tg in [p['t_gan'], p['t_ji']]:
                lookup = "비견" if tg == "본인" else tg
                if lookup in tg_counts: tg_counts[lookup] += 1

        me_idx = elements.index(me_elem) # 내 오행의 인덱스
        combined_list = []

        for i, elem in enumerate(elements):
            # 내 오행(me_idx)과 현재 오행(i)의 거리 계산 (0~4)
            dist = (i - me_idx) % 5
            pair = tg_pairs[dist]
            
            score_val = scores.get(elem, 0.0)
            status_str = "과다" if score_val >= 45 else "발달" if score_val >= 25 else "부족" if score_val == 0 else "적정"
            
            combined_list.append({
                "elem_name": elem,
                "score": f"{score_val:.1f}%",
                "status": status_str,
                "tg1_name": pair[0],
                "tg1_ratio": f"{(tg_counts[pair[0]] * 12.5):.1f}%" if tg_counts[pair[0]] > 0 else "-",
                "tg2_name": pair[1],
                "tg2_ratio": f"{(tg_counts[pair[1]] * 12.5):.1f}%" if tg_counts[pair[1]] > 0 else "-"
            })
        return combined_list
    # ==========================================================================
    # 4. 메인 분석 엔진 (Main Analysis Orchestrator)
    # ==========================================================================
    def analyze(self, birth_str, gender, location, use_yajas_i, calendar_type="양력"):
        # 1. 입력 날짜 파싱 및 양력 변환
        dt_raw, success = self._parse_and_convert_to_solar(birth_str, calendar_type)
        if not success: return {"error": f"입력 날짜({birth_str})를 찾을 수 없습니다."}
        
        # 2. 지역 경도 및 역사적 표준시 보정 (시각 결정)
        lng_off = int(round((sc.CITY_DATA.get(location, sc.DEFAULT_LNG) - 135) * 4))
        dt_solar = dt_raw + timedelta(minutes=self._get_historical_correction(dt_raw) + lng_off)
        
        # 3. 야자시/조자시 판정 및 DB 데이터 로드
        jasi, fetch_dt = self._get_jasi_type(dt_solar), dt_solar
        if not use_yajas_i and jasi == "YAJAS-I": 
            fetch_dt = dt_solar + timedelta(hours=2)
            
        day_data = self.m_db.get(fetch_dt.strftime("%Y%m%d"))
        if not day_data: return {"error": "DB 데이터가 없습니다."}
        
        # 4. [절기 보정] 입절 시각을 정밀 비교하여 월건(mG) 확정
        yG, mG = self._apply_solar_correction(dt_raw, day_data['yG'], day_data['mG'])
        
        # 5. 시주(hG) 및 일주(dG) 결정
        h_idx = ((dt_solar.hour * 60 + dt_solar.minute + 60) // 120) % 12
        input_day_data = self.m_db.get(dt_raw.strftime("%Y%m%d"))
        target_dG = self.m_db.get((dt_solar + timedelta(hours=2)).strftime("%Y%m%d"))['dG'] if (use_yajas_i and jasi == "YAJAS-I") else input_day_data['dG']
        
        hG_gan = sc.STEMS[(sc.HG_START_IDX[target_dG[0]] + h_idx) % 10]
        
        # 6. [데이터 동기화] 8글자(palja) 구성
        palja = [yG[0], yG[1], mG[0], mG[1], target_dG[0], target_dG[1], hG_gan, sc.BRANCHES[h_idx]]
        print(f"\n>>> palja:\n{palja}")

        
        # 7. 오행/신강약 분석
        me_hj = sc.E_MAP_HJ.get(palja[4]) 
        scores, power = self._calculate_power(palja, me_hj)
        yongsin, pillars = self._get_yongsin_info(palja, power, me_hj), self._investigate_sinsal(palja, palja[4], me_hj)
        
        for p in pillars: 
            p['gan_elem'], p['ji_elem'] = sc.ELEMENT_MAP[p['gan']], sc.ELEMENT_MAP[p['ji']]
        
        # 8. 대운 계산
        l_term, n_term = self._get_solar_terms(dt_raw)
        daeun_num, daeun_list = self._calculate_daeun(dt_raw, yG, mG, gender, l_term, n_term)
        daeun_list = self._calculate_daeun_scores(daeun_list, yongsin, palja)
        
        # 9. 현재 운세(운로) 추적
        now = datetime.now()
        curr_age = now.year - dt_raw.year + 1
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), "age": curr_age,
            "daeun": next((d for d in daeun_list if d['start_age'] <= curr_age < d['start_age'] + 10), daeun_list[0]),
            "seun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('yG', 'N/A'),
            "wolun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('mG', 'N/A'),
            "ilun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('dG', 'N/A')
        }
        
        # 10. 상호작용 분석
        interactions = self._analyze_interactions(palja)
        display_tags = [item for sublist in interactions.values() for item in sublist][:8]
        
        # 11. 오행/십성 통계 구성 (HTML 에러 방지)
        element_dict = self._get_element_status(scores)
        tengod_dict = self._get_tengod_distribution(pillars)
        
        element_list = [{"name": k, **v} for k, v in element_dict.items()]
        tengod_list = [{"name": k, **v} for k, v in tengod_dict.items()]
        
        # ----------------------------------------------------------------------
        # [추가] 포스텔러 스타일 통합 분석 (오행 고정 + 십성 유동)
        # ----------------------------------------------------------------------
        elements_fixed = ["목", "화", "토", "금", "수"]
        tg_pairs = [("비견", "겁재"), ("식신", "상관"), ("편재", "정재"), ("편관", "정관"), ("편인", "정인")]
        group_names = ["비겁", "식상", "재성", "관성", "인성"]
        
        me_elem_name = sc.ELEMENT_MAP[palja[4]]
        me_idx = elements_fixed.index(me_elem_name)
        
        forestellar_analysis = [] # 표 전용 (목화토금수 순서)
        relation_groups = [None] * 5 # 그래프 전용 (나부터 시작하는 순서)

        for i, elem in enumerate(elements_fixed):
            dist = (i - me_idx) % 5  # 나와의 거리 (0:비겁, 1:식상...)
            pair = tg_pairs[dist]
            e_status = element_dict.get(elem, {"score": "0.0%", "status": "부족"})
            
            # 1. 표(Table) 데이터 구성
            row_data = {
                "elem_name": elem,
                "score": e_status['score'],
                "percent": float(e_status['score'].replace('%', '')), # 숫자형 추가
                "status": e_status['status'],
                "tg1_name": pair[0],
                "tg1_ratio": tengod_dict.get(pair[0], {}).get('ratio', '-'),
                "tg2_name": pair[1],
                "tg2_ratio": tengod_dict.get(pair[1], {}).get('ratio', '-')
            }
            forestellar_analysis.append(row_data)

            # 2. 그래프(Graph) 데이터 구성 (나를 0번 인덱스에 배치)
            relation_groups[dist] = {
                "group_name": group_names[dist],
                "elem_name": elem,
                "score": row_data["score"],
                "percent": row_data["percent"]
            }
        # ----------------------------------------------------------------------

        # [교정] 대표 오행 추출 (동률 시 일간 우선 로직)
        max_score_val = max(scores.values())
        winners = [k for k, v in scores.items() if v == max_score_val]
        
        representative_elem = me_elem_name if me_elem_name in winners else winners[0]
        # 2. [신규 추가] 대표 성향(십성) 추출
        # tengod_dict에서 가장 count가 높은 십성 이름을 찾습니다.
        # 본인(비견) 세력이 강한 경우 '비견'이 대표 성향으로 잡히게 됩니다.
        representative_tendency = max(tengod_dict, key=lambda k: (tengod_dict[k]['count'], k == "비견"))
      
        
    
        # 12. 최종 결과 조립
        final_result = {
            "solar_display": dt_raw.strftime("%Y/%m/%d %H:%M"), 
            "calendar_type": calendar_type, 
            "corrected_display": dt_solar.strftime("%Y/%m/%d %H:%M"),
            "lunar_display": f"{day_data['ly']}/{day_data['lm']:02d}/{day_data['ld']:02d} {dt_raw.strftime('%H:%M')}", 
            "lunar_type": "윤" if day_data.get('ls') else "평",
            "lng_diff_str": f"{lng_off:+d}분", 
            "gender_str": "여자" if gender == "F" else "남자", 
            "location_name": location, 
            "display_tags": display_tags,
            "pillars": pillars, 
            "me": palja[4], 
            "me_elem": me_elem_name,
            "representative_elem": representative_elem,
            "representative_tendency": representative_tendency,
            "scores": scores, 
            "power": power, 
            "status": self._get_detailed_status(power),
            "yongsin_detail": yongsin, 
            "wealth_analysis": self._analyze_wealth_and_career(pillars, power, yongsin['eokbu_elements']),
            "daeun_num": daeun_num, 
            "daeun_list": daeun_list, 
            "current_trace": current_trace, 
            "interactions": interactions, 
            "jasi_type": jasi, 
            "birth": birth_str, 
            "gender": gender, 
            "ilju": palja[4]+palja[5],
            "element_analysis": element_list, 
            "tengod_analysis": tengod_list,
            "forestellar_analysis": forestellar_analysis, # 통합 분석 데이터 추가
            "me_kor": me_elem_name, 
            "relation_groups" :relation_groups
        }
        
        debug_json = json.dumps(final_result, indent=4, ensure_ascii=False, default=str)
        print(f"\n>>> DEBUG REPORT:\n{debug_json}")

        return final_result