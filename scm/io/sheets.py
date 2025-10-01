import pandas as pd
import streamlit as st
from typing import Optional, Dict, Any
import json

class GoogleSheetsLoadError(Exception):
    """Google Sheets 로딩 에러"""
    pass

def load_from_gsheet_api(
    gsheet_id: str,
    sheet_name: Optional[str] = None,
    credentials: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Google Sheets API를 통해 데이터를 로드합니다.
    
    Args:
        gsheet_id: Google Sheets ID
        sheet_name: 시트 이름 (None이면 첫 번째 시트)
        credentials: 서비스 계정 인증 정보
    
    Returns:
        DataFrame
    
    Raises:
        GoogleSheetsLoadError: 로딩 실패 시
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        if credentials is None:
            # Streamlit secrets에서 인증 정보 가져오기
            if 'gsheets' not in st.secrets:
                raise GoogleSheetsLoadError("Google Sheets 인증 정보가 설정되지 않았습니다.")
            credentials = st.secrets['gsheets']
        
        # 인증 설정
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(credentials, scopes=scopes)
        gc = gspread.authorize(creds)
        
        # 스프레드시트 열기
        spreadsheet = gc.open_by_key(gsheet_id)
        
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            worksheet = spreadsheet.sheet1
        
        # 데이터 가져오기
        records = worksheet.get_all_records()
        
        if not records:
            raise GoogleSheetsLoadError("시트에 데이터가 없습니다.")
        
        # DataFrame으로 변환
        df = pd.DataFrame(records)
        
        # 빈 행 제거
        df = df.dropna(how='all')
        
        if df.empty:
            raise GoogleSheetsLoadError("유효한 데이터가 없습니다.")
        
        return df
        
    except ImportError:
        raise GoogleSheetsLoadError(
            "Google Sheets 라이브러리가 설치되지 않았습니다. "
            "다음 명령어로 설치하세요: pip install gspread google-auth"
        )
    except Exception as e:
        raise GoogleSheetsLoadError(f"Google Sheets 로딩 중 오류가 발생했습니다: {str(e)}")

def load_snapshot_from_gsheet(
    gsheet_id: str,
    credentials: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Google Sheets에서 스냅샷 데이터를 로드합니다.
    
    Args:
        gsheet_id: Google Sheets ID
        credentials: 서비스 계정 인증 정보
    
    Returns:
        스냅샷 DataFrame
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        if credentials is None:
            if 'gsheets' not in st.secrets:
                raise GoogleSheetsLoadError("Google Sheets 인증 정보가 설정되지 않았습니다.")
            credentials = st.secrets['gsheets']
        
        # 인증 설정
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(credentials, scopes=scopes)
        gc = gspread.authorize(creds)
        
        # 스프레드시트 열기
        spreadsheet = gc.open_by_key(gsheet_id)
        
        # 스냅샷 시트 찾기
        worksheets = spreadsheet.worksheets()
        snapshot_sheet = None
        
        for ws in worksheets:
            if 'snapshot' in ws.title.lower() or '재고' in ws.title:
                snapshot_sheet = ws
                break
        
        if snapshot_sheet is None:
            snapshot_sheet = worksheets[0]  # 첫 번째 시트 사용
        
        # 데이터 가져오기
        records = snapshot_sheet.get_all_records()
        df = pd.DataFrame(records)
        df = df.dropna(how='all')
        
        if df.empty:
            raise GoogleSheetsLoadError("스냅샷 데이터가 없습니다.")
        
        return df
        
    except Exception as e:
        raise GoogleSheetsLoadError(f"스냅샷 데이터 로딩 중 오류가 발생했습니다: {str(e)}")

def load_moves_from_gsheet(
    gsheet_id: str,
    credentials: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Google Sheets에서 이동 데이터를 로드합니다.
    
    Args:
        gsheet_id: Google Sheets ID
        credentials: 서비스 계정 인증 정보
    
    Returns:
        이동 데이터 DataFrame
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        if credentials is None:
            if 'gsheets' not in st.secrets:
                raise GoogleSheetsLoadError("Google Sheets 인증 정보가 설정되지 않았습니다.")
            credentials = st.secrets['gsheets']
        
        # 인증 설정
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_info(credentials, scopes=scopes)
        gc = gspread.authorize(creds)
        
        # 스프레드시트 열기
        spreadsheet = gc.open_by_key(gsheet_id)
        
        # 이동 데이터 시트 찾기
        worksheets = spreadsheet.worksheets()
        moves_sheet = None
        
        for ws in worksheets:
            if 'move' in ws.title.lower() or '이동' in ws.title or 'transaction' in ws.title.lower():
                moves_sheet = ws
                break
        
        if moves_sheet is None:
            if len(worksheets) > 1:
                moves_sheet = worksheets[1]  # 두 번째 시트 사용
            else:
                moves_sheet = worksheets[0]  # 첫 번째 시트 사용
        
        # 데이터 가져오기
        records = moves_sheet.get_all_records()
        df = pd.DataFrame(records)
        df = df.dropna(how='all')
        
        if df.empty:
            raise GoogleSheetsLoadError("이동 데이터가 없습니다.")
        
        return df
        
    except Exception as e:
        raise GoogleSheetsLoadError(f"이동 데이터 로딩 중 오류가 발생했습니다: {str(e)}")
