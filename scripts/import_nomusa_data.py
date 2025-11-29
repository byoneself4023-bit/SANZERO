"""
nomusa_dummy_data.json을 Supabase lawyers 테이블로 마이그레이션하는 스크립트
"""
import json
import os
import sys
import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.database import supabase


class NomusaDataMigrator:
    def __init__(self):
        self.nomusa_data_file = project_root / "app" / "nomusa_dummy_data.json"

    def load_nomusa_data(self):
        """nomusa_dummy_data.json 파일 로드"""
        try:
            with open(self.nomusa_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ nomusa 데이터 로드 완료: {len(data)}명의 노무사")
                return data
        except Exception as e:
            print(f"❌ nomusa 데이터 로드 실패: {e}")
            return []

    def extract_case_difficulty_years(self, case_difficulty):
        """case_difficulty를 경력 년수로 변환"""
        difficulty_map = {
            "상": 10,
            "중상": 8,
            "중": 5,
            "중하": 3,
            "하": 1
        }
        return difficulty_map.get(case_difficulty, 5)

    def parse_fee_policy(self, fee_policy):
        """fee_policy를 consultation_fee로 변환"""
        if "착수금 0원" in fee_policy:
            return 0
        elif "착수금 100만원" in fee_policy:
            return 1000000
        elif "초기 상담 무료" in fee_policy:
            return 0
        else:
            return 100000  # 기본값 10만원

    def generate_license_number(self, index, name):
        """노무사 면허번호 자동 생성"""
        return f"LAW-2024-{str(index + 1).zfill(4)}"

    def generate_temp_user_id(self):
        """임시 UUID 생성"""
        return str(uuid.uuid4())

    def calculate_rating(self, success_rate):
        """성공률을 기반으로 평점 계산 (1-5점)"""
        if success_rate >= 85:
            return 5.0
        elif success_rate >= 75:
            return 4.5
        elif success_rate >= 65:
            return 4.0
        elif success_rate >= 55:
            return 3.5
        else:
            return 3.0

    def generate_office_address(self, location_district):
        """지역 정보를 상세 주소로 확장"""
        address_map = {
            "서울 양천구": "서울특별시 양천구 목동서로 123",
            "성남 중원구": "경기도 성남시 중원구 성남대로 456",
            "천안 동남구": "충청남도 천안시 동남구 천안대로 789",
            "서울 강남구": "서울특별시 강남구 테헤란로 100",
            "부산 해운대구": "부산광역시 해운대구 해운대로 200",
            "대구 중구": "대구광역시 중구 동성로 300"
        }

        return address_map.get(location_district, f"{location_district} 000번길 123")

    def convert_nomusa_to_lawyer_data(self, nomusa_item, index):
        """nomusa 데이터를 lawyers 테이블 형식으로 변환"""

        # 기본 변환
        experience_years = self.extract_case_difficulty_years(nomusa_item["case_difficulty"])
        consultation_fee = self.parse_fee_policy(nomusa_item["fee_policy"])
        license_number = self.generate_license_number(index, nomusa_item["name"])
        rating = self.calculate_rating(nomusa_item["avg_success_rate_pct"])
        office_address = self.generate_office_address(nomusa_item["location_district"])

        # 온라인 상담 가능 여부
        is_online_available = nomusa_item["is_online_consult"][0] == "가능" if nomusa_item["is_online_consult"] else False

        # 사무소명 생성
        office_name = f"{nomusa_item['name']} 노무사 사무소"

        # 임시 user_id 생성 (실제 서비스에서는 사용자 등록 후 연결)
        temp_user_id = self.generate_temp_user_id()

        return {
            "user_id": "4dfb3123-7d40-4397-b7f5-fb80e899bc92",  # 기존 testlawyer 사용자 ID 사용
            "license_number": license_number,
            "office_name": office_name,
            "office_address": office_address,
            "specialties": nomusa_item["specialty_area"],  # 배열 그대로 사용
            "experience_years": experience_years,
            "rating": rating,
            "total_reviews": 0,  # 신규 노무사는 리뷰 없음
            "consultation_fee": consultation_fee,
            "success_rate": float(nomusa_item["avg_success_rate_pct"]),
            "avg_compensation_amount": 0,  # 기본값
            "case_count": 0,  # 기본값
            "response_time_hours": 24,  # 기본값 24시간
            "industry_experience": None,
            "case_types": None,
            "availability_schedule": None,
            "is_verified": True,  # 모든 nomusa 데이터는 인증된 것으로 처리
            "is_active": True,
            # 새로 추가된 nomusa 필드들
            "phone": nomusa_item.get("contact_phone", ""),
            "fee_policy": nomusa_item.get("fee_policy", ""),
            "is_online_consult": is_online_available,
            "website_url": nomusa_item.get("website_url", ""),
            "supports_sanzero_pay": nomusa_item.get("do_sanzeropay", [None])[0] == "가능" if nomusa_item.get("do_sanzeropay") else False,
            "case_difficulty": nomusa_item.get("case_difficulty", "중"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    async def migrate_to_supabase(self, nomusa_data):
        """nomusa 데이터를 Supabase로 마이그레이션"""

        # 1. 노무사 프로필 데이터 생성
        print("🔄 노무사 프로필 데이터 생성 중...")
        lawyers_data = []

        for i, nomusa_item in enumerate(nomusa_data):
            lawyer_data = self.convert_nomusa_to_lawyer_data(nomusa_item, i)
            lawyers_data.append(lawyer_data)

        print(f"✅ {len(lawyers_data)}개 노무사 데이터 변환 완료")

        # 2. 배치 삽입
        batch_size = 50  # 배치 크기
        success_count = 0

        for i in range(0, len(lawyers_data), batch_size):
            batch = lawyers_data[i:i + batch_size]

            try:
                response = supabase.table("lawyers").insert(batch).execute()

                if response.data:
                    success_count += len(response.data)
                    print(f"✅ 배치 {i//batch_size + 1} 완료: {len(response.data)}명 추가")
                else:
                    print(f"❌ 배치 {i//batch_size + 1} 실패")

            except Exception as e:
                print(f"❌ 배치 {i//batch_size + 1} 오류: {e}")

        print(f"\n🎉 마이그레이션 완료!")
        print(f"📊 총 처리: {len(nomusa_data)}명")
        print(f"📊 성공 삽입: {success_count}명")

        return success_count

    async def run_migration(self):
        """전체 마이그레이션 실행"""
        print("🚀 NOMUSA 데이터 마이그레이션 시작\n")

        # 1. 데이터 로드
        nomusa_data = self.load_nomusa_data()
        if not nomusa_data:
            print("❌ 마이그레이션 중단: 데이터 없음")
            return

        # 2. 샘플 데이터 확인 (처음 3개)
        print(f"\n📋 샘플 데이터 미리보기:")
        for i, item in enumerate(nomusa_data[:3]):
            print(f"  {i+1}. {item['name']} - {item['location_district']} - {', '.join(item['specialty_area'])}")

        # 3. 자동 진행 (배치 환경)
        print(f"\n🔄 {len(nomusa_data)}명의 노무사 데이터 마이그레이션을 시작합니다...")

        # 4. 마이그레이션 실행
        success_count = await self.migrate_to_supabase(nomusa_data)

        # 5. 결과 요약
        print(f"\n📈 마이그레이션 결과:")
        print(f"   성공률: {success_count}/{len(nomusa_data)} ({success_count/len(nomusa_data)*100:.1f}%)")

        if success_count > 0:
            print(f"\n✅ Supabase lawyers 테이블에 {success_count}명의 노무사가 추가되었습니다.")
            print("🔗 이제 SANZERO 애플리케이션에서 nomusa 데이터를 활용할 수 있습니다!")


async def main():
    """메인 실행 함수"""
    migrator = NomusaDataMigrator()
    await migrator.run_migration()


if __name__ == "__main__":
    asyncio.run(main())