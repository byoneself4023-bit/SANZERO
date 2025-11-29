"""
SANZERO 설정 관리
환경변수 및 설정값 중앙 관리
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """앱 설정 클래스"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    # 앱 기본 설정
    app_name: str = "SANZERO"
    app_version: str = "1.0.0"
    environment: str = "production"
    debug: bool = False

    # Supabase 설정
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # 세션 및 보안 설정
    session_secret: str = "sanzero-session-secret"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # JWT 설정
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24시간

    # CORS 설정
    allowed_origins: list = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:80",
        "http://127.0.0.1:8000"
    ]

    # 파일 업로드 설정
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]

    # AI 설정
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    ai_model: str = "gpt-4-turbo-preview"
    ai_max_tokens: int = 4000
    ai_temperature: float = 0.1

    # 임베딩 모델 설정
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # 데이터베이스 설정
    db_pool_size: int = 20
    db_max_overflow: int = 30

    # 로깅 설정
    log_level: str = "INFO"
    log_format: str = "<green>{time}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# 설정 인스턴스 생성
settings = Settings()

# 설정 검증
def validate_settings():
    """필수 설정값 검증"""
    errors = []

    if not settings.supabase_url:
        errors.append("SUPABASE_URL이 설정되지 않았습니다.")

    if not settings.supabase_anon_key:
        errors.append("SUPABASE_ANON_KEY가 설정되지 않았습니다.")

    if not settings.supabase_service_role_key:
        errors.append("SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다.")

    if not settings.session_secret:
        errors.append("SESSION_SECRET이 설정되지 않았습니다.")

    if errors:
        error_msg = "\n".join(errors)
        raise ValueError(f"설정 오류:\n{error_msg}")

    return True

# 환경별 설정
def get_database_url() -> str:
    """데이터베이스 URL 반환"""
    return settings.supabase_url

def get_cors_origins() -> list:
    """CORS 허용 도메인 반환"""
    if settings.environment == "development":
        return settings.allowed_origins + ["http://localhost:3000"]
    return settings.allowed_origins

def is_development() -> bool:
    """개발 환경 여부 확인"""
    return settings.environment == "development"

def is_production() -> bool:
    """프로덕션 환경 여부 확인"""
    return settings.environment == "production"