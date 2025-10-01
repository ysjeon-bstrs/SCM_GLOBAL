import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# 모듈화된 함수들 import
import sys
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# scm 모듈 import
try:
    from scm.config import DEFAULT_CONFIG
except ImportError as e:
    st.error(f"모듈 import 오류: {e}")
    st.info("streamlit_scm_step_v4.py를 사용해주세요.")
    st.stop()
from scm.io.excel import load_from_excel, load_snapshot_from_excel, load_moves_from_excel
from scm.io.sheets import load_from_gsheet_api, load_snapshot_from_gsheet, load_moves_from_gsheet
from scm.transform.normalize import normalize_refined_snapshot, normalize_moves
from scm.transform.wip import load_wip_from_incoming, merge_wip_as_moves
from scm.domain.timeline import build_timeline
from scm.domain.forecast import apply_consumption_with_events
from scm.domain.cost import pivot_inventory_cost_from_raw
from scm.ui.kpi import render_kpis, render_center_kpis, render_sku_kpis
from scm.ui.charts import plot_step_chart, plot_inventory_distribution, plot_sku_trend
from scm.ui.tables import render_upcoming_arrivals, render_inventory_snapshot, render_moves_summary
from scm.utils.dates import today, get_date_range, clamp_date_range

# 페이지 설정
st.set_page_config(
    page_title="SCM Dashboard (Modular)",
    page_icon="📊",
    layout="wide"
)

st.title("📊 SCM 재고 흐름 대시보드 (모듈화 버전)")
st.caption("글로벌 공급망 관리를 위한 재고 흐름 시각화")

# 사이드바 설정
st.sidebar.header("⚙️ 설정")

# 데이터 소스 선택
data_source = st.sidebar.radio(
    "데이터 소스",
    ["Excel 파일", "Google Sheets"],
    help="데이터를 불러올 소스를 선택하세요"
)

# Excel 파일 업로드
if data_source == "Excel 파일":
    uploaded_file = st.sidebar.file_uploader(
        "Excel 파일 업로드",
        type=['xlsx', 'xls'],
        help="스냅샷과 이동 데이터가 포함된 Excel 파일을 업로드하세요"
    )
    
    if uploaded_file is not None:
        try:
            # Excel에서 데이터 로드
            excel_data = load_from_excel(uploaded_file)
            snap_raw = load_snapshot_from_excel(uploaded_file)
            moves_raw = load_moves_from_excel(uploaded_file)
            
            st.sidebar.success("Excel 파일이 성공적으로 로드되었습니다!")
            
        except Exception as e:
            st.sidebar.error(f"Excel 파일 로딩 중 오류가 발생했습니다: {str(e)}")
            st.stop()
    else:
        st.info("Excel 파일을 업로드하세요.")
        st.stop()

# Google Sheets 연결
elif data_source == "Google Sheets":
    gsheet_id = st.sidebar.text_input(
        "Google Sheets ID",
        value=DEFAULT_CONFIG.gsheet_id,
        help="Google Sheets의 ID를 입력하세요"
    )
    
    if st.sidebar.button("Google Sheets에서 데이터 로드"):
        try:
            # Google Sheets에서 데이터 로드
            snap_raw = load_snapshot_from_gsheet(gsheet_id)
            moves_raw = load_moves_from_gsheet(gsheet_id)
            
            st.sidebar.success("Google Sheets에서 데이터가 성공적으로 로드되었습니다!")
            
        except Exception as e:
            st.sidebar.error(f"Google Sheets 로딩 중 오류가 발생했습니다: {str(e)}")
            st.stop()
    else:
        st.info("Google Sheets에서 데이터를 로드하세요.")
        st.stop()

# 데이터 정규화
try:
    snap_long = normalize_refined_snapshot(snap_raw)
    moves = normalize_moves(moves_raw)
    
    st.success("데이터가 성공적으로 정규화되었습니다!")
    
except Exception as e:
    st.error(f"데이터 정규화 중 오류가 발생했습니다: {str(e)}")
    st.stop()

# 필터 옵션
st.sidebar.header("🔍 필터")

# 센터 선택
available_centers = sorted(snap_long["center"].unique())
centers_sel = st.sidebar.multiselect(
    "센터 선택",
    available_centers,
    default=available_centers[:3] if len(available_centers) >= 3 else available_centers,
    help="분석할 센터를 선택하세요"
)

# SKU 선택
available_skus = sorted(snap_long["resource_code"].unique())
skus_sel = st.sidebar.multiselect(
    "SKU 선택",
    available_skus,
    default=available_skus[:5] if len(available_skus) >= 5 else available_skus,
    help="분석할 SKU를 선택하세요"
)

# 기간 설정
st.sidebar.header("📅 기간 설정")

# 날짜 범위
today_norm = today()
start_date, end_date = get_date_range(days_back=30, days_forward=30)

date_range = st.sidebar.date_input(
    "분석 기간",
    value=(start_date.date(), end_date.date()),
    min_value=(today_norm - timedelta(days=365)).date(),
    max_value=(today_norm + timedelta(days=365)).date(),
    format="YYYY-MM-DD"
)

start_dt = pd.Timestamp(date_range[0])
end_dt = pd.Timestamp(date_range[1])

# 미래 전망 일수
proj_days = st.sidebar.number_input(
    "미래 전망 일수",
    min_value=0,
    max_value=365,
    value=30,
    help="미래 몇 일까지 예측할지 설정하세요"
)

# 고급 옵션
st.sidebar.header("⚙️ 고급 옵션")

# 입고 반영 리드타임
lag_days = st.sidebar.number_input(
    "입고 반영 리드타임(일)",
    min_value=0,
    max_value=21,
    value=DEFAULT_CONFIG.arrival_to_inbound_lag_days,
    help="inbound 미기록 시 arrival+N일로 가정"
)

# 소진 예측 사용 여부
use_cons_forecast = st.sidebar.checkbox(
    "소진 예측 사용",
    value=True,
    help="일일 소진량을 기반으로 한 예측을 사용합니다"
)

# 메인 콘텐츠
if not centers_sel or not skus_sel:
    st.warning("센터와 SKU를 선택해주세요.")
    st.stop()

# 최신 스냅샷 날짜
latest_dt = snap_long["date"].max()

# KPI 섹션
st.header("📊 주요 지표")
render_kpis(snap_long, moves, centers_sel, skus_sel, latest_dt, today_norm, lag_days)

st.divider()

# 계단식 차트
st.header("📈 재고 흐름 타임라인")

# 타임라인 생성
timeline = build_timeline(
    snap_long, moves, centers_sel, skus_sel,
    start_dt, end_dt, horizon_days=proj_days, today=today_norm,
    lag_days=lag_days
)

# 소진 예측 적용
if use_cons_forecast and not timeline.empty:
    timeline = apply_consumption_with_events(
        timeline, snap_long, centers_sel, skus_sel,
        start_dt, end_dt, lookback_days=30, events=None
    )

# 오늘 앵커: 차트의 '오늘' 값을 스냅샷 값으로 고정
anchor_base = (snap_long[
    (snap_long["date"] == latest_dt) &
    (snap_long["center"].isin(centers_sel)) &
    (snap_long["resource_code"].isin(skus_sel))
].groupby(["center","resource_code"])["stock_qty"].sum())

for (ct, sku), y in anchor_base.items():
    m = ((timeline["center"] == ct) &
         (timeline["resource_code"] == sku) &
         (timeline["date"] == today_norm))
    timeline.loc[m, "stock_qty"] = int(y)

# 차트 렌더링
if timeline.empty:
    st.info("선택 조건에 해당하는 타임라인 데이터가 없습니다.")
else:
    plot_step_chart(timeline, start_dt, end_dt, today_norm)

# 탭으로 추가 정보 표시
tab1, tab2, tab3 = st.tabs(["📋 입고 예정", "📊 재고 분포", "📈 SKU 상세"])

with tab1:
    render_upcoming_arrivals(moves, centers_sel, skus_sel, today_norm, lag_days)

with tab2:
    plot_inventory_distribution(snap_long, centers_sel, skus_sel, latest_dt)

with tab3:
    if skus_sel:
        selected_sku = st.selectbox("SKU 선택", skus_sel)
        plot_sku_trend(timeline, selected_sku, start_dt, end_dt)

# 센터별 KPI
st.header("🏢 센터별 현황")
render_center_kpis(snap_long, moves, centers_sel, skus_sel, latest_dt, today_norm)

# SKU별 KPI
st.header("📦 SKU별 현황")
render_sku_kpis(snap_long, moves, centers_sel, skus_sel, latest_dt, today_norm)
