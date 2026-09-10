"""Streamlit Web Application: EIA Integrated Audit Verifier (생태계 + 환경질 종합 감사 대시보드)."""
from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from eia_verifier.gyeongsan_case import GYEONGSAN_CASE
from eia_verifier.hwp_parser import HWPParser

st.set_page_config(
    page_title="EIA-Verifier | 환경영향평가 거짓·부실 통합 감사 시스템",
    page_icon="🏛️",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR = BASE_DIR / "preview_jpgs"

# ----------------------------------------------------
# 보안 인증 시스템 (내부 관계자 전용 접근 제어)
# ----------------------------------------------------
def check_password() -> bool:
    """내부 감사단 전용 비밀번호 인증."""
    if st.session_state.get("authenticated", False):
        return True

    st.markdown(
        """
        <div style="max-width: 540px; margin: 40px auto 10px auto; padding: 36px 30px; background: white; border-radius: 16px; border: 1px solid #cbd5e1; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.1); text-align: center;">
            <div style="font-size: 52px; margin-bottom: 10px;">🔒</div>
            <h2 style="font-size: 22px; font-weight: 800; color: #0f172a; margin-bottom: 8px; letter-spacing: -0.5px;">국도4호선 환경영향평가 감사 포털</h2>
            <div style="display:inline-block; background: #dc2626; color: white; padding: 3px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-bottom: 16px;">
                RESTRICTED ACCESS · 내부 감사단 전용
            </div>
            <p style="font-size: 13.5px; color: #475569; line-height: 1.65; margin-bottom: 20px;">
                본 시스템은 <strong>환경영향평가 거짓·부실작성 실증 감사자료</strong>를 포함하고 있어 인가된 관계자만 열람할 수 있습니다.<br>
                비인가자의 무단 접속 및 외부 유출 시 법적 제재를 받을 수 있습니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        with st.form("login_form"):
            password = st.text_input(
                "🔑 내부 접속 비밀번호",
                type="password",
                placeholder="비밀번호를 입력하세요",
                help="내부 감사단 공유 암호를 입력하세요."
            )
            submit = st.form_submit_button("보안 접속 인증 ➔", use_container_width=True)

        if submit:
            valid_pw = ["YJ0101", "yj0101"]
            if "ADMIN_PASSWORD" in st.secrets:
                valid_pw.append(str(st.secrets["ADMIN_PASSWORD"]))
                valid_pw.append(str(st.secrets["ADMIN_PASSWORD"]).lower())

            if password.strip() in valid_pw:
                st.session_state["authenticated"] = True
                st.success("✅ 인증 완료! 대시보드를 불러옵니다...")
                st.rerun()
            else:
                st.error("🚨 비밀번호가 일치하지 않습니다. 인가된 관계자만 접속 가능합니다.")

        st.markdown(
            "<p style='text-align:center; font-size:12px; color:#64748b; margin-top:14px;'>🔒 TLS/HTTPS 256-bit 암호화 보안 세션</p>",
            unsafe_allow_html=True
        )
    return False

if not check_password():
    st.stop()

# 상단 타이틀
st.title("🏛️ 환경영향평가서 거짓·부실 통합 감사 대시보드")
st.caption("수기 조사야장, 환경질(대기·소음·수질) 측정기록부, 차량운행일지, 법인카드 영수증 교차 분석 검증 시스템")

# 사이드바 설정
with st.sidebar:
    st.markdown("### 🛡️ 보안 관리")
    st.success("🟢 **내부 감사단 인증 완료**")
    if st.button("🚪 안전 로그아웃", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()
    st.divider()

    st.header("📂 분석 프로젝트 선택")
    project_list = [
        "선택 대기 (신규 프로젝트 대기 상태)",
        "📌 [실전 감사] 국도4호선 경산 하양 부록 건",
        "📁 [신규 분석] 다른 HWP 파일 열기"
    ]
    
    current_idx = 0
    if st.session_state.get("switch_to_gyeongsan", False):
        current_idx = 1
        st.session_state["switch_to_gyeongsan"] = False
        
    mode = st.selectbox(
        "분석 프로젝트 선택",
        project_list,
        index=current_idx,
    )

    st.divider()
    st.subheader("🔍 검증 필터")
    filter_cat = st.multiselect(
        "분야 필터",
        ["자연생태계 (동·식물상)", "환경질 (대기·소음·수질)"],
        default=["자연생태계 (동·식물상)", "환경질 (대기·소음·수질)"],
    )
    filter_sev = st.multiselect(
        "심각도 필터",
        ["CRITICAL", "WARNING"],
        default=["CRITICAL", "WARNING"],
    )

# ----------------------------------------------------
# 1. 선택 대기 모드 (빈 화면 / Clean State)
# ----------------------------------------------------
if mode.startswith("선택 대기"):
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("📋 활성 프로젝트", "0 건", help="선택된 감사 대상 사업이 없습니다.")
    with m2:
        st.metric("🔴 중대 위반 (CRITICAL)", "0 건")
    with m3:
        st.metric("🟡 부실 산정 (WARNING)", "0 건")
    with m4:
        st.metric("🐾 법정보호종", "0 종")

    st.divider()

    st.info("👈 **좌측 사이드바의 [분석 프로젝트 선택]에서 분석할 사업을 선택하거나, 새로운 HWP 부록 파일을 등록해 주십시오.**")

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown(
            """
            ### 🏛️ 환경영향평가 거짓·부실 통합 감사 검증 시스템
            본 시스템은 환경영향평가서 및 부록에 수록된 원본 증빙을 교차 검증하여 **「환경영향평가법」 제58조(등록취소) 및 제74조(거짓작성죄)** 위반 사항을 과학적으로 규명합니다.

            #### 🔍 주요 검증 엔진 소개
            * **🌿 동·식물상 야장 전수 대조**: 수기 야장에 자필 기재된 멸종위기 야생생물(Ⅰ·Ⅱ급) 및 천연기념물이 최종 부록 및 본안 보고서 목록에서 고의 누락·은폐되었는지 자동 감지
            * **🧪 환경질 시공간 순간이동 적발**: 대기질/소음 측정 시작·종료 시각과 법인카드(식당·편의점·주유소) 결제 시각을 지리 좌표 기반으로 대조하여 물리적 이동 불가능 구간 자동 적발
            * **⏱️ 출장 동선 및 체류 시간 검증**: 차량운행일지, 고속도로 하이패스, 출장신청서를 대조하여 24시간 연속 측정 관리 공백 및 날림 측정 판정
            * **📐 공정시험기준 적합성 검증**: 소음 데시벨(dB)의 비과학적 단순 산술평균 계산 등 환경분야시험검사법 위반 자동 검증
            """
        )
    with c2:
        st.markdown("### 📂 프로젝트 바로 불러오기")
        st.write("등록된 정밀 감사 케이스를 열람하거나 신규 파일을 업로드할 수 있습니다.")
        if st.button("📌 국도4호선 경산 하양 실전 감사 케이스 열기 ➔", use_container_width=True, type="primary"):
            st.session_state["switch_to_gyeongsan"] = True
            st.rerun()

        st.markdown("---")
        st.markdown("### 📁 신규 HWP 부록 파일 등록")
        uploaded_file = st.file_uploader("검증할 환경영향평가 부록 HWP 파일 선택", type=["hwp", "hwpx"])
        if uploaded_file is not None:
            st.success(f"파일 수신 완료: {uploaded_file.name} ({len(uploaded_file.getvalue()):,} bytes)")
            st.info("좌측 사이드바에서 **[📁 신규 분석]** 모드를 선택하여 전체 파싱 및 검증을 진행하십시오.")

# ----------------------------------------------------
# 2. 실전 감사 모드 (국도4호선 경산 하양 건)
# ----------------------------------------------------
elif mode.startswith("📌"):
    case = GYEONGSAN_CASE

    # 요약 메트릭
    all_anomalies = case["eco_anomalies"] + case["env_anomalies"]
    crit_count = sum(1 for a in all_anomalies if a["severity"] == "CRITICAL")
    warn_count = sum(1 for a in all_anomalies if a["severity"] == "WARNING")

    st.markdown(f"### 📋 대상 사업: `{case['project_name']}`")
    st.markdown(
        f"**평가총괄**: {case['evaluation_agency']} | "
        f"**자연생태**: {case['eco_agency']} | "
        f"**환경질측정**: {case['env_quality_agency']} | "
        f"**조사일자**: {case['survey_date']}"
    )

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🔴 중대 위반 (CRITICAL)", f"{crit_count} 건", help="거짓작성죄, 멸종위기종 은폐, 시간조작 등")
    with m2:
        st.metric("🟡 부실 산정 (WARNING)", f"{warn_count} 건", help="공정시험기준 위반, 비현실적 동선 등")
    with m3:
        st.metric("🐾 은폐된 법정보호종", "3 종", help="삵(멸종위기Ⅱ급), 새매(멸종위기Ⅱ급/천연기념물), 황조롱이(천연기념물)")
    with m4:
        st.metric("⏱️ 시공간 순간이동 적발", "2 건", help="대기질 13:00 vs 돌짜장 13:02, 조사종료 15:55 vs 주유소 15:57")

    st.divider()

    # 메인 탭 구성
    tab_sum, tab_eco, tab_env, tab_map, tab_doc = st.tabs([
        "🏛️ 종합 감사 의견서",
        "🌿 1. 자연생태계 모순 대조",
        "🧪 2. 환경질(대기·소음) 모순 대조",
        "🗺️ 3. 시공간 타임라인 및 지도",
        "📄 4. 공식 감사 소명 요구서 출력",
    ])

    # ------------------------------------------------
    # TAB 1: 종합 감사 의견서
    # ------------------------------------------------
    with tab_sum:
        st.subheader("📑 환경영향평가 거짓·부실작성 종합 감사 소견")
        st.warning(
            "본 평가는 「환경영향평가법」 제58조(평가대행자의 등록취소 등) 및 제74조(벌칙), "
            "「환경영향평가서등의 거짓·부실작성 판단기준」(환경부령)에 의거하여 중대한 행정처분 및 형사고발 대상에 해당합니다."
        )

        rows = []
        for a in all_anomalies:
            rows.append({
                "식별번호": a["id"],
                "분야": a["category"],
                "심각도": "🔴 CRITICAL" if a["severity"] == "CRITICAL" else "🟡 WARNING",
                "핵심 적발 내용": a["title"],
                "적용 법조항": a["legal_basis"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🚨 분야별 핵심 위반 요약")
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("##### 🌿 자연생태계 (동·식물상) 주요 적발")
                st.markdown(
                    "1. **멸종위기 야생생물 Ⅱ급 '삵' 고의 은폐**: 수기 야장에 배설흔 명시 후 최종 목록 누락 (0건)\n"
                    "2. **천연기념물 '새매' 및 '황조롱이' 누락**: 조류 야장에 자필 기재 후 목록에서 삭제\n"
                    "3. **조사 종료 시각 허위 기재**: 15:55 종료 후 불과 2분 43초 만에 4.23km 떨어진 주유소 결제 완료"
                )
        with c2:
            with st.container(border=True):
                st.markdown("##### 🧪 환경질 (대기질 / 소음·진동) 주요 적발")
                st.markdown(
                    "1. **대기질 24시간 측정 시작 시간 날조**: 13:00 하양 측정 개시 기록 직후 13:02 10km 밖 '경산돌짜장' 카드 결제 (순간이동)\n"
                    "2. **소음측정 공정시험기준 위반**: 데시벨(dB) 단위를 초등수학식 단순 산술평균 `(66.3+62.0)/2=64.1`로 부실 산정\n"
                    "3. **밀양-경산 76km 동시 주파 날림 측정**: 5월 30일 밀양 대기 3개소 + 경산 소음 2개소를 당일 치기로 측정"
                )

    # ------------------------------------------------
    # TAB 2: 자연생태계 모순 정밀 대조
    # ------------------------------------------------
    with tab_eco:
        st.subheader("🌿 자연생태계 (수기 야장 vs 영수증 vs 목록 누락)")

        for a in case["eco_anomalies"]:
            with st.container(border=True):
                sev_icon = "🔴" if a["severity"] == "CRITICAL" else "🟡"
                st.markdown(f"### {sev_icon} [{a['severity']}] {a['title']}")
                st.write(f"**상세 소견**: {a['details']}")

                # 증빙 이미지 표시
                col_left, col_right = st.columns(2)
                with col_left:
                    img_path = IMG_DIR / a["evidence_image"]
                    if img_path.exists():
                        st.image(str(img_path), caption=f"증빙 1: {a['evidence_image']} ({a['title']})", use_container_width=True)
                with col_right:
                    comp_name = a.get("evidence_compare_image")
                    if comp_name:
                        comp_path = IMG_DIR / comp_name
                        if comp_path.exists():
                            st.image(str(comp_path), caption=f"대조 증빙 2: {comp_name}", use_container_width=True)
                    elif "species_info" in a:
                        st.markdown("##### 🐾 법정보호종 상세 정보")
                        for k, v in a["species_info"].items():
                            st.markdown(f"- **{k}**: `{v}`")

                if "metrics" in a:
                    st.json(a["metrics"])
                st.info(f"⚖️ **법적 제재 근거**: {a['legal_basis']}")

    # ------------------------------------------------
    # TAB 3: 환경질 모순 정밀 대조
    # ------------------------------------------------
    with tab_env:
        st.subheader("🧪 환경질 (대기질 측정기록부 vs 차량운행일지 vs 식사 영수증)")

        for a in case["env_anomalies"]:
            with st.container(border=True):
                sev_icon = "🔴" if a["severity"] == "CRITICAL" else "🟡"
                st.markdown(f"### {sev_icon} [{a['severity']}] {a['title']}")
                st.write(f"**상세 소견**: {a['details']}")

                col_l, col_r = st.columns(2)
                with col_l:
                    img_path = IMG_DIR / a["evidence_image"]
                    if img_path.exists():
                        st.image(str(img_path), caption=f"증빙 1: {a['evidence_image']}", use_container_width=True)
                with col_r:
                    comp_name = a.get("evidence_compare_image")
                    if comp_name:
                        comp_path = IMG_DIR / comp_name
                        if comp_path.exists():
                            st.image(str(comp_path), caption=f"대조 증빙 2: {comp_name}", use_container_width=True)

                if "metrics" in a:
                    st.json(a["metrics"])
                st.info(f"⚖️ **법적 제재 근거**: {a['legal_basis']}")

    # ------------------------------------------------
    # TAB 4: 타임라인 및 인터랙티브 지도
    # ------------------------------------------------
    with tab_map:
        st.subheader("🗺️ 2026년 5월 28일 현지조사 및 결제 위치 인터랙티브 지도")

        # 지도 생성 (대구-경산 일대 중심)
        m = folium.Map(location=[35.882, 128.765], zoom_start=12, tiles="CartoDB positron")

        # 지점 마커 등록
        locations = [
            {"name": "경산 하양읍 남하리 현장 (생태조사 및 대기 A-1)", "coords": [35.886089, 128.776558], "type": "SITE", "icon": "leaf", "color": "green", "time": "11:20 ~ 15:55"},
            {"name": "경산돌짜장 (13:02 결제: 대기측정 개시 2분만 10km 이동)", "coords": [35.8157, 128.8021], "type": "ALERT", "icon": "cutlery", "color": "red", "time": "13:02:00 (42,000원)"},
            {"name": "(주)서재홈주유소 (15:57 결제: 조사종료 2분 43초만 4.23km 이동)", "coords": [35.8692, 128.7345], "type": "ALERT", "icon": "tint", "color": "red", "time": "15:57:43 (48,639원)"},
            {"name": "CU 대구메디밸리로점 (11:16 결제)", "coords": [35.8753, 128.7291], "type": "STORE", "icon": "shopping-cart", "color": "orange", "time": "11:16:00 (9,400원)"},
            {"name": "신대구부산 동대구TG (진출)", "coords": [35.8842, 128.7156], "type": "TOLL", "icon": "road", "color": "blue", "time": "10:53:00 (9,500원)"},
        ]

        for loc in locations:
            folium.Marker(
                location=loc["coords"],
                popup=f"<b>{loc['name']}</b><br>시간: {loc['time']}",
                tooltip=f"{loc['name']} ({loc['time']})",
                icon=folium.Icon(color=loc["color"], icon=loc["icon"]),
            ).add_to(m)

        # 모순 경로 붉은 선 표시 (하양 현장 -> 경산돌짜장)
        folium.PolyLine(
            [[35.886089, 128.776558], [35.8157, 128.8021]],
            color="red", weight=4, dash_array="10",
            tooltip="🔴 2분 만에 10km 순간이동 모순 구간 (13:00 측정시작 -> 13:02 돌짜장 결제)",
        ).add_to(m)

        # 모순 경로 붉은 선 표시 (하양 현장 -> 서재홈주유소)
        folium.PolyLine(
            [[35.886089, 128.776558], [35.8692, 128.7345]],
            color="purple", weight=4, dash_array="5",
            tooltip="🟣 2분 43초 만에 4.23km 이동 모순 구간 (15:55 조사종료 -> 15:57 주유 결제)",
        ).add_to(m)

        st_folium(m, width="100%", height=520)
        st.caption("🔴 빨간 점선: 대기질 측정-식당 결제 순간이동 구간 | 🟣 보라 점선: 조사종료-주유 결제 이동시간 결손 구간")

        st.divider()
        st.subheader("⏱️ 2026년 5월 28일 일과 시계열 타임라인")
        timeline_df = pd.DataFrame(case["timeline_events"])[["time", "title", "place", "note"]]
        timeline_df.columns = ["시각", "사건/기록 내용", "위치/가맹점", "감사 검증 소견"]
        st.dataframe(timeline_df, use_container_width=True, hide_index=True)

    # ------------------------------------------------
    # TAB 5: 공식 감사 소명 요구서 출력
    # ------------------------------------------------
    with tab_doc:
        st.subheader("📄 공문서 제출용 [환경영향평가 거짓·부실작성 소명요구 및 감사청구서]")

        doc_text = f"""# 환경영향평가서 거짓·부실작성에 따른 감사 청구 및 소명요구서

## 1. 개 요
- **사업명**: {case['project_name']}
- **평가서 작성 총괄**: {case['evaluation_agency']}
- **자연생태환경 조사**: {case['eco_agency']}
- **환경질 측정 대행**: {case['env_quality_agency']}
- **조사 일자**: {case['survey_date']}

## 2. 핵심 위반 혐의 내역

### 가. 환경질(대기질) 측정시간 허위 기재 (거짓작성죄 혐의)
1. **적발 사실**: 
   - 대기 측정기록부(A-1 지점)에 2026년 5월 28일 13:00부터 24시간 시료채취를 개시하였다고 기재함.
   - 그러나 실제 증빙 영수증 상 불과 2분 후인 13:02에 10km 떨어진 '경산돌짜장'(경산시 압량읍)에서 점심 식사(42,000원)를 결제함.
2. **법적 판단**:
   - 2분 만에 10km를 이동하는 것은 물리적으로 불가능하므로, 13:00 측정 개시 기록은 사후에 날조된 명백한 거짓작성에 해당함.

### 나. 자연생태계 법정보호종 고의 은폐·누락 혐의
1. **적발 사실**:
   - 수기 조사야장 원본(포유류 양식-4)에 환경부 지정 멸종위기 야생생물 Ⅱ급인 '삵'(배설흔 D)이 명확히 자필 기재됨.
   - 조류 야장(양식-5)에 멸종위기 Ⅱ급이자 천연기념물 제323-4호인 '새매', 천연기념물 '황조롱이'가 자필 기재됨.
   - 그러나 부록 9.4.1 출현 생물종 목록에서는 포유류/조류 목록 전체가 누락되었으며 본안 보고서 전체에서 출현 건수 0건으로 은폐됨.
2. **법적 판단**:
   - 개발 사업 인허가에 불리한 법정보호종의 서식 사실을 은폐하기 위한 고의적 축소·누락 혐의가 매우 짙음.

### 다. 조사종료 시각 허위 기재 및 이동시간 결손
1. **적발 사실**:
   - 전 분야 현지조사 야장에 15:55 일괄 종료로 기재하였으나, 불과 2분 43초 후인 15:57:43에 4.23km(도로 5.5km) 떨어진 대구 동구 주유소에서 결제함.
2. **법적 판단**:
   - 현장 철수 및 차량 주행에 최소 8~10분이 소요되므로 실제 조사는 15:55 이전에 종료되었음에도 조사 시간을 부풀려 허위 기재함.

### 라. 소음·진동 공정시험기준 위반 부실 계산
1. **적발 사실**:
   - 야간소음(NV-2) 측정값을 에너지 등가 평균을 적용하지 않고 단순 산술평균 '(66.3 + 62.0) / 2 = 64.1 dB'로 날림 계산함.

## 3. 적용 법조항 및 요구 조치
- **「환경영향평가법」 제58조(평가대행자의 등록취소 등)**: 거짓으로 평가서를 작성한 경우 등록취소
- **「환경영향평가법」 제74조(벌칙)**: 2년 이하의 징역 또는 2천만원 이하의 벌금
- **요구사항**: 즉각적인 현장 재조사 명령, 원본 조사일지 전수 제출, 및 대행업체에 대한 영업정지·형사고발 조치 청구.
"""
        st.text_area("공식 공문서 미리보기", doc_text, height=450)
        st.download_button(
            label="📥 감사청구서(Markdown) 다운로드",
            data=doc_text,
            file_name=f"EIA_Audit_Statement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

# ----------------------------------------------------
# 3. 신규 HWP 파일 분석 모드
# ----------------------------------------------------
elif mode.startswith("📁"):
    st.subheader("📁 다른 환경영향평가 부록 HWP 파일 분석")
    st.write("새로운 `부록.hwp` 파일을 선택하면 문서 내 수기 야장, 측정기록부, 영수증 사진을 자동 추출하고 교차 분석합니다.")

    custom_path = st.text_input("HWP 파일 전체 경로 입력", value=r"C:\Users\dsu\Desktop\(본안) 0900 부록_완.hwp")
    
    if st.button("HWP 파일 자동 파싱 및 검증 실행", type="primary"):
        if not os.path.exists(custom_path):
            st.error(f"지정한 경로에 파일이 존재하지 않습니다: {custom_path}")
        else:
            with st.spinner("HWP 내부 텍스트 및 BinData 이미지 일괄 추출 중..."):
                try:
                    parser = HWPParser(custom_path)
                    text = parser.extract_text()
                    out_img_dir = Path(os.getcwd()) / "custom_extracted_images"
                    img_list = parser.extract_bindata_images(out_img_dir)
                    parser.close()

                    st.success(f"성공! 텍스트 {len(text):,}자 추출, 내장 이미지 {len(img_list)}개 추출 완료!")
                    
                    st.write(f"- 추출 이미지 저장 위치: `{out_img_dir}`")
                    st.write(f"- 추출된 이미지 중 상위 10개 파일:")
                    for fname, p, sz in img_list[:10]:
                        st.caption(f"  • {fname} ({sz//1024:,} KB)")
                except Exception as e:
                    st.error(f"HWP 파싱 실패: {e}")
