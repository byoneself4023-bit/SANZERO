"""
AI 판례 분석 서비스
RAG 기반 유사 판례 검색 및 LLM 분석 서비스
"""

import json
import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from app.utils.database import supabase
from app.utils.security import security
from app.utils.config import settings
from app.utils.api_monitor import api_monitor

# 조건부 import - 라이브러리가 없어도 서비스 동작
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    openai = None
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False


class AnalysisService:
    """AI 판례 분석 서비스"""

    def __init__(self):
        # 로거 초기화
        self.logger = logging.getLogger(__name__)

        # SBERT 모델 초기화 (한국어 최적화)
        self.embedding_model = None
        self.openai_client = None
        self.anthropic_client = None
        self.fallback_mode = False
        self._initialize_models()

    def _initialize_models(self):
        """AI 모델들 초기화"""
        try:
            # SBERT 모델 로드 시도
            if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer:
                try:
                    self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                    self.logger.info("SBERT embedding model loaded successfully")
                except Exception as e:
                    self.logger.warning(f"Failed to load SBERT model: {e}, using fallback mode")
                    self.fallback_mode = True
            else:
                self.logger.warning("sentence-transformers not available, using fallback mode")
                self.fallback_mode = True

            # OpenAI 클라이언트 초기화
            if OPENAI_AVAILABLE and openai and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                try:
                    self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                    self.logger.info("OpenAI client initialized")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize OpenAI client: {e}")
            else:
                self.logger.warning("OpenAI library not available or API key not set")

            # Anthropic 클라이언트 초기화
            if ANTHROPIC_AVAILABLE and anthropic and hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
                try:
                    self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                    self.logger.info("Anthropic client initialized")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize Anthropic client: {e}")
            else:
                self.logger.warning("Anthropic library not available or API key not set")

        except Exception as e:
            self.logger.error(f"Failed to initialize AI models: {e}")
            self.fallback_mode = True
            # 모델 초기화 실패 시에도 서비스는 동작하도록 함

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """텍스트를 벡터로 임베딩"""
        try:
            # 텍스트 전처리
            cleaned_text = security.sanitize_text(text)
            if not cleaned_text.strip():
                return None

            # Fallback 모드 또는 모델 없음
            if self.fallback_mode or not self.embedding_model:
                self.logger.info("Using fallback embedding generation")
                return self._generate_fallback_embedding(cleaned_text)

            # 실제 SBERT 임베딩 생성 (비동기 처리)
            embedding = await asyncio.to_thread(
                lambda: self.embedding_model.encode(cleaned_text)
            )
            return embedding.tolist()

        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            # 에러 발생 시 fallback 사용
            return self._generate_fallback_embedding(cleaned_text)

    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """Fallback 임베딩 생성 (ML 라이브러리 없이)"""
        import hashlib
        import math

        # 텍스트 기반 특징 벡터 생성 (384차원)
        features = []

        # 1. 텍스트 길이 특징
        features.append(len(text) / 1000.0)  # 정규화

        # 2. 문자 빈도 특징
        char_counts = {}
        for char in text.lower():
            char_counts[char] = char_counts.get(char, 0) + 1

        # 주요 문자들의 빈도
        common_chars = 'abcdefghijklmnopqrstuvwxyz가나다라마바사아자차카타파하'
        char_limit = min(50, len(common_chars))  # 안전한 길이 제한
        for char in common_chars[:char_limit]:  # 실제 문자 개수만큼 (40개)
            features.append(char_counts.get(char, 0) / len(text) if text else 0)

        # 3. 해시 기반 특징
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        for i in range(32):  # 32바이트
            features.append((hash_bytes[i] % 256) / 255.0)

        # 4. 키워드 기반 특징 (산재 관련)
        keywords = [
            '산업재해', '산재', '사고', '부상', '절단', '골절', '화상', '타박상',
            '제조업', '건설업', '서비스업', '기계', '안전', '보상금', '승인', '거부',
            '병원', '치료', '수술', '재활', '장해', '등급', '노무사', '상담'
        ]

        for keyword in keywords:
            features.append(1.0 if keyword in text else 0.0)

        # 5. 나머지 차원을 0으로 패딩하거나 반복으로 채움
        target_dim = 1536  # OpenAI text-embedding-ada-002 차원과 일치
        current_len = len(features)

        # 간단한 패딩
        for i in range(target_dim - current_len):
            features.append(0.1 * (i % 10))

        # 정확히 1536차원으로 자르기
        return features[:target_dim]

    async def search_similar_precedents(
        self,
        query_text: str,
        similarity_threshold: float = 0.7,
        max_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """유사 판례 검색"""
        try:
            # 쿼리 텍스트 임베딩 생성
            query_embedding = await self.generate_embedding(query_text)
            if not query_embedding:
                self.logger.error("Failed to generate query embedding")
                return []

            # Supabase에서 벡터 유사도 검색
            query = supabase.table("precedents").select("""
                id, case_number, title, summary, court_name, case_date,
                outcome, compensation_amount, injury_type, industry_code,
                keywords
            """).eq("is_active", True)

            # 필터 적용
            if filters:
                if filters.get("injury_type"):
                    query = query.eq("injury_type", filters["injury_type"])
                if filters.get("industry_code"):
                    query = query.eq("industry_code", filters["industry_code"])
                if filters.get("outcome"):
                    query = query.eq("outcome", filters["outcome"])

            # 벡터 유사도 검색 실행
            response = await asyncio.to_thread(
                lambda: query.limit(max_results * 2).execute()  # 필터링 고려해 더 많이 가져옴
            )

            if not response.data:
                return []

            # 실제 벡터 유사도 계산
            similar_precedents = []
            for precedent in response.data:
                precedent_embedding = precedent.get("embedding")

                if precedent_embedding and query_embedding:
                    # 코사인 유사도 계산
                    similarity_score = self._calculate_cosine_similarity(
                        query_embedding, precedent_embedding
                    )
                else:
                    # 임베딩이 없는 경우 키워드 기반 유사도
                    similarity_score = self._calculate_text_similarity(
                        query_text, precedent.get("title", "") + " " + precedent.get("summary", "")
                    )

                similar_precedents.append({
                    "precedent": precedent,
                    "similarity_score": round(similarity_score, 3),
                    "matching_factors": {
                        "injury_type_match": filters and filters.get("injury_type") == precedent.get("injury_type"),
                        "industry_match": filters and filters.get("industry_code") == precedent.get("industry_code"),
                        "embedding_match": precedent_embedding is not None
                    }
                })

            # 유사도로 정렬
            similar_precedents.sort(key=lambda x: x["similarity_score"], reverse=True)

            # 유사도 임계값 필터링
            filtered_precedents = [
                p for p in similar_precedents
                if p["similarity_score"] >= similarity_threshold
            ]

            return filtered_precedents[:max_results]

        except Exception as e:
            self.logger.error(f"Failed to search similar precedents: {e}")
            return []

    async def analyze_precedents_with_llm(
        self,
        user_case: Dict[str, Any],
        similar_precedents: List[Dict[str, Any]],
        analysis_type: str = "comprehensive"
    ) -> Optional[Dict[str, Any]]:
        """LLM을 통한 판례 분석"""
        try:
            # 사용자 사건 요약
            case_summary = self._create_case_summary(user_case)

            # 유사 판례 요약
            precedents_summary = self._create_precedents_summary(similar_precedents)

            # 분석 프롬프트 생성
            prompt = self._create_analysis_prompt(case_summary, precedents_summary, analysis_type)

            # LLM 분석 실행
            analysis_result = await self._call_llm_analysis(prompt)

            if not analysis_result:
                return None

            # 분석 결과 구조화
            structured_result = {
                "analysis_summary": analysis_result.get("summary", ""),
                "success_probability": analysis_result.get("success_probability", 50.0),
                "key_factors": analysis_result.get("key_factors", []),
                "similar_precedents_analysis": analysis_result.get("precedents_analysis", []),
                "recommended_actions": analysis_result.get("recommended_actions", []),
                "legal_reasoning": analysis_result.get("legal_reasoning", ""),
                "risk_assessment": analysis_result.get("risk_assessment", {}),
                "confidence_score": analysis_result.get("confidence", 75.0),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "model_version": "gpt-4-turbo"  # 또는 사용된 모델명
            }

            return structured_result

        except Exception as e:
            self.logger.error(f"Failed to analyze precedents with LLM: {e}")
            return None

    def _create_case_summary(self, user_case: Dict[str, Any]) -> str:
        """사용자 사건 요약 생성"""
        return f"""
        사고 날짜: {user_case.get('incident_date', 'N/A')}
        사고 장소: {user_case.get('incident_location', 'N/A')}
        부상 유형: {user_case.get('injury_type', 'N/A')}
        사고 경위: {user_case.get('incident_description', 'N/A')}
        심각도: {user_case.get('severity_level', 'N/A')}
        업종: {user_case.get('industry_code', 'N/A')}
        """

    def _create_precedents_summary(self, precedents: List[Dict[str, Any]]) -> str:
        """유사 판례 요약 생성 (토큰 제한 고려)"""
        if not precedents:
            return "유사 판례 없음"

        summary_parts = []
        for i, item in enumerate(precedents[:2], 1):  # 상위 2개만으로 더 축소 (비용 절약)
            precedent = item["precedent"]
            similarity = item["similarity_score"]

            # 요약을 30자로 더 축소 (비용 절약)
            short_summary = precedent.get('summary', 'N/A')[:30] + "..."

            summary_parts.append(f"판례{i}({similarity:.1f}): {precedent.get('outcome', 'N/A')}, {precedent.get('compensation_amount', 0)//10000}만원")

        return "\n".join(summary_parts)

    def _create_analysis_prompt(
        self,
        case_summary: str,
        precedents_summary: str,
        analysis_type: str
    ) -> str:
        """LLM 분석을 위한 프롬프트 생성 (토큰 최적화)"""
        return f"""사건: {case_summary}
판례: {precedents_summary}

JSON 응답:
{{
    "summary": "분석요약(1문장)",
    "success_probability": 75.5,
    "key_factors": {{"positive": ["요인1"], "negative": ["요인1"]}},
    "recommended_actions": ["조치1", "조치2"],
    "confidence": 85.0
}}"""

    async def _call_llm_analysis(self, prompt: str) -> Optional[Dict[str, Any]]:
        """LLM API 호출"""
        try:
            # OpenAI API 사용 (우선순위)
            if self.openai_client:
                response = await self._call_openai(prompt)
                if response:
                    return response

            # Anthropic API 사용 (대안)
            if self.anthropic_client:
                response = await self._call_anthropic(prompt)
                if response:
                    return response

            # Fallback 분석 (LLM 없이)
            self.logger.warning("No LLM client available, using fallback analysis")
            return self._generate_fallback_analysis(prompt)

        except Exception as e:
            self.logger.error(f"Failed to call LLM: {e}")
            # 에러 시에도 fallback 사용
            return self._generate_fallback_analysis(prompt)

    def _generate_fallback_analysis(self, prompt: str) -> Dict[str, Any]:
        """Fallback 분석 생성 (LLM API 없이)"""
        # 프롬프트에서 키워드 추출 및 간단한 규칙 기반 분석
        prompt_lower = prompt.lower()

        # 키워드 기반 유리도 계산
        positive_keywords = ['업무중', '사고', '부상', '안전장치', '부족', '제조업', '건설업', '절단', '골절']
        negative_keywords = ['음주', '고의', '개인적', '질병']

        positive_score = sum(10 for keyword in positive_keywords if keyword in prompt_lower)
        negative_score = sum(15 for keyword in negative_keywords if keyword in prompt_lower)

        base_probability = 65.0  # 기본 유리도
        final_probability = max(20.0, min(95.0, base_probability + positive_score - negative_score))

        # 부상 유형별 조정
        if any(injury in prompt_lower for injury in ['절단', '골절', '화상']):
            final_probability += 10.0
        elif any(injury in prompt_lower for injury in ['타박상', '염좌']):
            final_probability += 5.0

        # 업종별 조정
        if any(industry in prompt_lower for industry in ['제조업', '건설업']):
            final_probability += 5.0

        final_probability = max(15.0, min(95.0, final_probability))

        return {
            "summary": f"규칙 기반 분석 결과, 사안의 유리도는 {final_probability:.1f}%입니다. 업무 관련성과 사고 경위를 고려한 결과입니다.",
            "favorability_score": final_probability,
            "key_factors": {
                "positive": [
                    "업무 중 발생한 사고",
                    "명확한 사고 경위",
                    "즉시 병원 치료"
                ] if positive_score > 0 else [],
                "negative": [
                    "추가 검토 필요 사항 존재"
                ] if negative_score > 0 else []
            },
            "recommended_actions": [
                "의료진단서 및 소견서 준비",
                "사고 경위서 상세 작성",
                "목격자 진술서 확보",
                "노무사 상담을 통한 전문 검토"
            ],
            "risk_assessment": {
                "level": "중간" if final_probability < 70 else "낮음",
                "factors": [
                    "업무 관련성 입증 필요",
                    "의료 기록 충실성",
                    "사고 경위의 명확성"
                ]
            },
            "confidence": 75.0,
            "model_note": "현재 AI 모델을 사용할 수 없어 규칙 기반 분석을 제공합니다. 더 정확한 분석을 위해서는 전문 노무사 상담을 권장합니다."
        }

    async def _call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """OpenAI API 호출 (토큰 최적화)"""
        try:
            # Rate limiting 확인
            if not await api_monitor.check_rate_limit("analysis"):
                self.logger.warning("Analysis service rate limit exceeded")
                return None

            response = await asyncio.to_thread(
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",  # 더 효율적인 모델 사용
                    messages=[
                        {"role": "system", "content": "산재전문가"},  # 프롬프트 단축
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500  # 토큰 수 대폭 감소 (비용 절약)
                )
            )

            # API 사용량 추적
            usage = response.usage
            await api_monitor.track_usage(
                service="analysis",
                provider="openai",
                model="gpt-4o-mini",
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens
            )

            content = response.choices[0].message.content

            # JSON 응답 파싱 시도
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # JSON이 아닌 경우 텍스트로 처리
                return {"summary": content, "success_probability": 50.0}

        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            return None

    async def _call_anthropic(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Anthropic Claude API 호출 (토큰 최적화)"""
        try:
            # Rate limiting 확인
            if not await api_monitor.check_rate_limit("analysis"):
                self.logger.warning("Analysis service rate limit exceeded")
                return None

            response = await asyncio.to_thread(
                lambda: self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",  # 더 효율적인 모델 사용
                    max_tokens=500,  # 토큰 수 대폭 감소 (비용 절약)
                    temperature=0.3,
                    system="산재전문가",  # 시스템 프롬프트 단축
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
            )

            # API 사용량 추적
            usage = response.usage
            await api_monitor.track_usage(
                service="analysis",
                provider="anthropic",
                model="claude-3-haiku-20240307",
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens
            )

            content = response.content[0].text

            # JSON 응답 파싱 시도
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"summary": content, "success_probability": 50.0}

        except Exception as e:
            self.logger.error(f"Anthropic API call failed: {e}")
            return None

    async def create_analysis_request(
        self,
        user_id: str,
        query_text: str,
        case_description: str,
        application_id: Optional[str] = None,
        industry_type: Optional[str] = None,
        injury_type: Optional[str] = None,
        accident_circumstances: Optional[str] = None
    ) -> Optional[str]:
        """분석 요청 생성"""
        try:
            # XSS 방어
            query_text = security.sanitize_text(query_text)
            case_description = security.sanitize_text(case_description)
            if accident_circumstances:
                accident_circumstances = security.sanitize_text(accident_circumstances)

            request_data = {
                "user_id": user_id,
                "application_id": application_id,
                "query_text": query_text,
                "analysis_type": "precedent_search",
                "status": "pending",
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            response = await asyncio.to_thread(
                lambda: supabase.table("analysis_requests").insert(request_data).execute()
            )

            if response.data:
                request_id = response.data[0]["id"]
                self.logger.info(f"Analysis request created: {request_id}")

                # 백그라운드에서 분석 수행
                asyncio.create_task(self._process_analysis_request(request_id, {
                    "case_description": case_description,
                    "industry_type": industry_type,
                    "injury_type": injury_type,
                    "accident_circumstances": accident_circumstances,
                    "query_text": query_text
                }))

                return request_id

            return None

        except Exception as e:
            self.logger.error(f"Failed to create analysis request: {e}")
            return None

    async def _process_analysis_request(self, request_id: str, case_data: Dict[str, Any]):
        """분석 요청 처리 (백그라운드)"""
        try:
            start_time = datetime.now()

            # 상태를 processing으로 변경
            await asyncio.to_thread(
                lambda: supabase.table("analysis_requests")
                .update({"status": "processing", "updated_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", request_id).execute()
            )

            # 1. 유사 판례 검색
            similar_precedents = await self.search_similar_precedents(
                query_text=case_data["query_text"],
                similarity_threshold=0.6,
                max_results=10,
                filters={
                    "injury_type": case_data.get("injury_type"),
                    "industry_code": case_data.get("industry_type")
                }
            )

            # 2. LLM 분석
            analysis_result = await self.analyze_precedents_with_llm(
                user_case=case_data,
                similar_precedents=similar_precedents,
                analysis_type="comprehensive"
            )

            # 3. 결과 저장
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            result_data = {
                "similar_precedents": similar_precedents,
                "analysis_result": analysis_result,
                "processing_time_ms": processing_time
            }

            await asyncio.to_thread(
                lambda: supabase.table("analysis_requests")
                .update({
                    "status": "completed",
                    "result": result_data,
                    "processing_time_ms": processing_time,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                .eq("id", request_id).execute()
            )

            self.logger.info(f"Analysis request {request_id} completed in {processing_time}ms")

        except Exception as e:
            self.logger.error(f"Failed to process analysis request {request_id}: {e}")

            # 에러 상태로 변경
            await asyncio.to_thread(
                lambda: supabase.table("analysis_requests")
                .update({
                    "status": "failed",
                    "error_message": str(e),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                .eq("id", request_id).execute()
            )

    async def get_analysis_result(self, request_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """분석 결과 조회"""
        try:
            response = await asyncio.to_thread(
                lambda: supabase.table("analysis_requests")
                .select("*")
                .eq("id", request_id)
                .eq("user_id", user_id)
                .eq("is_active", True)
                .single()
                .execute()
            )

            if response.data:
                result = response.data.copy()

                # 날짜 문자열을 datetime 객체로 변환 (템플릿에서 strftime 사용 가능하도록)
                try:
                    if result.get("created_at"):
                        result["created_at"] = datetime.fromisoformat(result["created_at"].replace('Z', '+00:00'))
                    if result.get("updated_at"):
                        result["updated_at"] = datetime.fromisoformat(result["updated_at"].replace('Z', '+00:00'))
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"Failed to parse datetime fields: {e}")
                    # 파싱 실패 시 원본 유지

                return result

            return None

        except Exception as e:
            self.logger.error(f"Failed to get analysis result: {e}")
            return None

    async def get_user_analysis_history(
        self,
        user_id: str,
        limit: int = 20,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """사용자 분석 요청 내역 조회"""
        try:
            query = supabase.table("analysis_requests").select("""
                id, query_text, analysis_type, status,
                processing_time_ms, created_at, updated_at
            """).eq("user_id", user_id).eq("is_active", True)

            if status_filter:
                query = query.eq("status", status_filter)

            response = await asyncio.to_thread(
                lambda: query.order("created_at", desc=True).limit(limit).execute()
            )

            return response.data or []

        except Exception as e:
            self.logger.error(f"Failed to get user analysis history: {e}")
            return []

    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        try:
            if NUMPY_AVAILABLE and np:
                # numpy 배열로 변환
                arr1 = np.array(vec1)
                arr2 = np.array(vec2)

                # 코사인 유사도 공식: dot(a, b) / (norm(a) * norm(b))
                dot_product = np.dot(arr1, arr2)
                norm1 = np.linalg.norm(arr1)
                norm2 = np.linalg.norm(arr2)

                if norm1 == 0 or norm2 == 0:
                    return 0.0

                similarity = dot_product / (norm1 * norm2)
                return max(0.0, min(1.0, similarity))  # 0-1 범위로 클램핑
            else:
                # Pure Python fallback
                return self._calculate_cosine_similarity_fallback(vec1, vec2)

        except Exception as e:
            self.logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0

    def _calculate_cosine_similarity_fallback(self, vec1: List[float], vec2: List[float]) -> float:
        """순수 Python으로 코사인 유사도 계산 (numpy 없이)"""
        try:
            import math

            # 내적 계산
            dot_product = sum(a * b for a, b in zip(vec1, vec2))

            # 노름 계산
            norm1 = math.sqrt(sum(a * a for a in vec1))
            norm2 = math.sqrt(sum(b * b for b in vec2))

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return max(0.0, min(1.0, similarity))  # 0-1 범위로 클램핑

        except Exception as e:
            self.logger.error(f"Failed to calculate cosine similarity fallback: {e}")
            return 0.0

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """텍스트 기반 유사도 계산 (벡터 임베딩이 없는 경우)"""
        try:
            if not text1 or not text2:
                return 0.0

            # 간단한 키워드 기반 유사도
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            if not words1 or not words2:
                return 0.0

            # 자카드 유사도 계산
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))

            return intersection / union if union > 0 else 0.0

        except Exception as e:
            self.logger.error(f"Failed to calculate text similarity: {e}")
            return 0.0

    async def summarize_precedent_content(self, case_id: str, content: str, title: str = "") -> Dict[str, Any]:
        """
        복잡한 판결문을 일반인이 이해하기 쉽게 요약하는 기능

        Args:
            case_id: 판례 ID
            content: 판결문 전체 내용
            title: 판례 제목 (선택사항)

        Returns:
            Dict containing:
                - summary: 쉬운 언어로 작성된 요약
                - key_points: 핵심 포인트들
                - outcome: 판결 결과 요약
                - significance: 이 판례의 의미
        """
        try:
            self.logger.info(f"Starting precedent content summarization for case {case_id}")

            # 내용이 너무 길면 처음 부분만 사용 (토큰 제한 고려)
            max_content_length = 2000
            truncated_content = content[:max_content_length] if len(content) > max_content_length else content

            # 요약을 위한 프롬프트 구성
            summary_prompt = f"""
다음 판례를 일반인이 쉽게 이해할 수 있도록 요약해주세요.

【판례 정보】
제목: {title if title else '제목 없음'}
내용: {truncated_content}

【요약 가이드】
1. 전문 법률 용어를 일상 언어로 바꿔서 설명
2. 핵심 쟁점을 간단명료하게 정리
3. 판결 결과와 그 이유를 알기 쉽게 설명
4. 일반인이 이해할 수 있는 수준으로 작성

다음 형식으로 응답해주세요:

**🏛️ 사건 개요**
(무엇에 대한 분쟁인지 간단히)

**🎯 핵심 쟁점**
(법원에서 판단해야 할 주요 문제)

**⚖️ 판결 결과**
(법원의 결론과 그 이유)

**💡 이 판례의 의미**
(이후 유사한 사건에 어떤 영향을 주는지)

**📝 한줄 요약**
(이 판례를 한 문장으로 정리하면)
"""

            # AI 요약 실행
            if OPENAI_AVAILABLE and self.openai_client:
                summary_result = await self._call_openai_for_summary(summary_prompt)
            elif ANTHROPIC_AVAILABLE and self.anthropic_client:
                summary_result = await self._call_anthropic_for_summary(summary_prompt)
            else:
                # Fallback: 규칙 기반 간단 요약
                summary_result = self._create_simple_summary(truncated_content, title)

            # 결과 구성
            result = {
                "success": True,
                "case_id": case_id,
                "summary": summary_result.get("summary", "요약을 생성할 수 없습니다."),
                "key_points": summary_result.get("key_points", []),
                "outcome": summary_result.get("outcome", "판결 결과를 확인할 수 없습니다."),
                "significance": summary_result.get("significance", "이 판례의 의미를 파악하지 못했습니다."),
                "one_line_summary": summary_result.get("one_line_summary", "간단 요약을 생성할 수 없습니다."),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content),
                "truncated": len(content) > max_content_length
            }

            self.logger.info(f"Successfully summarized precedent {case_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error summarizing precedent content for {case_id}: {e}")
            return {
                "success": False,
                "case_id": case_id,
                "error": f"요약 생성 중 오류가 발생했습니다: {str(e)}",
                "summary": "죄송합니다. 현재 이 판례를 요약할 수 없습니다.",
                "key_points": [],
                "outcome": "판결 결과를 확인할 수 없습니다.",
                "significance": "판례의 의미를 파악하지 못했습니다.",
                "one_line_summary": "요약을 생성할 수 없습니다."
            }

    async def _call_openai_for_summary(self, prompt: str) -> Dict[str, Any]:
        """OpenAI API를 사용한 판례 요약"""
        try:
            response = await asyncio.to_thread(
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 법률 전문가이면서 동시에 일반인에게 법률을 쉽게 설명하는 교육자입니다. 복잡한 법원 판결문을 누구나 이해할 수 있는 일상 언어로 설명해주세요."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1000
                )
            )

            content = response.choices[0].message.content
            return self._parse_summary_response(content)

        except Exception as e:
            self.logger.error(f"OpenAI summary API error: {e}")
            return {"summary": f"OpenAI 요약 실패: {str(e)}"}

    async def _call_anthropic_for_summary(self, prompt: str) -> Dict[str, Any]:
        """Anthropic API를 사용한 판례 요약"""
        try:
            message = await asyncio.to_thread(
                lambda: self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=1000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            content = message.content[0].text
            return self._parse_summary_response(content)

        except Exception as e:
            self.logger.error(f"Anthropic summary API error: {e}")
            return {"summary": f"Anthropic 요약 실패: {str(e)}"}

    def _parse_summary_response(self, content: str) -> Dict[str, Any]:
        """AI 응답에서 구조화된 요약 정보 추출"""
        try:
            # 섹션별로 내용 추출
            sections = {}
            current_section = None
            current_content = []

            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue

                # 섹션 헤더 감지
                if '🏛️ 사건 개요' in line:
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = 'case_overview'
                    current_content = []
                elif '🎯 핵심 쟁점' in line:
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = 'key_issues'
                    current_content = []
                elif '⚖️ 판결 결과' in line:
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = 'outcome'
                    current_content = []
                elif '💡 이 판례의 의미' in line:
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = 'significance'
                    current_content = []
                elif '📝 한줄 요약' in line:
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = 'one_line_summary'
                    current_content = []
                else:
                    # 일반 내용 라인
                    if current_section and line:
                        current_content.append(line)

            # 마지막 섹션 저장
            if current_section and current_content:
                sections[current_section] = '\n'.join(current_content)

            # 결과 구성
            case_overview = sections.get('case_overview', '').strip()
            key_issues = sections.get('key_issues', '').strip()
            outcome = sections.get('outcome', '').strip()
            significance = sections.get('significance', '').strip()
            one_line = sections.get('one_line_summary', '').strip()

            # 전체 요약 생성
            full_summary = f"{case_overview}\n\n{key_issues}".strip()

            return {
                "summary": full_summary if full_summary else content[:500],
                "key_points": [key_issues] if key_issues else [],
                "outcome": outcome if outcome else "판결 결과를 파악할 수 없습니다.",
                "significance": significance if significance else "판례의 의미를 확인할 수 없습니다.",
                "one_line_summary": one_line if one_line else content[:100]
            }

        except Exception as e:
            self.logger.warning(f"Failed to parse AI response structure: {e}")
            # 파싱 실패 시 전체 내용을 요약으로 사용
            return {
                "summary": content[:500] if content else "요약을 생성할 수 없습니다.",
                "key_points": [],
                "outcome": "판결 결과를 파악할 수 없습니다.",
                "significance": "판례의 의미를 확인할 수 없습니다.",
                "one_line_summary": content[:100] if content else "요약 없음"
            }

    def _create_simple_summary(self, content: str, title: str = "") -> Dict[str, Any]:
        """AI가 없을 때 사용하는 간단한 규칙 기반 요약"""
        try:
            # 키워드 기반 간단 분석
            content_lower = content.lower()

            # 판결 결과 키워드 확인
            if any(keyword in content_lower for keyword in ['승소', '인용', '취소', '지급']):
                outcome = "원고(신청인)에게 유리한 판결"
            elif any(keyword in content_lower for keyword in ['패소', '기각', '각하']):
                outcome = "원고(신청인)에게 불리한 판결"
            else:
                outcome = "판결 결과 확인 필요"

            # 간단 요약 생성
            summary = f"제목: {title}\n\n" if title else ""
            summary += f"내용: {content[:200]}..." if len(content) > 200 else content

            return {
                "summary": summary,
                "key_points": ["AI 분석을 사용할 수 없어 간단 요약만 제공"],
                "outcome": outcome,
                "significance": "정확한 분석을 위해서는 전문가 상담이 필요합니다.",
                "one_line_summary": f"{title} - {outcome}" if title else outcome
            }

        except Exception as e:
            return {
                "summary": f"간단 요약 생성 실패: {str(e)}",
                "key_points": [],
                "outcome": "판결 결과 확인 불가",
                "significance": "분석 불가",
                "one_line_summary": "요약 생성 실패"
            }


# 서비스 인스턴스 (싱글톤)
analysis_service = AnalysisService()