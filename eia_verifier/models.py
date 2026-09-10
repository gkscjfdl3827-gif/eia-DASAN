"""Data models for EIA Verifier."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "CRITICAL"  # 중대 위반 (거짓작성 혐의 / 멸종위기종 누락 / 동시 결제)
    WARNING = "WARNING"    # 경고 (비정상적 이동 속도 / 과소 시간)
    INFO = "INFO"          # 참고 (일반 종 누락 / 경미한 불일치)


class AnomalyType(str, Enum):
    TIME_OVERLAP_RECEIPT = "TIME_OVERLAP_RECEIPT"          # 조사 시간 도중 식사/결제 발생
    IMPOSSIBLE_TRAVEL_RECEIPT = "IMPOSSIBLE_TRAVEL_RECEIPT"# 조사지-식당 간 물리적 이동 불가
    EXCESSIVE_MOVEMENT_SPEED = "EXCESSIVE_MOVEMENT_SPEED"  # 지형 한계 이동 속도 초과
    TIME_OVERLAP_SURVEY = "TIME_OVERLAP_SURVEY"            # 동일 조사자 동시간 중복 조사
    ENDANGERED_SPECIES_OMISSION = "ENDANGERED_SPECIES_OMISSION" # 멸종위기종/천연기념물 고의 누락 의심
    SPECIES_OMISSION = "SPECIES_OMISSION"                  # 일반 생물종 누락
    INSUFFICIENT_DURATION = "INSUFFICIENT_DURATION"        # 조사시간 과소 산정


class SurveyPoint(BaseModel):
    point_name: str
    time: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None


class ObservedSpecies(BaseModel):
    species_name: str  # 한국어 국명 (예: 삵, 수달, 소나무)
    scientific_name: Optional[str] = None  # 학명
    count: Optional[str] = None            # 개체수 (예: 2개체, 다수)
    evidence_type: Optional[str] = None    # 관찰형태 (직접관찰, 배설물, 발자국, 청음 등)
    point_name: Optional[str] = None       # 관찰 지점


class SurveySession(BaseModel):
    """조사야장 기록 단위"""
    session_id: str
    date: date
    investigator_name: str
    category: str = "동·식물상"  # 포유류, 조류, 양서파충류, 식물상 등
    start_time: datetime
    end_time: datetime
    route_name: Optional[str] = None
    points: List[SurveyPoint] = Field(default_factory=list)
    observed_species: List[ObservedSpecies] = Field(default_factory=list)
    source_file: Optional[str] = None


class ReceiptRecord(BaseModel):
    """식사 및 경비 영수증 기록"""
    receipt_id: str
    payment_time: datetime
    store_name: str
    store_category: str = "일반음식점"
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    amount: Optional[int] = None
    payer_name: Optional[str] = None
    source_file: Optional[str] = None


class SummaryTableRecord(BaseModel):
    """최종 보고서 총괄표 수록 내용"""
    table_title: str
    category: str
    recorded_species: List[str] = Field(default_factory=list)  # 총괄표에 보고된 종 국명
    source_file: Optional[str] = None


class Anomaly(BaseModel):
    """모순 검출 결과 항목"""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: Severity
    title: str
    description: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str


class AuditReport(BaseModel):
    """전체 감사 보고서"""
    report_id: str
    project_name: str
    generated_at: datetime = Field(default_factory=datetime.now)
    surveys_count: int
    receipts_count: int
    species_in_notes_count: int
    species_in_summary_count: int
    anomalies: List[Anomaly] = Field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(1 for a in self.anomalies if a.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for a in self.anomalies if a.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for a in self.anomalies if a.severity == Severity.INFO)
