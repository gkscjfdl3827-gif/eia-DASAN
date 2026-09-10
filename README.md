# EIA-Verifier (환경영향평가서 거짓·부실 검증 시스템)

환경영향평가서의 **수기 조사야장(Field Notes)**, **경비/식사 영수증(Receipts)**, **최종 본안 보고서 총괄표(Summary Table)** 이미지를 대조하여 주요 위법 및 부실 작성 혐의를 자동으로 교차 검증하는 감사 분석 도구입니다.

---

## 🎯 3대 핵심 검증 기능

1. **조사 시간 - 영수증 시공간 충돌 (Time & Space Collision)**
   - 현지조사 시간(예: 09:30~15:30) 정한가운데에 식당 카드 결제 영수증이 존재하는 경우 (`[CRITICAL]` 적발)
   - 조사 종료 직후, 조사지에서 식당까지의 물리적 이동 소요시간이 턱없이 부족한 경우 (`[CRITICAL]` 적발)
2. **조사자 이동 속도 및 동선 모순 (Unrealistic Trajectory)**
   - 산악 식생/포유류 조사 등 험준한 지형에서 도보 허용한계 속도(시속 5km)를 초과하여 비현실적인 고속 주파가 기록된 경우
   - 동일 조사자가 동시간대에 다른 격격 지점에 출현하는 순간이동(시간 중복) 감지
3. **생물종 누락 및 왜곡 대조 (Species Omission & Fraud)**
   - 수기 조사야장에 기록된 모든 생물종과 최종 보고서 총괄표 목록을 전수 대조
   - 야장에는 적혀있지만 총괄표에서 누락된 종을 자동 추출하고, **환경부 멸종위기 야생생물(Ⅰ·Ⅱ급) 및 천연기념물** 여부를 즉시 판별하여 고의 은폐 의혹 제기

---

## 🚀 실행 방법

### 1. CLI (명령줄) 실행

```bash
# 내장된 대표 감사 시나리오(풍력발전단지 가상 감사) 즉시 검증
python run_cli.py --demo

# 실제 이미지 파일을 지정하여 검증 실행 (Gemini API 키 지정 가능)
python run_cli.py --notes ./sample_notes.jpg --receipt ./sample_receipt.jpg --summary ./sample_summary.png --api-key YOUR_GEMINI_API_KEY
```

### 2. Streamlit 웹 대시보드 실행

인터랙티브 지도, 타임라인, 생물종 대조표, 드래그앤드롭 이미지 업로드를 지원하는 웹 대시보드:

```bash
python -m streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속하여 확인하실 수 있습니다.

---

## 📁 프로젝트 구조

```
eia_verifier/
├── app.py                     # Streamlit 인터랙티브 웹 UI
├── run_cli.py                 # CLI 콘솔 실행기
├── requirements.txt           # 의존성 패키지
├── eia_verifier/
│   ├── models.py              # Pydantic 데이터 모델 (야장, 영수증, 총괄표, 리포트)
│   ├── endangered_db.py       # 환경부 멸종위기 야생생물 및 천연기념물 사전
│   ├── geo_utils.py           # 구면 대권거리(Haversine), 속도 산정, 이동시간 추정
│   ├── validator.py           # 3대 핵심 모순 검증 엔진
│   ├── extractor.py           # 멀티모달 비전 AI (Gemini Vision) 이미지 파서
│   ├── reporter.py            # 터미널 & Markdown 감사 보고서 포맷터
│   └── mock_data.py           # 가상 실전 시나리오 데이터셋
└── tests/
    └── test_validator.py      # 자동화 단위 테스트
```
