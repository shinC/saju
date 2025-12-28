import json
from datetime import datetime, timedelta
import saju_constants as sc

class SajuEngine:
    """
    v1.1: 역사적 표준시 및 서머타임 보정 버전 (Priority 2 해결)
    - [추가] _get_historical_correction: 대한민국 표준시 변천사 및 서머타임 정밀 보정
    - [수정] analyze: 보정된 표준시(Standard Reference)를 적용하여 시주 및 절기 비교 정밀화
    """
    def __init__(self, m_file, t_file):
        with open(m_file, 'r', encoding='utf-8') as f: self.m_db = json.load(f)
        with open(t_file, 'r', encoding='utf-8') as f: self.t_db = json.load(f)
        self.SIXTY_GANZI = [f"{sc.STEMS[i%10]}{sc.BRANCHES[i%12]}" for i in range(60)]

    def _get_historical_correction(self, dt):
        """
        [Priority 2 해결] 역사적 표준시 및 서머타임 보정 로직
        - 127.5도(UTC+8.5) 사용기: 현재 기준(UTC+9)보다 30분 느림 -> +30분 보정
        - 서머타임 사용기: 현재 기준보다 1시간 빠름 -> -60분 보정
        """
        offset = 0
        ts = dt.strftime("%Y%m%d%H%M")
        
        # 1. 대한민국 표준시 변천사 (127.5도 사용 기간: +30분)
        # 1908.04.01 00:00 ~ 1911.12.31 23:59
        if "190804010000" <= ts <= "191112312359":
            offset += 30
        # 1954.03.21 00:00 ~ 1961.08.09 23:59
        elif "195403210000" <= ts <= "196108092359":
            offset += 30
            
        # 2. 서머타임 실시 기간 (-60분)
        # 주요 기간만 수록 (정밀 데이터 기반)
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

    def _get_solar_terms(self, dt_in):
        """[절기 연산] 로직 분리"""
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
        """[Priority 1 해결] 절기 시각 정밀 교정 (v1.0 유지)"""
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
        """[1. 가중치 기반 신강약] 로직 분리"""
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
        """[2. 신살 전수 조사] 로직 분리"""
        sinsal_start_idx = sc.BRANCHES.find(sc.SAMHAP_START_MAP[palja[1]])
        pillars = []
        for i in range(4):
            g, j = palja[i*2], palja[i*2+1]
            offset = (sc.BRANCHES.find(j) - sinsal_start_idx) % 12
            s_12 = sc.SINSAL_12_NAMES[offset]
            special = []
            if s_12 in ["화개살", "도화살", "역마살"]: special.append(s_12)
            if g in sc.HYEONCHIM_CHARS or j in sc.HYEONCHIM_CHARS: special.append("현침살")
            if (g+j) in sc.BAEKHO_LIST: special.append("백호대살")
            if j in sc.TAEGEUK_MAP.get(me, []): special.append("태극귀인")
            if j == sc.HAKGWAN_MAP.get(me): special.append("관귀학관")
            if j == sc.HONGYEOM_MAP.get(me): special.append("홍염살")
            if j == sc.JEONGROK_MAP.get(me): special.append("정록(록신)")
            if j in sc.CHEONEUL_MAP.get(me, []): special.append("천을귀인")
            t_gan = "본인" if i==2 else sc.TEN_GODS_MAP.get((sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[g])), sc.POLARITY_MAP[me]==sc.POLARITY_MAP[g]), "-")
            t_ji = sc.TEN_GODS_MAP.get((sc.REL_MAP.get((me_hj, sc.E_MAP_HJ[j])), sc.POLARITY_MAP[me]==sc.POLARITY_MAP[j]), "-")
            pillars.append({
                "gan": g, "ji": j, "t_gan": t_gan, "t_ji": t_ji, 
                "sinsal_12": s_12, "special": sorted(list(set(special)))
            })
        return pillars

    def _calculate_daeun(self, dt_in, yG, mG, gender, l_term, n_term):
        """[3. 대운수 및 경로 계산] 로직 분리"""
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

    def analyze(self, birth_str, gender, location='서울'):
        """메인 분석 오케스트레이터 - 시차 및 서머타임 보정 버전"""
        dt_raw = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        
        # [Priority 2 해결] 표준시 변천사 + 서머타임 통합 보정값 계산
        hist_offset = self._get_historical_correction(dt_raw)
        
        # 엔진의 내부 기준(UTC+9, 135도)과 입력 시각의 시차를 보정한 '기준 시각' 산출
        dt_ref = dt_raw + timedelta(minutes=hist_offset)
        
        day_key = dt_ref.strftime("%Y%m%d")
        
        # [추가] 디버깅 로그: 실제로 JSON에서 찾는 키가 무엇인지 확인
        print(f"디버깅 - 입력시각: {birth_str}")
        print(f"디버깅 - 보정시각: {dt_ref}")
        print(f"디버깅 - 찾을 날짜(Key): {day_key}")
        
        day_data = self.m_db.get(day_key)
        print(f"디버깅 - 가져온 데이터: {day_data}")

        # 경도 시차 보정 (평균 태양시 산출)
        lng_offset = (sc.CITY_DATA.get(location, 126.97) - 135) * 4
        dt_std = dt_ref + timedelta(minutes=lng_offset)
        
        # 0. 절기 데이터 확보 (보정 전 시각 기준으로 절기 시각과 비교)
        l_term, n_term = self._get_solar_terms(dt_raw)
        
        # m_db에서 기준 시각(dt_ref)에 해당하는 날짜의 간지 로드
        day_key = dt_ref.strftime("%Y%m%d")
        day_data = self.m_db.get(day_key)
        if not day_data: return {"error": f"Data not found for {day_key}"}
        
        yG, mG, dG = day_data['yG'], day_data['mG'], day_data['dG']
        
        # [Priority 1] 절기 당일 시각 비교를 통한 연주/월주 강제 교정 (보정 전 시각 기준)
        yG, mG = self._apply_solar_correction(dt_raw, yG, mG)
        
        me, me_hj = dG[0], sc.E_MAP_HJ[dG[0]]
        
        # 시주(hG) 계산 (모든 보정이 끝난 dt_std 기준)
        h_idx = ((dt_std.hour * 60 + dt_std.minute + 60) // 120) % 12
        hG_gan = sc.STEMS[({ '甲':0,'己':0,'乙':2,'庚':2,'丙':4,'辛':4,'丁':6,'壬':6,'戊':8,'癸':8 }[dG[0]] + h_idx) % 10]
        hG = hG_gan + sc.BRANCHES[h_idx]
        
        palja = [yG[0], yG[1], mG[0], mG[1], dG[0], dG[1], hG[0], hG[1]]

        # 1. 신강약/오행 점수 / 2. 신살 조사 / 3. 대운 계산
        scores, power = self._calculate_power(palja, me_hj)
        pillars = self._investigate_sinsal(palja, me, me_hj)
        daeun_num, daeun_list = self._calculate_daeun(dt_raw, yG, mG, gender, l_term, n_term)

        # 실시간 현재 운세 및 리턴 데이터 (생략된 부분 v1.0과 동일)
        now = datetime.now()
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), "age": now.year - dt_raw.year + 1,
            "daeun": next((d for d in daeun_list if d['start_age'] <= (now.year - dt_raw.year + 1) < d['start_age'] + 10), daeun_list[0]),
            "seun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('yG', 'N/A'),
            "wolun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('mG', 'N/A'),
            "ilun": self.m_db.get(now.strftime("%Y%m%d"), {}).get('dG', 'N/A')
        }

        return {
            "birth": birth_str, "gender": gender, "pillars": pillars, "me": me, "me_elem": sc.ELEMENT_MAP[me],
            "scores": scores, "power": power, "status": "신강" if power > 45 else "신약",
            "yongsin": "인성/비겁" if power <= 45 else "식상/재성/관성", 
            "daeun_num": daeun_num, "daeun_list": daeun_list, "current_trace": current_trace
        }