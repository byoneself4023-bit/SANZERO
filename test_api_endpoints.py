#!/usr/bin/env python3
"""
새로운 하이브리드 검색 API 엔드포인트 테스트
"""

import requests
import json
import time

# 서버 설정
BASE_URL = "http://localhost:8000"

def test_api_endpoints():
    """새로운 API 엔드포인트 테스트"""
    print("🚀 하이브리드 검색 API 엔드포인트 테스트\n")

    # 1. 서비스 통계 확인
    print("1️⃣ 검색 서비스 통계 확인")
    print("-" * 50)

    try:
        response = requests.get(f"{BASE_URL}/analysis/api/search-stats")
        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            stats = response.json()
            print(f"✅ 서비스명: {stats.get('service_name', 'N/A')}")
            print(f"✅ 버전: {stats.get('version', 'N/A')}")

            capabilities = stats.get('capabilities', {})
            print("🔧 서비스 기능:")
            print(f"  - TF-IDF 검색: {'✅' if capabilities.get('tfidf_search') else '❌'}")
            print(f"  - RAG 분석: {'✅' if capabilities.get('rag_analysis') else '❌'}")
            print(f"  - 하이브리드: {'✅' if capabilities.get('hybrid_search') else '❌'}")

            if 'tfidf_statistics' in stats:
                tfidf_stats = stats['tfidf_statistics']
                print(f"📊 총 판례: {tfidf_stats.get('total_cases', 'N/A'):,}개")
                print(f"📚 어휘 크기: {tfidf_stats.get('vocabulary_size', 'N/A'):,}개")
        else:
            print(f"❌ 통계 조회 실패: {response.text}")

    except Exception as e:
        print(f"❌ 통계 API 오류: {e}")

    time.sleep(1)

    # 2. 빠른 검색 API 테스트
    print(f"\n2️⃣ 빠른 검색 API 테스트")
    print("-" * 50)

    try:
        data = {
            "query": "작업 중 손가락 절단 사고",
            "top_k": 3
        }

        response = requests.post(f"{BASE_URL}/analysis/api/quick-search", data=data)
        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 검색어: {result.get('query')}")
            print(f"✅ 결과 수: {result.get('total_found')}개")
            print(f"✅ 처리 시간: {result.get('processing_time')}")

            results = result.get('results', [])
            print("📋 검색 결과:")
            for i, case in enumerate(results, 1):
                print(f"  {i}. [{case.get('similarity', 0):.3f}] {case.get('title', 'Unknown')[:50]}...")
        else:
            print(f"❌ 빠른 검색 실패: {response.text}")

    except Exception as e:
        print(f"❌ 빠른 검색 API 오류: {e}")

    time.sleep(1)

    # 3. 하이브리드 검색 API 테스트
    print(f"\n3️⃣ 하이브리드 검색 API 테스트")
    print("-" * 50)

    try:
        data = {
            "query": "프레스 작업 중 손목 부상",
            "tfidf_top_k": 5,
            "include_rag_analysis": False,  # 빠른 테스트를 위해 RAG 제외
            "timeout_seconds": 10
        }

        start_time = time.time()
        response = requests.post(f"{BASE_URL}/analysis/api/hybrid-search", data=data)
        request_time = time.time() - start_time

        print(f"상태 코드: {response.status_code}")
        print(f"요청 시간: {request_time:.2f}초")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 검색어: {result.get('query')}")
            print(f"✅ 총 처리 시간: {result.get('total_processing_time', 0):.2f}초")
            print(f"✅ TF-IDF 결과: {len(result.get('tfidf_results', []))}개")
            print(f"✅ 신뢰도 점수: {result.get('confidence_score', 0):.2f}")
            print(f"💡 권고사항: {result.get('recommendation', 'N/A')[:100]}...")

            # 통합 인사이트
            insights = result.get('combined_insights', {})
            tfidf_analysis = insights.get('tfidf_analysis', {})
            print(f"📊 평균 유사도: {tfidf_analysis.get('avg_similarity', 'N/A')}")
            print(f"📊 고유사도 결과: {tfidf_analysis.get('high_similarity_count', 'N/A')}개")

        else:
            print(f"❌ 하이브리드 검색 실패: {response.text}")

    except Exception as e:
        print(f"❌ 하이브리드 검색 API 오류: {e}")

    time.sleep(1)

    # 4. JSON API 테스트 (AJAX용)
    print(f"\n4️⃣ JSON API 테스트 (AJAX용)")
    print("-" * 50)

    try:
        # JSON으로 데이터 전송
        data = {
            "query": "추락 사고 머리 부상",
            "top_k": 3
        }

        response = requests.post(
            f"{BASE_URL}/analysis/api/precedent/quick",
            json=data,  # JSON으로 전송
            headers={"Content-Type": "application/json"}
        )

        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 검색어: {result.get('query')}")
            print(f"✅ 총 결과: {result.get('total')}개")

            results = result.get('results', [])
            print("📋 JSON API 결과:")
            for i, case in enumerate(results, 1):
                print(f"  {i}. [{case.get('similarity', 0):.3f}] {case.get('title', 'Unknown')[:40]}...")
        else:
            print(f"❌ JSON API 실패: {response.text}")

    except Exception as e:
        print(f"❌ JSON API 오류: {e}")

def test_error_handling():
    """에러 처리 테스트"""
    print(f"\n5️⃣ 에러 처리 테스트")
    print("-" * 50)

    # 빈 쿼리 테스트
    try:
        data = {"query": "", "top_k": 3}
        response = requests.post(f"{BASE_URL}/analysis/api/quick-search", data=data)
        print(f"빈 쿼리 테스트 - 상태 코드: {response.status_code}")

        if response.status_code != 200:
            print(f"✅ 빈 쿼리 적절히 처리됨")
        else:
            print(f"⚠️ 빈 쿼리가 처리됨: {response.json()}")

    except Exception as e:
        print(f"빈 쿼리 테스트 오류: {e}")

def test_performance():
    """성능 테스트"""
    print(f"\n6️⃣ 성능 테스트")
    print("-" * 50)

    test_queries = [
        "프레스 작업 중 손가락 절단",
        "추락 사고로 인한 다리 골절",
        "기계 조작 중 끼임 사고"
    ]

    times = []

    for i, query in enumerate(test_queries, 1):
        try:
            data = {"query": query, "top_k": 5}

            start_time = time.time()
            response = requests.post(f"{BASE_URL}/analysis/api/quick-search", data=data)
            request_time = time.time() - start_time

            times.append(request_time)

            if response.status_code == 200:
                result = response.json()
                print(f"  {i}. [{request_time:.2f}s] {query} → {result.get('total_found', 0)}개 결과")
            else:
                print(f"  {i}. [{request_time:.2f}s] {query} → 오류")

        except Exception as e:
            print(f"  {i}. 테스트 오류: {e}")

    if times:
        avg_time = sum(times) / len(times)
        print(f"\n📊 평균 응답 시간: {avg_time:.2f}초")
        print(f"📊 최빠른 응답: {min(times):.2f}초")
        print(f"📊 최느린 응답: {max(times):.2f}초")

if __name__ == "__main__":
    print("🔍 SANZERO 하이브리드 검색 API 종합 테스트\n")

    # 기본 API 테스트
    test_api_endpoints()

    # 에러 처리 테스트
    test_error_handling()

    # 성능 테스트
    test_performance()

    print(f"\n🎉 모든 API 테스트 완료!")