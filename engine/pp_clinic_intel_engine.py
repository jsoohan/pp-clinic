import os
import sys
import requests
import json
import datetime
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


def _get_gemini_client():
    """Lazy init: .env에 GEMINI_API_KEY가 있을 때만 클라이언트 생성"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        return None
    from google import genai
    return genai.Client(api_key=api_key)


GEMINI_MODEL = "models/gemini-2.5-flash"  # Separate quota from gemini-2.0-flash
CALL_DELAY_SECONDS = 5  # free tier: avoid rate limit


class PPClinicIntelligenceEngine:
    """
    PP Clinic Market Intelligence Engine (v2.2)
    Gemini API 기반 AI 감성분석 / 키워드 확장 / AEO 탐지 / Notion 동기화
    """

    def __init__(self):
        self.naver_id = os.getenv("NAVER_CLIENT_ID")
        self.naver_secret = os.getenv("NAVER_CLIENT_SECRET")
        self.notion_api_key = os.getenv("NOTION_API_KEY")
        self.notion_log_db_id = os.getenv("NOTION_LOG_DB_ID")
        self.notion_master_db_id = os.getenv("NOTION_MASTER_DB_ID")
        self._gemini = None  # lazy load

    @property
    def gemini(self):
        if self._gemini is None:
            self._gemini = _get_gemini_client()
            if self._gemini is None:
                raise RuntimeError("[ERROR] GEMINI_API_KEY가 .env에 설정되지 않았습니다.")
        return self._gemini

    def _gemini_prompt(self, prompt: str) -> str:
        """Gemini API call helper (paid plan - no retry needed)"""
        response = self.gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        text = response.text.strip()
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        return text.strip()

    # --------------------------------------------------
    # [1] 네이버 데이터랩 트렌드 수집 (05/06단계)
    # --------------------------------------------------
    def get_naver_trend(self, keywords: List[str], start_date: str, end_date: str) -> Dict:
        if not self.naver_id or self.naver_id == "your_naver_id_here":
            print("[Naver] API 키 미설정 - 건너뜀")
            return {"status": "skipped", "keywords": keywords}
        url = "https://openapi.naver.com/v1/datalab/search"
        headers = {
            "X-Naver-Client-Id": self.naver_id,
            "X-Naver-Client-Secret": self.naver_secret,
            "Content-Type": "application/json"
        }
        groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords[:5]]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": "date",
            "keywordGroups": groups
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Naver Trend ERROR] {e}")
            return {"status": "error", "message": str(e)}

    # --------------------------------------------------
    # [2] 휴리스틱 키워드 확장 (04/05/06단계)
    # --------------------------------------------------
    def generate_heuristic_keywords(self, seed_word: str, count: int = 50) -> List[str]:
        prompt = f"""
너는 대한민국 미용 성형 클리닉의 마케팅 전문가야.
"{seed_word}"에 관심 있는 잠재 환자들이 네이버/구글에서 실제로 검색할 법한 키워드를 {count}개 생성해줘.
조건: 부작용, 가격, 병원 선택, 지역, 대안 시술, 자가진단 등 다양한 관점 포함.
JSON 배열 형식만 반환. 예: ["실리프팅 부작용", "실리프팅 볼패임"]
"""
        try:
            text = self._gemini_prompt(prompt)
            keywords = json.loads(text)
            print(f"[Gemini] {seed_word}: {len(keywords)}개 키워드 생성")
            return keywords
        except Exception as e:
            print(f"[Gemini Keyword ERROR] {e}")
            return [f"{seed_word} {s}" for s in ["부작용", "가격", "추천", "신사역", "후기"]]

    # --------------------------------------------------
    # [3] 리뷰 감성 분석 (09단계)
    # --------------------------------------------------
    def analyze_review_sentiment(self, review_text: str) -> Dict:
        prompt = f"""
병원 후기를 분석해서 JSON으로 반환해줘:
후기: "{review_text}"

반환 형식:
{{"sentiment_score": -1.0~1.0 숫자, "complaint_keywords": ["불만 키워드"], "is_competitor_opportunity": true/false, "summary": "한 줄 요약"}}
JSON만 반환.
"""
        try:
            text = self._gemini_prompt(prompt)
            return json.loads(text)
        except Exception as e:
            print(f"[Gemini Sentiment ERROR] {e}")
            return {
                "sentiment_score": 0, "complaint_keywords": [],
                "is_competitor_opportunity": False, "summary": "분석 실패"
            }

    # --------------------------------------------------
    # [4] AEO 노출도 탐지 (05단계)
    # --------------------------------------------------
    def check_aeo_visibility(self, query: str) -> Dict:
        try:
            response = self.gemini.models.generate_content(
                model=GEMINI_MODEL, contents=query
            )
            answer = response.text
            is_mentioned = "팽팽" in answer or "pp clinic" in answer.lower()
            return {
                "query": query,
                "answer_snippet": answer[:300],
                "pp_clinic_mentioned": is_mentioned,
                "timestamp": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {"query": query, "pp_clinic_mentioned": False, "error": str(e)}

    # --------------------------------------------------
    # [5] Notion 기록
    # --------------------------------------------------
    def sync_to_notion(self, insight: Dict, label: str = "Daily Pulse"):
        if not self.notion_api_key or self.notion_api_key == "your_notion_api_key_here":
            print("[Notion] API 키 미설정 - 건너뜀")
            return
        url = "https://api.notion.com/v1/pages"
        headers = {
            "Authorization": f"Bearer {self.notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        payload = {
            "parent": {"database_id": self.notion_log_db_id},
            "properties": {
                "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                "핵심 인사이트": {
                    "title": [{"text": {"content": insight.get("summary", label)[:200]}}]
                },
                "AI 감성 점수": {"number": insight.get("sentiment_score", 0)},
                "Loss 포착": {"checkbox": bool(insight.get("is_competitor_opportunity", False))},
            }
        }
        try:
            r = requests.post(url, headers=headers, json=payload)
            r.raise_for_status()
            print(f"[Notion] 기록 완료: {insight.get('summary', label)[:50]}")
        except Exception as e:
            print(f"[Notion Sync ERROR] {e}")
