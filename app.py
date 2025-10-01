"""
SCM Dashboard - Streamlit 엔트리 포인트
"""
import streamlit as st
import pandas as pd
from scm.config import config
from scm.io.excel import load_from_excel
from scm.io.sheets import load_from_gsheet_api, load_snapshot_raw_from_gsheet
from scm.transform.normalize import normalize_moves, normalize_refined_snapshot
from scm.transform.wip import load_wip_from_incoming, merge_wip_as_moves
from scm.domain.timeline import build_timeline
from scm.domain.forecast import apply_consumption_with_events
from scm.domain.cost import pivot_inventory_cost_from_raw
from scm.utils.dates import today, get_date_range, clamp_date_range

# 페이지 설정
st.set_page_config(page_title="글로벌 대시보드 — v5", layout="wide")
st.title("📦 SCM 재고 흐름 대시보드 — v5 (모듈화)")

# 세션 상태 초기화
if "_data_source" not in st.session_state:
    st.session_state["_data_source"] = None
if "_snapshot_raw_cache" not in st.session_state:
    st.session_state["_snapshot_raw_cache"] = None

# 캐시된 함수들
@st.cache_data(ttl=config.CACHE_TTL_EXCEL)
def _load_excel_cached(file):
    """Excel 로딩 캐시 래퍼"""
    return load_from_excel(file)

@st.cache_data(ttl=config.CACHE_TTL_GSHEET)
def _load_gsheet_cached():
    """Google Sheets 로딩 캐시 래퍼"""
    try:
        gs = st.secrets["google_sheets"]
        creds_obj = gs.get("credentials", None)
        creds_json = gs.get("credentials_json", None)
        
        if creds_obj is not None:
            if isinstance(creds_obj, dict):
                credentials_info = dict(creds_obj)
            else:
                credentials_info = {k: creds_obj[k] for k in creds_obj.keys()}
        elif creds_json:
            import json
            credentials_info = json.loads(str(creds_json))
        else:
            raise ValueError("Google Sheets 인증 정보가 없습니다.")
            
        return load_from_gsheet_api(config.GSHEET_ID, credentials_info)
    except Exception as e:
        st.error(f"Google Sheets 로딩 실패: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=config.CACHE_TTL_EVENTS)
def _apply_consumption_cached(timeline, snap_long, centers_sel, skus_sel, start_dt, end_dt, lookback_days, events):
    """소진 예측 캐시 래퍼"""
    return apply_consumption_with_events(
        timeline, snap_long, centers_sel, skus_sel,
        start_dt, end_dt, lookback_days, events
    )

# 데이터 로딩 UI
tab1, tab2 = st.tabs(["엑셀 업로드", "Google Sheets"])

with tab1:
    xfile = st.file_uploader("엑셀 업로드 (.xlsx)", type=["xlsx"], key="excel")
    if xfile is not None:
        try:
            df_move, df_ref, df_incoming, snap_raw_df = _load_excel_cached(xfile)
            st.session_state["_data_source"] = "excel"
            st.session_state["_snapshot_raw_cache"] = snap_raw_df
            
            moves_raw = normalize_moves(df_move)
            snap_long = normalize_refined_snapshot(df_ref)
            
            try:
                wip_df = load_wip_from_incoming(df_incoming)
                moves = merge_wip_as_moves(moves_raw, wip_df)
                st.success(f"WIP {len(wip_df)}건 반영 완료" if wip_df is not None and not wip_df.empty else "WIP 없음")
            except Exception as e:
                moves = moves_raw
                st.warning(f"WIP 불러오기 실패: {e}")
                
        except Exception as e:
            st.error(f"Excel 로딩 실패: {e}")

with tab2:
    st.info("Google Sheets API를 사용하여 데이터를 로드합니다.")
    
    if st.button("Google Sheets에서 데이터 로드", type="primary"):
        try:
            df_move, df_ref, df_incoming = _load_gsheet_cached()
            
            if df_move.empty or df_ref.empty:
                st.error("❌ Google Sheets에서 데이터를 불러올 수 없습니다.")
            else:
                st.session_state["_data_source"] = "gsheet"
                
                moves_raw = normalize_moves(df_move)
                snap_long = normalize_refined_snapshot(df_ref)
                
                try:
                    wip_df = load_wip_from_incoming(df_incoming)
                    moves = merge_wip_as_moves(moves_raw, wip_df)
                    st.success(f"✅ Google Sheets 로드 완료! WIP {len(wip_df)}건 반영" if wip_df is not None and not wip_df.empty else "✅ Google Sheets 로드 완료! WIP 없음")
                except Exception as e:
                    moves = moves_raw
                    st.warning(f"⚠️ WIP 불러오기 실패: {e}")
        except Exception as e:
            st.error(f"❌ Google Sheets 데이터 로드 중 오류: {e}")

# 데이터가 로드되지 않은 경우 안내
if "snap_long" not in locals():
    st.info("엑셀 업로드 또는 Google Sheets에서 데이터를 로드하면 필터/차트가 나타납니다.")
    st.stop()

# 필터 UI
st.sidebar.header("필터")

# 센터 및 SKU 선택
centers_snap = set(snap_long["center"].dropna().astype(str).unique().tolist())
centers_moves = set(moves["from_center"].dropna().astype(str).unique().tolist() + 
                   moves["to_center"].dropna().astype(str).unique().tolist())

def normalize_center_name(center):
    if center in ["", "nan", "None", "WIP", "In-Transit"]:
        return None
    if center in ["AcrossBUS", "어크로스비US"]:
        return "어크로스비US"
    return center

all_centers = set()
for center in centers_snap | centers_moves:
    normalized = normalize_center_name(center)
    if normalized:
        all_centers.add(normalized)

centers = sorted(list(all_centers))
skus = sorted(snap_long["resource_code"].dropna().astype(str).unique().tolist())

centers_sel = st.sidebar.multiselect("센터 선택", centers, default=(["태광KR"] if "태광KR" in centers else centers[:1]))
skus_sel = st.sidebar.multiselect("SKU 선택", skus, default=([s for s in ["BA00022","BA00021"] if s in skus] or skus[:2]))

# 기간 설정
_today = today()
start_dt, end_dt = get_date_range(_today, config.PAST_DAYS, config.FUTURE_DAYS)

st.sidebar.subheader("기간 설정")
horizon_days = st.sidebar.number_input("미래 전망 일수", min_value=0, max_value=config.FUTURE_DAYS, step=1, value=20)

date_range = st.sidebar.date_input("기간",
    value=(_today - pd.Timedelta(days=20), _today + pd.Timedelta(days=20)),
    min_value=start_dt.date(),
    max_value=end_dt.date(),
    format="YYYY-MM-DD")

start_dt = pd.Timestamp(date_range[0]).normalize()
end_dt = pd.Timestamp(date_range[1]).normalize()

# 표시 옵션
st.sidebar.header("표시 옵션")
show_prod = st.sidebar.checkbox("생산중(미완료) 표시", value=True)
show_transit = st.sidebar.checkbox("이동중 표시", value=True)
use_cons_forecast = st.sidebar.checkbox("추세 기반 재고 예측", value=True)
lookback_days = st.sidebar.number_input("추세 계산 기간(일)", min_value=7, max_value=56, value=config.DEFAULT_LOOKBACK_DAYS, step=7)

# 입고 반영 가정 옵션
st.sidebar.subheader("입고 반영 가정")
lag_days = st.sidebar.number_input("입고 반영 리드타임(일) – inbound 미기록 시 arrival+N", 
                                   min_value=0, max_value=21, value=config.ARRIVAL_TO_INBOUND_LAG_DAYS, step=1)

# 이벤트 설정
with st.sidebar.expander("프로모션 가중치(+%)", expanded=False):
    enable_event = st.checkbox("가중치 적용", value=False)
    ev_start = st.date_input("시작일")
    ev_end   = st.date_input("종료일")
    ev_pct   = st.number_input("가중치(%)", min_value=-100.0, max_value=300.0, value=30.0, step=5.0)
events = [{"start": pd.Timestamp(ev_start).strftime("%Y-%m-%d"),
           "end":   pd.Timestamp(ev_end).strftime("%Y-%m-%d"),
           "uplift": ev_pct/100.0}] if enable_event else []

# 메인 로직
if centers_sel and skus_sel:
    # 타임라인 구축
    _latest_snap = snap_long["date"].max()
    proj_days_for_build = max(0, int((end_dt - _latest_snap).days))
    
    timeline = build_timeline(snap_long, moves, centers_sel, skus_sel,
                              start_dt, end_dt, horizon_days=proj_days_for_build, today=_today,
                              lag_days=int(lag_days))
    
    # 소진 예측 적용
    if use_cons_forecast and not timeline.empty:
        timeline = _apply_consumption_cached(
            timeline, snap_long, centers_sel, skus_sel,
            start_dt, end_dt, lookback_days=int(lookback_days), events=events
        )
    
    # 오늘 앵커: 차트의 '오늘' 값을 스냅샷 값으로 고정
    latest_dt = snap_long["date"].max()
    anchor_base = (snap_long[
        (snap_long["date"] == latest_dt) &
        (snap_long["center"].isin(centers_sel)) &
        (snap_long["resource_code"].isin(skus_sel))
    ].groupby(["center","resource_code"])["stock_qty"].sum())
    
    for (ct, sku), y in anchor_base.items():
        m = ((timeline["center"] == ct) &
             (timeline["resource_code"] == sku) &
             (timeline["date"] == _today))
        timeline.loc[m, "stock_qty"] = int(y)
    
    # 결과 표시
    if timeline.empty:
        st.info("선택 조건에 해당하는 타임라인 데이터가 없습니다.")
    else:
        st.success(f"✅ 타임라인 구축 완료! {len(timeline)}개 데이터 포인트")
        st.dataframe(timeline.head(10))
        
        # 간단한 통계
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 데이터 포인트", f"{len(timeline):,}")
        with col2:
            st.metric("센터 수", f"{timeline['center'].nunique()}")
        with col3:
            st.metric("SKU 수", f"{timeline['resource_code'].nunique()}")
else:
    st.warning("센터와 SKU를 선택해주세요.")
