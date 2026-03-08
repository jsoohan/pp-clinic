"""
네이버 검색 결과 HTML에서 Place ID 자동 추출
모바일 검색 결과에 포함된 map.naver.com 링크에서 숫자 ID 파싱
"""
import requests
import re
import time
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13; SM-S911B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://m.naver.com",
}

CLINICS = [
    "리팅성형외과 강남",
    "셀팅의원 청담",
    "비브이의원 강남",
    "리프톤피부과의원 신사",
    "포엔의원 강남",
    "신사엘성형외과",
    "신사인피부과",
    "청담BLS의원",
    "메이퓨어의원 강남",
    "플래티넘의원 신사",
]

def find_place_id(query: str) -> str | None:
    """네이버 모바일 검색에서 Place ID 추출"""
    url = f"https://m.search.naver.com/search.naver"
    params = {"query": query, "where": "m_place", "sm": "mtp_hty"}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=8)
        html = r.text

        # 패턴 1: map.naver.com/p/entry/place/숫자
        m = re.search(r'map\.naver\.com/p/entry/place/(\d+)', html)
        if m:
            return m.group(1)

        # 패턴 2: place.naver.com/숫자
        m = re.search(r'place\.naver\.com/[^/]*/(\d{8,})', html)
        if m:
            return m.group(1)

        # 패턴 3: data-id="숫자" 형태
        m = re.search(r'"businessId"\s*:\s*"(\d{8,})"', html)
        if m:
            return m.group(1)

        # 패턴 4: /entry/place/숫자
        m = re.search(r'/entry/place/(\d{8,})', html)
        if m:
            return m.group(1)

        return None
    except Exception as e:
        print(f"  [ERROR] {query}: {e}")
        return None


if __name__ == "__main__":
    print("=== 네이버 Place ID 자동 수집 ===\n")
    results = {}
    for clinic in CLINICS:
        pid = find_place_id(clinic)
        results[clinic] = pid
        status = f"ID: {pid}" if pid else "ID 없음"
        print(f"  {clinic[:20]:<20} → {status}")
        time.sleep(1.5)  # 요청 간격

    print("\n=== 결과 요약 ===")
    found = {k: v for k, v in results.items() if v}
    print(f"수집 성공: {len(found)}/{len(CLINICS)}\n")
    for name, pid in found.items():
        print(f'  "{name}": "{pid}"')
