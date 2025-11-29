#!/usr/bin/env python3
"""
노무사 검색 페이지 드롭다운 데이터 문제 진단 스크립트
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import asyncio
from app.services.lawyer_service import LawyerService
from app.utils.database import supabase

async def test_dropdown_data():
    """드롭다운 데이터 테스트"""

    print("=== 노무사 데이터 상태 진단 ===\n")

    try:
        # 1. 기본 노무사 데이터 확인
        print("1. 기본 노무사 데이터 확인...")
        lawyers_result = supabase.table('lawyers').select('id, office_name, specialties, office_address, is_active').limit(3).execute()
        print(f"  - 노무사 데이터 샘플 ({len(lawyers_result.data)}개):")
        for lawyer in lawyers_result.data:
            print(f"    * {lawyer.get('office_name', 'N/A')} | 활성: {lawyer.get('is_active', False)}")
            print(f"      전문분야: {lawyer.get('specialties', [])}")
            print(f"      주소: {lawyer.get('office_address', 'N/A')}")
        print()

        # 2. 전문분야 데이터 확인
        print("2. 전문분야 데이터 확인...")
        unique_specialties = await LawyerService.get_unique_specialties()
        print(f"  - 고유 전문분야 개수: {len(unique_specialties)}")
        if unique_specialties:
            print(f"  - 전문분야 샘플 (처음 10개): {unique_specialties[:10]}")
        else:
            print(f"  - 전문분야 없음!")
        print()

        # 3. 지역 데이터 확인
        print("3. 지역 데이터 확인...")
        unique_locations = await LawyerService.get_unique_locations()
        print(f"  - 고유 지역 개수: {len(unique_locations)}")
        if unique_locations:
            print(f"  - 지역 샘플: {unique_locations}")
        else:
            print(f"  - 지역 없음!")
        print()

        # 4. 검색 테스트 (빈 검색)
        print("4. 기본 검색 테스트...")
        lawyers, total = await LawyerService.search_lawyers(
            specialties=None,
            location=None,
            is_verified=True,
            page=1,
            size=5
        )
        print(f"  - 검색 결과: {total}명의 노무사")
        print(f"  - 반환된 데이터: {len(lawyers)}개")
        for lawyer in lawyers[:3]:
            print(f"    * {lawyer.get('office_name', 'N/A')} | 성공률: {lawyer.get('success_rate', 0)}%")
        print()

        # 5. 특정 전문분야 검색 테스트
        if unique_specialties:
            test_specialty = unique_specialties[0] if unique_specialties else None
            print(f"5. 전문분야 검색 테스트 ('{test_specialty}')...")
            lawyers, total = await LawyerService.search_lawyers(
                specialties=[test_specialty] if test_specialty else None,
                is_verified=True,
                page=1,
                size=5
            )
            print(f"  - 검색 결과: {total}명의 노무사")
            print(f"  - 반환된 데이터: {len(lawyers)}개")
            print()

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    asyncio.run(test_dropdown_data())

if __name__ == "__main__":
    main()