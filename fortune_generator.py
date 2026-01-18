"""
Fortune Generator (운세 생성기)
사주 분석 결과를 바탕으로 오늘의 운세를 생성하는 메인 클래스

설계 원칙:
1. 사주 전문용어 노출 금지 - 내부 로직에서만 사용
2. 풍부한 표현 - 같은 내용이 반복되지 않도록 템플릿 조합
3. 일관성 - 같은 생년월일 + 같은 날짜 = 같은 결과 (시드 고정)
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 템플릿 임포트
from fortune_templates.overall import (
    OVERALL_EXCELLENT, OVERALL_GOOD, OVERALL_AVERAGE, OVERALL_CAUTION, OVERALL_DIFFICULT,
    UNSEONG_ENERGY, SPECIAL_HARMONY, SPECIAL_CONFLICT, SPECIAL_PUNISHMENT,
    SEASON_MOOD, WEEKDAY_SPECIAL
)
from fortune_templates.study import (
    STUDY_EXCELLENT, STUDY_GOOD, STUDY_AVERAGE, STUDY_CAUTION, STUDY_DIFFICULT,
    STUDY_BY_SIBSUNG, STUDY_SITUATION
)
from fortune_templates.wealth import (
    WEALTH_EXCELLENT, WEALTH_GOOD, WEALTH_AVERAGE, WEALTH_CAUTION, WEALTH_DIFFICULT,
    WEALTH_BY_SIBSUNG, WEALTH_SITUATION
)
from fortune_templates.love import (
    LOVE_SINGLE_EXCELLENT, LOVE_SINGLE_GOOD, LOVE_SINGLE_AVERAGE, LOVE_SINGLE_CAUTION, LOVE_SINGLE_DIFFICULT,
    LOVE_COUPLE_EXCELLENT, LOVE_COUPLE_GOOD, LOVE_COUPLE_AVERAGE, LOVE_COUPLE_CAUTION, LOVE_COUPLE_DIFFICULT,
    LOVE_BY_SIBSUNG
)
from fortune_templates.marriage import (
    MARRIAGE_SINGLE_EXCELLENT, MARRIAGE_SINGLE_GOOD, MARRIAGE_SINGLE_AVERAGE, MARRIAGE_SINGLE_CAUTION, MARRIAGE_SINGLE_DIFFICULT,
    MARRIAGE_MARRIED_EXCELLENT, MARRIAGE_MARRIED_GOOD, MARRIAGE_MARRIED_AVERAGE, MARRIAGE_MARRIED_CAUTION, MARRIAGE_MARRIED_DIFFICULT,
    MARRIAGE_BY_SIBSUNG
)
from fortune_templates.career import (
    CAREER_EXCELLENT, CAREER_GOOD, CAREER_AVERAGE, CAREER_CAUTION, CAREER_DIFFICULT,
    CAREER_BY_SIBSUNG, CAREER_SITUATION
)
from fortune_templates.business import (
    BUSINESS_EXCELLENT, BUSINESS_GOOD, BUSINESS_AVERAGE, BUSINESS_CAUTION, BUSINESS_DIFFICULT,
    BUSINESS_BY_SIBSUNG, BUSINESS_SITUATION
)
from fortune_templates.health import (
    HEALTH_EXCELLENT, HEALTH_GOOD, HEALTH_AVERAGE, HEALTH_CAUTION, HEALTH_DIFFICULT,
    HEALTH_BY_ELEMENT, HEALTH_BY_UNSEONG, HEALTH_BY_SEASON, HEALTH_BY_AGE, HEALTH_SPECIAL
)
from fortune_templates.common import (
    GREETINGS, CLOSINGS, LUCKY_COLORS, LUCKY_NUMBERS, LUCKY_DIRECTIONS,
    LUCKY_FOODS, LUCKY_ACTIVITIES, TIME_ADVICE, WEEKDAY_TRAITS, MONTHLY_TRAITS
)


class FortuneGenerator:
    """
    사주 분석 결과를 바탕으로 오늘의 운세를 생성하는 클래스
    
    주요 기능:
    - 일간/월운/세운과 사주 원국의 상호작용 분석
    - 점수 기반 템플릿 선택
    - 시드 기반 일관된 결과 생성
    """
    
    # 오행 상생상극 관계
    ELEMENT_GENERATE = {  # 상생 (나를 생하는, 내가 생하는)
        "목": ("수", "화"), "화": ("목", "토"), "토": ("화", "금"),
        "금": ("토", "수"), "수": ("금", "목")
    }
    ELEMENT_CONTROL = {  # 상극 (나를 극하는, 내가 극하는)
        "목": ("금", "토"), "화": ("수", "금"), "토": ("목", "수"),
        "금": ("화", "목"), "수": ("토", "화")
    }
    
    # 십성 그룹
    SIBSUNG_GROUPS = {
        "비겁": ["비견", "겁재", "본인"],
        "식상": ["식신", "상관"],
        "재성": ["편재", "정재"],
        "관성": ["편관", "정관"],
        "인성": ["편인", "정인"]
    }
    
    # 요일 한글 매핑
    WEEKDAYS_KO = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    
    # 계절 판별
    SEASONS = {
        (3, 4, 5): "봄",
        (6, 7, 8): "여름",
        (9, 10, 11): "가을",
        (12, 1, 2): "겨울"
    }
    
    def __init__(self, fortune_bridge=None):
        """
        Args:
            fortune_bridge: FortuneBridge 인스턴스 (행운 아이템용)
        """
        self.fortune_bridge = fortune_bridge
    
    def generate_daily_fortune(
        self,
        analysis: Dict[str, Any],
        target_date: datetime = None,
        name: str = "회원",
        relationship_status: str = "single",  # "single" or "couple"
        marriage_status: str = "single",  # "single" or "married"
        age_group: str = None  # "청년", "중년", "장년", "노년"
    ) -> Dict[str, Any]:
        """
        오늘의 운세를 생성합니다.
        
        Args:
            analysis: saju_engine.analyze() 반환값
            target_date: 운세를 볼 날짜 (기본값: 오늘)
            name: 사용자 이름
            relationship_status: 연애 상태 (single/couple)
            marriage_status: 결혼 상태 (single/married)
            age_group: 연령대 (자동 계산 가능)
            
        Returns:
            운세 결과 딕셔너리
        """
        if "error" in analysis:
            return {"error": analysis["error"]}
        
        target_date = target_date or datetime.now()
        
        # 시드 생성 (같은 사람 + 같은 날짜 = 같은 결과)
        seed = self._generate_seed(analysis["birth"], target_date)
        random.seed(seed)
        
        # 기본 정보 추출
        me_elem = analysis.get("me_elem", "목")
        pillars = analysis.get("pillars", [])
        power = analysis.get("power", 50)
        interactions = analysis.get("interactions", {})
        yongsin = analysis.get("yongsin_detail", {})
        current_trace = analysis.get("current_trace", {})
        
        # 연령대 자동 계산
        if not age_group:
            age = current_trace.get("age", 30)
            age_group = self._get_age_group(age)
        
        # 계절 판별
        season = self._get_season(target_date.month)
        
        # 요일 정보
        weekday = self.WEEKDAYS_KO[target_date.weekday()]
        
        # 일운 정보 추출 (오늘의 간지)
        daily_pillar = current_trace.get("ilun", "甲子")
        daily_gan = daily_pillar[0] if daily_pillar else "甲"
        daily_ji = daily_pillar[1] if len(daily_pillar) > 1 else "子"
        
        # 점수 계산
        scores = self._calculate_all_scores(analysis, daily_pillar, target_date)
        
        # 대표 십성 추출 (일운 기준)
        dominant_sibsung = self._get_dominant_sibsung(pillars)
        
        # 각 영역별 운세 생성
        result = {
            "date": target_date.strftime("%Y년 %m월 %d일") + f" {weekday}",
            "name": name,
            "overall_score": scores["overall"],
            "greeting": self._select_greeting(target_date.hour),
            "overall": self._generate_overall(scores["overall"], interactions, season, weekday),
            "study": self._generate_study(scores["study"], dominant_sibsung),
            "wealth": self._generate_wealth(scores["wealth"], dominant_sibsung, yongsin),
            "love": self._generate_love(scores["love"], dominant_sibsung, relationship_status),
            "marriage": self._generate_marriage(scores["marriage"], dominant_sibsung, marriage_status),
            "career": self._generate_career(scores["career"], dominant_sibsung),
            "business": self._generate_business(scores["business"], dominant_sibsung),
            "health": self._generate_health(scores["health"], me_elem, season, age_group, interactions),
            "lucky": self._generate_lucky_items(yongsin, target_date),
            "time_advice": self._select_time_advice(target_date.hour),
            "closing": self._select_closing(scores["overall"]),
            "scores": scores
        }
        
        # 시드 리셋
        random.seed()
        
        return result
    
    def _generate_seed(self, birth_str: str, target_date: datetime) -> int:
        """동일한 입력에 대해 동일한 시드 생성"""
        seed_string = f"{birth_str}_{target_date.strftime('%Y%m%d')}"
        return int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)
    
    def _get_age_group(self, age: int) -> str:
        """나이에 따른 연령대 반환"""
        if age < 35:
            return "청년"
        elif age < 50:
            return "중년"
        elif age < 65:
            return "장년"
        else:
            return "노년"
    
    def _get_season(self, month: int) -> str:
        """월에 따른 계절 반환"""
        for months, season in self.SEASONS.items():
            if month in months:
                return season
        return "봄"
    
    def _calculate_all_scores(
        self, 
        analysis: Dict, 
        daily_pillar: str,
        target_date: datetime
    ) -> Dict[str, int]:
        """모든 영역의 점수를 계산합니다."""
        base_score = 50
        
        # 신강/신약에 따른 기본 점수 조정
        power = analysis.get("power", 50)
        if 45 <= power <= 55:
            base_score += 10  # 중화에 가까우면 기본 운이 좋음
        
        # 일운과의 상호작용 분석
        me = analysis.get("me", "甲")
        interactions = analysis.get("interactions", {})
        
        # 합/충/형에 따른 점수 조정
        has_hap = bool(interactions.get("합", []))
        has_chung = bool(interactions.get("충", []))
        has_hyung = bool(interactions.get("형", []))
        has_gongmang = bool(interactions.get("공망", []))
        
        # 점수 조정
        adjustment = 0
        if has_hap:
            adjustment += random.randint(5, 15)
        if has_chung:
            adjustment -= random.randint(10, 20)
        if has_hyung:
            adjustment -= random.randint(5, 15)
        if has_gongmang:
            adjustment -= random.randint(3, 8)
        
        # 날짜 기반 변동 (약간의 랜덤성)
        day_variation = random.randint(-10, 10)
        
        # 최종 점수 계산 (영역별 미세 조정)
        overall = min(100, max(0, base_score + adjustment + day_variation))
        
        return {
            "overall": overall,
            "study": min(100, max(0, overall + random.randint(-8, 8))),
            "wealth": min(100, max(0, overall + random.randint(-10, 10))),
            "love": min(100, max(0, overall + random.randint(-12, 12))),
            "marriage": min(100, max(0, overall + random.randint(-8, 8))),
            "career": min(100, max(0, overall + random.randint(-10, 10))),
            "business": min(100, max(0, overall + random.randint(-10, 10))),
            "health": min(100, max(0, overall + random.randint(-5, 5)))
        }
    
    def _get_template_level(self, score: int) -> str:
        """점수에 따른 템플릿 레벨 반환"""
        if score >= 85:
            return "excellent"
        elif score >= 65:
            return "good"
        elif score >= 45:
            return "average"
        elif score >= 30:
            return "caution"
        else:
            return "difficult"
    
    def _get_dominant_sibsung(self, pillars: List[Dict]) -> str:
        """원국에서 가장 많은 십성 반환"""
        sibsung_count = {}
        for p in pillars:
            for key in ["t_gan", "t_ji"]:
                sibsung = p.get(key, "")
                if sibsung and sibsung != "본인":
                    sibsung_count[sibsung] = sibsung_count.get(sibsung, 0) + 1
        
        if not sibsung_count:
            return "비견"
        return max(sibsung_count, key=sibsung_count.get)
    
    def _select_template(self, templates: List[str]) -> str:
        """템플릿 리스트에서 하나를 선택"""
        if not templates:
            return ""
        return random.choice(templates)
    
    def _select_greeting(self, hour: int) -> str:
        """시간대에 맞는 인사말 선택"""
        if 5 <= hour < 12:
            return self._select_template(GREETINGS.get("morning", []))
        elif 12 <= hour < 18:
            return self._select_template(GREETINGS.get("afternoon", []))
        else:
            return self._select_template(GREETINGS.get("evening", []))
    
    def _select_closing(self, score: int) -> str:
        """점수에 따른 마무리 멘트 선택"""
        if score >= 60:
            return self._select_template(CLOSINGS.get("positive", []))
        elif score >= 40:
            return self._select_template(CLOSINGS.get("neutral", []))
        else:
            return self._select_template(CLOSINGS.get("encouragement", []))
    
    def _select_time_advice(self, hour: int) -> str:
        """시간대에 맞는 조언 선택"""
        if 5 <= hour < 12:
            return self._select_template(TIME_ADVICE.get("morning", []))
        elif 12 <= hour < 18:
            return self._select_template(TIME_ADVICE.get("afternoon", []))
        else:
            return self._select_template(TIME_ADVICE.get("evening", []))
    
    # =========================================================================
    # 영역별 운세 생성 메서드
    # =========================================================================
    
    def _generate_overall(
        self, 
        score: int, 
        interactions: Dict,
        season: str,
        weekday: str
    ) -> str:
        """총운 생성"""
        level = self._get_template_level(score)
        
        # 기본 템플릿 선택
        templates_map = {
            "excellent": OVERALL_EXCELLENT,
            "good": OVERALL_GOOD,
            "average": OVERALL_AVERAGE,
            "caution": OVERALL_CAUTION,
            "difficult": OVERALL_DIFFICULT
        }
        base = self._select_template(templates_map.get(level, OVERALL_AVERAGE))
        
        # 계절감 추가 (50% 확률)
        season_text = ""
        if random.random() < 0.5 and season in SEASON_MOOD:
            season_text = " " + self._select_template(SEASON_MOOD[season])
        
        return base + season_text
    
    def _generate_study(self, score: int, dominant_sibsung: str) -> str:
        """학업운 생성"""
        level = self._get_template_level(score)
        
        templates_map = {
            "excellent": STUDY_EXCELLENT,
            "good": STUDY_GOOD,
            "average": STUDY_AVERAGE,
            "caution": STUDY_CAUTION,
            "difficult": STUDY_DIFFICULT
        }
        base = self._select_template(templates_map.get(level, STUDY_AVERAGE))
        
        # 십성별 추가 조언 (30% 확률)
        sibsung_text = ""
        if random.random() < 0.3 and dominant_sibsung in STUDY_BY_SIBSUNG:
            sibsung_text = " " + self._select_template(STUDY_BY_SIBSUNG[dominant_sibsung])
        
        return base + sibsung_text
    
    def _generate_wealth(
        self, 
        score: int, 
        dominant_sibsung: str,
        yongsin: Dict
    ) -> str:
        """재물운 생성"""
        level = self._get_template_level(score)
        
        templates_map = {
            "excellent": WEALTH_EXCELLENT,
            "good": WEALTH_GOOD,
            "average": WEALTH_AVERAGE,
            "caution": WEALTH_CAUTION,
            "difficult": WEALTH_DIFFICULT
        }
        base = self._select_template(templates_map.get(level, WEALTH_AVERAGE))
        
        # 십성별 추가 조언 (40% 확률 - 재물은 십성 영향 큼)
        sibsung_text = ""
        if random.random() < 0.4 and dominant_sibsung in WEALTH_BY_SIBSUNG:
            sibsung_text = " " + self._select_template(WEALTH_BY_SIBSUNG[dominant_sibsung])
        
        return base + sibsung_text
    
    def _generate_love(
        self, 
        score: int, 
        dominant_sibsung: str,
        status: str
    ) -> str:
        """연애운 생성"""
        level = self._get_template_level(score)
        
        if status == "couple":
            templates_map = {
                "excellent": LOVE_COUPLE_EXCELLENT,
                "good": LOVE_COUPLE_GOOD,
                "average": LOVE_COUPLE_AVERAGE,
                "caution": LOVE_COUPLE_CAUTION,
                "difficult": LOVE_COUPLE_DIFFICULT
            }
        else:
            templates_map = {
                "excellent": LOVE_SINGLE_EXCELLENT,
                "good": LOVE_SINGLE_GOOD,
                "average": LOVE_SINGLE_AVERAGE,
                "caution": LOVE_SINGLE_CAUTION,
                "difficult": LOVE_SINGLE_DIFFICULT
            }
        
        base = self._select_template(templates_map.get(level, []))
        
        # 십성별 추가 (35% 확률)
        sibsung_text = ""
        if random.random() < 0.35 and dominant_sibsung in LOVE_BY_SIBSUNG:
            sibsung_text = " " + self._select_template(LOVE_BY_SIBSUNG[dominant_sibsung])
        
        return base + sibsung_text
    
    def _generate_marriage(
        self, 
        score: int, 
        dominant_sibsung: str,
        status: str
    ) -> str:
        """결혼운 생성"""
        level = self._get_template_level(score)
        
        if status == "married":
            templates_map = {
                "excellent": MARRIAGE_MARRIED_EXCELLENT,
                "good": MARRIAGE_MARRIED_GOOD,
                "average": MARRIAGE_MARRIED_AVERAGE,
                "caution": MARRIAGE_MARRIED_CAUTION,
                "difficult": MARRIAGE_MARRIED_DIFFICULT
            }
        else:
            templates_map = {
                "excellent": MARRIAGE_SINGLE_EXCELLENT,
                "good": MARRIAGE_SINGLE_GOOD,
                "average": MARRIAGE_SINGLE_AVERAGE,
                "caution": MARRIAGE_SINGLE_CAUTION,
                "difficult": MARRIAGE_SINGLE_DIFFICULT
            }
        
        base = self._select_template(templates_map.get(level, []))
        
        # 십성별 추가 (30% 확률)
        sibsung_text = ""
        if random.random() < 0.3 and dominant_sibsung in MARRIAGE_BY_SIBSUNG:
            sibsung_text = " " + self._select_template(MARRIAGE_BY_SIBSUNG[dominant_sibsung])
        
        return base + sibsung_text
    
    def _generate_career(self, score: int, dominant_sibsung: str) -> str:
        """직업운 생성"""
        level = self._get_template_level(score)
        
        templates_map = {
            "excellent": CAREER_EXCELLENT,
            "good": CAREER_GOOD,
            "average": CAREER_AVERAGE,
            "caution": CAREER_CAUTION,
            "difficult": CAREER_DIFFICULT
        }
        base = self._select_template(templates_map.get(level, CAREER_AVERAGE))
        
        # 십성별 추가 (40% 확률)
        sibsung_text = ""
        if random.random() < 0.4 and dominant_sibsung in CAREER_BY_SIBSUNG:
            sibsung_text = " " + self._select_template(CAREER_BY_SIBSUNG[dominant_sibsung])
        
        return base + sibsung_text
    
    def _generate_business(self, score: int, dominant_sibsung: str) -> str:
        """사업운 생성"""
        level = self._get_template_level(score)
        
        templates_map = {
            "excellent": BUSINESS_EXCELLENT,
            "good": BUSINESS_GOOD,
            "average": BUSINESS_AVERAGE,
            "caution": BUSINESS_CAUTION,
            "difficult": BUSINESS_DIFFICULT
        }
        base = self._select_template(templates_map.get(level, BUSINESS_AVERAGE))
        
        # 십성별 추가 (35% 확률)
        sibsung_text = ""
        if random.random() < 0.35 and dominant_sibsung in BUSINESS_BY_SIBSUNG:
            sibsung_text = " " + self._select_template(BUSINESS_BY_SIBSUNG[dominant_sibsung])
        
        return base + sibsung_text
    
    def _generate_health(
        self, 
        score: int, 
        me_elem: str,
        season: str,
        age_group: str,
        interactions: Dict
    ) -> str:
        """건강운 생성"""
        level = self._get_template_level(score)
        
        templates_map = {
            "excellent": HEALTH_EXCELLENT,
            "good": HEALTH_GOOD,
            "average": HEALTH_AVERAGE,
            "caution": HEALTH_CAUTION,
            "difficult": HEALTH_DIFFICULT
        }
        base = self._select_template(templates_map.get(level, HEALTH_AVERAGE))
        
        # 오행별 건강 조언 추가 (40% 확률)
        elem_text = ""
        if random.random() < 0.4 and me_elem in HEALTH_BY_ELEMENT:
            elem_text = " " + self._select_template(HEALTH_BY_ELEMENT[me_elem])
        
        # 계절별 건강 조언 추가 (30% 확률)
        season_text = ""
        if random.random() < 0.3 and season in HEALTH_BY_SEASON:
            season_text = " " + self._select_template(HEALTH_BY_SEASON[season])
        
        return base + elem_text + season_text
    
    def _generate_lucky_items(self, yongsin: Dict, target_date: datetime) -> Dict[str, str]:
        """행운 아이템 생성"""
        # FortuneBridge가 있으면 사용
        if self.fortune_bridge:
            yongsin_elem = yongsin.get("name", "목")
            lucky = self.fortune_bridge.get_lucky_report(yongsin_elem)
            return {
                "color": lucky.get("color", "초록색"),
                "number": lucky.get("number", "3, 8"),
                "direction": lucky.get("direction", "동쪽"),
                "item": lucky.get("item", "식물")
            }
        
        # 기본값
        return {
            "color": "초록색",
            "number": "3, 8",
            "direction": "동쪽",
            "item": "식물, 나무 액세서리"
        }


# ============================================================
# 간편 사용을 위한 함수형 인터페이스
# ============================================================

def get_daily_fortune(
    analysis: Dict[str, Any],
    name: str = "회원",
    target_date: datetime = None,
    relationship_status: str = "single",
    marriage_status: str = "single",
    fortune_bridge = None
) -> Dict[str, Any]:
    """
    간편하게 오늘의 운세를 생성합니다.
    
    Args:
        analysis: saju_engine.analyze() 반환값
        name: 사용자 이름
        target_date: 운세를 볼 날짜
        relationship_status: 연애 상태 (single/couple)
        marriage_status: 결혼 상태 (single/married)
        fortune_bridge: FortuneBridge 인스턴스
        
    Returns:
        운세 결과 딕셔너리
    """
    generator = FortuneGenerator(fortune_bridge=fortune_bridge)
    return generator.generate_daily_fortune(
        analysis=analysis,
        target_date=target_date,
        name=name,
        relationship_status=relationship_status,
        marriage_status=marriage_status
    )
