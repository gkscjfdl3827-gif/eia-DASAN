"""Realistic mock dataset for testing and immediate demonstration."""
from datetime import date, datetime
from typing import Tuple, List

from .models import (
    ObservedSpecies,
    ReceiptRecord,
    SummaryTableRecord,
    SurveyPoint,
    SurveySession,
)


def get_sample_eia_case() -> Tuple[str, List[SurveySession], List[ReceiptRecord], List[SummaryTableRecord]]:
    """
    실제 환경영향평가 거짓·부실 작성 감사에서 적발되는 전형적인 시나리오 생성:
    1. 산악 조사(09:30 ~ 15:30) 정한가운데(12:45)에 식당 카드 결제 영수증 존재
    2. 산악 지형 6km를 20분 만에 이동(시속 18km/h)한 비현실적 이동 기록
    3. 수기 야장에는 멸종위기종(삵, 하늘다람쥐)이 적혀 있으나 최종 보고서 총괄표에서 누락
    """
    project_name = "○○산 풍력발전단지 개발사업 환경영향평가서"
    survey_date = date(2024, 5, 15)

    # 1. 수기 조사야장 데이터
    survey_session = SurveySession(
        session_id="SURVEY-20240515-01",
        date=survey_date,
        investigator_name="김철수",
        category="육상동식물상(포유류/식생)",
        start_time=datetime(2024, 5, 15, 9, 30),
        end_time=datetime(2024, 5, 15, 15, 30),
        route_name="풍력발전기 1~5호기 설치 예정 능선부",
        points=[
            SurveyPoint(
                point_name="정점 1 (임도 입구)",
                time=datetime(2024, 5, 15, 9, 30),
                latitude=37.5300,
                longitude=127.5600,
                notes="산림 진입 시작",
            ),
            SurveyPoint(
                point_name="정점 2 (제1능선 안부)",
                time=datetime(2024, 5, 15, 11, 0),
                latitude=37.5350,
                longitude=127.5680,
                notes="신갈나무 군락, 소나무 확인",
            ),
            SurveyPoint(
                point_name="정점 3 (제2봉우리 암릉)",
                time=datetime(2024, 5, 15, 11, 20),  # 20분 만에 6km 이동 (시속 18km/h -> 모순!)
                latitude=37.5700,
                longitude=127.6200,
                notes="암릉 지대 통과",
            ),
            SurveyPoint(
                point_name="정점 4 (계곡부 배후지)",
                time=datetime(2024, 5, 15, 14, 0),
                latitude=37.5400,
                longitude=127.5750,
                notes="흔적 조사 및 트랩 확인",
            ),
        ],
        observed_species=[
            ObservedSpecies(species_name="신갈나무", count="군락 우점", evidence_type="직접관찰"),
            ObservedSpecies(species_name="소나무", count="다수", evidence_type="직접관찰"),
            ObservedSpecies(species_name="노루", count="1개체", evidence_type="직접목격"),
            # [CRITICAL] 멸종위기종
            ObservedSpecies(
                species_name="삵(배설물 흔적)",
                scientific_name="Prionailurus bengalensis",
                count="배설흔 2개소",
                evidence_type="배설물 흔적",
                point_name="정점 2 (제1능선 안부)",
            ),
            ObservedSpecies(
                species_name="하늘다람쥐(배설흔)",
                scientific_name="Pteromys volans",
                count="배설흔",
                evidence_type="배설물 흔적",
                point_name="정점 4 (계곡부 배후지)",
            ),
            ObservedSpecies(species_name="고라니", count="발자국 다수", evidence_type="발자국"),
            ObservedSpecies(species_name="멧돼지", count="굴광흔", evidence_type="흔적"),
        ],
        source_file="야장_스캔_20240515.jpg",
    )

    # 2. 식사 영수증 데이터 (치명적 충돌)
    receipt1 = ReceiptRecord(
        receipt_id="RCP-20240515-001",
        payment_time=datetime(2024, 5, 15, 12, 45, 12),  # 조사시간(09:30~15:30) 정중앙!
        store_name="용문산 토종마을식당",
        store_category="일반음식점",
        address="경기 양평군 용문면 용문산로 123",
        latitude=37.4988,
        longitude=127.5936,
        amount=65000,
        payer_name="김철수",
        source_file="영수증_점심_20240515.jpg",
    )

    # 3. 최종 보고서 총괄표 데이터 (멸종위기종 누락)
    summary_table = SummaryTableRecord(
        table_title="[표 4-2-1] 육상 동·식물상 조사결과 총괄표 (본안 보고서)",
        category="육상동식물상",
        recorded_species=[
            "신갈나무",
            "소나무",
            "노루",
            "고라니",
            "멧돼지",
            "청설모",
            "다람쥐",
            "꿩",
        ],
        source_file="총괄표_본안_P142.png",
    )

    return project_name, [survey_session], [receipt1], [summary_table]
