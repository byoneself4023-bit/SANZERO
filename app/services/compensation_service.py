"""
산재 보상금 신청 서비스

보상금 신청의 전체 생명주기를 관리합니다.
- 신청서 작성/수정/삭제
- 보상금 자동 계산 연동
- AI 분석 서비스 연동
- 관리자 승인/거부 프로세스
"""

from datetime import datetime, timezone, date
from typing import Dict, Any, Optional, List
import uuid
import logging

from app.utils.database import supabase
from app.utils.security import SecurityManager
from app.services.compensation_calculator_service import CompensationCalculatorService

logger = logging.getLogger(__name__)


class CompensationService:
    """보상금 신청 관리 서비스"""

    @staticmethod
    async def create_application(
        user_id: str,
        incident_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        보상금 신청서 생성

        Args:
            user_id: 신청자 ID
            incident_data: 사고 및 신청 정보

        Returns:
            Optional[Dict]: 생성된 신청서 정보
        """
        try:
            # XSS 방어: 모든 텍스트 입력 sanitization
            sanitized_data = CompensationService._sanitize_incident_data(incident_data)

            # 자동 보상금 추정 계산
            estimated_amount = await CompensationService._calculate_estimated_amount(
                sanitized_data
            )

            # 신청서 데이터 구성
            application_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "incident_date": sanitized_data.get("incident_date"),
                "incident_location": sanitized_data.get("incident_location"),
                "incident_description": sanitized_data.get("incident_description"),
                "injury_type": sanitized_data.get("injury_type"),
                "severity_level": sanitized_data.get("severity_level", "moderate"),
                "medical_records": sanitized_data.get("medical_records", {}),
                "employment_info": sanitized_data.get("employment_info", {}),
                "salary_info": sanitized_data.get("salary_info", {}),
                "estimated_amount": estimated_amount,
                "approved_amount": 0,
                "status": "pending",
                "documents": sanitized_data.get("documents", []),
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # 데이터베이스에 저장
            result = supabase.table("compensation_applications").insert(
                application_data
            ).execute()

            if result.data and len(result.data) > 0:
                created_application = result.data[0]
                logger.info(f"보상금 신청서 생성 완료: {created_application['id']}")

                # 변경 이력 기록
                await CompensationService._record_application_change(
                    created_application["id"],
                    user_id,
                    "created",
                    "신청서 생성"
                )

                return created_application

            logger.error("보상금 신청서 생성 실패: 데이터베이스 응답 없음")
            return None

        except Exception as e:
            logger.error(f"보상금 신청서 생성 오류: {e}")
            return None

    @staticmethod
    async def get_application_by_id(
        application_id: str,
        current_user: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        신청서 ID로 조회 (권한 확인 포함)

        Args:
            application_id: 신청서 ID
            current_user: 현재 사용자 정보

        Returns:
            Optional[Dict]: 신청서 정보
        """
        try:
            # 신청서 조회
            result = supabase.table("compensation_applications").select("*").eq(
                "id", application_id
            ).eq("is_active", True).execute()

            if not result.data or len(result.data) == 0:
                return None

            application = result.data[0]

            # 권한 확인 (신청자 본인 또는 관리자)
            if not CompensationService._check_user_permission(application, current_user):
                logger.warning(f"권한 없는 신청서 접근 시도: {application_id}, 사용자: {current_user.get('user_id')}")
                return None

            # 사용자 정보 추가
            application = await CompensationService._enrich_application_with_user_info(application)

            return application

        except Exception as e:
            logger.error(f"신청서 조회 오류: {e}")
            return None

    @staticmethod
    async def get_applications_by_user(
        user_id: str,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        사용자별 신청서 목록 조회

        Args:
            user_id: 사용자 ID
            status_filter: 상태 필터 ('pending', 'approved', 'rejected' 등)
            limit: 조회 제한 수
            offset: 시작 위치

        Returns:
            List[Dict]: 신청서 목록
        """
        try:
            query = supabase.table("compensation_applications").select(
                "id, incident_date, incident_location, injury_type, severity_level, "
                "estimated_amount, approved_amount, status, created_at, updated_at"
            ).eq("user_id", user_id).eq("is_active", True)

            if status_filter:
                query = query.eq("status", status_filter)

            result = query.order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"사용자별 신청서 목록 조회 오류: {e}")
            return []

    @staticmethod
    async def update_application(
        application_id: str,
        update_data: Dict[str, Any],
        current_user: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        신청서 수정 (pending 상태만 가능)

        Args:
            application_id: 신청서 ID
            update_data: 수정할 데이터
            current_user: 현재 사용자

        Returns:
            Optional[Dict]: 수정된 신청서 정보
        """
        try:
            # 기존 신청서 조회 및 권한 확인
            application = await CompensationService.get_application_by_id(
                application_id, current_user
            )

            if not application:
                return None

            # pending 상태만 수정 가능
            if application["status"] != "pending":
                logger.warning(f"수정 불가능한 상태의 신청서: {application_id}, 상태: {application['status']}")
                return None

            # 데이터 sanitization
            sanitized_update = CompensationService._sanitize_incident_data(update_data)

            # 보상금 재계산 (급여 정보가 변경된 경우)
            if "salary_info" in sanitized_update or "severity_level" in sanitized_update:
                # 기존 데이터와 새 데이터 병합
                merged_data = {**application, **sanitized_update}
                estimated_amount = await CompensationService._calculate_estimated_amount(merged_data)
                sanitized_update["estimated_amount"] = estimated_amount

            # 수정 시간 업데이트
            sanitized_update["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 데이터베이스 업데이트
            result = supabase.table("compensation_applications").update(
                sanitized_update
            ).eq("id", application_id).execute()

            if result.data and len(result.data) > 0:
                updated_application = result.data[0]

                # 변경 이력 기록
                await CompensationService._record_application_change(
                    application_id,
                    current_user["user_id"],
                    "updated",
                    "신청서 수정"
                )

                logger.info(f"신청서 수정 완료: {application_id}")
                return updated_application

            return None

        except Exception as e:
            logger.error(f"신청서 수정 오류: {e}")
            return None

    @staticmethod
    async def delete_application(
        application_id: str,
        current_user: Dict[str, Any]
    ) -> bool:
        """
        신청서 삭제 (소프트 삭제, pending 상태만 가능)

        Args:
            application_id: 신청서 ID
            current_user: 현재 사용자

        Returns:
            bool: 삭제 성공 여부
        """
        try:
            # 기존 신청서 조회 및 권한 확인
            application = await CompensationService.get_application_by_id(
                application_id, current_user
            )

            if not application:
                return False

            # pending 상태만 삭제 가능
            if application["status"] != "pending":
                logger.warning(f"삭제 불가능한 상태의 신청서: {application_id}, 상태: {application['status']}")
                return False

            # 소프트 삭제 (is_active = False)
            result = supabase.table("compensation_applications").update({
                "is_active": False,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", application_id).execute()

            if result.data and len(result.data) > 0:
                # 변경 이력 기록
                await CompensationService._record_application_change(
                    application_id,
                    current_user["user_id"],
                    "deleted",
                    "신청서 삭제"
                )

                logger.info(f"신청서 삭제 완료: {application_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"신청서 삭제 오류: {e}")
            return False

    @staticmethod
    async def update_application_status(
        application_id: str,
        new_status: str,
        admin_user: Dict[str, Any],
        admin_notes: Optional[str] = None,
        approved_amount: Optional[int] = None
    ) -> bool:
        """
        신청서 상태 변경 (관리자 전용)

        Args:
            application_id: 신청서 ID
            new_status: 새로운 상태 ('approved', 'rejected', 'reviewing')
            admin_user: 관리자 사용자 정보
            admin_notes: 관리자 메모
            approved_amount: 승인 금액 (승인 시)

        Returns:
            bool: 상태 변경 성공 여부
        """
        try:
            # 관리자 권한 확인
            if admin_user.get("user_type") != "admin":
                logger.warning(f"관리자 권한 없는 상태 변경 시도: {admin_user.get('user_id')}")
                return False

            # 업데이트 데이터 구성
            update_data = {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if approved_amount is not None:
                update_data["approved_amount"] = approved_amount

            if admin_notes:
                update_data["admin_notes"] = SecurityManager.sanitize_text(admin_notes)

            # 데이터베이스 업데이트
            result = supabase.table("compensation_applications").update(
                update_data
            ).eq("id", application_id).execute()

            if result.data and len(result.data) > 0:
                # 변경 이력 기록
                await CompensationService._record_application_change(
                    application_id,
                    admin_user["user_id"],
                    f"status_changed_to_{new_status}",
                    f"관리자가 상태를 {new_status}로 변경. 메모: {admin_notes or '없음'}"
                )

                logger.info(f"신청서 상태 변경: {application_id} -> {new_status}")
                return True

            return False

        except Exception as e:
            logger.error(f"신청서 상태 변경 오류: {e}")
            return False

    @staticmethod
    def _sanitize_incident_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """사고 정보 데이터 sanitization"""
        sanitized = {}

        # 텍스트 필드 sanitization
        text_fields = [
            "incident_location", "incident_description", "injury_type"
        ]

        for field in text_fields:
            if field in data and isinstance(data[field], str):
                sanitized[field] = SecurityManager.sanitize_text(data[field])

        # 날짜 필드
        if "incident_date" in data:
            sanitized["incident_date"] = data["incident_date"]

        # 선택 필드
        if "severity_level" in data:
            sanitized["severity_level"] = data["severity_level"]

        # JSON 필드들
        json_fields = ["medical_records", "employment_info", "salary_info"]
        for field in json_fields:
            if field in data:
                sanitized[field] = data[field]

        # 문서 배열
        if "documents" in data:
            sanitized["documents"] = data["documents"]

        return sanitized

    @staticmethod
    async def _calculate_estimated_amount(incident_data: Dict[str, Any]) -> int:
        """신청서 데이터 기반 보상금 추정"""
        try:
            # 급여 정보에서 기본 급여 추출
            salary_info = incident_data.get("salary_info", {})
            base_salary = salary_info.get("base_salary", 0)

            if base_salary <= 0:
                return 0

            # 일 평균임금 계산 (월급 ÷ 21.7일)
            daily_wage = base_salary / 21.7

            # 부상 심각도별 배수 적용
            severity_multiplier = CompensationService._get_severity_multiplier(
                incident_data.get("severity_level", "moderate")
            )

            # 의료비 추가
            medical_records = incident_data.get("medical_records", {})
            medical_cost = medical_records.get("medical_cost", 0)

            # 기본 계산: (일 평균임금 × 심각도 배수 × 180일) + 의료비
            estimated_amount = int(daily_wage * severity_multiplier * 180) + medical_cost

            return max(estimated_amount, 0)

        except Exception as e:
            logger.error(f"보상금 추정 계산 오류: {e}")
            return 0

    @staticmethod
    def _get_severity_multiplier(severity: str) -> float:
        """부상 심각도별 배수"""
        multipliers = {
            "critical": 3.0,
            "severe": 2.0,
            "moderate": 1.5,
            "minor": 1.0
        }
        return multipliers.get(severity, 1.5)

    @staticmethod
    def _check_user_permission(
        application: Dict[str, Any],
        current_user: Dict[str, Any]
    ) -> bool:
        """사용자 권한 확인"""
        # 신청자 본인
        if application["user_id"] == current_user.get("user_id"):
            return True

        # 관리자
        if current_user.get("user_type") == "admin":
            return True

        return False

    @staticmethod
    async def _enrich_application_with_user_info(
        application: Dict[str, Any]
    ) -> Dict[str, Any]:
        """신청서에 사용자 정보 추가"""
        try:
            # 사용자 정보 조회
            user_result = supabase.table("users").select(
                "id, username, email, phone"
            ).eq("id", application["user_id"]).execute()

            if user_result.data and len(user_result.data) > 0:
                application["user"] = user_result.data[0]

            return application

        except Exception as e:
            logger.error(f"사용자 정보 추가 오류: {e}")
            return application

    @staticmethod
    async def _record_application_change(
        application_id: str,
        user_id: str,
        change_type: str,
        description: str
    ) -> None:
        """신청서 변경 이력 기록"""
        try:
            change_data = {
                "id": str(uuid.uuid4()),
                "application_id": application_id,
                "user_id": user_id,
                "change_type": change_type,
                "description": description,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            supabase.table("compensation_application_changes").insert(
                change_data
            ).execute()

        except Exception as e:
            logger.error(f"변경 이력 기록 오류: {e}")
            # 이력 기록 실패가 주 작업을 방해하지 않도록 pass

    @staticmethod
    async def get_all_applications_for_admin(
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        관리자용 전체 신청서 목록 조회

        Args:
            status_filter: 상태 필터
            limit: 조회 제한 수
            offset: 시작 위치

        Returns:
            List[Dict]: 신청서 목록 (사용자 정보 포함)
        """
        try:
            query = supabase.table("compensation_applications").select(
                "*, users(username, email)"
            ).eq("is_active", True)

            if status_filter:
                query = query.eq("status", status_filter)

            result = query.order("created_at", desc=True).range(
                offset, offset + limit - 1
            ).execute()

            return result.data if result.data else []

        except Exception as e:
            logger.error(f"관리자용 신청서 목록 조회 오류: {e}")
            return []

    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """신청서 통계 조회"""
        try:
            # 전체 신청서 수
            total_result = supabase.table("compensation_applications").select(
                "id", count="exact"
            ).eq("is_active", True).execute()

            # 상태별 통계
            stats = {}
            for status in ["pending", "approved", "rejected", "reviewing"]:
                status_result = supabase.table("compensation_applications").select(
                    "id", count="exact"
                ).eq("status", status).eq("is_active", True).execute()

                stats[f"{status}_count"] = status_result.count or 0

            # 총 승인 금액
            approved_result = supabase.table("compensation_applications").select(
                "approved_amount"
            ).eq("status", "approved").eq("is_active", True).execute()

            total_approved_amount = sum(
                app.get("approved_amount", 0) for app in (approved_result.data or [])
            )

            return {
                "total_applications": total_result.count or 0,
                "total_approved_amount": total_approved_amount,
                **stats
            }

        except Exception as e:
            logger.error(f"통계 조회 오류: {e}")
            return {
                "total_applications": 0,
                "total_approved_amount": 0,
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
                "reviewing_count": 0
            }