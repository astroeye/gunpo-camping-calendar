# 군포 캠핑장 예약 현황 달력

군포시 캠핑장의 실시간 예약 현황을 달력 형태로 보여주는 웹 애플리케이션입니다.

## 🌟 주요 기능

- **실시간 예약 현황**: 군포시 캠핑장 API를 통한 실시간 데이터
- **달력 형태 표시**: 월별 예약 현황을 한눈에 확인
- **4가지 캠핑장 타입**: 고급, 일반, 자갈, 데크 구분 표시
- **모바일 최적화**: 갤럭시 S22 울트라 등 모바일 디바이스 지원
- **빠른 로딩**: 병렬 처리를 통한 성능 최적화

## 📱 스크린샷

### 데스크톱
![Desktop View](screenshots/desktop.png)

### 모바일
![Mobile View](screenshots/mobile.png)

## 🚀 시작하기

### 요구사항
- Python 3.7+
- pip

### 설치 및 실행

1. **저장소 클론**
```bash
git clone https://github.com/yourusername/gunpo-camping-calendar.git
cd gunpo-camping-calendar
```

2. **가상환경 생성 및 활성화**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **패키지 설치**
```bash
pip install -r requirements.txt
```

4. **애플리케이션 실행**
```bash
python app.py
```

5. **브라우저에서 접속**
```
http://localhost:5000
```

## 📋 API 엔드포인트

### 개별 날짜 조회
```
GET /api/camp-data/<date>
```
- 특정 날짜의 캠핑장 예약 현황 조회
- 예: `/api/camp-data/2025-10-01`

### 날짜 범위 조회
```
GET /api/camp-data-range?start_date=<start>&end_date=<end>
```
- 날짜 범위의 캠핑장 예약 현황 조회
- 예: `/api/camp-data-range?start_date=2025-10-01&end_date=2025-10-31`

### 캐시된 데이터 조회
```
GET /api/camp-data-cached/<date>
```
- 5분간 캐시된 데이터 조회 (서버 부담 감소)

## 🏗️ 프로젝트 구조

```
gunpo-camping-calendar/
├── app.py                 # Flask 메인 애플리케이션
├── requirements.txt       # Python 패키지 목록
├── README.md             # 프로젝트 설명서
├── .gitignore           # Git 무시 파일 목록
├── templates/           # HTML 템플릿
│   └── calendar.html    # 메인 달력 페이지
├── static/             # 정적 파일
│   ├── css/
│   │   └── style.css   # 스타일시트
│   └── js/
│       └── main.js     # JavaScript
└── screenshots/        # 스크린샷 이미지
```

## 🛠️ 기술 스택

### 백엔드
- **Flask**: 웹 프레임워크
- **Requests**: HTTP 클라이언트
- **BeautifulSoup4**: HTML 파싱
- **Flask-CORS**: CORS 처리
- **ThreadPoolExecutor**: 병렬 처리

### 프론트엔드
- **HTML5**: 마크업
- **CSS3**: 반응형 스타일링
- **JavaScript (ES6+)**: 클라이언트 로직
- **Fetch API**: 비동기 데이터 통신

## 🔧 주요 특징

### 성능 최적화
- **병렬 처리**: ThreadPoolExecutor를 사용한 동시 요청 처리
- **세션 재사용**: HTTP 연결 재사용으로 속도 향상
- **정규식 파싱**: BeautifulSoup보다 빠른 데이터 추출
- **배치 처리**: 서버 부담을 줄이는 배치 단위 요청

### 반응형 디자인
- **모바일 퍼스트**: 모바일 환경 우선 설계
- **미디어 쿼리**: 화면 크기별 최적화
- **터치 친화적**: 모바일 터치 인터페이스 고려
- **고해상도 지원**: 레티나 디스플레이 최적화

### 사용자 경험
- **실시간 피드백**: 로딩 상태 및 진행률 표시
- **에러 처리**: 네트워크 오류 및 타임아웃 처리
- **캐시 시스템**: 빠른 응답을 위한 5분 캐시
- **직관적 UI**: 색상으로 구분된 예약 상태

## 📊 API 응답 형식

### 개별 날짜 응답
```json
{
    "success": true,
    "date": "2025-10-01",
    "data": {
        "고급": 2,
        "일반": 1,
        "자갈": 5,
        "데크": 3
    },
    "processing_time": 1.23
}
```

### 날짜 범위 응답
```json
{
    "success": true,
    "data": {
        "2025-10-01": {
            "고급": 2,
            "일반": 1,
            "자갈": 5,
            "데크": 3
        },
        "2025-10-02": {
            "고급": 0,
            "일반": 2,
            "자갈": 4,
            "데크": 1
        }
    },
    "processing_time": 15.67
}
```

## 🎨 색상 가이드

- **🔵 파란색**: 예약 가능 (available)
- **🔴 빨간색**: 예약 불가 (unavailable)
- **🟠 주황색**: 로딩 중 (loading)
- **⚫ 회색**: 오류 발생 (error)

## 🤝 기여하기

1. Fork 프로젝트
2. Feature 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 Push (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🔗 관련 링크

- [군포시 캠핑장 공식 사이트](https://www.gunpouc.or.kr/)
- [Flask 공식 문서](https://flask.palletsprojects.com/)
- [Bootstrap 문서](https://getbootstrap.com/)

## 📞 문의사항

프로젝트에 대한 질문이나 제안사항이 있으시면 Issue를 생성해 주세요.

---

**Made with ❤️ by [Your Name]**