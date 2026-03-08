"""
PP Clinic - Review Crawler Module (v1.0)
네이버 플레이스 / 카카오맵 실시간 리뷰 수집

구조:
- ReviewCrawler 기반 클래스 (공통 인터페이스)
- NaverPlaceCrawler: 네이버 플레이스 리뷰 수집
- KakaoMapCrawler: 카카오맵 리뷰 수집
- TMapCrawler: 티맵 리뷰 수집 (공유 + 평점)

확장: 새 플랫폼 추가 시 ReviewCrawler를 상속하면 됨
"""

import time
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv()

# 요청 헤더 (봇 감지 회피용)
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://www.naver.com",
}


@dataclass
class Review:
    """수집된 리뷰 표준 데이터 구조"""
    platform: str        # naver / kakao / tmap
    clinic_name: str     # 병원 이름
    rating: float        # 별점 (0 ~ 5)
    text: str            # 리뷰 텍스트
    date: str            # 작성 날짜
    url: str             # 원문 URL


class ReviewCrawler:
    """기반 클래스 - 모든 크롤러가 공통으로 구현해야 하는 인터페이스"""
    PLATFORM = "base"

    def get_reviews(self, clinic_name: str, place_id: str, count: int = 10) -> List[Review]:
        raise NotImplementedError


# ──────────────────────────────────────────────
# [1] 네이버 블로그 검색 크롤러 (Naver Blog Search API)
# 네이버 플레이스리뷰는 JS렌더링이어서 HTTP 스크레이핑 불가
# 대신 인증된 업체 API로 네이버 블로그 후기원문을 가져옴
# ──────────────────────────────────────────────
class NaverPlaceCrawler(ReviewCrawler):
    PLATFORM = "naver"
    BLOG_URL = "https://openapi.naver.com/v1/search/blog.json"

    def __init__(self):
        import os
        self.client_id = os.getenv("NAVER_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET")

    def get_reviews(self, clinic_name: str, place_id: str = None, count: int = 5) -> List[Review]:
        """네이버 블로그 검색 API로 실제 환자 후기 블로그 포스트 수집"""
        reviews = []
        query = f"{clinic_name} 시술 후기"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {
            "query": query,
            "display": count,
            "sort": "date",  # 최신순
        }
        try:
            r = requests.get(self.BLOG_URL, headers=headers, params=params, timeout=8)
            items = r.json().get("items", [])
            for item in items:
                # HTML 태그 제거
                import re
                title = re.sub(r"<[^>]+>", "", item.get("title", ""))
                desc = re.sub(r"<[^>]+>", "", item.get("description", ""))
                text = f"{title}. {desc}".strip()
                if len(text) > 20:
                    reviews.append(Review(
                        platform="naver_blog",
                        clinic_name=clinic_name,
                        rating=0,
                        text=text[:500],
                        date=item.get("postdate", ""),
                        url=item.get("link", ""),
                    ))
            print(f"[NaverBlog] {clinic_name}: {len(reviews)}개 후기 블로그 수집")
        except Exception as e:
            print(f"[NaverBlog ERROR] {clinic_name}: {e}")

        return reviews



# ──────────────────────────────────────────────
# [2] 카카오맵 크롤러
# ──────────────────────────────────────────────
class KakaoMapCrawler(ReviewCrawler):
    PLATFORM = "kakao"
    SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
    REVIEW_URL = "https://place.map.kakao.com/m/commentlist/v/{place_id}"

    # 카카오 REST API 키가 필요하면 .env에 KAKAO_REST_API_KEY 추가
    # 무키 방식으로도 일부 정보 수집 가능
    def get_reviews(self, clinic_name: str, place_id: str = None, count: int = 10) -> List[Review]:
        """카카오맵 리뷰 수집 (commentlist API)"""
        if not place_id:
            print(f"[KakaoMap] {clinic_name}: place_id 필요. 카카오맵에서 URL 확인하세요.")
            return []

        reviews = []
        url = self.REVIEW_URL.format(place_id=place_id)
        try:
            r = requests.get(url, headers=BROWSER_HEADERS, timeout=8)
            data = r.json()
            comment_list = data.get("comment", {}).get("list", [])
            for item in comment_list[:count]:
                reviews.append(Review(
                    platform="kakao",
                    clinic_name=clinic_name,
                    rating=item.get("point", 0),
                    text=item.get("contents", ""),
                    date=item.get("date", ""),
                    url=f"https://place.map.kakao.com/{place_id}",
                ))
            print(f"[KakaoMap] {clinic_name}: {len(reviews)}개 리뷰 수집")
        except Exception as e:
            print(f"[KakaoMap ERROR] {clinic_name}: {e}")

        return reviews


# ──────────────────────────────────────────────
# [3] 통합 크롤러 코디네이터
# ──────────────────────────────────────────────
class ReviewCrawlerCoordinator:
    """
    여러 플랫폼 크롤러를 한 번에 실행하는 코디네이터
    clinic_config에 병원 정보를 추가하면 자동으로 모든 플랫폼에서 수집
    """

    def __init__(self):
        self.crawlers = {
            "naver": NaverPlaceCrawler(),
            "kakao": KakaoMapCrawler(),
        }

    def crawl_all(self, clinic_configs: List[Dict], count_per_platform: int = 5) -> List[Review]:
        """
        clinic_configs 예시:
        [
            {"name": "A성형외과", "naver_id": "12345678", "kakao_id": "987654"},
            {"name": "B피부과", "naver_id": "23456789", "kakao_id": None},
        ]
        """
        all_reviews = []
        for clinic in clinic_configs:
            name = clinic["name"]
            for platform, crawler in self.crawlers.items():
                place_id = clinic.get(f"{platform}_id")
                reviews = crawler.get_reviews(
                    clinic_name=name,
                    place_id=place_id,
                    count=count_per_platform
                )
                all_reviews.extend(reviews)
                time.sleep(1)  # 서버 부하 방지

        return all_reviews
