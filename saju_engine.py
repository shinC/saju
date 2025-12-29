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
            
        # 억부용신 오행 찾기 (한자로 검색)
        hj_elements = ['木', '火', '土', '金', '水']
        # 한자 결과를 한글로 변환하기 위한 매핑
        hj_to_hg = {'木': '목', '火': '화', '土': '토', '金': '금', '水': '수'}
        
        found_elements = []
        for target_hj in hj_elements:
            # (나의한자오행, 대상한자오행)으로 REL_MAP 검색
            rel = sc.REL_MAP.get((me_hj_hanja, target_hj))
            
            if rel and rel in targets:
                found_elements.append(hj_to_hg[target_hj]) # 결과는 한글로 저장
        
        if not found_elements:
            # 여기마저 실패하면 REL_MAP 구조 자체를 출력해봐야 합니다.
            print(f"⚠️ 경고: 용신 추출 실패 (입력값: {me_hj_hanja}, 타입: {eokbu_type})")
            found_elements = ["데이터 확인 필요"]
        
        # 2. 조후 용신 (기존 유지)
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

    def analyze(self, birth_str, gender, location='서울', use_yajas_i=True):
        """메인 분석 오케스트레이터 v1.5 (억부/조후 용신 상세 분석 포함)"""
        dt_raw = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        hist_offset = self._get_historical_correction(dt_raw)
        dt_ref = dt_raw + timedelta(minutes=hist_offset)
        eot_offset = self._get_equation_of_time(dt_ref)
        lng_offset = (sc.CITY_DATA.get(location, 126.97) - 135) * 4
        dt_true_solar = dt_ref + timedelta(minutes=lng_offset + eot_offset)
        
        jasi_type = self._get_jasi_type(dt_true_solar)
        
        fetch_dt = dt_true_solar
        if not use_yajas_i and jasi_type == "YAJAS-I":
            fetch_dt = dt_true_solar + timedelta(hours=2)
            
        day_key = fetch_dt.strftime("%Y%m%d")
        day_data = self.m_db.get(day_key)
        if not day_data: return {"error": f"Data not found for {day_key}"}
        
        yG, mG, dG = day_data['yG'], day_data['mG'], day_data['dG']
        yG, mG = self._apply_solar_correction(dt_raw, yG, mG)
        
        # dG[0]는 '甲', '乙' 같은 일간 한자입니다.
        me = dG[0] # '甲' 등
        me_hj_hangeul = sc.ELEMENT_MAP.get(me) # '목'
        me_hj_hanja = sc.E_MAP_HJ.get(me)      # '木'
        
        h_idx = ((dt_true_solar.hour * 60 + dt_true_solar.minute + 60) // 120) % 12
        target_dG_for_hour = dG
        if use_yajas_i and jasi_type == "YAJAS-I":
            next_day_key = (dt_true_solar + timedelta(hours=2)).strftime("%Y%m%d")
            next_day_data = self.m_db.get(next_day_key)
            if next_day_data: target_dG_for_hour = next_day_data['dG']
        
        hG_gan = sc.STEMS[({ '甲':0,'己':0,'乙':2,'庚':2,'丙':4,'辛':4,'丁':6,'壬':6,'戊':8,'癸':8 }[target_dG_for_hour[0]] + h_idx) % 10]
        hG = hG_gan + sc.BRANCHES[h_idx]
        
        palja = [yG[0], yG[1], mG[0], mG[1], dG[0], dG[1], hG[0], hG[1]]
        
        # [데이터 연산] 신강약 및 상세 용신 판별
        scores, power = self._calculate_power(palja, me_hj_hanja)
        detailed_status = self._get_detailed_status(power)
        
        # [신규 추가] 용신 정보 상세 추출
        yongsin_info = self._get_yongsin_info(palja, power, me_hj_hanja)
        
        pillars = self._investigate_sinsal(palja, me, me_hj_hanja)
        l_term, n_term = self._get_solar_terms(dt_raw)
        daeun_num, daeun_list = self._calculate_daeun(dt_raw, yG, mG, gender, l_term, n_term)

        now = datetime.now()
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), "age": now.year - dt_raw.year + 1,
            "daeun": next((d for d in daeun_list if d['start_age'] <= (now.year - dt_raw.year + 1) < d['start_age'] + 10), daeun_list[0]),
            "seun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('yG', 'N/A'),
            "wolun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('mG', 'N/A'),
            "ilun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('dG', 'N/A')
        }

        return {
            "birth": birth_str, 
            "gender": gender, 
            "pillars": pillars, 
            "me": me, 
            "me_elem": sc.ELEMENT_MAP[me],
            "scores": scores, 
            "power": power, 
            "status": detailed_status,
            "yongsin_detail": { # [v1.5 핵심] 가공된 용신 데이터
                "eokbu_elements": yongsin_info['eokbu_elements'],
                "eokbu_type": yongsin_info['eokbu_type'],
                "johoo": yongsin_info['johoo']
            },
            "daeun_num": daeun_num, 
            "daeun_list": daeun_list, 
            "current_trace": current_trace,
            "jasi_type": jasi_type
        }