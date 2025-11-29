#!/usr/bin/env python3
"""
PrecedentSearchService - 하이브리드 판례 검색 서비스
기존 RAG 기반 분석 + 새로운 TF-IDF 검색을 통합한 종합 서비스
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# SANZERO 기존 서비스들
from app.services.analysis_service import AnalysisService
from app.services.searcher import WorkInjuryCaseSearcher, PrecedentResult, get_searcher
from app.services.advanced_case_searcher import (
    AdvancedCaseSearcher, AdvancedPrecedentResult, DynamicThresholdResult,
    get_advanced_searcher
)

# 로깅 설정 (먼저 정의)
logger = logging.getLogger(__name__)

# Enhanced searcher 제거됨 - Basic searcher만 사용
ENHANCED_SEARCHER_AVAILABLE = False

@dataclass
class HybridSearchResult:
    """하이브리드 검색 결과 통합 데이터 클래스"""
    # 메타데이터
    query: str
    search_timestamp: str
    total_processing_time: float

    # TF-IDF 검색 결과 (빠른 검색) - 고급 결과로 변경
    tfidf_results: List[AdvancedPrecedentResult]
    tfidf_search_time: float
    tfidf_available: bool

    # 동적 임계값 정보 (새로 추가)
    dynamic_threshold: Optional[DynamicThresholdResult]

    # RAG 기반 분석 결과 (심화 분석)
    rag_results: Optional[Dict[str, Any]]
    rag_analysis_time: float
    rag_available: bool

    # 통합 분석
    combined_insights: Dict[str, Any]
    recommendation: str
    confidence_score: float


class PrecedentSearchService:
    """
    하이브리드 판례 검색 서비스

    두 가지 검색 방식을 통합:
    1. TF-IDF 기반 빠른 유사도 검색 (27,339건 실제 판례)
    2. RAG 기반 LLM 분석 (기존 SANZERO 분석)

    사용자에게 빠른 검색과 심화 분석을 모두 제공
    """

    def __init__(self):
        """PrecedentSearchService 초기화"""
        self.analysis_service = AnalysisService()
        self.tfidf_searcher = None
        self.advanced_searcher = None
        self.is_tfidf_available = False
        self.is_advanced_available = False

        # 초기화
        self._initialize_services()

    def _initialize_services(self):
        """서비스 초기화"""
        try:
            # 고급 검색 서비스 초기화 (우선)
            self.advanced_searcher = get_advanced_searcher()
            self.is_advanced_available = self.advanced_searcher.is_loaded

            if self.is_advanced_available:
                logger.info("✅ Advanced searcher with dynamic thresholds initialized successfully")
                # Advanced searcher 통계 로그 추가
                stats = self.advanced_searcher.get_statistics()
                if stats.get("status") == "loaded":
                    logger.info(f"   📊 Advanced searcher loaded: {stats.get('total_precedents', 0)} precedents, "
                              f"vocab: {stats.get('vocabulary_size', 0)}")
            else:
                logger.warning("⚠️ Advanced searcher loaded but not ready, falling back to basic searcher")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Advanced searcher: {e}")
            logger.error(f"   Error type: {type(e).__name__}")
            logger.error(f"   Falling back to Basic searcher for compatibility")
            self.is_advanced_available = False

        # 기본 TF-IDF 검색기 (fallback)
        if not self.is_advanced_available:
            try:
                self.tfidf_searcher = get_searcher()
                self.is_tfidf_available = self.tfidf_searcher.is_loaded

                if self.is_tfidf_available:
                    logger.info("✅ Basic TF-IDF searcher initialized successfully as fallback")
                    # Basic searcher 통계 로그 추가
                    basic_stats = self.tfidf_searcher.get_statistics()
                    if basic_stats.get("status") == "loaded":
                        logger.info(f"   📊 Basic searcher loaded: {basic_stats.get('total_cases', 0)} cases, "
                                  f"vocab: {basic_stats.get('vocabulary_size', 0)}")
                else:
                    logger.error("❌ Basic TF-IDF searcher failed to load - no searcher available!")

            except Exception as e:
                logger.error(f"❌ Failed to initialize basic TF-IDF searcher: {e}")
                logger.error(f"   Error type: {type(e).__name__}")
                logger.error(f"   No search functionality available!")
                self.is_tfidf_available = False

        # Enhanced 시스템 제거됨 - Basic TF-IDF searcher만 사용
        logger.info("Using optimized TF-IDF searcher for fast performance")

    async def hybrid_search(
        self,
        query: str,
        tfidf_top_k: int = 10,
        include_rag_analysis: bool = True,
        timeout_seconds: int = 30,
        accuracy_level: str = "medium"
    ) -> HybridSearchResult:
        """
        하이브리드 검색 수행 (동적 임계값 적용)

        Args:
            query: 검색 쿼리
            tfidf_top_k: TF-IDF 검색 결과 수
            include_rag_analysis: RAG 분석 포함 여부
            timeout_seconds: 전체 타임아웃
            accuracy_level: 정확도 수준 (high/medium/low)

        Returns:
            HybridSearchResult: 동적 임계값이 적용된 통합 검색 결과
        """
        start_time = datetime.now()

        logger.info(f"Starting hybrid search with dynamic threshold for query: '{query}'")

        # 결과 초기화
        tfidf_results = []
        tfidf_time = 0.0
        rag_results = None
        rag_time = 0.0
        dynamic_threshold_result = None

        # 1. 고급 TF-IDF 검색 (동적 임계값 적용)
        if self.is_advanced_available:
            tfidf_start = datetime.now()
            try:
                tfidf_results, dynamic_threshold_result = await self._perform_advanced_search(
                    query, tfidf_top_k, accuracy_level
                )
                tfidf_time = (datetime.now() - tfidf_start).total_seconds()
                logger.info(f"Advanced search completed in {tfidf_time:.2f}s, "
                          f"found {len(tfidf_results)} results with threshold {dynamic_threshold_result.final_threshold:.3f}")
            except Exception as e:
                logger.error(f"Advanced search failed: {e}")
                tfidf_results = []

        # Fallback: 기본 TF-IDF 검색
        elif self.is_tfidf_available:
            tfidf_start = datetime.now()
            try:
                basic_results = await self._perform_tfidf_search(query, tfidf_top_k)
                # 기본 결과를 고급 결과 형식으로 변환
                tfidf_results = self._convert_to_advanced_results(basic_results)
                tfidf_time = (datetime.now() - tfidf_start).total_seconds()
                logger.info(f"Basic TF-IDF search completed in {tfidf_time:.2f}s, found {len(tfidf_results)} results")
            except Exception as e:
                logger.error(f"Basic TF-IDF search failed: {e}")
                tfidf_results = []

        # 2. RAG 분석 (선택적)
        if include_rag_analysis:
            rag_start = datetime.now()
            try:
                rag_results = await self._perform_rag_analysis(query, timeout_seconds)
                rag_time = (datetime.now() - rag_start).total_seconds()
                logger.info(f"RAG analysis completed in {rag_time:.2f}s")
            except Exception as e:
                logger.error(f"RAG analysis failed: {e}")
                rag_results = None

        # 3. 결과 통합 및 분석
        total_time = (datetime.now() - start_time).total_seconds()

        combined_insights = self._combine_insights(tfidf_results, rag_results, query)
        recommendation = self._generate_recommendation(tfidf_results, rag_results, combined_insights)
        confidence_score = self._calculate_confidence_score(tfidf_results, rag_results)

        # 통합 결과 생성
        result = HybridSearchResult(
            query=query,
            search_timestamp=start_time.isoformat(),
            total_processing_time=total_time,

            tfidf_results=tfidf_results,
            tfidf_search_time=tfidf_time,
            tfidf_available=self.is_advanced_available or self.is_tfidf_available,

            dynamic_threshold=dynamic_threshold_result,

            rag_results=rag_results,
            rag_analysis_time=rag_time,
            rag_available=include_rag_analysis and rag_results is not None,

            combined_insights=combined_insights,
            recommendation=recommendation,
            confidence_score=confidence_score
        )

        logger.info(f"Hybrid search completed in {total_time:.2f}s (confidence: {confidence_score:.2f})")
        return result

    async def _perform_tfidf_search(self, query: str, top_k: int) -> List[PrecedentResult]:
        """TF-IDF 검색 수행 (강화된 버전 우선 사용)"""

        # TF-IDF 검색 (빠른 성능을 위해 최적화)
        if self.is_tfidf_available:
            logger.info("Using standard TF-IDF searcher")
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.tfidf_searcher.search,
                query,
                top_k
            )
            return results

        # 3. 검색 불가능
        logger.error("No searcher available (neither enhanced nor standard)")
        return []

    async def _perform_advanced_search(
        self,
        query: str,
        top_k: int,
        accuracy_level: str = "medium"
    ) -> Tuple[List[AdvancedPrecedentResult], DynamicThresholdResult]:
        """고급 검색 수행 (동적 임계값 적용)"""
        if not self.is_advanced_available:
            raise ValueError("Advanced searcher not available")

        user_preferences = {"accuracy_level": accuracy_level}

        loop = asyncio.get_event_loop()

        # 비동기로 고급 검색 실행
        search_results = await loop.run_in_executor(
            None,
            self.advanced_searcher.search,
            query,
            top_k,
            user_preferences
        )

        # 동적 임계값 결과도 비동기로 계산
        threshold_result = await loop.run_in_executor(
            None,
            self.advanced_searcher.calculate_dynamic_threshold,
            query,
            user_preferences
        )

        return search_results, threshold_result

    def _convert_to_advanced_results(self, basic_results: List[PrecedentResult]) -> List[AdvancedPrecedentResult]:
        """기본 검색 결과를 고급 결과 형식으로 안전하게 변환"""
        advanced_results = []

        logger.info(f"Converting {len(basic_results)} basic results to advanced format")

        for i, basic in enumerate(basic_results):
            try:
                # 안전한 필드 접근
                case_id = getattr(basic, 'case_id', f'CASE_{i}')
                title = getattr(basic, 'title', 'Unknown Title')
                content = getattr(basic, 'content', '')
                court = getattr(basic, 'court', 'Unknown Court')
                date = getattr(basic, 'date', 'Unknown Date')
                similarity = getattr(basic, 'similarity', 0.0)
                category = getattr(basic, 'category', 'Unknown')
                keywords = getattr(basic, 'keywords', [])

                # 안전한 문자열 변환
                title = str(title) if title else 'Unknown Title'
                content = str(content) if content else ''
                court = str(court) if court else 'Unknown Court'
                date = str(date) if date else 'Unknown Date'

                # 기본 유불리 분석 (개선된 버전)
                favorability = "애매 △"  # 기본값
                favorable_score = 0
                unfavorable_score = 0

                if content:
                    content_lower = content.lower()
                    # 근로자에게 유리한 키워드
                    favorable_keywords = ["승소", "인용", "배상", "인정", "지급", "책임", "과실", "위반"]
                    # 근로자에게 불리한 키워드
                    unfavorable_keywords = ["패소", "기각", "면책", "무과실", "기여과실", "자기과실", "거부"]

                    for keyword in favorable_keywords:
                        favorable_score += content_lower.count(keyword)
                    for keyword in unfavorable_keywords:
                        unfavorable_score += content_lower.count(keyword)

                    # 판단 로직 개선
                    if favorable_score > unfavorable_score + 1:
                        favorability = "유리 O"
                    elif unfavorable_score > favorable_score + 1:
                        favorability = "불리 X"
                    else:
                        favorability = "애매 △"

                # 키워드 처리 개선
                if isinstance(keywords, list) and keywords:
                    top_keywords = keywords[:5]
                    match_keywords = ', '.join(str(kw) for kw in keywords[:3] if kw)
                else:
                    top_keywords = []
                    match_keywords = '-'

                if not match_keywords or match_keywords.strip() == ',':
                    match_keywords = '-'

                advanced = AdvancedPrecedentResult(
                    case_id=case_id,
                    title=title,
                    content=content[:1000] + ("..." if len(content) > 1000 else ""),
                    court=court,
                    date=date,
                    similarity=float(similarity),
                    similarity_pct=round(float(similarity) * 100, 2),
                    category=category,
                    keywords=top_keywords,
                    match_keywords=match_keywords,
                    worker_favorable=favorability,
                    favorability_score={"favorable": favorable_score, "unfavorable": unfavorable_score}
                )
                advanced_results.append(advanced)

                # 첫 번째 결과는 상세 로그 출력
                if i == 0:
                    logger.info(f"   Sample conversion: Basic(title='{title[:30]}...', similarity={similarity:.3f}) "
                              f"→ Advanced(favorability='{favorability}', match_keywords='{match_keywords[:20]}...')")

            except Exception as e:
                logger.error(f"Failed to convert basic result {i}: {e}")
                logger.error(f"   Basic result fields: {vars(basic) if hasattr(basic, '__dict__') else str(basic)}")
                # 변환 실패 시에도 기본 결과 생성
                advanced = AdvancedPrecedentResult(
                    case_id=f'ERROR_{i}',
                    title=f'Conversion Error {i}',
                    content=f'Failed to convert basic result: {str(e)}',
                    court='Unknown',
                    date='Unknown',
                    similarity=0.0,
                    similarity_pct=0.0,
                    category='Error',
                    keywords=[],
                    match_keywords='-',
                    worker_favorable="애매 △",
                    favorability_score={"favorable": 0, "unfavorable": 0}
                )
                advanced_results.append(advanced)

        logger.info(f"Successfully converted {len(advanced_results)} results to advanced format")
        return advanced_results

    async def _perform_rag_analysis(
        self,
        query: str,
        timeout_seconds: int
    ) -> Optional[Dict[str, Any]]:
        """RAG 기반 분석 수행"""
        try:
            # 기존 SANZERO 분석 서비스 사용
            result = await asyncio.wait_for(
                self.analysis_service.analyze_precedent(query),
                timeout=timeout_seconds
            )

            if result and result.get('status') == 'success':
                return result.get('data', {})
            else:
                logger.warning("RAG analysis returned no valid results")
                return None

        except asyncio.TimeoutError:
            logger.warning(f"RAG analysis timed out after {timeout_seconds}s")
            return None
        except Exception as e:
            logger.error(f"RAG analysis error: {e}")
            return None

    def _combine_insights(
        self,
        tfidf_results: List[AdvancedPrecedentResult],
        rag_results: Optional[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """고급 TF-IDF와 RAG 결과를 통합하여 인사이트 생성"""
        insights = {
            "query_analysis": {
                "original_query": query,
                "query_length": len(query),
                "has_keywords": len(query.split()) > 1
            }
        }

        # 고급 TF-IDF 결과 분석
        if tfidf_results:
            insights["tfidf_analysis"] = {
                "total_results": len(tfidf_results),
                "avg_similarity": round(sum(r.similarity for r in tfidf_results) / len(tfidf_results), 3),
                "max_similarity": round(max(r.similarity for r in tfidf_results), 3),
                "min_similarity": round(min(r.similarity for r in tfidf_results), 3),
                "high_similarity_count": sum(1 for r in tfidf_results if r.similarity > 0.5),
                "courts": list(set([r.court for r in tfidf_results if r.court != "Unknown Court"])),
                "top_similarities": [round(r.similarity, 3) for r in tfidf_results[:5]]
            }

            # 근로자 유불리 분포 분석 (신규)
            from collections import Counter
            favorability_counts = Counter([r.worker_favorable for r in tfidf_results])
            insights["tfidf_analysis"]["favorability_distribution"] = dict(favorability_counts)

            # 카테고리 분석
            categories = [r.category for r in tfidf_results if r.category]
            if categories:
                category_counts = Counter(categories)
                insights["tfidf_analysis"]["category_distribution"] = dict(category_counts.most_common(5))

            # 매칭 키워드 분석 (신규)
            all_match_keywords = []
            for r in tfidf_results:
                if r.match_keywords and r.match_keywords != '-':
                    all_match_keywords.extend([kw.strip() for kw in r.match_keywords.split(',')])

            if all_match_keywords:
                keyword_counts = Counter(all_match_keywords)
                insights["tfidf_analysis"]["top_matching_keywords"] = dict(keyword_counts.most_common(10))

        # RAG 결과 분석
        if rag_results:
            insights["rag_analysis"] = {
                "has_precedents": bool(rag_results.get("precedents")),
                "precedent_count": len(rag_results.get("precedents", [])),
                "has_analysis": bool(rag_results.get("analysis")),
                "has_recommendations": bool(rag_results.get("recommendations")),
                "analysis_summary": rag_results.get("analysis", "")[:200] + "..." if rag_results.get("analysis") else ""
            }

        # 교차 분석
        insights["cross_analysis"] = {
            "both_available": bool(tfidf_results and rag_results),
            "consistency_check": self._check_consistency(tfidf_results, rag_results),
            "complementary_value": self._assess_complementary_value(tfidf_results, rag_results)
        }

        return insights

    def _check_consistency(
        self,
        tfidf_results: List[PrecedentResult],
        rag_results: Optional[Dict[str, Any]]
    ) -> str:
        """TF-IDF와 RAG 결과의 일관성 검토"""
        if not tfidf_results or not rag_results:
            return "insufficient_data"

        # 간단한 일관성 검사
        tfidf_avg_sim = sum(r.similarity for r in tfidf_results) / len(tfidf_results)
        rag_has_good_precedents = len(rag_results.get("precedents", [])) > 0

        if tfidf_avg_sim > 0.3 and rag_has_good_precedents:
            return "consistent"
        elif tfidf_avg_sim < 0.1 and not rag_has_good_precedents:
            return "consistently_low"
        else:
            return "mixed"

    def _assess_complementary_value(
        self,
        tfidf_results: List[PrecedentResult],
        rag_results: Optional[Dict[str, Any]]
    ) -> str:
        """두 방식의 상호 보완적 가치 평가"""
        if not tfidf_results and not rag_results:
            return "both_unavailable"
        elif tfidf_results and not rag_results:
            return "tfidf_only"
        elif not tfidf_results and rag_results:
            return "rag_only"
        else:
            return "complementary"

    def _generate_recommendation(
        self,
        tfidf_results: List[AdvancedPrecedentResult],
        rag_results: Optional[Dict[str, Any]],
        insights: Dict[str, Any]
    ) -> str:
        """고급 분석을 기반으로 권고사항 생성"""
        recommendations = []

        # 고급 TF-IDF 기반 권고사항
        if tfidf_results:
            avg_sim = insights.get("tfidf_analysis", {}).get("avg_similarity", 0)
            if avg_sim > 0.5:
                recommendations.append("높은 유사도의 판례들이 발견되었습니다.")
            elif avg_sim > 0.3:
                recommendations.append("적정한 유사도의 판례들이 찾아졌습니다.")
            else:
                recommendations.append("유사도가 낮은 편입니다. 더 구체적인 검색어를 사용해보세요.")

            # 근로자 유불리 분석 기반 권고사항 (신규)
            favorability_dist = insights.get("tfidf_analysis", {}).get("favorability_distribution", {})
            if favorability_dist:
                favorable_count = favorability_dist.get("유리 O", 0)
                unfavorable_count = favorability_dist.get("불리 X", 0)
                neutral_count = favorability_dist.get("애매 △", 0)

                total_cases = favorable_count + unfavorable_count + neutral_count
                if total_cases > 0:
                    favorable_ratio = favorable_count / total_cases
                    if favorable_ratio > 0.6:
                        recommendations.append("대부분의 유사 판례에서 근로자에게 유리한 결과를 보였습니다.")
                    elif favorable_ratio < 0.3:
                        recommendations.append("유사 판례 중 근로자에게 불리한 결과가 많습니다. 신중한 접근이 필요합니다.")
                    else:
                        recommendations.append("유사 판례의 결과가 혼재되어 있어 사안별 검토가 필요합니다.")

        # RAG 기반 권고사항
        if rag_results and rag_results.get("recommendations"):
            rag_rec = rag_results["recommendations"]
            if isinstance(rag_rec, list) and rag_rec:
                recommendations.append(f"AI 분석: {rag_rec[0][:100]}...")
            elif isinstance(rag_rec, str):
                recommendations.append(f"AI 분석: {rag_rec[:100]}...")

        # 통합 권고사항
        consistency = insights.get("cross_analysis", {}).get("consistency_check", "")
        if consistency == "consistent":
            recommendations.append("TF-IDF 검색과 AI 분석이 일치하여 신뢰도가 높습니다.")
        elif consistency == "mixed":
            recommendations.append("다양한 관점의 분석 결과를 종합적으로 검토하시기 바랍니다.")

        # 기본 권고사항
        if not recommendations:
            recommendations.append("추가적인 검색어나 더 구체적인 사고 상황을 입력해보시기 바랍니다.")

        return " ".join(recommendations)

    def _calculate_confidence_score(
        self,
        tfidf_results: List[AdvancedPrecedentResult],
        rag_results: Optional[Dict[str, Any]]
    ) -> float:
        """고급 신뢰도 점수 계산 (0.0 ~ 1.0)"""
        score = 0.0

        # 고급 TF-IDF 신뢰도 (최대 0.6점)
        if tfidf_results:
            avg_similarity = sum(r.similarity for r in tfidf_results) / len(tfidf_results)
            result_count_bonus = min(len(tfidf_results) / 10, 0.15)  # 결과 수 보너스

            # 매칭 키워드 품질 보너스 (신규)
            keyword_quality_bonus = 0.0
            for result in tfidf_results:
                if result.match_keywords and result.match_keywords != '-':
                    keyword_count = len(result.match_keywords.split(','))
                    keyword_quality_bonus += min(keyword_count * 0.02, 0.05)
            keyword_quality_bonus = min(keyword_quality_bonus / len(tfidf_results), 0.1)

            # 근로자 유불리 일관성 보너스 (신규)
            favorable_results = [r for r in tfidf_results if r.worker_favorable in ["유리 O", "불리 X"]]
            consistency_bonus = 0.0
            if len(favorable_results) >= 3:
                consistency_bonus = 0.05

            tfidf_score = avg_similarity + result_count_bonus + keyword_quality_bonus + consistency_bonus
            score += min(tfidf_score, 0.6)

        # RAG 신뢰도 (최대 0.4점)
        if rag_results:
            rag_score = 0.0
            if rag_results.get("precedents"):
                rag_score += 0.15  # 판례 존재
            if rag_results.get("analysis"):
                rag_score += 0.15  # 분석 존재
            if rag_results.get("recommendations"):
                rag_score += 0.1  # 권고사항 존재
            score += rag_score

        return min(score, 1.0)

    async def quick_search(self, query: str, top_k: int = 5) -> List[PrecedentResult]:
        """빠른 TF-IDF 검색만 수행"""
        if not self.is_tfidf_available:
            return []

        return await self._perform_tfidf_search(query, top_k)

    async def deep_analysis(
        self,
        query: str,
        timeout_seconds: int = 30
    ) -> Optional[Dict[str, Any]]:
        """심화 RAG 분석만 수행"""
        return await self._perform_rag_analysis(query, timeout_seconds)

    def get_search_statistics(self) -> Dict[str, Any]:
        """검색 서비스 통계 반환"""
        stats = {
            "service_name": "PrecedentSearchService",
            "version": "3.0.0",  # Enhanced 제거, 최적화된 버전
            "capabilities": {
                "tfidf_search": self.is_tfidf_available,
                "rag_analysis": True,
                "hybrid_search": self.is_tfidf_available,
                "optimized_performance": True  # 성능 최적화 완료
            }
        }

        # TF-IDF 통계 (최적화된 성능)
        if self.is_tfidf_available:
            try:
                tfidf_stats = self.tfidf_searcher.get_statistics()
                stats["tfidf_statistics"] = tfidf_stats
                stats["primary_searcher"] = "optimized_tfidf"
            except Exception as e:
                logger.error(f"Failed to get TF-IDF statistics: {e}")
                stats["tfidf_statistics"] = {"error": str(e)}

        return stats

    def to_dict(self, result: HybridSearchResult) -> Dict[str, Any]:
        """HybridSearchResult를 dict로 변환 (JSON 직렬화용)"""
        data = asdict(result)

        # AdvancedPrecedentResult 객체들을 dict로 변환
        data["tfidf_results"] = [
            {
                "case_id": r.case_id,
                "title": r.title,
                "content": r.content[:300] + "..." if len(r.content) > 300 else r.content,
                "court": r.court,
                "date": r.date,
                "similarity": r.similarity,
                "similarity_pct": r.similarity_pct,
                "category": r.category,
                "keywords": r.keywords,
                "match_keywords": r.match_keywords,
                "worker_favorable": r.worker_favorable,
                "favorability_score": r.favorability_score
            }
            for r in result.tfidf_results
        ]

        # DynamicThresholdResult 직렬화
        if result.dynamic_threshold:
            data["dynamic_threshold"] = asdict(result.dynamic_threshold)

        return data


# 전역 서비스 인스턴스 (싱글톤)
_precedent_service_instance: Optional[PrecedentSearchService] = None

def get_precedent_service() -> PrecedentSearchService:
    """
    PrecedentSearchService 싱글톤 인스턴스 반환
    FastAPI 의존성 주입용
    """
    global _precedent_service_instance

    if _precedent_service_instance is None:
        _precedent_service_instance = PrecedentSearchService()

    return _precedent_service_instance


# 편의 함수들
async def hybrid_precedent_search(
    query: str,
    tfidf_top_k: int = 10,
    include_rag_analysis: bool = True,
    timeout_seconds: int = 30
) -> HybridSearchResult:
    """하이브리드 검색 편의 함수"""
    service = get_precedent_service()
    return await service.hybrid_search(
        query=query,
        tfidf_top_k=tfidf_top_k,
        include_rag_analysis=include_rag_analysis,
        timeout_seconds=timeout_seconds
    )

async def quick_precedent_search(query: str, top_k: int = 5) -> List[PrecedentResult]:
    """빠른 검색 편의 함수"""
    service = get_precedent_service()
    return await service.quick_search(query, top_k)

async def deep_precedent_analysis(
    query: str,
    timeout_seconds: int = 30
) -> Optional[Dict[str, Any]]:
    """심화 분석 편의 함수"""
    service = get_precedent_service()
    return await service.deep_analysis(query, timeout_seconds=timeout_seconds)


if __name__ == "__main__":
    # 테스트 코드
    async def test_service():
        service = PrecedentSearchService()

        # 서비스 상태 확인
        stats = service.get_search_statistics()
        print("📊 서비스 통계:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # 빠른 검색 테스트
        print("\n🔍 빠른 검색 테스트:")
        quick_results = await service.quick_search("작업 중 손가락 다침", top_k=3)
        print(f"결과 수: {len(quick_results)}")
        for i, result in enumerate(quick_results, 1):
            print(f"{i}. 유사도: {result.similarity:.3f} | {result.title[:50]}...")

        # 하이브리드 검색 테스트
        print("\n🔄 하이브리드 검색 테스트:")
        hybrid_result = await service.hybrid_search(
            "추락 사고로 인한 머리 부상",
            tfidf_top_k=5,
            include_rag_analysis=False  # RAG 분석 제외 (빠른 테스트)
        )

        print(f"전체 처리 시간: {hybrid_result.total_processing_time:.2f}s")
        print(f"TF-IDF 결과: {len(hybrid_result.tfidf_results)}개")
        print(f"신뢰도 점수: {hybrid_result.confidence_score:.2f}")
        print(f"권고사항: {hybrid_result.recommendation}")

    # 비동기 테스트 실행
    import asyncio
    asyncio.run(test_service())