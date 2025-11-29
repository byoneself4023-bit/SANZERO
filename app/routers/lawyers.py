"""
SANZERO 노무사 서비스 라우터
노무사 검색, 프로필, 상담 예약 등 노무사 관련 엔드포인트
"""

from fastapi import APIRouter, Request, Form, HTTPException, status, Depends, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional, List
from datetime import datetime
from loguru import logger

from app.models.schemas import (
    LawyerResponse, LawyerCreate, LawyerUpdate, LawyerSearchRequest, LawyerListResponse,
    LawyerMatchRequest, LawyerMatchResponse, ConsultationCreate, ConsultationResponse,
    ConsultationUpdate, SuccessResponse, ErrorResponse
)
from app.services.lawyer_service import LawyerService, ConsultationService
from app.utils.security import get_current_user, require_auth, csrf_middleware, security
from app.utils.database import supabase

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ========================
# 페이지 엔드포인트 (HTML)
# ========================

@router.get("", response_class=HTMLResponse)
async def lawyers_main_page(request: Request):
    """노무사 서비스 메인 페이지"""
    return RedirectResponse(
        url="/lawyers/search",
        status_code=301  # 영구 리다이렉트
    )

@router.get("/search", response_class=HTMLResponse)
async def lawyers_search_page(
    request: Request,
    specialties: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    experience_years_min: Optional[str] = Query(None),
    case_difficulty: Optional[str] = Query(None),
    consultation_fee_max: Optional[str] = Query(None),
    sort: Optional[str] = Query("success_rate"),
    online_consult: Optional[str] = Query(None),
    sanzero_pay: Optional[str] = Query(None),
    free_consult: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    current_user: Optional[dict] = Depends(get_current_user)
):
    """노무사 검색 페이지"""
    try:
        # 검색 파라미터 파싱
        specialty_list = []
        if specialties:
            specialty_list = [s.strip() for s in specialties.split(',')]

        # 숫자 파라미터 안전한 파싱 (빈 문자열 처리)
        def safe_int(value: Optional[str]) -> Optional[int]:
            if not value or value.strip() == "":
                return None
            try:
                return int(value)
            except ValueError:
                return None

        def safe_float(value: Optional[str]) -> Optional[float]:
            if not value or value.strip() == "":
                return None
            try:
                return float(value)
            except ValueError:
                return None

        # 안전하게 파싱된 숫자값들
        experience_years_min_int = safe_int(experience_years_min)
        consultation_fee_max_int = safe_int(consultation_fee_max)

        # 동적 필터 옵션 조회
        available_specialties = await LawyerService.get_unique_specialties()
        available_locations = await LawyerService.get_unique_locations()

        # 노무사 검색
        lawyers, total = await LawyerService.search_lawyers(
            specialties=specialty_list if specialty_list else None,
            location=location,
            experience_years_min=experience_years_min_int,
            case_difficulty=case_difficulty,
            consultation_fee_max=consultation_fee_max_int,
            sort_by=sort,
            is_online_consult=True if online_consult == "true" else None,
            supports_sanzero_pay=True if sanzero_pay == "true" else None,
            free_consult=True if free_consult == "true" else None,
            is_verified=True,
            page=page,
            size=12
        )

        # 페이지네이션 계산
        total_pages = (total + 11) // 12

        return templates.TemplateResponse(
            "pages/lawyers/search.html",
            {
                "request": request,
                "current_user": current_user,
                "lawyers": lawyers,
                "total": total,
                "page": page,
                "total_pages": total_pages,
                "current_specialties": specialties,
                "current_location": location,
                "available_specialties": available_specialties,
                "available_locations": available_locations
            }
        )

    except Exception as e:
        logger.error(f"Error in lawyers search page: {str(e)}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

@router.get("/consultations", response_class=HTMLResponse)
async def consultations_page(
    request: Request,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1)
):
    """내 상담 목록 페이지"""
    try:
        current_user = await require_auth(request)
        if not current_user:
            return RedirectResponse(url="/auth/login", status_code=302)

        # 사용자 타입에 따라 다른 조회
        if current_user.get("user_type") == "lawyer":
            # 노무사인 경우: 본인에게 예약된 상담들 조회
            lawyer = await LawyerService.get_lawyer_by_user_id(current_user["user_id"])
            if lawyer:
                consultations, total = await ConsultationService.get_consultations_by_lawyer(
                    current_user["user_id"], status=status, page=page, size=20
                )
            else:
                consultations, total = [], 0
        else:
            # 일반 사용자인 경우: 본인이 신청한 상담들 조회
            consultations, total = await ConsultationService.get_consultations_by_client(
                current_user["user_id"], status=status, page=page, size=20
            )

        total_pages = (total + 19) // 20

        return templates.TemplateResponse(
            "pages/lawyers/consultations.html",
            {
                "request": request,
                "consultations": consultations,
                "current_user": current_user,
                "total": total,
                "page": page,
                "total_pages": total_pages,
                "current_status": status
            }
        )

    except Exception as e:
        logger.error(f"Error in consultations page: {str(e)}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

@router.get("/{lawyer_id}", response_class=HTMLResponse)
async def lawyer_profile_page(
    request: Request,
    lawyer_id: str,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """노무사 프로필 페이지"""
    try:
        lawyer = await LawyerService.get_lawyer_by_id(lawyer_id, include_user=True)
        if not lawyer:
            raise HTTPException(status_code=404, detail="노무사를 찾을 수 없습니다.")

        current_user = await get_current_user(request)

        return templates.TemplateResponse(
            "pages/lawyers/profile.html",
            {
                "request": request,
                "lawyer": lawyer,
                "current_user": current_user
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in lawyer profile page: {str(e)}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

@router.get("/{lawyer_id}/booking", response_class=HTMLResponse)
@router.get("/booking/{lawyer_id}", response_class=HTMLResponse)
async def consultation_booking_page(request: Request, lawyer_id: str):
    """상담 예약 페이지"""
    try:
        current_user = await get_current_user(request)
        if not current_user:
            return RedirectResponse(url="/auth/login", status_code=302)

        lawyer = await LawyerService.get_lawyer_by_id(lawyer_id, include_user=True)
        if not lawyer or not lawyer.get("is_verified"):
            raise HTTPException(status_code=404, detail="인증된 노무사를 찾을 수 없습니다.")

        # 사용자의 보상금 신청 목록 조회 (상담 연결용)
        applications_result = supabase.table("compensation_applications")\
            .select("id, incident_description, injury_type, created_at")\
            .eq("user_id", current_user["user_id"])\
            .eq("is_active", True)\
            .order("created_at", desc=True)\
            .execute()

        applications = applications_result.data or []

        csrf_token = request.cookies.get("csrf_token", "")

        return templates.TemplateResponse(
            "pages/lawyers/booking.html",
            {
                "request": request,
                "lawyer": lawyer,
                "current_user": current_user,
                "applications": applications,
                "csrf_token": csrf_token
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in consultation booking page: {str(e)}")
        raise HTTPException(status_code=500, detail="서버 오류가 발생했습니다.")

# ========================
# API 엔드포인트 (JSON)
# ========================

@router.get("/api/search", response_model=LawyerListResponse)
async def search_lawyers_api(
    specialties: Optional[List[str]] = Query(None),
    location: Optional[str] = Query(None),
    experience_years_min: Optional[int] = Query(None, ge=0),
    rating_min: Optional[float] = Query(None, ge=0.0, le=5.0),
    consultation_fee_max: Optional[int] = Query(None, ge=0),
    is_verified: bool = Query(True),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """노무사 검색 API"""
    try:
        lawyers, total = await LawyerService.search_lawyers(
            specialties=specialties,
            location=location,
            experience_years_min=experience_years_min,
            rating_min=rating_min,
            consultation_fee_max=consultation_fee_max,
            is_verified=is_verified,
            page=page,
            size=size
        )

        total_pages = (total + size - 1) // size

        return LawyerListResponse(
            lawyers=[LawyerResponse(**lawyer) for lawyer in lawyers],
            total=total,
            page=page,
            size=size,
            pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error in search lawyers API: {str(e)}")
        raise HTTPException(status_code=500, detail="검색 중 오류가 발생했습니다.")

@router.get("/api/match-recommendations/{application_id}")
async def get_lawyer_matches(
    request: Request,
    application_id: str,
    max_results: int = Query(3, ge=1, le=10)
):
    """AI 기반 노무사 매칭 추천"""
    try:
        current_user = await require_auth(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="인증이 필요합니다.")

        # 신청서 소유권 확인
        app_result = supabase.table("compensation_applications")\
            .select("user_id")\
            .eq("id", application_id)\
            .eq("is_active", True)\
            .single()\
            .execute()

        if not app_result.data or app_result.data.get("user_id") != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")

        matches = await LawyerService.find_best_matches(application_id, max_results)

        return {"matches": matches}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in lawyer matching: {str(e)}")
        raise HTTPException(status_code=500, detail="매칭 중 오류가 발생했습니다.")

@router.get("/api/{lawyer_id}/performance-metrics")
async def get_lawyer_performance(lawyer_id: str):
    """노무사 성과 지표 조회"""
    try:
        lawyer = await LawyerService.get_lawyer_by_id(lawyer_id)
        if not lawyer:
            raise HTTPException(status_code=404, detail="노무사를 찾을 수 없습니다.")

        performance_metrics = {
            "success_rate": lawyer.get("success_rate", 0.0),
            "avg_compensation_amount": lawyer.get("avg_compensation_amount", 0),
            "case_count": lawyer.get("case_count", 0),
            "rating": lawyer.get("rating", 0.0),
            "total_reviews": lawyer.get("total_reviews", 0),
            "response_time_hours": lawyer.get("response_time_hours", 24),
            "experience_years": lawyer.get("experience_years", 0),
            "specialties": lawyer.get("specialties", [])
        }

        return performance_metrics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lawyer performance: {str(e)}")
        raise HTTPException(status_code=500, detail="성과 지표 조회 중 오류가 발생했습니다.")

@router.post("/api/consultations")
async def create_consultation_api(
    request: Request,
    lawyer_id: str = Form(...),
    consultation_type: str = Form(...),
    preferred_date: str = Form(...),
    preferred_time: str = Form(...),
    application_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    csrf_token: str = Form(...)
):
    """상담 예약 생성"""
    try:
        # CSRF 토큰 검증
        if not security.verify_csrf_token(request, csrf_token):
            raise HTTPException(status_code=403, detail="CSRF 토큰이 유효하지 않습니다.")

        current_user = await require_auth(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="인증이 필요합니다.")

        # 날짜와 시간 파싱
        try:
            date_str = f"{preferred_date} {preferred_time}:00"
            scheduled_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="올바른 날짜 또는 시간 형식이 아닙니다.")

        # 노무사 정보 조회하여 user_id 가져오기
        lawyer = await LawyerService.get_lawyer_by_id(lawyer_id)
        if not lawyer:
            raise HTTPException(status_code=404, detail="노무사를 찾을 수 없습니다.")

        consultation = await ConsultationService.create_consultation(
            client_id=current_user["user_id"],
            lawyer_id=lawyer["user_id"],  # lawyers.user_id 사용
            consultation_type=consultation_type,
            scheduled_at=scheduled_at,
            application_id=application_id,
            notes=notes
        )

        if consultation:
            return RedirectResponse(
                url=f"/lawyers/consultations?success=true",
                status_code=303
            )
        else:
            raise HTTPException(status_code=400, detail="상담 예약에 실패했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating consultation: {str(e)}")
        raise HTTPException(status_code=500, detail="상담 예약 중 오류가 발생했습니다.")

@router.post("/api/consultations/{consultation_id}/status")
async def update_consultation_status_api(
    request: Request,
    consultation_id: str,
    status: str = Form(...),
    notes: Optional[str] = Form(None),
    csrf_token: str = Form(...)
):
    """상담 상태 업데이트"""
    try:
        # CSRF 토큰 검증
        if not security.verify_csrf_token(request, csrf_token):
            raise HTTPException(status_code=403, detail="CSRF 토큰이 유효하지 않습니다.")

        current_user = await require_auth(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="인증이 필요합니다.")

        consultation = await ConsultationService.update_consultation_status(
            consultation_id=consultation_id,
            user_id=current_user["user_id"],
            status=status,
            notes=notes
        )

        if consultation:
            return RedirectResponse(
                url="/lawyers/consultations?success=status_updated",
                status_code=303
            )
        else:
            raise HTTPException(status_code=400, detail="상태 업데이트에 실패했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating consultation status: {str(e)}")
        raise HTTPException(status_code=500, detail="상태 업데이트 중 오류가 발생했습니다.")

@router.get("/api/{lawyer_id}/availability")
async def get_lawyer_availability(lawyer_id: str):
    """노무사 예약 가능 시간 조회"""
    try:
        lawyer = await LawyerService.get_lawyer_by_id(lawyer_id)
        if not lawyer:
            raise HTTPException(status_code=404, detail="노무사를 찾을 수 없습니다.")

        # 기본 가용성 스케줄 반환 (실제로는 더 복잡한 로직 필요)
        availability = lawyer.get("availability_schedule", {
            "monday": [{"start": "09:00", "end": "18:00"}],
            "tuesday": [{"start": "09:00", "end": "18:00"}],
            "wednesday": [{"start": "09:00", "end": "18:00"}],
            "thursday": [{"start": "09:00", "end": "18:00"}],
            "friday": [{"start": "09:00", "end": "18:00"}],
            "saturday": [],
            "sunday": []
        })

        return {"availability": availability}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lawyer availability: {str(e)}")
        raise HTTPException(status_code=500, detail="가용성 조회 중 오류가 발생했습니다.")

# 관리자 전용 엔드포인트
@router.post("/api/{lawyer_id}/verify")
async def verify_lawyer_api(
    request: Request,
    lawyer_id: str,
    csrf_token: str = Form(...)
):
    """노무사 인증 승인 (관리자 전용)"""
    try:
        # CSRF 토큰 검증
        if not security.verify_csrf_token(request, csrf_token):
            raise HTTPException(status_code=403, detail="CSRF 토큰이 유효하지 않습니다.")

        current_user = await require_auth(request)
        if not current_user or current_user.get("user_type") != "admin":
            raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

        success = await LawyerService.verify_lawyer(lawyer_id, current_user["user_id"])

        if success:
            return {"success": True, "message": "노무사 인증이 승인되었습니다."}
        else:
            raise HTTPException(status_code=400, detail="인증 승인에 실패했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying lawyer: {str(e)}")
        raise HTTPException(status_code=500, detail="인증 승인 중 오류가 발생했습니다.")