#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP Clinic Dashboard Data Generator
실제 API 데이터를 수집하여 dashboard_data.json 생성
Usage: python data_generator.py
"""

import os
import sys
import json
import datetime
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from engine.pp_clinic_intel_engine import PPClinicIntelligenceEngine
from engine.review_crawler import ReviewCrawlerCoordinator
from competitor_config import COMPETITOR_CLINICS, REVIEWS_PER_PLATFORM

TODAY = datetime.date.today()
YESTERDAY = TODAY - datetime.timedelta(days=1)
WEEK_AGO = TODAY - datetime.timedelta(days=7)

# ─────────────────────────────────────────────
# 퍼널 단계별 수집 키워드 (Naver DataLab용)
# ─────────────────────────────────────────────
FUNNEL_KEYWORDS = {
    "stage_01_awareness": ["얼굴 처짐", "나이 들어 보이는 이유", "피부 탄력 저하"],
    "stage_02_problem":   ["볼 처짐 심한가", "팔자주름 심해지는 나이", "턱선 없어지는 이유"],
    "stage_03_homecare":  ["홈케어 리프팅 기기 추천", "가정용 HIFU", "콜라겐 크림 효과"],
    "stage_04_pivot":     ["홈케어 리프팅 기기 효과 없음", "셀프 리프팅 한계", "피부과 가야하나"],
    "stage_05_explore":   ["실리프팅이란", "울쎄라 vs 실리프팅", "리프팅 시술 종류"],
    "stage_06_risk":      ["실리프팅 부작용", "실리프팅 볼패임", "실리프팅 통증"],
    "stage_07_compare":   ["강남 실리프팅 잘하는 곳", "실리프팅 명의", "팽팽클리닉 실리프팅"],
    "stage_08_local":     ["신사동 실리프팅", "압구정 피부과 실리프팅", "강남역 근처 리프팅"],
    "stage_09_intent":    ["팽팽클리닉 상담", "실리프팅 이벤트", "실리프팅 첫 방문 할인"],
    "stage_10_convert":   ["팽팽클리닉 예약", "실리프팅 예약"],
}

AEO_QUERIES = [
    "강남 실리프팅 잘 하는 병원 추천해줘",
    "신사역 피부과 리프팅 잘 하는 곳",
    "Thread lift clinic Sinsa Seoul recommendation",
]

# ─────────────────────────────────────────────
# Fallback 기본 데이터 (API 없을 때)
# ─────────────────────────────────────────────
FALLBACK_STAGE_COUNTS = {
    "stage_01_awareness": 12400,
    "stage_02_problem":    8900,
    "stage_03_homecare":   6700,
    "stage_04_pivot":      4200,
    "stage_05_explore":    3840,
    "stage_06_risk":       2900,
    "stage_07_compare":    1680,
    "stage_08_local":       980,
    "stage_09_intent":       47,
    "stage_10_convert":      23,
}

FALLBACK_KPI = {
    "today_inquiries":  47,
    "today_bookings":   23,
    "search_vol_main":  3840,
    "competitor_risks": 3,
}


# ─────────────────────────────────────────────
# 1. Naver Trend 수집
# ─────────────────────────────────────────────
def collect_naver_trends(engine: PPClinicIntelligenceEngine) -> dict:
    """퍼널 단계별 키워드 트렌드 수집"""
    print("\n[1/4] Naver DataLab 트렌드 수집 중...")
    trends = {}

    for stage_key, kws in list(FUNNEL_KEYWORDS.items())[:6]:  # API quota 절약: 상위 6단계
        try:
            result = engine.get_naver_trend(
                kws[:3],
                WEEK_AGO.strftime("%Y-%m-%d"),
                TODAY.strftime("%Y-%m-%d")
            )
            if result.get("status") == "skipped":
                print(f"  [{stage_key}] API 키 없음 - 기본값 사용")
                trends[stage_key] = {"keywords": kws, "ratio": []}
                continue

            # 최신 ratio값 (0~100 상대 검색량)
            ratios = []
            for group in result.get("results", []):
                data = group.get("data", [])
                if data:
                    ratios.append({
                        "keyword": group.get("title"),
                        "latest_ratio": data[-1].get("ratio", 0),
                        "prev_ratio": data[-7].get("ratio", 0) if len(data) >= 7 else data[0].get("ratio", 0),
                    })

            trends[stage_key] = {
                "keywords": kws,
                "ratios": ratios,
                "collected_at": datetime.datetime.now().isoformat()
            }
            print(f"  [{stage_key}] {len(ratios)}개 키워드 트렌드 수집 완료")
            time.sleep(0.5)

        except Exception as e:
            print(f"  [{stage_key}] ERROR: {e}")
            trends[stage_key] = {"keywords": kws, "ratios": [], "error": str(e)}

    return trends


# ─────────────────────────────────────────────
# 2. 경쟁사 리뷰 수집 + 감성 분석
# ─────────────────────────────────────────────
def collect_competitor_reviews(engine: PPClinicIntelligenceEngine) -> list:
    """경쟁사 리뷰 수집 및 감성 분석"""
    print("\n[2/4] 경쟁사 리뷰 크롤링 + 감성 분석 중...")
    coordinator = ReviewCrawlerCoordinator()
    active_clinics = [c for c in COMPETITOR_CLINICS if c.get("naver_id") or c.get("kakao_id")]

    analyzed = []

    if not active_clinics:
        print("  [INFO] competitor_config.py에 병원 ID 없음 - 샘플로 실행")
        sample_reviews = [
            {"clinic": "경쟁사A", "text": "시술 후 볼이 꺼진 것 같아요. 관리도 안 해줌.", "platform": "naver"},
            {"clinic": "경쟁사B", "text": "대기가 너무 길고 원장님 진료시간 5분도 안됨.", "platform": "naver"},
            {"clinic": "경쟁사C", "text": "공장형이라는 느낌. 비용도 불투명하고.", "platform": "kakao"},
        ]
        for r in sample_reviews:
            sentiment = engine.analyze_review_sentiment(r["text"])
            analyzed.append({
                "clinic": r["clinic"],
                "text": r["text"][:80],
                "platform": r["platform"],
                "sentiment_score": sentiment.get("sentiment_score", 0),
                "complaint_keywords": sentiment.get("complaint_keywords", []),
                "is_opportunity": sentiment.get("is_competitor_opportunity", False),
                "summary": sentiment.get("summary", ""),
                "collected_at": datetime.datetime.now().isoformat()
            })
            time.sleep(1)
    else:
        live_reviews = coordinator.crawl_all(active_clinics, count_per_platform=REVIEWS_PER_PLATFORM)
        for rev in live_reviews[:10]:  # API quota 절약: 최대 10건 분석
            if not rev.text.strip():
                continue
            sentiment = engine.analyze_review_sentiment(rev.text)
            analyzed.append({
                "clinic": getattr(rev, 'clinic_name', '경쟁사'),
                "text": rev.text[:80],
                "platform": getattr(rev, 'platform', 'naver'),
                "sentiment_score": sentiment.get("sentiment_score", 0),
                "complaint_keywords": sentiment.get("complaint_keywords", []),
                "is_opportunity": sentiment.get("is_competitor_opportunity", False),
                "summary": sentiment.get("summary", ""),
                "collected_at": datetime.datetime.now().isoformat()
            })
            time.sleep(1)
        print(f"  총 {len(analyzed)}건 분석 완료")

    opportunity_count = sum(1 for r in analyzed if r["is_opportunity"])
    print(f"  공략 기회 포착: {opportunity_count}건")
    return analyzed


# ─────────────────────────────────────────────
# 3. AEO (AI 엔진 노출도)
# ─────────────────────────────────────────────
def collect_aeo(engine: PPClinicIntelligenceEngine) -> list:
    """ChatGPT/Gemini 우리 병원 언급 빈도 체크"""
    print("\n[3/4] AEO(AI 엔진 노출도) 점검 중...")
    results = []
    for query in AEO_QUERIES:
        result = engine.check_aeo_visibility(query)
        results.append(result)
        status = "✅ 언급됨" if result.get("pp_clinic_mentioned") else "❌ 미언급"
        print(f"  {status} | {query[:40]}...")
        time.sleep(1)
    return results


# ─────────────────────────────────────────────
# 4. KPI 집계 (CRM 데이터 - 현재는 수동/샘플)
# ─────────────────────────────────────────────
def collect_kpi() -> dict:
    """
    실제 CRM 연동 시 이 함수를 수정하세요.
    현재: .env의 MANUAL_KPI_XXX 값 또는 fallback 기본값 사용
    """
    print("\n[4/4] KPI 집계 중 (수동 입력 또는 CRM 연동)...")
    def _get_int(key: str, default: int) -> int:
        val = os.getenv(key, "").strip()
        return int(val) if val.isdigit() else default

    kpi = {
        "today_inquiries":    _get_int("MANUAL_KPI_INQUIRIES", FALLBACK_KPI["today_inquiries"]),
        "today_bookings":     _get_int("MANUAL_KPI_BOOKINGS", FALLBACK_KPI["today_bookings"]),
        "search_vol_main":    _get_int("MANUAL_KPI_SEARCH_VOL", FALLBACK_KPI["search_vol_main"]),
        "competitor_risks":   _get_int("MANUAL_KPI_RISKS", FALLBACK_KPI["competitor_risks"]),
        "target_inquiries":   60,
        "target_bookings":    36,
        "target_conversion":  60.0,
    }
    conv_rate = round(kpi["today_bookings"] / max(kpi["today_inquiries"], 1) * 100, 1)
    kpi["conversion_rate"] = conv_rate
    print(f"  문의 {kpi['today_inquiries']}건 | 예약 {kpi['today_bookings']}건 | 전환율 {conv_rate}%")
    return kpi


# ─────────────────────────────────────────────
# 5. 트렌드 → 퍼널 카운트/퍼센트 계산
# ─────────────────────────────────────────────
def compute_funnel_metrics(trends: dict) -> dict:
    """
    Naver DataLab ratio를 퍼널 단계 카운트로 환산
    fallback: hardcoded 값 사용
    """
    metrics = {}
    max_count = FALLBACK_STAGE_COUNTS["stage_01_awareness"]

    for stage_key, fallback_count in FALLBACK_STAGE_COUNTS.items():
        trend_data = trends.get(stage_key, {})
        ratios = trend_data.get("ratios", [])

        if ratios:
            # 평균 ratio (0~100) → 상대적 규모 추산
            avg_ratio = sum(r["latest_ratio"] for r in ratios) / len(ratios)
            prev_ratio = sum(r.get("prev_ratio", avg_ratio) for r in ratios) / len(ratios)
            trend_pct = round((avg_ratio - prev_ratio) / max(prev_ratio, 0.1) * 100, 1)
            count = int(avg_ratio * max_count / 100) if avg_ratio > 0 else fallback_count
            top_keyword = ratios[0]["keyword"] if ratios else ""
        else:
            count = fallback_count
            trend_pct = 0.0
            top_keyword = ""

        metrics[stage_key] = {
            "count": count,
            "trend_pct": trend_pct,
            "top_keyword": top_keyword,
        }

    return metrics


# ─────────────────────────────────────────────
# 6. AI 인사이트 생성 (Gemini 요약)
# ─────────────────────────────────────────────
def generate_ai_alerts(engine: PPClinicIntelligenceEngine,
                        reviews: list,
                        aeo: list,
                        kpi: dict) -> list:
    """전체 데이터를 종합해 오늘의 AI 액션 알림 생성"""
    print("\n AI 인사이트 알림 생성 중...")
    opportunity_reviews = [r for r in reviews if r["is_opportunity"]]
    aeo_missed = [a for a in aeo if not a.get("pp_clinic_mentioned")]

    alerts = []

    # 경쟁사 기회 포착 알림
    if opportunity_reviews:
        keywords = []
        for r in opportunity_reviews[:3]:
            keywords.extend(r.get("complaint_keywords", [])[:2])
        alerts.append({
            "level": "red",
            "icon": "🚨",
            "title": f"경쟁사 약점 포착 {len(opportunity_reviews)}건",
            "body": f"불만 키워드: {', '.join(list(set(keywords))[:5])}. 즉시 우리 강점 콘텐츠 배포 권장."
        })

    # 전환율 경고
    if kpi["conversion_rate"] < 50:
        alerts.append({
            "level": "yellow",
            "icon": "⚡",
            "title": f"09→10단계 전환율 {kpi['conversion_rate']}% (목표 60%)",
            "body": "상담 → 예약 전환이 낮습니다. 카카오 즉시 응답 속도 및 첫 방문 할인 이벤트 점검이 필요합니다."
        })

    # AEO 미노출 경고
    if aeo_missed:
        alerts.append({
            "level": "yellow",
            "icon": "🤖",
            "title": f"AI 엔진 {len(aeo_missed)}개 쿼리에서 미노출",
            "body": f"'{aeo_missed[0]['query'][:30]}...' 등 쿼리에서 팽팽클리닉 미언급. AEO 콘텐츠 강화 필요."
        })

    # 기본 긍정 알림
    if kpi["today_bookings"] >= kpi.get("target_bookings", 30):
        alerts.append({
            "level": "green",
            "icon": "✅",
            "title": f"오늘 예약 {kpi['today_bookings']}건 달성",
            "body": "일일 예약 목표 달성. SNS 콘텐츠 성과 지속 모니터링."
        })

    if not alerts:
        alerts.append({
            "level": "green",
            "icon": "✅",
            "title": "오늘 특이사항 없음",
            "body": "모든 지표가 정상 범위입니다. 예정된 콘텐츠 게시를 진행하세요."
        })

    return alerts


# ─────────────────────────────────────────────
# 7. 최종 JSON 조립 및 저장
# ─────────────────────────────────────────────
def build_dashboard_json(kpi: dict,
                          funnel_metrics: dict,
                          reviews: list,
                          aeo: list,
                          alerts: list,
                          trends: dict) -> dict:
    """dashboard.html이 fetch()로 읽을 JSON 구조 생성"""

    # 경쟁사 감성 요약
    competitor_summary = []
    clinic_groups = {}
    for r in reviews:
        name = r["clinic"]
        if name not in clinic_groups:
            clinic_groups[name] = []
        clinic_groups[name].append(r["sentiment_score"])

    for i, (name, scores) in enumerate(clinic_groups.items()):
        avg = sum(scores) / len(scores)
        sentiment_0_100 = int((avg + 1) / 2 * 100)
        is_opportunity = any(r["is_opportunity"] for r in reviews if r["clinic"] == name)
        competitor_summary.append({
            "rank": i + 1,
            "name": name,
            "sentiment": sentiment_0_100,
            "alert": "공략기회" if is_opportunity else ("주의" if sentiment_0_100 < 70 else "양호"),
            "alertClass": "alert-red" if is_opportunity else ("alert-yellow" if sentiment_0_100 < 70 else "alert-green"),
            "pain": reviews[[r["clinic"] for r in reviews].index(name)]["summary"][:30] if name in [r["clinic"] for r in reviews] else ""
        })

    # AEO 요약
    aeo_mention_rate = round(
        sum(1 for a in aeo if a.get("pp_clinic_mentioned")) / max(len(aeo), 1) * 100, 1
    )

    return {
        "meta": {
            "generated_at": datetime.datetime.now().isoformat(),
            "date": TODAY.isoformat(),
            "data_version": "2.0",
        },
        "kpi": kpi,
        "funnel_metrics": funnel_metrics,
        "competitor_reviews": reviews,
        "competitor_summary": competitor_summary,
        "aeo": {
            "results": aeo,
            "mention_rate_pct": aeo_mention_rate,
        },
        "alerts": alerts,
        "raw_trends": {k: v for k, v in trends.items()},  # 디버깅용
    }


# ─────────────────────────────────────────────
# 주간/월간 요약 생성
# ─────────────────────────────────────────────
def build_weekly_summary(data: dict, trends: dict) -> dict:
    """주간 급등 키워드 + 병목 단계 요약"""
    hot = []
    for stage_key, td in trends.items():
        for r in td.get("ratios", []):
            pct = round((r["latest_ratio"] - r.get("prev_ratio", r["latest_ratio"]))
                        / max(r.get("prev_ratio", 0.1), 0.1) * 100, 1)
            if pct > 10:
                hot.append({"keyword": r["keyword"], "trend": f"↑{pct}%", "stage": stage_key})
    hot.sort(key=lambda x: float(x["trend"].replace("↑","").replace("%","")), reverse=True)

    fm = data.get("funnel_metrics", {})
    bottleneck = "09단계"
    min_count = 9999999
    for k, v in fm.items():
        c = v.get("count", 9999999)
        if c < min_count and k not in ("stage_10_convert",):
            min_count = c
            bottleneck = k.replace("stage_","").replace("_"," ").strip()

    cr = data.get("kpi", {}).get("conversion_rate", 49)
    content_tips = [
        f"퍼널 {bottleneck} 단계 콘텐츠 강화 권장",
        "경쟁사 부작용 리뷰 소재로 신뢰 콘텐츠 1편 제작",
        "네이버 블로그 롱테일 키워드 포스팅 2편 이상 게시",
    ]
    if hot:
        content_tips.insert(0, f'"{hot[0]["keyword"]}" 급등 키워드 SEO 포스팅 즉시 제작')

    return {
        "hot_keywords": hot[:5],
        "bottleneck_stage": bottleneck,
        "prev_conversion_rate": max(cr - 2.5, 0),
        "content_tips": content_tips[:4],
    }


def build_monthly_summary(data: dict) -> dict:
    """월간 KPI 달성률 요약"""
    kpi = data.get("kpi", {})
    cr  = kpi.get("conversion_rate", 49)
    return {
        "avg_conversion_rate": cr,
        "explorer_conversion": float(os.getenv("MANUAL_KPI_EXPLORER_CONVERSION", "2.4")),
        "revisit_rate":        float(os.getenv("MANUAL_KPI_REVISIT_RATE", "34")),
        "mom_revenue_growth":  float(os.getenv("MANUAL_KPI_MOM_GROWTH", "12")),
    }


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="PP Clinic Dashboard Data Generator")
    parser.add_argument("--mode", choices=["daily", "weekly", "monthly", "dashboard"],
                        default="daily", help="수집/발송 모드 (기본: daily)")
    parser.add_argument("--dry-run", action="store_true",
                        help="텔레그램 발송 없이 로컬 출력만")
    parser.add_argument("--no-telegram", action="store_true",
                        help="JSON만 생성하고 텔레그램 발송 건너뜀")
    args = parser.parse_args()

    mode = args.mode
    dry_run = args.dry_run or args.no_telegram

    print("=" * 55)
    print(f"PP Clinic Data Generator v2.1  [{mode.upper()}]")
    print(f"   Date: {TODAY} | Time: {datetime.datetime.now().strftime('%H:%M')}")
    print(f"   Dry-run: {dry_run}")
    print("=" * 55)

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_data.json")

    # ── 데이터 수집 ──
    engine  = PPClinicIntelligenceEngine()
    trends  = collect_naver_trends(engine)
    reviews = collect_competitor_reviews(engine)
    aeo     = collect_aeo(engine)
    kpi     = collect_kpi()

    funnel_metrics = compute_funnel_metrics(trends)
    alerts         = generate_ai_alerts(engine, reviews, aeo, kpi)
    data           = build_dashboard_json(kpi, funnel_metrics, reviews, aeo, alerts, trends)

    # ── JSON 저장 ──
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ dashboard_data.json 저장 완료")
    print(f"   KPI: 문의 {kpi['today_inquiries']}건 | 예약 {kpi['today_bookings']}건")
    print(f"   경쟁사: {len(reviews)}건 | 공략기회: {sum(1 for r in reviews if r['is_opportunity'])}건")
    print(f"   AEO 노출률: {data['aeo']['mention_rate_pct']}%")

    # ── 텔레그램 발송 ──
    if dry_run:
        print("\n[dry-run] 텔레그램 발송 건너뜀 — 위 데이터로 메시지 내용 확인:")

    from engine.telegram_reporter import TelegramReporter
    reporter = TelegramReporter()

    # dry-run 시 토큰을 빈 값으로 만들어 출력만 하도록
    if dry_run:
        reporter.token = ""

    if mode in ("daily", "dashboard"):
        print("\n[Telegram] Daily 리포트 발송 중...")
        reporter.send_daily(data)

    elif mode == "weekly":
        weekly_summary = build_weekly_summary(data, trends)
        print("\n[Telegram] Weekly 리포트 발송 중...")
        reporter.send_weekly(data, weekly_summary)

    elif mode == "monthly":
        monthly_summary = build_monthly_summary(data)
        print("\n[Telegram] Monthly 리포트 발송 중...")
        reporter.send_monthly(data, monthly_summary)

    print("\n[Done] 완료")


if __name__ == "__main__":
    main()

