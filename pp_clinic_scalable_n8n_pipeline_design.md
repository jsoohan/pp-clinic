# ⚡ 팽팽클리닉: n8n 기반 무한 확장형 데이터 파이프라인 설계

추후 소스(Source)나 키워드가 늘어나도 **워크플로우를 새로 짜지 않고 '설정'만 추가**하면 작동하는 모듈형 파이프라인 구조입니다.

---

## 1. 전역 설정 모듈 (Global Config Loader)
*   **기능:** 노션의 [Master Config DB]에 등록된 모든 '활성화' 키워드와 소스 리스트를 10분마다 읽어옴.
*   **확장성:** 새로운 키워드나 플랫폼을 버튼 하나로 파이프라인에 즉시 배포 가능.

---

## 2. 엔진별 수집 모듈 (Modular Collectors)
각 플랫폼별로 전용 수집기를 독립적으로 운영합니다.

*   **[Collector A] Naver/Google Trends:** API를 통해 대량의 검색 트렌드 수집.
*   **[Collector B] Review Scrapers:** 네이버, 카카오, 티맵의 최일선 리뷰 데이터 크롤링.
*   **[Collector C] SNS Intelligence:** 경쟁사 10곳의 SNS(블로그, 인스타 등) 활동 지표 추출.
*   **[Collector D] AI Engine Probe (AEO):** ChatGPT, Gemini API에 페르소나 질문을 던져 응답 데이터 수집.

---

## 3. AI 인텔리전스 가공 (AI Processing Layer)
수집된 로우 데이터를 '인사이트'로 정제합니다.

*   **Sentiment Engine:** (GPT-4o mini 등 활용) 리뷰 텍스트의 감성과 핵심 불만 키워드 요약.
*   **Keyword Expansion:** 수집된 트렌드를 바탕으로 "다음 주에 추가하면 좋을 연관 키워드 20개" 자동 제안.
*   **Global Translator:** 해외 데이터를 한국어로 자동 번역하여 대시보드와 통합.

---

## 4. 최종 결과 배포 (Delivery Layer)
*   **Dashboard Sync:** 정제된 데이터를 Notion DB와 Spreadsheet에 즉시 기록.
*   **Emergency Alert (Slack/Kakao):** 경쟁사 부작용 급증이나 리뷰 리스크 감지 시 즉시 메시지 발송.

---

## 💎 확장을 위한 기술적 가이드 (Developer's Note)

1.  **JSON-based Logic:** 모든 수집 로직은 플랫폼 이름을 변수 처리하여, 새로운 플랫폼 추가 시 `platform_name: "Tiktok"`만 전달하면 수집 프로세스가 자동으로 생성되게 설계.
2.  **Rate Limit Management:** 플랫폼별 차단 방지를 위한 Proxy 및 Delay 로직을 중앙에서 관리하여 대량 수집 시 안정성 확보.
3.  **Heuristic Expansion:** AI 가공 단계에서 '새로운 장비명'이 포착되면 이를 [Master Config]에 자동으로 '검토 대상'으로 등록하는 셀프-러닝(Self-learning) 루프 구축 가능.
