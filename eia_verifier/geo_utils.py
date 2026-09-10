"""Geographical and kinematic calculation utilities."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional, Tuple


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 위·경도 좌표 간의 구면 대권거리(km)를 계산."""
    R = 6371.0  # 지구 반지름 (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def calculate_speed_kmh(distance_km: float, time_diff: timedelta) -> float:
    """거리와 시간 차이로 시속(km/h) 계산."""
    total_seconds = time_diff.total_seconds()
    if total_seconds <= 0:
        return float("inf") if distance_km > 0 else 0.0
    hours = total_seconds / 3600.0
    return distance_km / hours


def estimate_driving_minutes(distance_km: float, average_speed_kmh: float = 45.0, tortuosity: float = 1.35) -> float:
    """
    직선거리(km)를 기반으로 산간/지방 도로의 굴곡도(tortuosity) 및 평균 주행속도를 감안한
    최소 차량 이동 소요 시간(분)을 추정.
    """
    actual_road_distance_km = distance_km * tortuosity
    travel_hours = actual_road_distance_km / average_speed_kmh
    return travel_hours * 60.0


# 주요 지역 주소에 대한 간이 좌표 룩업 (오프라인/테스트용)
MOCK_GEOCODE_DB = {
    "용문산": (37.5350, 127.5683),
    "용문면": (37.4988, 127.5936),
    "양평읍": (37.4913, 127.4876),
    "문막읍": (37.3194, 127.8286),
    "치악산": (37.3653, 128.0528),
    "청계산": (37.4091, 127.0505),
    "관악산": (37.4442, 126.9639),
    "양양군": (38.0754, 128.6189),
    "설악산": (38.1194, 128.4656),
}


def geocode_korean_address(address: str) -> Optional[Tuple[float, float]]:
    """주소 텍스트에서 주요 지명을 검색하여 위·경도 근사치 반환."""
    for key, coords in MOCK_GEOCODE_DB.items():
        if key in address:
            return coords
    return None
