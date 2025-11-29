"""
관리자 서비스
관리자 대시보드, 사용자 관리, AI 서비스 통계 등
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.utils.database import supabase


class AdminService:
    """관리자 서비스 클래스"""

    @staticmethod
    async def get_dashboard_stats() -> Dict:
        """
        관리자 대시보드 통계 조회 (4가지 핵심 AI 서비스 중심)

        Returns:
            Dict: 대시보드 통계 데이터
        """
        # 사용자 통계
        users_response = supabase.table("users")\
            .select("id, user_type")\
            .eq("is_active", True)\
            .execute()

        users = users_response.data if users_response.data else []
        total_users = len(users)
        general_users = sum(1 for user in users if user["user_type"] == "general")
        lawyers_count = sum(1 for user in users if user["user_type"] == "lawyer")
        admins_count = sum(1 for user in users if user["user_type"] == "admin")

        # 노무사 통계 (Phase 1: 노무사 서비스)
        lawyers_response = supabase.table("lawyers")\
            .select("id, is_verified")\
            .eq("is_active", True)\
            .execute()

        lawyers = lawyers_response.data if lawyers_response.data else []
        verified_lawyers = sum(1 for lawyer in lawyers if lawyer["is_verified"])
        unverified_lawyers = sum(1 for lawyer in lawyers if not lawyer["is_verified"])

        # 상담 통계 (Phase 1: 노무사 서비스)
        consultations_response = supabase.table("consultations")\
            .select("id, status")\
            .execute()

        consultations = consultations_response.data if consultations_response.data else []
        total_consultations = len(consultations)
        completed_consultations = sum(1 for c in consultations if c["status"] == "completed")

        # AI 분석 요청 통계 (Phase 2: AI 판례 분석)
        try:
            analysis_response = supabase.table("analysis_requests")\
                .select("id, status")\
                .execute()

            analysis_requests = analysis_response.data if analysis_response.data else []
            total_analysis = len(analysis_requests)
            completed_analysis = sum(1 for a in analysis_requests if a["status"] == "completed")
        except:
            total_analysis = 0
            completed_analysis = 0


        return {
            "users": {
                "total": total_users,
                "general": general_users,
                "lawyers": lawyers_count,
                "admins": admins_count
            },
            "lawyers": {
                "total": len(lawyers),
                "verified": verified_lawyers,
                "unverified": unverified_lawyers
            },
            "consultations": {
                "total": total_consultations,
                "completed": completed_consultations
            },
            "ai_analysis": {
                "total": total_analysis,
                "completed": completed_analysis
            }
        }


    @staticmethod
    async def get_all_users(
        user_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict:
        """
        모든 사용자 조회 (페이지네이션 포함)

        Args:
            user_type: 사용자 타입 필터 (general, lawyer, admin)
            limit: 페이지당 개수
            offset: 시작 위치

        Returns:
            Dict: 사용자 목록 및 총 개수
        """
        query = supabase.table("users")\
            .select("id, email, username, user_type, phone, address, is_active, created_at", count="exact")\
            .eq("is_active", True)

        if user_type and user_type != "all":
            query = query.eq("user_type", user_type)

        query = query.order("created_at", desc=True)\
            .range(offset, offset + limit - 1)

        response = query.execute()

        return {
            "data": response.data if response.data else [],
            "total": response.count if response.count else 0
        }

    @staticmethod
    async def toggle_user_status(user_id: str, is_active: bool) -> Dict:
        """
        사용자 활성화/비활성화 토글

        Args:
            user_id: 사용자 ID
            is_active: 활성화 여부

        Returns:
            Dict: 업데이트된 사용자
        """
        response = supabase.table("users")\
            .update({
                "is_active": is_active,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })\
            .eq("id", user_id)\
            .execute()

        if not response.data:
            raise ValueError("사용자를 찾을 수 없습니다.")

        return response.data[0]

