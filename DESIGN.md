# SANZERO 디자인 문서

### 디자인 가이드라인
- 반응형 완벽 지원 (puppeteer MCP 로 반응형 디자인도 문제가 없는지 확인)
- https://tx.shadcn.com/ 스타일로 전체 웹페이지에 일관된 디자인 적용

## XML 디자인 파일 개요

- SANZERO 서비스의 모든 페이지 구조를 XML 형식으로 정의합니다.
- 각 XML 파일은 페이지의 구조와 요소를 명확하게 표현하여 구현 시 참조할 수 있도록 합니다.

## XML 파일 목록

### 1. 공통 컴포넌트
- **@header.xml**: 공통 헤더 (SANZERO 네비게이션, 사용자 메뉴)
- **@footer.xml**: 공통 푸터

### 2. 메인 대시보드
- **@dashboard.xml**: SANZERO 메인 대시보드

### 3. 산재 보상 서비스
- **@compensation-apply.xml**: 보상금 신청 페이지
- **@compensation-status.xml**: 신청 현황 조회 페이지
- **@compensation-calculate.xml**: 보상금 계산 페이지

### 4. AI 분석 서비스
- **@analysis-main.xml**: AI 분석 메인 페이지
- **@analysis-precedent.xml**: 판례 분석 페이지
- **@analysis-disability.xml**: AI 장해등급 예측 페이지 (준비 중)

### 5. 노무사 서비스
- **@lawyers-search.xml**: 노무사 검색/매칭 페이지
- **@lawyers-profile.xml**: 노무사 프로필 페이지
- **@lawyers-booking.xml**: 상담 예약 페이지

### 6. 인증 및 사용자 관리
- **@auth-login.xml**: 로그인 페이지
- **@auth-signup.xml**: 회원가입 페이지
- **@auth-profile.xml**: 프로필 관리 페이지

### 7. 관리자
- **@admin-dashboard.xml**: 관리자 대시보드
- **@admin-users.xml**: 사용자 관리 페이지
- **@admin-applications.xml**: 보상금 승인/거부 페이지



