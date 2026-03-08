#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP Clinic SNS Public Data Crawler (Layer 1)
-------------------------------------------
플랫폼별 공개 데이터를 수집합니다:
  - YouTube Data API v3      → Shorts / 키워드 영상 통계
  - Naver Blog Search API    → 이미 구현된 방식 재활용
  - TikTok (Apify)           → 해시태그 트렌드 (API 키 필요)
  - Instagram (Apify)        → 해시태그 Top Posts (API 키 필요)
  - Threads                  → 공개 게시물 (비공식 크롤, 폴백 지원)

Usage:
    from engine.sns_crawler import SNSCrawler
    crawler = SNSCrawler()
    results = crawler.collect_all(keywords=["실리프팅", "피부관리"])
"""

import os
import time
import json
import datetime
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
#  데이터 클래스
# ─────────────────────────────────────────────
class SNSPost:
    def __init__(self, platform: str, keyword: str, title: str,
                 url: str, views: int = 0, likes: int = 0,
                 comments: int = 0, shares: int = 0,
                 author: str = "", published_at: str = "",
                 raw: dict = None):
        self.platform = platform
        self.keyword = keyword
        self.title = title
        self.url = url
        self.views = views
        self.likes = likes
        self.comments = comments
        self.shares = shares
        self.author = author
        self.published_at = published_at
        self.raw = raw or {}
        self.collected_at = datetime.datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "keyword": self.keyword,
            "title": self.title[:100],
            "url": self.url,
            "views": self.views,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "author": self.author,
            "published_at": self.published_at,
            "collected_at": self.collected_at,
        }

    def engagement_score(self) -> float:
        """단순 인게이지먼트 점수 (높을수록 좋음)"""
        if self.views == 0:
            return float(self.likes + self.comments * 3 + self.shares * 5)
        return round((self.likes + self.comments * 3 + self.shares * 5) / max(self.views, 1) * 100, 2)

    def __repr__(self):
        return f"[{self.platform}] {self.title[:40]}... | 👁{self.views:,} ❤{self.likes:,}"


# ─────────────────────────────────────────────
#  플랫폼별 크롤러
# ─────────────────────────────────────────────

class YouTubeCrawler:
    """YouTube Data API v3 - 공식 API (무료 쿼터: 10,000 units/day)"""

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search_shorts(self, keyword: str, max_results: int = 10) -> List[SNSPost]:
        """키워드로 YouTube Shorts 검색 후 통계 수집"""
        if not self.api_key or self.api_key == "your_youtube_api_key_here":
            print("[YouTube] API 키 미설정 - 건너뜀")
            return []

        posts = []
        try:
            # 1단계: 검색
            search_url = f"{self.BASE_URL}/search"
            params = {
                "key": self.api_key,
                "q": keyword,
                "part": "id,snippet",
                "type": "video",
                "videoDuration": "short",   # Shorts 필터
                "order": "viewCount",
                "regionCode": "KR",
                "relevanceLanguage": "ko",
                "maxResults": max_results,
            }
            resp = requests.get(search_url, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            if not items:
                return []

            # 2단계: 통계 조회 (videoId 배열)
            video_ids = [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]
            stats_url = f"{self.BASE_URL}/videos"
            stats_params = {
                "key": self.api_key,
                "id": ",".join(video_ids),
                "part": "statistics,snippet",
            }
            stats_resp = requests.get(stats_url, params=stats_params, timeout=10)
            stats_resp.raise_for_status()
            stats_map = {v["id"]: v for v in stats_resp.json().get("items", [])}

            for item in items:
                vid_id = item.get("id", {}).get("videoId", "")
                snippet = item.get("snippet", {})
                stat = stats_map.get(vid_id, {}).get("statistics", {})
                posts.append(SNSPost(
                    platform="YouTube Shorts",
                    keyword=keyword,
                    title=snippet.get("title", ""),
                    url=f"https://www.youtube.com/shorts/{vid_id}",
                    views=int(stat.get("viewCount", 0)),
                    likes=int(stat.get("likeCount", 0)),
                    comments=int(stat.get("commentCount", 0)),
                    author=snippet.get("channelTitle", ""),
                    published_at=snippet.get("publishedAt", ""),
                ))

            print(f"[YouTube] '{keyword}' → {len(posts)}개 수집")
        except Exception as e:
            print(f"[YouTube ERROR] {e}")

        return posts


class NaverBlogCrawler:
    """Naver Blog Search API - 기존 구현 재활용"""

    BASE_URL = "https://openapi.naver.com/v1/search/blog"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def search(self, keyword: str, max_results: int = 10) -> List[SNSPost]:
        if not self.client_id or self.client_id == "your_naver_id_here":
            print("[Naver Blog] API 키 미설정 - 건너뜀")
            return []

        posts = []
        try:
            headers = {
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_secret,
            }
            params = {
                "query": keyword,
                "display": max_results,
                "sort": "sim",
            }
            resp = requests.get(self.BASE_URL, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                # Naver Blog API는 조회수를 제공하지 않음 — 제목/링크만
                title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                posts.append(SNSPost(
                    platform="Naver Blog",
                    keyword=keyword,
                    title=title,
                    url=item.get("link", ""),
                    author=item.get("bloggername", ""),
                    published_at=item.get("postdate", ""),
                ))

            print(f"[Naver Blog] '{keyword}' → {len(posts)}개 수집")
        except Exception as e:
            print(f"[Naver Blog ERROR] {e}")

        return posts


class ApifyBaseCrawler:
    """Apify API 기반 크롤러 베이스 (Instagram, TikTok 공통)"""

    APIFY_BASE = "https://api.apify.com/v2"

    def __init__(self, api_token: str):
        self.api_token = api_token

    def _is_configured(self) -> bool:
        return bool(self.api_token and self.api_token != "your_apify_token_here")

    def _run_actor(self, actor_id: str, input_data: dict, timeout: int = 60) -> list:
        """Apify Actor를 실행하고 결과를 반환"""
        if not self._is_configured():
            return []

        headers = {"Content-Type": "application/json"}
        run_url = f"{self.APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items"
        params = {"token": self.api_token, "timeout": timeout, "memory": 256}

        try:
            resp = requests.post(run_url, headers=headers,
                                 params=params, json=input_data, timeout=timeout + 10)
            resp.raise_for_status()
            return resp.json() if isinstance(resp.json(), list) else []
        except Exception as e:
            print(f"[Apify ERROR] Actor {actor_id}: {e}")
            return []


class InstagramCrawler(ApifyBaseCrawler):
    """Apify Instagram Hashtag Scraper (공개 해시태그 게시물)"""

    ACTOR_ID = "apify~instagram-hashtag-scraper"

    def search_hashtag(self, hashtag: str, max_results: int = 10) -> List[SNSPost]:
        if not self._is_configured():
            print("[Instagram] Apify 토큰 미설정 - 건너뜀")
            return []

        # Instagram 해시태그는 공백 불가 → 제거
        clean_tag = hashtag.lstrip("#").replace(" ", "")
        if not clean_tag:
            return []
        input_data = {
            "hashtags": [clean_tag],
            "resultsLimit": max_results,
        }
        items = self._run_actor(self.ACTOR_ID, input_data)
        posts = []
        for item in items:
            posts.append(SNSPost(
                platform="Instagram",
                keyword=f"#{clean_tag}",
                title=item.get("caption", "")[:120] or f"#{clean_tag} 게시물",
                url=item.get("url", ""),
                views=item.get("videoViewCount", 0),
                likes=item.get("likesCount", 0),
                comments=item.get("commentsCount", 0),
                author=item.get("ownerUsername", ""),
                published_at=item.get("timestamp", ""),
            ))

        print(f"[Instagram] '#{clean_tag}' → {len(posts)}개 수집")
        return posts


class TikTokCrawler(ApifyBaseCrawler):
    """Apify TikTok Hashtag Scraper (공개 해시태그 영상)"""

    ACTOR_ID = "clockworks~tiktok-hashtag-scraper"

    def search_hashtag(self, hashtag: str, max_results: int = 10) -> List[SNSPost]:
        if not self._is_configured():
            print("[TikTok] Apify 토큰 미설정 - 건너뜀")
            return []

        clean_tag = hashtag.lstrip("#")
        input_data = {
            "hashtags": [clean_tag],
            "resultsPerPage": max_results,
        }
        items = self._run_actor(self.ACTOR_ID, input_data)
        posts = []
        for item in items:
            posts.append(SNSPost(
                platform="TikTok",
                keyword=f"#{clean_tag}",
                title=item.get("text", "")[:120] or f"#{clean_tag} 영상",
                url=item.get("webVideoUrl", ""),
                views=item.get("playCount", 0),
                likes=item.get("diggCount", 0),
                comments=item.get("commentCount", 0),
                shares=item.get("shareCount", 0),
                author=item.get("authorMeta", {}).get("name", ""),
                published_at=str(item.get("createTime", "")),
            ))

        print(f"[TikTok] '#{clean_tag}' → {len(posts)}개 수집")
        return posts


class ThreadsCrawler:
    """Threads 공개 게시물 크롤러 (비공식, Requests 기반)"""

    BASE_URL = "https://www.threads.net"

    def search_keyword(self, keyword: str, max_results: int = 10) -> List[SNSPost]:
        """
        Threads는 공식 API가 없으므로 공개 검색 결과를 파싱.
        Meta Graph API가 활성화된 경우 더 안정적이나 현재는 폴백 처리.
        """
        posts = []
        try:
            # Threads는 TOS상 자동화가 제한적이므로 Meta Graph API 엔드포인트를 우선 시도
            # 현재 공개 API 없음 → 폴백: 플레이스홀더 반환
            print(f"[Threads] '{keyword}' → Meta 공식 API 미지원, 건너뜀 (Meta Graph API 승인 필요)")
        except Exception as e:
            print(f"[Threads ERROR] {e}")

        return posts


# ─────────────────────────────────────────────
#  통합 SNS 크롤러
# ─────────────────────────────────────────────

class SNSCrawler:
    """
    Layer 1 통합 SNS 공개 데이터 크롤러
    ---
    .env 키:
      YOUTUBE_API_KEY        → YouTube Data API v3
      APIFY_API_TOKEN        → Instagram / TikTok (Apify)
      NAVER_CLIENT_ID/SECRET → Naver Blog (기존)
    """

    # 클리닉 관련 기본 해시태그 / 키워드
    DEFAULT_HASHTAGS = [
        "실리프팅", "리프팅시술", "얼굴리프팅",
        "안티에이징", "피부관리", "강남피부과",
        "신사역피부과", "울쎄라", "인모드", "피부과추천"
    ]

    def __init__(self):
        self.youtube = YouTubeCrawler(os.getenv("YOUTUBE_API_KEY", ""))
        self.naver_blog = NaverBlogCrawler(
            os.getenv("NAVER_CLIENT_ID", ""),
            os.getenv("NAVER_CLIENT_SECRET", "")
        )
        apify_token = os.getenv("APIFY_API_TOKEN", "")
        self.instagram = InstagramCrawler(apify_token)
        self.tiktok = TikTokCrawler(apify_token)
        self.threads = ThreadsCrawler()

    def collect_all(self, keywords: Optional[List[str]] = None,
                    max_per_keyword: int = 5) -> Dict[str, List[SNSPost]]:
        """
        모든 플랫폼에서 키워드별 공개 데이터 수집

        Returns:
            {platform: [SNSPost, ...]} 딕셔너리
        """
        if keywords is None:
            keywords = self.DEFAULT_HASHTAGS[:5]

        collected: Dict[str, List[SNSPost]] = {
            "YouTube Shorts": [],
            "Naver Blog": [],
            "Instagram": [],
            "TikTok": [],
            "Threads": [],
        }

        print(f"\n[SNS Layer 1] {len(keywords)}개 키워드 × 5개 플랫폼 수집 시작")
        print("-" * 50)

        for kw in keywords:
            # YouTube Shorts
            yt_posts = self.youtube.search_shorts(kw, max_results=max_per_keyword)
            collected["YouTube Shorts"].extend(yt_posts)
            time.sleep(0.5)

            # Naver Blog
            nb_posts = self.naver_blog.search(kw, max_results=max_per_keyword)
            collected["Naver Blog"].extend(nb_posts)
            time.sleep(0.5)

            # Instagram (해시태그)
            ig_posts = self.instagram.search_hashtag(kw, max_results=max_per_keyword)
            collected["Instagram"].extend(ig_posts)
            time.sleep(1.0)

            # TikTok (해시태그)
            tt_posts = self.tiktok.search_hashtag(kw, max_results=max_per_keyword)
            collected["TikTok"].extend(tt_posts)
            time.sleep(1.0)

            # Threads
            th_posts = self.threads.search_keyword(kw, max_results=max_per_keyword)
            collected["Threads"].extend(th_posts)

        return collected

    def summarize(self, collected: Dict[str, List[SNSPost]]) -> Dict:
        """수집 결과 요약 통계"""
        summary = {}
        total_posts = 0

        for platform, posts in collected.items():
            if not posts:
                continue
            total_posts += len(posts)
            top = sorted(posts, key=lambda p: p.views + p.likes * 10, reverse=True)[:3]
            summary[platform] = {
                "total_collected": len(posts),
                "total_views": sum(p.views for p in posts),
                "total_likes": sum(p.likes for p in posts),
                "total_comments": sum(p.comments for p in posts),
                "avg_engagement_score": round(
                    sum(p.engagement_score() for p in posts) / len(posts), 2
                ) if posts else 0,
                "top_posts": [p.to_dict() for p in top],
            }

        summary["_meta"] = {
            "total_posts": total_posts,
            "collected_at": datetime.datetime.now().isoformat(),
            "platforms_active": [p for p, d in summary.items() if p != "_meta"],
        }
        return summary

    def print_report(self, collected: Dict[str, List[SNSPost]]):
        """콘솔 리포트 출력"""
        print("\n" + "=" * 55)
        print("📱 SNS Layer 1 수집 결과")
        print("=" * 55)

        summary = self.summarize(collected)
        for platform, data in summary.items():
            if platform == "_meta":
                continue
            print(f"\n🔷 {platform}")
            print(f"   수집: {data['total_collected']}건 | "
                  f"총 조회수: {data['total_views']:,} | "
                  f"총 좋아요: {data['total_likes']:,}")
            print(f"   평균 인게이지먼트 점수: {data['avg_engagement_score']}")
            if data["top_posts"]:
                print(f"   🏆 Top 게시물:")
                for p in data["top_posts"][:2]:
                    print(f"      • {p['title'][:50]}...")
                    print(f"        👁{p['views']:,} ❤{p['likes']:,} 💬{p['comments']:,}")

        meta = summary.get("_meta", {})
        print(f"\n[완료] 총 {meta.get('total_posts', 0)}건 수집 | "
              f"{meta.get('collected_at', '')[:16]}")

    def save_to_json(self, collected: Dict[str, List[SNSPost]],
                     output_dir: str = "data") -> str:
        """수집 결과를 JSON 파일로 저장"""
        os.makedirs(output_dir, exist_ok=True)
        today = datetime.date.today().strftime("%Y%m%d")
        filepath = os.path.join(output_dir, f"sns_layer1_{today}.json")

        data = {
            platform: [p.to_dict() for p in posts]
            for platform, posts in collected.items()
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[저장] {filepath}")
        return filepath
