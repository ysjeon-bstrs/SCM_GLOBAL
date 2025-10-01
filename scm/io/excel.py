import pandas as pd
import streamlit as st
from typing import Optional, Dict, Any

class ExcelLoadError(Exception):
    """Excel 파일 로딩 에러"""
    pass

def load_from_excel(uploaded_file) -> Dict[str, pd.DataFrame]:
    """
    Excel 파일에서 데이터를 로드합니다.
    
    Args:
        uploaded_file: Streamlit 업로드된 파일 객체
    
    Returns:
        시트별 DataFrame 딕셔너리
    
    Raises:
        ExcelLoadError: 파일 로딩 실패 시
    """
    try:
        if uploaded_file is None:
            raise ExcelLoadError("업로드된 파일이 없습니다.")
        
        # Excel 파일 읽기
        excel_data = pd.read_excel(uploaded_file, sheet_name=None, engine='openpyxl')
        
        if not excel_data:
            raise ExcelLoadError("Excel 파일에 시트가 없습니다.")
        
        # 데이터 정리
        cleaned_data = {}
        for sheet_name, df in excel_data.items():
            if df.empty:
                continue
            
            # 컬럼명 정리
            df.columns = df.columns.astype(str)
            df = df.dropna(how='all')  # 빈 행 제거
            
            if not df.empty:
                cleaned_data[sheet_name] = df
        
        if not cleaned_data:
            raise ExcelLoadError("유효한 데이터가 없습니다.")
        
        return cleaned_data
        
    except Exception as e:
        raise ExcelLoadError(f"Excel 파일 로딩 중 오류가 발생했습니다: {str(e)}")

def load_snapshot_from_excel(uploaded_file) -> pd.DataFrame:
    """
    Excel 파일에서 스냅샷 데이터를 로드합니다.
    
    Args:
        uploaded_file: Streamlit 업로드된 파일 객체
    
    Returns:
        스냅샷 DataFrame
    """
    try:
        excel_data = load_from_excel(uploaded_file)
        
        # 스냅샷 시트 찾기
        snapshot_sheets = [name for name in excel_data.keys() 
                          if 'snapshot' in name.lower() or '재고' in name]
        
        if not snapshot_sheets:
            # 첫 번째 시트 사용
            sheet_name = list(excel_data.keys())[0]
        else:
            sheet_name = snapshot_sheets[0]
        
        return excel_data[sheet_name]
        
    except Exception as e:
        raise ExcelLoadError(f"스냅샷 데이터 로딩 중 오류가 발생했습니다: {str(e)}")

def load_moves_from_excel(uploaded_file) -> pd.DataFrame:
    """
    Excel 파일에서 이동 데이터를 로드합니다.
    
    Args:
        uploaded_file: Streamlit 업로드된 파일 객체
    
    Returns:
        이동 데이터 DataFrame
    """
    try:
        excel_data = load_from_excel(uploaded_file)
        
        # 이동 데이터 시트 찾기
        moves_sheets = [name for name in excel_data.keys() 
                       if 'move' in name.lower() or '이동' in name or 'transaction' in name.lower()]
        
        if not moves_sheets:
            # 두 번째 시트 사용 (첫 번째는 스냅샷으로 가정)
            if len(excel_data) > 1:
                sheet_name = list(excel_data.keys())[1]
            else:
                sheet_name = list(excel_data.keys())[0]
        else:
            sheet_name = moves_sheets[0]
        
        return excel_data[sheet_name]
        
    except Exception as e:
        raise ExcelLoadError(f"이동 데이터 로딩 중 오류가 발생했습니다: {str(e)}")
