# SCM 재고 흐름 대시보드

글로벌 공급망 관리(SCM)를 위한 재고 흐름 시각화 대시보드입니다.

## 🚀 주요 기능

- **실시간 재고 추적**: 센터별 재고 현황 및 변화 추이
- **예측 분석**: 소진 예측 및 수요 예측
- **이동 추적**: In-Transit, WIP 상태 추적
- **다중 데이터 소스**: Excel, Google Sheets 지원
- **인터랙티브 차트**: Plotly 기반 계단식 차트

## 📊 지원하는 센터

- 태광KR
- AMZUS (Amazon US)
- 품고KR
- Shopee (PH, SG, MY)
- AcrossBUS

## 🛠️ 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 설정 파일 생성
```bash
cp secrets.toml.example secrets.toml
```

### 3. Google Sheets API 설정 (선택사항)
`secrets.toml`에 Google Sheets 서비스 계정 정보를 추가하세요.

### 4. 실행
```bash
# 모듈화된 버전 (권장)
streamlit run app.py

# 또는 기존 단일 파일 버전
streamlit run streamlit_scm_step_v4.py
```

## 📁 프로젝트 구조

```
├── app.py                          # 모듈화된 Streamlit 앱
├── streamlit_scm_step_v4.py        # 기존 단일 파일 앱
├── requirements.txt                # 의존성
├── secrets.toml.example           # 설정 예시
├── scm/                           # 핵심 로직 패키지
│   ├── config.py                  # 설정
│   ├── domain/                    # 비즈니스 로직
│   │   ├── timeline.py            # 타임라인 계산
│   │   ├── forecast.py            # 예측 로직
│   │   └── cost.py                # 비용 계산
│   ├── io/                        # 데이터 소스
│   │   ├── excel.py               # Excel 로딩
│   │   └── sheets.py              # Google Sheets 로딩
│   ├── transform/                 # 데이터 정규화
│   │   ├── normalize.py           # 정규화 함수
│   │   └── wip.py                 # WIP 처리
│   └── utils/                     # 유틸리티
└── tests/                         # 테스트
```

## 🔧 주요 개선사항

- **모듈화**: 단일 파일을 기능별 모듈로 분리
- **성능 최적화**: 벡터화된 연산으로 O(N²) → O(N log N)
- **에러 처리**: 커스텀 예외 및 명확한 에러 메시지
- **설정 중앙화**: 모든 설정을 config.py에서 관리
- **타입 힌트**: 코드 가독성 및 유지보수성 향상

## 📈 사용법

1. **데이터 로드**: Excel 파일 업로드 또는 Google Sheets 연결
2. **센터 선택**: 분석할 센터 선택
3. **SKU 선택**: 분석할 상품 선택
4. **기간 설정**: 분석 기간 및 미래 전망 일수 설정
5. **옵션 설정**: 예측, 이벤트 등 추가 옵션 설정

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 이슈를 생성해 주세요.

