"""
SANZERO Pydantic 스키마 정의
API 요청/응답 모델
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from enum import Enum

# Enum 정의
class UserType(str, Enum):
    GENERAL = "general"
    LAWYER = "lawyer"
    ADMIN = "admin"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class SeverityLevel(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"

class ConsultationType(str, Enum):
    INITIAL = "initial"
    FOLLOWUP = "followup"
    LEGAL_ADVICE = "legal_advice"

class ConsultationStatus(str, Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

# 인증 관련 스키마
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserSignup(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    user_type: UserType = UserType.GENERAL
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('비밀번호가 일치하지 않습니다.')
        return v

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# 사용자 관련 스키마
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    user_type: UserType = UserType.GENERAL
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None
    industry_code: Optional[str] = Field(None, max_length=10)
    job_title: Optional[str] = Field(None, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    birth_date: Optional[date] = None
    gender: Optional[Gender] = None
    industry_code: Optional[str] = Field(None, max_length=10)
    job_title: Optional[str] = Field(None, max_length=100)
    work_environment: Optional[Dict[str, Any]] = None
    medical_history: Optional[Dict[str, Any]] = None
    family_info: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None

class UserResponse(UserBase):
    id: str
    work_environment: Optional[Dict[str, Any]] = None
    medical_history: Optional[Dict[str, Any]] = None
    family_info: Optional[Dict[str, Any]] = None
    risk_profile: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# 노무사 관련 스키마
class LawyerBase(BaseModel):
    license_number: str = Field(..., min_length=5, max_length=50)
    office_name: str = Field(..., min_length=2, max_length=255)
    office_address: Optional[str] = Field(None, max_length=500)
    specialties: List[str] = Field(default_factory=list)
    experience_years: int = Field(default=0, ge=0)
    consultation_fee: int = Field(default=0, ge=0)

    # nomusa 확장 필드들
    phone: Optional[str] = Field(None, max_length=20, description="연락처")
    fee_policy: Optional[str] = Field(None, description="수임료 정책")
    is_online_consult: bool = Field(default=False, description="온라인 상담 가능 여부")
    website_url: Optional[str] = Field(None, max_length=255, description="웹사이트 URL")
    supports_sanzero_pay: bool = Field(default=False, description="SANZERO 페이 지원 여부")
    case_difficulty: Optional[str] = Field(None, max_length=10, description="사건 난이도")

class LawyerCreate(LawyerBase):
    user_id: str

class LawyerUpdate(BaseModel):
    office_name: Optional[str] = Field(None, min_length=2, max_length=255)
    office_address: Optional[str] = Field(None, max_length=500)
    specialties: Optional[List[str]] = None
    experience_years: Optional[int] = Field(None, ge=0)
    consultation_fee: Optional[int] = Field(None, ge=0)
    industry_experience: Optional[Dict[str, Any]] = None
    case_types: Optional[Dict[str, Any]] = None
    availability_schedule: Optional[Dict[str, Any]] = None

    # nomusa 확장 필드들
    phone: Optional[str] = Field(None, max_length=20)
    fee_policy: Optional[str] = None
    is_online_consult: Optional[bool] = None
    website_url: Optional[str] = Field(None, max_length=255)
    supports_sanzero_pay: Optional[bool] = None
    case_difficulty: Optional[str] = Field(None, max_length=10)

class LawyerResponse(LawyerBase):
    id: str
    user_id: str
    rating: float = 0.0
    total_reviews: int = 0
    success_rate: float = 0.0
    avg_compensation_amount: int = 0
    case_count: int = 0
    response_time_hours: int = 24
    industry_experience: Optional[Dict[str, Any]] = None
    case_types: Optional[Dict[str, Any]] = None
    availability_schedule: Optional[Dict[str, Any]] = None
    is_verified: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# 보상금 신청 관련 스키마
class CompensationApplicationBase(BaseModel):
    incident_date: date
    incident_location: str = Field(..., min_length=5, max_length=500)
    incident_description: str = Field(..., min_length=10, max_length=2000)
    injury_type: str = Field(..., min_length=2, max_length=100)
    severity_level: SeverityLevel

class CompensationApplicationCreate(CompensationApplicationBase):
    medical_records: Optional[Dict[str, Any]] = None
    employment_info: Optional[Dict[str, Any]] = None
    salary_info: Optional[Dict[str, Any]] = None

class CompensationApplicationUpdate(BaseModel):
    incident_date: Optional[date] = None
    incident_location: Optional[str] = Field(None, min_length=5, max_length=500)
    incident_description: Optional[str] = Field(None, min_length=10, max_length=2000)
    injury_type: Optional[str] = Field(None, min_length=2, max_length=100)
    severity_level: Optional[SeverityLevel] = None
    medical_records: Optional[Dict[str, Any]] = None
    employment_info: Optional[Dict[str, Any]] = None
    salary_info: Optional[Dict[str, Any]] = None

class CompensationApplicationResponse(CompensationApplicationBase):
    id: str
    user_id: str
    medical_records: Optional[Dict[str, Any]] = None
    employment_info: Optional[Dict[str, Any]] = None
    salary_info: Optional[Dict[str, Any]] = None
    ai_analysis_result: Optional[Dict[str, Any]] = None
    risk_factors: Optional[Dict[str, Any]] = None
    similar_cases: Optional[Dict[str, Any]] = None
    personalized_calculation: Optional[Dict[str, Any]] = None
    success_probability: Optional[float] = None
    recommended_actions: Optional[Dict[str, Any]] = None
    status: ApplicationStatus = ApplicationStatus.PENDING
    estimated_amount: int = 0
    approved_amount: int = 0
    documents: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True

# 상담 관련 스키마
class ConsultationBase(BaseModel):
    consultation_type: ConsultationType
    scheduled_at: datetime
    notes: Optional[str] = Field(None, max_length=1000)

class ConsultationCreate(ConsultationBase):
    lawyer_id: str
    application_id: Optional[str] = None

class ConsultationUpdate(BaseModel):
    status: Optional[ConsultationStatus] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)
    client_satisfaction: Optional[float] = Field(None, ge=1.0, le=5.0)
    outcome_result: Optional[str] = Field(None, max_length=50)
    follow_up_needed: Optional[bool] = None

class ConsultationResponse(ConsultationBase):
    id: str
    client_id: str
    lawyer_id: str
    application_id: Optional[str] = None
    status: ConsultationStatus = ConsultationStatus.REQUESTED
    consultation_fee: int = 0
    match_score: Optional[float] = None
    match_reasons: Optional[Dict[str, Any]] = None
    client_satisfaction: Optional[float] = None
    outcome_result: Optional[str] = None
    follow_up_needed: bool = False
    effectiveness_score: Optional[float] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    client: Optional[UserResponse] = None
    lawyer: Optional[UserResponse] = None
    application: Optional[CompensationApplicationResponse] = None

    class Config:
        from_attributes = True

# AI 분석 관련 스키마
class PrecedentAnalysisRequest(BaseModel):
    incident_description: str = Field(..., min_length=10, max_length=2000)
    injury_type: str = Field(..., min_length=2, max_length=100)
    industry_code: Optional[str] = Field(None, max_length=10)
    employment_info: Optional[Dict[str, Any]] = None

class PrecedentAnalysisResponse(BaseModel):
    similar_cases: List[Dict[str, Any]]
    legal_precedents: List[Dict[str, Any]]
    success_probability: float
    recommended_actions: List[str]
    estimated_timeline: str
    confidence_score: float

# Phase 4: 장해등급 예측 DNN 모델 관련 스키마
class DisabilityPredictionRequest(BaseModel):
    """장해등급 예측 요청 스키마"""
    injury_type: str = Field(..., min_length=2, max_length=100, description="부상 유형")
    severity_level: SeverityLevel = Field(..., description="부상 심각도")
    age: Optional[int] = Field(35, ge=18, le=100, description="나이")
    gender: Optional[str] = Field("male", pattern="^(male|female)$", description="성별")
    body_part: Optional[str] = Field("기타", max_length=50, description="부상 부위")
    accident_type: Optional[str] = Field("기타", max_length=100, description="사고 유형")
    medical_cost: Optional[int] = Field(500000, ge=0, description="의료비")
    treatment_days: Optional[int] = Field(30, ge=0, description="치료 기간(일)")
    surgery_required: Optional[bool] = Field(False, description="수술 필요 여부")
    complications: Optional[bool] = Field(False, description="합병증 여부")
    medical_records: Optional[Dict[str, Any]] = Field(None, description="의료 기록")

class DisabilityGradePrediction(BaseModel):
    """장해등급 예측 결과"""
    grade: str = Field(..., description="장해등급")
    probability: float = Field(..., ge=0.0, le=1.0, description="확률")
    percentage: float = Field(..., ge=0.0, le=100.0, description="백분율")

class DisabilityPredictionResponse(BaseModel):
    """장해등급 예측 응답 스키마"""
    predicted_grade: str = Field(..., description="예측된 장해등급")
    confidence: float = Field(..., ge=0.0, le=1.0, description="신뢰도")
    confidence_percentage: float = Field(..., ge=0.0, le=100.0, description="신뢰도 백분율")
    top_predictions: List[DisabilityGradePrediction] = Field(..., description="상위 3개 예측 결과")
    explanation: str = Field(..., description="예측 설명")
    recommendations: List[str] = Field(..., description="추천 조치사항")
    model_info: Dict[str, Any] = Field(..., description="모델 정보")

class DisabilityAnalysisHistory(BaseModel):
    """장해등급 분석 이력"""
    id: str
    user_id: str
    request_data: DisabilityPredictionRequest
    prediction_result: DisabilityPredictionResponse
    created_at: datetime
    model_version: str

# 채팅 관련 스키마
class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)
    timestamp: datetime

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    context: Optional[Dict[str, Any]] = None
    suggestions: List[str] = Field(default_factory=list)

# 알림 관련 스키마
class NotificationCreate(BaseModel):
    user_id: str
    type: str = Field(..., max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=1000)

class NotificationResponse(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    content: str
    status: str = "pending"
    sent_at: Optional[datetime] = None
    is_read: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

# 공통 응답 스키마
class SuccessResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
    pages: int

# 보상금 계산 관련 스키마
class CompensationCalculationRequest(BaseModel):
    base_salary: int = Field(..., gt=0)
    injury_severity: SeverityLevel
    disability_grade: Optional[str] = Field(None, max_length=10)
    medical_costs: int = Field(default=0, ge=0)
    industry_code: Optional[str] = Field(None, max_length=10)
    region_code: Optional[str] = Field(None, max_length=10)

class CompensationCalculationResponse(BaseModel):
    base_amount: int
    severity_multiplier: float
    grade_multiplier: float
    industry_multiplier: float
    regional_multiplier: float
    medical_costs: int
    total_amount: int
    calculation_factors: Dict[str, Any]

# 노무사 검색 관련 스키마
class LawyerSearchRequest(BaseModel):
    specialties: Optional[List[str]] = None
    location: Optional[str] = None
    experience_years_min: Optional[int] = Field(None, ge=0)
    rating_min: Optional[float] = Field(None, ge=0.0, le=5.0)
    consultation_fee_max: Optional[int] = Field(None, ge=0)
    is_verified: bool = True
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

class LawyerListResponse(BaseModel):
    lawyers: List[LawyerResponse]
    total: int
    page: int
    size: int
    pages: int

# 노무사 매칭 관련 스키마
class LawyerMatchRequest(BaseModel):
    application_id: str
    max_results: int = Field(default=3, ge=1, le=10)

class LawyerMatchResponse(BaseModel):
    lawyer_id: str
    match_score: float
    match_reasons: Dict[str, Any]
    lawyer: LawyerResponse

# AI 분석 서비스 관련 스키마 (Phase 2)
class AnalysisRequestCreate(BaseModel):
    query_text: str = Field(..., min_length=10, max_length=1000)
    case_description: str = Field(..., min_length=20, max_length=2000)
    application_id: Optional[str] = None
    industry_type: Optional[str] = Field(None, max_length=100)
    injury_type: Optional[str] = Field(None, max_length=100)
    accident_circumstances: Optional[str] = Field(None, max_length=2000)

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SimilarPrecedentResult(BaseModel):
    precedent_id: str
    case_number: str
    case_title: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    judgment_result: str
    compensation_amount: int
    judgment_summary: str
    matching_factors: Dict[str, Any]

class LegalAnalysisResult(BaseModel):
    analysis_summary: str
    success_probability: float = Field(..., ge=0.0, le=100.0)
    key_factors: Dict[str, List[str]]  # positive, negative
    similar_precedents_analysis: List[Dict[str, str]]
    recommended_actions: List[str]
    legal_reasoning: str
    risk_assessment: Dict[str, Any]
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    analysis_timestamp: datetime
    model_version: str

class AnalysisRequestResponse(BaseModel):
    id: str
    user_id: str
    application_id: Optional[str]
    query_text: str
    analysis_type: str
    status: AnalysisStatus
    result: Optional[Dict[str, Any]] = None
    processing_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AnalysisHistoryResponse(BaseModel):
    id: str
    query_text: str
    analysis_type: str
    status: AnalysisStatus
    processing_time_ms: Optional[int] = None
    created_at: datetime
    updated_at: datetime

class PrecedentSearchRequest(BaseModel):
    query_text: str = Field(..., min_length=5, max_length=500)
    similarity_threshold: float = Field(default=0.7, ge=0.5, le=1.0)
    max_results: int = Field(default=10, ge=1, le=50)
    filters: Optional[Dict[str, str]] = None

class PrecedentSearchResponse(BaseModel):
    precedents: List[SimilarPrecedentResult]
    total_found: int
    query_processing_time_ms: int

# 고급 판례 분석 요청
class ComprehensiveAnalysisRequest(BaseModel):
    case_description: str = Field(..., min_length=50, max_length=3000)
    incident_date: Optional[date] = None
    incident_location: Optional[str] = Field(None, max_length=200)
    injury_type: str = Field(..., min_length=2, max_length=100)
    severity_level: SeverityLevel
    industry_code: Optional[str] = Field(None, max_length=10)
    employment_info: Optional[Dict[str, Any]] = None
    medical_records: Optional[Dict[str, Any]] = None
    salary_info: Optional[Dict[str, Any]] = None
    previous_claims: Optional[List[Dict[str, Any]]] = None

class ComprehensiveAnalysisResponse(BaseModel):
    request_id: str
    similar_precedents: List[SimilarPrecedentResult]
    legal_analysis: LegalAnalysisResult
    statistical_analysis: Dict[str, Any]
    risk_factors: List[Dict[str, Any]]
    success_probability: float
    estimated_compensation_range: Dict[str, int]  # min, max, average
    recommended_next_steps: List[Dict[str, Any]]
    processing_summary: Dict[str, Any]

# 판례 임베딩 관련
class EmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int
    model_used: str
    processing_time_ms: int


# AI 챗봇 관련 스키마
class ChatMessage(BaseModel):
    """채팅 메시지 스키마"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)
    timestamp: datetime

class ChatSessionCreate(BaseModel):
    """채팅 세션 생성 요청"""
    pass  # 사용자 ID는 인증에서 가져옴

class ChatSessionResponse(BaseModel):
    """채팅 세션 응답"""
    session_id: str
    created_at: datetime
    message_count: int = 0

class ChatMessageCreate(BaseModel):
    """채팅 메시지 생성 요청"""
    content: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    """채팅 메시지 응답"""
    session_id: str
    user_message: str
    ai_response: str
    timestamp: datetime

class ChatHistoryResponse(BaseModel):
    """채팅 기록 응답"""
    messages: List[ChatMessage]
    session_id: str
    total_count: int

class ChatSessionListResponse(BaseModel):
    """채팅 세션 목록 응답"""
    session_id: str
    created_at: datetime
    last_message: str
    message_count: int

class ChatContextData(BaseModel):
    """채팅 컨텍스트 데이터"""
    user_type: Optional[str] = None
    industry: Optional[str] = None
    job_title: Optional[str] = None
    recent_applications: Optional[List[Dict[str, Any]]] = None
    consultation_history: Optional[List[Dict[str, Any]]] = None


# ============ 산재 보상금 계산기 관련 스키마 ============

class SaturdayWorkTypeEnum(str, Enum):
    """토요일 근무 유형"""
    FULL_PAY_8H = "full_8h"      # 토요일 유급 8시간
    HALF_PAY_4H = "half_4h"      # 토요일 유급 4시간
    NO_PAY = "no_pay"            # 토요일 무급

class WageCalculationMethod(str, Enum):
    """통상임금 계산 방법"""
    DIRECT = "direct"            # 방법 1: 직접 계산한 통상임금 입력
    MONTHLY = "monthly"          # 방법 2: 월 통상임금으로 자동 계산
    SKIP = "skip"                # 방법 3: 통상임금 입력 건너뛰기

class CompensationCalculatorRequest(BaseModel):
    """보상금 계산기 요청 스키마"""
    wage_method: WageCalculationMethod = Field(..., description="통상임금 계산 방법")
    wage_amount: int = Field(0, ge=0, description="입력 금액")
    saturday_type: SaturdayWorkTypeEnum = Field(SaturdayWorkTypeEnum.NO_PAY, description="토요일 근무 유형")
    calculation_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="계산 기준일 (YYYY-MM-DD)")
    disability_grade: Optional[str] = Field(None, pattern=r"^[1-9]|1[0-4]급$", description="장해등급")
    survivors_count: int = Field(1, ge=1, le=10, description="유족 수")
    apply_limits: bool = Field(True, description="최저/최고 한도 적용 여부")

class WageCalculationResult(BaseModel):
    """통상임금 계산 결과"""
    method: str = Field(..., description="계산 방법")
    hourly_wage: int = Field(..., description="시간급 통상임금")
    daily_wage: int = Field(..., description="일급 통상임금")
    monthly_wage: int = Field(..., description="월급 통상임금")
    monthly_hours: Optional[int] = Field(None, description="월 소정근로시간")
    saturday_type: Optional[str] = Field(None, description="토요일 근무 유형")
    calculation_details: str = Field(..., description="계산 상세 정보")

class CompensationBenefitResult(BaseModel):
    """개별 보상금 계산 결과"""
    name: str = Field(..., description="보상금 명칭")
    description: str = Field(..., description="보상금 설명")
    daily_amount: Optional[int] = Field(None, description="일당 금액")
    monthly_amount: Optional[int] = Field(None, description="월 금액")
    annual_amount: Optional[int] = Field(None, description="연 금액")
    total_amount: Optional[int] = Field(None, description="총 금액")
    lump_sum: Optional[int] = Field(None, description="일시금")
    calculation: str = Field(..., description="계산식")
    legal_basis: str = Field(..., description="법적 근거")
    payment_type: Optional[str] = Field(None, description="지급 방식")
    grade: Optional[str] = Field(None, description="등급")
    days: Optional[int] = Field(None, description="지급일수")
    rate: Optional[str] = Field(None, description="지급률")

class CompensationCalculationSummary(BaseModel):
    """보상금 계산 요약"""
    total_estimated_amount: int = Field(..., description="총 예상 보상금")
    calculation_date: str = Field(..., description="계산 기준일")
    year_standard: int = Field(..., description="적용 기준연도")
    notes: str = Field(..., description="주의사항")

class CompensationCalculatorResponse(BaseModel):
    """보상금 계산기 전체 응답"""
    wage_calculation: WageCalculationResult = Field(..., description="통상임금 계산 결과")
    compensation_calculation: Dict[str, Any] = Field(..., description="보상금 계산 결과")
    calculation_metadata: Dict[str, Any] = Field(..., description="계산 메타데이터")

class CompensationStandardsResponse(BaseModel):
    """보상 기준 조회 응답"""
    year: int = Field(..., description="기준 연도")
    min_daily_amount: int = Field(..., description="최저 일당 보상기준")
    max_daily_amount: int = Field(..., description="최고 일당 보상기준")
    min_wage_hourly: int = Field(..., description="시간당 최저임금")
    min_wage_daily: int = Field(..., description="일급 최저임금")
    min_wage_monthly: int = Field(..., description="월급 최저임금")
    survivor_base_rate: float = Field(..., description="유족급여 기본률")
    updated_at: str = Field(..., description="갱신일시")

# ============ 기존 보상금 신청 시스템과의 연동 ============

class CompensationApplicationCreateExtended(BaseModel):
    """확장된 보상금 신청 생성 요청"""
    incident_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="사고 발생일")
    incident_location: str = Field(..., min_length=5, max_length=200, description="사고 발생 장소")
    incident_description: str = Field(..., min_length=20, max_length=2000, description="사고 경위")
    injury_type: str = Field(..., min_length=2, max_length=100, description="부상 유형")
    severity_level: SeverityLevel = Field(..., description="부상 심각도")

    # 의료 정보
    hospital_name: Optional[str] = Field(None, max_length=100, description="병원명")
    diagnosis: Optional[str] = Field(None, max_length=200, description="진단명")
    treatment_period: Optional[str] = Field(None, max_length=50, description="치료 기간")
    medical_cost: int = Field(0, ge=0, description="의료비")

    # 고용 정보
    company_name: Optional[str] = Field(None, max_length=100, description="회사명")
    position: Optional[str] = Field(None, max_length=50, description="직위")
    employment_type: Optional[str] = Field(None, max_length=30, description="고용 형태")
    work_start_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="입사일")

    # 급여 정보
    base_salary: int = Field(0, ge=0, description="기본 급여")
    monthly_bonus: int = Field(0, ge=0, description="월 수당")
    annual_salary: int = Field(0, ge=0, description="연봉")

    # 계산기 연동 필드
    use_calculator_result: bool = Field(False, description="계산기 결과 사용 여부")
    calculator_estimated_amount: Optional[int] = Field(None, ge=0, description="계산기 추정 금액")

class CompensationApplicationResponseExtended(CompensationApplicationResponse):
    """확장된 보상금 신청 응답 (계산 정보 포함)"""
    calculation_history: Optional[List[Dict[str, Any]]] = Field(None, description="계산 이력")
    ai_analysis_summary: Optional[Dict[str, Any]] = Field(None, description="AI 분석 요약")
    disability_prediction: Optional[Dict[str, Any]] = Field(None, description="장해등급 예측")
    similar_cases_count: Optional[int] = Field(None, description="유사 사례 수")

# ============ 관리자용 보상 기준 관리 ============

class CompensationStandardCreate(BaseModel):
    """보상 기준 생성 요청"""
    year: int = Field(..., ge=2020, le=2030, description="기준 연도")
    standard_type: str = Field(..., max_length=50, description="기준 유형")
    amount: int = Field(..., gt=0, description="기준 금액")
    effective_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="시행일")
    description: Optional[str] = Field(None, max_length=200, description="설명")

class CompensationStandardUpdate(BaseModel):
    """보상 기준 수정 요청"""
    amount: Optional[int] = Field(None, gt=0, description="기준 금액")
    effective_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="시행일")
    description: Optional[str] = Field(None, max_length=200, description="설명")
    is_active: Optional[bool] = Field(None, description="활성화 여부")

class CompensationStandardResponse(BaseModel):
    """보상 기준 응답"""
    id: str = Field(..., description="기준 ID")
    year: int = Field(..., description="기준 연도")
    standard_type: str = Field(..., description="기준 유형")
    amount: int = Field(..., description="기준 금액")
    effective_date: str = Field(..., description="시행일")
    description: Optional[str] = Field(None, description="설명")
    is_active: bool = Field(..., description="활성화 여부")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")

# ============ 계산 이력 관리 ============

class CalculationHistoryCreate(BaseModel):
    """계산 이력 생성 요청"""
    calculation_type: str = Field(..., max_length=50, description="계산 유형")
    input_data: Dict[str, Any] = Field(..., description="입력 데이터")
    result_data: Dict[str, Any] = Field(..., description="결과 데이터")

class CalculationHistoryResponse(BaseModel):
    """계산 이력 응답"""
    id: str = Field(..., description="이력 ID")
    user_id: str = Field(..., description="사용자 ID")
    calculation_type: str = Field(..., description="계산 유형")
    input_data: Dict[str, Any] = Field(..., description="입력 데이터")
    result_data: Dict[str, Any] = Field(..., description="결과 데이터")
    created_at: datetime = Field(..., description="생성일시")

# ============ 통계 및 보고서 ============

class CompensationStatistics(BaseModel):
    """보상금 통계"""
    total_applications: int = Field(..., description="총 신청 건수")
    total_approved_amount: int = Field(..., description="총 승인 금액")
    average_compensation: int = Field(..., description="평균 보상금")
    approval_rate: float = Field(..., description="승인률")
    common_injury_types: List[Dict[str, Any]] = Field(..., description="빈발 부상 유형")
    monthly_trends: List[Dict[str, Any]] = Field(..., description="월별 트렌드")

class CalculatorUsageStats(BaseModel):
    """계산기 사용 통계"""
    total_calculations: int = Field(..., description="총 계산 횟수")
    daily_calculations: int = Field(..., description="일일 계산 횟수")
    popular_calculation_types: List[Dict[str, Any]] = Field(..., description="인기 계산 유형")
    average_compensation_amount: int = Field(..., description="평균 계산 보상금")
    user_distribution: Dict[str, int] = Field(..., description="사용자 분포")


# ============================================
# 장해등급 예측 관련 스키마
# ============================================

class PredictionRequest(BaseModel):
    """장해등급 예측 요청"""
    산업_분류: int = Field(..., ge=1, le=10, description="산업 분류 코드")
    나이: int = Field(..., ge=15, le=100, description="나이")
    성별: int = Field(..., ge=1, le=2, description="1=남성, 2=여성")
    부상_부위: int = Field(..., ge=1, le=20, description="부상 부위 코드")
    부상_종류: int = Field(..., ge=1, le=20, description="부상 종류 코드")
    치료_기간: int = Field(..., ge=1, le=10, description="치료 기간 코드")
    재해유형: int = Field(..., ge=1, le=20, description="재해 유형 코드")
    장해_내용: Optional[str] = Field(None, description="장해 설명 (선택)")

    class Config:
        json_schema_extra = {
            "example": {
                "산업_분류": 2,
                "나이": 45,
                "성별": 1,
                "부상_부위": 1,
                "부상_종류": 1,
                "치료_기간": 3,
                "재해유형": 1,
                "장해_내용": "손가락 절단"
            }
        }


class PredictionResponse(BaseModel):
    """장해등급 예측 응답"""
    predicted_grade: int = Field(..., description="예측된 장해등급 (1~15)")
    cluster: Optional[int] = Field(None, description="소속 클러스터 (0~5)")
    cluster_probabilities: Optional[List[float]] = Field(None, description="각 클러스터 소속 확률")
    cluster_expected: Optional[float] = Field(None, description="클러스터 기대값")
    source: str = Field(..., description="예측 소스 (model/text-exact)")
    message: str = Field(..., description="사용자 메시지")
    error: Optional[str] = Field(None, description="에러 메시지")

    class Config:
        json_schema_extra = {
            "example": {
                "predicted_grade": 12,
                "cluster": 3,
                "cluster_probabilities": [0.1, 0.15, 0.2, 0.35, 0.15, 0.05],
                "cluster_expected": 2.8,
                "source": "model",
                "message": "예측 장해등급: 12급",
                "error": None
            }
        }