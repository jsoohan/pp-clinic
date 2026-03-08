#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from credit_monitor import check_apify, check_youtube, check_naver, check_gemini, load_usage_log
import requests, datetime

log = load_usage_log()
results = [check_apify(), check_youtube(log), check_naver(log), check_gemini(log)]

today = datetime.date.today().strftime("%Y-%m-%d")
lines = [f"*[PP Clinic] API 크레딧 현황 보고* ({today})", ""]

icons = {"ok": "[OK]", "warning": "[!!]", "error": "[XX]"}
for r in results:
    if r.get("status") == "skipped":
        continue
    icon = icons.get(r.get("status", "ok"), "[?]")
    lines.append(f"{icon} *{r.get('api', '')}*")
    lines.append(f"   {r.get('message', '')}")

lines += ["", "-> `python run.py credit` 으로 언제든 재확인 가능"]
text = "\n".join(lines)

token = os.getenv("TELEGRAM_BOT_TOKEN", "")
chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
resp = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
    timeout=10
)
print("발송:", resp.json().get("ok"))
print("메시지:")
print(text)
