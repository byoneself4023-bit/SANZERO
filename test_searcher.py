#!/usr/bin/env python3
"""
Searcher 모듈 기능 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from app.services.searcher import WorkInjuryCaseSearcher, get_searcher

def test_searcher_loading():
    """Searcher 로딩 테스트"""
    print("🔍 Searcher 모듈 로딩 테스트 시작")

    searcher = WorkInjuryCaseSearcher()

    # 모델 로딩
    print("⏳ 모델 로딩 중...")
    success = searcher.load_model()

    if success:
        print("✅ 모델 로딩 성공!")

        # 통계 확인
        stats = searcher.get_statistics()
        print(f"📊 총 판례 수: {stats.get('total_cases', 'N/A'):,}개")
        print(f"📚 어휘 크기: {stats.get('vocabulary_size', 'N/A'):,}개")
        print(f"🔧 토크나이저: {stats.get('tokenizer_type', 'N/A')}")

        # 데이터프레임 컬럼 확인
        if 'available_columns' in stats:
            print(f"📋 사용 가능한 컬럼: {stats['available_columns']}")

        return searcher
    else:
        print("❌ 모델 로딩 실패")
        return None

def test_search(searcher):
    """검색 기능 테스트"""
    if not searcher:
        return

    print("\n🔍 검색 기능 테스트")

    # 테스트 쿼리들
    test_queries = [
        "작업 중 손가락 다침",
        "추락 사고 머리 부상",
        "기계 조작 중 절단",
        "프레스 작업 손목"
    ]

    for query in test_queries:
        print(f"\n🔎 검색 쿼리: '{query}'")

        try:
            results = searcher.search(query, top_k=3)
            print(f"   📊 결과 수: {len(results)}개")

            for i, result in enumerate(results, 1):
                print(f"   {i}. 유사도: {result.similarity:.3f}")
                print(f"      제목: {result.title[:50]}...")
                print(f"      법원: {result.court}")

        except Exception as e:
            print(f"   ❌ 검색 오류: {e}")

def test_report_generation(searcher):
    """보고서 생성 테스트"""
    if not searcher:
        return

    print("\n📋 보고서 생성 테스트")

    query = "작업 중 손가락 절단 사고"
    print(f"📝 보고서 쿼리: '{query}'")

    try:
        report = searcher.generate_report(query, top_n=3)

        print(f"   📊 총 결과 수: {report.get('total_results', 'N/A')}개")
        print(f"   🎯 평균 유사도: {report.get('average_similarity', 'N/A')}")
        print(f"   🏛️ 법원 분포: {report.get('court_distribution', {})}")

        if 'key_keywords' in report:
            keywords = report['key_keywords'][:5]  # 상위 5개만
            print(f"   🔑 주요 키워드: {[k['keyword'] for k in keywords]}")

        print(f"   💡 권고사항: {report.get('recommendation', 'N/A')}")

    except Exception as e:
        print(f"   ❌ 보고서 생성 오류: {e}")

def test_singleton_pattern():
    """싱글톤 패턴 테스트"""
    print("\n🔧 싱글톤 패턴 테스트")

    try:
        searcher1 = get_searcher()
        searcher2 = get_searcher()

        print(f"   📍 인스턴스 1 ID: {id(searcher1)}")
        print(f"   📍 인스턴스 2 ID: {id(searcher2)}")
        print(f"   ✅ 동일 인스턴스: {searcher1 is searcher2}")

        # 로딩 상태 확인
        print(f"   📊 로딩 상태: {searcher1.is_loaded}")

    except Exception as e:
        print(f"   ❌ 싱글톤 테스트 오류: {e}")

if __name__ == "__main__":
    print("🚀 WorkInjuryCaseSearcher 종합 테스트 시작\n")

    # 1. 로딩 테스트
    searcher = test_searcher_loading()

    # 2. 검색 테스트
    test_search(searcher)

    # 3. 보고서 테스트
    test_report_generation(searcher)

    # 4. 싱글톤 테스트
    test_singleton_pattern()

    print("\n🎉 테스트 완료!")