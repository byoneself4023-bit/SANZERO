# SANZERO 개발자 가이드

> **AI 기반 산업재해 보상 서비스 플랫폼 - 팀 개발 가이드**

## 📚 관련 문서
- **@README.md**: 프로젝트 개요 및 빠른 시작
- **@ARCHITECTURE.md**: 시스템 구조 및 기술 명세
- **@PROGRESS.md**: 개발 진행 상황 및 완료 기능
- **@TESTPLAN.md**: 테스트 계획 및 케이스
- **@NOTE.md**: 개발 시 주의사항

---

## 🎯 **6개 핵심 기능별 코드 위치 매핑**

> **"이 기능을 수정하려면 어느 파일을 봐야 하나?"** 에 대한 빠른 답변

### 1. 📋 **산재 보상 신청/관리** (보상금 계산, CRUD, 상태 추적)

#### 🛤️ **API 라우터**
- **`app/routers/compensation.py`** - 메인 라우터
  - 주요 엔드포인트: `/compensation/calculator`, `/compensation/status`

#### 💼 **비즈니스 로직**
- **`app/services/compensation_service.py`** - 신청서 CRUD 관리
- **`app/services/compensation_calculator_service.py`** - 보상금 계산 엔진

#### 🎨 **템플릿**
- **`app/templates/pages/compensation/calculator.html`** - 보상금 계산기 (메인)
- **`app/templates/components/calculation_result.html`** - 계산 결과 컴포넌트

---

### 2. 👨‍💼 **노무사 서비스** (AI 매칭, 검색, 상담 예약)

#### 🛤️ **API 라우터**
- **`app/routers/lawyers.py`** - 메인 라우터
  - 주요 엔드포인트: `/lawyers/search`, `/lawyers/{id}`, `/lawyers/booking`

#### 💼 **비즈니스 로직**
- **`app/services/lawyer_service.py`** - 노무사 검색, 매칭, 상담 예약 관리
  - AI 매칭 알고리즘 구현
  - 상담 예약 시스템

#### 🎨 **템플릿**
- **`app/templates/pages/lawyers/search.html`** - 노무사 검색/매칭
- **`app/templates/pages/lawyers/profile.html`** - 노무사 프로필
- **`app/templates/pages/lawyers/booking.html`** - 상담 예약

---

### 3. 🤖 **AI 판례 분석** (RAG 기반 유사 판례 검색 및 분석)

#### 🛤️ **API 라우터**
- **`app/routers/analysis.py`** - 메인 라우터
  - 주요 엔드포인트: `/analysis/precedent`, `/analysis/history`

#### 💼 **AI 서비스 (핵심 구현)**
- **`app/services/analysis_service.py`** - 메인 AI 분석 서비스
- **`app/services/precedent_search_service.py`** - 판례 검색 서비스
- **`app/services/integrated_bundle_service.py`** - 통합 번들 서비스
- **`app/services/fast_search_pipeline.py`** - 빠른 검색 파이프라인
- **`app/services/simple_search_service.py`** - 간단 검색 서비스

#### 🎨 **템플릿**
- **`app/templates/pages/analysis/precedent.html`** - 판례 분석 메인
- **`app/templates/pages/analysis/results*.html`** - 분석 결과 페이지들
- **`app/templates/pages/analysis/history.html`** - 분석 이력

---

### 4. 🎯 **AI 장해등급 예측** (v3 통합 파이프라인 구현 완료)

#### 🛤️ **API 라우터**
- **`app/routers/analysis.py`** (판례 분석과 통합)
  - 주요 엔드포인트: `/analysis/disability`, `/analysis/api/predict-grade`

#### 💼 **예측 시스템**
- **3단계 예측 파이프라인**: analysis.py 라우터 내부에 구현
  1. 정확 매칭 (100% 정확도)
  2. BERT 유사도 (72%+ 정확도)
  3. DNN 모델 예측

#### 🎨 **템플릿**
- **`app/templates/pages/analysis/disability.html`** - 장해등급 예측 메인
- **`app/templates/pages/analysis/disability_simple.html`** - 빠른 예측
- **`app/templates/pages/analysis/disability_results*.html`** - 예측 결과

---

### 5. 🔐 **사용자 인증 시스템**

#### 🛤️ **API 라우터**
- **`app/routers/auth.py`** - 인증 라우터
  - 주요 엔드포인트: `/auth/login`, `/auth/signup`, `/auth/logout`

#### 💼 **보안 시스템**
- **`app/utils/security.py`** - 보안 유틸리티
  - JWT 토큰 관리
  - CSRF 보호
  - 권한 검증 미들웨어
- **`app/utils/database.py`** - Supabase 연동

#### 🎨 **템플릿**
- **`app/templates/pages/auth/login.html`** - 로그인
- **`app/templates/pages/auth/signup.html`** - 회원가입
- **`app/templates/pages/auth/profile.html`** - 프로필 관리

---

### 6. 📊 **메인 대시보드** (통합 대시보드)

#### 🛤️ **메인 애플리케이션**
- **`app/main.py`** - FastAPI 메인 애플리케이션
  - 라우트: `/` - testuser 기반 통합 대시보드

#### 🎨 **템플릿**
- **`app/templates/pages/dashboard.html`** - 메인 대시보드
- **`app/templates/base.html`** - 기본 레이아웃
- **`app/templates/components/header.html`** - 공통 헤더
- **`app/templates/components/footer.html`** - 공통 푸터

---

## 📁 **디렉토리 구조 및 역할**

```
app/
├── main.py                     # 🎯 FastAPI 메인 애플리케이션 & 라우터 등록
├── routers/                    # 🛤️ API 라우팅 레이어
│   ├── auth.py                # 🔐 사용자 인증 (로그인/회원가입)
│   ├── compensation.py        # 📋 보상금 신청 및 계산
│   ├── lawyers.py             # 👨‍💼 노무사 서비스 (검색/매칭/예약)
│   └── analysis.py            # 🤖 AI 분석 (판례 + 장해등급 예측)
├── services/                   # 💼 비즈니스 로직 레이어
│   ├── compensation_*.py      # 📋 보상금 관련 서비스들
│   ├── lawyer_service.py      # 👨‍💼 노무사 서비스 로직
│   ├── analysis_service.py    # 🤖 AI 분석 메인 서비스
│   ├── *_search_*.py          # 🔍 각종 검색 서비스들
│   └── integrated_bundle_service.py # 🎯 통합 서비스
├── models/                     # 📊 데이터 모델
│   └── schemas.py             # Pydantic 스키마 정의
├── templates/                  # 🎨 Jinja2 HTML 템플릿
│   ├── base.html              # 📄 기본 레이아웃
│   ├── components/            # 🧩 재사용 컴포넌트
│   └── pages/                 # 📑 기능별 페이지들
├── utils/                      # 🔧 공통 유틸리티
│   ├── security.py            # 🔐 보안 (JWT, CSRF)
│   ├── database.py            # 🗄️ Supabase 연동
│   └── config.py              # ⚙️ 환경설정
└── static/                     # 📁 정적 파일 (CSS/JS/이미지)
```

---

## 🎯 **신규 팀원 우선 학습 가이드**

### 🔥 **1단계: 필수 이해 파일** (첫 주)
1. **`app/main.py`** - 전체 애플리케이션 구조 파악
2. **`app/utils/security.py`** - 인증 및 보안 시스템 이해
3. **`app/utils/database.py`** - Supabase 연동 방식 파악
4. **`app/models/schemas.py`** - 데이터 구조 이해

### ⚡ **2단계: 기능별 핵심 파일** (둘째 주)
- **보상금 시스템**: `app/services/compensation_service.py`
- **노무사 서비스**: `app/services/lawyer_service.py`
- **AI 분석**: `app/services/analysis_service.py`

### 📝 **3단계: 템플릿 구조** (셋째 주)
- **기본 레이아웃**: `app/templates/base.html`
- **공통 컴포넌트**: `app/templates/components/`
- **페이지별 템플릿**: `app/templates/pages/[기능명]/`

---

## 🛠️ **새로운 기능 추가 가이드**

### **1. 새로운 API 기능 추가**
```python
# 1. 라우터 생성/수정: app/routers/[기능명].py
# 2. 서비스 로직: app/services/[기능명]_service.py
# 3. 데이터 스키마: app/models/schemas.py에 추가
# 4. main.py에 라우터 등록
```

### **2. 새로운 UI 페이지 추가**
```html
<!-- 1. 템플릿 작성: app/templates/pages/[기능명]/[페이지명].html -->
<!-- 2. 필요시 컴포넌트: app/templates/components/[컴포넌트명].html -->
<!-- 3. base.html 상속 구조 활용 -->
```

### **3. 공통 유틸리티 추가**
```python
# app/utils/[유틸리티명].py 생성
# 기존 security.py, database.py 패턴 참조
```

---

## 🔧 **개발 환경 설정**

### **빠른 시작**
```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일 편집 (Supabase, OpenAI API 키 등)

# 2. Docker 실행
docker compose up --build -d

# 3. 접속 확인
# http://localhost (Nginx 프록시)
# http://localhost:8000 (FastAPI 직접)
```

### **테스트 계정**
```
일반사용자: testuser@example.com / test123456!
노무사: lawyer@example.com / lawyer123456!
```

### **주요 의존성**
- **FastAPI**: 웹 프레임워크
- **Supabase**: 데이터베이스 & 인증
- **HTMX**: 동적 UI 업데이트
- **Tailwind CSS**: 스타일링
- **OpenAI/Anthropic API**: AI 분석

---

## 📊 **기능 완성도 현황**

| 기능 | 라우터 | 서비스 | 템플릿 | 완성도 | 상태 |
|------|--------|--------|--------|--------|------|
| 📋 산재 보상 신청/관리 | ✅ | ✅ | ✅ | 100% | 🟢 Production |
| 👨‍💼 노무사 서비스 | ✅ | ✅ | ✅ | 100% | 🟢 Production |
| 🤖 AI 판례 분석 | ✅ | ✅ | ✅ | 100% | 🟢 Production |
| 🎯 AI 장해등급 예측 | ✅ | ✅ | ✅ | 100% | 🟢 Production |
| 🔐 사용자 인증 | ✅ | ✅ | ✅ | 100% | 🟢 Production |
| 📊 메인 대시보드 | ✅ | ✅ | ✅ | 100% | 🟢 Production |

**🎯 전체 완성도: 100%** - 모든 핵심 기능 프로덕션 준비 완료

---

## 🚀 **주요 API 엔드포인트**

### **인증 시스템**
```
POST /auth/login          # 로그인
POST /auth/signup         # 회원가입
POST /auth/logout         # 로그아웃
GET  /auth/profile        # 프로필 조회
```

### **보상금 서비스**
```
GET  /compensation/calculator    # 보상금 계산기
POST /compensation/api/calculate # 보상금 계산 API
GET  /compensation/status        # 신청 현황
```

### **노무사 서비스**
```
GET  /lawyers/search            # 노무사 검색/매칭
GET  /lawyers/{id}              # 노무사 프로필
POST /lawyers/booking           # 상담 예약
```

### **AI 분석**
```
GET  /analysis/precedent        # 판례 분석
POST /analysis/api/search       # 판례 검색 API
GET  /analysis/disability       # 장해등급 예측
POST /analysis/api/predict-grade # 장해등급 예측 API
```

---

## 💡 **개발 팁**

### **코딩 스타일**
- **라우터**: RESTful API 설계 원칙 준수
- **서비스**: 단일 책임 원칙, 비즈니스 로직 분리
- **템플릿**: Jinja2 + HTMX + Tailwind CSS 조합
- **보안**: 모든 입력 데이터 검증, CSRF 토큰 사용

### **디버깅**
- **FastAPI 자동 문서**: `http://localhost:8000/docs`
- **로그**: `app/utils/logging_config.py` 설정
- **개발자 도구**: 브라우저 Network 탭으로 HTMX 요청 확인

### **성능 최적화**
- **비동기 처리**: async/await 사용
- **데이터베이스**: Supabase RPC 함수 활용
- **캐싱**: 필요시 `app/utils/cache.py` 활용

---

## 🤝 **팀 협업 가이드**

### **Git 워크플로우**
```bash
# 1. 기능 브랜치 생성
git checkout -b feature/새기능명

# 2. 개발 및 테스트
# 3. 커밋 및 푸시
git commit -m "Add: 새기능 설명"
git push origin feature/새기능명

# 4. Pull Request 생성
```

### **코드 리뷰 체크포인트**
- [ ] 보안: XSS, CSRF 방어 확인
- [ ] 성능: 비동기 처리, DB 쿼리 최적화
- [ ] 테스트: 주요 기능 테스트 케이스 포함
- [ ] 문서: API 변경사항 문서 업데이트

### **배포**
- Docker Compose 기반 배포
- 환경변수 설정 확인 필수
- Health Check 엔드포인트: `/health`

---

**🎯 이 가이드를 통해 팀원들이 SANZERO 프로젝트를 빠르게 이해하고 효율적으로 개발할 수 있습니다.**

*마지막 업데이트: 2025-11-30*
*프로젝트 상태: Production Ready*