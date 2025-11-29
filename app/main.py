"""
SANZERO - AI 기반 산업재해 보상 서비스 플랫폼
메인 FastAPI 애플리케이션
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import os
from pathlib import Path

# 라우터 임포트
from app.routers import auth

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv()

# 로깅 시스템 초기화
from app.utils.logging_config import setup_logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))

# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title="SANZERO",
    description="AI 기반 산업재해 보상 서비스 플랫폼",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") == "development" else None
)

# 정적 파일 및 템플릿 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8000", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CSRF 보호 미들웨어 추가
from app.utils.security import security, set_csrf_cookie

@app.middleware("http")
async def csrf_token_middleware(request: Request, call_next):
    """CSRF 토큰 자동 설정 미들웨어"""
    # 기존 CSRF 토큰 확인
    existing_token = request.cookies.get("csrf_token")

    # 요청 처리
    response = await call_next(request)

    # HTML 응답이고 CSRF 토큰이 없는 경우에만 새 토큰 생성
    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type and not existing_token:
        csrf_token = security.generate_csrf_token()
        set_csrf_cookie(response, csrf_token)
        # 생성된 토큰을 응답 헤더에도 추가 (디버깅용)
        response.headers["X-CSRF-Token"] = csrf_token

    return response

# TrustedHostMiddleware - 프로덕션 환경에서는 실제 도메인으로 제한
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # 테스트를 위해 모든 호스트 허용, 프로덕션에서는 실제 도메인으로 변경
    )

# 라우터 등록
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# 관리자 라우터
from app.routers import admin
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

# 노무사 서비스 라우터
from app.routers import lawyers
app.include_router(lawyers.router, prefix="/lawyers", tags=["Lawyers"])

# 보상금 서비스 라우터
from app.routers import compensation
app.include_router(compensation.router, prefix="/compensation", tags=["Compensation"])

# AI 분석 서비스 라우터 (Phase 2) - 의존성이 설치된 경우에만 활성화
try:
    from app.routers import analysis
    app.include_router(analysis.router, prefix="/analysis", tags=["AI Analysis"])
    print("✅ AI 분석 서비스가 활성화되었습니다.")
except ImportError as e:
    print(f"⚠️  AI 분석 서비스를 비활성화했습니다: {e}")



# 메인 페이지 라우트
@app.get("/")
async def root(request: Request):
    """메인 대시보드 페이지"""
    from app.utils.security import get_current_user
    from app.services.admin_service import AdminService

    current_user = await get_current_user(request)

    # 관리자인 경우 관리자 대시보드 표시
    if current_user and current_user.get("user_type") == "admin":
        # 대시보드 통계 조회 (4가지 핵심 AI 서비스 통계)
        stats = await AdminService.get_dashboard_stats()

        return templates.TemplateResponse(
            "pages/admin/dashboard.html",
            {
                "request": request,
                "current_user": current_user,
                "stats": stats
            }
        )

    # 일반 사용자는 일반 대시보드
    return templates.TemplateResponse(
        "pages/dashboard.html",
        {
            "request": request,
            "title": "SANZERO - 산업재해 보상 서비스",
            "current_user": current_user
        }
    )

# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """시스템 상태 확인"""
    return {"status": "healthy", "service": "sanzero"}

# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화 작업"""
    print("🚀 SANZERO 서비스가 시작되었습니다.")
    print("📊 대시보드: http://localhost:8000")

    # 데이터베이스 연결 테스트 (Docker 환경에서는 401 에러 발생하므로 건너뜀)
    # REST API는 호스트에서는 작동하지만 Docker 컨테이너 내부에서는 Supabase 제한으로 401 발생
    print("ℹ️  데이터베이스 연결 테스트 생략 (Docker 네트워크 제한)")

    # analysis_requests 테이블 자동 생성
    try:
        from app.utils.database import create_analysis_requests_table
        await create_analysis_requests_table()
        print("✅ analysis_requests 테이블 설정 완료")
    except Exception as e:
        print(f"⚠️  analysis_requests 테이블 설정 실패: {e}")

    print("🎯 테스트 계정:")
    print("   관리자: byoneself4023@ajou.ac.kr / rlarlduf0")
    print("   일반사용자: testuser@example.com / test123456!")
    print("   노무사: lawyer@example.com / lawyer123456!")

# 애플리케이션 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 정리 작업"""

    print("🛑 SANZERO 서비스가 종료되었습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )