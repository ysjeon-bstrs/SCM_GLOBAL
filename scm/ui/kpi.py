import streamlit as st
import pandas as pd
from typing import List, Dict, Any

def render_kpis(
    snap_long: pd.DataFrame,
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    latest_dt: pd.Timestamp,
    today: pd.Timestamp,
    lag_days: int = 7
) -> None:
    """
    KPI 카드들을 렌더링합니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        latest_dt: 최신 날짜
        today: 오늘 날짜
        lag_days: 도착-입고 지연 일수
    """
    # 현재 재고 계산
    current_stock = snap_long[
        (snap_long["date"] == latest_dt) &
        (snap_long["center"].isin(centers_sel)) &
        (snap_long["resource_code"].isin(skus_sel))
    ]["stock_qty"].sum()
    
    # 이동중 재고 계산 (Non-WIP)
    in_transit_mask = (
        (moves["carrier_mode"] != "WIP") &
        (moves["to_center"].isin(centers_sel)) &
        (moves["resource_code"].isin(skus_sel)) &
        (moves["onboard_date"].notna()) &
        (moves["onboard_date"] <= today)
    )
    
    # 예측 입고일 계산
    moves_copy = moves.copy()
    moves_copy["pred_inbound_date"] = moves_copy["inbound_date"]
    mask = moves_copy["pred_inbound_date"].isna() & moves_copy["arrival_date"].notna()
    fut = mask & (moves_copy["arrival_date"] > today)
    past = mask & (moves_copy["arrival_date"] <= today)
    
    moves_copy.loc[fut, "pred_inbound_date"] = moves_copy.loc[fut, "arrival_date"]
    moves_copy.loc[past, "pred_inbound_date"] = moves_copy.loc[past, "arrival_date"] + pd.Timedelta(days=lag_days)
    moves_copy["pred_end_date"] = moves_copy["pred_inbound_date"]
    moves_copy.loc[moves_copy["pred_end_date"].isna(), "pred_end_date"] = today + pd.Timedelta(days=1)
    
    in_transit_total = moves_copy[
        in_transit_mask & (today < moves_copy["pred_end_date"])
    ]["qty_ea"].sum()
    
    # WIP 재고 계산
    wip_total = moves[
        (moves["carrier_mode"] == "WIP") &
        (moves["to_center"].isin(centers_sel)) &
        (moves["resource_code"].isin(skus_sel))
    ]["qty_ea"].sum()
    
    # KPI 카드 렌더링
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="현재 재고",
            value=f"{int(current_stock):,}",
            help="최신 스냅샷 기준 재고"
        )
    
    with col2:
        st.metric(
            label="이동중 재고",
            value=f"{int(in_transit_total):,}",
            help="Non-WIP 이동중 재고"
        )
    
    with col3:
        st.metric(
            label="WIP 재고",
            value=f"{int(wip_total):,}",
            help="Work In Progress 재고"
        )
    
    with col4:
        total_inventory = current_stock + in_transit_total + wip_total
        st.metric(
            label="총 재고",
            value=f"{int(total_inventory):,}",
            help="현재 + 이동중 + WIP 재고"
        )

def render_center_kpis(
    snap_long: pd.DataFrame,
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    latest_dt: pd.Timestamp,
    today: pd.Timestamp
) -> None:
    """
    센터별 KPI를 렌더링합니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        latest_dt: 최신 날짜
        today: 오늘 날짜
    """
    st.subheader("센터별 재고 현황")
    
    for center in centers_sel:
        with st.expander(f"📦 {center}", expanded=False):
            # 센터별 현재 재고
            center_stock = snap_long[
                (snap_long["date"] == latest_dt) &
                (snap_long["center"] == center) &
                (snap_long["resource_code"].isin(skus_sel))
            ]["stock_qty"].sum()
            
            # 센터별 이동중 재고
            center_in_transit = moves[
                (moves["to_center"] == center) &
                (moves["resource_code"].isin(skus_sel)) &
                (moves["onboard_date"].notna()) &
                (moves["onboard_date"] <= today) &
                (moves["inbound_date"].isna())
            ]["qty_ea"].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("현재 재고", f"{int(center_stock):,}")
            with col2:
                st.metric("이동중 재고", f"{int(center_in_transit):,}")

def render_sku_kpis(
    snap_long: pd.DataFrame,
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    latest_dt: pd.Timestamp,
    today: pd.Timestamp
) -> None:
    """
    SKU별 KPI를 렌더링합니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        latest_dt: 최신 날짜
        today: 오늘 날짜
    """
    st.subheader("SKU별 재고 현황")
    
    # SKU별 재고 집계
    sku_stock = snap_long[
        (snap_long["date"] == latest_dt) &
        (snap_long["center"].isin(centers_sel)) &
        (snap_long["resource_code"].isin(skus_sel))
    ].groupby("resource_code")["stock_qty"].sum().sort_values(ascending=False)
    
    if not sku_stock.empty:
        # 상위 10개 SKU만 표시
        top_skus = sku_stock.head(10)
        
        for sku, stock in top_skus.items():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{sku}**")
            with col2:
                st.metric("재고", f"{int(stock):,}")
            with col3:
                # SKU별 이동중 재고
                sku_in_transit = moves[
                    (moves["resource_code"] == sku) &
                    (moves["to_center"].isin(centers_sel)) &
                    (moves["onboard_date"].notna()) &
                    (moves["onboard_date"] <= today) &
                    (moves["inbound_date"].isna())
                ]["qty_ea"].sum()
                st.metric("이동중", f"{int(sku_in_transit):,}")
    else:
        st.info("선택된 조건에 해당하는 SKU가 없습니다.")
