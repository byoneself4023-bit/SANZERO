#!/usr/bin/env python3
"""
WorkInjuryCaseSearcher 서비스
Test_casePedia.ipynb에서 이식된 산재 판례 검색 시스템
SANZERO FastAPI 애플리케이션과 통합하기 위해 최적화됨
"""

import pickle
import joblib
import zlib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import re
import logging
from dataclasses import dataclass
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity

# 한글 처리를 위한 의존성 - 선택적 import
try:
    from konlpy.tag import Okt
    from konlpy.tag import Mecab
    KOREAN_NLP_AVAILABLE = True
except ImportError:
    KOREAN_NLP_AVAILABLE = False
    logging.warning("Korean NLP libraries (konlpy) not available. Using basic tokenization.")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PrecedentResult:
    """판례 검색 결과 데이터 클래스"""
    case_id: str
    title: str
    content: str
    court: str
    date: str
    similarity: float
    category: Optional[str] = None
    keywords: Optional[List[str]] = None


class WorkInjuryCaseSearcher:
    """
    산재 판례 검색 시스템

    27,339개의 실제 판례 데이터를 TF-IDF 벡터화하여
    빠르고 정확한 유사도 검색을 제공합니다.

    주요 기능:
    - 한글 텍스트 토크나이징 (Okt/Mecab 지원)
    - TF-IDF 기반 코사인 유사도 검색
    - 카테고리별 필터링
    - 검색 결과 보고서 생성
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        WorkInjuryCaseSearcher 초기화

        Args:
            model_path: searcher_model.pkl 파일 경로
        """
        self.model_path = model_path or self._get_default_model_path()
        self.df = None
        self.vectorizer = None
        self.tfidf_matrix = None
        self.config = None
        self.tokenizer = None
        self.is_loaded = False

        # 키워드 부스팅 관련 속성들
        self.domain_keywords = []
        self.boost_multiplier = 2.0
        self.stopwords = set()

        # 한글 토크나이저 초기화
        self._init_tokenizer()

    def _get_default_model_path(self) -> str:
        """기본 모델 파일 경로 반환"""
        current_dir = Path(__file__).parent
        app_dir = current_dir.parent
        return str(app_dir / "searcher_model.pkl")

    def _init_tokenizer(self):
        """한글 토크나이저 초기화"""
        if not KOREAN_NLP_AVAILABLE:
            logger.warning("Korean NLP not available. Using basic tokenization.")
            return

        try:
            # Mecab이 있으면 사용 (더 정확함)
            self.tokenizer = Mecab()
            logger.info("Mecab tokenizer initialized successfully")
        except Exception as e:
            try:
                # Mecab이 없으면 Okt 사용
                self.tokenizer = Okt()
                logger.info("Okt tokenizer initialized successfully")
            except Exception as e2:
                logger.warning(f"Failed to initialize Korean tokenizers: {e}, {e2}")
                self.tokenizer = None

    def load_model(self) -> bool:
        """
        searcher_model.pkl 파일을 로드

        Returns:
            bool: 로드 성공 여부
        """
        try:
            logger.info(f"Loading model from: {self.model_path}")

            # 파일 존재 확인
            if not Path(self.model_path).exists():
                logger.error(f"Model file not found: {self.model_path}")
                return False

            file_size = Path(self.model_path).stat().st_size
            logger.info(f"File size: {file_size / 1024 / 1024:.2f} MB")

            # joblib으로 로드 (원본 노트북과 동일한 방식)
            logger.info("Loading with joblib (original method)...")
            model_data = joblib.load(self.model_path)

            # 데이터 할당
            self.df = model_data.get('df')
            self.vectorizer = model_data.get('vectorizer')
            self.tfidf_matrix = model_data.get('tfidf_matrix')
            self.config = model_data.get('config', {})

            # 로드 검증
            if self.df is None or self.vectorizer is None or self.tfidf_matrix is None:
                logger.error("Required model components missing")
                return False

            # 키워드 부스팅 설정 로드
            self._load_keyword_boosting_config()

            self.is_loaded = True
            logger.info(f"Model loaded successfully: {len(self.df)} cases, "
                       f"vocabulary: {len(self.vectorizer.vocabulary_):,}")

            return True

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def _load_keyword_boosting_config(self):
        """키워드 부스팅 설정 로드"""
        try:
            # config에서 키워드 정보 로드
            self.domain_keywords = self.config.get('domain_keywords', [])
            self.boost_multiplier = self.config.get('boost_multiplier', 2.0)
            self.stopwords = set(self.config.get('stopwords', []))

            # config에 키워드가 없으면 기본 키워드 설정
            if not self.domain_keywords:
                self.domain_keywords = [
                    "산업재해", "작업", "부상", "사고", "재해", "안전", "근로", "업무",
                    "기계", "추락", "끼임", "절단", "화상", "감전", "질식", "중독",
                    "프레스", "크레인", "사다리", "비계", "용접", "절삭", "연삭",
                    "손가락", "팔", "다리", "머리", "허리", "목", "어깨", "무릎",
                    "골절", "타박", "열상", "화상", "염좌", "탈구", "파열", "절단",
                    "산재보험", "보상금", "치료비", "요양급여", "장해급여", "휴업급여",
                    "근로복지공단", "산업안전보건법", "승인", "불승인", "재심", "이의신청"
                ]

            # 기본 불용어 설정
            if not self.stopwords:
                self.stopwords = {
                    '이', '그', '저', '것', '는', '은', '이다', '있다', '하다', '되다',
                    '의', '가', '을', '를', '에', '와', '과', '로', '으로', '에서',
                    '부터', '까지', '에게', '한테', '보다', '처럼', '같이', '따라',
                    '및', '또는', '그리고', '하지만', '그러나', '따라서', '그런데'
                }

            logger.info(f"Keyword boosting configured: {len(self.domain_keywords)} domain keywords, "
                       f"boost multiplier: {self.boost_multiplier}")

        except Exception as e:
            logger.warning(f"Failed to load keyword boosting config: {e}, using defaults")
            # 기본값 설정
            self.domain_keywords = ["산업재해", "작업", "부상", "사고", "재해"]
            self.boost_multiplier = 2.0
            self.stopwords = {'이', '그', '저', '것', '는', '은'}

    def _tokenize(self, text: str) -> List[str]:
        """
        텍스트 토크나이징

        Args:
            text: 토크나이징할 텍스트

        Returns:
            List[str]: 토큰 리스트
        """
        if not text:
            return []

        # 기본 전처리
        text = re.sub(r'[^\w\s]', ' ', text)  # 특수문자 제거
        text = re.sub(r'\s+', ' ', text)      # 여러 공백을 하나로
        text = text.strip().lower()

        if self.tokenizer and KOREAN_NLP_AVAILABLE:
            try:
                # 한글 형태소 분석
                if hasattr(self.tokenizer, 'morphs'):
                    tokens = self.tokenizer.morphs(text)
                else:
                    tokens = self.tokenizer.nouns(text)

                # 길이 2 이상의 토큰만 유지하고 불용어 제거
                tokens = [token for token in tokens
                         if len(token) >= 2 and token not in self.stopwords]

                # 도메인 키워드 중복 추가 (Test_casePedia 방식)
                domain_words = [token for token in tokens if token in self.domain_keywords]
                final_tokens = list(set(tokens + domain_words))  # 중복 제거

                return final_tokens

            except Exception as e:
                logger.warning(f"Korean tokenization failed: {e}, using basic split")

        # 기본 토크나이징 (fallback)
        tokens = text.split()
        tokens = [token for token in tokens
                 if len(token) >= 2 and token not in self.stopwords]

        # 기본 토큰화에도 도메인 키워드 중복 추가 적용
        domain_words = [token for token in tokens if token in self.domain_keywords]
        final_tokens = list(set(tokens + domain_words))  # 중복 제거

        return final_tokens

    def search(self, query: str, top_k: int = 10, category_filter: Optional[str] = None) -> List[PrecedentResult]:
        """
        판례 검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            category_filter: 카테고리 필터

        Returns:
            List[PrecedentResult]: 검색 결과 리스트
        """
        if not self.is_loaded:
            logger.error("Model not loaded. Call load_model() first.")
            return []

        try:
            # 쿼리 전처리
            query_tokens = self._tokenize(query)
            if not query_tokens:
                logger.warning("No valid tokens found in query")
                return []

            processed_query = ' '.join(query_tokens)
            query_set = set(query_tokens)
            logger.info(f"Processed query: '{processed_query}' (from: '{query}')")

            # TF-IDF 벡터화
            query_vector = self.vectorizer.transform([processed_query])

            # 코사인 유사도 계산 (올바른 방법)
            base_similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]

            # 키워드 부스팅 적용
            similarities = self._apply_keyword_boosting(base_similarities, query_set, query_tokens)

            # 카테고리 필터링
            df_filtered = self.df.copy()
            if category_filter and 'category' in df_filtered.columns:
                df_filtered = df_filtered[df_filtered['category'] == category_filter]
                # 필터링된 인덱스에 맞춰 유사도 조정
                filtered_indices = df_filtered.index.tolist()
                similarities = similarities[filtered_indices]

            # 상위 결과 선택
            top_indices = np.argsort(similarities)[::-1][:top_k]

            # 결과 생성
            results = []
            for idx in top_indices:
                if float(similarities[idx]) >= 0.001:  # 유사도 임계값 추가 완화 (Test_casePedia 수준 매칭)
                    original_idx = df_filtered.iloc[idx].name if category_filter else idx
                    case_data = self.df.iloc[original_idx]

                    result = PrecedentResult(
                        case_id=f"CASE_{original_idx}",
                        title=str(case_data.get('title', 'Unknown')),
                        content=str(case_data.get('noncontent', '')),
                        court=str(case_data.get('courtname', 'Unknown Court')),
                        date=str(case_data.get('kinda', 'Unknown Date')),
                        similarity=float(similarities[idx]),
                        category=case_data.get('category', 'Unknown'),
                        keywords=self._extract_keywords(processed_query)
                    )
                    results.append(result)

            logger.info(f"Found {len(results)} relevant cases for query: '{query}'")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 주요 키워드 추출"""
        if not text:
            return []

        # 기본적인 키워드 추출 (빈도 기반)
        tokens = self._tokenize(text)

        # 불용어 제거 (간단한 버전)
        stopwords = {'이', '그', '저', '것', '는', '은', '이다', '있다', '하다', '되다'}
        keywords = [token for token in tokens if token not in stopwords and len(token) >= 2]

        # 빈도 계산 후 상위 키워드 반환
        from collections import Counter
        keyword_counts = Counter(keywords)
        return [word for word, count in keyword_counts.most_common(10)]

    def _apply_keyword_boosting(
        self,
        base_similarities: np.ndarray,
        query_set: set,
        query_tokens: List[str]
    ) -> np.ndarray:
        """
        키워드 부스팅 적용 (Test_casePedia.ipynb 방식)

        Args:
            base_similarities: 기본 코사인 유사도 결과
            query_set: 쿼리 토큰 집합
            query_tokens: 쿼리 토큰 리스트

        Returns:
            np.ndarray: 부스팅이 적용된 유사도
        """
        boosted = base_similarities.copy()

        # tokens 컬럼이 없는 경우를 위한 처리
        if 'tokens' not in self.df.columns:
            logger.warning("No tokens column found, skipping keyword boosting")
            return boosted

        try:
            for i, similarity in enumerate(base_similarities):
                try:
                    # 문서의 토큰 가져오기 (Jupyter 노트북 방식: 단순하고 확실함)
                    tokens_data = self.df.iloc[i]['tokens']

                    # tokens가 None이거나 빈 값인 경우 건너뛰기
                    if pd.isna(tokens_data) or not tokens_data:
                        continue

                    doc_tokens = set(tokens_data)

                    # 공통 키워드 찾기
                    common_keywords = query_set & doc_tokens

                    if common_keywords:
                        # 도메인 키워드 가중치 계산
                        domain_count = sum(1 for kw in common_keywords
                                         if kw in self.domain_keywords)

                        # 매칭 비율 계산
                        match_ratio = len(common_keywords) / max(len(query_tokens), 1)

                        # 부스팅 계산 (Test_casePedia 방식)
                        boost_factor = match_ratio * (1 + domain_count * 0.2) * (self.boost_multiplier - 1)

                        # 유사도 부스팅 적용 (최대 1.0으로 제한)
                        boosted[i] = min(similarity * (1 + boost_factor), 1.0)

                        # 첫 번째 부스팅 사례 로그
                        if i == 0 and boost_factor > 0:
                            logger.info(f"Keyword boosting applied: match_ratio={match_ratio:.3f}, "
                                      f"domain_count={domain_count}, boost_factor={boost_factor:.3f}, "
                                      f"original_sim={similarity:.3f} → boosted_sim={boosted[i]:.3f}")

                except Exception as e:
                    # 개별 문서 처리 실패 시 원본 유사도 유지
                    logger.warning(f"Failed to apply boosting to document {i}: {e}")
                    continue

            # 부스팅 통계 로그
            boosted_count = sum(1 for i in range(len(base_similarities))
                              if abs(boosted[i] - base_similarities[i]) > 0.001)
            if boosted_count > 0:
                logger.info(f"Keyword boosting applied to {boosted_count}/{len(base_similarities)} documents")

        except Exception as e:
            logger.error(f"Keyword boosting failed: {e}, returning original similarities")
            return base_similarities

        return boosted

    def generate_report(self, query: str, top_n: int = 3) -> Dict[str, Any]:
        """
        검색 결과 보고서 생성

        Args:
            query: 검색 쿼리
            top_n: 분석할 상위 결과 수

        Returns:
            Dict[str, Any]: 분석 보고서
        """
        if not self.is_loaded:
            return {"error": "Model not loaded"}

        try:
            # 검색 수행
            search_results = self.search(query, top_k=top_n * 2)  # 여유있게 검색

            if not search_results:
                return {
                    "query": query,
                    "total_results": 0,
                    "message": "관련된 판례를 찾을 수 없습니다."
                }

            # 상위 결과 분석
            top_results = search_results[:top_n]

            # 카테고리 분석
            categories = {}
            for result in search_results:
                if result.category:
                    categories[result.category] = categories.get(result.category, 0) + 1

            # 평균 유사도 계산
            avg_similarity = np.mean([r.similarity for r in top_results])

            # 법원별 분포
            courts = {}
            for result in top_results:
                courts[result.court] = courts.get(result.court, 0) + 1

            # 키워드 통계
            all_keywords = []
            for result in top_results:
                if result.keywords:
                    all_keywords.extend(result.keywords)

            from collections import Counter
            keyword_stats = Counter(all_keywords).most_common(10)

            report = {
                "query": query,
                "search_time": datetime.now().isoformat(),
                "total_results": len(search_results),
                "analyzed_cases": len(top_results),
                "average_similarity": round(avg_similarity, 3),
                "top_cases": [
                    {
                        "case_id": r.case_id,
                        "title": r.title[:100] + "..." if len(r.title) > 100 else r.title,
                        "court": r.court,
                        "date": r.date,
                        "similarity": round(r.similarity, 3),
                        "summary": r.content[:200] + "..." if len(r.content) > 200 else r.content
                    }
                    for r in top_results
                ],
                "category_distribution": categories,
                "court_distribution": courts,
                "key_keywords": [{"keyword": k, "frequency": v} for k, v in keyword_stats],
                "recommendation": self._generate_recommendation(avg_similarity, categories)
            }

            return report

        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {"error": f"보고서 생성 중 오류 발생: {str(e)}"}

    def _generate_recommendation(self, avg_similarity: float, categories: Dict[str, int]) -> str:
        """분석 결과 기반 권고사항 생성"""
        if avg_similarity > 0.7:
            rec = "매우 유사한 판례들이 발견되었습니다. "
        elif avg_similarity > 0.5:
            rec = "적절한 유사도의 판례들이 발견되었습니다. "
        else:
            rec = "유사도가 낮은 판례들입니다. 검색어를 다시 확인해보세요. "

        if categories:
            main_category = max(categories.keys(), key=lambda k: categories[k])
            rec += f"주로 '{main_category}' 카테고리와 관련된 사건입니다."

        return rec

    def get_statistics(self) -> Dict[str, Any]:
        """모델 및 데이터 통계 반환"""
        if not self.is_loaded:
            return {"error": "Model not loaded"}

        stats = {
            "total_cases": len(self.df),
            "vocabulary_size": len(self.vectorizer.vocabulary_) if self.vectorizer else 0,
            "tfidf_matrix_shape": self.tfidf_matrix.shape if self.tfidf_matrix is not None else None,
            "available_columns": list(self.df.columns) if self.df is not None else [],
            "korean_nlp_available": KOREAN_NLP_AVAILABLE,
            "tokenizer_type": type(self.tokenizer).__name__ if self.tokenizer else "basic",
            "config": self.config
        }

        # 카테고리 통계
        if 'category' in self.df.columns:
            stats["categories"] = self.df['category'].value_counts().to_dict()

        # 법원별 통계
        court_col = 'court' if 'court' in self.df.columns else '법원'
        if court_col in self.df.columns:
            stats["courts"] = self.df[court_col].value_counts().head(10).to_dict()

        return stats


# 전역 인스턴스 (싱글톤 패턴)
_searcher_instance: Optional[WorkInjuryCaseSearcher] = None


def get_searcher() -> WorkInjuryCaseSearcher:
    """
    WorkInjuryCaseSearcher 싱글톤 인스턴스 반환
    FastAPI 의존성 주입용
    """
    global _searcher_instance

    if _searcher_instance is None:
        _searcher_instance = WorkInjuryCaseSearcher()

        # 모델 로드 시도
        if not _searcher_instance.load_model():
            logger.error("Failed to load searcher model on initialization")

    return _searcher_instance


def init_searcher(model_path: Optional[str] = None) -> bool:
    """
    Searcher 강제 초기화
    테스트나 수동 설정시 사용
    """
    global _searcher_instance

    _searcher_instance = WorkInjuryCaseSearcher(model_path)
    return _searcher_instance.load_model()


# 편의 함수들
def search_precedents(query: str, top_k: int = 10, category_filter: Optional[str] = None) -> List[PrecedentResult]:
    """판례 검색 편의 함수"""
    searcher = get_searcher()
    return searcher.search(query, top_k, category_filter)


def generate_precedent_report(query: str, top_n: int = 3) -> Dict[str, Any]:
    """판례 분석 보고서 생성 편의 함수"""
    searcher = get_searcher()
    return searcher.generate_report(query, top_n)


def get_searcher_stats() -> Dict[str, Any]:
    """Searcher 통계 조회 편의 함수"""
    searcher = get_searcher()
    return searcher.get_statistics()


if __name__ == "__main__":
    # 테스트 코드
    searcher = WorkInjuryCaseSearcher()

    if searcher.load_model():
        print("🎉 모델 로드 성공!")

        # 통계 출력
        stats = searcher.get_statistics()
        print(f"📊 총 판례 수: {stats['total_cases']:,}개")
        print(f"📚 어휘 크기: {stats['vocabulary_size']:,}개")

        # 테스트 검색
        test_query = "작업 중 다친 손가락"
        print(f"\n🔍 테스트 검색: '{test_query}'")

        results = searcher.search(test_query, top_k=3)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result.title}")
            print(f"   법원: {result.court}")
            print(f"   유사도: {result.similarity:.3f}")
            print(f"   요약: {result.content[:100]}...")

        # 보고서 생성
        print(f"\n📋 분석 보고서 생성...")
        report = searcher.generate_report(test_query)
        print(f"   평균 유사도: {report.get('average_similarity', 'N/A')}")
        print(f"   관련 판례 수: {report.get('total_results', 'N/A')}개")

    else:
        print("❌ 모델 로드 실패")