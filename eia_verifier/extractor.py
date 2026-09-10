"""Vision AI extractor for handwritten survey notes, receipts, and summary tables."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional, Union, Tuple, List
import requests

from .models import (
    ObservedSpecies,
    ReceiptRecord,
    SummaryTableRecord,
    SurveyPoint,
    SurveySession,
)
from .mock_data import get_sample_eia_case


class DocumentExtractor:
    """멀티모달 비전 AI(Gemini Vision)를 이용한 수기 야장·영수증·총괄표 추출기"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

    def _encode_image(self, image_path: Union[str, Path]) -> Tuple[str, str]:
        path = Path(image_path)
        suffix = path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime = mime_types.get(suffix, "image/jpeg")
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return encoded, mime

    def _call_gemini_vision(self, prompt: str, image_path: Union[str, Path]) -> Optional[dict]:
        """Gemini API 호출 및 JSON 응답 반환."""
        if not self.api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        img_b64, mime = self._encode_image(image_path)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": img_b64}},
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except Exception as e:
            print(f"[Extractor Warning] Gemini API 호출 실패 ({e}). Mock 모드로 대체합니다.")
            return None

    def extract_survey_notes(self, image_path: Union[str, Path]) -> SurveySession:
        """수기 조사야장 이미지에서 시간, 지점, 관찰 생물종 추출."""
        prompt = """
        당신은 환경영향평가서 수기 조사야장 전문 분석가입니다.
        제공된 수기 조사야장 이미지에서 다음 정보를 추출하여 정확한 JSON 형태로 응답하세요.

        출력 JSON 스키마:
        {
            "session_id": "야장 고유번호 또는 날짜기반 ID",
            "date": "YYYY-MM-DD",
            "investigator_name": "조사자 이름",
            "category": "조사분야 (예: 포유류, 조류, 식물상 등)",
            "start_time": "YYYY-MM-DDTHH:MM:SS",
            "end_time": "YYYY-MM-DDTHH:MM:SS",
            "route_name": "조사 노선 또는 지점명",
            "points": [
                {
                    "point_name": "지점명",
                    "time": "YYYY-MM-DDTHH:MM:SS (시간이 적혀있다면)",
                    "latitude": 37.xxx (좌표가 적혀있다면),
                    "longitude": 127.xxx,
                    "notes": "특이사항"
                }
            ],
            "observed_species": [
                {
                    "species_name": "생물종 한국어 국명 (예: 삵, 소나무)",
                    "count": "개체수 또는 흔적 (예: 1개체, 배설물)",
                    "evidence_type": "관찰형태 (직접관찰, 배설물, 발자국, 청음 등)"
                }
            ]
        }
        """
        result = self._call_gemini_vision(prompt, image_path)
        if result:
            return SurveySession.model_validate(result)

        # Mock fallback
        _, sample_surveys, _, _ = get_sample_eia_case()
        sample = sample_surveys[0]
        sample.source_file = str(image_path)
        return sample

    def extract_receipt(self, image_path: Union[str, Path]) -> ReceiptRecord:
        """영수증 이미지에서 결제시간, 상호, 주소, 금액 추출."""
        prompt = """
        영수증 이미지에서 결제 시간, 상호명, 가맹점 주소, 결제 금액, 결제자(카드소유자)를 추출하세요.

        출력 JSON 스키마:
        {
            "receipt_id": "승인번호 또는 식별자",
            "payment_time": "YYYY-MM-DDTHH:MM:SS",
            "store_name": "가맹점 상호명",
            "store_category": "업종 (예: 일반음식점, 카페, 주유소)",
            "address": "도로명 또는 지번 주소",
            "amount": 50000 (숫자 원 단위),
            "payer_name": "결제자 이름 (있을 경우)"
        }
        """
        result = self._call_gemini_vision(prompt, image_path)
        if result:
            return ReceiptRecord.model_validate(result)

        # Mock fallback
        _, _, sample_receipts, _ = get_sample_eia_case()
        sample = sample_receipts[0]
        sample.source_file = str(image_path)
        return sample

    def extract_summary_table(self, image_path: Union[str, Path]) -> SummaryTableRecord:
        """최종 보고서 총괄표 이미지에서 수록된 모든 생물종 국명 추출."""
        prompt = """
        환경영향평가서 본안 보고서의 생물종 총괄표 이미지입니다.
        표에 나열된 모든 출현 생물종의 한국어 명칭(국명) 목록을 추출하세요.

        출력 JSON 스키마:
        {
            "table_title": "표 제목 (예: 표 4-2-1 ...)",
            "category": "분야",
            "recorded_species": ["신갈나무", "소나무", "노루", "고라니", ...]
        }
        """
        result = self._call_gemini_vision(prompt, image_path)
        if result:
            return SummaryTableRecord.model_validate(result)

        # Mock fallback
        _, _, _, sample_tables = get_sample_eia_case()
        sample = sample_tables[0]
        sample.source_file = str(image_path)
        return sample
