import json
import os

class FortuneBridge:
    # [작업 2] 행운의 아이템 매핑 데이터 (클래스 상수로 관리)
    LUCKY_MAP = {
        "목": {"color": "초록색", "number": "3, 8", "direction": "동쪽", "item": "식물, 나무 액세서리"},
        "화": {"color": "빨간색", "number": "2, 7", "direction": "남쪽", "item": "조명, 화려한 소품"},
        "토": {"color": "노란색", "number": "5, 0", "direction": "중앙", "item": "도자기, 황토 제품"},
        "금": {"color": "흰색", "number": "4, 9", "direction": "서쪽", "item": "금속 시계, 반지"},
        "수": {"color": "검정색", "number": "1, 6", "direction": "북쪽", "item": "수족관, 물 관련 소품"}
    }

    def __init__(self, data_path='data/ilju_data.json'):
        # JSON 데이터 로드 및 에러 핸들링
        if os.path.exists(data_path):
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    self.ilju_master = json.load(f)['ILJU_DATA']
            except Exception as e:
                print(f"⚠️ 데이터 로드 에러: {e}")
                self.ilju_master = {}
        else:
            print(f"⚠️ 경고: {data_path} 파일을 찾을 수 없습니다.")
            self.ilju_master = {}

    def get_ilju_report(self, ilju_ganzi):
        """일주 데이터를 기반으로 성격 리포트 생성"""
        data = self.ilju_master.get(ilju_ganzi)
        
        # 데이터가 없을 경우를 대비해 동일한 구조의 '기본값' 딕셔너리 반환 (TypeError 방지)
        if not data:
            return {
                "title": "미지의 탐구자",
                "mbti": "None",
                "tags": ["신비로움", "알 수 없음"],
                "description": f"({ilju_ganzi})에 해당하는 일주 분석 데이터를 찾을 수 없습니다."
            }
        
        return {
            "title": data.get('title', '정보 없음'),
            "mbti": data.get('mbti', 'N/A'),
            "tags": data.get('keyword', []),
            "description": data.get('desc', '상세 설명이 없습니다.')
        }

    def get_lucky_report(self, yongsin_elem):
        """
        [작업 2 구현] 용신 오행을 기반으로 행운 리포트 생성
        yongsin_elem: 엔진에서 전달된 '목/화' 또는 '금' 형태의 문자열
        """
        if not yongsin_elem:
            return self._get_default_lucky()

        # '목/화'와 같이 여러 개인 경우 첫 번째를 주 용신으로 판단
        main_elem = yongsin_elem.split('/')[0] if '/' in yongsin_elem else yongsin_elem
        
        lucky_data = self.LUCKY_MAP.get(main_elem)
        if not lucky_data:
            return self._get_default_lucky()
            
        return lucky_data

    def _get_default_lucky(self):
        """매핑 실패 시 반환할 기본 행운 데이터"""
        return {
            "color": "무지개색",
            "number": "모든 숫자",
            "direction": "사방팔방",
            "item": "자신감과 긍정적인 마음"
        }