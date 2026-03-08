#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PP Clinic Telegram Reporter
daily / weekly / monthly 리포트를 텔레그램 봇으로 발송
"""

import os
import requests
import datetime
from typing import Optional


class TelegramReporter:
    def __init__(self):
        self.token         = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id       = os.getenv("TELEGRAM_CHAT_ID", "")
        self.dashboard_url = os.getenv("DASHBOARD_URL", "")  # 예: GitHub Pages URL

    def _send(self, text: str) -> bool:
        """텔레그램 메시지 발송 (MarkdownV2)"""
        if not self.token or not self.chat_id:
            print("[Telegram] 토큰/채팅ID 미설정 — .env에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 추가 필요")
            print("──── 발송 예정 메시지 ────")
            print(text)
            print("──────────────────────────")
            return False
        resp = requests.post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
            timeout=15
        )
        ok = resp.json().get("ok", False)
        if ok:
            print(f"[Telegram] OK - sent ({len(text)} chars)")
        else:
            print(f"[Telegram] FAIL: {resp.json()}")
        return ok

    def _bar(self, rate: float, target: float, width: int = 8) -> str:
        """진행률 바 생성 (예: ████░░░░ 49%)"""
        pct  = min(rate / max(target, 1) * 100, 100)
        fill = int(pct / 100 * width)
        bar  = "█" * fill + "░" * (width - fill)
        return f"{bar} {pct:.0f}%"

    # ─────────────────────────────────────────────
    # DAILY REPORT
    # ─────────────────────────────────────────────
    def send_daily(self, data: dict) -> bool:
        alerts   = data.get("alerts", [])
        aeo      = data.get("aeo", {})
        fm       = data.get("funnel_metrics", {})
        reviews  = data.get("competitor_reviews", [])
        raw      = data.get("raw_trends", {})
        today    = data.get("meta", {}).get("date", datetime.date.today().isoformat())

        # ── ① 급등 키워드 TOP3 (퍼널 전체에서) ──
        hot_kws = []
        for stage_key, td in raw.items():
            stage_num = stage_key.replace("stage_","").split("_")[0]
            for r in td.get("ratios", []):
                prev = r.get("prev_ratio", r["latest_ratio"])
                pct  = round((r["latest_ratio"] - prev) / max(prev, 0.1) * 100, 1)
                if pct > 5:
                    hot_kws.append({
                        "kw": r["keyword"],
                        "pct": pct,
                        "stage": f"{stage_num}단계"
                    })
        hot_kws.sort(key=lambda x: x["pct"], reverse=True)

        kw_block = ""
        for h in hot_kws[:3]:
            kw_block += f"\n  📈 *{h['kw']}* +{h['pct']}% ({h['stage']})"
        if not kw_block:
            kw_block = "\n  (수집 중 — Naver DataLab 트렌드 반영 대기)"

        # ── ② 퍼널 단계별 핵심 현황 ──
        stage_labels = {
            "stage_01_awareness": "01 욕구발생",
            "stage_02_problem":   "02 문제인식",
            "stage_03_homecare":  "03 홈케어시도",
            "stage_04_pivot":     "04 한계인식 ⚡",
            "stage_05_explore":   "05 시술탐색",
            "stage_06_risk":      "06 리스크평가",
        }
        funnel_block = ""
        for key, label in stage_labels.items():
            td   = raw.get(key, {})
            rats = td.get("ratios", [])
            if rats:
                top = rats[0]
                prev = top.get("prev_ratio", top["latest_ratio"])
                pct  = round((top["latest_ratio"] - prev) / max(prev, 0.1) * 100, 1)
                arrow = f"↑{pct}%" if pct > 0 else (f"↓{abs(pct)}%" if pct < 0 else "→")
                color = "🔴" if pct > 20 else ("🟡" if pct > 5 else "🟢")
                funnel_block += f"\n  {color} *{label}*: {top['keyword']} {arrow}"
            else:
                funnel_block += f"\n  ⚪ *{label}*: 데이터 수집 중"

        # ── ③ 경쟁사 공략 기회 ──
        opps = [r for r in reviews if r.get("is_opportunity")]
        if opps:
            opp_block = ""
            for r in opps[:2]:
                kws = r.get("complaint_keywords", [])[:2]
                opp_block += f"\n  🔴 *{r['clinic']}* — {r.get('summary','')[:40]}"
                if kws:
                    opp_block += f"\n     키워드: {', '.join(kws)}"
        else:
            opp_block = "\n  ✅ 오늘 포착된 경쟁사 약점 없음"

        # ── ④ AEO ──
        aeo_rate = aeo.get("mention_rate_pct", 0)
        aeo_line = (
            f"🔴 *{aeo_rate}%* — AI 검색 미노출. 블로그·롱테일 콘텐츠 강화 시급"
            if aeo_rate < 10 else
            f"🟡 *{aeo_rate}%* — 부분 노출. AEO 콘텐츠 추가 필요"
            if aeo_rate < 30 else
            f"🟢 *{aeo_rate}%* — 양호"
        )

        # ── ⑤ P0 액션 ──
        red_alerts = [a for a in alerts if a.get("level") == "red"]
        action_block = ""
        for a in red_alerts[:2]:
            action_block += f"\n  🚨 {a.get('title','')}\n     ▶ {a.get('body','')[:70]}"
        if not action_block:
            action_block = "\n  ✅ 오늘 긴급 액션 없음. 예정 콘텐츠 진행"

        link = f"\n\n[대시보드 열기]({self.dashboard_url})" if self.dashboard_url else ""

        text = (
            f"📊 *[팽팽클리닉] 마케팅 일일 브리핑* {today}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n🔑 *오늘 급등 키워드*"
            f"{kw_block}"
            f"\n\n🎯 *퍼널 단계별 검색 트렌드*"
            f"{funnel_block}"
            f"\n\n🕵️ *경쟁사 공략 기회*"
            f"{opp_block}"
            f"\n\n🤖 *AEO 노출률*: {aeo_line}"
            f"\n\n🚦 *P0 즉시 액션*"
            f"{action_block}"
            f"{link}"
        )
        return self._send(text)

    # ─────────────────────────────────────────────
    # WEEKLY REPORT
    # ─────────────────────────────────────────────
    def send_weekly(self, data: dict, weekly_summary: dict) -> bool:
        kpi    = data.get("kpi", {})
        alerts = data.get("alerts", [])
        fm     = data.get("funnel_metrics", {})
        today  = datetime.date.today()
        week_start = (today - datetime.timedelta(days=6)).strftime("%m/%d")
        week_end   = today.strftime("%m/%d")

        # 급등 키워드
        hot_keywords = weekly_summary.get("hot_keywords", [])
        kw_lines = ""
        for kw in hot_keywords[:3]:
            kw_lines += f"\n  📈 *{kw.get('keyword', '')}* {kw.get('trend', '')}"

        # 전환율 변화
        cr_prev = weekly_summary.get("prev_conversion_rate", 0)
        cr_now  = kpi.get("conversion_rate", 0)
        cr_change = round(cr_now - cr_prev, 1)
        cr_arrow = "▲" if cr_change >= 0 else "▼"

        # 퍼널 병목 단계
        bottleneck_stage = weekly_summary.get("bottleneck_stage", "09단계")

        # 콘텐츠 제안
        content_tips = weekly_summary.get("content_tips", ["이번 주 퍼널 병목 단계 위주 콘텐츠 강화 권장"])

        text = (
            f"📈 *[팽팽클리닉] 주간 리포트* {week_start}~{week_end}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n🔑 *이번 주 급등 키워드*"
            f"{kw_lines if kw_lines else chr(10) + '  수집 중...'}"
            f"\n\n📊 *전환율 변화*\n"
            f"  상담→예약: *{cr_now}%* ({cr_arrow}{abs(cr_change)}%p) {self._bar(cr_now, 60)}\n"
            f"\n⚡ *퍼널 병목: {bottleneck_stage}*\n"
            f"  {content_tips[0] if content_tips else '대시보드 확인 권장'}"
            f"\n\n✍️ *이번 주 콘텐츠 방향*\n"
            + "".join(f"  • {t}\n" for t in content_tips[:3])
            + f"\n" + (f"[대시보드 열기]({self.dashboard_url})" if self.dashboard_url else "_주간 모니터링 탭에서 SOV 상세 확인_")
        )
        return self._send(text)

    # ─────────────────────────────────────────────
    # MONTHLY REPORT
    # ─────────────────────────────────────────────
    def send_monthly(self, data: dict, monthly_summary: dict) -> bool:
        kpi   = data.get("kpi", {})
        aeo   = data.get("aeo", {})
        today = datetime.date.today()
        month_label = today.strftime("%Y-%m")

        # KPI 달성률 체크
        def _kpi_row(label, current, target, unit=""):
            ok = current >= target * 0.9
            icon = "✅" if ok else "❌"
            return f"  {icon} {label}: *{current}{unit}* / 목표 {target}{unit}\n"

        cr_monthly = monthly_summary.get("avg_conversion_rate", kpi.get("conversion_rate", 0))
        explorer_rate = monthly_summary.get("explorer_conversion", 2.4)
        revisit_rate  = monthly_summary.get("revisit_rate", 34)
        mom_growth    = monthly_summary.get("mom_revenue_growth", 0)

        # 다음 달 전략 (분기 기반)
        next_month = (today.month % 12) + 1
        quarter_map = {
            1: "Q1 — 새해 결심·봄맞이 (01~03단계 공략)",
            2: "Q1 — 봄맞이 변신 캠페인 (03~05단계 전환)",
            3: "Q1 — 졸업·입학 2030 타겟 (04단계 Pivot)",
            4: "Q2 — 결혼식 시즌 D-day 공략 (05~06단계)",
            5: "Q2 — 야외 자외선 피부 고민 콘텐츠 (06단계)",
            6: "Q2 — 부작용 불안 해소 원장 라이브 (06단계)",
            7: "Q3 — 가을 준비 before/after 강조 (07~08단계)",
            8: "Q3 — 추석 전 특가 이벤트 (08~09단계)",
            9: "Q3 — 지역 SEO 강화 (신사동 키워드)",
            10: "Q4 — 연말 파티 특가 이벤트 집중 (09~10단계)",
            11: "Q4 — 선물권 도입 + 재방문 CRM (10단계)",
            12: "Q4 — 새해 조기 예약 유도 캠페인 (전 단계)",
        }
        next_strategy = quarter_map.get(next_month, "다음 달 전략 수립 필요")

        text = (
            f"📋 *[팽팽클리닉] 월간 리포트* {month_label}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"\n💰 *매출 성과*\n"
            f"  MoM 성장률: *{mom_growth:+.1f}%*\n"
            f"\n🎯 *KPI 달성률*\n"
            + _kpi_row("탐색→상담 전환", explorer_rate, 3.0, "%")
            + _kpi_row("상담→예약 전환", cr_monthly, 60.0, "%")
            + _kpi_row("재방문율", revisit_rate, 40.0, "%")
            + f"\n🤖 *AEO 노출률: {aeo.get('mention_rate_pct', 0)}%*\n"
            f"  {'✅ 목표 달성' if aeo.get('mention_rate_pct', 0) >= 30 else '❌ 강화 필요 — 블로그·롱테일 콘텐츠 증가'}"
            f"\n\n📅 *다음 달 집중 전략*\n"
            f"  {next_strategy}"
            f"\n\n" + (f"[대시보드 열기]({self.dashboard_url})" if self.dashboard_url else "_월간 모니터링 탭 + KPI 테이블 전체 검토 권장_")
        )
        return self._send(text)

    def test_send(self) -> bool:
        """연결 테스트 메시지 발송"""
        text = (
            "🤖 *[팽팽클리닉] 텔레그램 봇 연결 테스트*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ 연결 성공!\n"
            "  • Daily 리포트: 매일 오후 10시\n"
            "  • Weekly 리포트: 매주 일요일 오후 10시\n"
            "  * Monthly 리포트: 매달 마지막 날 오후 10시"
            + (f"\n\n[대시보드 열기]({self.dashboard_url})" if self.dashboard_url else "")
        )
        return self._send(text)
