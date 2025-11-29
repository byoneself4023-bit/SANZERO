-- SANZERO AI 분석 요청 테이블 생성
-- analysis_service.py에서 사용하는 컬럼들을 기반으로 구성

CREATE TABLE IF NOT EXISTS analysis_requests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    application_id UUID REFERENCES compensation_applications(id) ON DELETE SET NULL,
    query_text TEXT NOT NULL,
    analysis_type TEXT DEFAULT 'precedent_search' CHECK (analysis_type IN ('precedent_search', 'disability_prediction', 'comprehensive')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    result JSONB,
    error_message TEXT,
    processing_time_ms INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_analysis_requests_user_id ON analysis_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_requests_status ON analysis_requests(status);
CREATE INDEX IF NOT EXISTS idx_analysis_requests_created_at ON analysis_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_requests_is_active ON analysis_requests(is_active);

-- RLS (Row Level Security) 활성화
ALTER TABLE analysis_requests ENABLE ROW LEVEL SECURITY;

-- 사용자는 자신의 분석 요청만 조회/생성 가능
CREATE POLICY "Users can view their own analysis requests" ON analysis_requests
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own analysis requests" ON analysis_requests
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- 관리자는 모든 분석 요청 관리 가능 (선택사항)
CREATE POLICY "Admins can manage all analysis requests" ON analysis_requests
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.user_type = 'admin'
            AND users.is_active = true
        )
    );

-- updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_analysis_requests_updated_at BEFORE UPDATE
    ON analysis_requests FOR EACH ROW EXECUTE PROCEDURE
    update_updated_at_column();