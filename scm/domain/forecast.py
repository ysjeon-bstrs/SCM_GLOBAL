import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any

def estimate_daily_consumption(
    snap_long: pd.DataFrame,
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    lookback_days: int = 30
) -> pd.DataFrame:
    """
    일일 소진량을 추정합니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        lookback_days: 회귀 분석 일수
    
    Returns:
        일일 소진량 DataFrame
    """
    results = []
    
    for sku in skus_sel:
        for ct in centers_sel:
            # 센터별 스냅샷 데이터
            snap_ct = snap_long[
                (snap_long["resource_code"] == sku) & 
                (snap_long["center"] == ct)
            ].sort_values("date")
            
            if len(snap_ct) < 2:
                continue
            
            # 출고 데이터
            outbound = moves[
                (moves["resource_code"] == sku) & 
                (moves["from_center"].astype(str) == str(ct)) &
                (moves["onboard_date"].notna())
            ].copy()
            
            if outbound.empty:
                continue
            
            # 일별 출고량 집계
            daily_outbound = (
                outbound.groupby("onboard_date")["qty_ea"]
                .sum()
                .reset_index()
                .rename(columns={"onboard_date": "date"})
            )
            
            # 스냅샷과 출고 데이터 병합
            merged = pd.merge(
                snap_ct[["date", "stock_qty"]], 
                daily_outbound, 
                on="date", 
                how="left"
            ).fillna(0)
            
            # 회귀 분석을 통한 일일 소진량 추정
            if len(merged) >= 2:
                # 최근 lookback_days일 데이터만 사용
                recent_data = merged.tail(lookback_days)
                
                if len(recent_data) >= 2:
                    # 선형 회귀: stock_qty = a - b * days
                    days = np.arange(len(recent_data))
                    stock_qty = recent_data["stock_qty"].values
                    
                    # 회귀 계수 계산
                    n = len(days)
                    sum_x = np.sum(days)
                    sum_y = np.sum(stock_qty)
                    sum_xy = np.sum(days * stock_qty)
                    sum_x2 = np.sum(days * days)
                    
                    # 기울기 (일일 소진량)
                    if n * sum_x2 - sum_x * sum_x != 0:
                        daily_consumption = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                        daily_consumption = max(0, daily_consumption)  # 음수 방지
                        
                        results.append({
                            "resource_code": sku,
                            "center": ct,
                            "daily_consumption": daily_consumption
                        })
    
    return pd.DataFrame(results)

def apply_consumption_with_events(
    timeline: pd.DataFrame,
    snap_long: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
    lookback_days: int = 30,
    events: Optional[List[Dict[str, Any]]] = None
) -> pd.DataFrame:
    """
    소진 예측을 타임라인에 적용합니다.
    
    Args:
        timeline: 타임라인 DataFrame
        snap_long: 정규화된 스냅샷 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        start_dt: 시작 날짜
        end_dt: 종료 날짜
        lookback_days: 회귀 분석 일수
        events: 이벤트 목록
    
    Returns:
        소진 예측이 적용된 타임라인 DataFrame
    """
    if timeline.empty:
        return timeline
    
    out = timeline.copy()
    
    # 일일 소진량 추정
    consumption = estimate_daily_consumption(
        snap_long, moves=None, centers_sel=centers_sel, 
        skus_sel=skus_sel, lookback_days=lookback_days
    )
    
    if consumption.empty:
        return out
    
    # 소진 시작일 계산 (내일부터)
    snap_cols = {c.lower(): c for c in snap_long.columns}
    date_col = snap_cols.get("date") or snap_cols.get("snapshot_date")
    if date_col is None:
        raise KeyError("snap_long에는 'date' 또는 'snapshot_date' 컬럼이 필요합니다.")
    
    latest_snap = pd.to_datetime(snap_long[date_col]).max().normalize()
    today_norm = pd.Timestamp.today().normalize()
    cons_start = max(
        latest_snap + pd.Timedelta(days=1),
        today_norm + pd.Timedelta(days=1),   # 내일부터 시작
        start_dt
    )
    
    if cons_start > end_dt:
        return out
    
    # 이벤트 처리
    idx = pd.date_range(cons_start, end_dt, freq="D")
    uplift = pd.Series(1.0, index=idx)
    if events:
        for e in events:
            if "date" in e and "uplift" in e:
                event_date = pd.to_datetime(e["date"]).normalize()
                if event_date in idx:
                    uplift.loc[event_date] = float(e["uplift"])
    
    # 센터별, SKU별로 소진 적용
    chunks = []
    for (ct, sku), g in out.groupby(["center", "resource_code"]):
        if ct == "In-Transit":
            chunks.append(g)
            continue
        
        # 해당 센터/SKU의 일일 소진량
        cons_data = consumption[
            (consumption["center"] == ct) & 
            (consumption["resource_code"] == sku)
        ]
        
        if cons_data.empty:
            chunks.append(g)
            continue
        
        rate = cons_data["daily_consumption"].iloc[0]
        if rate <= 0:
            chunks.append(g)
            continue
        
        # 소진 적용
        mask = g["date"] >= cons_start
        if not mask.any():
            chunks.append(g)
            continue
        
        daily = g.loc[mask, "date"].map(uplift).fillna(1.0).values * rate
        stk = g.loc[mask, "stock_qty"].astype(float).values
        for i in range(len(stk)):
            dec = daily[i]
            stk[i:] = np.maximum(0.0, stk[i:] - dec)
        # float 값을 int로 변환하여 할당
        g.loc[mask, "stock_qty"] = stk.astype(int)
        chunks.append(g)
    
    if not chunks:
        return out
    
    result = pd.concat(chunks, ignore_index=True)
    result["stock_qty"] = pd.to_numeric(result["stock_qty"], errors="coerce").fillna(0).replace([np.inf, -np.inf], 0).round().clip(lower=0).astype(int)
    
    return result
