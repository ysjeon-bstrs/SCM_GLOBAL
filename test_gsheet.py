import requests
import pandas as pd
from urllib.parse import quote

GSHEET_ID = "1RYjKW2UDJ2kWJLAqQH26eqx2-r9Xb0_qE_hfwu9WIj8"

def test_gsheet_csv():
    """Google Sheets CSV 다운로드 테스트"""
    try:
        # CSV 다운로드 URL 생성
        sheet_name = "snap_정제"
        url = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/gviz/tq?tqx=out:csv&sheet={quote(sheet_name)}"
        
        print(f"CSV 다운로드 URL: {url}")
        print("Google Sheets CSV 다운로드 중...")
        
        # 여러 인코딩 시도
        for encoding in ['utf-8', 'cp949', 'latin-1']:
            try:
                print(f"인코딩 {encoding} 시도 중...")
                response = requests.get(url)
                response.raise_for_status()
                
                # CSV 데이터를 DataFrame으로 읽기
                from io import StringIO
                df = pd.read_csv(StringIO(response.text), encoding=encoding)
                
                if not df.empty:
                    print(f"성공! {len(df)}개 행을 찾았습니다.")
                    print(f"컬럼: {list(df.columns)}")
                    print(f"첫 번째 행: {df.iloc[0].to_dict()}")
                    return df
                else:
                    print(f"인코딩 {encoding}: 빈 데이터")
                    
            except UnicodeDecodeError:
                print(f"인코딩 {encoding}: 실패")
                continue
            except Exception as e:
                print(f"인코딩 {encoding}: 오류 - {e}")
                continue
        
        print("모든 인코딩 시도 실패")
        return None
        
    except Exception as e:
        print(f"오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_public_access():
    """공개 접근 테스트"""
    try:
        # 공개 시트인지 확인
        public_url = f"https://docs.google.com/spreadsheets/d/{GSHEET_ID}/edit"
        print(f"공개 URL 테스트: {public_url}")
        
        response = requests.get(public_url)
        print(f"공개 URL 응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            print("시트가 공개되어 있습니다.")
        else:
            print("시트가 비공개이거나 접근할 수 없습니다.")
            
    except Exception as e:
        print(f"공개 접근 테스트 오류: {e}")

if __name__ == "__main__":
    print("=== Google Sheets 테스트 ===")
    test_public_access()
    print("\n=== CSV 다운로드 테스트 ===")
    df = test_gsheet_csv()
    if df is not None:
        print(f"\n데이터프레임 정보:")
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
