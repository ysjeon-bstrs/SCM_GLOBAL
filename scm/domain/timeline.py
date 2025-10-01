import pandas as pd
import numpy as np
from typing import List, Optional

def build_timeline(
    snap_long: pd.DataFrame,
    moves: pd.DataFrame,
    centers_sel: List[str],
    skus_sel: List[str],
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
    horizon_days: int = 0,
    today: Optional[pd.Timestamp] = None,
    lag_days: int = 7
) -> pd.DataFrame:
    """
    재고 타임라인을 구축합니다.
    
    Args:
        snap_long: 정규화된 스냅샷 데이터
        moves: 이동 데이터
        centers_sel: 선택된 센터 목록
        skus_sel: 선택된 SKU 목록
        start_dt: 시작 날짜
        end_dt: 종료 날짜
        horizon_days: 미래 전망 일수
        today: 오늘 날짜
        lag_days: 도착-입고 지연 일수
    
    Returns:
        타임라인 DataFrame
    """
    if today is None:
        today = pd.Timestamp.today().normalize()
    
    horizon_end = end_dt + pd.Timedelta(days=horizon_days)
    lines = []
    
    for sku in skus_sel:
        # 스냅샷 데이터 필터링
        snap_sku = snap_long[
            (snap_long["resource_code"] == sku) & 
            (snap_long["center"].isin(centers_sel))
        ].copy()
        
        if snap_sku.empty:
            continue
            
        # 이동 데이터 필터링
        mv = moves[moves["resource_code"] == sku].copy()
        
        # 예측 입고일 계산
        mv["pred_inbound_date"] = mv["inbound_date"]
        mask = mv["pred_inbound_date"].isna() & mv["arrival_date"].notna()
        fut = mask & (mv["arrival_date"] > today)
        past = mask & (mv["arrival_date"] <= today)
        
        mv.loc[fut, "pred_inbound_date"] = mv.loc[fut, "arrival_date"]
        mv.loc[past, "pred_inbound_date"] = mv.loc[past, "arrival_date"] + pd.Timedelta(days=lag_days)
        
        # In-Transit 종료일 계산
        mv["pred_end_date"] = mv["pred_inbound_date"]
        mv.loc[mv["pred_end_date"].isna(), "pred_end_date"] = today + pd.Timedelta(days=1)
        
        for ct in centers_sel:
            # 센터별 스냅샷
            snap_ct = snap_sku[snap_sku["center"] == ct]
            if snap_ct.empty:
                continue
                
            # 최신 스냅샷 날짜
            latest_dt = snap_ct["date"].max()
            base_stock = snap_ct[snap_ct["date"] == latest_dt]["stock_qty"].sum()
            
            # 타임라인 생성
            idx = pd.date_range(start_dt, horizon_end, freq="D")
            
            # 출고 이벤트
            eff_minus = (
                mv[(mv["from_center"].astype(str) == str(ct)) & 
                   (mv["onboard_date"].notna()) & 
                   (mv["onboard_date"] > latest_dt)]
                .groupby("onboard_date", as_index=False)["qty_ea"].sum()
                .rename(columns={"onboard_date": "date", "qty_ea": "delta"})
            )
            eff_minus["delta"] *= -1
            
            # 입고 이벤트 (예측 입고일 사용)
            eff_plus = (
                mv[(mv["to_center"].astype(str) == str(ct)) & 
                   (mv["pred_inbound_date"].notna()) & 
                   (mv["pred_inbound_date"] > latest_dt)]
                .groupby("pred_inbound_date", as_index=False)["qty_ea"].sum()
                .rename(columns={"pred_inbound_date": "date", "qty_ea": "delta"})
            )
            
            # 이벤트 합치기
            events = pd.concat([eff_minus, eff_plus], ignore_index=True)
            if not events.empty:
                events = events.groupby("date")["delta"].sum().reset_index()
                events = events.set_index("date").reindex(idx, fill_value=0)["delta"]
            else:
                events = pd.Series(0, index=idx)
            
            # 재고 계산
            stock_series = pd.Series(base_stock, index=idx)
            for i, (date, delta) in enumerate(events.items()):
                if i == 0:
                    stock_series.iloc[i:] += delta
                else:
                    stock_series.iloc[i:] += delta
            
            stock_series = stock_series.clip(lower=0).astype(int)
            
            # 결과 추가
            lines.append(pd.DataFrame({
                "date": stock_series.index,
                "center": ct,
                "resource_code": sku,
                "stock_qty": stock_series.values
            }))
            
            # In-Transit 라인 (Non-WIP)
            g_nonwip = mv[
                (mv["carrier_mode"] != "WIP") & 
                (mv["to_center"].astype(str) == str(ct))
            ].copy()
            
            if not g_nonwip.empty:
                # 시작: onboard_date
                starts = (
                    g_nonwip.dropna(subset=["onboard_date"])
                    .groupby("onboard_date")["qty_ea"].sum()
                )
                
                # 종료: pred_end_date
                ends = (
                    g_nonwip.groupby("pred_end_date")["qty_ea"].sum() * -1
                )
                
                # 델타 계산
                delta = (
                    starts.rename_axis("date").to_frame("delta")
                    .add(ends.rename_axis("date").to_frame("delta"), fill_value=0)["delta"]
                    .sort_index()
                )
                
                s = delta.reindex(idx, fill_value=0).cumsum().clip(lower=0)
                
                if s.any():
                    lines.append(pd.DataFrame({
                        "date": s.index,
                        "center": "In-Transit",
                        "resource_code": sku,
                        "stock_qty": s.values
                    }))
    
    if not lines:
        return pd.DataFrame(columns=["date", "center", "resource_code", "stock_qty"])
    
    return pd.concat(lines, ignore_index=True)
