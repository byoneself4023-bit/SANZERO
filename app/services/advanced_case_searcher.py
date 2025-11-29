#!/usr/bin/env python3
"""
AdvancedCaseSearcher - 고급 판례 검색 서비스
Test_casePedia.ipynb의 WorkInjuryCaseSearcher를 기반으로 한 동적 임계값 구현
"""

import os
import joblib
import pandas as pd
import numpy as np
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

# 형태소 분석기 import (조건부)
try:
    from konlpy.tag import Mecab, Okt
    KONLPY_AVAILABLE = True
except ImportError:
    KONLPY_AVAILABLE = False
    logging.warning("KoNLPy not available, using basic tokenization")

logger = logging.getLogger(__name__)

@dataclass
class AdvancedPrecedentResult:
    """고급 판례 검색 결과"""
    case_id: str
    title: str
    content: str
    court: str
    date: str
    similarity: float
    similarity_pct: float
    category: str
    keywords: List[str]
    match_keywords: str
    worker_favorable: str  # 유리 O / 애매 △ / 불리 X
    favorability_score: Dict[str, float]  # 세부 점수
    accnum: str = ""  # 사건번호 (연도 추출용)
    kinda: str = ""   # 쟁점 정보


@dataclass
class DynamicThresholdResult:
    """동적 임계값 계산 결과"""
    final_threshold: float
    base_threshold: float
    adjustments: Dict[str, float]
    reasoning: Dict[str, str]
    query_analysis: Dict[str, Any]


class AdvancedCaseSearcher:
    """
    고급 판례 검색 서비스

    특징:
    - 동적 임계값 계산 (케이스별 최적화)
    - 키워드 부스팅 및 도메인 가중치
    - 근로자 유불리 분석
    - 고급 텍스트 전처리
    """

    def __init__(self):
        self.df = None
        self.tokenizer = None
        self.vectorizer = None
        self.tfidf_matrix = None
        self.config = None
        self.is_loaded = False

        # 설정값들
        self.favorable_keywords = []
        self.unfavorable_keywords = []
        self.domain_keywords = []
        self.stopwords = []
        self.boost_multiplier = 2.0

        # 초기화
        self._initialize()

    def _initialize(self):
        """서비스 초기화"""
        try:
            self._load_model()
            self._initialize_tokenizer()
            self.is_loaded = True
            logger.info("AdvancedCaseSearcher initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AdvancedCaseSearcher: {e}")
            self.is_loaded = False

    def _load_model(self):
        """모델 파일 로드 (joblib 방식 통일)"""
        model_path = Path(__file__).parent.parent / "searcher_model.pkl"

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        logger.info(f"Loading model from: {model_path}")

        # joblib으로 로드 (Basic searcher와 동일한 방식)
        try:
            logger.info("Loading with joblib (unified method)...")
            model_data = joblib.load(model_path)
        except Exception as e:
            logger.error(f"Failed to load with joblib: {e}")
            raise

        # 데이터 로드
        self.df = model_data['df']
        self.vectorizer = model_data['vectorizer']
        self.tfidf_matrix = model_data['tfidf_matrix']
        self.config = model_data['config']

        # 설정 적용
        self.favorable_keywords = self.config['favorable_keywords']
        self.unfavorable_keywords = self.config['unfavorable_keywords']
        self.domain_keywords = self.config['domain_keywords']
        self.stopwords = self.config['stopwords']
        self.boost_multiplier = self.config['boost_multiplier']

        logger.info(f"Model loaded: {len(self.df):,} precedents, "
                   f"TF-IDF matrix shape: {self.tfidf_matrix.shape}")

    def _initialize_tokenizer(self):
        """형태소 분석기 초기화"""
        if not KONLPY_AVAILABLE:
            logger.warning("Using basic tokenization (KoNLPy not available)")
            self.tokenizer = None
            return

        try:
            self.tokenizer = Mecab()
            logger.info("Mecab tokenizer initialized")
        except:
            try:
                self.tokenizer = Okt()
                logger.info("Okt tokenizer initialized")
            except:
                logger.warning("Failed to initialize KoNLPy tokenizers, using basic tokenization")
                self.tokenizer = None

    def _clean_text(self, text: str) -> str:
        """텍스트 전처리"""
        if pd.isna(text):
            return ""
        return ' '.join(re.sub(r'[^가-힣a-zA-Z0-9\s]+', ' ', str(text)).split())

    def _tokenize(self, text: str) -> List[str]:
        """토큰화"""
        if not text:
            return []

        try:
            if self.tokenizer:
                tokens = self.tokenizer.pos(text)
                words = [w for w, p in tokens if p == 'Noun' and len(w) > 1 and w not in self.stopwords]
                # 도메인 키워드 추가 (중복 제거)
                domain_words = [w for w in words if w in self.domain_keywords]
                return list(set(words + domain_words))
            else:
                # 기본 토큰화
                words = [w for w in text.split() if len(w) > 1 and w not in self.stopwords]
                return words
        except Exception as e:
            logger.warning(f"Tokenization failed, using basic split: {e}")
            return [w for w in text.split() if len(w) > 1]

    def calculate_dynamic_threshold(self, query: str, user_preferences: Dict[str, Any] = None) -> DynamicThresholdResult:
        """
        동적 임계값 계산

        Args:
            query: 검색 쿼리
            user_preferences: 사용자 선호도 설정

        Returns:
            DynamicThresholdResult: 계산된 임계값 및 근거
        """
        base_threshold = 0.1  # 기본 임계값
        adjustments = {}
        reasoning = {}

        # 1. 쿼리 품질 분석
        query_analysis = self._analyze_query_quality(query)

        # 2. 쿼리 길이 기반 조정
        query_length = len(query.split())
        if query_length <= 3:
            length_adjustment = -0.05  # 짧은 쿼리는 임계값 낮춤
            reasoning["length"] = f"짧은 쿼리({query_length}단어)로 임계값 완화"
        elif query_length >= 10:
            length_adjustment = 0.15  # 긴 쿼리는 임계값 높임
            reasoning["length"] = f"상세한 쿼리({query_length}단어)로 임계값 상향"
        else:
            length_adjustment = 0.0
            reasoning["length"] = f"적정 길이 쿼리({query_length}단어)"

        adjustments["length"] = length_adjustment

        # 3. 도메인 키워드 밀도 기반 조정
        query_tokens = set(self._tokenize(query))
        domain_ratio = len(query_tokens & set(self.domain_keywords)) / max(len(query_tokens), 1)

        if domain_ratio > 0.3:
            domain_adjustment = 0.1
            reasoning["domain"] = f"도메인 키워드 비율 높음({domain_ratio:.1%})"
        elif domain_ratio > 0.1:
            domain_adjustment = 0.05
            reasoning["domain"] = f"도메인 키워드 적정({domain_ratio:.1%})"
        else:
            domain_adjustment = -0.05
            reasoning["domain"] = f"도메인 키워드 부족({domain_ratio:.1%})"

        adjustments["domain"] = domain_adjustment

        # 4. 사용자 선호도 반영
        if user_preferences:
            accuracy_level = user_preferences.get("accuracy_level", "medium")
            if accuracy_level == "high":
                preference_adjustment = 0.2
                reasoning["preference"] = "높은 정확도 선호"
            elif accuracy_level == "low":
                preference_adjustment = -0.15
                reasoning["preference"] = "관련성 우선 선호"
            else:
                preference_adjustment = 0.0
                reasoning["preference"] = "표준 정확도"
        else:
            preference_adjustment = 0.0
            reasoning["preference"] = "기본 설정"

        adjustments["preference"] = preference_adjustment

        # 5. 예상 결과 분포 기반 조정 (간단한 추정)
        if query_analysis["has_specific_terms"]:
            distribution_adjustment = 0.05
            reasoning["distribution"] = "구체적 용어로 결과 품질 향상 예상"
        else:
            distribution_adjustment = -0.05
            reasoning["distribution"] = "일반적 용어로 결과 확산 예상"

        adjustments["distribution"] = distribution_adjustment

        # 6. 최종 임계값 계산
        total_adjustment = sum(adjustments.values())
        final_threshold = max(0.05, min(0.8, base_threshold + total_adjustment))

        # 설명 생성
        main_reasoning = []
        for key, value in adjustments.items():
            if abs(value) > 0.01:  # 유의미한 조정만 표시
                direction = "상향" if value > 0 else "하향"
                main_reasoning.append(f"{reasoning[key]} ({direction} {abs(value):.2f})")

        threshold_explanation = f"기본 임계값 {base_threshold} → 최종 {final_threshold:.3f}"
        if main_reasoning:
            threshold_explanation += f" ({', '.join(main_reasoning)})"

        return DynamicThresholdResult(
            final_threshold=final_threshold,
            base_threshold=base_threshold,
            adjustments=adjustments,
            reasoning={
                "threshold_explanation": threshold_explanation,
                **reasoning
            },
            query_analysis=query_analysis
        )

    def _analyze_query_quality(self, query: str) -> Dict[str, Any]:
        """쿼리 품질 분석"""
        tokens = self._tokenize(query)

        # 키워드 유형 분석
        legal_terms = ["사고", "재해", "부상", "손해", "배상", "책임", "과실", "안전", "작업", "근무"]
        specific_terms = ["프레스", "추락", "절단", "화상", "끼임", "충돌", "감전", "중독"]

        has_legal_terms = any(term in query for term in legal_terms)
        has_specific_terms = any(term in query for term in specific_terms)

        # 품질 점수 계산 (0.0 ~ 1.0)
        quality_score = 0.5  # 기본값

        if has_legal_terms:
            quality_score += 0.2
        if has_specific_terms:
            quality_score += 0.2
        if len(tokens) >= 5:
            quality_score += 0.1

        return {
            "token_count": len(tokens),
            "has_legal_terms": has_legal_terms,
            "has_specific_terms": has_specific_terms,
            "quality_score": min(quality_score, 1.0),
            "complexity": "high" if len(tokens) > 8 else "medium" if len(tokens) > 4 else "low"
        }

    def search(self, query: str, top_k: int = 10,
               user_preferences: Dict[str, Any] = None) -> List[AdvancedPrecedentResult]:
        """
        고급 판례 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            user_preferences: 사용자 선호도 설정

        Returns:
            List[AdvancedPrecedentResult]: 검색 결과 리스트
        """
        if not self.is_loaded:
            logger.error("Searcher not loaded properly")
            return []

        # 1. 동적 임계값 계산
        threshold_result = self.calculate_dynamic_threshold(query, user_preferences)
        dynamic_threshold = threshold_result.final_threshold

        logger.info(f"Dynamic threshold: {dynamic_threshold:.3f} for query: '{query[:50]}...'")

        # 2. 텍스트 전처리 및 토큰화
        query_clean = self._clean_text(query)
        query_tokens = self._tokenize(query_clean)
        query_str = ' '.join(query_tokens)
        query_set = set(query_tokens)

        # 3. TF-IDF 유사도 계산
        query_vec = self.vectorizer.transform([query_str])
        base_similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # 4. 키워드 부스팅 적용
        boosted_similarities = self._apply_keyword_boosting(
            base_similarities, query_set, query_tokens
        )

        # 5. 동적 임계값 필터링
        valid_indices = np.where(boosted_similarities >= dynamic_threshold)[0]
        if len(valid_indices) == 0:
            # 임계값을 만족하는 결과가 없으면 기본 임계값으로 재시도
            logger.warning(f"No results above dynamic threshold {dynamic_threshold:.3f}, using base threshold")
            valid_indices = np.where(boosted_similarities >= 0.05)[0]

        # 6. 상위 결과 선택
        if len(valid_indices) > top_k:
            top_indices = valid_indices[np.argsort(boosted_similarities[valid_indices])[-top_k:]][::-1]
        else:
            top_indices = valid_indices[np.argsort(boosted_similarities[valid_indices])[::-1]]

        # 7. 결과 생성
        results = []
        for i, idx in enumerate(top_indices):
            row = self.df.iloc[idx]
            similarity_score = boosted_similarities[idx]

            # 매칭 키워드 추출
            match_keywords = self._extract_matching_keywords(query_set, row)

            # 근로자 유불리 분석
            favorability_analysis = self._analyze_worker_favorability(row['noncontent'])

            result = AdvancedPrecedentResult(
                case_id=str(row.get('accnum', f'CASE_{idx}')),  # accnum을 case_id로 사용, 없으면 CASE_{idx}
                title=row['title'],
                content=row['noncontent'][:1000],  # 처음 1000자만
                court=row['courtname'],
                date=str(row.get('date', 'Unknown')),
                similarity=round(similarity_score, 4),
                similarity_pct=round(similarity_score * 100, 2),
                category=row.get('category', '기타'),  # 사고 유형
                keywords=query_tokens[:5],  # 상위 5개 키워드
                match_keywords=match_keywords,
                worker_favorable=favorability_analysis["assessment"],
                favorability_score=favorability_analysis["scores"],
                accnum=str(row.get('accnum', '')),  # 사건번호 (연도 추출용)
                kinda=str(row.get('kinda', ''))     # 쟁점 정보
            )
            results.append(result)

        logger.info(f"Found {len(results)} results above threshold {dynamic_threshold:.3f}")
        return results

    def _apply_keyword_boosting(self, base_similarities: np.ndarray,
                              query_set: set, query_tokens: List[str]) -> np.ndarray:
        """키워드 부스팅 적용"""
        boosted = base_similarities.copy()

        for i, similarity in enumerate(base_similarities):
            try:
                doc_tokens = set(self.df.iloc[i]['tokens'])
                common_keywords = query_set & doc_tokens

                if common_keywords:
                    # 도메인 키워드 가중치
                    domain_count = sum(1 for kw in common_keywords if kw in self.domain_keywords)

                    # 매칭 비율
                    match_ratio = len(common_keywords) / max(len(query_tokens), 1)

                    # 부스팅 계산
                    boost_factor = match_ratio * (1 + domain_count * 0.2) * (self.boost_multiplier - 1)
                    boosted[i] = min(similarity * (1 + boost_factor), 1.0)
            except Exception as e:
                # 에러 발생 시 원본 유사도 유지
                continue

        return boosted

    def _extract_matching_keywords(self, query_set: set, row: pd.Series) -> str:
        """매칭 키워드 추출"""
        try:
            doc_tokens = set(row['tokens'])
            common = (query_set & doc_tokens) - set(self.stopwords)

            # 도메인 키워드 우선
            domain_keywords = [kw for kw in common if kw in self.domain_keywords]
            other_keywords = [kw for kw in common if kw not in self.domain_keywords]

            # 상위 5개 선택
            top_keywords = (domain_keywords + other_keywords)[:5]
            return ', '.join(top_keywords) if top_keywords else '-'
        except:
            return '-'

    def _analyze_worker_favorability(self, content: str) -> Dict[str, Any]:
        """근로자 유불리 분석"""
        if pd.isna(content):
            return {"assessment": "애매 △", "scores": {"favorable": 0, "unfavorable": 0}}

        text = str(content).lower()

        # 결론 부분 가중치 (마지막 30%)
        text_length = len(text)
        conclusion = text[int(text_length * 0.7):]

        # 키워드 점수 계산
        favorable_score = 0
        unfavorable_score = 0

        # 결론 부분 (가중치 2배)
        for keyword in self.favorable_keywords:
            favorable_score += conclusion.lower().count(keyword.lower()) * 2

        for keyword in self.unfavorable_keywords:
            unfavorable_score += conclusion.lower().count(keyword.lower()) * 2

        # 전체 문서
        for keyword in self.favorable_keywords:
            favorable_score += text.count(keyword.lower())

        for keyword in self.unfavorable_keywords:
            unfavorable_score += text.count(keyword.lower())

        # 판단
        if favorable_score > unfavorable_score + 2:
            assessment = "유리 O"
        elif unfavorable_score > favorable_score + 2:
            assessment = "불리 X"
        else:
            assessment = "애매 △"

        return {
            "assessment": assessment,
            "scores": {
                "favorable": favorable_score,
                "unfavorable": unfavorable_score
            }
        }

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        if not self.is_loaded:
            return {"status": "not_loaded"}

        return {
            "status": "loaded",
            "total_precedents": len(self.df),
            "tfidf_matrix_shape": self.tfidf_matrix.shape,
            "vocabulary_size": len(self.vectorizer.vocabulary_),
            "favorable_keywords": len(self.favorable_keywords),
            "unfavorable_keywords": len(self.unfavorable_keywords),
            "domain_keywords": len(self.domain_keywords),
            "boost_multiplier": self.boost_multiplier,
            "tokenizer": "Mecab" if self.tokenizer.__class__.__name__ == "Mecab" else "Okt" if self.tokenizer else "Basic"
        }


# 전역 인스턴스 (싱글톤)
_advanced_searcher_instance: Optional[AdvancedCaseSearcher] = None

def get_advanced_searcher() -> AdvancedCaseSearcher:
    """AdvancedCaseSearcher 싱글톤 인스턴스 반환"""
    global _advanced_searcher_instance

    if _advanced_searcher_instance is None:
        _advanced_searcher_instance = AdvancedCaseSearcher()

    return _advanced_searcher_instance


# 편의 함수들
def search_with_dynamic_threshold(
    query: str,
    top_k: int = 10,
    accuracy_level: str = "medium"
) -> Tuple[List[AdvancedPrecedentResult], DynamicThresholdResult]:
    """동적 임계값을 사용한 검색"""
    searcher = get_advanced_searcher()

    if not searcher.is_loaded:
        return [], None

    user_preferences = {"accuracy_level": accuracy_level}
    threshold_result = searcher.calculate_dynamic_threshold(query, user_preferences)
    results = searcher.search(query, top_k, user_preferences)

    return results, threshold_result


if __name__ == "__main__":
    # 테스트 코드
    def test_advanced_searcher():
        searcher = AdvancedCaseSearcher()

        if not searcher.is_loaded:
            print("❌ 검색기 로드 실패")
            return

        print("📊 검색기 통계:")
        stats = searcher.get_statistics()
        for key, value in stats.items():
            print(f"  {key}: {value}")

        # 테스트 검색
        query = "작업 중 프레스 기계에 손가락 끼임"
        print(f"\n🔍 테스트 검색: '{query}'")

        # 동적 임계값 계산
        threshold_result = searcher.calculate_dynamic_threshold(
            query,
            {"accuracy_level": "medium"}
        )
        print(f"\n📊 동적 임계값: {threshold_result.final_threshold:.3f}")
        print(f"   설명: {threshold_result.reasoning['threshold_explanation']}")

        # 검색 실행
        results = searcher.search(query, top_k=5, user_preferences={"accuracy_level": "medium"})

        print(f"\n📋 검색 결과: {len(results)}건")
        for i, result in enumerate(results, 1):
            print(f"{i}. [{result.similarity_pct:5.1f}%] {result.worker_favorable} | {result.title[:50]}...")

    test_advanced_searcher()