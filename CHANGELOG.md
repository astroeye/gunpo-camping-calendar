// filepath: c:\workspace\chomakgol\CHANGELOG.md
# 변경 로그

이 프로젝트의 모든 중요한 변경사항이 이 파일에 문서화됩니다.

## [1.0.0] - 2025-09-12

### 추가됨
- 군포 캠핑장 예약 현황 달력 초기 버전
- Flask 백엔드 API 서버
- 반응형 웹 인터페이스
- 병렬 처리를 통한 성능 최적화
- 모바일 최적화 (갤럭시 S22 울트라 지원)
- 4가지 캠핑장 타입 지원 (고급, 일반, 자갈, 데크)
- 실시간 예약 현황 조회
- 월별 네비게이션
- 캐시 시스템 (5분)
- 진행률 표시
- 에러 처리 및 타임아웃 관리

### 기술적 특징
- ThreadPoolExecutor를 사용한 병렬 처리
- 세션 재사용으로 성능 향상
- 정규식 기반 빠른 HTML 파싱
- CORS 문제 해결
- 반응형 CSS 미디어 쿼리
- JavaScript ES6+ 사용

### API 엔드포인트
- `GET /api/camp-data/<date>` - 개별 날짜 조회
- `GET /api/camp-data-range` - 날짜 범위 조회
- `GET /api/camp-data-cached/<date>` - 캐시된 데이터 조회