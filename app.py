"""Streamlit Web Application: EIA Universal Dynamic Audit Portal (순수 동적 환경영향평가 전수 검증 포털).
모든 더미/목업 데이터와 특정 프로젝트 하드코딩을 완전히 제거하고,
사용자가 등록하거나 선택한 파일만을 100% 실시간 동적 분석합니다.
"""
from __future__ import annotations

import os
import sys
import glob
from pathlib import Path
from datetime import datetime
import tempfile
import re
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
pkg_dir = BASE_DIR / "eia_verifier"
if pkg_dir.exists() and str(pkg_dir) not in sys.path:
    sys.path.insert(0, str(pkg_dir))

from PIL import Image
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

try:
    from eia_verifier.dynamic_analyzer import UniversalEIAAnalyzer
    from eia_verifier.hwp_parser import HWPParser
except (ImportError, ModuleNotFoundError):
    try:
        from dynamic_analyzer import UniversalEIAAnalyzer
        from hwp_parser import HWPParser
    except Exception as e:
        import traceback
        st.error(f"모듈 로드 실패: {e}\n\n{traceback.format_exc()}")
        st.stop()

st.set_page_config(
    page_title="다산컨설턴트 종합환경부 보고서 검증 포털",
    page_icon="🏛️",
    layout="wide",
)

# ----------------------------------------------------
# 1. 고속 분석 엔진 캐시 함수
# ----------------------------------------------------
@st.cache_data(show_spinner=False)
def analyze_uploaded_hwp(target_hwp_path: str, part_doc_path: Optional[str] = None) -> dict:
    """선택되거나 업로드된 HWP 부록 문서를 범용 동적 분석 엔진으로 100% 실시간 분석."""
    return UniversalEIAAnalyzer.analyze(target_hwp_path, part_doc_path=part_doc_path)


# ----------------------------------------------------
# 2. 세션 상태 관리
# ----------------------------------------------------
if "current_target_hwp" not in st.session_state:
    st.session_state["current_target_hwp"] = ""
if "current_part_path" not in st.session_state:
    st.session_state["current_part_path"] = ""
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

target_hwp_path = st.session_state.get("current_target_hwp", "")
part_doc_path = st.session_state.get("current_part_path", "")

def trigger_reset():
    """모든 업로드 상태 및 캐시를 완전히 초기화하여 이전 파일 데이터 유입을 차단."""
    st.session_state["current_target_hwp"] = ""
    st.session_state["current_part_path"] = ""
    st.session_state["uploader_key"] = st.session_state.get("uploader_key", 0) + 1
    st.cache_data.clear()
    st.rerun()

# ----------------------------------------------------
# 3. 사이드바: 도구 제어 및 필터
# ----------------------------------------------------
with st.sidebar:
    st.markdown("### 🛠️ 부록 검증 도구")
    if target_hwp_path and os.path.exists(target_hwp_path):
        st.success(f"📄 **분석 대상 문서**:\n`{Path(target_hwp_path).name}`")
        if part_doc_path and os.path.exists(part_doc_path):
            st.caption(f"📑 본안 파트: `{Path(part_doc_path).name}`")
        if st.button("🔄 다른 부록 검증하기 (초기화)", key="sidebar_reset_btn", use_container_width=True):
            trigger_reset()
    else:
        st.info("👈 우측 화면에서 검증할 HWP/HWPX 부록 문서를 업로드해 주십시오.")

    st.divider()
    st.subheader("🔍 검증 필터")
    filter_cat = st.multiselect(
        "분야 필터",
        ["자연생태계", "환경질", "기타항목 (토양/해양)"],
        default=["자연생태계", "환경질"],
    )
    filter_sev = st.multiselect(
        "검토 등급 필터",
        ["중점 검토 (확인요망)", "일반 검토 (참고/보완)"],
        default=["중점 검토 (확인요망)", "일반 검토 (참고/보완)"],
    )


# ----------------------------------------------------
# 4. 메인 화면: 선택된 파일 100% 전용 동적 대시보드
# ----------------------------------------------------
st.markdown(
    """
    <div style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: white; padding: 22px 28px; border-radius: 14px; margin-bottom: 24px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
        <h1 style="font-size: 25px; font-weight: 800; margin: 0 0 6px 0; color: #ffffff;">🛠️ 환경영향평가 부록 원본 검증 도구</h1>
        <p style="font-size: 13.5px; margin: 0; color: #94a3b8;">
            사후환경영향조사서 부록(HWP/HWPX)의 원문 텍스트, 측정기록부, 영수증 증빙을 실시간 파싱하여 4대 시공간 정합성 및 거짓·부실 모순을 전수 자동 검증하는 독립형 툴입니다.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# 대상 파일 유무 검증 및 랜딩 페이지 표출
if not target_hwp_path or not os.path.exists(target_hwp_path):
    st.info("💡 **검증을 진행할 사후환경영향조사서 부록(HWP/HWPX)을 등록해 주십시오.**")

    tab_upload, tab_manual = st.tabs(["📁 브라우저 파일 업로드 (드래그 앤 드롭)", "✍️ 파일 전체 경로 직접 입력"])

    with tab_upload:
        up_main = st.file_uploader(
            "검증할 환경영향평가 부록 HWP/HWPX 파일을 여기에 끌어다 놓으세요 (최대 2GB)",
            type=["hwp", "hwpx"],
            key=f"main_landing_uploader_{st.session_state['uploader_key']}"
        )
        up_part = st.file_uploader(
            "(선택) 본안 파트보고서 첨부 (HWP, HWPX, PDF, XLSX)",
            type=["hwp", "hwpx", "pdf", "xlsx"],
            key=f"main_part_uploader_{st.session_state['uploader_key']}"
        )
        if up_main is not None:
            import time
            unique_prefix = str(int(time.time() * 1000))
            td = Path(tempfile.gettempdir()) / "eia_upload" / unique_prefix
            td.mkdir(parents=True, exist_ok=True)
            tf = td / up_main.name
            tf.write_bytes(up_main.getvalue())
            st.session_state["current_target_hwp"] = str(tf)

            if up_part is not None:
                tf_part = td / up_part.name
                tf_part.write_bytes(up_part.getvalue())
                st.session_state["current_part_path"] = str(tf_part)

            st.cache_data.clear()
            st.success(f"파일 수신 완료: {up_main.name}")
            st.rerun()

    with tab_manual:
        with st.form("manual_path_form"):
            manual_hwp = st.text_input(
                "부록 HWP/HWPX 파일 전체 경로 입력",
                value="",
                placeholder=r"C:\경로\부록보고서.hwp",
                key="manual_path_input"
            )
            manual_part = st.text_input(
                "(선택) 본안 보고서 전체 경로 입력",
                value="",
                placeholder=r"C:\경로\본안보고서.hwp",
                key="manual_part_input"
            )
            manual_submit = st.form_submit_button("검증 시작 ➔", use_container_width=True)

            if manual_submit:
                m_path = manual_hwp.strip().strip('"').strip("'")
                if m_path and os.path.exists(m_path):
                    st.session_state["current_target_hwp"] = m_path
                    m_part = manual_part.strip().strip('"').strip("'")
                    if m_part and os.path.exists(m_part):
                        st.session_state["current_part_path"] = m_part
                    st.cache_data.clear()
                    st.success("경로 확인 완료! 분석을 시작합니다.")
                    st.rerun()
                else:
                    st.error("입력하신 파일 경로가 올바르지 않거나 파일을 찾을 수 없습니다. 경로를 확인해 주십시오.")

    st.markdown("<br>", unsafe_allow_html=True)
    c_g1, c_g2 = st.columns(2)
    with c_g1:
        st.markdown(
            """
            ### 🔍 4대 핵심 정합성 검증 항목
            * **🌿 생태계 조사야장 vs 본문 대조**: 수기 야장에 자필 기재된 보호종(삵, 새매 등) 및 소산식물 종수 불일치 자동 진단
            * **⏱️ 출장 동선 및 이동시간 결손**: 수도권 본사/고속도로 IC ➔ 현장 도착 후 연속측정 장비 거치시간(20~30분) 부족 확인
            * **🔊 다지점 순회 측정 물리적 한계**: 소음·진동 6~10개 지점 순회 간격 및 삼각대 철수/재설치 시간 검토
            * **📋 분담/재대행업체 자격 증빙**: 부록 표지 명단과 실제 첨부된 환경영향평가업 등록증 유효성 교차 대조
            """
        )
    with c_g2:
        st.markdown(
            """
            ### 💡 이용 안내
            * 본 시스템은 외부 더미 데이터나 바탕화면 임의 폴더에 연결되지 않으며, **사용자께서 직접 등록하신 파일만을 100% 단독 분석**합니다.
            * HWP 5.0 OLE 포맷의 원문 텍스트, 표 구조, 내장 BinData 이미지(영수증, 성적서, 현장사진)를 고속으로 자체 파싱합니다.
            * 분석 결과는 화면에서 실시간 인터랙티브 지도(Esri) 및 시계열 타임라인으로 시각화됩니다.
            """
        )
    st.stop()


# ----------------------------------------------------
# 5. 선택된 파일 실시간 동적 분석 실행
# ----------------------------------------------------
with st.spinner("부록 HWP 문서 및 내장 원본 증빙자료 고속 분석 중..."):
    hwp_info = analyze_uploaded_hwp(target_hwp_path, part_doc_path=part_doc_path if part_doc_path else None)

if not hwp_info:
    st.error("HWP 문서 분석에 실패하였습니다. 파일 형식을 확인해 주십시오.")
    st.stop()

# 성공 배너 및 상단 즉시 초기화 버튼 (선택된 파일에서 추출된 정보만 표출)
c_top_info, c_top_reset = st.columns([4, 1.2])
with c_top_info:
    st.success(f"✅ 프로젝트 **[{hwp_info['title']}]** 부록 기반 조사경로·시간 분석 및 원시데이터 정밀 검증 완료!")
with c_top_reset:
    if st.button("🔄 다른 부록 검증하기 (초기화)", key="main_top_reset_btn", use_container_width=True):
        trigger_reset()

# 1. 4대 요약 KPI (물리적 이동시간 및 동선 정합성 지표)
bk1, bk2, bk3, bk4 = st.columns(4)
with bk1:
    bk1.metric("🔴 이동·시간 결손", f"{hwp_info['critical_count']} 건", help="고속도로 진출 후 측정 개시 시간 부족, 다지점 순회 간격 결손, 조사 종료 직후 원거리 결제")
with bk2:
    bk2.metric("🟡 증빙·목록 검토", f"{hwp_info['warning_count']} 건", help="소산식물 종수 불일치, 분담업체 등록증 및 기술자 명단 미비 확인")
with bk3:
    bk3.metric("🚗 1일 출장 이동거리", f"{hwp_info['est_distance_km']} km", help=f"조사기관 본사 ➔ 현장({hwp_info.get('location_name', '현장').split()[0] if hwp_info.get('location_name') else '현장'}) 출장 거리")
with bk4:
    bk4.metric("🧾 대조 영수증·증빙", f"{hwp_info['img_count']} 건 전수", help="부록 내 첨부된 출장 영수증, 하이패스 통행료, 공인성적서, 수기야장 전수")

st.divider()

# 메인 4대 탭 구성
tab_anomalies, tab_timeline, tab_map, tab_gallery = st.tabs([
    "💳 1. 시공간 조사경로 및 모순 분석",
    "⏱️ 2. 일과 시계열 타임라인 대조표",
    "🗺️ 3. 현장 조사동선 인터랙티브 지도",
    "🖼️ 4. 부록 내장 원본 증빙자료 갤러리"
])

# ----------------------------------------------------
# TAB 1: 모순 분석 카드 전수 동적 렌더링
# ----------------------------------------------------
with tab_anomalies:
    st.markdown(f"### 💳 대상 사업: `{hwp_info['title']}` ({hwp_info['location_name']})")
    st.info(
        "💡 부록 내 **측정기록부(조사 개시·종료 시각)**와 **출장 증빙 영수증(결제 시각·가맹점 위치)**, "
        "**환경영향조사 업체 현황** 간의 상호 교차 대조를 통해 **소산식물 종수 불일치, 물리적 이동시간 부족, 장비 거치시간 결손**을 전수 자동 연산한 결과입니다.",
        icon="💡",
    )

    # 필터 적용
    visible_anomalies = []
    for a in hwp_info['anomalies']:
        sev_label = "중점 검토 (확인요망)" if a.get("severity") == "CRITICAL" else "일반 검토 (참고/보완)"
        if sev_label in filter_sev:
            visible_anomalies.append(a)

    if not visible_anomalies:
        st.success("선택하신 필터 조건에 해당하는 검토 항목이 없습니다. (모든 항목 적합)")
    else:
        for idx, anomaly in enumerate(visible_anomalies):
            card_key = f"status_{anomaly.get('category', idx)}_{idx}"
            if card_key not in st.session_state:
                st.session_state[card_key] = "NO (확인 필요 / 미결)"

            with st.container(border=True):
                c_top1, c_top2 = st.columns([4, 1.2])
                with c_top1:
                    st.markdown(f"#### {anomaly['title']}")
                with c_top2:
                    current_val = st.session_state[card_key]
                    is_ok = (current_val == "OK (이상 없음 / 소명 완료)")
                    new_val = st.radio(
                        "소명 상태",
                        ["NO (확인 필요 / 미결)", "OK (이상 없음 / 소명 완료)"],
                        index=1 if is_ok else 0,
                        key=f"radio_{card_key}",
                        label_visibility="collapsed",
                        horizontal=True
                    )
                    st.session_state[card_key] = new_val

                st.write(anomaly['description'])
                if "json_evidence" in anomaly:
                    st.json(anomaly['json_evidence'])


# ----------------------------------------------------
# TAB 2: 시계열 타임라인 대조표
# ----------------------------------------------------
with tab_timeline:
    st.markdown("### ⏱️ 부록 기록 기반 일과 시계열 타임라인 대조표")
    if hwp_info.get('timeline'):
        df_tl = pd.DataFrame(hwp_info['timeline'])
        st.dataframe(df_tl, use_container_width=True, hide_index=True)
    else:
        st.write("시계열 데이터가 검출되지 않았습니다.")


# ----------------------------------------------------
# TAB 3: 현장 조사동선 인터랙티브 지도
# ----------------------------------------------------
with tab_map:
    st.markdown(f"### 🗺️ {hwp_info['title']} 조사 동선 및 결제 위치 인터랙티브 지도")
    st.caption(f"🌐 **{hwp_info['location_name']}** 중심의 고해상도 Esri 엔지니어링 도로망/지형 및 조사경로 결손 시각화 (감지된 측정지점 {len(hwp_info['points'])}개 전수)")

    map_meta = hwp_info['map_data']
    m_dynamic = folium.Map(
        location=map_meta['center'],
        zoom_start=map_meta.get('zoom', 12),
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri WorldStreetMap",
        name="Esri 엔지니어링 도로망/지형 (기본)",
    )
    folium.TileLayer("CartoDB positron", name="CartoDB Positron (심플)").add_to(m_dynamic)
    folium.TileLayer("CartoDB voyager", name="CartoDB Voyager (선명한 컬러)").add_to(m_dynamic)
    folium.LayerControl(collapsed=False).add_to(m_dynamic)

    for marker in map_meta['markers']:
        folium.Marker(
            location=marker["coords"],
            popup=f"<b>{marker['name']}</b><br>내용: {marker.get('time', '')}",
            tooltip=f"{marker['name']} ({marker.get('time', '')})",
            icon=folium.Icon(color=marker.get("color", "blue"), icon=marker.get("icon", "info-sign")),
        ).add_to(m_dynamic)

    # 결손 경로 (빨간 점선)
    if map_meta.get('anomaly_polyline'):
        folium.PolyLine(
            map_meta['anomaly_polyline'],
            color="red", weight=4, dash_array="10",
            tooltip="🔴 고속도로 진출 ➔ 현장 도착: 장비 거치 및 설치 준비시간 확인 필요",
        ).add_to(m_dynamic)

    # 조사 노선 (남색 실선)
    if map_meta.get('survey_route') and len(map_meta['survey_route']) > 1:
        folium.PolyLine(
            map_meta['survey_route'],
            color="darkblue", weight=5, opacity=0.8,
            tooltip=f"{hwp_info['title']} 조사 선형 노선",
        ).add_to(m_dynamic)

    st_folium(m_dynamic, width="100%", height=540, returned_objects=[], key="folium_universal_map_clean")
    st.caption("📍 파랑: 대기질 | 🟢 초록: 소음·진동 | 🟦 청록/하늘: 수질/지하수 | 🔴 빨강 점선: 고속도로 진출 후 접근 경로 | 🔵 남색 실선: 조사 노선")


# ----------------------------------------------------
# TAB 4: 부록 내장 원본 증빙자료 전수 추출 갤러리
# ----------------------------------------------------
with tab_gallery:
    total_imgs = hwp_info['img_count']
    st.markdown(f"### 🖼️ 부록 내장 원본 증빙자료 전수 추출 갤러리 (총 {total_imgs}건)")
    st.info(
        f"💡 부록 HWP 내에 첨부된 **출장 증빙 영수증, 하이패스 통행료 영수증, 공인시험성적서, 수기 현지조사표, 현장사진** 총 **{total_imgs}건**을 전수 추출하였습니다.",
        icon="💡",
    )

    if total_imgs > 0:
        page_size = 6
        total_pages = (total_imgs + page_size - 1) // page_size
        c_pg1, c_pg2 = st.columns([1, 3])
        with c_pg1:
            page = st.number_input("📄 증빙 갤러리 페이지 선택", min_value=1, max_value=max(1, total_pages), value=1, step=1, key="clean_gallery_page")
        with c_pg2:
            st.caption(f"총 {total_imgs}건의 증빙 이미지 중 {(page - 1) * page_size + 1} ~ {min(page * page_size, total_imgs)}번째 자료 표시 중 (전체 {total_pages} 페이지)")

        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_imgs)
        raw_imgs = hwp_info.get('img_list', hwp_info.get('images', []))
        page_items = raw_imgs[start_idx:end_idx]

        # 3열 카드 배치
        cols = st.columns(3)
        for i, item in enumerate(page_items):
            with cols[i % 3]:
                st.markdown(f"**📌 증빙 #{start_idx + i + 1}: {item['name']}** ({item['size_kb']} KB)")
                # 온디맨드 이미지 로딩 및 썸네일 표시
                try:
                    img_data = HWPParser.get_cached_or_raw_image(item['path'])
                    if img_data:
                        st.image(img_data, use_container_width=True)
                    else:
                        st.caption("미리보기 준비 중 (HWP 압축 포맷)")
                except Exception:
                    st.caption("이미지 로드 대기")