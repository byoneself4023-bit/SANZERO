"""
관리자 라우터
관리자 대시보드, 사용자 관리, AI 서비스 통계
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from app.utils.security import get_current_user
from app.services.admin_service import AdminService

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def require_admin(request: Request):
    """관리자 권한 검증 미들웨어"""
    current_user = await get_current_user(request)

    if not current_user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    if current_user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    return current_user


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: dict = Depends(require_admin)):
    """
    관리자 대시보드
    4가지 핵심 AI 서비스 통계 표시
    """
    # 대시보드 통계 조회
    stats = await AdminService.get_dashboard_stats()

    return templates.TemplateResponse(
        "pages/admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": stats
        }
    )


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    user_type: Optional[str] = "all",
    page: int = 1,
    current_user: dict = Depends(require_admin)
):
    """
    사용자 관리 페이지
    """
    limit = 20
    offset = (page - 1) * limit

    # 사용자 목록 조회
    result = await AdminService.get_all_users(
        user_type=user_type if user_type != "all" else None,
        limit=limit,
        offset=offset
    )

    total_pages = (result["total"] + limit - 1) // limit

    return templates.TemplateResponse(
        "pages/admin/users.html",
        {
            "request": request,
            "current_user": current_user,
            "users": result["data"],
            "total": result["total"],
            "current_user_type": user_type,
            "page": page,
            "total_pages": total_pages
        }
    )


@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    request: Request,
    user_id: str,
    is_active: bool = Form(...),
    current_user: dict = Depends(require_admin)
):
    """
    사용자 활성화/비활성화
    """
    try:
        await AdminService.toggle_user_status(user_id=user_id, is_active=is_active)

        return RedirectResponse(
            url="/admin/users?message=사용자 상태가 변경되었습니다",
            status_code=303
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 변경 중 오류가 발생했습니다: {str(e)}")