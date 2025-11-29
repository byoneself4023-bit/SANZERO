"""
SANZERO 보안 유틸리티
인증, 암호화, CSRF 보호 등
"""

import hashlib
import secrets
import bleach
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request, Response
from app.utils.config import settings
import re

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 허용된 HTML 태그 및 속성 (최소한으로 제한)
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li']
ALLOWED_ATTRIBUTES = {}

class SecurityManager:
    """보안 관리 클래스"""

    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """JWT 액세스 토큰 생성"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.session_secret, algorithm=settings.jwt_algorithm)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(token, settings.session_secret, algorithms=[settings.jwt_algorithm])
            return payload
        except JWTError:
            return None

    @staticmethod
    def generate_csrf_token() -> str:
        """CSRF 토큰 생성"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def verify_csrf_token(request: Request, form_token: Optional[str] = None) -> bool:
        """CSRF 토큰 검증 (헤더 및 Form 데이터 지원)"""
        cookie_token = request.cookies.get("csrf_token")
        if not cookie_token:
            return False

        # Form 데이터에서 토큰 확인 (일반 폼 제출)
        if form_token:
            return secrets.compare_digest(cookie_token, form_token)

        # 헤더에서 토큰 확인 (HTMX 요청)
        header_token = request.headers.get("X-CSRFToken") or request.headers.get("X-CSRF-Token")
        if header_token:
            return secrets.compare_digest(cookie_token, header_token)

        # 토큰이 전혀 없으면 실패
        return False

    @staticmethod
    def sanitize_html(text: str) -> str:
        """HTML 새니타이징"""
        if not text:
            return ""
        return bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)

    @staticmethod
    def sanitize_text(text: str) -> str:
        """텍스트 새니타이징 (HTML 태그 완전 제거)"""
        if not text:
            return ""
        return bleach.clean(text, tags=[], attributes={}, strip=True)

    @staticmethod
    def validate_email(email: str) -> bool:
        """이메일 주소 유효성 검증"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_password_strength(password: str) -> tuple[bool, str]:
        """비밀번호 강도 검증"""
        if len(password) < 8:
            return False, "비밀번호는 최소 8자 이상이어야 합니다."

        if not re.search(r'[A-Za-z]', password):
            return False, "비밀번호에는 영문자가 포함되어야 합니다."

        if not re.search(r'\d', password):
            return False, "비밀번호에는 숫자가 포함되어야 합니다."

        # 특수문자 포함 (선택사항)
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "비밀번호에는 특수문자가 포함되어야 합니다."

        return True, "비밀번호가 유효합니다."

    @staticmethod
    def mask_sensitive_data(text: str, mask_char: str = "*") -> str:
        """민감한 데이터 마스킹"""
        if not text or len(text) <= 4:
            return mask_char * len(text) if text else ""

        # 앞 2자리와 뒤 2자리만 보여주고 나머지는 마스킹
        return text[:2] + mask_char * (len(text) - 4) + text[-2:]

    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """민감한 데이터 해싱 (로깅용)"""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

# CSRF 미들웨어
class CSRFMiddleware:
    """CSRF 보호 미들웨어"""

    def __init__(self, exempt_paths: list = None):
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
            "/auth/login",
            "/auth/signup",
            "/auth/refresh"
        ]

    def is_exempt(self, path: str) -> bool:
        """CSRF 검증 제외 경로인지 확인"""
        return any(path.startswith(exempt_path) for exempt_path in self.exempt_paths)

    def should_verify_csrf(self, request: Request) -> bool:
        """CSRF 검증이 필요한지 확인"""
        # GET, HEAD, OPTIONS 요청은 제외
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return False

        # 제외 경로 확인
        if self.is_exempt(request.url.path):
            return False

        return True

# 전역 보안 관리자 인스턴스
security = SecurityManager()
csrf_middleware = CSRFMiddleware()

# 인증 의존성
async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """현재 로그인된 사용자 정보 가져오기"""
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = security.verify_token(token)
    if not payload:
        return None

    return payload

async def require_auth(request: Request) -> Dict[str, Any]:
    """인증 필수 의존성"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def require_admin(request: Request) -> Dict[str, Any]:
    """관리자 권한 필수 의존성"""
    user = await require_auth(request)
    if user.get("user_type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return user

async def require_lawyer(request: Request) -> Dict[str, Any]:
    """노무사 권한 필수 의존성"""
    user = await require_auth(request)
    if user.get("user_type") not in ["lawyer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="노무사 권한이 필요합니다."
        )
    return user

# 쿠키 설정 헬퍼
def set_auth_cookie(response: Response, token: str):
    """인증 쿠키 설정"""
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60
    )

def set_csrf_cookie(response: Response, token: str):
    """CSRF 쿠키 설정"""
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # JavaScript에서 접근 가능해야 함
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=60 * 60 * 24  # 24시간
    )

def clear_auth_cookies(response: Response):
    """인증 관련 쿠키 삭제"""
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")