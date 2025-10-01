import pandas as pd
from typing import List, Optional

def pivot_inventory_cost_from_raw(
    snap_long: pd.DataFrame,
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    latest_dt: pd.Timestamp,
    cost_per_unit: Optional[float] = None
) -> pd.DataFrame:
    """
    재고 비용을 피벗 테이블로 변환합니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        latest_dt: 최신 날짜
        cost_per_unit: 단위당 비용 (기본값: 1.0)
    
    Returns:
        비용 피벗 테이블 DataFrame
    """
    if cost_per_unit is None:
        cost_per_unit = 1.0
    
    # 최신 스냅샷 데이터 필터링
    latest_snap = snap_long[
        (snap_long["date"] == latest_dt) &
        (snap_long["center"].isin(centers_sel)) &
        (snap_long["resource_code"].isin(skus_sel))
    ].copy()
    
    if latest_snap.empty:
        return pd.DataFrame(columns=["center", "resource_code", "stock_qty", "cost"])
    
    # 비용 계산
    latest_snap["cost"] = latest_snap["stock_qty"] * cost_per_unit
    
    # 피벗 테이블 생성
    pivot_df = latest_snap.groupby(["center", "resource_code"]).agg({
        "stock_qty": "sum",
        "cost": "sum"
    }).reset_index()
    
    return pivot_df
