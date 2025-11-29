"""
노무사 서비스
노무사 등록, 검색, 매칭, 상담 예약 등의 비즈니스 로직
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from app.utils.database import supabase
from app.utils.security import security

class LawyerService:
    """노무사 관리 서비스"""

    logger = logging.getLogger(__name__)

    @staticmethod
    async def create_lawyer_profile(
        user_id: str,
        license_number: str,
        office_name: str,
        office_address: Optional[str] = None,
        specialties: Optional[List[str]] = None,
        experience_years: int = 0,
        consultation_fee: int = 0
    ) -> Optional[Dict[str, Any]]:
        """노무사 프로필 생성"""
        try:
            # XSS 방어: 모든 텍스트 입력 sanitize
            license_number = security.sanitize_text(license_number)
            office_name = security.sanitize_text(office_name)
            if office_address:
                office_address = security.sanitize_text(office_address)

            # specialties도 sanitize
            if specialties:
                specialties = [security.sanitize_text(specialty) for specialty in specialties]

            lawyer_data = {
                "user_id": user_id,
                "license_number": license_number,
                "office_name": office_name,
                "office_address": office_address,
                "specialties": specialties or [],
                "experience_years": experience_years,
                "consultation_fee": consultation_fee,
                "is_verified": False,  # 초기에는 미인증 상태
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = supabase.table("lawyers").insert(lawyer_data).execute()

            if result.data:
                LawyerService.logger.info(f"Lawyer profile created: {result.data[0]['id']}")
                return result.data[0]
            else:
                LawyerService.logger.error("Failed to create lawyer profile")
                return None

        except Exception as e:
            LawyerService.logger.error(f"Error creating lawyer profile: {str(e)}")
            return None

    @staticmethod
    async def get_lawyer_by_id(lawyer_id: str, include_user: bool = True) -> Optional[Dict[str, Any]]:
        """노무사 ID로 조회"""
        try:
            if include_user:
                query = supabase.table("lawyers").select("*, user:users(*)")
            else:
                query = supabase.table("lawyers").select("*")

            result = query.eq("id", lawyer_id).eq("is_active", True).single().execute()

            if result.data:
                return result.data
            return None

        except Exception as e:
            LawyerService.logger.error(f"Error getting lawyer by id {lawyer_id}: {str(e)}")
            return None

    @staticmethod
    async def get_lawyer_by_user_id(user_id: str, include_user: bool = True) -> Optional[Dict[str, Any]]:
        """사용자 ID로 노무사 정보 조회"""
        try:
            if include_user:
                query = supabase.table("lawyers").select("*, user:users(*)")
            else:
                query = supabase.table("lawyers").select("*")

            result = query.eq("user_id", user_id).eq("is_active", True).single().execute()

            if result.data:
                return result.data
            return None

        except Exception as e:
            LawyerService.logger.error(f"Error getting lawyer by user_id {user_id}: {str(e)}")
            return None

    @staticmethod
    async def search_lawyers(
        specialties: Optional[List[str]] = None,
        location: Optional[str] = None,
        experience_years_min: Optional[int] = None,
        case_difficulty: Optional[str] = None,
        consultation_fee_max: Optional[int] = None,
        sort_by: Optional[str] = "success_rate",
        is_verified: bool = True,
        is_online_consult: Optional[bool] = None,
        supports_sanzero_pay: Optional[bool] = None,
        free_consult: Optional[bool] = None,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """노무사 검색"""
        try:
            # 기본 쿼리 구성 - 전문분야 필터는 클라이언트 측에서 처리
            query = supabase.table("lawyers").select("*, user:users(*)")

            # 필터 적용
            query = query.eq("is_active", True).eq("is_verified", is_verified)

            # 지역 필터 (office_address에서 검색)
            if location:
                location = security.sanitize_text(location)
                query = query.ilike("office_address", f"%{location}%")

            # 경력 필터
            if experience_years_min is not None:
                query = query.gte("experience_years", experience_years_min)


            # 상담료 필터
            if consultation_fee_max is not None:
                query = query.lte("consultation_fee", consultation_fee_max)

            # 온라인 상담 가능 필터
            if is_online_consult is not None:
                query = query.eq("is_online_consult", is_online_consult)

            # SANZERO 페이 지원 필터
            if supports_sanzero_pay is not None:
                query = query.eq("supports_sanzero_pay", supports_sanzero_pay)

            # 무료 상담 필터 (상담료가 0인 경우)
            if free_consult is not None and free_consult:
                query = query.eq("consultation_fee", 0)

            # 사건 난이도 필터
            if case_difficulty:
                query = query.eq("case_difficulty", case_difficulty)

            # 동적 정렬 적용
            if sort_by == "rating":
                query = query.order("rating", desc=True).order("success_rate", desc=True)
            elif sort_by == "experience":
                query = query.order("experience_years", desc=True).order("success_rate", desc=True)
            elif sort_by == "success_rate":
                query = query.order("success_rate", desc=True).order("rating", desc=True)
            elif sort_by == "fee":
                query = query.order("consultation_fee", desc=False).order("success_rate", desc=True)
            else:
                # 기본값: 성공률 순
                query = query.order("success_rate", desc=True).order("rating", desc=True).order("experience_years", desc=True)

            # 모든 데이터 조회 (전문분야 필터링을 위해)
            result = query.execute()
            all_lawyers = result.data or []

            # 클라이언트 측 전문분야 필터링 및 주소 간소화
            filtered_lawyers = []
            if specialties:
                # 전문분야 필터가 있는 경우
                normalized_specialties = [s.strip() for s in specialties]

                for lawyer in all_lawyers:
                    lawyer_specialties = lawyer.get("specialties", [])
                    # 각 노무사의 전문분야를 문자열로 변환하여 검색
                    specialties_str = " ".join(lawyer_specialties).lower()

                    # 요청된 전문분야 중 하나라도 매치되면 포함
                    for requested_specialty in normalized_specialties:
                        if requested_specialty.lower() in specialties_str:
                            # 간소화된 주소 추가
                            lawyer['simplified_address'] = LawyerService._simplify_address(lawyer.get('office_address', ''))
                            filtered_lawyers.append(lawyer)
                            break
            else:
                # 전문분야 필터가 없는 경우 모든 결과 사용
                for lawyer in all_lawyers:
                    # 간소화된 주소 추가
                    lawyer['simplified_address'] = LawyerService._simplify_address(lawyer.get('office_address', ''))
                    filtered_lawyers.append(lawyer)

            # 페이지네이션 적용
            total = len(filtered_lawyers)
            start_idx = (page - 1) * size
            end_idx = start_idx + size
            paged_lawyers = filtered_lawyers[start_idx:end_idx]

            LawyerService.logger.info(f"Found {total} lawyers with filters (specialties: {specialties})")
            return paged_lawyers, total

        except Exception as e:
            LawyerService.logger.error(f"Error searching lawyers: {str(e)}")
            # Fallback 더미 데이터 (nomusa 더미 데이터 기반)
            dummy_lawyers = [
                {
                    "id": "nomusa-1",
                    "office_name": "황지훈 노무사 사무소",
                    "license_number": "LAW-2024-0001",
                    "office_address": "서울 양천구",
                    "specialties": ["소음성 난청"],
                    "experience_years": 5,
                    "success_rate": 50.0,
                    "rating": 4.0,
                    "case_count": 50,
                    "consultation_fee": 100000,
                    "is_verified": True,
                    "is_online_consult": True,
                    "supports_sanzero_pay": True,
                    "phone": "017-504-3563",
                    "website_url": "http://황지nomu68.com",
                    "fee_policy": "착수금 0원, 성공보수 협의",
                    "case_difficulty": "상",
                    "simplified_address": "서울 양천구",
                    "user": {
                        "full_name": "황지훈"
                    }
                },
                {
                    "id": "nomusa-2",
                    "office_name": "김영환 노무사 사무소",
                    "license_number": "LAW-2024-0002",
                    "office_address": "성남 중원구",
                    "specialties": ["퇴행성관절염"],
                    "experience_years": 7,
                    "success_rate": 57.0,
                    "rating": 4.2,
                    "case_count": 75,
                    "consultation_fee": 0,
                    "is_verified": True,
                    "is_online_consult": False,
                    "supports_sanzero_pay": True,
                    "phone": "070-5757-1815",
                    "website_url": "http://김영nomu95.com",
                    "fee_policy": "사안 검토 후 정책 결정 (초기 상담 무료)",
                    "case_difficulty": "중",
                    "simplified_address": "성남 중원구",
                    "user": {
                        "full_name": "김영환"
                    }
                },
                {
                    "id": "nomusa-3",
                    "office_name": "이채원 노무사 사무소",
                    "license_number": "LAW-2024-0003",
                    "office_address": "천안 동남구",
                    "specialties": ["외측상과염"],
                    "experience_years": 9,
                    "success_rate": 83.0,
                    "rating": 4.4,
                    "case_count": 100,
                    "consultation_fee": 100000,
                    "is_verified": True,
                    "is_online_consult": False,
                    "supports_sanzero_pay": False,
                    "phone": "010-7737-7157",
                    "website_url": "http://이채nomu50.com",
                    "fee_policy": "착수금 100만원, 성공보수 15%",
                    "case_difficulty": "상",
                    "simplified_address": "천안 동남구",
                    "user": {
                        "full_name": "이채원"
                    }
                },
                {
                    "id": "nomusa-4",
                    "office_name": "김주원 노무사 사무소",
                    "license_number": "LAW-2024-0004",
                    "office_address": "인천 동구",
                    "specialties": ["산재 부지급", "진폐증 폐질환"],
                    "experience_years": 11,
                    "success_rate": 86.0,
                    "rating": 4.6,
                    "case_count": 125,
                    "consultation_fee": 0,
                    "is_verified": True,
                    "is_online_consult": True,
                    "supports_sanzero_pay": True,
                    "phone": "011-827-7405",
                    "website_url": "http://김주nomu53.com",
                    "fee_policy": "사안 검토 후 정책 결정 (초기 상담 무료)",
                    "case_difficulty": "하",
                    "simplified_address": "인천 동구",
                    "user": {
                        "full_name": "김주원"
                    }
                },
                {
                    "id": "nomusa-5",
                    "office_name": "김서연 노무사 사무소",
                    "license_number": "LAW-2024-0005",
                    "office_address": "부천 원미구",
                    "specialties": ["산재 부지급", "급성 심근경색"],
                    "experience_years": 13,
                    "success_rate": 50.0,
                    "rating": 4.8,
                    "case_count": 150,
                    "consultation_fee": 0,
                    "is_verified": True,
                    "is_online_consult": True,
                    "supports_sanzero_pay": True,
                    "phone": "041-196-3614",
                    "website_url": "http://김서nomu65.com",
                    "fee_policy": "사안 검토 후 정책 결정 (초기 상담 무료)",
                    "case_difficulty": "중하",
                    "simplified_address": "부천 원미구",
                    "user": {
                        "full_name": "김서연"
                    }
                }
            ]

            # 전문분야 필터가 있는 경우 간단한 매칭
            if specialties:
                filtered = []
                for dummy in dummy_lawyers:
                    for spec in specialties:
                        if any(spec.lower() in s.lower() for s in dummy["specialties"]):
                            filtered.append(dummy)
                            break
                return filtered[:size], len(filtered)

            return dummy_lawyers[:size], len(dummy_lawyers)

    @staticmethod
    async def get_recommended_lawyers_by_injury_type(
        injury_type: str,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """부상 유형 기반 노무사 추천"""
        try:
            # 부상 유형별 전문분야 매핑
            injury_to_specialty_map = {
                # 근골격계 질환
                "발목 염좌": ["근골격계 질환", "외상"],
                "손목 부상": ["근골격계 질환", "외상"],
                "허리 부상": ["근골격계 질환", "척추협착증"],
                "무릎 부상": ["근골격계 질환", "퇴행성관절염"],
                "어깨 부상": ["근골격계 질환", "외측상과염"],

                # 절단 및 외상
                "손가락 절단": ["외상", "산업재해"],
                "발가락 절단": ["외상", "산업재해"],
                "팔 절단": ["외상", "산업재해"],
                "다리 절단": ["외상", "산업재해"],

                # 화상
                "화상": ["화상", "산업재해"],
                "전기 화상": ["화상", "전기재해"],

                # 호흡기 질환
                "진폐증": ["진폐증 폐질환", "직업성 질환"],
                "폐질환": ["진폐증 폐질환", "직업성 질환"],
                "천식": ["호흡기 질환", "직업성 질환"],

                # 청력 손실
                "소음성 난청": ["소음성 난청", "직업성 질환"],
                "돌발성 난청": ["소음성 난청", "직업성 질환"],

                # 심혈관계 질환
                "급성 심근경색": ["급성 심근경색", "과로사"],
                "뇌출혈": ["뇌혈관 질환", "과로사"],
                "뇌경색": ["뇌혈관 질환", "과로사"],

                # 정신적 질환
                "우울증": ["정신적 질환", "과로", "스트레스"],
                "PTSD": ["정신적 질환", "외상후스트레스"],
                "적응장애": ["정신적 질환", "스트레스"],

                # 기본값
                "기타": ["산업재해", "근골격계 질환"]
            }

            # 부상 유형에 따른 전문분야 추출
            target_specialties = injury_to_specialty_map.get(injury_type, ["산업재해"])

            # 전문분야 기반 노무사 검색
            lawyers, _ = await LawyerService.search_lawyers(
                specialties=target_specialties,
                is_verified=True,
                page=1,
                size=max_results
            )

            LawyerService.logger.info(f"Found {len(lawyers)} lawyers for injury type: {injury_type}")
            return lawyers

        except Exception as e:
            LawyerService.logger.error(f"Error finding lawyers for injury type {injury_type}: {str(e)}")
            return []

    @staticmethod
    async def find_best_matches(application_id: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """AI 기반 노무사 매칭 (RPC 함수 사용)"""
        try:
            # ARCHITECTURE.md에 정의된 RPC 함수 호출
            result = supabase.rpc("find_best_lawyer_match", {
                "application_id": application_id,
                "max_results": max_results
            }).execute()

            if result.data:
                # 매칭 결과에 노무사 상세 정보 추가
                matches = []
                for match in result.data:
                    lawyer = await LawyerService.get_lawyer_by_id(match["lawyer_id"])
                    if lawyer:
                        matches.append({
                            "lawyer_id": match["lawyer_id"],
                            "match_score": float(match["match_score"]),
                            "match_reasons": match["match_reasons"],
                            "lawyer": lawyer
                        })

                LawyerService.logger.info(f"Found {len(matches)} lawyer matches for application {application_id}")
                return matches

            return []

        except Exception as e:
            LawyerService.logger.error(f"Error finding lawyer matches for application {application_id}: {str(e)}")
            return []

    @staticmethod
    async def update_lawyer_profile(
        lawyer_id: str,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """노무사 프로필 수정"""
        try:
            # 권한 확인: 해당 노무사 본인만 수정 가능
            lawyer = await LawyerService.get_lawyer_by_id(lawyer_id)
            if not lawyer or lawyer.get("user_id") != user_id:
                LawyerService.logger.warning(f"Unauthorized lawyer profile update attempt: {user_id}")
                return None

            # XSS 방어: 텍스트 필드 sanitize
            sanitized_data = {}
            for key, value in update_data.items():
                if key in ["office_name", "office_address"] and value:
                    sanitized_data[key] = security.sanitize_text(value)
                elif key == "specialties" and value:
                    sanitized_data[key] = [security.sanitize_text(specialty) for specialty in value]
                else:
                    sanitized_data[key] = value

            sanitized_data["updated_at"] = datetime.now(timezone.utc).isoformat()

            result = supabase.table("lawyers").update(sanitized_data).eq("id", lawyer_id).execute()

            if result.data:
                LawyerService.logger.info(f"Lawyer profile updated: {lawyer_id}")
                return result.data[0]
            return None

        except Exception as e:
            LawyerService.logger.error(f"Error updating lawyer profile {lawyer_id}: {str(e)}")
            return None

    @staticmethod
    async def verify_lawyer(lawyer_id: str, admin_user_id: str) -> bool:
        """노무사 인증 승인 (관리자만 가능)"""
        try:
            # 관리자 권한 확인
            admin_check = supabase.table("users").select("user_type").eq("id", admin_user_id).single().execute()
            if not admin_check.data or admin_check.data.get("user_type") != "admin":
                LawyerService.logger.warning(f"Unauthorized lawyer verification attempt: {admin_user_id}")
                return False

            result = supabase.table("lawyers").update({
                "is_verified": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", lawyer_id).execute()

            if result.data:
                LawyerService.logger.info(f"Lawyer verified: {lawyer_id} by admin: {admin_user_id}")
                return True
            return False

        except Exception as e:
            LawyerService.logger.error(f"Error verifying lawyer {lawyer_id}: {str(e)}")
            return False

    @staticmethod
    async def get_unique_specialties() -> List[str]:
        """실제 DB에서 모든 노무사의 전문분야 목록 조회"""
        try:
            result = supabase.table("lawyers")\
                .select("specialties")\
                .eq("is_active", True)\
                .execute()

            if not result.data:
                # Fallback 데이터 (nomusa 더미 데이터 기반)
                return [
                    "산재 부지급", "과로사", "근골격계 질환", "급성 심근경색",
                    "불승인 재심사", "소음성 난청", "외측상과염", "진폐증 폐질환",
                    "척추협착증", "퇴행성관절염", "특수 고용직 및 프리렌서"
                ]

            # 모든 specialties 배열을 하나로 합치기
            all_specialties = []
            for lawyer in result.data:
                if lawyer.get("specialties"):
                    all_specialties.extend(lawyer["specialties"])

            # 중복 제거 및 정렬
            unique_specialties = sorted(list(set(all_specialties)))

            LawyerService.logger.info(f"Found {len(unique_specialties)} unique specialties")
            return unique_specialties

        except Exception as e:
            LawyerService.logger.error(f"Error getting unique specialties: {str(e)}")
            # Fallback 데이터 (nomusa 더미 데이터 기반)
            return [
                "산재 부지급", "과로사", "근골격계 질환", "급성 심근경색",
                "불승인 재심사", "소음성 난청", "외측상과염", "진폐증 폐질환",
                "척추협착증", "퇴행성관절염", "특수 고용직 및 프리렌서"
            ]

    @staticmethod
    async def get_unique_locations() -> List[str]:
        """실제 DB에서 모든 노무사의 지역 목록 조회"""
        try:
            result = supabase.table("lawyers")\
                .select("office_address")\
                .eq("is_active", True)\
                .neq("office_address", None)\
                .execute()

            if not result.data:
                # Fallback 데이터 (nomusa 더미 데이터 기반)
                return [
                    "고양", "광주", "대구", "대전", "마산", "부산", "부천",
                    "서울", "성남", "수원", "안산", "안양", "용인", "울산",
                    "인천", "전주", "창원", "천안", "청주", "포항"
                ]

            # office_address에서 시/도 정보만 추출 (단순화)
            locations = []
            for lawyer in result.data:
                address = lawyer.get("office_address", "")
                if address:
                    parts = address.split(" ")
                    if len(parts) >= 1:
                        # 첫 번째 부분에서 시/도 정보 추출
                        city = parts[0]
                        if "특별시" in city:
                            city = city.replace("특별시", "")
                        elif "광역시" in city:
                            city = city.replace("광역시", "")
                        elif "도" in city:
                            city = city.replace("도", "")

                        # 단순화된 시/도 이름만 사용
                        if city in ["서울", "부산", "대구", "인천", "광주", "대전", "울산"]:
                            locations.append(city)
                        elif city == "경기":
                            locations.append("경기")
                        elif city == "충청남":
                            locations.append("충남")
                        elif city == "충청북":
                            locations.append("충북")
                        elif city == "전라남":
                            locations.append("전남")
                        elif city == "전라북":
                            locations.append("전북")
                        elif city == "경상남":
                            locations.append("경남")
                        elif city == "경상북":
                            locations.append("경북")
                        elif city == "강원":
                            locations.append("강원")
                        elif city == "제주":
                            locations.append("제주")
                        else:
                            locations.append(city)

            # 중복 제거 및 정렬
            unique_locations = sorted(list(set(locations)))

            LawyerService.logger.info(f"Found {len(unique_locations)} unique locations")
            return unique_locations

        except Exception as e:
            LawyerService.logger.error(f"Error getting unique locations: {str(e)}")
            # Fallback 데이터 (nomusa 더미 데이터 기반)
            return [
                "고양", "광주", "대구", "대전", "마산", "부산", "부천",
                "서울", "성남", "수원", "안산", "안양", "용인", "울산",
                "인천", "전주", "창원", "천안", "청주", "포항"
            ]

    @staticmethod
    def _simplify_address(full_address: str) -> str:
        """주소를 location_district 형식으로 간소화"""
        if not full_address:
            return ""

        parts = full_address.split(' ')
        if len(parts) < 2:
            return full_address

        city = parts[0]
        if '특별시' in city:
            city = city.replace('특별시', '')
        elif '광역시' in city:
            city = city.replace('광역시', '')
        elif '도' in city:
            city = city.replace('도', '')

        second_part = parts[1]

        # "성남시" 같은 경우 처리
        if '시' in second_part and ('구' not in second_part and '군' not in second_part):
            if len(parts) >= 3:
                district = parts[2]
                if '구' in district or '군' in district:
                    return f"{second_part.replace('시', '')} {district}"
                else:
                    return f"{second_part.replace('시', '')} {district}구"
            else:
                return second_part
        else:
            # "인천 중구" 같은 경우
            return f"{city} {second_part}"


class ConsultationService:
    """상담 관리 서비스"""

    @staticmethod
    async def create_consultation(
        client_id: str,
        lawyer_id: str,
        consultation_type: str,
        scheduled_at: datetime,
        application_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """상담 예약 생성"""
        try:
            # XSS 방어
            if notes:
                notes = security.sanitize_text(notes)

            # 노무사 존재 및 활성화 확인
            lawyer = await LawyerService.get_lawyer_by_id(lawyer_id)
            if not lawyer or not lawyer.get("is_verified"):
                LawyerService.logger.warning(f"Attempt to book consultation with unverified lawyer: {lawyer_id}")
                return None

            # 시간 중복 확인
            existing = supabase.table("consultations").select("id").eq("lawyer_id", lawyer_id).eq("scheduled_at", scheduled_at.isoformat()).eq("status", "accepted").execute()

            if existing.data:
                LawyerService.logger.warning(f"Consultation time conflict for lawyer {lawyer_id} at {scheduled_at}")
                return None

            consultation_data = {
                "client_id": client_id,
                "lawyer_id": lawyer_id,
                "application_id": application_id,
                "consultation_type": consultation_type,
                "scheduled_at": scheduled_at.isoformat(),
                "notes": notes,
                "consultation_fee": lawyer.get("consultation_fee", 0),
                "status": "requested",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = supabase.table("consultations").insert(consultation_data).execute()

            if result.data:
                LawyerService.logger.info(f"Consultation created: {result.data[0]['id']}")
                return result.data[0]
            return None

        except Exception as e:
            LawyerService.logger.error(f"Error creating consultation: {str(e)}")
            return None

    @staticmethod
    async def get_consultation_by_id(consultation_id: str, include_relations: bool = True) -> Optional[Dict[str, Any]]:
        """상담 ID로 조회"""
        try:
            query = supabase.table("consultations").select("*")

            if include_relations:
                query = query.select("*, client:users!client_id(*), lawyer:users!lawyer_id(*), application:compensation_applications(*)")

            result = query.eq("id", consultation_id).eq("is_active", True).single().execute()

            if result.data:
                return result.data
            return None

        except Exception as e:
            LawyerService.logger.error(f"Error getting consultation {consultation_id}: {str(e)}")
            return None

    @staticmethod
    async def get_consultations_by_client(
        client_id: str,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """클라이언트의 상담 목록 조회"""
        try:
            query = supabase.table("consultations").select("*, lawyer:users!lawyer_id(*), application:compensation_applications(*)", count="exact")

            query = query.eq("client_id", client_id).eq("is_active", True)

            if status:
                query = query.eq("status", status)

            query = query.order("created_at", desc=True)

            # 페이지네이션
            offset = (page - 1) * size
            query = query.range(offset, offset + size - 1)

            result = query.execute()

            consultations = result.data or []
            total = result.count or 0

            return consultations, total

        except Exception as e:
            LawyerService.logger.error(f"Error getting consultations for client {client_id}: {str(e)}")
            return [], 0

    @staticmethod
    async def get_consultations_by_lawyer(
        lawyer_id: str,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """노무사의 상담 목록 조회"""
        try:
            query = supabase.table("consultations").select("*, client:users!client_id(*), application:compensation_applications(*)", count="exact")

            query = query.eq("lawyer_id", lawyer_id).eq("is_active", True)

            if status:
                query = query.eq("status", status)

            query = query.order("created_at", desc=True)

            # 페이지네이션
            offset = (page - 1) * size
            query = query.range(offset, offset + size - 1)

            result = query.execute()

            consultations = result.data or []
            total = result.count or 0

            return consultations, total

        except Exception as e:
            LawyerService.logger.error(f"Error getting consultations for lawyer {lawyer_id}: {str(e)}")
            return [], 0

    @staticmethod
    async def update_consultation_status(
        consultation_id: str,
        user_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """상담 상태 업데이트"""
        try:
            # 상담 정보 조회 및 권한 확인
            consultation = await ConsultationService.get_consultation_by_id(consultation_id)
            if not consultation:
                return None

            # 클라이언트 또는 노무사만 상태 변경 가능
            if user_id not in [consultation.get("client_id"), consultation.get("lawyer_id")]:
                LawyerService.logger.warning(f"Unauthorized consultation status update: {user_id}")
                return None

            # 상태 전이 검증 (NOTE.md #28)
            current_status = consultation.get("status")
            valid_transitions = {
                "requested": ["accepted", "rejected", "cancelled"],
                "accepted": ["completed", "cancelled"],
                "rejected": [],
                "completed": [],
                "cancelled": []
            }

            if status not in valid_transitions.get(current_status, []):
                LawyerService.logger.warning(f"Invalid status transition: {current_status} -> {status}")
                return None

            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            if notes:
                update_data["notes"] = security.sanitize_text(notes)

            result = supabase.table("consultations").update(update_data).eq("id", consultation_id).execute()

            if result.data:
                LawyerService.logger.info(f"Consultation status updated: {consultation_id} -> {status}")
                return result.data[0]
            return None

        except Exception as e:
            LawyerService.logger.error(f"Error updating consultation status {consultation_id}: {str(e)}")
            return None

    @staticmethod
    async def check_user_permission(user_id: str, consultation_id: str) -> bool:
        """상담 관련 사용자 권한 확인"""
        try:
            consultation = await ConsultationService.get_consultation_by_id(consultation_id, include_relations=False)
            if not consultation:
                return False

            return user_id in [consultation.get("client_id"), consultation.get("lawyer_id")]

        except Exception as e:
            LawyerService.logger.error(f"Error checking consultation permission: {str(e)}")
            return False