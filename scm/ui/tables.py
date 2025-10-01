import streamlit as st
import pandas as pd
from typing import List, Optional

def render_upcoming_arrivals(
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    today: pd.Timestamp,
    lag_days: int = 7
) -> None:
    """
    입고 예정 내역 테이블을 렌더링합니다.
    
    Args:
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        today: 오늘 날짜
        lag_days: 도착-입고 지연 일수
    """
    st.subheader("입고 예정 내역")
    
    # 예측 입고일 계산
    moves_copy = moves.copy()
    moves_copy["pred_inbound_date"] = moves_copy["inbound_date"]
    mask = moves_copy["pred_inbound_date"].isna() & moves_copy["arrival_date"].notna()
    fut = mask & (moves_copy["arrival_date"] > today)
    past = mask & (moves_copy["arrival_date"] <= today)
    
    moves_copy.loc[fut, "pred_inbound_date"] = moves_copy.loc[fut, "arrival_date"]
    moves_copy.loc[past, "pred_inbound_date"] = moves_copy.loc[past, "arrival_date"] + pd.Timedelta(days=lag_days)
    
    # 입고 예정 데이터 필터링
    upcoming = moves_copy[
        (moves_copy["to_center"].isin(centers_sel)) &
        (moves_copy["resource_code"].isin(skus_sel)) &
        (moves_copy["pred_inbound_date"].notna()) &
        (moves_copy["pred_inbound_date"] > today)
    ].copy()
    
    if upcoming.empty:
        st.info("입고 예정 내역이 없습니다.")
        return
    
    # 컬럼 선택 및 정리
    display_cols = [
        "resource_code", "to_center", "qty_ea", 
        "onboard_date", "arrival_date", "pred_inbound_date"
    ]
    
    available_cols = [col for col in display_cols if col in upcoming.columns]
    upcoming_display = upcoming[available_cols].copy()
    
    # 날짜 포맷팅
    date_cols = ["onboard_date", "arrival_date", "pred_inbound_date"]
    for col in date_cols:
        if col in upcoming_display.columns:
            upcoming_display[col] = pd.to_datetime(upcoming_display[col]).dt.strftime("%Y-%m-%d")
    
    # 입고까지 남은 일수 계산
    if "pred_inbound_date" in upcoming_display.columns:
        upcoming_display["days_to_inbound"] = (
            pd.to_datetime(upcoming_display["pred_inbound_date"]) - today
        ).dt.days
    
    # 컬럼명 한글화
    column_mapping = {
        "resource_code": "SKU",
        "to_center": "도착센터",
        "qty_ea": "수량",
        "onboard_date": "출발일",
        "arrival_date": "도착예정일",
        "pred_inbound_date": "입고예정일",
        "days_to_inbound": "입고까지(일)"
    }
    
    upcoming_display = upcoming_display.rename(columns=column_mapping)
    
    # 정렬 (입고예정일 순)
    if "입고예정일" in upcoming_display.columns:
        upcoming_display = upcoming_display.sort_values("입고예정일")
    
    # 테이블 표시
    st.dataframe(
        upcoming_display,
        use_container_width=True,
        hide_index=True
    )

def render_inventory_snapshot(
    snap_long: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    latest_dt: pd.Timestamp
) -> None:
    """
    재고 스냅샷 테이블을 렌더링합니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        latest_dt: 최신 날짜
    """
    st.subheader("현재 재고 스냅샷")
    
    # 스냅샷 데이터 필터링
    snapshot = snap_long[
        (snap_long["date"] == latest_dt) &
        (snap_long["center"].isin(centers_sel)) &
        (snap_long["resource_code"].isin(skus_sel))
    ].copy()
    
    if snapshot.empty:
        st.info("재고 스냅샷 데이터가 없습니다.")
        return
    
    # 피벗 테이블 생성
    pivot_table = snapshot.pivot_table(
        index="resource_code",
        columns="center",
        values="stock_qty",
        fill_value=0,
        aggfunc="sum"
    ).astype(int)
    
    # 총합 행 추가
    pivot_table.loc["총합"] = pivot_table.sum()
    
    # 테이블 표시
    st.dataframe(
        pivot_table,
        use_container_width=True
    )

def render_moves_summary(
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp
) -> None:
    """
    이동 내역 요약 테이블을 렌더링합니다.
    
    Args:
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        start_dt: 시작 날짜
        end_dt: 종료 날짜
    """
    st.subheader("이동 내역 요약")
    
    # 이동 데이터 필터링
    moves_filtered = moves[
        (moves["from_center"].isin(centers_sel) | moves["to_center"].isin(centers_sel)) &
        (moves["resource_code"].isin(skus_sel)) &
        (moves["onboard_date"].notna()) &
        (moves["onboard_date"] >= start_dt) &
        (moves["onboard_date"] <= end_dt)
    ].copy()
    
    if moves_filtered.empty:
        st.info("선택된 기간에 이동 내역이 없습니다.")
        return
    
    # 요약 통계 계산
    summary_stats = []
    
    # 출고 통계
    outbound = moves_filtered[moves_filtered["from_center"].isin(centers_sel)]
    if not outbound.empty:
        outbound_summary = outbound.groupby("from_center")["qty_ea"].sum().reset_index()
        outbound_summary["type"] = "출고"
        outbound_summary = outbound_summary.rename(columns={"from_center": "center"})
        summary_stats.append(outbound_summary)
    
    # 입고 통계
    inbound = moves_filtered[moves_filtered["to_center"].isin(centers_sel)]
    if not inbound.empty:
        inbound_summary = inbound.groupby("to_center")["qty_ea"].sum().reset_index()
        inbound_summary["type"] = "입고"
        inbound_summary = inbound_summary.rename(columns={"to_center": "center"})
        summary_stats.append(inbound_summary)
    
    if summary_stats:
        summary_df = pd.concat(summary_stats, ignore_index=True)
        
        # 피벗 테이블 생성
        pivot_summary = summary_df.pivot_table(
            index="center",
            columns="type",
            values="qty_ea",
            fill_value=0
        ).astype(int)
        
        # 테이블 표시
        st.dataframe(
            pivot_summary,
            use_container_width=True
        )
    else:
        st.info("요약할 데이터가 없습니다.")

def render_sku_details(
    timeline_df: pd.DataFrame,
    sku: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp
) -> None:
    """
    특정 SKU의 상세 정보 테이블을 렌더링합니다.
    
    Args:
        timeline_df: 타임라인 DataFrame
        sku: SKU 코드
        start_dt: 시작 날짜
        end_dt: 종료 날짜
    """
    st.subheader(f"SKU {sku} 상세 정보")
    
    # SKU 데이터 필터링
    sku_data = timeline_df[
        (timeline_df["resource_code"] == sku) &
        (timeline_df["date"] >= start_dt) &
        (timeline_df["date"] <= end_dt)
    ].copy()
    
    if sku_data.empty:
        st.info(f"SKU '{sku}'에 대한 데이터가 없습니다.")
        return
    
    # 피벗 테이블 생성
    pivot_data = sku_data.pivot_table(
        index="date",
        columns="center",
        values="stock_qty",
        fill_value=0
    ).astype(int)
    
    # 날짜 포맷팅
    pivot_data.index = pivot_data.index.strftime("%Y-%m-%d")
    
    # 테이블 표시
    st.dataframe(
        pivot_data,
        use_container_width=True
    )
