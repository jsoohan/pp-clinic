# 📊 팽팽클리닉: 확장이 용이한 휴리스틱 데이터 트래커 (Spreadsheet Template)

엑셀/구글 스프레드시트로 수천 개의 키워드와 원시 데이터를 핸들링하기 위한 확장형 템플릿 구조입니다.

---

## 📂 Sheet 1: [Master_Keywords] - 키워드 뱅크
수천 개의 키워드를 '분류'와 '우선순위'에 따라 관리합니다.

| Category | Sub-Category | Keyword | Priority | Target Region | Language |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 06. Risk | Side Effects | 울쎄라 볼패임 | P0 | Local | KR |
| 08. Geofencing | Global | 糸リフト | P1 | Japan | JP |
| 04. Pivot | Home Care Fail | 홈케어 기기 효과 없음 | P2 | Global | KR |
| ... | (무한 추가 가능) | ... | ... | ... | ... |

---

## 📂 Sheet 2: [Raw_Data_Lake] - 무손실 데이터 수집
API나 크롤러가 쏟아내는 모든 로우 데이터를 담습니다. (추후 AI 분석의 재료)

| Timestamp | Source | Key/Url | Value | Sentiment | Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-03-07 | Naver_Place | A병원 리뷰 | 4.2 | Negative | 대기가 너무 길어요 |
| 2026-03-07 | Google_Trends | 실리프팅 | 85 | - | 상승 추세 |
| 2026-03-07 | T-Map | 목적지 검색량 | 1,200 | - | 경쟁사 유입 분석 |

---

## 📂 Sheet 3: [Intelligence_Dashboard] - 요약 및 시각화
원장님께서 매일/매주 보게 될 '의사결정 보드'입니다.

*   **View 1: Daily loss captures** (오늘 뺏어올 경쟁사의 약점 5선)
*   **View 2: Weekly SOV Rank** (리프팅 시장 내 점유율 피벗 테이블)
*   **View 3: AEO Visibility Tracker** (주요 AI 엔진별 브랜드 노출 확률)

---

## 🛡️ 확장성 유지 비결 (Scalability Secret)

1.  **VLOOKUP-Free:** 모든 데이터는 '키워드 ID'를 기준으로 연동되어, 키워드가 1,000개로 늘어나도 시트 구조가 깨지지 않습니다.
2.  **API Friendly:** n8n이나 파이썬 스크립트가 이 시트의 특정 영역에 데이터를 'Append'만 하면 자동으로 시각화가 갱신됩니다.
3.  **Global Layer:** 'Language' 필드를 통해 한국어 데이터와 일어/중국어 데이터를 분리하고 결합하는 것이 자유롭습니다.
