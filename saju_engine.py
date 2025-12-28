import json
from datetime import datetime, timedelta
import saju_constants as sc

class SajuEngine:
    """
    v31.0: 기능별 메소드 분리 리팩토링 버전
    - [분리] _get_solar_terms: 절기 데이터 정밀 연산
    - [분리] _calculate_power: 가중치 기반 신강약 및 오행 점수
    - [분리] _investigate_sinsal: 12신살 및 20종 프리미엄 신살
    - [분리] _calculate_daeun: 대운수 및 100세 대운 경로
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

    def _calculate_power(self, palja, me_hj):
        """[1. 가중치 기반 신강약] 로직 분리"""
        scores = {'목': 0.0, '화': 0.0, '토': 0.0, '금': 0.0, '수': 0.0}
        power = 0
        # 가중치: 월지(30), 일지(15), 나머지(각 11)
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
        """메인 분석 오케스트레이터 - 실시간 현재 운세 반영 버전"""
        dt_in = datetime.strptime(birth_str, "%Y-%m-%d %H:%M")
        dt_std = dt_in + timedelta(minutes=(sc.CITY_DATA.get(location, 126.97) - 135) * 4)
        
        # 0. 절기 연산 메소드 호출
        l_term, n_term = self._get_solar_terms(dt_in)
        
        # 기본 데이터 세팅
        day_data = self.m_db[dt_std.strftime("%Y%m%d")]
        yG, mG, dG = day_data['yG'], day_data['mG'], day_data['dG']
        me, me_hj = dG[0], sc.E_MAP_HJ[dG[0]]
        
        h_idx = ((dt_std.hour * 60 + dt_std.minute + 60) // 120) % 12
        hG_gan = sc.STEMS[({ '甲':0,'己':0,'乙':2,'庚':2,'丙':4,'辛':4,'丁':6,'壬':6,'戊':8,'癸':8 }[dG[0]] + h_idx) % 10]
        hG = hG_gan + sc.BRANCHES[h_idx]
        palja = [yG[0], yG[1], mG[0], mG[1], dG[0], dG[1], hG[0], hG[1]]

        # 1. 신강약 연산 메소드 호출
        scores, power = self._calculate_power(palja, me_hj)

        # 2. 신살 전수 조사 메소드 호출
        pillars = self._investigate_sinsal(palja, me, me_hj)

        # 3. 대운수 연산 메소드 호출
        daeun_num, daeun_list = self._calculate_daeun(dt_in, yG, mG, gender, l_term, n_term)

        # --- 실시간 현재 운세(current_trace) 계산 로직 시작 ---
        now = datetime.now()
        current_age = now.year - dt_in.year + 1
        
        # 현재 나이에 맞는 대운 찾기
        curr_daeun = next((d for d in daeun_list if d['start_age'] <= current_age < d['start_age'] + 10), daeun_list[0])
        
        # 오늘 날짜의 간지 정보 가져오기 (m_db 참조)
        today_key = now.strftime("%Y%m%d")
        today_info = self.m_db.get(today_key, {"yG": "N/A", "mG": "N/A", "dG": "N/A"})
        
        current_trace = {
            "date": now.strftime("%Y-%m-%d"),
            "age": current_age,
            "daeun": curr_daeun,
            "seun": today_info['yG'],
            "wolun": today_info['mG'],
            "ilun": today_info['dG']
        }
        # --- 실시간 현재 운세 계산 로직 종료 ---

        return {
            "birth": birth_str, "gender": gender, "pillars": pillars, "me": me, "me_elem": sc.ELEMENT_MAP[me],
            "scores": scores, "power": power, "status": "신강" if power > 45 else "신약",
            "yongsin": "인성/비겁" if power <= 45 else "식상/재성/관성", 
            "daeun_num": daeun_num, "daeun_list": daeun_list,
            "current_trace": current_trace
        }