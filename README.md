# SANZERO
AI 기반 산업재해 보상 서비스 플랫폼

## 📚 관련 문서
- **@DEVELOPMENT_GUIDE.md**: 🎯 **팀 개발자 가이드** (기능별 코드 위치 매핑)
- **@CLAUDE.md**: 개발 가이드 (Claude Code용)
- **@ARCHITECTURE.md**: 시스템 구조 및 기술 명세
- **@PROGRESS.md**: 개발 진행 상황 및 마일스톤
- **@TESTPLAN.md**: 테스트 계획 및 케이스
- **@TESTDATA.md**: 테스트 계정 및 데이터
- **@NOTE.md**: 개발 시 주의사항
- **@DESIGN.md**: UI/UX 디자인 가이드

## 🚀 빠른 시작

```bash
# 1. 환경변수 설정
cp .env.example .env

# .env 파일을 편집하여 실제 값으로 변경:
# - SUPABASE_URL: Supabase 프로젝트 URL
# - SUPABASE_SERVICE_ROLE_KEY: Supabase Service Role Key
# - OPENAI_API_KEY: OpenAI API 키 (AI 분석용)
# - ANTHROPIC_API_KEY: Anthropic Claude API 키 (선택)

# 2. 도커 실행
docker compose up --build -d

# 3. 접속 확인
http://localhost        # Nginx 프록시
http://localhost:8000   # FastAPI 직접 접속
```

## ✨ 주요 기능 (6개)

1. **산재 보상 신청/관리**: 보상금 계산, CRUD, 상태 추적
2. **노무사 서비스**: AI 매칭, 검색, 상담 예약
3. **AI 판례 분석**: RAG 기반 유사 판례 검색 및 분석
4. **AI 장해등급 예측**: v3 통합 파이프라인 완료 ✅
5. **사용자 인증 시스템**: Supabase 기반 인증/권한 관리
6. **통합 대시보드**: testuser 기반 단일 대시보드

## 🛠️ 기술 스택

Python 3.13 + FastAPI, Supabase, HTMX, Tailwind CSS, Docker

## 📡 주요 API (6개)

```
/auth/*                    - 인증 시스템
/compensation/*            - 산재 보상 신청
/lawyers/*                 - 노무사 서비스
/analysis/*                - AI 판례 분석
/analysis/disability/*     - AI 장해등급 예측 ✅
/                          - 메인 대시보드
```

_상세한 API 명세는 @ARCHITECTURE.md 참조_

---

**SANZERO는 모든 핵심 기능이 완성된 프로덕션 준비 상태의 AI 기반 산재 보상 서비스입니다.**

*자세한 정보는 위의 관련 문서들을 참조하세요.*
