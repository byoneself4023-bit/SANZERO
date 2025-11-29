"""
산재 보상금 관련 라우터

보상금 신청, 조회, 수정, 삭제 및 계산기 기능을 제공합니다.
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Dict, Any, Optional
from datetime import datetime, date
import logging

from app.utils.security import get_current_user, require_auth, SecurityManager
from app.services.compensation_service import CompensationService
from app.services.lawyer_service import LawyerService
from app.services.compensation_calculator_service import (
    CompensationCalculatorService,
    SaturdayWorkType,
    CompensationStandards
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
async def compensation_main(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """보상금 서비스 - 바로 계산기로 리다이렉트"""
    return RedirectResponse(
        url="/compensation/calculator",
        status_code=301  # 영구 리다이렉트
    )


@router.get("/calculator", response_class=HTMLResponse)
async def compensation_calculator(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """보상금 계산기 페이지"""
    csrf_token = SecurityManager.generate_csrf_token()

    return templates.TemplateResponse("pages/compensation/calculator.html", {
        "request": request,
        "current_user": current_user,
        "csrf_token": csrf_token,
        "standards": {
            "min_daily": CompensationStandards.MIN_DAILY_AMOUNT,
            "max_daily": CompensationStandards.MAX_DAILY_AMOUNT,
            "min_wage_daily": CompensationStandards.MIN_WAGE_DAILY,
            "year": 2025
        }
    })


@router.get("/calculate", response_class=HTMLResponse)
async def compensation_calculate_page(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """보상금 계산 페이지 (계산기 페이지로 리다이렉트)"""
    return RedirectResponse(
        url="/compensation/calculator",
        status_code=301  # 영구 리다이렉트
    )


@router.post("/calculate")
async def calculate_compensation(
    request: Request,
    csrf_token: str = Form(...),
    wage_method: str = Form(...),
    wage_amount: str = Form("0"),  # 문자열로 받아서 콤마 제거 후 변환
    saturday_type: str = Form("no_pay"),
    calculation_date: str = Form(...),
    disability_grade: Optional[str] = Form(None),
    survivors_count: int = Form(1),
    apply_limits: bool = Form(True),
    injury_type: Optional[str] = Form("기타"),  # 부상 유형 추가
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """보상금 계산 API"""
    try:
        # CSRF 토큰 검증 (헤더와 폼 데이터 모두 확인)
        csrf_from_header = request.headers.get('X-CSRFToken')
        csrf_from_form = csrf_token

        if not (SecurityManager.verify_csrf_token(request, csrf_from_form) or
                SecurityManager.verify_csrf_token(request, csrf_from_header)):
            raise HTTPException(status_code=403, detail="보안 토큰 검증 실패")

        # 급여 금액에서 콤마 제거 후 정수 변환
        try:
            wage_amount_int = int(wage_amount.replace(",", "")) if wage_amount else 0
        except (ValueError, AttributeError):
            wage_amount_int = 0

        # 입력값 검증
        is_valid, error_message = CompensationCalculatorService.validate_calculation_input(
            wage_method, wage_amount_int, calculation_date, saturday_type
        )

        if not is_valid:
            return JSONResponse(
                status_code=400,
                content={"error": error_message}
            )

        # 통상임금 계산
        saturday_work_type = SaturdayWorkType(saturday_type)
        wage_result = CompensationCalculatorService.calculate_regular_wage(
            wage_method, wage_amount_int, saturday_work_type
        )

        # 일 평균임금 (통상임금과 동일하게 처리)
        daily_wage = wage_result["daily_wage"]

        if daily_wage <= 0 and wage_method != "skip":
            return JSONResponse(
                status_code=400,
                content={"error": "유효한 통상임금을 입력해주세요."}
            )

        # 계산 기준일
        calc_date = datetime.strptime(calculation_date, "%Y-%m-%d").date()

        # 모든 보상금 계산
        compensation_result = CompensationCalculatorService.calculate_all_benefits(
            daily_wage,
            calc_date,
            disability_grade,
            survivors_count,
            apply_limits
        )

        # 부상 유형 기반 노무사 추천
        recommended_lawyers = []
        if injury_type and injury_type != "기타":
            try:
                recommended_lawyers = await LawyerService.get_recommended_lawyers_by_injury_type(
                    injury_type, max_results=3
                )
            except Exception as e:
                logger.warning(f"Failed to get recommended lawyers: {str(e)}")

        # 결과 조합
        result = {
            "wage_calculation": wage_result,
            "compensation_calculation": compensation_result,
            "recommended_lawyers": recommended_lawyers,
            "injury_type": injury_type,
            "calculation_metadata": {
                "calculated_at": datetime.now().isoformat(),
                "user_id": current_user["user_id"],
                "version": "2025.1.0"
            }
        }

        # HTMX 요청인지 확인
        accept_header = request.headers.get("accept", "")
        hx_request = request.headers.get("hx-request", "")

        if "text/html" in accept_header or hx_request:
            # HTMX 응답용 템플릿 렌더링
            return templates.TemplateResponse("components/calculation_result.html", {
                "request": request,
                "result": result
            })
        else:
            # JSON 응답
            return JSONResponse(content=result)

    except ValueError as ve:
        return JSONResponse(
            status_code=400,
            content={"error": str(ve)}
        )
    except Exception as e:
        logger.error(f"계산 중 오류 발생: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"계산 중 오류가 발생했습니다: {str(e)}"}
        )


@router.get("/apply", response_class=HTMLResponse)
async def application_form(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """보상금 신청 - 계산기 페이지로 리다이렉트"""
    return RedirectResponse(
        url="/compensation/calculator",
        status_code=301  # 영구 리다이렉트
    )


@router.post("/apply")
async def create_application_form(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """보상금 신청 - 계산기 페이지로 리다이렉트"""
    return RedirectResponse(
        url="/compensation/calculator",
        status_code=303
    )


@router.get("/status", response_class=HTMLResponse)
async def application_status(
    request: Request,
    status: str = Query("all", pattern="^(all|pending|approved|rejected|reviewing)$"),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """신청 현황 조회 페이지"""
    try:
        # 상태 필터 처리
        status_filter = None if status == "all" else status

        # 사용자의 신청서 목록 조회
        applications = await CompensationService.get_applications_by_user(
            current_user["user_id"],
            status_filter=status_filter,
            limit=50
        )

        return templates.TemplateResponse("pages/compensation/status.html", {
            "request": request,
            "current_user": current_user,
            "applications": applications,
            "current_status": status
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 로드 오류: {str(e)}")


@router.get("/{application_id}", response_class=HTMLResponse)
async def application_detail(
    request: Request,
    application_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """신청서 상세 페이지"""
    try:
        application = await CompensationService.get_application_by_id(
            application_id, current_user
        )

        if not application:
            raise HTTPException(status_code=404, detail="신청서를 찾을 수 없습니다.")

        csrf_token = SecurityManager.generate_csrf_token()

        return templates.TemplateResponse("pages/compensation/detail.html", {
            "request": request,
            "current_user": current_user,
            "application": application,
            "csrf_token": csrf_token
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 로드 오류: {str(e)}")


@router.get("/{application_id}/edit", response_class=HTMLResponse)
async def edit_application_form(
    request: Request,
    application_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """신청서 수정 폼 페이지"""
    try:
        application = await CompensationService.get_application_by_id(
            application_id, current_user
        )

        if not application:
            raise HTTPException(status_code=404, detail="신청서를 찾을 수 없습니다.")

        if application["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="대기 중인 신청서만 수정할 수 있습니다."
            )

        csrf_token = SecurityManager.generate_csrf_token()

        return templates.TemplateResponse("pages/compensation/edit.html", {
            "request": request,
            "current_user": current_user,
            "application": application,
            "csrf_token": csrf_token
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"페이지 로드 오류: {str(e)}")


@router.post("/{application_id}/edit")
async def update_application_form(
    request: Request,
    application_id: str,
    csrf_token: str = Form(...),
    incident_location: str = Form(...),
    incident_description: str = Form(...),
    injury_type: str = Form(...),
    severity_level: str = Form(...),
    # 의료 정보 (선택사항)
    hospital_name: str = Form(""),
    diagnosis: str = Form(""),
    treatment_period: str = Form(""),
    medical_cost: int = Form(0),
    # 급여 정보 (선택사항)
    base_salary: int = Form(0),
    monthly_bonus: int = Form(0),
    annual_salary: int = Form(0),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """신청서 수정 처리"""
    try:
        # CSRF 토큰 검증
        if not SecurityManager.verify_csrf_token(request, csrf_token):
            raise HTTPException(status_code=403, detail="보안 토큰 검증 실패")

        # 수정 데이터 구성
        update_data = {
            "incident_location": incident_location,
            "incident_description": incident_description,
            "injury_type": injury_type,
            "severity_level": severity_level,
            "medical_records": {
                "hospital": hospital_name,
                "diagnosis": diagnosis,
                "treatment_period": treatment_period,
                "medical_cost": medical_cost
            },
            "salary_info": {
                "base_salary": base_salary,
                "monthly_bonus": monthly_bonus,
                "annual_salary": annual_salary
            }
        }

        # 신청서 수정
        updated_application = await CompensationService.update_application(
            application_id, update_data, current_user
        )

        if updated_application:
            return RedirectResponse(
                url=f"/compensation/{application_id}",
                status_code=303
            )
        else:
            raise HTTPException(status_code=400, detail="수정에 실패했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"수정 처리 오류: {str(e)}")


@router.post("/{application_id}/delete")
async def delete_application_form(
    request: Request,
    application_id: str,
    csrf_token: str = Form(...),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """신청서 삭제 처리"""
    try:
        # CSRF 토큰 검증
        if not SecurityManager.verify_csrf_token(request, csrf_token):
            raise HTTPException(status_code=403, detail="보안 토큰 검증 실패")

        # 신청서 삭제
        success = await CompensationService.delete_application(
            application_id, current_user
        )

        if success:
            return RedirectResponse(
                url="/compensation/status",
                status_code=303
            )
        else:
            raise HTTPException(status_code=400, detail="삭제에 실패했습니다.")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 처리 오류: {str(e)}")


# API 엔드포인트들
@router.get("/api/standards/{year}")
async def get_compensation_standards(
    year: int,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """연도별 보상 기준 조회 API"""
    if year != 2025:
        raise HTTPException(status_code=400, detail="2025년 기준만 지원됩니다.")

    return JSONResponse(content={
        "year": 2025,
        "min_daily_amount": CompensationStandards.MIN_DAILY_AMOUNT,
        "max_daily_amount": CompensationStandards.MAX_DAILY_AMOUNT,
        "min_wage_hourly": CompensationStandards.MIN_WAGE_HOURLY,
        "min_wage_daily": CompensationStandards.MIN_WAGE_DAILY,
        "min_wage_monthly": CompensationStandards.MIN_WAGE_MONTHLY,
        "survivor_base_rate": CompensationStandards.SURVIVOR_BASE_RATE,
        "updated_at": "2025-01-01"
    })


@router.get("/api/applications")
async def get_user_applications_api(
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """사용자 신청서 목록 API"""
    try:
        applications = await CompensationService.get_applications_by_user(
            current_user["user_id"],
            status_filter=status,
            limit=limit,
            offset=offset
        )

        return JSONResponse(content={
            "applications": applications,
            "total": len(applications),
            "limit": limit,
            "offset": offset
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 오류: {str(e)}")


@router.get("/api/applications/{application_id}")
async def get_application_api(
    application_id: str,
    current_user: Dict[str, Any] = Depends(require_auth)
):
    """신청서 상세 정보 API"""
    try:
        application = await CompensationService.get_application_by_id(
            application_id, current_user
        )

        if not application:
            raise HTTPException(status_code=404, detail="신청서를 찾을 수 없습니다.")

        return JSONResponse(content=application)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"조회 오류: {str(e)}")