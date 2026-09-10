"""Audit report generator in Markdown, HTML, and Terminal formats."""
from __future__ import annotations

from typing import Optional
from .models import AuditReport, Severity


class AuditReporter:
    """감사 보고서 출력 포맷터"""

    @staticmethod
    def to_markdown(report: AuditReport) -> str:
        """Markdown 형식 보고서 생성"""
        md = []
        md.append(f"# [감사 보고서] {report.project_name}")
        md.append(f"- **보고서 ID**: `{report.report_id}`")
        md.append(f"- **감사 일시**: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"- **분석 대상**: 수기 야장 {report.surveys_count}건 | 영수증 {report.receipts_count}건 | 야장 관찰 종 {report.species_in_notes_count}종 | 총괄표 수록 {report.species_in_summary_count}종\n")

        # 요약 통계 박스
        md.append("## 1. 감사 요약 (Audit Summary)")
        md.append(f"- 🔴 **중대 위반(CRITICAL)**: **{report.critical_count}건** (거짓작성/멸종위기종 은폐 혐의)")
        md.append(f"- 🟡 **경고(WARNING)**: **{report.warning_count}건** (동선 속도 초과/부실 조사)")
        md.append(f"- 🔵 **단순 참고(INFO)**: **{report.info_count}건**\n")

        if not report.anomalies:
            md.append("> [!NOTE]\n> 검출된 시공간 충돌이나 생물종 누락 이상치가 없습니다. (정상)\n")
            return "\n".join(md)

        md.append("## 2. 세부 모순 적발 내역\n")

        for idx, a in enumerate(report.anomalies, 1):
            sev_icon = "🔴" if a.severity == Severity.CRITICAL else ("🟡" if a.severity == Severity.WARNING else "🔵")
            md.append(f"### {idx}. {sev_icon} [{a.severity.value}] {a.title}")
            md.append(f"**유형**: `{a.anomaly_type.value}` | **식별자**: `{a.anomaly_id}`\n")
            md.append(f"**상세 소견**:\n{a.description}\n")

            if a.evidence:
                md.append("**검증 증거 데이터**:")
                for k, v in a.evidence.items():
                    md.append(f"- `{k}`: {v}")
                md.append("")

            md.append(f"**조치 권고사항**:\n> 💡 {a.recommendation}\n")
            md.append("---\n")

        return "\n".join(md)

    @staticmethod
    def print_terminal(report: AuditReport) -> None:
        """콘솔 터미널 출력용 포맷"""
        line = "━" * 68
        print(f"\n{line}")
        print(f" 🔍 [환경영향평가서 거짓·부실 검증 리포트]")
        print(f" 프로젝트: {report.project_name}")
        print(f" 일시: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(line)
        print(f" 📊 분석 현황: 야장 {report.surveys_count}건 | 영수증 {report.receipts_count}건")
        print(f"    생물종 대조: 야장 기록 {report.species_in_notes_count}종 vs 총괄표 {report.species_in_summary_count}종")
        print(f" 🚨 적발 결과: 🔴 중대 위반 {report.critical_count}건  |  🟡 경고 {report.warning_count}건  |  🔵 참고 {report.info_count}건")
        print(line)

        for idx, a in enumerate(report.anomalies, 1):
            sev_badge = "[🔴 CRITICAL]" if a.severity == Severity.CRITICAL else ("[🟡 WARNING ]" if a.severity == Severity.WARNING else "[🔵 INFO    ]")
            print(f"\n{idx}. {sev_badge} {a.title}")
            print(f"   내용: {a.description}")
            if a.evidence:
                items = [f"{k}={v}" for k, v in a.evidence.items() if k in ["investigator", "receipt_time", "distance_km", "calculated_speed_kmh", "species_name", "grade"]]
                if items:
                    print(f"   증거: {', '.join(items)}")
            print(f"   권고: {a.recommendation}")

        print(f"\n{line}\n")
