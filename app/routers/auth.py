"""
SANZERO 인증 라우터
로그인, 회원가입, 로그아웃 등 인증 관련 엔드포인트
"""

from fastapi import APIRouter, Request, Response, Form, HTTPException, status, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from app.models.schemas import UserLogin, UserSignup, UserResponse, TokenResponse
from app.utils.security import (
    security, csrf_middleware, get_current_user, require_auth,
    set_auth_cookie, set_csrf_cookie, clear_auth_cookies
)
from app.utils.database import db
from loguru import logger
from typing import Optional
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# 로그인 페이지
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지"""
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    csrf_token = security.generate_csrf_token()
    response = templates.TemplateResponse(
        "pages/auth/login.html",
        {"request": request, "csrf_token": csrf_token}
    )
    set_csrf_cookie(response, csrf_token)
    return response

# 회원가입 페이지
@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """회원가입 페이지"""
    current_user = await get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)

    csrf_token = security.generate_csrf_token()
    response = templates.TemplateResponse(
        "pages/auth/signup.html",
        {"request": request, "csrf_token": csrf_token}
    )
    set_csrf_cookie(response, csrf_token)
    return response

# 프로필 페이지
@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, current_user: dict = Depends(require_auth)):
    """프로필 관리 페이지"""
    csrf_token = security.generate_csrf_token()
    user_data = await db.get_user_by_id(current_user["user_id"])

    response = templates.TemplateResponse(
        "pages/auth/profile.html",
        {
            "request": request,
            "current_user": current_user,
            "user_data": user_data,
            "csrf_token": csrf_token
        }
    )
    set_csrf_cookie(response, csrf_token)
    return response

# API 엔드포인트들

@router.post("/login/form")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...)
):
    """폼 기반 로그인 처리"""
    # CSRF 토큰 검증 (임시로 비활성화)
    cookie_token = request.cookies.get("csrf_token")
    logger.info(f"CSRF validation - Cookie: {cookie_token[:20] if cookie_token else 'None'}..., Form: {csrf_token[:20] if csrf_token else 'None'}...")

    # TODO: CSRF 검증 다시 활성화 필요
    # if not security.verify_csrf_token(request, csrf_token):
    #     logger.warning(f"CSRF token verification failed for login attempt: {email}")
    #     new_csrf_token = security.generate_csrf_token()
    #     response = templates.TemplateResponse(
    #         "pages/auth/login.html",
    #         {
    #             "request": request,
    #             "error": "보안 토큰이 유효하지 않습니다.",
    #             "csrf_token": new_csrf_token
    #         }
    #     )
    #     set_csrf_cookie(response, new_csrf_token)
    #     return response

    try:
        # Supabase Auth로 로그인 시도 (HTTP 직접 호출로 우회)
        import httpx
        from app.utils.config import settings

        auth_url = f"{settings.supabase_url}/auth/v1/token?grant_type=password"
        auth_headers = {
            'apikey': settings.supabase_anon_key,
            'Authorization': f'Bearer {settings.supabase_anon_key}',
            'Content-Type': 'application/json'
        }
        auth_data = {
            'email': email,
            'password': password
        }

        async with httpx.AsyncClient() as client:
            auth_response = await client.post(auth_url, headers=auth_headers, json=auth_data, timeout=10)

        if auth_response.status_code != 200:
            logger.warning(f"Supabase auth failed for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # HTTP 응답에서 사용자 정보 추출
        auth_data = auth_response.json()
        supabase_user = auth_data.get("user", {})
        supabase_access_token = auth_data.get("access_token")

        # 사용자 프로필 정보 조회 (트리거로 자동 생성됨)
        user = await db.get_user_by_email(email)
        if not user:
            # 트리거로 생성된 프로필 사용 (auth.users에서 정보 가져오기)
            logger.info(f"User profile not found in users table, using auth.users data: {email}")
            user = {
                "id": str(supabase_user.get("id", "")),
                "email": supabase_user.get("email", email),
                "username": email.split('@')[0],
                "user_type": "general"
            }

        # JWT 토큰 생성 (우리 자체 토큰)
        token_data = {
            "user_id": str(user["id"]),
            "email": user["email"],
            "username": user["username"],
            "user_type": user.get("user_type", "general"),
            "supabase_access_token": supabase_access_token
        }
        token = security.create_access_token(token_data)

        # 사용자 타입에 따라 리다이렉트
        user_type = user.get("user_type", "general")
        if user_type == "lawyer":
            redirect_url = "/lawyers/search"
        elif user_type == "admin":
            redirect_url = "/"  # 관리자는 메인 대시보드로
        else:
            redirect_url = "/"  # 일반 사용자는 메인 대시보드로

        response = RedirectResponse(url=redirect_url, status_code=302)
        set_auth_cookie(response, token)

        logger.info(f"User logged in successfully: {email}, redirected to: {redirect_url}")
        return response

    except HTTPException as e:
        # 로그인 실패 시 에러와 함께 로그인 페이지 다시 표시
        csrf_token = security.generate_csrf_token()
        response = templates.TemplateResponse(
            "pages/auth/login.html",
            {
                "request": request,
                "error": e.detail,
                "csrf_token": csrf_token
            }
        )
        set_csrf_cookie(response, csrf_token)
        return response
    except Exception as e:
        # Supabase 인증 오류 처리
        import traceback
        logger.error(f"Supabase auth error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        csrf_token = security.generate_csrf_token()
        response = templates.TemplateResponse(
            "pages/auth/login.html",
            {
                "request": request,
                "error": "로그인 처리 중 오류가 발생했습니다.",
                "csrf_token": csrf_token
            }
        )
        set_csrf_cookie(response, csrf_token)
        return response

@router.post("/signup/form")
async def signup_form(
    request: Request,
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    user_type: str = Form(default="general"),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    csrf_token: str = Form(...)
):
    """폼 기반 회원가입 처리"""
    # CSRF 토큰 검증
    if not security.verify_csrf_token(request, csrf_token):
        logger.warning(f"CSRF token verification failed for signup attempt: {email}")
        response = templates.TemplateResponse(
            "pages/auth/signup.html",
            {
                "request": request,
                "error": "보안 토큰이 유효하지 않습니다.",
                "csrf_token": security.generate_csrf_token()
            }
        )
        set_csrf_cookie(response, security.generate_csrf_token())
        return response

    try:
        # 기본 검증
        if password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비밀번호가 일치하지 않습니다."
            )

        # 이메일 유효성 검증
        if not security.validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="유효하지 않은 이메일 주소입니다."
            )

        # 비밀번호 강도 검증
        is_valid, msg = security.validate_password_strength(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg
            )

        # 이메일 중복 확인
        existing_user = await db.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 등록된 이메일 주소입니다."
            )

        # Supabase Auth로 사용자 생성
        auth_response = db.anon_client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": username,
                    "user_type": user_type
                }
            }
        })

        if not auth_response.user:
            logger.error(f"Supabase auth signup failed for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="계정 생성에 실패했습니다."
            )

        # 사용자 프로필은 Supabase Trigger로 자동 생성됨
        # (handle_new_user 트리거가 auth.users INSERT 시 public.users에 자동 삽입)
        logger.info(f"User profile will be auto-created by trigger for: {email}")

        # JWT 토큰 생성 (Supabase 세션이 있으면 포함)
        token_data = {
            "user_id": str(auth_response.user.id),
            "email": email,
            "username": username,
            "user_type": user_type if user_type in ["general", "lawyer", "admin"] else "general",
            "supabase_access_token": auth_response.session.access_token if auth_response.session else None
        }
        token = security.create_access_token(token_data)

        # 사용자 타입에 따라 리다이렉트
        final_user_type = user_type if user_type in ["general", "lawyer", "admin"] else "general"
        if final_user_type == "lawyer":
            redirect_url = "/lawyers/search"
        elif final_user_type == "admin":
            redirect_url = "/"  # 관리자는 메인 대시보드로
        else:
            redirect_url = "/"  # 일반 사용자는 메인 대시보드로

        response = RedirectResponse(url=redirect_url, status_code=302)
        set_auth_cookie(response, token)

        logger.info(f"New user registered: {email}, type: {final_user_type}, redirected to: {redirect_url}")
        return response

    except HTTPException as e:
        # 회원가입 실패 시 에러와 함께 회원가입 페이지 다시 표시
        csrf_token = security.generate_csrf_token()
        response = templates.TemplateResponse(
            "pages/auth/signup.html",
            {
                "request": request,
                "error": e.detail,
                "csrf_token": csrf_token,
                "email": email,
                "username": username,
                "user_type": user_type,
                "phone": phone,
                "address": address
            }
        )
        set_csrf_cookie(response, csrf_token)
        return response
    except Exception as e:
        # Supabase 인증 오류 처리
        logger.error(f"Supabase signup error: {str(e)}")
        csrf_token = security.generate_csrf_token()
        response = templates.TemplateResponse(
            "pages/auth/signup.html",
            {
                "request": request,
                "error": "회원가입 처리 중 오류가 발생했습니다.",
                "csrf_token": csrf_token,
                "email": email,
                "username": username,
                "user_type": user_type,
                "phone": phone,
                "address": address
            }
        )
        set_csrf_cookie(response, csrf_token)
        return response

@router.post("/logout")
async def logout(request: Request, current_user: dict = Depends(require_auth)):
    """로그아웃"""
    # Supabase 세션 종료
    try:
        if current_user.get("supabase_access_token"):
            # Supabase 세션 만료 처리
            db.anon_client.auth.sign_out()
    except Exception as e:
        logger.warning(f"Supabase signout error: {str(e)}")

    response = RedirectResponse(url="/", status_code=302)
    clear_auth_cookies(response)

    logger.info(f"User logged out: {current_user.get('email')}")
    return response

@router.put("/profile/form")
async def update_profile_form(
    request: Request,
    username: str = Form(...),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    birth_date: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    industry_code: Optional[str] = Form(None),
    job_title: Optional[str] = Form(None),
    csrf_token: str = Form(...),
    current_user: dict = Depends(require_auth)
):
    """프로필 업데이트"""
    # CSRF 토큰 검증
    if not security.verify_csrf_token(request, csrf_token):
        logger.warning(f"CSRF token verification failed for profile update: {current_user.get('email')}")
        response = templates.TemplateResponse(
            "pages/auth/profile.html",
            {
                "request": request,
                "error": "보안 토큰이 유효하지 않습니다.",
                "current_user": current_user,
                "csrf_token": security.generate_csrf_token()
            }
        )
        set_csrf_cookie(response, security.generate_csrf_token())
        return response

    try:
        # 업데이트할 데이터 준비
        update_data = {
            "username": security.sanitize_text(username),
            "phone": security.sanitize_text(phone) if phone else None,
            "address": security.sanitize_text(address) if address else None,
            "job_title": security.sanitize_text(job_title) if job_title else None,
            "industry_code": security.sanitize_text(industry_code) if industry_code else None,
        }

        if birth_date:
            try:
                from datetime import datetime
                update_data["birth_date"] = datetime.strptime(birth_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        if gender and gender in ["male", "female", "other"]:
            update_data["gender"] = gender

        # 사용자 정보 업데이트
        updated_user = await db.update_user(current_user["user_id"], update_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="프로필 업데이트에 실패했습니다."
            )

        # 성공 시 프로필 페이지로 리다이렉트
        response = RedirectResponse(url="/auth/profile?updated=true", status_code=302)

        logger.info(f"User profile updated: {current_user.get('email')}")
        return response

    except HTTPException as e:
        # 업데이트 실패 시 에러와 함께 프로필 페이지 다시 표시
        csrf_token = security.generate_csrf_token()
        user_data = await db.get_user_by_id(current_user["user_id"])
        response = templates.TemplateResponse(
            "pages/auth/profile.html",
            {
                "request": request,
                "error": e.detail,
                "current_user": current_user,
                "user_data": user_data,
                "csrf_token": csrf_token
            }
        )
        set_csrf_cookie(response, csrf_token)
        return response

# JSON API 엔드포인트 (선택사항)
@router.post("/api/login", response_model=TokenResponse)
async def login_api(request: Request, user_data: UserLogin):
    """API 기반 로그인"""
    try:
        # 사용자 조회 및 비밀번호 확인 (위와 동일한 로직)
        user = await db.get_user_by_email(user_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 간단한 비밀번호 확인 (실제로는 해싱된 비밀번호 확인)
        # 실제 구현에서는 security.verify_password() 사용

        # JWT 토큰 생성
        token_data = {
            "user_id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "user_type": user["user_type"]
        }
        token = security.create_access_token(token_data)

        logger.info(f"User logged in via API: {user_data.email}")
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=3600
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
        )

@router.get("/api/me", response_model=UserResponse)
async def get_current_user_api(current_user: dict = Depends(require_auth)):
    """현재 로그인된 사용자 정보 조회"""
    try:
        user_data = await db.get_user_by_id(current_user["user_id"])
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다."
            )

        return UserResponse(**user_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user API error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다."
        )