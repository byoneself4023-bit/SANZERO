"""
테스트 사용자 계정 생성 스크립트

TESTDATA.md에 정의된 모든 테스트 계정을 Supabase에 생성합니다.
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.database import supabase


# 테스트 계정 데이터
TEST_USERS = [
    {
        "email": "byoneself4023@ajou.ac.kr",
        "password": "rlarlduf0",
        "username": "Kuka",
        "user_type": "admin",
        "phone": "010-0000-0001",
        "address": "경기도 수원시 영통구 월드컵로 206"
    },
    {
        "email": "testuser@example.com",
        "password": "test123456!",
        "username": "testuser",
        "user_type": "general",
        "phone": "010-1234-5678",
        "address": "서울시 강남구 테스트동 123번지"
    },
    {
        "email": "lawyer@example.com",
        "password": "lawyer123456!",
        "username": "testlawyer",
        "user_type": "lawyer",
        "phone": "010-9999-0001",
        "address": "서울시 서초구 법조로 123",
        "lawyer_info": {
            "license_number": "LAW-2024-001",
            "office_name": "테스트 노무사 사무소",
            "office_address": "서울시 서초구 법조로 123",
            "specialties": ["산업재해", "근로기준법", "산업안전"],
            "experience_years": 5,
            "consultation_fee": 100000,
            "rating": 4.5,
            "total_reviews": 10,
            "is_verified": True
        }
    }
]


async def create_test_users():
    """테스트 사용자 생성"""
    print("=== 테스트 사용자 생성 시작 ===\n")

    for user_data in TEST_USERS:
        email = user_data["email"]
        print(f"🔄 {email} 생성 중...")

        try:
            # 1. Supabase Auth 계정 생성
            auth_response = supabase.auth.admin.create_user({
                "email": email,
                "password": user_data["password"],
                "email_confirm": True  # 이메일 확인 건너뛰기
            })

            if not auth_response.user:
                print(f"❌ {email} Auth 계정 생성 실패")
                continue

            user_id = auth_response.user.id
            print(f"   ✅ Auth 계정 생성 완료 (ID: {user_id})")

            # 2. users 테이블에 프로필 생성
            profile_data = {
                "id": user_id,
                "email": email,
                "username": user_data["username"],
                "user_type": user_data["user_type"],
                "phone": user_data.get("phone"),
                "address": user_data.get("address")
            }

            profile_response = supabase.table("users").insert(profile_data).execute()

            if profile_response.data:
                print(f"   ✅ 프로필 생성 완료")
            else:
                print(f"   ⚠️  프로필 생성 실패")

            # 3. 노무사 계정인 경우 lawyers 테이블에 추가
            if user_data["user_type"] == "lawyer" and "lawyer_info" in user_data:
                lawyer_info = user_data["lawyer_info"]
                lawyer_data = {
                    "user_id": user_id,
                    "license_number": lawyer_info["license_number"],
                    "office_name": lawyer_info["office_name"],
                    "office_address": lawyer_info["office_address"],
                    "specialties": lawyer_info["specialties"],
                    "experience_years": lawyer_info["experience_years"],
                    "consultation_fee": lawyer_info["consultation_fee"],
                    "rating": lawyer_info["rating"],
                    "total_reviews": lawyer_info["total_reviews"],
                    "is_verified": lawyer_info["is_verified"]
                }

                lawyer_response = supabase.table("lawyers").insert(lawyer_data).execute()

                if lawyer_response.data:
                    print(f"   ✅ 노무사 정보 생성 완료")
                else:
                    print(f"   ⚠️  노무사 정보 생성 실패")

            print(f"✅ {email} 계정 생성 완료\n")

        except Exception as e:
            error_message = str(e)
            if "already exists" in error_message or "duplicate" in error_message.lower():
                print(f"⚠️  {email} 이미 존재하는 계정\n")
            else:
                print(f"❌ {email} 생성 중 오류 발생: {error_message}\n")

    print("=== 테스트 사용자 생성 완료 ===")


async def verify_users():
    """생성된 사용자 확인"""
    print("\n=== 생성된 사용자 확인 ===\n")

    for user_data in TEST_USERS:
        email = user_data["email"]

        # users 테이블에서 확인
        result = supabase.table("users").select("id, email, username, user_type").eq("email", email).execute()

        if result.data:
            user = result.data[0]
            print(f"✅ {email}")
            print(f"   - Username: {user['username']}")
            print(f"   - User Type: {user['user_type']}")
            print(f"   - ID: {user['id']}")

            # 노무사 계정인 경우 lawyers 테이블 확인
            if user['user_type'] == 'lawyer':
                lawyer_result = supabase.table("lawyers").select("license_number, office_name, is_verified").eq("user_id", user['id']).execute()

                if lawyer_result.data:
                    lawyer = lawyer_result.data[0]
                    print(f"   - License: {lawyer['license_number']}")
                    print(f"   - Office: {lawyer['office_name']}")
                    print(f"   - Verified: {lawyer['is_verified']}")

            print()
        else:
            print(f"❌ {email} - 계정을 찾을 수 없습니다.\n")

    print("=== 확인 완료 ===")


if __name__ == "__main__":
    print("SANZERO 테스트 계정 생성 스크립트\n")

    # 사용자 생성
    asyncio.run(create_test_users())

    # 생성 확인
    asyncio.run(verify_users())
