import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# 페이지 설정
st.set_page_config(
    page_title="SCM Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 SCM 재고 흐름 대시보드")
st.caption("글로벌 공급망 관리를 위한 재고 흐름 시각화")

# 사이드바 설정
st.sidebar.header("⚙️ 설정")

# 데이터 소스 선택
data_source = st.sidebar.radio(
    "데이터 소스",
    ["Excel 파일", "Google Sheets"],
    help="데이터를 불러올 소스를 선택하세요"
)

# Excel 파일 업로드
if data_source == "Excel 파일":
    uploaded_file = st.sidebar.file_uploader(
        "Excel 파일 업로드",
        type=['xlsx', 'xls'],
        help="스냅샷과 이동 데이터가 포함된 Excel 파일을 업로드하세요"
    )
    
    if uploaded_file is not None:
        try:
            # 간단한 데이터 로딩
            st.sidebar.success("Excel 파일이 성공적으로 로드되었습니다!")
            st.info("데이터 로딩 기능은 개발 중입니다. 기존 streamlit_scm_step_v4.py를 사용해주세요.")
        except Exception as e:
            st.sidebar.error(f"Excel 파일 로딩 중 오류가 발생했습니다: {str(e)}")
            st.stop()
    else:
        st.info("Excel 파일을 업로드하세요.")
        st.stop()

# Google Sheets 연결
elif data_source == "Google Sheets":
    gsheet_id = st.sidebar.text_input(
        "Google Sheets ID",
        value="1RYjKW2UDJ2kWJLAqQH26eqx2-r9Xb0_qE_hfwu9WIj8",
        help="Google Sheets의 ID를 입력하세요"
    )
    
    if st.sidebar.button("Google Sheets에서 데이터 로드"):
        try:
            st.sidebar.success("Google Sheets에서 데이터가 성공적으로 로드되었습니다!")
            st.info("데이터 로딩 기능은 개발 중입니다. 기존 streamlit_scm_step_v4.py를 사용해주세요.")
        except Exception as e:
            st.sidebar.error(f"Google Sheets 로딩 중 오류가 발생했습니다: {str(e)}")
            st.stop()
    else:
        st.info("Google Sheets에서 데이터를 로드하세요.")
        st.stop()

# 메인 콘텐츠
st.header("📊 SCM 대시보드")

st.info("""
## 🚀 SCM 재고 흐름 대시보드

이 앱은 글로벌 공급망 관리를 위한 재고 흐름 시각화 도구입니다.

### 📁 프로젝트 구조:
- `streamlit_scm_step_v4.py` - 메인 앱 (완전한 기능)
- `scm/` - 모듈화된 패키지
  - `config.py` - 설정 관리
  - `domain/` - 핵심 비즈니스 로직
  - `io/` - 데이터 소스
  - `transform/` - 데이터 정규화
  - `ui/` - UI 컴포넌트
  - `utils/` - 유틸리티

### 🔧 현재 상태:
- ✅ 모듈화 구조 완성
- ✅ GitHub에 업로드 완료
- 🔄 웹 배포 중...

### 📖 사용법:
현재는 로컬에서 `streamlit_scm_step_v4.py`를 사용하시거나, 
모듈화된 버전의 완전한 기능을 위해 로컬에서 `app_modular.py`를 실행해주세요.

```bash
streamlit run streamlit_scm_step_v4.py
```

또는

```bash
streamlit run app_modular.py
```
""")

st.header("📈 주요 기능")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("현재 재고", "0", "데이터 로딩 필요")
    
with col2:
    st.metric("이동중 재고", "0", "데이터 로딩 필요")
    
with col3:
    st.metric("WIP 재고", "0", "데이터 로딩 필요")

st.header("🔗 관련 링크")

st.markdown("""
- **GitHub 리포지토리**: https://github.com/ysjeon-bstrs/scm
- **로컬 실행**: `streamlit run streamlit_scm_step_v4.py`
- **모듈화 버전**: `streamlit run app_modular.py`
""")

st.header("📊 데이터 구조")

st.markdown("""
### 스냅샷 데이터 (Wide Format):
- `resource_code` - SKU 코드
- `date` - 스냅샷 날짜
- `fba_available_stock` - AMZUS 재고
- `poomgo_v2_available_stock` - 품고KR 재고
- `shopee_ph_available_stock` - SBSPH 재고
- `shopee_sg_available_stock` - SBSSG 재고
- `shopee_my_available_stock` - SBSMY 재고
- `acrossb_available_stock` - AcrossBUS 재고

### 이동 데이터 (한글 컬럼):
- `품번` - SKU 코드
- `수량` - 이동 수량
- `출발창고` - 출발 센터
- `목적창고` - 도착 센터
- `입고예정일` - 입고 예정일
- `운송사` - 운송 수단
""")
