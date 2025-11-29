#!/usr/bin/env python3
"""
Simple Search Service - Test_casePedia.ipynb 정확한 방식 구현
기존 복잡한 검색 시스템을 대체하는 단순하고 확실한 검색 서비스
"""

import joblib
import pandas as pd
import numpy as np
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

logger = logging.getLogger(__name__)

# 전역 변수 (모델 캐싱용)
_model_loaded = False
_df = None
_vectorizer = None
_tfidf_matrix = None
_config = None

def load_searcher_model_direct() -> bool:
    """
    Test_casePedia 방식으로 searcher_model.pkl 직접 로드
    복잡한 클래스 구조 없이 단순하게 모델만 로드
    """
    global _model_loaded, _df, _vectorizer, _tfidf_matrix, _config

    if _model_loaded:
        return True

    try:
        # 모델 파일 경로
        model_path = Path(__file__).parent.parent / "searcher_model.pkl"

        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False

        logger.info(f"Loading model directly from: {model_path}")

        # joblib으로 직접 로드 (Test_casePedia 방식)
        model_data = joblib.load(model_path)

        # 전역 변수에 할당
        _df = model_data['df']
        _vectorizer = model_data['vectorizer']
        _tfidf_matrix = model_data['tfidf_matrix']
        _config = model_data.get('config', {})

        # 로드 성공 플래그
        _model_loaded = True

        logger.info(f"✅ Simple model loaded successfully: {len(_df):,} cases, "
                   f"vocabulary: {len(_vectorizer.vocabulary_):,}")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to load simple model: {e}")
        return False


def search_precedents_simple(query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Test_casePedia.ipynb의 정확한 검색 방식
    최소한의 전처리, 직접적인 유사도 계산
    """
    # 모델 로드 확인
    if not _model_loaded and not load_searcher_model_direct():
        logger.error("❌ Model could not be loaded")
        return []

    try:
        logger.info(f"Simple search started: query='{query}', top_k={top_k}")

        # 1. 최소한의 전처리 (Test_casePedia 방식)
        query_clean = re.sub(r'[^\w\s]', ' ', query)  # 특수문자 제거
        query_clean = ' '.join(query_clean.split())    # 공백 정규화

        logger.info(f"Query preprocessed: '{query}' → '{query_clean}'")

        # 2. 벡터화 (직접적으로)
        query_vector = _vectorizer.transform([query_clean])

        logger.info(f"Query vectorized: shape={query_vector.shape}")

        # 3. 유사도 계산 (Test_casePedia 정확한 방식)
        similarities = cosine_similarity(query_vector, _tfidf_matrix)[0]

        # 유사도 통계 로깅
        max_sim = np.max(similarities)
        mean_sim = np.mean(similarities)
        nonzero_count = np.count_nonzero(similarities > 0.001)

        logger.info(f"Similarities calculated: max={max_sim:.4f}, mean={mean_sim:.4f}, "
                   f"nonzero_count={nonzero_count}")

        # 4. 상위 결과 선택
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # 5. 결과 구성 (단계적 필터링 적용)
        results = []
        raw_results = []

        # 먼저 모든 의미있는 결과 수집
        for i, idx in enumerate(top_indices):
            row = _df.iloc[idx]
            similarity = similarities[idx]

            # Test_casePedia 방식: 낮은 임계값 (0.1%)
            if similarity >= 0.001:
                title = str(row.get('title', 'Unknown Title'))
                court = str(row.get('courtname', 'Unknown Court'))

                # 내용 요약 (가독성 개선)
                content = str(row.get('noncontent', ''))
                content_summary = _create_readable_summary(content)

                # 사용자 친화적인 카테고리 적용
                friendly_category = get_friendly_category(title, content)

                # 실제 컬럼 구조 기반 수정
                # kinda를 날짜로 사용 (실제 데이터에서 kinda가 날짜 정보)
                raw_date = str(row.get('kinda', 'Unknown Date'))
                formatted_date = format_court_date(raw_date)

                # 제목 요약
                summarized_title = summarize_case_title(title)

                # 추가 필드들 (실제 컬럼 구조에 맞게 수정)
                kinda = str(row.get('kinda', ''))    # 실제 판결결과 (기각, 인용, 취하 등)
                kindb = str(row.get('kindb', ''))    # 사건 분야 1 (요양, 장해 등)
                kindc = str(row.get('kindc', ''))    # 사건 분야 2 (업무상사고, 업무상질병 등)

                # 연도 추출을 content(noncontent), title에서 시도 (kinda는 판결결과이므로 제외)
                year_info = extract_year_from_text(content, title)

                # 디버깅용 로그
                logger.info(f"데이터 확인 - kinda(판결결과): {kinda}, kindb: {kindb}, kindc: {kindc}, 연도: {year_info}")

                result = {
                    'rank': i + 1,
                    'case_id': f"CASE_{idx}",
                    'title': summarized_title,
                    'court': court,
                    'date': formatted_date,
                    'similarity': round(float(similarity), 4),
                    'similarity_pct': round(float(similarity) * 100, 2),
                    'content': content_summary,
                    'category': friendly_category,
                    'accnum': year_info,  # 연도 정보
                    'kinda': kinda,  # 실제 판결결과 (기각, 인용, 취하 등)
                    'case_type': f"{kindb} {kindc}".strip() if kindb and kindc else kindb or kindc or ''  # 사건분야
                }
                raw_results.append(result)

        logger.info(f"Raw results found: {len(raw_results)}")

        # 단계적 품질 필터링
        for result in raw_results:
            # 1차 필터링: Unknown 데이터 제외 (선택적)
            if result['court'] == 'Unknown Court':
                continue

            # 2차 필터링: 기각 판례 제외 (선택적)
            if "기각" in result['title'].lower():
                continue

            # 필터링 통과한 결과 추가
            result['rank'] = len(results) + 1  # 필터링 후 순위 재조정
            results.append(result)

        logger.info(f"Filtered results: {len(results)}")

        # 폴백 메커니즘: 필터링 결과가 너무 적으면 완화
        if len(results) < 3 and len(raw_results) >= 3:
            logger.info("Applying fallback mechanism due to insufficient filtered results")
            results = raw_results[:top_k]  # 상위 결과 그대로 사용

        # 첫 번째 결과 상세 로깅
        if results:
            top_result = results[0]
            logger.info(f"Top result: similarity={top_result['similarity']:.4f} "
                       f"({top_result['similarity_pct']:.2f}%), "
                       f"title='{top_result['title'][:50]}...', court='{top_result['court']}'")

        logger.info(f"✅ Simple search completed: found {len(results)} relevant results")
        return results

    except Exception as e:
        logger.error(f"❌ Simple search failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def get_simple_search_stats() -> Dict[str, Any]:
    """모델 상태 및 통계 정보 반환"""
    if not _model_loaded:
        return {
            "status": "not_loaded",
            "message": "Model not loaded"
        }

    try:
        return {
            "status": "loaded",
            "total_cases": len(_df),
            "vocabulary_size": len(_vectorizer.vocabulary_),
            "tfidf_matrix_shape": _tfidf_matrix.shape,
            "available_columns": list(_df.columns),
            "sample_titles": _df['title'].head(3).tolist() if 'title' in _df.columns else [],
            "model_type": "simple_direct"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def extract_year_from_text(*texts: str) -> str:
    """텍스트들에서 연도 정보 추출 (강화된 버전)"""
    import re

    logger.debug(f"연도 추출 시도 - 입력 텍스트 개수: {len(texts)}")

    for i, text in enumerate(texts):
        if not text or str(text).strip() == '' or str(text) == 'nan':
            logger.debug(f"텍스트 {i+1}: 빈 문자열 스킵")
            continue

        text = str(text).strip()
        logger.debug(f"텍스트 {i+1} 분석 중: '{text[:50]}...'")

        # 판례 문서에 특화된 확장된 연도 패턴
        year_patterns = [
            # 1순위: 한국 법원 사건번호 패턴 (가장 확실한 연도 정보)
            r'(\d{4})고합\d*',     # 2018고합123
            r'(\d{4})고단\d*',     # 2019고단456
            r'(\d{4})나\d*',       # 2020나789
            r'(\d{4})다\d*',       # 2021다123
            r'(\d{4})누\d*',       # 행정소송
            r'(\d{4})아\d*',       # 특별법
            r'(\d{4})노\d*',       # 형사소송
            r'(\d{4})구\d*',       # 구단
            r'(\d{4})초\d*',       # 초기결정
            r'(\d{4})재\d*',       # 재심

            # 2순위: 판결/선고 관련 패턴
            r'(\d{4})년.*?선고',     # 2022년 3월 15일 선고
            r'(\d{4})년.*?판결',     # 2021년 판결
            r'선고.*?(\d{4})년',     # 선고 2020년
            r'판결.*?(\d{4})년',     # 판결 2019년

            # 3순위: 일반적인 날짜 패턴
            r'(\d{4})[년]',         # 2022년
            r'(\d{4})\.\s*\d',      # 2023. 1
            r'(\d{4})-\d',          # 2024-01
            r'(\d{4})/\d',          # 2024/01

            # 4순위: 사건 관련 패턴
            r'사건.*?(\d{4})',      # 사건 2020
            r'신청.*?(\d{4})',      # 신청 2021
            r'처분.*?(\d{4})',      # 처분 2019

            # 5순위: 기타 패턴 (덜 확실함)
            r'(\d{4})\s+\d',        # 2025 01
            r'[^\d](\d{4})[^\d]',   # 양쪽이 숫자가 아닌 4자리
            r'^(\d{4})',            # 문자열 시작의 4자리
            r'(\d{4})'              # 마지막 후보: 일반적인 4자리 숫자
        ]

        for pattern in year_patterns:
            try:
                matches = re.findall(pattern, text)
                logger.debug(f"패턴 '{pattern}' 매치 결과: {matches}")

                for match in matches:
                    try:
                        year = int(match)
                        if 1990 <= year <= 2030:  # 범위를 1990-2030으로 조정
                            logger.debug(f"✅ 연도 추출 성공: {year} (패턴: '{pattern}', 텍스트: '{text[:30]}...')")
                            return str(year)
                    except (ValueError, TypeError):
                        continue
            except Exception as e:
                logger.debug(f"패턴 '{pattern}' 처리 중 오류: {e}")
                continue

    logger.debug("❌ 연도 추출 실패 - 모든 패턴에서 매치되지 않음")
    return '미상'

def get_friendly_category(title: str, content: str) -> str:
    """제목과 내용을 기반으로 사용자 친화적인 카테고리 반환"""
    title_lower = title.lower()
    content_lower = content.lower()

    # 제목과 내용을 모두 검색
    combined_text = f"{title_lower} {content_lower}"

    # 추락사고
    if any(word in combined_text for word in ["추락", "낙상", "떨어", "비계", "사다리", "고소", "높이", "옥상", "아래로"]):
        return "추락사고"

    # 기계사고
    elif any(word in combined_text for word in ["끼임", "절단", "프레스", "기계", "크레인", "컨베이어", "끼여", "절단기", "압착"]):
        return "기계사고"

    # 화재사고
    elif any(word in combined_text for word in ["화상", "화재", "폭발", "용접", "고온", "증기", "화염", "폭발", "열상"]):
        return "화재사고"

    # 교통사고
    elif any(word in combined_text for word in ["교통", "차량", "충돌", "지게차", "화물차", "트럭", "버스", "승용차"]):
        return "교통사고"

    # 중독사고
    elif any(word in combined_text for word in ["중독", "질식", "화학", "가스", "약품", "독성", "중독성", "흡입"]):
        return "중독사고"

    # 감전사고
    elif any(word in combined_text for word in ["감전", "전기", "전선", "누전", "전류", "전압", "전기적"]):
        return "감전사고"

    # 기타 산업재해
    else:
        return "산업재해"

def format_court_date(date_str: str) -> str:
    """법원 날짜를 사용자 친화적으로 포맷"""
    if not date_str or date_str == "Unknown Date":
        return "날짜미상"

    # "취소" 등 잘못된 데이터 처리
    if "취소" in date_str or "기각" in date_str:
        return "날짜미상"

    # 그대로 반환 (pkl 파일의 원본 날짜 데이터 사용)
    return date_str

def summarize_case_title(title: str) -> str:
    """복잡한 판례 제목을 사용자 친화적으로 요약"""
    if len(title) > 50:
        return title[:47] + "..."
    return title

def _create_readable_summary(content: str, max_length: int = 500) -> str:
    """가독성 좋은 콘텐츠 요약 생성"""
    if not content or content.strip() == "":
        return "내용 정보가 없습니다."

    # 기본 정리
    content = content.strip()

    # 길이가 제한보다 짧으면 그대로 반환
    if len(content) <= max_length:
        return content

    # 문장 단위로 자르기 시도
    sentences = content.split('. ')
    result = ""

    for sentence in sentences:
        # 다음 문장을 추가했을 때 길이가 초과되는지 확인
        test_result = result + sentence + ". " if result else sentence + ". "

        if len(test_result) <= max_length - 3:  # "..." 공간 확보
            result = test_result
        else:
            break

    # 문장 단위로 잘렸으면 그것을 사용, 그렇지 않으면 글자 단위로 자르기
    if result and len(result) > 100:  # 최소한의 의미있는 길이
        return result.rstrip() + "..."
    else:
        # 글자 단위로 자르되, 자연스러운 끝맺음 찾기
        truncated = content[:max_length]

        # 마지막 공백이나 구두점에서 자르기
        for i in range(len(truncated) - 1, max(0, len(truncated) - 50), -1):
            if truncated[i] in [' ', '.', ',', '다', '고', '며', '음', '임']:
                truncated = truncated[:i + 1]
                break

        return truncated + "..."

def debug_model_structure():
    """pkl 파일의 정확한 구조 디버그 (개발용)"""
    if not _model_loaded and not load_searcher_model_direct():
        return {"error": "Model not loaded"}

    try:
        debug_info = {
            "dataframe_shape": _df.shape,
            "columns": list(_df.columns),
            "tfidf_matrix_shape": _tfidf_matrix.shape,
            "vocabulary_sample": list(_vectorizer.vocabulary_.keys())[:10],
        }

        # 첫 3개 행의 실제 데이터 확인 (연도 추출 디버깅용) - 모든 필드 확인
        sample_data = []
        for i in range(min(3, len(_df))):
            row = _df.iloc[i]

            # 모든 필드의 실제 내용 확인
            row_data = {"index": i}
            for col in _df.columns:
                value = str(row.get(col, ''))
                # noncontent는 길이가 길 수 있으므로 200자로 제한
                if col == 'noncontent':
                    row_data[col] = value[:200] + ("..." if len(value) > 200 else "")
                else:
                    row_data[col] = value[:150] + ("..." if len(value) > 150 else "")

            sample_data.append(row_data)

        debug_info["sample_data"] = sample_data

        return debug_info

    except Exception as e:
        return {"debug_error": str(e)}

def generate_simple_report(query: str, top_n: int = 5) -> Dict[str, Any]:
    """간단한 검색 보고서 생성"""
    start_time = datetime.now()

    # 검색 수행
    results = search_precedents_simple(query, top_n)

    search_time = (datetime.now() - start_time).total_seconds()

    if not results:
        return {
            "query": query,
            "total_results": 0,
            "search_time": search_time,
            "message": "관련된 판례를 찾을 수 없습니다.",
            "success": False
        }

    # 기본 통계
    similarities = [r['similarity'] for r in results]
    courts = [r['court'] for r in results]

    # 법원별 분포
    court_counts = {}
    for court in courts:
        court_counts[court] = court_counts.get(court, 0) + 1

    return {
        "query": query,
        "search_time": round(search_time, 3),
        "total_results": len(results),
        "success": True,
        "avg_similarity": round(np.mean(similarities), 3),
        "max_similarity": round(max(similarities), 3),
        "min_similarity": round(min(similarities), 3),
        "court_distribution": court_counts,
        "results": results[:top_n],
        "recommendation": _generate_simple_recommendation(similarities, court_counts)
    }

def _generate_simple_recommendation(similarities: List[float], court_counts: Dict[str, int]) -> str:
    """간단한 권고사항 생성"""
    avg_sim = np.mean(similarities)

    if avg_sim > 0.3:
        rec = "매우 관련성 높은 판례들이 발견되었습니다. "
    elif avg_sim > 0.1:
        rec = "적절한 관련성의 판례들이 발견되었습니다. "
    else:
        rec = "유사도가 낮습니다. 더 구체적인 검색어를 사용해보세요. "

    if court_counts:
        main_court = max(court_counts.keys(), key=lambda k: court_counts[k])
        rec += f"주로 '{main_court}' 사건과 관련되어 있습니다."

    return rec

# 편의 함수들
def get_precedent_detail(case_id: str) -> Optional[Dict[str, Any]]:
    """개별 판례 상세 정보 조회"""
    # 모델 로드 확인
    if not _model_loaded and not load_searcher_model_direct():
        logger.error("Model not loaded, cannot get precedent detail")
        return None

    try:
        # Case ID에서 인덱스 추출 (CASE_12345 -> 12345)
        if case_id.startswith('CASE_'):
            idx = int(case_id[5:])
        else:
            idx = int(case_id)

        # 유효한 인덱스인지 확인
        if idx < 0 or idx >= len(_df):
            logger.error(f"Invalid case index: {idx}")
            return None

        # 데이터 조회
        row = _df.iloc[idx]

        title = str(row.get('title', 'Unknown Title'))
        court = str(row.get('courtname', 'Unknown Court'))
        date = format_court_date(str(row.get('kinda', 'Unknown Date')))

        # 전체 내용 (요약하지 않음)
        full_content = str(row.get('noncontent', ''))

        # 추가 정보
        case_number = str(row.get('caseno', '사건번호 미상'))
        plaintiff = str(row.get('plaintiff', '원고 정보 미상'))
        defendant = str(row.get('defendant', '피고 정보 미상'))

        # 카테고리
        category = get_friendly_category(title, full_content)

        # 키워드 추출 (간단한 키워드 추출)
        keywords = extract_keywords_from_content(full_content)

        detail = {
            'case_id': case_id,
            'index': idx,
            'title': title,
            'court': court,
            'date': date,
            'case_number': case_number,
            'plaintiff': plaintiff,
            'defendant': defendant,
            'category': category,
            'full_content': full_content,
            'keywords': keywords,
            'content_length': len(full_content),
            'summarized_title': summarize_case_title(title)
        }

        logger.info(f"Precedent detail retrieved successfully: {case_id}")
        return detail

    except Exception as e:
        logger.error(f"Failed to get precedent detail for {case_id}: {e}")
        return None

def extract_keywords_from_content(content: str, max_keywords: int = 10) -> List[str]:
    """판례 내용에서 주요 키워드 추출"""
    if not content:
        return []

    # 산재 관련 주요 키워드들
    important_terms = [
        '산업재해', '업무상', '재해', '부상', '사망', '질병',
        '안전보건', '작업', '근로자', '사업주', '보상금',
        '치료비', '휴업급여', '장해급여', '유족급여', '장해등급',
        '의료비', '간병비', '추락', '절단', '감전', '화상',
        '중독', '골절', '염좌', '타박상'
    ]

    found_keywords = []
    content_lower = content.lower()

    for term in important_terms:
        if term in content:
            found_keywords.append(term)
            if len(found_keywords) >= max_keywords:
                break

    return found_keywords

def quick_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """빠른 검색 편의 함수"""
    return search_precedents_simple(query, top_k)

def test_search_service():
    """서비스 테스트 함수"""
    print("🔍 Simple Search Service Test")

    # 모델 로드 테스트
    if load_searcher_model_direct():
        print("✅ Model loaded successfully")

        # 통계 확인
        stats = get_simple_search_stats()
        print(f"📊 Total cases: {stats['total_cases']:,}")
        print(f"📚 Vocabulary size: {stats['vocabulary_size']:,}")

        # 테스트 검색
        test_query = "작업 중 손가락 다침"
        print(f"\n🔍 Test query: '{test_query}'")

        results = search_precedents_simple(test_query, 3)
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['similarity_pct']:.1f}%] {result['title'][:50]}...")
            print(f"   법원: {result['court']}")

        # 보고서 테스트
        report = generate_simple_report(test_query, 3)
        print(f"\n📋 Report: {report['total_results']} results, "
              f"avg similarity: {report.get('avg_similarity', 'N/A')}")
        print(f"💡 Recommendation: {report.get('recommendation', 'N/A')}")

    else:
        print("❌ Model loading failed")

if __name__ == "__main__":
    test_search_service()