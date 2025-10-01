import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import logging

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
    
    # 필수 컬럼 매핑
    column_mapping = {
        "resource_code": ["resource_code", "sku", "product_code", "item_code", "SKU", "Product Code"],
        "date": ["date", "snapshot_date", "created_date", "날짜", "Date", "Snapshot Date"]
    }
    
    result = coalesce_columns(result, column_mapping)
    
    # 필수 컬럼 확인
    required_cols = ["resource_code", "date"]
    missing_cols = [col for col in required_cols if col not in result.columns]
    
    if missing_cols:
        # 자동 매핑 시도
        auto_mapping = {}
        for col in missing_cols:
            if col == "resource_code":
                sku_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["sku", "product", "item"])]
                if sku_candidates:
                    auto_mapping[col] = sku_candidates[0]
            elif col == "date":
                date_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["date", "time"])]
                if date_candidates:
                    auto_mapping[col] = date_candidates[0]
        
        if auto_mapping:
            for new_col, old_col in auto_mapping.items():
                result[new_col] = result[old_col]
                logging.info(f"자동 매핑: '{old_col}' → '{new_col}'")
        
        missing_cols = [col for col in required_cols if col not in result.columns]
        if missing_cols:
            available_cols = list(result.columns)
            raise NormalizationError(f"필수 컬럼이 없습니다: {missing_cols}\n사용 가능한 컬럼: {available_cols}")
    
    # 센터별 재고 컬럼 찾기 및 변환
    center_columns = {}
    center_mapping = {
        "태광KR": ["stock2"],
        "AMZUS": ["fba_available_stock"],
        "품고KR": ["poomgo_v2_available_stock"],
        "SBSPH": ["shopee_ph_available_stock"],
        "SBSSG": ["shopee_sg_available_stock"],
        "SBSMY": ["shopee_my_available_stock"],
        "AcrossBUS": ["acrossb_available_stock"],
        "어크로스비US": ["acrossb_available_stock"]
    }
    
    for center, possible_cols in center_mapping.items():
        for col in possible_cols:
            if col in result.columns:
                center_columns[center] = col
                break
    
    if not center_columns:
        raise NormalizationError("센터별 재고 컬럼을 찾을 수 없습니다.")
    
    # 데이터를 long format으로 변환
    melted_data = []
    
    for center, stock_col in center_columns.items():
        if stock_col in result.columns:
            center_data = result[["resource_code", "date", stock_col]].copy()
            center_data["center"] = center
            center_data["stock_qty"] = center_data[stock_col]
            center_data = center_data[["resource_code", "center", "date", "stock_qty"]]
            melted_data.append(center_data)
    
    if not melted_data:
        raise NormalizationError("변환할 데이터가 없습니다.")
    
    result = pd.concat(melted_data, ignore_index=True)
    
    # 데이터 타입 변환
    result["stock_qty"] = pd.to_numeric(result["stock_qty"], errors="coerce").fillna(0).astype(int)
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    
    # 날짜가 없는 행 제거
    result = result.dropna(subset=["date"])
    
    # 수량이 0인 행 제거
    result = result[result["stock_qty"] > 0]
    
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
        "resource_code": ["resource_code", "sku", "product_code", "item_code", "SKU", "Product Code"],
        "qty_ea": ["qty_ea", "quantity", "qty", "수량", "Quantity", "Qty"],
        "onboard_date": ["onboard_date", "departure_date", "ship_date", "출발일", "Onboard Date"],
        "arrival_date": ["arrival_date", "eta", "expected_arrival", "도착예정일", "Arrival Date"],
        "inbound_date": ["inbound_date", "received_date", "입고일", "Inbound Date"],
        "carrier_mode": ["carrier_mode", "transport_mode", "운송수단", "Carrier Mode"]
    }
    
    result = coalesce_columns(result, column_mapping)
    
    # 필수 컬럼 확인
    required_cols = ["resource_code", "qty_ea"]
    missing_cols = [col for col in required_cols if col not in result.columns]
    
    if missing_cols:
        # 자동 매핑 시도
        auto_mapping = {}
        for col in missing_cols:
            if col == "resource_code":
                sku_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["sku", "product", "item"])]
                if sku_candidates:
                    auto_mapping[col] = sku_candidates[0]
            elif col == "qty_ea":
                qty_candidates = [c for c in result.columns if any(keyword in c.lower() for keyword in ["qty", "quantity"])]
                if qty_candidates:
                    auto_mapping[col] = qty_candidates[0]
        
        if auto_mapping:
            for new_col, old_col in auto_mapping.items():
                result[new_col] = result[old_col]
                logging.info(f"자동 매핑: '{old_col}' → '{new_col}'")
        
        missing_cols = [col for col in required_cols if col not in result.columns]
        if missing_cols:
            available_cols = list(result.columns)
            raise NormalizationError(f"필수 컬럼이 없습니다: {missing_cols}\n사용 가능한 컬럼: {available_cols}")
    
    # 센터별 이동 컬럼 찾기
    center_mapping = {
        "태광KR": ["stock2"],
        "AMZUS": ["fba_available_stock"],
        "품고KR": ["poomgo_v2_available_stock"],
        "SBSPH": ["shopee_ph_available_stock"],
        "SBSSG": ["shopee_sg_available_stock"],
        "SBSMY": ["shopee_my_available_stock"],
        "AcrossBUS": ["acrossb_available_stock"],
        "어크로스비US": ["acrossb_available_stock"]
    }
    
    # 이동 데이터가 있는 센터 찾기
    available_centers = []
    for center, possible_cols in center_mapping.items():
        for col in possible_cols:
            if col in result.columns:
                available_centers.append(center)
                break
    
    if not available_centers:
        # 센터 정보가 없으면 기본값으로 처리
        result["from_center"] = "Unknown"
        result["to_center"] = "Unknown"
    else:
        # 첫 번째 센터를 기본값으로 설정
        result["from_center"] = available_centers[0]
        result["to_center"] = available_centers[0]
    
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
