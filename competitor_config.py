"""
경쟁사 병원 설정 파일 (competitor_config.py)
Naver Place ID는 자동 수집 스크립트(find_competitors.py)로 채워짐

[새 병원 추가]
COMPETITOR_CLINICS 리스트에 딕셔너리 추가 → python run.py daily 실행
"""

COMPETITOR_CLINICS = [
    # ─────────────────────────────────────────────────────
    # 팽팽의원 (우리 병원 - 자체 모니터링)
    # ─────────────────────────────────────────────────────
    {
        "name": "팽팽의원",
        "is_own_clinic": True,
        "naver_id": None,     # 네이버 지도에서 확인 후 입력
        "kakao_id": None,
        "specialty": "실리프팅 전문",
        "priority": "P0",
    },

    # ─────────────────────────────────────────────────────
    # 경쟁사 TOP 10 (신사/강남 실리프팅 직접 경쟁사)
    # ─────────────────────────────────────────────────────
    {
        "name": "리팅성형외과",
        "is_own_clinic": False,
        "naver_id": "38673363",
        "kakao_id": None,
        "website": "https://liting.co.kr",
        "specialty": "리프팅 전문 성형외과, 실리프팅·안면거상·절개리프팅",
        "priority": "P1",
    },
    {
        "name": "셀팅의원 청담",
        "is_own_clinic": False,
        "naver_id": "1127453670",
        "kakao_id": None,
        "website": "https://cellting.com",
        "specialty": "줄기세포+실리프팅(셀프팅), 리프팅 전문",
        "priority": "P1",
    },
    {
        "name": "비브이의원",
        "is_own_clinic": False,
        "naver_id": "1738429526",
        "kakao_id": None,
        "website": "https://bvclinic.co.kr",
        "specialty": "실리프팅 재시술·부작용 치료 전문",
        "priority": "P1",
    },
    {
        "name": "리프톤피부과의원",
        "is_own_clinic": False,
        "naver_id": "1032127288",
        "kakao_id": None,
        "website": "https://www.liftonskin.com",
        "specialty": "실리프팅, 울쎄라, 써마지 (신사역 8번 출구 75m)",
        "priority": "P1",
    },
    {
        "name": "포엔의원",
        "is_own_clinic": False,
        "naver_id": "2005791982",
        "kakao_id": None,
        "website": "https://poenclinic.kr",
        "specialty": "프리미엄 Jamver 실리프팅",
        "priority": "P1",
    },
    {
        "name": "신사엘성형외과",
        "is_own_clinic": False,
        "naver_id": "37853231",
        "kakao_id": None,
        "website": "https://sinsael.com",
        "specialty": "실리프팅, 절개리프팅, 안면거상",
        "priority": "P1",
    },
    {
        "name": "신사인피부과",
        "is_own_clinic": False,
        "naver_id": "1320612563",
        "kakao_id": None,
        "website": "https://sinsain.com",
        "specialty": "울쎄라, 써마지, 1:1 맞춤 리프팅 (신사역 7번 출구)",
        "priority": "P2",
    },
    {
        "name": "청담BLS의원",
        "is_own_clinic": False,
        "naver_id": "32294569",
        "kakao_id": None,
        "website": "http://www.blsclinic2.com",
        "specialty": "실리프팅, 안면거상",
        "priority": "P2",
    },
    {
        "name": "메이퓨어의원",
        "is_own_clinic": False,
        "naver_id": "36351454",
        "kakao_id": None,
        "website": "https://www.maypureclinic.com",
        "specialty": "리프팅, 피부 전반 (네트워크 피부과)",
        "priority": "P2",
    },
    {
        "name": "플래티넘의원",
        "is_own_clinic": False,
        "naver_id": "1478354860",
        "kakao_id": None,
        "website": "https://platinumclinic.co.kr",
        "specialty": "티타늄 리프팅, 인모드, 쥬베룩 (신사역 인근)",
        "priority": "P2",
    },
]

# ─────────────────────────────────────────────────────
# 수집 설정
# ─────────────────────────────────────────────────────
REVIEWS_PER_PLATFORM = 5
MAX_CLINICS = 10
