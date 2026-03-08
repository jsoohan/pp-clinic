#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""오늘 수집된 JSON을 Notion에 동기화하는 테스트 스크립트"""
import sys, os, json, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from engine.notion_sns_sync import NotionSNSSync
from engine.sns_crawler import SNSPost

# 오늘 JSON 파일 로드
today = datetime.date.today().strftime("%Y%m%d")
json_path = os.path.join("data", f"sns_layer1_{today}.json")

if not os.path.exists(json_path):
    print(f"파일 없음: {json_path}")
    sys.exit(1)

with open(json_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

# dict → SNSPost 객체로 복원
collected = {}
for platform, posts in raw.items():
    collected[platform] = []
    for p in posts:
        post = SNSPost(
            platform=p.get("platform",""),
            keyword=p.get("keyword",""),
            title=p.get("title",""),
            url=p.get("url",""),
            views=p.get("views",0),
            likes=p.get("likes",0),
            comments=p.get("comments",0),
            shares=p.get("shares",0),
            author=p.get("author",""),
            published_at=p.get("published_at",""),
        )
        collected[platform].append(post)
    print(f"  {platform}: {len(collected[platform])}건 로드")

print(f"\nNotion 동기화 시작...")
syncer = NotionSNSSync()
saved = syncer.sync(collected, top_n=5)
print(f"\n완료: {saved}건 저장됨")
