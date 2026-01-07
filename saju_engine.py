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
    # def _calculate_power(self, palja, me_hj):
    #     """포스텔러 스타일: 8글자 단순 개수 중심(각 12.5%) 점수 계산"""
    #     scores = {"목": 0.0, "화": 0.0, "토": 0.0, "금": 0.0, "수": 0.0}
        
    #     # 1. 오행 분포: 8글자 각각 12.5%씩 배분
    #     for char in palja:
    #         elem = sc.ELEMENT_MAP[char]
    #         scores[elem] += 12.5
            
    #     # 2. 신강약 세력: 나를 돕는 글자 개수 x 12.5
    #     power = 0
    #     for char in palja:
    #         target_hj = sc.E_MAP_HJ[char]
    #         if sc.REL_MAP.get((me_hj, target_hj)) in sc.STRONG_ENERGY:
    #             power += 12.5
                
    #     return scores, power

    # def _get_detailed_status(self, power):
    #     """신강약 8단계 세분화"""
    #     if power <= 15: return "극약(極弱)"
    #     elif power <= 30: return "태약(太弱)"
    #     elif power <= 43: return "신약(身弱)"
    #     elif power <= 49: return "중화신약(中和身弱)"
    #     elif power <= 56: return "중화신강(中和身强)"
    #     elif power <= 70: return "신강(身强)"
    #     elif power <= 85: return "태강(太强)"
    #     else: return "극왕(極旺)"


    def _get_element_distribution(self, palja, use_hap_correction=False):
        """오행 분포 계산 (합에 따른 오행 변화 옵션 반영)"""
        dist_scores = {"목": 0.0, "화": 0.0, "토": 0.0, "금": 0.0, "수": 0.0}
        
        # 1. 기본 오행 리스트 추출
        effective_elements = [sc.ELEMENT_MAP[char] for char in palja]
        
        # 2. 합(Hap) 적용 시 오행 변환
        if use_hap_correction:
            bl = [palja[1], palja[3], palja[5], palja[7]] # 지지
            hap_rules = list(sc.B_SAMHAP.items()) + list(sc.B_BANGHAP.items())
            
            for key, val_info in hap_rules:
                res_elem = val_info[0] if isinstance(val_info, tuple) else val_info
                match_indices = [i for i, b in enumerate(bl) if b in key]
                
                # 3글자가 모두 모여 합이 성립하면 해당 지지들의 오행 속성을 결과 오행으로 변경
                if len(set(match_indices)) >= 3:
                    for m_idx in match_indices:
                        actual_idx = [1, 3, 5, 7][m_idx] # 지지 인덱스 매핑
                        effective_elements[actual_idx] = res_elem

        # 3. 최종 오행 분포 합산 (개당 12.5%)
        for elem in effective_elements:
            dist_scores[elem] += 12.5
            
        return dist_scores

    def _calculate_strength_score(self, palja, me_hj, use_hap_correction=False, use_johoo_correction=False):
        """
        [최종 보정판] 합(Hap) 변환 및 조후/궁성 보정값이 적용된 비중 기반 신강약 계산
        """
        me_elem = sc.ELEMENT_MAP[palja[4]]
        
        # 1. 위치별 기본 가중치 (총합 100점)
        weights = {
            3: 30.0, 5: 15.0, 7: 15.0, 1: 10.0, 0: 10.0, 2: 10.0, 6: 10.0
        }
        
        # [옵션] 조후 및 궁성 보정 적용
        if use_johoo_correction:
            month_b = palja[3]
            # 조후: 계절의 기운(월지) 가중치 강화
            if month_b in sc.WINTER_BS or month_b in sc.SUMMER_BS:
                weights[3] += 5.0 # 계절적 영향력 30 -> 35로 상향
            
            # 궁성: 일간과 먼 년주(0, 1)의 영향력을 소폭 하향 보정 (-10%)
            weights[0] *= 0.9
            weights[1] *= 0.9

        # 기본 존재 점수 및 분모 초기화
        strong_sum = 10.0 
        total_presence = 10.0 + sum(weights.values())

        # 2. [옵션] 합(Hap)에 따른 오행 변화 사전 판정
        # 각 자리의 실제 오행 한자(HJ)를 결정합니다.
        effective_hjs = [sc.E_MAP_HJ[c] for c in palja]
        
        if use_hap_correction:
            bl = [palja[1], palja[3], palja[5], palja[7]]
            b_indices = [1, 3, 5, 7]
            hap_rules = list(sc.B_SAMHAP.items()) + list(sc.B_BANGHAP.items())
            
            for key, val_info in hap_rules:
                res_elem_name = val_info[0] if isinstance(val_info, tuple) else val_info
                # 결과 오행 이름(예: '목')을 한자(예: '木')로 변환
                res_hj = next((k for k, v in sc.HJ_TO_HG.items() if v == res_elem_name), None)
                
                match_indices = [i for i, b in enumerate(bl) if b in key]
                if len(set(match_indices)) >= 3: # 3글자가 모두 모여 합이 성립하면
                    for m_idx in match_indices:
                        effective_hjs[b_indices[m_idx]] = res_hj # 오행 속성 영구 변환

        # 3. 각 위치별 기운 합산
        for idx, weight in weights.items():
            char = palja[idx]
            # [중요] 변환 옵션에 따라 수정된 effective_hjs를 사용합니다.
            target_hj = effective_hjs[idx] 
            relation = sc.REL_MAP.get((me_hj, target_hj))
            
            if relation in sc.STRONG_ENERGY:
                strong_sum += weight
                # 통근 보너스
                if palja[4] in sc.JIJANGAN_MAP.get(char, ""):
                    bonus = weight * 0.3
                    strong_sum += bonus
                    total_presence += bonus
            # [궁성 보정] 억제 세력일 때 멀리 있으면 감점 효과 완화 로직 추가 가능
        
        # 4. 합(Hap) 분석: 세력 보너스 (중복 가산 방지를 위해 옵션 미적용 시에만 더 강력히 작동)
        # (기존의 3번 섹션 로직을 유지하되, 세력 판정용으로 활용)
        if not use_hap_correction:
            bl = [palja[1], palja[3], palja[5], palja[7]]
            for key, val_info in (list(sc.B_SAMHAP.items()) + list(sc.B_BANGHAP.items())):
                res_elem = val_info[0] if isinstance(val_info, tuple) else val_info
                if sc.ELEMENT_MAP[palja[4]] == res_elem:
                    match_count = sum(1 for b in bl if b in key)
                    if match_count >= 3:
                        strong_sum += 15.0; total_presence += 15.0
                    elif match_count == 2:
                        strong_sum += 7.0; total_presence += 7.0

        # 5. 머릿수 보정
        strong_count = sum(1 for i, char in enumerate(palja) 
                          if i not in [3, 4] and 
                          sc.REL_MAP.get((me_hj, effective_hjs[i])) in sc.STRONG_ENERGY)
        
        if strong_count >= 5: strong_sum += 5.0
        elif strong_count <= 1: strong_sum -= 5.0

        # 최종 점수 계산
        final_score = (strong_sum / total_presence) * 100
        return max(5, min(100, int(final_score)))

    def _get_detailed_status(self, power):
        """신강약 8단계 세분화 (가중치 지수 기반)"""
        if power <= 15: return "극약(極弱) - 실령, 실지, 실세 상태"
        elif power <= 30: return "태약(太弱)"
        elif power <= 43: return "신약(身弱)"
        elif power <= 49: return "중화신약(中和身弱)"
        elif power <= 56: return "중화신강(中和身强)"
        elif power <= 70: return "신강(身强)"
        elif power <= 85: return "태강(太强)"
        else: return "극왕(極旺) - 득령, 득지, 득세 상태"


    def _get_yongsin_info(self, palja, power, me_hj_hanja):
        """개선된 용신 분석: 억부, 조후, 종용신 통합"""
        # 1. 종격(종용신) 판별
        is_special = False
        if power <= 15 or power >= 85:
            is_special = True
            counts = {}
            for char in palja:
                elem = sc.ELEMENT_MAP[char]
                counts[elem] = counts.get(elem, 0) + 1
            strongest_elem = max(counts, key=counts.get)
            
            main_yongsin_name = f"{strongest_elem}(종용신)"
            needed_elements = [strongest_elem]
            eokbu_type = "전왕/종격 (강한 기운에 순응)"
        else:
            # 2. 일반적인 억부용신 로직
            targets = sc.STRONG_ENERGY if power <= 49 else sc.WEAK_ENERGY
            eokbu_type = "/".join(targets)
            needed_elements = [sc.HJ_TO_HG[hj] for hj in sc.HJ_ELEMENTS if sc.REL_MAP.get((me_hj_hanja, hj)) in targets]
            main_yongsin_name = f"{needed_elements[0]}(억부용신)"

        # 3. 실제 원국 내 존재 확인
        present_hj = set(sc.E_MAP_HJ[c] for c in palja)
        existing_yongsin = [sc.HJ_TO_HG[hj] for hj in present_hj if sc.HJ_TO_HG[hj] in needed_elements]
        
        # 4. 조후 분석 (출력 형식 수정 및 설명 문구 분리)
        mb = palja[3]
        johoo_name = ""
        johoo_desc = ""

        if mb in sc.WINTER_BS:
            johoo_name = "화(조후용신)"
            johoo_desc = "화(火) - 추운 계절이라 따뜻한 기운이 최우선입니다."
        elif mb in sc.SUMMER_BS:
            johoo_name = "수(조후용신)"
            johoo_desc = "수(水) - 더운 계절이라 시원한 기운이 최우선입니다."
        elif mb in sc.SPRING_BS:
            johoo_name = "화(조후용신)"
            johoo_desc = "화(火) - 만물이 성장하도록 온기가 필요합니다."
        elif mb in sc.AUTUMN_BS:
            johoo_name = "수(조후용신)"
            johoo_desc = "수(水) - 건조한 계절이라 적절한 수기가 필요합니다."

        return {
            "eokbu_elements": "/".join(needed_elements), 
            "main_yongsin": main_yongsin_name,  # 예: "토(억부용신)"
            "johoo_name": johoo_name,          # 예: "화(조후용신)"
            "johoo_desc": johoo_desc,          # 예: "화(火) - 추운 계절이라..."
            "actual_yongsin": "/".join(existing_yongsin) if existing_yongsin else "원국 내 없음",
            "eokbu_type": eokbu_type, 
            "is_special": is_special
        }
    
    def _get_ten_god(self, me, target, me_hj):

        """체용 변화가 적용된 FUNCTIONAL_POLARITY를 참조하여 십성을 계산합니다."""
        rel = sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[target]))

        print(f"me_hj:{me_hj}, rel:{rel}")
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
    def _calculate_daeun(self, dt_in, yG, mG, gender, l_term, n_term, me, me_hj):
        """대운수 및 상세 정보(이미지 스타일) 계산"""
        is_fwd = (gender == 'M' and sc.POLARITY_MAP[yG[0]] == '+') or (gender == 'F' and sc.POLARITY_MAP[yG[0]] == '-')
        target_term = n_term if is_fwd else l_term
        daeun_num = max(1, int(round(abs((target_term['dt_obj'] - dt_in).total_seconds() / 86400) / 3.0)))
        
        daeun_list = []
        curr_idx = self.SIXTY_GANZI.index(mG)
        
        # 이미지처럼 보통 10개 혹은 11개의 대운을 보여줍니다.
        for i in range(1, 11):
            curr_idx = (curr_idx + 1) % 60 if is_fwd else (curr_idx - 1) % 60
            ganzi = self.SIXTY_GANZI[curr_idx]
            g, j = ganzi[0], ganzi[1]
            
            daeun_list.append({
                "start_age": daeun_num + (i-1)*10,
                "ganzi": ganzi,
                "gan": g,
                "gan_kor": sc.B_KOR[g],
                "gan_elem": sc.ELEMENT_MAP[g],
                "t_gan": self._get_ten_god(me, g, me_hj), # 천간 십성
                "ji": j,
                "ji_kor": sc.B_KOR[j],
                "ji_elem": sc.ELEMENT_MAP[j],
                "t_ji": self._get_ten_god(me, j, me_hj), # 지지 십성
                "unseong": sc.UNSEONG_MAP.get(me, {}).get(j, "-"), # 12운성
            })
            
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
    # SajuEngine 클래스 내부에 추가
    def get_yeonun_only(self, birth_year, daeun_start_age, me_gan, me_hj):
        """
        특정 대운의 10년치 연운 데이터를 생성합니다. (누락 필드 보강)
        """
        yeonun_list = []
        start_year = int(birth_year) + int(daeun_start_age) - 1
        # [수정] 일간 한자(庚)를 오행 이름(金)으로 미리 변환
        me_elem = sc.E_MAP_HJ.get(me_hj)
        
        for i in range(10):
            target_year = start_year + i
            ganzi_idx = (target_year - 2023 + 39) % 60
            ganzi = self.SIXTY_GANZI[ganzi_idx]
            g, j = ganzi[0], ganzi[1]
            
            yeonun_list.append({
                "year": target_year,
                "ganzi": ganzi,             # 한자 원문 (예: '癸')
                "gan_kor": sc.B_KOR[g],      # 한글 (예: '계')
                "gan_elem": sc.ELEMENT_MAP[g],
                "t_gan": self._get_ten_god(me_gan, g, me_elem), # 천간 십성
                "ji": j,                    # 지지 한자 원문
                "ji_kor": sc.B_KOR[j],       # 지지 한글
                "ji_elem": sc.ELEMENT_MAP[j],
                "t_ji": self._get_ten_god(me_gan, j, me_elem), # 지지 십성
                "unseong": sc.UNSEONG_MAP.get(me_gan, {}).get(j, "-"), # 12운성
            })
            # debug_json = json.dumps(yeonun_list, indent=4, ensure_ascii=False, default=str)
            # print(f"\n>>> DEBUG REPORT:\n{debug_json}, -{g}, -{j}")
        return yeonun_list[::-1] # 최신 연도가 왼쪽으로 오게 정렬
    def get_wolun_only(self, target_year, me_gan, me_hj):
        """
        포스텔러 방식: 양력 1월(전년도 축월)부터 12월(당해년도 자월)까지 계산
        """
        wolun_list = []
        me_elem = sc.E_MAP_HJ.get(me_hj) # 일간 오행 (예: '金')
        target_year = int(target_year)

        # 1. 당해년도분 계산 (양력 2월 ~ 12월 = 사주 인월 ~ 자월)
        y_idx = (target_year - 2023 + 39) % 60
        y_stem = self.SIXTY_GANZI[y_idx][0]
        # 연두법 공식 적용
        start_stem_idx = (sc.STEMS.index(y_stem) * 2 + 2) % 10
        
        for i in range(11): # 인(寅)월부터 자(子)월까지 11개 달
            g = sc.STEMS[(start_stem_idx + i) % 10]
            j = sc.BRANCHES[(2 + i) % 12]
            wolun_list.append({
                "month": i + 2, # 양력 2월 ~ 12월로 라벨링
                "ganzi": g + j,
                "gan_kor": sc.B_KOR[g],
                "gan_elem": sc.ELEMENT_MAP[g],
                "t_gan": self._get_ten_god(me_gan, g, me_elem),
                "ji_kor": sc.B_KOR[j],
                "ji_elem": sc.ELEMENT_MAP[j],
                "t_ji": self._get_ten_god(me_gan, j, me_elem),
                "unseong": sc.UNSEONG_MAP.get(me_gan, {}).get(j, "-"),
            })

        # 2. 전년도분 계산 (양력 1월 = 사주 전년도 축월)
        y_prev_idx = (target_year - 1 - 2023 + 39) % 60
        y_prev_stem = self.SIXTY_GANZI[y_prev_idx][0]
        start_stem_prev_idx = (sc.STEMS.index(y_prev_stem) * 2 + 2) % 10
        
        g_jan = sc.STEMS[(start_stem_prev_idx + 11) % 10] # 12번째 달(축월)
        j_jan = sc.BRANCHES[(2 + 11) % 12] # 丑
        wolun_list.append({
            "month": 1, # 양력 1월로 라벨링
            "ganzi": g_jan + j_jan,
            "gan_kor": sc.B_KOR[g_jan],
            "gan_elem": sc.ELEMENT_MAP[g_jan],
            "t_gan": self._get_ten_god(me_gan, g_jan, me_elem),
            "ji_kor": sc.B_KOR[j_jan],
            "ji_elem": sc.ELEMENT_MAP[j_jan],
            "t_ji": self._get_ten_god(me_gan, j_jan, me_elem),
            "unseong": sc.UNSEONG_MAP.get(me_gan, {}).get(j_jan, "-"),
        })

        # [정렬] 12월부터 1월까지 내림차순 정렬 (오른쪽이 작은 숫자)
        return sorted(wolun_list, key=lambda x: x['month'], reverse=True)
    
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
        """
        인덱스를 년(0), 월(1), 일(2), 시(3) 순서로 고정하여 화면과 동기화합니다.
        양방향 체크 로직을 통해 딕셔너리 키 순서와 상관없이 모든 상호작용을 검출합니다.
        """
        res = {k: [] for k in sc.INTERACTION_KEYS}
        sl = [palja[0], palja[2], palja[4], palja[6]]
        bl = [palja[1], palja[3], palja[5], palja[7]]
        
        print(f"\n>>> DEBUG REPORT:\n sl: { sl }")
        print(f"\n>>> DEBUG REPORT:\n bl: { bl }")
        
        for i in range(4):
            for j in range(i + 1, 4):
                for key, mapping, target_type in sc.PAIRWISE_RULES:
                    target_list = sl if target_type == "stem" else bl
                    
                    # [수정 구간] 두 글자의 조합을 양방향으로 생성하여 체크합니다.
                    char1, char2 = target_list[i], target_list[j]
                    pair1 = char1 + char2
                    pair2 = char2 + char1
                    
                    # 정방향(pair1) 또는 역방향(pair2) 중 하나라도 매핑 테이블에 있는지 확인합니다.
                    if pair1 in mapping:
                        res[key].append({"name": mapping[pair1], "subs": [i, j]})
                    elif pair2 in mapping:
                        res[key].append({"name": mapping[pair2], "subs": [i, j]})
                        
        print(f"\n>>> DEBUG REPORT:\n bl : {bl} ,res : { res }")
        
        # 삼합/방합/삼형 등 그룹 단위 분석
        self._check_group_interactions(bl, res)
        
        # 공망 분석
        ilju_name = palja[4] + palja[5]
        g_jis = sc.GONGMANG_MAP[self.SIXTY_GANZI.index(ilju_name) // 10]
        
        print(f"\n>>> DEBUG REPORT:\n  bl2 : {bl} , res2 : { res }")
        print(f"\n>>> DEBUG REPORT:\n  ilju_name : {ilju_name} ")
        print(f"\n>>> DEBUG REPORT:\n  g_jis : {g_jis} ")
        
        for i, b in enumerate(bl):
            if b in g_jis: 
                res["공망"].append({"name": f"{sc.POSITIONS[i]} 공망({sc.B_KOR.get(b, b)})", "subs": [i]})

        # 결과값 중복 제거 및 가나다순 정렬
        unique_res = {}
        pos_names = ["년", "월", "일", "시"] # 위치 명칭 정의

        for k, v in res.items():
            # 1. 이름별로 그룹화하여 위치(subs)를 합침
            combined = {}
            for item in v:
                name = item["name"]
                if name not in combined:
                    combined[name] = set(item["subs"]) # set으로 중복 위치 방지
                else:
                    combined[name].update(item["subs"]) # 새로운 위치 인덱스 추가

            # 2. 합쳐진 위치를 바탕으로 표시용 이름 생성
            final_list = []
            for name, subs_set in combined.items():
                sorted_subs = sorted(list(subs_set)) # 인덱스 정렬 [0, 2, 3]
                
                # 위치 명칭 추출 (예: "년-일-시")
                loc_str = "-".join([pos_names[i] for i in sorted_subs])
                
                # 표시용 이름 결정: 2개 이상 중첩되면 위치를 병기함
                display_name = f"{name}({loc_str})" if len(sorted_subs) > 2 else name
                
                final_list.append({
                    "name": display_name,     # 화면 표시용 (예: 자묘형(년-일-시))
                    "pure_name": name,        # 순수 명칭 (해석 데이터 매칭용)
                    "subs": sorted_subs       # 하이라이트할 모든 인덱스 [0, 2, 3]
                })

            # 가나다순 정렬하여 저장
            unique_res[k] = sorted(final_list, key=lambda x: x["name"])
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
    
    def get_month_calendar(self, year, month):
        import calendar
        cal_data = []
        last_day = calendar.monthrange(year, month)[1]
        
        # 1. 해당 월의 첫날과 마지막 날 데이터를 가져옴
        first_info = self.m_db.get(f"{year}{month:02d}01")
        last_info = self.m_db.get(f"{year}{month:02d}{last_day:02d}")
        
        saju_header = ""
        if first_info and last_info:
            # [수정] 포스텔러 스타일: 연도는 마지막 날(새로운 기운)을 기준으로 하나만 표시
            # 2026년 2월의 경우, 마지막 날은 입춘 이후이므로 '병오년'으로 고정됩니다.
            y_final = f"{sc.B_KOR[last_info['yG'][0]]}{sc.B_KOR[last_info['yG'][1]]}"
            year_part = f"{y_final}년"
                
            # [월 범위] 월건은 기존처럼 범위로 표시 (절기 변화 강조)
            m_start = f"{sc.B_KOR[first_info['mG'][0]]}{sc.B_KOR[first_info['mG'][1]]}"
            m_end = f"{sc.B_KOR[last_info['mG'][0]]}{sc.B_KOR[last_info['mG'][1]]}"
            
            if m_start != m_end:
                month_part = f"{m_start}~{m_end}월" # 예: "기축~경인월"
            else:
                month_part = f"{m_start}월"
                
            # [최종 헤더] "병오년 기축~경인월"
            saju_header = f"{year_part} {month_part}"

        for day in range(1, last_day + 1):
            date_str = f"{year}{month:02d}{day:02d}"
            day_info = self.m_db.get(date_str)
            if day_info:
                dg = day_info['dG']
                term_name, term_time = "", ""
                year_terms = self.t_db.get(str(year), [])
                for t in year_terms:
                    if t['datetime'].startswith(f"{year}-{month:02d}-{day:02d}"):
                        term_name = t['term']
                        term_time = t['datetime'].split('T')[1]
                        break

                cal_data.append({
                    "day": day,
                    "ganzi_kor": f"{sc.B_KOR[dg[0]]}{sc.B_KOR[dg[1]]}",
                    "ganzi_hj": dg,
                    "lunar": f"{day_info['lm']}.{day_info['ld']}",
                    "term_name": term_name,
                    "term_time": term_time,
                    "is_today": (datetime.now().strftime("%Y%m%d") == date_str)
                })
        
        first_weekday = (calendar.monthrange(year, month)[0] + 1) % 7 
        return {
            "first_weekday": first_weekday, 
            "days": cal_data,
            "saju_header": saju_header # "을사년 정해~무자월" 형태
        }
    # ==========================================================================
    # 4. 메인 분석 엔진 (Main Analysis Orchestrator)
    # ==========================================================================
    def analyze(self, birth_str, gender, location, use_yajas_i, calendar_type="양력",use_hap_correction=False, use_johoo_correction=False):
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
        
        # 5. [수정] 시주 및 일주 결정 (경도 보정값 반영)
        h_idx = ((dt_solar.hour * 60 + dt_solar.minute + 60) // 120) % 12
        
        # [중요] 모든 기준 날짜를 보정된 dt_solar의 날짜로 고정합니다.
        solar_date_str = dt_solar.strftime("%Y%m%d")
        next_solar_date_str = (dt_solar + timedelta(days=1)).strftime("%Y%m%d")
        
        curr_day_data = self.m_db.get(solar_date_str)
        next_day_data = self.m_db.get(next_solar_date_str)

        if jasi == "YAJAS-I":
            # 야자시(23:00~): 날짜는 오늘(12/31), 시주 기준은 내일(1/1)
            target_dG = curr_day_data['dG'] if use_yajas_i else next_day_data['dG']
            ref_gan = next_day_data['dG'][0]
        else:
            # 조자시 포함 일반 시간: 날짜와 시주 기준 모두 현재 보정된 날짜
            target_dG = curr_day_data['dG']
            ref_gan = target_dG[0]

        # 최종 시주 천간 계산
        hG_gan = sc.STEMS[(sc.HG_START_IDX[ref_gan] + h_idx) % 10]
        
        # 6. [데이터 동기화] 8글자(palja) 구성
        palja = [yG[0], yG[1], mG[0], mG[1], target_dG[0], target_dG[1], hG_gan, sc.BRANCHES[h_idx]]
                
        # 7. 오행/신강약 분석
        me_hj = sc.E_MAP_HJ.get(palja[4]) 
         # 오행 분포(단순 개수)와 신강약 지수(가중치)를 각각 구함
        scores = self._get_element_distribution(palja,use_hap_correction)
        power = self._calculate_strength_score(palja, me_hj, use_hap_correction, use_johoo_correction)
        yongsin, pillars = self._get_yongsin_info(palja, power, me_hj), self._investigate_sinsal(palja, palja[4], me_hj)
        
        for p in pillars: 
            p['gan_elem'], p['ji_elem'] = sc.ELEMENT_MAP[p['gan']], sc.ELEMENT_MAP[p['ji']]
        
        # 8. 대운 계산
        l_term, n_term = self._get_solar_terms(dt_raw)
        daeun_num, daeun_list = self._calculate_daeun(dt_raw, yG, mG, gender, l_term, n_term, palja[4], me_hj)
        daeun_list = self._calculate_daeun_scores(daeun_list, yongsin, palja)
        
        # 9. 현재 운세(운로) 추적
        now = datetime.now()
        curr_age = now.year - dt_raw.year + 1
        # 현재 나이가 속한 대운 찾기
        current_daeun = next((d for d in daeun_list if d['start_age'] <= curr_age < d['start_age'] + 10), daeun_list[0])
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), "age": curr_age,
            "daeun": next((d for d in daeun_list if d['start_age'] <= curr_age < d['start_age'] + 10), daeun_list[0]),
            "seun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('yG', 'N/A'),
            "wolun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('mG', 'N/A'),
            "ilun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('dG', 'N/A')
        }
        # [추가] 초기 화면에 보여줄 연운 데이터 생성 (현재 대운 기준)
        initial_yeonun = self.get_yeonun_only(
            birth_year=dt_raw.year,
            daeun_start_age=current_daeun['start_age'],
            me_gan=palja[4],
            me_hj=palja[4] # me_hj 대신 me(palja[4])를 두 번 전달
        )
        initial_wolun = self.get_wolun_only(
            target_year=now.year,
            me_gan=palja[4],
            me_hj=palja[4]
        )

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
        
        #representative_elem = me_elem_name if me_elem_name in winners else winners[0]
        # 2. [신규 추가] 대표 성향(십성) 추출
        # tengod_dict에서 가장 count가 높은 십성 이름을 찾습니다.
        # 본인(비견) 세력이 강한 경우 '비견'이 대표 성향으로 잡히게 됩니다.
        # representative_tendency = max(tengod_dict, key=lambda k: (tengod_dict[k]['count'], k == "비견"))
      
        
        representative_elem = max(scores, key=scores.get)

        # 2. 대표 성향: 십성을 5개 그룹(비겁, 식상...)으로 합산 후 판정
        # (sc.TEN_GOD_GROUPS 상수가 정의되어 있다고 가정합니다)
        group_counts = {"비겁": 0, "식상": 0, "재성": 0, "관성": 0, "인성": 0}
        group_mapping = {
            "비견": "비겁", "겁재": "비겁", "본인": "비겁",
            "식신": "식상", "상관": "식상",
            "편재": "재성", "정재": "재성",
            "편관": "관성", "정관": "관성",
            "편인": "인성", "정인": "인성"
        }

        for p in pillars:
            group_counts[group_mapping.get(p['t_gan'], "비겁")] += 1
            group_counts[group_mapping.get(p['t_ji'], "비겁")] += 1

        # 가장 비중이 큰 그룹을 찾음 (예: 관성)
        representative_group_name = max(group_counts, key=group_counts.get)
        
        # 해당 그룹에 속하는 십성 중 원국에 가장 많은 것 선택
        group_to_tgs = {
            "비겁": ["비견", "겁재"], "식상": ["식신", "상관"],
            "재성": ["편재", "정재"], "관성": ["편관", "정관"], "인성": ["편인", "정인"]
        }
        target_tgs = group_to_tgs[representative_group_name]
        representative_tendency = max(target_tgs, key=lambda k: (tengod_dict.get(k, {'count': 0})['count']))
        



        
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
            "relation_groups" :relation_groups,
            "initial_yeonun": initial_yeonun,
            "initial_wolun": initial_wolun,
            "now_year": now.year,
            "now_month": now.month,
            "initial_calendar": self.get_month_calendar(now.year, now.month)  
        }
        
        # debug_json = json.dumps(final_result, indent=4, ensure_ascii=False, default=str)
        # print(f"\n>>> DEBUG REPORT:\n{debug_json}")

        return final_result