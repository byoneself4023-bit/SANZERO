# SANZERO 개발 참고사항

## 🎯 **프로덕션 준비 체크리스트**

### 1. 보안 필수 확인사항
- **XSS 방어**: 모든 사용자 입력 데이터 sanitization 완료 ✅
- **CSRF 보호**: Double Submit Cookie 패턴 적용 완료 ✅
- **권한 관리**: 사용자별 데이터 격리 및 역할 기반 접근 제어 ✅
- **민감정보 보호**: 의료정보, 급여정보 암호화 저장 ✅

### 2. 데이터 무결성 검증
- **is_active 필터링**: 모든 조회 쿼리에 `.eq("is_active", True)` 적용 ✅
- **Timezone 일관성**: 모든 시간 데이터 UTC 기준 처리 ✅
- **None 값 안전 처리**: dict.get() 기본값 제공으로 템플릿 에러 방지 ✅

### 3. API 안정성 확보
- **타임아웃 처리**: 외부 API (LLM) 호출 시 30초 제한 ✅
- **에러 처리**: 사용자 친화적 에러 메시지 제공 ✅
- **비동기 처리**: AI 분석, ML 예측 등 블로킹 방지 ✅

## 🚀 **핵심 개발 패턴 (현재 적용됨)**

### 4. Supabase 통합 아키텍처
- **Service Role Key**: 모든 데이터베이스 작업은 서버 측에서만 처리 ✅
- **Anon Key**: 사용자 인증 작업 (sign_up, sign_in, sign_out) 전용 ✅
- **RPC 함수**: 복잡한 계산 로직은 PostgreSQL 함수로 구현 ✅

### 5. HTMX 모범 사례
- **동적 컨텐츠**: 페이지 새로고침 없이 실시간 업데이트 ✅
- **폼 처리**: CSRF 토큰 자동 포함, 로딩 인디케이터 표시 ✅
- **에러 처리**: 사용자 친화적 메시지, 적절한 HTTP 상태 코드 ✅

### 6. 프로덕션 운영 참고사항
- **Docker 환경**: Health check 활성화, 로그 모니터링 ✅
- **성능 최적화**: 비동기 처리, 캐싱, 데이터베이스 인덱스 ✅
- **모니터링**: APM 연동, 에러 로그 추적, 사용자 행동 분석 준비

## ⚠️ **주의사항**

### 변수 정의 순서 (Critical)
- **전역 변수는 파일 상단에 정의**: import 직후, 함수 정의 전에 모든 전역 변수 초기화
- **조건부 import 변수**: try/except로 서비스 가용성 확인하는 변수들은 최우선 정의
- **예시 (analysis.py)**:
  ```python
  # ✅ 올바른 순서
  try:
      from app.services.disability_prediction_service import get_disability_prediction_service
      DISABILITY_PREDICTION_AVAILABLE = True
  except ImportError:
      DISABILITY_PREDICTION_AVAILABLE = True

  # 그 다음 함수 정의
  def disability_prediction_page(...):
      return {"disability_service_available": DISABILITY_PREDICTION_AVAILABLE}  # 사용 가능
  ```
- **실제 발생한 오류**: 변수를 사용하는 함수가 변수 정의보다 먼저 정의되어 500 에러 발생
- **해결책**: 모든 전역 변수를 파일 최상단(import 직후)에 정의

### AI 서비스 관련
- **API 키 관리**: 환경변수로 안전하게 관리, 로테이션 계획 수립
- **타임아웃 설정**: 외부 API 호출 시 30초 제한, 재시도 로직
- **Fallback 시스템**: AI 서비스 장애 시 기본 기능 유지

### 개인정보 처리
- **의료정보**: 암호화 저장, 접근 로그 기록, 최소 수집 원칙
- **급여정보**: 마스킹 처리, 통계 목적 외 노출 금지
- **로깅**: 민감정보 제외, exc_info=True로 스택 트레이스 분리

### 확장성 고려사항
- **부하 분산**: Nginx 설정, FastAPI worker 수 조정
- **데이터베이스**: 인덱스 최적화, 쿼리 성능 모니터링
- **스토리지**: Supabase Storage 용량 관리, CDN 활용

---

## 📝 **향후 개선 가능 영역**

### 1. 추가 보안 강화
- 2FA (이중 인증) 도입
- 개인정보 접근 감사 로그
- 정기적인 보안 취약점 점검

### 2. 사용자 경험 개선
- 실시간 알림 시스템
- 프로그레시브 웹 앱 (PWA) 적용
- 접근성 (Accessibility) 개선

### 3. 성능 최적화
- 데이터베이스 쿼리 최적화
- 이미지 최적화 및 지연 로딩
- API 응답 캐싱 전략

---

*최종 업데이트: 2025-11-05*
*상태: Production Ready - 모든 핵심 기능 완성*