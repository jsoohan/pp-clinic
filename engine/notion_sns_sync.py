#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP Clinic - Notion SNS Metrics Sync Module
-------------------------------------------
SNS Layer 1 크롤링 결과를 Notion 데이터베이스에 동기화합니다.

기능:
  1. Notion에 'SNS Metrics' DB 자동 생성 (최초 1회)
  2. 매일 수집된 플랫폼별 Top Posts를 Notion 페이지로 저장
  3. 수집 요약(총 조회수, 좋아요, Top 키워드)을 Daily Log에 기록

Usage:
    from engine.notion_sns_sync import NotionSNSSync
    syncer = NotionSNSSync()
    syncer.sync(collected)   # SNSCrawler.collect_all() 결과 전달
"""

import os
import json
import datetime
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_LOG_DB_ID = os.getenv("NOTION_LOG_DB_ID", "")
NOTION_SNS_DB_ID = os.getenv("NOTION_SNS_DB_ID", "")   # SNS 전용 DB (자동 생성)
PARENT_PAGE_ID = "70b7d540-87ee-4f8e-b27a-43f772f4a935"  # 기존 DB와 같은 페이지

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


class NotionSNSSync:
    """
    SNS 수집 데이터 → Notion DB 동기화 클래스
    """

    def __init__(self):
        self.api_key = NOTION_API_KEY
        self.log_db_id = NOTION_LOG_DB_ID
        self.sns_db_id = NOTION_SNS_DB_ID or self._get_or_create_sns_db()

    def _is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "your_notion_api_key_here")

    # ─────────────────────────────────────────────
    #  SNS Metrics DB 자동 생성
    # ─────────────────────────────────────────────
    def _get_or_create_sns_db(self) -> str:
        """SNS Metrics DB가 없으면 Notion에 새로 생성"""
        if not self._is_configured():
            return ""

        # .env에 ID가 있으면 재사용
        existing = os.getenv("NOTION_SNS_DB_ID", "")
        if existing and existing != "your_sns_db_id_here":
            return existing

        print("[Notion] SNS Metrics DB 생성 중...")
        payload = {
            "parent": {"type": "page_id", "page_id": PARENT_PAGE_ID},
            "title": [{"type": "text", "text": {"content": "PP Clinic - SNS Metrics Log"}}],
            "properties": {
                "제목": {"title": {}},
                "날짜": {"date": {}},
                "플랫폼": {"select": {
                    "options": [
                        {"name": "YouTube Shorts", "color": "red"},
                        {"name": "Instagram", "color": "pink"},
                        {"name": "TikTok", "color": "purple"},
                        {"name": "Naver Blog", "color": "green"},
                        {"name": "Threads", "color": "gray"},
                    ]
                }},
                "키워드": {"rich_text": {}},
                "조회수": {"number": {"format": "number_with_commas"}},
                "좋아요": {"number": {"format": "number_with_commas"}},
                "댓글": {"number": {"format": "number_with_commas"}},
                "공유": {"number": {"format": "number_with_commas"}},
                "인게이지먼트 점수": {"number": {"format": "number"}},
                "작성자": {"rich_text": {}},
                "원본 링크": {"url": {}},
                "AI 분석 메모": {"rich_text": {}},
            },
        }

        try:
            r = requests.post(
                "https://api.notion.com/v1/databases",
                headers=NOTION_HEADERS,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            db_id = r.json()["id"]
            print(f"[Notion] SNS DB 생성 완료: {db_id}")
            self._save_sns_db_id(db_id)
            return db_id
        except Exception as e:
            print(f"[Notion] DB 생성 오류: {e}")
            return ""

    def _save_sns_db_id(self, db_id: str):
        """생성된 DB ID를 .env에 저장"""
        env_path = ".env"
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()

            if "NOTION_SNS_DB_ID=" in content:
                import re
                content = re.sub(r"NOTION_SNS_DB_ID=.*", f"NOTION_SNS_DB_ID={db_id}", content)
            else:
                content += f"\nNOTION_SNS_DB_ID={db_id}\n"

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[Notion] .env에 NOTION_SNS_DB_ID 저장 완료")
        except Exception as e:
            print(f"[Notion] .env 저장 오류: {e}")

    # ─────────────────────────────────────────────
    #  개별 포스트 → Notion 페이지 저장
    # ─────────────────────────────────────────────
    def _create_post_page(self, post: dict) -> bool:
        """SNSPost.to_dict() 결과를 Notion 페이지로 저장"""
        if not self.sns_db_id:
            return False

        title = post.get("title", "")[:100] or f"{post.get('platform','')} 게시물"
        date_str = datetime.date.today().isoformat()

        # 인게이지먼트 점수 계산
        views = post.get("views", 0) or 0
        likes = post.get("likes", 0) or 0
        comments = post.get("comments", 0) or 0
        shares = post.get("shares", 0) or 0
        engagement = round(
            (likes + comments * 3 + shares * 5) / max(views, 1) * 100, 2
        ) if views > 0 else float(likes + comments * 3 + shares * 5)

        payload = {
            "parent": {"database_id": self.sns_db_id},
            "properties": {
                "제목": {"title": [{"text": {"content": title}}]},
                "날짜": {"date": {"start": date_str}},
                "플랫폼": {"select": {"name": post.get("platform", "기타")}},
                "키워드": {"rich_text": [{"text": {"content": post.get("keyword", "")}}]},
                "조회수": {"number": views},
                "좋아요": {"number": likes},
                "댓글": {"number": comments},
                "공유": {"number": shares},
                "인게이지먼트 점수": {"number": engagement},
                "작성자": {"rich_text": [{"text": {"content": post.get("author", "")[:100]}}]},
            },
        }

        # URL이 있을 때만 추가
        url = post.get("url", "")
        if url and url.startswith("http"):
            payload["properties"]["원본 링크"] = {"url": url}

        try:
            r = requests.post(
                "https://api.notion.com/v1/pages",
                headers=NOTION_HEADERS,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"[Notion] 페이지 저장 오류: {e}")
            return False

    # ─────────────────────────────────────────────
    #  Daily Log에 SNS 요약 기록
    # ─────────────────────────────────────────────
    def _update_daily_log(self, summary: dict):
        """기존 Daily Intelligence Log DB에 SNS 수집 요약 행 추가"""
        if not self.log_db_id:
            return

        total = summary.get("_meta", {}).get("total_posts", 0)
        platforms = summary.get("_meta", {}).get("platforms_active", [])

        # Top 게시물 찾기
        top_title = ""
        top_views = 0
        for platform, data in summary.items():
            if platform == "_meta":
                continue
            for p in data.get("top_posts", []):
                if p.get("views", 0) > top_views:
                    top_views = p.get("views", 0)
                    top_title = p.get("title", "")[:80]

        insight = (
            f"[SNS 수집] {total}건 | 플랫폼: {', '.join(platforms)} | "
            f"Top: {top_title} ({top_views:,} views)"
        )

        payload = {
            "parent": {"database_id": self.log_db_id},
            "properties": {
                "핵심 인사이트": {"title": [{"text": {"content": insight[:200]}}]},
                "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                "AI 감성 점수": {"number": 0},
                "Loss 포착": {"checkbox": False},
            },
        }
        try:
            r = requests.post(
                "https://api.notion.com/v1/pages",
                headers=NOTION_HEADERS,
                json=payload,
                timeout=15,
            )
            r.raise_for_status()
            print(f"[Notion] Daily Log 요약 기록: {insight[:60]}...")
        except Exception as e:
            print(f"[Notion] Daily Log 오류: {e}")

    # ─────────────────────────────────────────────
    #  메인 동기화 함수
    # ─────────────────────────────────────────────
    def sync(self, collected: dict, top_n: int = 5) -> int:
        """
        SNSCrawler.collect_all() 결과를 Notion에 저장

        Args:
            collected: {platform: [SNSPost, ...]} 딕셔너리
            top_n: 플랫폼별 저장할 Top N 게시물

        Returns:
            저장 성공한 페이지 수
        """
        if not self._is_configured():
            print("[Notion] API 키 미설정 - 건너뜀")
            return 0

        if not self.sns_db_id:
            print("[Notion] SNS DB ID 없음 - 건너뜀")
            return 0

        print(f"\n[Notion Sync] SNS 데이터 동기화 시작 (플랫폼별 Top {top_n})...")
        saved = 0

        for platform, posts in collected.items():
            if not posts:
                continue

            # 조회수 + 좋아요 기준 정렬 후 Top N만
            sorted_posts = sorted(
                posts,
                key=lambda p: p.views + p.likes * 10,
                reverse=True
            )[:top_n]

            for post in sorted_posts:
                if self._create_post_page(post.to_dict()):
                    saved += 1

            print(f"  [{platform}] {len(sorted_posts)}건 저장")

        # Daily Log 요약 기록
        from engine.sns_crawler import SNSCrawler
        crawler = SNSCrawler()
        summary = crawler.summarize(collected)
        self._update_daily_log(summary)

        print(f"\n[Notion Sync 완료] 총 {saved}개 게시물 저장")
        print(f"  -> SNS DB: https://notion.so/{self.sns_db_id.replace('-','')}")
        return saved
