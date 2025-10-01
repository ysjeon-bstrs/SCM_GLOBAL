import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
import re

def _parse_po_date(date_str: str) -> Optional[pd.Timestamp]:
    """
    PO 날짜 문자열을 파싱합니다.
    
    Args:
        date_str: 날짜 문자열
    
    Returns:
        파싱된 Timestamp 또는 None
    """
    if pd.isna(date_str) or date_str == "":
        return None
    
    try:
        # 다양한 날짜 형식 시도
        date_formats = [
            "%Y-%m-%d",
            "%Y/%m/%d", 
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S"
        ]
        
        for fmt in date_formats:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except ValueError:
                continue
        
        # 자동 파싱 시도
        return pd.to_datetime(date_str, errors="coerce")
        
    except Exception:
        return None

def load_wip_from_incoming(
    moves: pd.DataFrame,
    wip_columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    이동 데이터에서 WIP 정보를 추출합니다.
    
    Args:
        moves: 이동 데이터 DataFrame
        wip_columns: WIP 관련 컬럼 목록
    
    Returns:
        WIP 데이터 DataFrame
    """
    if moves.empty:
        return pd.DataFrame(columns=["resource_code", "po_number", "po_date", "qty_ea", "status"])
    
    # WIP 관련 컬럼 찾기
    if wip_columns is None:
        wip_columns = []
        for col in moves.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ["po", "purchase", "order", "wip", "work"]):
                wip_columns.append(col)
    
    if not wip_columns:
        return pd.DataFrame(columns=["resource_code", "po_number", "po_date", "qty_ea", "status"])
    
    # WIP 데이터 추출
    wip_data = []
    
    for _, row in moves.iterrows():
        # PO 번호 찾기
        po_number = None
        for col in wip_columns:
            if "po" in col.lower() and "number" in col.lower():
                po_number = row[col]
                break
        
        if pd.isna(po_number) or po_number == "":
            continue
        
        # PO 날짜 찾기
        po_date = None
        for col in wip_columns:
            if "po" in col.lower() and "date" in col.lower():
                po_date = _parse_po_date(row[col])
                break
        
        # 수량 찾기
        qty = row.get("qty_ea", 0)
        if pd.isna(qty) or qty <= 0:
            continue
        
        # 상태 결정
        status = "In Production"
        if po_date and po_date < pd.Timestamp.today():
            status = "Delayed"
        
        wip_data.append({
            "resource_code": row.get("resource_code", ""),
            "po_number": str(po_number),
            "po_date": po_date,
            "qty_ea": int(qty),
            "status": status
        })
    
    return pd.DataFrame(wip_data)

def merge_wip_as_moves(
    moves: pd.DataFrame,
    wip_data: pd.DataFrame,
    wip_lead_days: int = 30
) -> pd.DataFrame:
    """
    WIP 데이터를 이동 데이터로 병합합니다.
    
    Args:
        moves: 기존 이동 데이터
        wip_data: WIP 데이터
        wip_lead_days: WIP 리드 타임 (일)
    
    Returns:
        병합된 이동 데이터
    """
    if wip_data.empty:
        return moves
    
    # WIP를 이동 데이터로 변환
    wip_moves = []
    
    for _, wip in wip_data.iterrows():
        # 예상 도착일 계산
        if pd.notna(wip["po_date"]):
            expected_arrival = wip["po_date"] + pd.Timedelta(days=wip_lead_days)
        else:
            expected_arrival = pd.Timestamp.today() + pd.Timedelta(days=wip_lead_days)
        
        wip_moves.append({
            "resource_code": wip["resource_code"],
            "from_center": "WIP",
            "to_center": "Unknown",  # 실제 도착지가 명시되지 않은 경우
            "qty_ea": wip["qty_ea"],
            "onboard_date": wip["po_date"],
            "arrival_date": expected_arrival,
            "inbound_date": None,
            "carrier_mode": "WIP",
            "po_number": wip["po_number"],
            "status": wip["status"]
        })
    
    wip_moves_df = pd.DataFrame(wip_moves)
    
    # 기존 이동 데이터와 병합
    if moves.empty:
        return wip_moves_df
    else:
        return pd.concat([moves, wip_moves_df], ignore_index=True)

def calculate_wip_metrics(wip_data: pd.DataFrame) -> Dict[str, Any]:
    """
    WIP 메트릭을 계산합니다.
    
    Args:
        wip_data: WIP 데이터
    
    Returns:
        WIP 메트릭 딕셔너리
    """
    if wip_data.empty:
        return {
            "total_wip_qty": 0,
            "total_wip_value": 0,
            "delayed_orders": 0,
            "avg_lead_time": 0
        }
    
    total_qty = wip_data["qty_ea"].sum()
    delayed_orders = len(wip_data[wip_data["status"] == "Delayed"])
    
    # 평균 리드 타임 계산
    if "po_date" in wip_data.columns:
        valid_dates = wip_data.dropna(subset=["po_date"])
        if not valid_dates.empty:
            today = pd.Timestamp.today()
            lead_times = (today - valid_dates["po_date"]).dt.days
            avg_lead_time = lead_times.mean() if not lead_times.empty else 0
        else:
            avg_lead_time = 0
    else:
        avg_lead_time = 0
    
    return {
        "total_wip_qty": int(total_qty),
        "total_wip_value": 0,  # 비용 정보가 없으면 0
        "delayed_orders": int(delayed_orders),
        "avg_lead_time": float(avg_lead_time)
    }
