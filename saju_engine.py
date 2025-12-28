import json
from datetime import datetime, timedelta
import saju_constants as sc

class SajuEngine:
    """
    v1.0: 절기 정밀 교정 버전 (Priority 1 해결)
    - [수정] analyze: 절입 시각(분 단위) 비교를 통한 연주(yG) 및 월주(mG) 강제 교정 로직 추가
    - [추가] _apply_solar_correction: transition day(절기 당일) 시각 비교 및 간지 시프트(Shift) 처리
    """
    def __init__(self, m_file, t_file):
        with open(m_file, 'r', encoding='utf-8') as f: self.m_db = json.load(f)
        with open(t_file, 'r', encoding='utf-8') as f: self.t_db = json.load(f)
        self.SIXTY_GANZI = [f"{sc.STEMS[i%10]}{sc.BRANCHES[i%12]}" for i in range(60)]

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
        """
        [Priority 1 해결] 절기 시각 정밀 교정
        - manse_data.json(m_db)은 날짜 단위이므로, 절기 당일 오전/오후 오차를 잡기 위해 
          태어난 시각과 실제 절입 시각(t_db)을 비교하여 간지를 보정합니다.
        """
        today_str = dt_in.strftime("%Y%m%d")
        year_str = str(dt_in.year)
        
        # 오늘 날짜에 해당하는 절기(월 변경 절기)가 있는지 확인
        term_today = next((t for t in self.t_db.get(year_str, []) 
                          if t['date'] == today_str and t['isMonthChange']), None)
        
        if term_today:
            term_dt = datetime.strptime(term_today['datetime'], "%Y-%m-%dT%H:%M")
            # 태어난 시각이 절기 시각보다 이전이라면, m_db의 '이미 바뀐 간지'를 이전으로 되돌림
            if dt_in < term_dt:
                # 1. 월주(mG) 시프트 백
                m_idx = self.SIXTY_GANZI.index(mG)
                mG = self.SIXTY_GANZI[(m_idx - 1) % 60]
                
                # 2. 만약 해당 절기가 '입춘(1월)'이라면 연주(yG)도 이전 해로 시프트 백
                if term_today['monthIndex'] == 1:
                    y_idx = self.SIXTY_GANZI.index(yG)
                    yG = self.SIXTY_GANZI[(y_idx - 1) % 60]
        
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
        """메인 분석 오케스트레이터 - 정밀 절기 교정 버전"""
        dt_in = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        # 시주(時柱) 계산을 위한 표준시/경도 보정 시각
        dt_std = dt_in + timedelta(minutes=(sc.CITY_DATA.get(location, 126.97) - 135) * 4)
        
        # 0. 절기 데이터 확보
        l_term, n_term = self._get_solar_terms(dt_in)
        
        # m_db에서 기본 날짜 데이터 로드
        day_key = dt_in.strftime("%Y%m%d")
        if day_key not in self.m_db: return {"error": "Data not found"}
        day_data = self.m_db[day_key]
        
        yG, mG, dG = day_data['yG'], day_data['mG'], day_data['dG']
        
        # [Priority 1 해결] 절기 당일 시각 비교를 통한 연주/월주 강제 교정
        yG, mG = self._apply_solar_correction(dt_in, yG, mG)
        
        # 나를 나타내는 일간(me) 확정
        me, me_hj = dG[0], sc.E_MAP_HJ[dG[0]]
        
        # 시주(hG) 계산 (dt_std 기준)
        h_idx = ((dt_std.hour * 60 + dt_std.minute + 60) // 120) % 12
        hG_gan = sc.STEMS[({ '甲':0,'己':0,'乙':2,'庚':2,'丙':4,'辛':4,'丁':6,'壬':6,'戊':8,'癸':8 }[dG[0]] + h_idx) % 10]
        hG = hG_gan + sc.BRANCHES[h_idx]
        
        palja = [yG[0], yG[1], mG[0], mG[1], dG[0], dG[1], hG[0], hG[1]]

        # 1. 신강약/오행 점수
        scores, power = self._calculate_power(palja, me_hj)
        # 2. 신살 조사
        pillars = self._investigate_sinsal(palja, me, me_hj)
        # 3. 대운 계산
        daeun_num, daeun_list = self._calculate_daeun(dt_in, yG, mG, gender, l_term, n_term)

        # 실시간 현재 운세
        now = datetime.now()
        current_age = now.year - dt_in.year + 1
        curr_daeun = next((d for d in daeun_list if d['start_age'] <= current_age < d['start_age'] + 10), daeun_list[0])
        today_info = self.m_db.get(now.strftime("%Y%m%d"), {"yG": "N/A", "mG": "N/A", "dG": "N/A"})
        
        current_trace = {
            "date": now.strftime("%Y-%m-%d"), "age": current_age, "daeun": curr_daeun,
            "seun": today_info['yG'], "wolun": today_info['mG'], "ilun": today_info['dG']
        }

        return {
            "birth": birth_str, "gender": gender, "pillars": pillars, "me": me, "me_elem": sc.ELEMENT_MAP[me],
            "scores": scores, "power": power, "status": "신강" if power > 45 else "신약",
            "yongsin": "인성/비겁" if power <= 45 else "식상/재성/관성", 
            "daeun_num": daeun_num, "daeun_list": daeun_list,
            "current_trace": current_trace
        }