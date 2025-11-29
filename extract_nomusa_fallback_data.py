#!/usr/bin/env python3
"""
nomusa 더미 데이터에서 전문분야와 지역 데이터 추출
"""

import json
from pathlib import Path

def extract_fallback_data():
    """nomusa 더미 데이터에서 fallback 데이터 추출"""

    # nomusa 더미 데이터 로드
    nomusa_file = Path(__file__).parent / "app" / "nomusa_dummy_data.json"
    with open(nomusa_file, 'r', encoding='utf-8') as f:
        nomusa_data = json.load(f)

    print(f"총 {len(nomusa_data)}개의 노무사 데이터 로드됨")

    # 전문분야 추출
    all_specialties = []
    for lawyer in nomusa_data:
        specialty_area = lawyer.get("specialty_area", [])
        if isinstance(specialty_area, list):
            all_specialties.extend(specialty_area)
        else:
            all_specialties.append(specialty_area)

    unique_specialties = sorted(list(set(all_specialties)))
    print(f"\n고유 전문분야 {len(unique_specialties)}개:")
    for i, spec in enumerate(unique_specialties, 1):
        print(f"  {i:2d}. {spec}")

    # 지역 추출
    all_locations = []
    for lawyer in nomusa_data:
        location_district = lawyer.get("location_district", "")
        if location_district:
            # "서울 양천구" -> "서울"만 추출
            city = location_district.split()[0] if location_district.split() else location_district
            all_locations.append(city)

    unique_locations = sorted(list(set(all_locations)))
    print(f"\n고유 지역 {len(unique_locations)}개:")
    for i, loc in enumerate(unique_locations, 1):
        print(f"  {i:2d}. {loc}")

    # fallback 데이터 생성 (처음 5개 노무사)
    fallback_lawyers = []
    for i, lawyer in enumerate(nomusa_data[:5]):
        fallback_lawyer = {
            "id": f"nomusa-{i+1}",
            "office_name": f"{lawyer['name']} 노무사 사무소",
            "license_number": f"LAW-2024-{i+1:04d}",
            "office_address": lawyer["location_district"],
            "specialties": lawyer["specialty_area"],
            "experience_years": 5 + (i * 2),  # 5, 7, 9, 11, 13년
            "success_rate": lawyer["avg_success_rate_pct"],
            "rating": 4.0 + (i * 0.2),  # 4.0, 4.2, 4.4, 4.6, 4.8
            "case_count": 50 + (i * 25),  # 50, 75, 100, 125, 150
            "consultation_fee": 100000 if "착수금" in lawyer.get("fee_policy", "") else 0,
            "is_verified": True,
            "is_online_consult": "가능" in lawyer.get("is_online_consult", []),
            "supports_sanzero_pay": "가능" in lawyer.get("do_sanzeropay", []),
            "phone": lawyer.get("contact_phone", ""),
            "website_url": lawyer.get("website_url", ""),
            "fee_policy": lawyer.get("fee_policy", ""),
            "case_difficulty": lawyer.get("case_difficulty", "중"),
            "simplified_address": lawyer["location_district"],
            "user": {
                "full_name": lawyer["name"]
            }
        }
        fallback_lawyers.append(fallback_lawyer)

    print(f"\nfallback 노무사 {len(fallback_lawyers)}명 생성:")
    for lawyer in fallback_lawyers:
        print(f"  - {lawyer['office_name']} ({lawyer['office_address']}) - {lawyer['specialties']}")

    # Python 코드 형태로 출력
    print(f"\n" + "="*80)
    print("PYTHON 코드 (LawyerService에 붙여넣기용):")
    print("="*80)

    print("# 전문분야 fallback 데이터:")
    print("unique_specialties =", json.dumps(unique_specialties, ensure_ascii=False, indent=4))

    print("\n# 지역 fallback 데이터:")
    print("unique_locations =", json.dumps(unique_locations, ensure_ascii=False, indent=4))

    print("\n# 노무사 fallback 데이터:")
    print("fallback_lawyers =", json.dumps(fallback_lawyers, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    extract_fallback_data()