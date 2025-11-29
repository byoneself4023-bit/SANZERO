# SANZERO 데이터베이스 설정 가이드

## 📋 개요

SANZERO AI 분석 플로우에 필요한 모든 데이터베이스 테이블과 기능을 자동으로 설정하는 SQL 스크립트 모음입니다.

## 🎯 포함된 기능

### ✅ 생성되는 테이블 (7개)
1. **users** - 사용자 프로필 (auth.users 확장)
2. **lawyers** - 노무사 정보 (nomusa 확장 필드 포함)
3. **compensation_applications** - 보상금 신청/관리
4. **consultations** - 상담 예약/관리
5. **precedents** - 판례 데이터 (pgvector 임베딩 포함)
6. **notifications** - 알림 시스템
7. **analysis_requests** - AI 분석 요청 (기존 스크립트 통합)

### ✅ 고급 기능
- **pgvector 확장**: 판례 유사도 검색
- **현재 보안 설정**: RLS는 비활성화 상태 (기존 시스템과 완벽 호환)
- **성능 인덱스**: 11개 핵심 검색 최적화 인덱스
- **RPC 함수**: 보상금 계산, 통계 조회
- **자동 트리거**: updated_at 필드 자동 업데이트

### ⚠️ 중요 안전 정보
- **현재 SANZERO는 RLS OFF 상태**에서 정상 동작합니다
- 이 SQL 스크립트들은 **기존 기능을 그대로 유지**하면서 데이터베이스 초기화만 제공합니다
- **99% 완성 상태를 유지**하면서 안전하게 사용할 수 있습니다

## 🚀 빠른 시작 (권장)

### 방법 1: 원클릭 초기화 (가장 간단)

1. **Supabase 대시보드** 접속
2. **SQL Editor** 메뉴 선택
3. **`init_database.sql`** 파일 내용을 복사하여 붙여넣기
4. **Run** 버튼 클릭
5. ✅ 완료! 모든 설정이 자동으로 적용됩니다.

```sql
-- init_database.sql 실행 후 결과 확인
SELECT '🎉 SANZERO 데이터베이스 초기화 완료!' as status;
```

## 📚 개별 스크립트 사용법 (고급)

세부적인 제어가 필요한 경우 다음 순서로 개별 실행:

### 1단계: 핵심 테이블 생성
```bash
# 파일: create_core_tables.sql
# 실행: Supabase SQL Editor에서 실행
```

### 2단계: 확장 및 보안 설정
```bash
# 파일: setup_extensions_and_rls.sql
# 실행: Supabase SQL Editor에서 실행
```

### 3단계: 성능 최적화
```bash
# 파일: create_indexes_and_functions.sql
# 실행: Supabase SQL Editor에서 실행
```

### 4단계: 기존 스크립트 통합
```bash
# 파일: create_analysis_requests_table.sql (이미 존재)
# 파일: add_nomusa_fields.sql (이미 존재)
# 참고: init_database.sql에서 자동으로 처리됨
```

## 🔧 생성되는 주요 기능

### RPC 함수들
```sql
-- 보상금 계산
SELECT calculate_personalized_compensation(
    'user-uuid'::uuid,
    4000000,  -- 기본급
    'moderate', -- 심각도
    '12급',    -- 장해등급
    500000     -- 의료비
);

-- 대시보드 통계
SELECT get_dashboard_statistics();
```

### 벡터 검색 (판례 유사도)
```sql
-- 유사 판례 검색 (embedding이 있는 경우)
SELECT * FROM search_similar_precedents(
    query_embedding,  -- vector(384)
    0.7,             -- 유사도 임계값
    10               -- 최대 결과 수
);
```

## 📊 확인 방법

### 테이블 생성 확인
```sql
-- 모든 테이블 확인
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('users', 'lawyers', 'compensation_applications',
                   'consultations', 'precedents', 'notifications',
                   'analysis_requests')
ORDER BY table_name;
```

### 인덱스 확인
```sql
-- 생성된 인덱스 확인
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

### 확장 및 테이블 확인
```sql
-- PostgreSQL 확장 확인
SELECT extname, extversion FROM pg_extension
WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm');

-- RLS 상태 확인 (현재는 모두 비활성화 상태여야 함)
SELECT tablename,
       CASE WHEN rowsecurity THEN 'ON' ELSE 'OFF' END as rls_status
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('users', 'lawyers', 'compensation_applications',
                  'consultations', 'precedents', 'notifications', 'analysis_requests')
ORDER BY tablename;
```

## 🔒 보안 특징

### 현재 보안 설정 (RLS 비활성화)
- **FastAPI Service Role**: 모든 데이터베이스 작업을 Service Role Key로 수행
- **애플리케이션 레벨 보안**: FastAPI에서 사용자 권한 검증
- **기존 시스템 호환**: 현재 "99% 완성" 상태를 그대로 유지
- **향후 확장 가능**: 필요시 setup_extensions_and_rls.sql에서 RLS 활성화 가능
- **판례 공유**: 인증된 사용자는 판례 데이터 조회 가능

### 함수 보안
```sql
-- 모든 RPC 함수는 SECURITY DEFINER 모드
-- 인증된 사용자만 실행 가능
GRANT EXECUTE ON FUNCTION calculate_personalized_compensation TO authenticated;
```

## ⚡ 성능 최적화

### 주요 인덱스
- **이메일 조회**: `idx_users_email`
- **노무사 전문분야**: `idx_lawyers_specialties` (GIN)
- **보상금 신청 상태**: `idx_comp_apps_status`
- **벡터 유사도**: `idx_precedents_embedding_cosine` (IVFFLAT)

### 검색 최적화
- **전문검색**: pg_trgm 확장으로 fuzzy 검색 지원
- **배열 검색**: GIN 인덱스로 specialties 배열 빠른 검색
- **시간 범위**: created_at, scheduled_at 시간 범위 조회 최적화

## 🛠️ 트러블슈팅

### 자주 발생하는 문제

1. **pgvector 확장 오류**
   ```sql
   -- 해결: Supabase에서 pgvector 확장 활성화 확인
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **RLS 정책 충돌**
   ```sql
   -- 해결: 기존 정책이 있는 경우 DROP 후 재생성
   DROP POLICY IF EXISTS "정책이름" ON 테이블명;
   ```

3. **외래키 제약 오류**
   ```sql
   -- 해결: auth.users 테이블 존재 확인
   SELECT * FROM auth.users LIMIT 1;
   ```

### 로그 확인
```sql
-- 테이블 생성 로그
SELECT 'SANZERO 핵심 테이블 생성 완료!' as status;

-- RLS 설정 로그
SELECT '✅ RLS 정책 설정 완료' as result;

-- 완료 확인
SELECT '🎉 SANZERO 데이터베이스 초기화 완료!' as message;
```

## 📝 추가 정보

### 관련 파일
- **create_core_tables.sql**: 핵심 테이블 생성 (350줄)
- **setup_extensions_and_rls.sql**: 확장 및 보안 설정 (200줄)
- **create_indexes_and_functions.sql**: 성능 최적화 (450줄)
- **init_database.sql**: 통합 초기화 스크립트 (300줄)

### 기존 파일 통합
- **create_analysis_requests_table.sql**: analysis_requests 테이블 및 관련 기능
- **add_nomusa_fields.sql**: lawyers 테이블 확장 필드 추가

---

## 🎉 결과

### ✅ **100% 안전한 데이터베이스 초기화**
이 스크립트들을 실행하면 **기존 SANZERO 시스템을 그대로 유지**하면서 데이터베이스 초기화 기능을 추가할 수 있습니다:

1. **사례 입력 (판례 분석)** ✅
2. **분석 리포트 확인** ✅
3. **장해등급 예측 실행** ✅
4. **보상금 계산 수행** ✅
5. **노무사 검색 및 예약** ✅

### 🛡️ **보장사항**
- **기존 기능 유지**: 현재 동작하는 모든 기능이 그대로 작동
- **성능 향상**: pgvector 및 11개 인덱스로 검색 속도 개선
- **확장 기반**: 향후 AI 기능 확장을 위한 완벽한 데이터베이스 구조

**"99% 완성" 상태를 유지하면서 안전하게 데이터베이스를 완성합니다!** 🚀