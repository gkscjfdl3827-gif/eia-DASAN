"""Core validation engine for EIA anomaly detection."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from .endangered_db import lookup_endangered_species, normalize_species_name
from .geo_utils import (
    calculate_speed_kmh,
    estimate_driving_minutes,
    geocode_korean_address,
    haversine_distance_km,
)
from .models import (
    Anomaly,
    AnomalyType,
    AuditReport,
    ReceiptRecord,
    Severity,
    SummaryTableRecord,
    SurveySession,
)


class EIAValidator:
    """환경영향평가서 거짓·부실 검증 엔진"""

    def __init__(
        self,
        max_hiking_speed_kmh: float = 5.0,     # 산악 도보 허용 최대 속도 (초과 시 경고)
        critical_hiking_speed_kmh: float = 8.0,# 산악 도보 절대 한계 속도 (초과 시 중대 이상치)
        min_point_duration_minutes: float = 10.0, # 정점별 최소 필요 체류시간
    ):
        self.max_hiking_speed_kmh = max_hiking_speed_kmh
        self.critical_hiking_speed_kmh = critical_hiking_speed_kmh
        self.min_point_duration_minutes = min_point_duration_minutes

    def validate_receipt_conflicts(
        self, surveys: List[SurveySession], receipts: List[ReceiptRecord]
    ) -> List[Anomaly]:
        """영수증과 조사 시간·동선 간의 시공간 충돌 검증."""
        anomalies: List[Anomaly] = []

        for survey in surveys:
            survey_date = survey.start_time.date()
            # 같은 날짜에 발생한 영수증 필터링
            day_receipts = [r for r in receipts if r.payment_time.date() == survey_date]

            for receipt in day_receipts:
                # 1. 조사 시간 도중 결제 발생 (Time Overlap)
                if survey.start_time <= receipt.payment_time <= survey.end_time:
                    anomalies.append(
                        Anomaly(
                            anomaly_id=f"ANO-RCP-{uuid.uuid4().hex[:6].upper()}",
                            anomaly_type=AnomalyType.TIME_OVERLAP_RECEIPT,
                            severity=Severity.CRITICAL,
                            title="조사 진행 시간 도중 영수증 결제 발생 (거짓/부실 의심)",
                            description=(
                                f"조사자 [{survey.investigator_name}]의 조사 시간 "
                                f"({survey.start_time.strftime('%H:%M')} ~ {survey.end_time.strftime('%H:%M')}) 도중인 "
                                f"{receipt.payment_time.strftime('%H:%M')}에 식당/상점 "
                                f"'{receipt.store_name}'에서 결제한 영수증이 증빙으로 첨부되었습니다."
                            ),
                            evidence={
                                "survey_id": survey.session_id,
                                "investigator": survey.investigator_name,
                                "survey_period": f"{survey.start_time.strftime('%Y-%m-%d %H:%M')} ~ {survey.end_time.strftime('%H:%M')}",
                                "receipt_id": receipt.receipt_id,
                                "receipt_time": receipt.payment_time.strftime("%Y-%m-%d %H:%M:%S"),
                                "store_name": receipt.store_name,
                                "store_address": receipt.address,
                                "amount": receipt.amount,
                            },
                            recommendation=(
                                "해당 시간대에 조사가 중단되었는지, 또는 실제 현장 조사를 수행하지 않고 "
                                "시간을 허위 기재(거짓작성)했는지 소명 요구 및 조사일지 정밀 감사 필요."
                            ),
                        )
                    )
                    continue

                # 2. 조사 종료 직후/직전 물리적 이동 시간 부족 검증 (Space-Time Gap)
                survey_lat, survey_lon = None, None
                if survey.points:
                    last_point = survey.points[-1]
                    survey_lat, survey_lon = last_point.latitude, last_point.longitude

                rcp_lat, rcp_lon = receipt.latitude, receipt.longitude
                if (rcp_lat is None or rcp_lon is None) and receipt.address:
                    coords = geocode_korean_address(receipt.address)
                    if coords:
                        rcp_lat, rcp_lon = coords

                # 좌표가 모두 있는 경우 거리 및 소요시간 계산
                if survey_lat and survey_lon and rcp_lat and rcp_lon:
                    dist_km = haversine_distance_km(survey_lat, survey_lon, rcp_lat, rcp_lon)
                    min_travel_min = estimate_driving_minutes(dist_km)

                    # 조사 종료 후 결제한 경우
                    if receipt.payment_time > survey.end_time:
                        elapsed_min = (receipt.payment_time - survey.end_time).total_seconds() / 60.0
                        if elapsed_min < min_travel_min and dist_km > 3.0:
                            anomalies.append(
                                Anomaly(
                                    anomaly_id=f"ANO-MOV-RCP-{uuid.uuid4().hex[:6].upper()}",
                                    anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL_RECEIPT,
                                    severity=Severity.CRITICAL,
                                    title="조사 종료 후 식당 결제까지 물리적 이동시간 부족",
                                    description=(
                                        f"조사 종료({survey.end_time.strftime('%H:%M')}) 후 불과 {elapsed_min:.1f}분 만에 "
                                        f"{dist_km:.1f}km 떨어진 '{receipt.store_name}'에서 결제되었습니다. "
                                        f"도로 주행 최소 필요시간({min_travel_min:.1f}분)보다 현저히 부족합니다."
                                    ),
                                    evidence={
                                        "survey_end": survey.end_time.strftime("%H:%M"),
                                        "receipt_time": receipt.payment_time.strftime("%H:%M"),
                                        "elapsed_minutes": round(elapsed_min, 1),
                                        "distance_km": round(dist_km, 2),
                                        "min_required_minutes": round(min_travel_min, 1),
                                        "store_name": receipt.store_name,
                                    },
                                    recommendation=(
                                        "조사가 기재된 시각보다 일찍 종료되었거나 조사 지점이 허위 기재되었을 가능성이 높으므로 "
                                        "실제 조사 종료 시각과 이동 경로 증빙 확인 필요."
                                    ),
                                )
                            )

        return anomalies

    def validate_movement_feasibility(self, surveys: List[SurveySession]) -> List[Anomaly]:
        """조사 지점 간 이동 속도 및 동선 모순 검증."""
        anomalies: List[Anomaly] = []

        for survey in surveys:
            # 시간순 정렬된 지점 목록
            points_with_time = [p for p in survey.points if p.time and p.latitude and p.longitude]
            points_with_time.sort(key=lambda x: x.time)

            for i in range(len(points_with_time) - 1):
                p1 = points_with_time[i]
                p2 = points_with_time[i + 1]

                time_diff = p2.time - p1.time
                dist_km = haversine_distance_km(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
                speed_kmh = calculate_speed_kmh(dist_km, time_diff)

                # 1. 시간 역전 또는 동시 발생인데 거리가 먼 경우 (순간이동)
                if time_diff.total_seconds() <= 60 and dist_km > 0.5:
                    anomalies.append(
                        Anomaly(
                            anomaly_id=f"ANO-TELE-{uuid.uuid4().hex[:6].upper()}",
                            anomaly_type=AnomalyType.TIME_OVERLAP_SURVEY,
                            severity=Severity.CRITICAL,
                            title="동일 조사자 동시간대 격격 지점 순간이동(시간 중복)",
                            description=(
                                f"조사자 [{survey.investigator_name}]가 {p1.time.strftime('%H:%M')}에 "
                                f"[{p1.point_name}]에서 [{p2.point_name}]까지 {dist_km:.2f}km를 불과 "
                                f"{time_diff.total_seconds()/60.0:.1f}분 만에 이동한 것으로 기록됨."
                            ),
                            evidence={
                                "point1": p1.point_name,
                                "point2": p2.point_name,
                                "distance_km": round(dist_km, 2),
                                "time_diff_sec": time_diff.total_seconds(),
                            },
                            recommendation="복수 인원이 대리 조사했거나 조사 시간을 허위 기재한 명백한 정황임.",
                        )
                    )
                # 2. 산악 도보 이동 속도 초과
                elif speed_kmh > self.max_hiking_speed_kmh:
                    is_critical = speed_kmh > self.critical_hiking_speed_kmh
                    anomalies.append(
                        Anomaly(
                            anomaly_id=f"ANO-SPD-{uuid.uuid4().hex[:6].upper()}",
                            anomaly_type=AnomalyType.EXCESSIVE_MOVEMENT_SPEED,
                            severity=Severity.CRITICAL if is_critical else Severity.WARNING,
                            title=(
                                f"산악 현지조사 한계 이동속도 초과 ({speed_kmh:.1f} km/h)"
                                if is_critical
                                else f"비정상적 고속 도보 이동 주의 ({speed_kmh:.1f} km/h)"
                            ),
                            description=(
                                f"[{p1.point_name}] -> [{p2.point_name}] 구간 ({dist_km:.2f}km)을 "
                                f"{time_diff.total_seconds()/60.0:.1f}분 만에 이동. "
                                f"계산된 속도는 {speed_kmh:.1f} km/h로 일반 산악 도보 한계({self.max_hiking_speed_kmh} km/h)를 현저히 초과."
                            ),
                            evidence={
                                "point1": p1.point_name,
                                "point2": p2.point_name,
                                "distance_km": round(dist_km, 2),
                                "duration_min": round(time_diff.total_seconds() / 60.0, 1),
                                "calculated_speed_kmh": round(speed_kmh, 1),
                            },
                            recommendation="산악 지형에서 정상적인 조사를 수행하며 도보로 주파할 수 없는 속도이므로 날림 조사 여부 확인 필요.",
                        )
                    )

        return anomalies

    def validate_species_omissions(
        self, surveys: List[SurveySession], summary_tables: List[SummaryTableRecord]
    ) -> List[Anomaly]:
        """조사야장에 적힌 생물종과 최종 보고서 총괄표 간의 누락 및 왜곡 대조."""
        anomalies: List[Anomaly] = []

        # 1. 총괄표에 기재된 모든 종 집합 (정규화된 이름)
        summary_species_set = set()
        for table in summary_tables:
            for s in table.recorded_species:
                norm = normalize_species_name(s)
                if norm:
                    summary_species_set.add(norm)

        # 2. 야장에 기록된 생물종 전수 조사
        seen_species_checks = set()

        for survey in surveys:
            for obs in survey.observed_species:
                raw_name = obs.species_name
                norm_name = normalize_species_name(raw_name)

                if not norm_name or norm_name in seen_species_checks:
                    continue
                seen_species_checks.add(norm_name)

                # 총괄표에 해당 종이 있는가? (정확 일치 대조)
                in_summary = norm_name in summary_species_set

                if not in_summary:
                    # 법정보호종(멸종위기 야생생물 / 천연기념물) 확인
                    endangered_info = lookup_endangered_species(norm_name)

                    if endangered_info:
                        canon_name, info = endangered_info
                        anomalies.append(
                            Anomaly(
                                anomaly_id=f"ANO-ENDANG-{uuid.uuid4().hex[:6].upper()}",
                                anomaly_type=AnomalyType.ENDANGERED_SPECIES_OMISSION,
                                severity=Severity.CRITICAL,
                                title=f"[중대 위반] 법정보호종 '{canon_name}' 야장 기록 후 총괄표 누락 의심",
                                description=(
                                    f"수기 조사야장(세션: {survey.session_id}, 조사자: {survey.investigator_name})에는 "
                                    f"'{raw_name}'(등급: {info['grade']}, {info['monument']}) 관찰 기록이 명시되어 있으나, "
                                    f"최종 보고서 총괄표에 전혀 반영되지 않고 누락되었습니다."
                                ),
                                evidence={
                                    "species_name": canon_name,
                                    "raw_note_text": raw_name,
                                    "grade": info["grade"],
                                    "monument": info["monument"],
                                    "category": info["category"],
                                    "survey_session": survey.session_id,
                                    "investigator": survey.investigator_name,
                                    "evidence_type": obs.evidence_type or "미기재",
                                    "count": obs.count or "미기재",
                                },
                                recommendation=(
                                    "환경영향평가법상 가장 엄벌에 처해지는 '법정보호종 고의 은폐·축소(거짓작성)' 혐의가 짙으므로, "
                                    "야장 원본 및 총괄표 작성 경위에 대한 감사 청구와 정밀 소명 요구 필수."
                                ),
                            )
                        )
                    else:
                        anomalies.append(
                            Anomaly(
                                anomaly_id=f"ANO-SP-OMIT-{uuid.uuid4().hex[:6].upper()}",
                                anomaly_type=AnomalyType.SPECIES_OMISSION,
                                severity=Severity.INFO,
                                title=f"일반 생물종 '{norm_name}' 총괄표 미반영",
                                description=(
                                    f"야장에 기록된 '{norm_name}'이 최종 총괄표에 집계되지 않았습니다. "
                                    f"(야장 기록: {survey.investigator_name}, {obs.count or '관찰'})"
                                ),
                                evidence={
                                    "species_name": norm_name,
                                    "survey_session": survey.session_id,
                                },
                                recommendation="단순 집계 누락인지 확인 요망.",
                            )
                        )

        return anomalies

    def run_audit(
        self,
        project_name: str,
        surveys: List[SurveySession],
        receipts: List[ReceiptRecord],
        summary_tables: List[SummaryTableRecord],
    ) -> AuditReport:
        """전체 검증 실행 및 감사 리포트 생성."""
        anomalies: List[Anomaly] = []

        # 1. 영수증 충돌 검증
        anomalies.extend(self.validate_receipt_conflicts(surveys, receipts))

        # 2. 이동 동선 및 속도 모순 검증
        anomalies.extend(self.validate_movement_feasibility(surveys))

        # 3. 생물종 누락 검증
        anomalies.extend(self.validate_species_omissions(surveys, summary_tables))

        # 심각도순 정렬 (CRITICAL > WARNING > INFO)
        severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
        anomalies.sort(key=lambda a: severity_order.get(a.severity, 99))

        all_note_species = set()
        for s in surveys:
            for obs in s.observed_species:
                norm = normalize_species_name(obs.species_name)
                if norm:
                    all_note_species.add(norm)

        all_sum_species = set()
        for t in summary_tables:
            for s in t.recorded_species:
                norm = normalize_species_name(s)
                if norm:
                    all_sum_species.add(norm)

        return AuditReport(
            report_id=f"REP-{uuid.uuid4().hex[:8].upper()}",
            project_name=project_name,
            surveys_count=len(surveys),
            receipts_count=len(receipts),
            species_in_notes_count=len(all_note_species),
            species_in_summary_count=len(all_sum_species),
            anomalies=anomalies,
        )
