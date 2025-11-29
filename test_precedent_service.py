#!/usr/bin/env python3
"""
PrecedentSearchService 하이브리드 서비스 테스트
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from app.services.precedent_search_service import (
    PrecedentSearchService,
    get_precedent_service,
    hybrid_precedent_search,
    quick_precedent_search
)

async def test_service_initialization():
    """서비스 초기화 테스트"""
    print("🔧 서비스 초기화 테스트")
    print("-" * 60)

    service = PrecedentSearchService()

    # 통계 확인
    stats = service.get_search_statistics()
    print("📊 서비스 통계:")
    print(f"  서비스명: {stats.get('service_name')}")
    print(f"  버전: {stats.get('version')}")

    capabilities = stats.get('capabilities', {})
    print("🔧 서비스 기능:")
    print(f"  TF-IDF 검색: {'✅' if capabilities.get('tfidf_search') else '❌'}")
    print(f"  RAG 분석: {'✅' if capabilities.get('rag_analysis') else '❌'}")
    print(f"  하이브리드 검색: {'✅' if capabilities.get('hybrid_search') else '❌'}")

    if 'tfidf_statistics' in stats:
        tfidf_stats = stats['tfidf_statistics']
        if 'error' not in tfidf_stats:
            print(f"\n📚 TF-IDF 데이터:")
            print(f"  총 판례 수: {tfidf_stats.get('total_cases', 'N/A'):,}")
            print(f"  어휘 크기: {tfidf_stats.get('vocabulary_size', 'N/A'):,}")

    return service

async def test_quick_search(service):
    """빠른 검색 테스트"""
    print("\n🚀 빠른 검색 테스트")
    print("-" * 60)

    test_queries = [
        "작업 중 손가락 다침",
        "추락 사고로 머리 부상",
        "기계 조작 중 절단 사고"
    ]

    for query in test_queries:
        print(f"\n🔍 검색어: '{query}'")

        try:
            results = await service.quick_search(query, top_k=3)
            print(f"  📊 결과 수: {len(results)}개")

            if results:
                print(f"  🎯 평균 유사도: {sum(r.similarity for r in results) / len(results):.3f}")
                print("  📋 상위 결과:")
                for i, result in enumerate(results, 1):
                    print(f"    {i}. [{result.similarity:.3f}] {result.title[:40]}...")

        except Exception as e:
            print(f"  ❌ 오류: {e}")

async def test_hybrid_search(service):
    """하이브리드 검색 테스트"""
    print("\n🔄 하이브리드 검색 테스트")
    print("-" * 60)

    query = "프레스 작업 중 손목 부상"
    print(f"🔍 검색어: '{query}'")

    try:
        # RAG 분석 제외하고 빠른 테스트
        result = await service.hybrid_search(
            query=query,
            tfidf_top_k=5,
            include_rag_analysis=False,  # 빠른 테스트를 위해 RAG 제외
            timeout_seconds=10
        )

        print(f"\n⏱️  처리 시간: {result.total_processing_time:.2f}초")
        print(f"📊 TF-IDF 결과 수: {len(result.tfidf_results)}개")
        print(f"🎯 신뢰도 점수: {result.confidence_score:.2f}")
        print(f"💡 권고사항: {result.recommendation}")

        # 통합 인사이트 확인
        print(f"\n🔍 통합 인사이트:")
        insights = result.combined_insights

        if 'tfidf_analysis' in insights:
            tfidf_analysis = insights['tfidf_analysis']
            print(f"  TF-IDF 평균 유사도: {tfidf_analysis.get('avg_similarity', 'N/A')}")
            print(f"  고유사도 결과: {tfidf_analysis.get('high_similarity_count', 'N/A')}개")

        cross_analysis = insights.get('cross_analysis', {})
        print(f"  일관성 검사: {cross_analysis.get('consistency_check', 'N/A')}")
        print(f"  상호 보완성: {cross_analysis.get('complementary_value', 'N/A')}")

        # 상위 결과 상세
        print(f"\n📋 상위 {min(3, len(result.tfidf_results))}개 결과 상세:")
        for i, tfidf_result in enumerate(result.tfidf_results[:3], 1):
            print(f"  {i}. 유사도: {tfidf_result.similarity:.3f}")
            print(f"     제목: {tfidf_result.title[:60]}...")
            print(f"     법원: {tfidf_result.court}")
            if tfidf_result.keywords:
                print(f"     키워드: {tfidf_result.keywords[:3]}")

    except Exception as e:
        print(f"❌ 하이브리드 검색 오류: {e}")
        import traceback
        traceback.print_exc()

async def test_convenience_functions():
    """편의 함수 테스트"""
    print("\n🛠️  편의 함수 테스트")
    print("-" * 60)

    # 전역 서비스 인스턴스 테스트
    print("📦 싱글톤 패턴 테스트:")
    service1 = get_precedent_service()
    service2 = get_precedent_service()
    print(f"  동일 인스턴스: {'✅' if service1 is service2 else '❌'}")

    # 편의 함수 테스트
    print(f"\n🔍 편의 함수 테스트:")
    try:
        quick_results = await quick_precedent_search("계단 추락 사고", top_k=2)
        print(f"  quick_precedent_search: {len(quick_results)}개 결과")

        # 하이브리드 편의 함수 (RAG 제외)
        hybrid_result = await hybrid_precedent_search(
            "화재 사고 화상",
            tfidf_top_k=3,
            include_rag_analysis=False,
            timeout_seconds=10
        )
        print(f"  hybrid_precedent_search: 신뢰도 {hybrid_result.confidence_score:.2f}")

    except Exception as e:
        print(f"  ❌ 편의 함수 오류: {e}")

async def test_json_serialization(service):
    """JSON 직렬화 테스트"""
    print("\n📄 JSON 직렬화 테스트")
    print("-" * 60)

    try:
        # 간단한 하이브리드 검색
        result = await service.hybrid_search(
            "낙상 사고",
            tfidf_top_k=2,
            include_rag_analysis=False
        )

        # dict 변환
        result_dict = service.to_dict(result)
        print(f"✅ JSON 직렬화 성공")
        print(f"  키 개수: {len(result_dict)}")
        print(f"  TF-IDF 결과: {len(result_dict.get('tfidf_results', []))}개")

        # JSON 출력 테스트
        import json
        json_str = json.dumps(result_dict, ensure_ascii=False, indent=2)
        print(f"  JSON 크기: {len(json_str)}바이트")

    except Exception as e:
        print(f"❌ JSON 직렬화 오류: {e}")

async def main():
    """메인 테스트 함수"""
    print("🚀 PrecedentSearchService 종합 테스트\n")

    try:
        # 1. 서비스 초기화
        service = await test_service_initialization()

        # 2. 빠른 검색 테스트
        await test_quick_search(service)

        # 3. 하이브리드 검색 테스트
        await test_hybrid_search(service)

        # 4. 편의 함수 테스트
        await test_convenience_functions()

        # 5. JSON 직렬화 테스트
        await test_json_serialization(service)

        print(f"\n🎉 모든 테스트 완료!")

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())