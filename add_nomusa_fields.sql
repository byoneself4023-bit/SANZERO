-- nomusa_dummy_data.json의 추가 필드들을 lawyers 테이블에 추가

-- 연락처 필드 추가
ALTER TABLE lawyers ADD COLUMN IF NOT EXISTS phone VARCHAR(20);

-- 수임료 정책 필드 추가 (텍스트로 저장)
ALTER TABLE lawyers ADD COLUMN IF NOT EXISTS fee_policy TEXT;

-- 온라인 상담 가능 여부 추가
ALTER TABLE lawyers ADD COLUMN IF NOT EXISTS is_online_consult BOOLEAN DEFAULT false;

-- 웹사이트 URL 추가
ALTER TABLE lawyers ADD COLUMN IF NOT EXISTS website_url VARCHAR(255);

-- SANZERO 페이 지원 여부 추가
ALTER TABLE lawyers ADD COLUMN IF NOT EXISTS supports_sanzero_pay BOOLEAN DEFAULT false;

-- case_difficulty 필드 추가 (사건 난이도: 상, 중상, 중, 중하, 하)
ALTER TABLE lawyers ADD COLUMN IF NOT EXISTS case_difficulty VARCHAR(10);

-- 추가된 컬럼들에 대한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_lawyers_phone ON lawyers(phone);
CREATE INDEX IF NOT EXISTS idx_lawyers_is_online_consult ON lawyers(is_online_consult);
CREATE INDEX IF NOT EXISTS idx_lawyers_supports_sanzero_pay ON lawyers(supports_sanzero_pay);
CREATE INDEX IF NOT EXISTS idx_lawyers_case_difficulty ON lawyers(case_difficulty);

-- 확인용 쿼리
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'lawyers'
-- ORDER BY ordinal_position;