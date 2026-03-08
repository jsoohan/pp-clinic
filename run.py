#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP Clinic Market Intelligence - Main Runner
Usage: python run.py [daily|weekly|aeo|sns|all]
"""

import sys
import os
import datetime

# Windows UTF-8 인코딩 강제 설정 (stdout wrapper 대신 환경변수 방식)
import os
os.environ.setdefault("PYTHONUTF8", "1")
if os.name == "nt":
    os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine.pp_clinic_intel_engine import PPClinicIntelligenceEngine
from engine.review_crawler import ReviewCrawlerCoordinator
from engine.sns_crawler import SNSCrawler
from credit_monitor import run_credit_check
from competitor_config import COMPETITOR_CLINICS, REVIEWS_PER_PLATFORM

SEED_KEYWORDS = [
    "실리프팅", "울쎄라", "인모드", "실리프팅 부작용",
    "안면거상", "안티에이징", "볼처짐", "심술보"
]

# SNS Layer 1 키워드 (.env의 SNS_KEYWORDS 또는 기본값)
_sns_kw_env = os.getenv("SNS_KEYWORDS", "")
SNS_KEYWORDS = [kw.strip() for kw in _sns_kw_env.split(",") if kw.strip()] or [
    "실리프팅", "피부관리", "강남피부과", "안티에이징", "울쎄라"
]

# 크롤러에서 수집한 실제 리뷰가 없을 경우 사용하는 샘플 (테스트용)
SAMPLE_REVIEWS = [
    "상담 후 억지로 패키지 결제 유도됨. 다시는 안 옴.",
    "대기가 너무 길었어요. 원장님 진료시간 5분도 안됨.",
    "실리프팅 했는데 딤플 생겼어요. 관리도 안 해줌.",
]

AEO_QUERIES = [
    "강남 실리프팅 잘 하는 병원 추천해줘",
    "신사역 피부과 리프팅 잘 하는 곳",
    "Thread lift clinic Sinsa Seoul recommendation",
]


def run_daily(engine):
    print("\n[Daily Mode] 리뷰 수집 + 감성 분석 시작...\n")

    # [1] 실제 리뷰 크롤링
    coordinator = ReviewCrawlerCoordinator()
    active_clinics = [c for c in COMPETITOR_CLINICS
                      if c.get("naver_id") or c.get("kakao_id")]

    reviews_to_analyze = []
    if active_clinics:
        print(f"  {len(active_clinics)}개 병원에서 리뷰 수집 중...")
        live_reviews = coordinator.crawl_all(active_clinics, count_per_platform=REVIEWS_PER_PLATFORM)
        reviews_to_analyze = [r.text for r in live_reviews if r.text.strip()]
        print(f"  총 {len(reviews_to_analyze)}개 리뷰 수집 완료\n")
    else:
        print("  [INFO] competitor_config.py에 병원 ID가 없어 샘플 리뷰로 실행합니다.")
        print("  -> competitor_config.py에 naver_id / kakao_id를 입력하면 실제 리뷰가 수집됩니다.\n")
        reviews_to_analyze = SAMPLE_REVIEWS

    # [2] Gemini 감성 분석 + Notion 저장
    opportunity_count = 0
    for review_text in reviews_to_analyze:
        result = engine.analyze_review_sentiment(review_text)
        print(f"  리뷰: {review_text[:45]}...")
        print(f"  점수: {result.get('sentiment_score')} | 기회 포착: {result.get('is_competitor_opportunity')}")
        print(f"  요약: {result.get('summary')}\n")
        if result.get("is_competitor_opportunity"):
            opportunity_count += 1
            engine.sync_to_notion(result, label="경쟁사 Loss 포착")

    print(f"  [완료] 기회 포착 건수: {opportunity_count} / {len(reviews_to_analyze)}")


def run_weekly(engine):
    print("\n[Weekly Mode] 휴리스틱 키워드 확장 + 트렌드 수집\n")
    all_keywords = []
    for seed in SEED_KEYWORDS[:3]:
        kws = engine.generate_heuristic_keywords(seed, count=20)
        all_keywords.extend(kws)
        print(f"  '{seed}' => {len(kws)}개 키워드 생성")

    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    trend = engine.get_naver_trend(
        all_keywords[:5],
        week_ago.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d")
    )
    print(f"\n  네이버 트렌드 수집 상태: {trend.get('status', 'ok')}")


def run_aeo(engine):
    print("\n[AEO Mode] AI 엔진 노출도 점검 시작...\n")
    for query in AEO_QUERIES:
        result = engine.check_aeo_visibility(query)
        status = "언급됨 [OK]" if result["pp_clinic_mentioned"] else "미언급 [주의]"
        print(f"  질문: {query}")
        print(f"  결과: {status}")
        print(f"  답변: {result.get('answer_snippet', '')[:120]}...\n")


def run_sns():
    print("\n[SNS Mode] Layer 1 공개 SNS 데이터 수집 시작...\n")
    max_per = int(os.getenv("SNS_MAX_PER_KEYWORD", "5"))

    crawler = SNSCrawler()
    collected = crawler.collect_all(keywords=SNS_KEYWORDS, max_per_keyword=max_per)
    crawler.print_report(collected)

    # JSON으로 저장 (data/ 폴더)
    saved_path = crawler.save_to_json(collected)
    print(f"\n[SNS] 수집 데이터 저장: {saved_path}")

    # Notion 동기화 (subprocess로 분리 실행 - stdout wrapper 충돌 방지)
    import subprocess
    print("\n[Notion] SNS 데이터 Notion 동기화 중...")
    result = subprocess.run(
        [sys.executable, "_sync_to_notion.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        capture_output=False,
    )
    if result.returncode != 0:
        print("[Notion] 동기화 중 오류 발생 - _sync_to_notion.py 직접 실행으로 확인하세요")

    print("[Done] SNS 대시보드 업데이트 완료")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"

    print("=" * 55)
    print("PP Clinic Market Intelligence Engine")
    print(f"   Mode: {mode.upper()} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    if not os.path.exists(".env"):
        print("\n[ERROR] .env 파일이 없습니다.")
        print("  .env.template을 복사하여 .env 파일을 만들고 API 키를 입력하세요.")
        sys.exit(1)

    engine = PPClinicIntelligenceEngine()

    if mode == "daily":
        run_daily(engine)
    elif mode == "weekly":
        run_weekly(engine)
    elif mode == "aeo":
        run_aeo(engine)
    elif mode == "sns":
        run_sns()   # SNS Layer 1 — engine 불필요
    elif mode == "credit":
        run_credit_check()  # API 크레딧 점검 + 이메일 알림
    elif mode == "dashboard":
        # 대시보드 JSON 생성 (data_generator.py 호출)
        import subprocess
        print("\n[Dashboard Mode] dashboard_data.json 생성 중...")
        result = subprocess.run(
            [sys.executable, "data_generator.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        sys.exit(result.returncode)
    elif mode == "all":
        run_daily(engine)
        run_weekly(engine)
        run_aeo(engine)
        run_sns()
        run_credit_check()  # 마지막에 크레딧 점검
    else:
        print(f"Unknown mode: {mode}. Use [daily|weekly|aeo|sns|credit|dashboard|all]")
        sys.exit(1)

    print("\n[Done] Notion 대시보드를 확인하세요.")


if __name__ == "__main__":
    main()
