#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNS 키워드 자동 확장 스크립트
Gemini API로 피부과/클리닉 관련 SNS 키워드를 확장하고 .env에 저장
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from engine.pp_clinic_intel_engine import PPClinicIntelligenceEngine

SEED_WORDS = [
    "실리프팅", "울쎄라", "인모드", "강남피부과",
    "피부관리", "안티에이징", "리프팅시술"
]

def main():
    engine = PPClinicIntelligenceEngine()
    all_keywords = set()

    print("=== Gemini 키워드 확장 시작 ===\n")
    for seed in SEED_WORDS:
        kws = engine.generate_heuristic_keywords(seed, count=15)
        all_keywords.update(kws)
        print(f"  '{seed}' → {len(kws)}개")

    # 중복 제거 + 너무 짧거나 긴 키워드 제외
    filtered = sorted(list(set([
        kw.strip() for kw in all_keywords
        if 2 <= len(kw.strip()) <= 20
    ])))

    print(f"\n총 {len(filtered)}개 키워드 생성 (공백 없는 해시태그형)")
    print("키워드 목록:", filtered[:30], "...")

    # .env에 SNS_KEYWORDS 업데이트
    env_path = ".env"
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    kw_line = "SNS_KEYWORDS=" + ",".join(filtered)

    if "SNS_KEYWORDS=" in content:
        import re
        content = re.sub(r"SNS_KEYWORDS=.*", kw_line, content)
    else:
        content += f"\n{kw_line}\n"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n[완료] .env SNS_KEYWORDS 업데이트 → {len(filtered)}개 키워드")
    print(f"샘플: {', '.join(filtered[:10])}")

if __name__ == "__main__":
    main()
