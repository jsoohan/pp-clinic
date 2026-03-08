#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP Clinic API Credit Monitor
-----------------------------
사용 중인 API 크레딧/할당량을 점검하고 부족하면 텔레그램으로 알림을 보냅니다.

체크 대상:
  - Apify (무료 $5/월)         → REST API로 실시간 사용량 조회
  - YouTube Data API v3        → 10,000 units/day → 로컬 사용량 추적
  - Gemini API                 → 로컬 호출 횟수 추적
  - Naver Search API           → 25,000 calls/day → 로컬 사용량 추적

Usage:
    python credit_monitor.py          # 스탠드얼론 실행
    python run.py credit              # 파이프라인 통합 실행
"""

import sys
import os
import json
import datetime
import requests
from typing import Dict, List
from dotenv import load_dotenv

# Windows cp949 인코딩 문제 해결
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv()


# ─────────────────────────────────────────────
#  설정
# ─────────────────────────────────────────────
# Telegram Bot 설정
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

USAGE_LOG_FILE = os.path.join("data", "api_usage_log.json")

# 알림 임계값
THRESHOLDS = {
    "apify_remaining_usd":    1.0,    # $1 미만이면 경고
    "youtube_daily_units":    8000,   # 10,000 중 8,000 초과시 경고
    "gemini_daily_calls":     950,    # 1,000 중 950 초과시 경고
    "naver_daily_calls":      22000,  # 25,000 중 22,000 초과시 경고
}


# ─────────────────────────────────────────────
#  사용량 로그 (로컬 JSON)
# ─────────────────────────────────────────────
def load_usage_log() -> dict:
    os.makedirs("data", exist_ok=True)
    today = datetime.date.today().isoformat()
    if os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") == today:
            return data
    # 하루가 바뀌면 초기화
    return {
        "date": today,
        "youtube_daily_units": 0,
        "gemini_daily_calls": 0,
        "naver_daily_calls": 0,
        "sns_runs_today": 0,
        "last_checked": "",
    }


def save_usage_log(log: dict):
    log["last_checked"] = datetime.datetime.now().isoformat()
    with open(USAGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def increment_usage(api: str, amount: int = 1):
    """run.py에서 각 API 호출 시 사용량을 기록하기 위해 외부에서 호출"""
    log = load_usage_log()
    key = f"{api}_daily_units" if api == "youtube" else f"{api}_daily_calls"
    log[key] = log.get(key, 0) + amount
    save_usage_log(log)


# ─────────────────────────────────────────────
#  API별 크레딧 체크
# ─────────────────────────────────────────────
def check_apify() -> Dict:
    token = os.getenv("APIFY_API_TOKEN", "")
    if not token or token == "your_apify_token_here":
        return {"status": "skipped", "reason": "토큰 미설정"}
    try:
        r = requests.get(
            f"https://api.apify.com/v2/users/me?token={token}", timeout=10
        )
        r.raise_for_status()
        data = r.json().get("data", {})
        plan = data.get("plan", {})

        # 이번 달 누적 사용 비용
        monthly_usage = data.get("monthlyUsage", {})
        used_usd = monthly_usage.get("totalCostUsd", 0.0)
        limit_usd = plan.get("maxMonthlyUsageUsd", 5.0)
        remaining_usd = max(0.0, limit_usd - used_usd)

        status = "ok"
        if remaining_usd < THRESHOLDS["apify_remaining_usd"]:
            status = "warning"

        return {
            "api": "Apify",
            "status": status,
            "used_usd": round(used_usd, 4),
            "limit_usd": limit_usd,
            "remaining_usd": round(remaining_usd, 4),
            "plan": plan.get("id", "FREE"),
            "message": f"${remaining_usd:.2f} 남음 (한도 ${limit_usd:.0f}/월)",
        }
    except Exception as e:
        return {"api": "Apify", "status": "error", "message": str(e)}


def check_youtube(log: dict) -> Dict:
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key or api_key == "your_youtube_api_key_here":
        return {"status": "skipped", "reason": "API 키 미설정"}

    used = log.get("youtube_daily_units", 0)
    limit = 10000
    remaining = limit - used
    status = "warning" if used >= THRESHOLDS["youtube_daily_units"] else "ok"

    return {
        "api": "YouTube Data API v3",
        "status": status,
        "used_units": used,
        "limit_units": limit,
        "remaining_units": remaining,
        "message": f"{used:,} / {limit:,} units 사용 (오늘)",
    }


def check_naver(log: dict) -> Dict:
    naver_id = os.getenv("NAVER_CLIENT_ID", "")
    if not naver_id or naver_id == "your_naver_id_here":
        return {"status": "skipped", "reason": "API 키 미설정"}

    used = log.get("naver_daily_calls", 0)
    limit = 25000
    status = "warning" if used >= THRESHOLDS["naver_daily_calls"] else "ok"

    return {
        "api": "Naver Search API",
        "status": status,
        "used_calls": used,
        "limit_calls": limit,
        "remaining_calls": limit - used,
        "message": f"{used:,} / {limit:,} calls 사용 (오늘)",
    }


def check_gemini(log: dict) -> Dict:
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        return {"status": "skipped", "reason": "API 키 미설정"}

    used = log.get("gemini_daily_calls", 0)
    limit = 1000  # Gemini 2.5 Flash 기본 무료 쿼터
    status = "warning" if used >= THRESHOLDS["gemini_daily_calls"] else "ok"

    return {
        "api": "Gemini API",
        "status": status,
        "used_calls": used,
        "limit_calls": limit,
        "remaining_calls": limit - used,
        "message": f"{used:,} / {limit:,} calls 사용 (오늘)",
    }


# ─────────────────────────────────────────────
#  텔레그램 알림 발송
# ─────────────────────────────────────────────
def send_telegram_alert(warnings: List[Dict]) -> bool:
    """Telegram Bot API로 경고 메시지 발송"""
    token = TELEGRAM_BOT_TOKEN
    chat_id = TELEGRAM_CHAT_ID

    if not token or not chat_id:
        print("[Telegram] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 미설정 - .env 확인")
        return False

    today = datetime.date.today().strftime("%Y-%m-%d")
    lines = [f"*[PP Clinic] API 크레딧 경고* ({today})", ""]

    for w in warnings:
        api = w.get("api", "Unknown")
        msg = w.get("message", "")
        icon = "🔴" if w.get("status") == "error" else "🟡"
        lines.append(f"{icon} *{api}*")
        lines.append(f"   {msg}")

    lines += [
        "",
        "🔧 빠른 조치 링크:",
        "• [Apify 충전](https://console.apify.com/billing)",
        "• [Google Cloud 할당량](https://console.cloud.google.com/apis/dashboard)",
        "• [Naver API 사용량](https://developers.naver.com/apps/)",
    ]

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[Telegram] 경고 메시지 발송 완료 → chat_id: {chat_id}")
        return True
    except Exception as e:
        print(f"[Telegram ERROR] {e}")
        return False


# ─────────────────────────────────────────────
#  메인 실행
# ─────────────────────────────────────────────
def run_credit_check(send_alert: bool = True) -> List[Dict]:
    """
    모든 API 크레딧을 체크하고, 경고가 있으면 텔레그램 발송.
    Returns: results (List of check dicts)
    """
    print("\n[Credit Monitor] API 크레딧 점검 시작...\n")
    log = load_usage_log()

    results = [
        check_apify(),
        check_youtube(log),
        check_naver(log),
        check_gemini(log),
    ]

    # 출력
    print(f"{'API':<25} {'상태':<10} {'현황'}")
    print("-" * 65)
    warnings = []
    for r in results:
        if r.get("status") == "skipped":
            continue
        icon = {"ok": "[OK]", "warning": "[!!]", "error": "[XX]"}.get(r.get("status"), "[??]")
        print(f"{r.get('api',''):<25} {icon} {r.get('status',''):<8} {r.get('message','')}")
        if r.get("status") in ("warning", "error"):
            warnings.append(r)

    if warnings:
        print(f"\n[!!] 경고 {len(warnings)}건 발생!")
        if send_alert:
            send_telegram_alert(warnings)
    else:
        print("\n✅ 모든 API 크레딧 정상")

    save_usage_log(log)
    return results


if __name__ == "__main__":
    run_credit_check()
