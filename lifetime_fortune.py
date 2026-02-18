"""
평생운세 생성 모듈 (Gemini API 기반)

- Gemini 2.5 Flash API를 사용하여 점신 스타일의 평생운세 생성
- SQLite 캐싱으로 대용량 처리 가능
"""

import hashlib
import json
import os
import re
import sqlite3
import urllib.request
from datetime import datetime
from typing import Optional

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

CACHE_DB_PATH = "./data/lifetime_cache.db"


class LifetimeFortuneGenerator:
    
    def __init__(self, saju_engine, fortune_bridge=None):
        self.engine = saju_engine
        self.bridge = fortune_bridge
        self._init_db()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(CACHE_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fortune_cache (
                cache_key TEXT PRIMARY KEY,
                birth_str TEXT,
                gender TEXT,
                ilju TEXT,
                overall TEXT,
                daeun TEXT,
                wealth TEXT,
                love TEXT,
                marriage TEXT,
                career TEXT,
                business TEXT,
                social TEXT,
                health TEXT,
                ilju_info TEXT,
                generated_at TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cache_key ON fortune_cache(cache_key)')
        conn.commit()
        conn.close()
    
    def _generate_cache_key(self, birth_str: str, gender: str) -> str:
        key_source = f"{birth_str}_{gender}"
        return hashlib.md5(key_source.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[dict]:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM fortune_cache WHERE cache_key = ?', (cache_key,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'cache_key': row[0],
                'birth': row[1],
                'gender': row[2],
                'ilju': row[3],
                'overall': row[4],
                'daeun': row[5],
                'wealth': row[6],
                'love': row[7],
                'marriage': row[8],
                'career': row[9],
                'business': row[10],
                'social': row[11],
                'health': row[12],
                'ilju_info': json.loads(row[13]) if row[13] else {},
                'generated_at': row[14]
            }
        return None
    
    def _save_to_cache(self, cache_key: str, data: dict):
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO fortune_cache 
            (cache_key, birth_str, gender, ilju, overall, daeun, wealth, love, marriage, career, business, social, health, ilju_info, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cache_key,
            data.get('birth', ''),
            data.get('gender', ''),
            data.get('ilju', ''),
            data.get('overall', ''),
            data.get('daeun', ''),
            data.get('wealth', ''),
            data.get('love', ''),
            data.get('marriage', ''),
            data.get('career', ''),
            data.get('business', ''),
            data.get('social', ''),
            data.get('health', ''),
            json.dumps(data.get('ilju_info', {}), ensure_ascii=False),
            data.get('generated_at', '')
        ))
        conn.commit()
        conn.close()
    
    def generate(
        self,
        birth_str: str,
        gender: str,
        location: str = "서울",
        name: str = "회원",
        calendar_type: str = "양력",
        use_cache: bool = True
    ) -> dict:
        cache_key = self._generate_cache_key(birth_str, gender)
        
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached:
                print(f"✅ 캐시 히트: {cache_key[:8]}...")
                cached['name'] = name
                cached['from_cache'] = True
                return cached
        
        print(f"🔍 사주 분석 중: {birth_str}")
        analysis = self.engine.analyze(
            birth_str=birth_str,
            gender=gender,
            location=location,
            use_yajas_i=True,
            calendar_type=calendar_type
        )
        
        if "error" in analysis:
            return {"error": analysis["error"]}
        
        ilju_info = {}
        if self.bridge:
            ilju_info = self.bridge.get_ilju_report(analysis.get('ilju', ''))
        
        print(f"🤖 Gemini API 호출 중...")
        prompt = self._build_prompt(analysis, ilju_info, name, gender)
        fortune_text = self._call_gemini_api(prompt)
        
        if not fortune_text:
            return {"error": "AI 응답 생성 실패"}
        
        result = self._parse_fortune_text(fortune_text)
        result['name'] = name
        result['birth'] = birth_str
        result['gender'] = gender
        result['ilju'] = analysis.get('ilju', '')
        result['ilju_info'] = ilju_info
        result['generated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result['from_cache'] = False
        
        self._save_to_cache(cache_key, result)
        print(f"💾 캐시 저장: {cache_key[:8]}...")
        
        return result
    
    def _build_prompt(self, analysis: dict, ilju_info: dict, name: str, gender: str) -> str:
        birth_year = int(analysis.get('birth', '1990')[:4]) if analysis.get('birth') else 1990
        current_year = datetime.now().year
        current_age = current_year - birth_year + 1
        
        gender_text = "남성" if gender == "M" else "여성"
        
        pillars_text = ""
        pillar_names = ['년주', '월주', '일주', '시주']
        for i, p in enumerate(analysis.get('pillars', [])):
            pillars_text += f"- {pillar_names[i]}: {p.get('gan','')}{p.get('ji','')} ({p.get('gan_kor','')}{p.get('ji_kor','')})\n"
        
        scores = analysis.get('scores', {})
        scores_text = f"목: {scores.get('목', 0)}, 화: {scores.get('화', 0)}, 토: {scores.get('토', 0)}, 금: {scores.get('금', 0)}, 수: {scores.get('수', 0)}"
        
        current_trace = analysis.get('current_trace', {})
        daeun = current_trace.get('daeun', {})
        daeun_text = ""
        if daeun:
            daeun_text = f"현재 대운: {daeun.get('ganzi', '')} ({daeun.get('start_age', '')}세~)"
        
        ilju_title = ilju_info.get('title', '')
        ilju_desc = ilju_info.get('description', '')
        ilju_tags = ', '.join(ilju_info.get('tags', []))
        
        prompt = f"""당신은 한국 최고의 사주명리 전문가이자 15년 경력의 운세 콘텐츠 작가입니다.

## 미션
아래 사주 분석 데이터를 바탕으로 점신/포스텔러 앱과 동일한 품질의 평생운세를 작성하세요.

## 사주 분석 데이터

**이름**: {name}님
**생년월일시**: {analysis.get('birth', '')}
**성별**: {gender_text}
**현재 나이**: {current_age}세 ({current_year}년 기준)

### 사주 4기둥
{pillars_text}

### 핵심 정보 (내부용, 절대 노출 금지)
- 일주: {analysis.get('ilju', '')}
- 일주 특성: {ilju_title} - {ilju_desc}
- 키워드: {ilju_tags}
- 오행 분포: {scores_text}
- 신강약: {analysis.get('status', '')}
- 대표 성향: {analysis.get('representative_tendency', '')}
- {daeun_text}

## 점신 스타일 가이드 (필수 준수)

### 1. 어투와 문체
- "~하게 됩니다", "~하는 시기입니다", "~해보세요" 등 부드러운 존댓말
- 문장이 자연스럽게 이어지는 스토리텔링
- 한 문단 내에서 주제가 유기적으로 연결

### 2. 절대 금지 (전문용어 노출)
금지어: 오행, 십성, 비견, 겁재, 식신, 상관, 정재, 편재, 정관, 편관, 정인, 편인, 용신, 신강, 신약, 대운, 세운, 천간, 지지, 합, 충, 형, 공망, MBTI, 건록, 제왕
대체: 자연스러운 성격/상황 묘사로 풀어서 설명

### 3. 분량
- 각 섹션 최소 500자 이상 (600~800자 권장)

### 4. 구체성
- 추상적 표현 금지: "운이 좋습니다"
- 구체적 표현: "이 시기에는 직장에서 중요한 프로젝트를 맡게 되거나, 승진의 기회가 찾아올 수 있습니다"

## 작성할 섹션 (9개)

각 섹션을 ## 섹션명 형식으로 구분하고, 500자 이상의 자연스러운 문단으로 작성하세요.

1. **총운 (평생운세)** - 타고난 성격과 기질, 인생 전반의 흐름 (청년기→중년기→노년기)
2. **대운풀이** - 현재 시기의 특성과 기회, 주의점
3. **재물운** - 돈 버는 스타일, 재물 흐름, 투자 성향
4. **애정운** - 연애 스타일, 이상형, 주의점
5. **결혼운** - 결혼 적기, 배우자 특성, 결혼생활 조언
6. **직업운** - 적성, 어울리는 직업, 커리어 조언
7. **사업운** - 사업 적합성, 어울리는 업종, 주의사항
8. **대인운** - 대인관계 스타일, 인복, 주의점
9. **건강운** - 체질, 주의할 건강 부위, 관리법"""
        
        return prompt
    
    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        try:
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 8192
                }
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0].get('content', {})
                    parts = content.get('parts', [])
                    if parts:
                        return parts[0].get('text', '')
                
                print(f"API 응답 오류: {result}")
                return None
                
        except Exception as e:
            print(f"Gemini API 호출 실패: {e}")
            return None
    
    def _parse_fortune_text(self, text: str) -> dict:
        sections = {
            'overall': '',
            'daeun': '',
            'wealth': '',
            'love': '',
            'marriage': '',
            'career': '',
            'business': '',
            'social': '',
            'health': ''
        }
        
        section_patterns = {
            'overall': r'##\s*총운.*?\n(.*?)(?=##|$)',
            'daeun': r'##\s*대운.*?\n(.*?)(?=##|$)',
            'wealth': r'##\s*재물운.*?\n(.*?)(?=##|$)',
            'love': r'##\s*애정운.*?\n(.*?)(?=##|$)',
            'marriage': r'##\s*결혼운.*?\n(.*?)(?=##|$)',
            'career': r'##\s*직업운.*?\n(.*?)(?=##|$)',
            'business': r'##\s*사업운.*?\n(.*?)(?=##|$)',
            'social': r'##\s*대인운.*?\n(.*?)(?=##|$)',
            'health': r'##\s*건강운.*?\n(.*?)(?=##|$)'
        }
        
        for key, pattern in section_patterns.items():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                content = re.sub(r'\n##.*$', '', content, flags=re.DOTALL)
                sections[key] = content.strip()
        
        if not any(sections.values()):
            sections['overall'] = text
        
        return sections
    
    def clear_cache(self):
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM fortune_cache')
        conn.commit()
        conn.close()
        print("캐시가 삭제되었습니다.")
    
    def get_cache_stats(self) -> dict:
        conn = sqlite3.connect(CACHE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM fortune_cache')
        count = cursor.fetchone()[0]
        conn.close()
        
        db_size = 0
        if os.path.exists(CACHE_DB_PATH):
            db_size = os.path.getsize(CACHE_DB_PATH) / 1024  # KB
        
        return {
            "total_entries": count,
            "cache_db": CACHE_DB_PATH,
            "db_size_kb": round(db_size, 2)
        }
