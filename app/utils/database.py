"""
SANZERO 데이터베이스 연결 및 관리
Supabase REST API 직접 사용 (Python 클라이언트 401 에러 우회)
"""

from supabase import create_client, Client
from app.utils.config import settings, validate_settings
import asyncio
from typing import Optional, Dict, Any, List
import json
import httpx
from loguru import logger

# 설정 검증
validate_settings()

# REST API 직접 호출을 위한 httpx 클라이언트
async_http_client = httpx.AsyncClient(timeout=30.0)

# Supabase REST API 헤더
def get_rest_headers(use_service_role=True):
    """REST API 헤더 생성"""
    key = settings.supabase_service_role_key if use_service_role else settings.supabase_anon_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

# Supabase 클라이언트 인스턴스 (Auth 용도로만 사용)
try:
    from supabase.client import ClientOptions
    client_options = ClientOptions(
        schema="public",
        headers={"Prefer": "return=minimal"},
        auto_refresh_token=True,
        persist_session=True
    )
    anon_supabase: Client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=client_options
    )

    # Service role 클라이언트 (데이터 작업용)
    supabase: Client = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        options=client_options
    )
except Exception as e:
    logger.warning(f"Supabase client creation warning: {e}")
    anon_supabase = None
    supabase = None

class DatabaseManager:
    """데이터베이스 관리 클래스 (REST API 직접 사용)"""

    def __init__(self):
        self.base_url = settings.supabase_url
        self.anon_client = anon_supabase

    async def test_connection(self) -> bool:
        """데이터베이스 연결 테스트"""
        try:
            url = f"{self.base_url}/rest/v1/users?select=count"
            response = await async_http_client.get(url, headers=get_rest_headers())

            if response.status_code == 200:
                logger.info(f"데이터베이스 연결 성공")
                return True
            else:
                logger.error(f"데이터베이스 연결 실패: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {str(e)}")
            return False

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """이메일로 사용자 조회"""
        try:
            url = f"{self.base_url}/rest/v1/users?email=eq.{email}&is_active=eq.true&limit=1"
            response = await async_http_client.get(url, headers=get_rest_headers())

            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            return None
        except Exception as e:
            logger.warning(f"사용자 조회 실패 (email: {email}): {str(e)}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ID로 사용자 조회"""
        try:
            url = f"{self.base_url}/rest/v1/users?id=eq.{user_id}&is_active=eq.true&limit=1"
            response = await async_http_client.get(url, headers=get_rest_headers())

            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            return None
        except Exception as e:
            logger.warning(f"사용자 조회 실패 (id: {user_id}): {str(e)}")
            return None

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """새 사용자 생성"""
        try:
            url = f"{self.base_url}/rest/v1/users"
            response = await async_http_client.post(url, headers=get_rest_headers(), json=user_data)

            if response.status_code in [200, 201]:
                data = response.json()
                logger.info(f"새 사용자 생성 성공: {user_data.get('email')}")
                return data[0] if isinstance(data, list) else data
            else:
                logger.error(f"사용자 생성 실패: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"사용자 생성 실패: {str(e)}")
            return None

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """사용자 정보 업데이트"""
        try:
            url = f"{self.base_url}/rest/v1/users?id=eq.{user_id}"
            response = await async_http_client.patch(url, headers=get_rest_headers(), json=update_data)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"사용자 정보 업데이트 성공: {user_id}")
                return data[0] if isinstance(data, list) else data
            else:
                logger.error(f"사용자 정보 업데이트 실패: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"사용자 정보 업데이트 실패: {str(e)}")
            return None

    async def get_compensation_applications(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """보상금 신청 목록 조회"""
        try:
            query = self.client.table("compensation_applications").select("*").eq("is_active", True)

            if user_id:
                query = query.eq("user_id", user_id)

            if status:
                query = query.eq("status", status)

            result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            return result.data
        except Exception as e:
            logger.error(f"보상금 신청 목록 조회 실패: {str(e)}")
            return []

    async def get_application_by_id(self, application_id: str) -> Optional[Dict[str, Any]]:
        """보상금 신청 상세 조회"""
        try:
            result = self.client.table("compensation_applications").select("*").eq("id", application_id).eq("is_active", True).single().execute()
            return result.data
        except Exception as e:
            logger.warning(f"보상금 신청 조회 실패 (id: {application_id}): {str(e)}")
            return None

    async def create_compensation_application(self, application_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """보상금 신청 생성"""
        try:
            result = self.client.table("compensation_applications").insert(application_data).execute()
            logger.info(f"보상금 신청 생성 성공: {application_data.get('user_id')}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"보상금 신청 생성 실패: {str(e)}")
            return None

    async def update_compensation_application(
        self,
        application_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """보상금 신청 업데이트"""
        try:
            result = self.client.table("compensation_applications").update(update_data).eq("id", application_id).execute()
            logger.info(f"보상금 신청 업데이트 성공: {application_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"보상금 신청 업데이트 실패: {str(e)}")
            return None

    async def get_lawyers(
        self,
        verified_only: bool = True,
        specialty: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """노무사 목록 조회"""
        try:
            query = self.client.table("lawyers").select("*, users(*)").eq("is_active", True)

            if verified_only:
                query = query.eq("is_verified", True)

            if specialty:
                query = query.contains("specialties", [specialty])

            result = query.order("rating", desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"노무사 목록 조회 실패: {str(e)}")
            return []

    async def calculate_compensation(
        self,
        user_id: str,
        base_salary: int,
        injury_severity: str,
        disability_grade: str = "",
        medical_costs: int = 0
    ) -> Optional[Dict[str, Any]]:
        """RPC 함수를 사용한 보상금 계산"""
        try:
            result = self.client.rpc(
                "calculate_personalized_compensation",
                {
                    "user_id_param": user_id,
                    "base_salary": base_salary,
                    "injury_severity": injury_severity,
                    "disability_grade": disability_grade,
                    "medical_costs": medical_costs
                }
            ).execute()

            return result.data
        except Exception as e:
            logger.error(f"보상금 계산 실패: {str(e)}")
            return None

    async def find_matching_lawyers(self, application_id: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """AI 기반 노무사 매칭"""
        try:
            result = self.client.rpc(
                "find_best_lawyer_match",
                {
                    "application_id_param": application_id,
                    "max_results": max_results
                }
            ).execute()

            return result.data
        except Exception as e:
            logger.error(f"노무사 매칭 실패: {str(e)}")
            return []

# 데이터베이스 매니저 인스턴스
db = DatabaseManager()

# 연결 테스트 함수
async def test_database_connection():
    """데이터베이스 연결 테스트 실행"""
    return await db.test_connection()

async def create_analysis_requests_table():
    """analysis_requests 테이블 확인 및 안전한 초기화"""
    try:
        logger.info("analysis_requests 테이블 확인 중...")

        # 테이블 존재 여부 확인 (안전한 방법)
        try:
            # 빈 쿼리로 테이블 존재 확인 (에러가 나면 테이블이 없음)
            test_query = supabase.table("analysis_requests").select("id").limit(1).execute()
            logger.info("analysis_requests 테이블이 이미 존재합니다.")
            return True
        except Exception as table_check_error:
            logger.info(f"analysis_requests 테이블이 없습니다: {table_check_error}")

        # 간단한 테이블 생성 시도 (Supabase 클라이언트를 통한 안전한 방법)
        try:
            # 테이블이 없다면 기본 구조로 초기화
            # Supabase 대시보드에서 수동으로 생성하거나, SQL 에디터를 통해 생성하도록 안내
            logger.warning("analysis_requests 테이블을 수동으로 생성해야 합니다.")
            logger.warning("Supabase 대시보드에서 다음 SQL을 실행해주세요:")
            logger.warning("CREATE TABLE analysis_requests (id UUID DEFAULT gen_random_uuid() PRIMARY KEY, user_id UUID REFERENCES auth.users(id), query_text TEXT NOT NULL, analysis_type TEXT DEFAULT 'precedent_search', status TEXT DEFAULT 'pending', result JSONB, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());")
            return False
        except Exception as create_error:
            logger.warning(f"테이블 생성 실패: {create_error}")
            return False

    except Exception as e:
        logger.warning(f"analysis_requests 테이블 확인 중 오류: {e}")
        return False

async def setup_test_accounts():
    """테스트 계정 및 초기 데이터 설정"""
    try:
        logger.info("테스트 계정 설정 시작...")

        test_accounts = [
            {
                "email": "byoneself4023@ajou.ac.kr",
                "password": "rlarlduf0",
                "username": "Kuka",
                "user_type": "admin",
                "phone": "010-1234-5678",
                "address": "서울시 강남구"
            },
            {
                "email": "testuser@example.com",
                "password": "test123456!",
                "username": "testuser",
                "user_type": "general",
                "phone": "010-1111-2222",
                "address": "서울시 강남구 테스트동 123번지"
            },
            {
                "email": "lawyer@example.com",
                "password": "lawyer123456!",
                "username": "testlawyer",
                "user_type": "lawyer",
                "phone": "010-3333-4444",
                "address": "서울시 서초구 법조로 123"
            }
        ]

        created_count = 0
        for account in test_accounts:
            # 기존 사용자 확인
            existing_user = await db.get_user_by_email(account["email"])
            if existing_user:
                logger.info(f"테스트 계정이 이미 존재함: {account['email']}")
                continue

            try:
                # Supabase Auth에 계정 생성
                auth_response = anon_supabase.auth.sign_up({
                    "email": account["email"],
                    "password": account["password"],
                    "options": {
                        "data": {
                            "username": account["username"],
                            "user_type": account["user_type"]
                        }
                    }
                })

                if auth_response.user:
                    # users 테이블에 프로필 생성
                    user_data = {
                        "id": auth_response.user.id,
                        "email": account["email"],
                        "username": account["username"],
                        "user_type": account["user_type"],
                        "phone": account["phone"],
                        "address": account["address"],
                        "is_active": True
                    }

                    user = await db.create_user(user_data)
                    if user:
                        created_count += 1
                        logger.info(f"테스트 계정 생성 성공: {account['email']}")

                        # 노무사 계정인 경우 lawyers 테이블에도 추가
                        if account["user_type"] == "lawyer":
                            lawyer_data = {
                                "user_id": user["id"],
                                "license_number": "LAW-2024-001",
                                "office_name": "테스트 노무사 사무소",
                                "office_address": "서울시 서초구 법조로 123, 7층",
                                "specialties": ["산업재해", "근로기준법", "산업안전", "노동분쟁"],
                                "experience_years": 5,
                                "consultation_fee": 100000,
                                "success_rate": 94.0,
                                "rating": 4.8,
                                "total_reviews": 247,
                                "case_count": 156,
                                "is_verified": True,
                                "is_active": True
                            }

                            lawyer_result = supabase.table("lawyers").insert(lawyer_data).execute()
                            if lawyer_result.data:
                                logger.info(f"노무사 프로필 생성 성공: {account['email']}")
                    else:
                        logger.error(f"사용자 프로필 생성 실패: {account['email']}")
                else:
                    logger.error(f"Supabase Auth 계정 생성 실패: {account['email']}")

            except Exception as e:
                logger.error(f"테스트 계정 생성 오류 ({account['email']}): {str(e)}")
                continue

        logger.info(f"테스트 계정 설정 완료: {created_count}개 계정 생성")
        return created_count

    except Exception as e:
        logger.error(f"테스트 계정 설정 실패: {str(e)}")
        return 0