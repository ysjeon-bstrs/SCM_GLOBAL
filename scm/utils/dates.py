import pandas as pd
from typing import Tuple, Optional
from datetime import datetime, timedelta

def today() -> pd.Timestamp:
    """오늘 날짜를 반환합니다."""
    return pd.Timestamp.today().normalize()

def normalize_date(date_input) -> pd.Timestamp:
    """
    날짜 입력을 정규화합니다.
    
    Args:
        date_input: 날짜 입력 (문자열, datetime, Timestamp 등)
    
    Returns:
        정규화된 Timestamp
    """
    if pd.isna(date_input):
        return today()
    
    if isinstance(date_input, str):
        try:
            return pd.to_datetime(date_input).normalize()
        except:
            return today()
    
    if isinstance(date_input, datetime):
        return pd.Timestamp(date_input).normalize()
    
    if isinstance(date_input, pd.Timestamp):
        return date_input.normalize()
    
    return today()

def get_date_range(
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    days_back: int = 30,
    days_forward: int = 30
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    날짜 범위를 계산합니다.
    
    Args:
        start_date: 시작 날짜 (None이면 days_back일 전)
        end_date: 종료 날짜 (None이면 days_forward일 후)
        days_back: 과거 일수
        days_forward: 미래 일수
    
    Returns:
        (시작날짜, 종료날짜) 튜플
    """
    today_norm = today()
    
    if start_date is None:
        start_date = today_norm - pd.Timedelta(days=days_back)
    else:
        start_date = normalize_date(start_date)
    
    if end_date is None:
        end_date = today_norm + pd.Timedelta(days=days_forward)
    else:
        end_date = normalize_date(end_date)
    
    return start_date, end_date

def clamp_date_range(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    min_date: Optional[pd.Timestamp] = None,
    max_date: Optional[pd.Timestamp] = None
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    날짜 범위를 제한합니다.
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        min_date: 최소 날짜
        max_date: 최대 날짜
    
    Returns:
        제한된 (시작날짜, 종료날짜) 튜플
    """
    if min_date is not None:
        start_date = max(start_date, min_date)
    
    if max_date is not None:
        end_date = min(end_date, max_date)
    
    # 시작날짜가 종료날짜보다 늦으면 조정
    if start_date > end_date:
        start_date = end_date - pd.Timedelta(days=1)
    
    return start_date, end_date

def get_business_days(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp
) -> int:
    """
    두 날짜 사이의 영업일 수를 계산합니다.
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
    
    Returns:
        영업일 수
    """
    # 간단한 구현 (주말 제외)
    date_range = pd.date_range(start_date, end_date, freq='D')
    business_days = date_range[date_range.weekday < 5]  # 월-금만
    return len(business_days)

def add_business_days(
    date: pd.Timestamp,
    days: int
) -> pd.Timestamp:
    """
    영업일을 추가합니다.
    
    Args:
        date: 기준 날짜
        days: 추가할 영업일 수
    
    Returns:
        계산된 날짜
    """
    current_date = date
    added_days = 0
    
    while added_days < days:
        current_date += pd.Timedelta(days=1)
        if current_date.weekday() < 5:  # 월-금
            added_days += 1
    
    return current_date

def format_date_range(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    format_str: str = "%Y-%m-%d"
) -> str:
    """
    날짜 범위를 문자열로 포맷합니다.
    
    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        format_str: 날짜 포맷 문자열
    
    Returns:
        포맷된 날짜 범위 문자열
    """
    start_str = start_date.strftime(format_str)
    end_str = end_date.strftime(format_str)
    return f"{start_str} ~ {end_str}"

def get_quarter_dates(year: int, quarter: int) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """
    분기 날짜 범위를 계산합니다.
    
    Args:
        year: 연도
        quarter: 분기 (1-4)
    
    Returns:
        (분기 시작일, 분기 종료일) 튜플
    """
    quarter_starts = {
        1: (1, 1),
        2: (4, 1),
        3: (7, 1),
        4: (10, 1)
    }
    
    if quarter not in quarter_starts:
        raise ValueError("분기는 1-4 사이여야 합니다.")
    
    month, day = quarter_starts[quarter]
    start_date = pd.Timestamp(year, month, day)
    
    if quarter == 4:
        end_date = pd.Timestamp(year + 1, 1, 1) - pd.Timedelta(days=1)
    else:
        next_quarter = quarter + 1
        next_month, next_day = quarter_starts[next_quarter]
        end_date = pd.Timestamp(year, next_month, next_day) - pd.Timedelta(days=1)
    
    return start_date, end_date
