"""Database and lookup for Korean Endangered Wildlife & Natural Monuments."""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple


# 한국 멸종위기 야생생물 및 천연기념물 핵심 데이터베이스
ENDANGERED_SPECIES_DB: Dict[str, Dict[str, str]] = {
    # [포유류]
    "수달": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제330호", "category": "포유류"},
    "산양": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제217호", "category": "포유류"},
    "반달가슴곰": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제329호", "category": "포유류"},
    "사향노루": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제216호", "category": "포유류"},
    "여우": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "포유류"},
    "늑대": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "포유류"},
    "표범": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "포유류"},
    "호랑이": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "포유류"},
    "삵": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "포유류"},
    "담비": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "포유류"},
    "하늘다람쥐": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제328호", "category": "포유류"},
    "물범": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제331호", "category": "포유류"},
    "무산쇠족제비": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "포유류"},

    # [조류]
    "저어새": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제205-1호", "category": "조류"},
    "노랑부리백로": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제361호", "category": "조류"},
    "황새": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제199호", "category": "조류"},
    "두루미": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제202호", "category": "조류"},
    "참수리": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제243-3호", "category": "조류"},
    "흰꼬리수리": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제243-4호", "category": "조류"},
    "매": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제323-7호", "category": "조류"},
    "팔색조": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제204호", "category": "조류"},
    "삼광조": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "조류"},
    "수리부엉이": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제324-2호", "category": "조류"},
    "올빼미": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제324-1호", "category": "조류"},
    "소쩍새": {"grade": "보호종", "monument": "천연기념물 제324-6호", "category": "조류"},
    "원앙": {"grade": "보호종", "monument": "천연기념물 제327호", "category": "조류"},
    "새매": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제323-4호", "category": "조류"},
    "참매": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제323-1호", "category": "조류"},
    "붉은배새매": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제323-2호", "category": "조류"},
    "흑두루미": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제228호", "category": "조류"},
    "재두루미": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제203호", "category": "조류"},
    "큰고니": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제201-2호", "category": "조류"},
    "검은머리물떼새": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제326호", "category": "조류"},
    "독수리": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제243-1호", "category": "조류"},

    # [양서·파충류]
    "수원청개구리": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "양서류"},
    "금개구리": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "양서류"},
    "맹꽁이": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "양서류"},
    "구렁이": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "파충류"},
    "남생이": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제453호", "category": "파충류"},
    "표범장지뱀": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "파충류"},
    "비바리뱀": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "파충류"},

    # [어류]
    "감돌고기": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "어류"},
    "꼬치동자개": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제455호", "category": "어류"},
    "미호종개": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제454호", "category": "어류"},
    "퉁사리": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "어류"},
    "열목어": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "천연기념물 제74호(서식지)", "category": "어류"},
    "모래주사": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "어류"},
    "돌상어": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "어류"},

    # [곤충류]
    "장수하늘소": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제218호", "category": "곤충류"},
    "붉은점모시나비": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "곤충류"},
    "비단벌레": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "천연기념물 제496호", "category": "곤충류"},
    "물장군": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "곤충류"},
    "대모잠자리": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "곤충류"},
    "애기뿔소똥구리": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "곤충류"},

    # [식물상]
    "광릉요강꽃": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "식물"},
    "나도풍란": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "식물"},
    "만년콩": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "식물"},
    "암매": {"grade": "멸종위기 야생생물 Ⅰ급", "monument": "", "category": "식물"},
    "단양쑥부쟁이": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "식물"},
    "가시연": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "식물"},
    "개병풍": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "식물"},
    "백부자": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "식물"},
    "순채": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "식물"},
    "자주땅귀개": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "식물"},
    "제비동자꽃": {"grade": "멸종위기 야생생물 Ⅱ급", "monument": "", "category": "식물"},
}


def normalize_species_name(name: str) -> str:
    """괄호, 공백, 특수문자, 조사 제거 (예: '삵(배설물)' -> '삵')"""
    # 괄호와 그 안의 내용 제거
    cleaned = re.sub(r"\(.*?\)", "", name)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    # 꼬리말 제거 (배설물, 깃털, 사체, 흔적, 울음소리, 서식확인 등)
    suffixes = ["배설물", "발자국", "깃털", "사체", "흔적", "서식", "울음", "청음", "둥지"]
    for s in suffixes:
        cleaned = cleaned.replace(s, "")
    return cleaned.strip()


def lookup_endangered_species(raw_name: str) -> Optional[Tuple[str, Dict[str, str]]]:
    """생물명이 멸종위기종 또는 천연기념물인지 매칭하여 정보 반환."""
    cleaned = normalize_species_name(raw_name)
    if not cleaned:
        return None

    # 1. 완전 일치
    if cleaned in ENDANGERED_SPECIES_DB:
        return cleaned, ENDANGERED_SPECIES_DB[cleaned]

    # 2. 부분 일치 검색
    for name, info in ENDANGERED_SPECIES_DB.items():
        if name in cleaned or cleaned in name:
            return name, info

    return None
