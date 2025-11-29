# 산재 보상 서비스 시스템

## 프로젝트 개요
- **서비스명**: SANZERO - AI 기반 산업재해 보상 서비스 플랫폼

## 기술 스택
- **백엔드 & SSR 프론트**
  - Python 3.13 + FastAPI
  - 템플릿: **Jinja2**
  - UI: Tailwind CSS 3.4 + **HTMX**(전체 페이지 HTMX 갱신)
- **인증·DB·파일 저장**: **Supabase**
  - Auth·Storage·SQL은 Supabase API를 *서버 측(FastAPI)* 에서만 호출
  - **브라우저에는 Supabase JS SDK·키를 포함하지 않음**
- **배포**: 도커컴포즈 (uvicorn 기반 실행 FastAPI 도커, nginx 도커로 구성)
  - FastAPI에서 정적 파일 직접 서빙
  - 단순 구조 지향 (개발/운영 환경 분리 없음)

## AI/ML 기술 스택
- **NLP & 임베딩**
  - SBERT (Sentence-BERT): 판례 문서 벡터화
  - 개체명 인식 (NER): 산재 키워드 추출
  - OCR: 문서 이미지 텍스트 변환
- **RAG 시스템** (Retrieval-Augmented Generation)
  - Supabase pgvector: 판례 벡터 저장소
  - LangChain: RAG 파이프라인 구축
  - 검색 증강 생성: 유사 판례 기반 분석
- **딥러닝 모델**
  - TensorFlow/PyTorch: DNN 장해등급 예측 모델 (차후 구현 예정)
  - MLflow: 모델 버전 관리 및 실험 추적 (차후 구현 예정)
  - Jupyter Notebook: ML 개발 환경 (차후 구현 예정)
- **LLM API 연동**
  - OpenAI API / Anthropic Claude API: 판례 분석
  - 프롬프트 엔지니어링: 산재 특화 분석

## 📚 관련 문서
- **@README.md**: 프로젝트 개요 및 빠른 시작
- **@ARCHITECTURE.md**: 시스템 구조, DB 스키마, API 명세
- **@PROGRESS.md**: 개발 진행 상황, 완료/미완료 작업 (작업 후 반드시 기억해야할 사항)
- **@TESTPLAN.md**: 테스트 계획 및 케이스
- **@TESTDATA.md**: 테스트 계정 및 데이터
- **@NOTE.md**: 개발 시 주의사항
- **@DESIGN.md**: UI/UX 디자인 가이드

## 공통 작업 가이드
- 모든 작업은 ultra think 해서 작업해주세요.
- 모든 작업은
  1. 먼저 현재 상태를 철저히 분석하고,
  2. 철저하게 계획을 세우고,
  3. sub agents 로 분리하지 말고, 순차적인 작업 계획을 작성한 후,
  4. API 는 모두 TDD 기반으로 테스트 코드 및 실제 코드를 구현하고,
  5. API 는 예외 케이스까지 완벽히 테스트하고,
  6. 코드 완성 후에는 바로 종료하지 말고, 전체 코드를 코드 레벨로 확인하여, 확실한 버그가 발견되면, 수정해주세요
- **🚫 Docker 관련 중요 사항**: 도커 빌드, 재시작, 테스트는 **사용자가 직접** 수행합니다. Claude는 Docker 명령어를 실행하지 말고 코드 수정만 완료 후 사용자에게 알려주세요.
- 작업이 완료되면 꼭 기억해야할 내용에 대해서는 PROGRESS.md 파일에 기록해주고,
- 필요시 CLAUDE.md 와 ARCHITECTURE.md 등의 다음 주요 파일들도 개선해주세요
- 모든 작업은 다음 주요 파일을 확인하여 작업해주세요
  - **@CLAUDE.md**: 전체 프로젝트 개요 및 기술스택과 작업 가이드
  - **@ARCHITECTURE.md**: 시스템 구조, DB 스키마, API 명세
  - **@PROGRESS.md**: 개발 진행 상황, 완료/미완료 작업 (작업 후 반드시 기억해야할 내용)
  - **@DESIGN.md**: UI/UX 디자인 가이드
    - wireframes 하위폴더에 UI 구현이 필요한 모든 화면은 xml 포멧으로 UI 화면 표현
  - **@TESTPLAN.md**: 테스트 항목
  - **@TESTDATA.md**: 테스트시 필요한 데이터
  - **@NOTE.md**: 빈번한 실수와 해결 방법 기억
- 작업 완료 후에는 테스트 항목을 @TESTPLAN.md 파일에 작성하고, 직접 docker 를 실행하고, puppeteer MCP 로 테스트하여, 모든 버그를 side effect 를 고려하여 신중하게 수정한 후, @TESTPLAN.md 에 기재된 모든 테스트 항목이 PASS 할 때까지 작업을 반복합니다
  - 주로 실수하는 항목은 @NOTE.md 파일에 이후 실수를 반복하지 않기 위해 기재합니다.

## MCP 사용 설정
- 다음 MCP 가 연결되어 있으므로, 관련 작업은 해당 MCP 를 직접 사용해서 작업해주세요
  - supabase MCP (supabase 제어)
  - puppeteer MCP (브라우저 제어)

## Supabase 설정
- **프로젝트 ID**: ityipqwjounyjkbvzgqu
- **초기 관리자**: byoneself4023@ajou.ac.kr (Kuka) - 자세한 정보는 @TESTDATA.md 참조
- **중요**: Email confirmation OFF, RLS OFF
  - FastAPI 내부에서만 supabase 에 엑세스하므로 RLS 불필요

## 주요 기능
1. **산재 보상 신청/관리**: 보상금 계산, CRUD 기능, 상태 추적, 관리자 승인/거부
2. **노무사 서비스**: AI 기반 매칭, 검색/필터링, 상담 예약, 평점 시스템
3. **AI 판례 분석**: RAG 기반 유사 판례 검색, LLM 분석, 사안 유불리 분석
4. **장해등급 예측**: AI 모델 기반 자동 예측 (준비 중)
5. **사용자 관리**: Supabase Auth, 권한 기반 접근 제어, 프로필 관리
6. **관리자 시스템**: 사용자 관리, 데이터 대시보드, 시스템 모니터링
7. **보안 시스템**: CSRF/XSS 방어, 데이터 암호화, 접근 로그 추적

## 필수 환경변수 (.env)
```bash
# Supabase 설정
SUPABASE_URL=https://ityipqwjounyjkbvzgqu.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# LLM API 키
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# 보안 설정
SECRET_KEY=your-secret-key-here
CSRF_SECRET_KEY=your-csrf-secret-key

# 애플리케이션 설정
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 보안 체크리스트
- XSS 방어 (bleach) 
- CSRF 보호 (Double Submit Cookie)
- Rate Limiting (Nginx) 
- HttpOnly·Secure 쿠키 
- 보안 헤더 (CSP, X-Frame-Options 등)
- 에러 로깅 보안 (민감정보 노출 방지) 

## 초기 데이터 셋업
- **Supabase 프로젝트**: ityipqwjounyjkbvzgqu (PostgreSQL + pgvector)
- **초기 관리자**: byoneself4023@ajou.ac.kr (Kuka)
- **테스트 계정**: testuser@example.com, testworker@example.com, lawyer@example.com
- **Docker 컨테이너**: FastAPI 애플리케이션 + Nginx 리버스 프록시
- **데이터베이스 테이블**: 사용자, 보상금 신청, 노무사, 상담, 판례 등
- **AI 모델**: TensorFlow DNN 장해등급 예측 모델, SBERT 임베딩
- **외부 API**: OpenAI/Anthropic LLM 연동

## 환경변수 추가 옵션
```bash
# CORS 허용 도메인 (쉼표로 구분, 기본값: localhost 도메인들)
ALLOWED_ORIGINS=http://localhost:8000,http://localhost:8001

# 데이터베이스 풀 설정
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# AI 서비스 설정
AI_REQUEST_TIMEOUT=30
MAX_TOKENS=1000
TEMPERATURE=0.7

# 파일 업로드 설정
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=pdf,jpg,jpeg,png,doc,docx
```