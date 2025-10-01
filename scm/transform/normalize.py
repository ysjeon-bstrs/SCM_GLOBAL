import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

class NormalizationError(Exception):
    """데이터 정규화 에러"""
    pass

def _flatten_candidates(candidates: List[str]) -> str:
    """후보 컬럼명들을 하나의 문자열로 합칩니다."""
    return " | ".join(candidates)

def coalesce_columns(df: pd.DataFrame, column_mapping: Dict[str, List[str]]) -> pd.DataFrame:
    """
    여러 컬럼을 하나로 합칩니다.
    
    Args:
        df: 원본 DataFrame
        column_mapping: 컬럼 매핑 딕셔너리 {새컬럼명: [기존컬럼명들]}
    
    Returns:
        정규화된 DataFrame
    """
    result = df.copy()
    
    for new_col, old_cols in column_mapping.items():
        # 기존 컬럼들 중 존재하는 것들만 선택
        existing_cols = [col for col in old_cols if col in df.columns]
        
        if not existing_cols:
            continue
        
        # 첫 번째로 존재하는 컬럼의 값을 사용
        result[new_col] = df[existing_cols[0]]
        
        # 나머지 컬럼들도 확인하여 누락된 값 채우기
        for col in existing_cols[1:]:
            mask = result[new_col].isna() & df[col].notna()
            result.loc[mask, new_col] = df.loc[mask, col]
    
    return result

def normalize_refined_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """
    정제된 스냅샷 데이터를 정규화합니다.
    
    Args:
        df: 원본 스냅샷 DataFrame
    
    Returns:
        정규화된 스냅샷 DataFrame
    """
    if df.empty:
        raise NormalizationError("스냅샷 데이터가 비어있습니다.")
    
    result = df.copy()
    
    # 컬럼명 정규화
    result.columns = result.columns.astype(str).str.strip()
    
    # 필수 컬럼 매핑 (더 많은 변형 포함)
    column_mapping = {
        "resource_code": ["resource_code", "sku", "product_code", "item_code", "SKU", "Product Code"],
        "center": ["center", "warehouse", "location", "센터", "Center", "Warehouse", "Location"],
        "stock_qty": ["stock_qty", "quantity", "qty", "재고수량", "Stock Qty", "Quantity", "Qty"],
        "date": ["date", "snapshot_date", "created_date", "날짜", "Date", "Snapshot Date"]
    }
    
    result = coalesce_columns(result, column_mapping)
    
    # 필수 컬럼 확인 및 자동 매핑 시도
    required_cols = ["resource_code", "center", "stock_qty", "date"]
    missing_cols = [col for col in required_cols if col not in result.columns]
    
    if missing_cols:
        # 자동 매핑 시도
        auto_mapping = {}
        for col in missing_cols:
            if col == "resource_code":
                # SKU 관련 컬럼 찾기
                sku_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["sku", "product", "item"])]
                if sku_candidates:
                    auto_mapping[col] = sku_candidates[0]
            elif col == "center":
                # 센터 관련 컬럼 찾기
                center_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["center", "warehouse", "location"])]
                if center_candidates:
                    auto_mapping[col] = center_candidates[0]
            elif col == "stock_qty":
                # 수량 관련 컬럼 찾기
                qty_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["qty", "quantity", "stock"])]
                if qty_candidates:
                    auto_mapping[col] = qty_candidates[0]
            elif col == "date":
                # 날짜 관련 컬럼 찾기
                date_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["date", "time"])]
                if date_candidates:
                    auto_mapping[col] = date_candidates[0]
        
        # 자동 매핑 적용
        if auto_mapping:
            for new_col, old_col in auto_mapping.items():
                result[new_col] = result[old_col]
                st.info(f"자동 매핑: '{old_col}' → '{new_col}'")
        
        # 다시 확인
        missing_cols = [col for col in required_cols if col not in result.columns]
        if missing_cols:
            # 사용 가능한 컬럼 목록 표시
            available_cols = list(result.columns)
            raise NormalizationError(f"필수 컬럼이 없습니다: {missing_cols}\n사용 가능한 컬럼: {available_cols}")
    
    # 데이터 타입 변환
    result["stock_qty"] = pd.to_numeric(result["stock_qty"], errors="coerce").fillna(0).astype(int)
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    
    # 날짜가 없는 행 제거
    result = result.dropna(subset=["date"])
    
    # 중복 제거
    result = result.drop_duplicates(subset=["resource_code", "center", "date"])
    
    return result

def normalize_moves(df: pd.DataFrame) -> pd.DataFrame:
    """
    이동 데이터를 정규화합니다.
    
    Args:
        df: 원본 이동 DataFrame
    
    Returns:
        정규화된 이동 DataFrame
    """
    if df.empty:
        raise NormalizationError("이동 데이터가 비어있습니다.")
    
    result = df.copy()
    
    # 컬럼명 정규화
    result.columns = result.columns.astype(str).str.strip()
    
    # 필수 컬럼 매핑
    column_mapping = {
        "resource_code": ["resource_code", "sku", "product_code", "item_code"],
        "from_center": ["from_center", "from_warehouse", "from_location", "출발센터"],
        "to_center": ["to_center", "to_warehouse", "to_location", "도착센터"],
        "qty_ea": ["qty_ea", "quantity", "qty", "수량"],
        "onboard_date": ["onboard_date", "departure_date", "ship_date", "출발일"],
        "arrival_date": ["arrival_date", "eta", "expected_arrival", "도착예정일"],
        "inbound_date": ["inbound_date", "received_date", "입고일"],
        "carrier_mode": ["carrier_mode", "transport_mode", "운송수단"]
    }
    
    result = coalesce_columns(result, column_mapping)
    
    # 필수 컬럼 확인
    required_cols = ["resource_code", "from_center", "to_center", "qty_ea"]
    missing_cols = [col for col in required_cols if col not in result.columns]
    if missing_cols:
        raise NormalizationError(f"필수 컬럼이 없습니다: {missing_cols}")
    
    # 데이터 타입 변환
    result["qty_ea"] = pd.to_numeric(result["qty_ea"], errors="coerce").fillna(0).astype(int)
    
    # 날짜 컬럼들 변환
    date_cols = ["onboard_date", "arrival_date", "inbound_date"]
    for col in date_cols:
        if col in result.columns:
            result[col] = pd.to_datetime(result[col], errors="coerce")
    
    # 수량이 0인 행 제거
    result = result[result["qty_ea"] > 0]
    
    # 중복 제거
    result = result.drop_duplicates()
    
    return result
