"""
SANZERO Redis 캐싱 시스템
AI 판례 분석 결과 캐싱을 통한 성능 최적화
"""

import json
import hashlib
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis not available. Caching will be disabled.")
    REDIS_AVAILABLE = False

class SearchCache:
    """
    판례 검색 결과 캐싱 클래스

    특징:
    - 쿼리 기반 해시키 생성
    - TTL 설정 (기본 1시간)
    - 압축 저장으로 메모리 효율성
    - 캐시 통계 제공
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 3600,  # 1시간
        key_prefix: str = "sanzero:precedent:",
        enable_compression: bool = True
    ):
        self.redis_client = None
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.enable_compression = enable_compression
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_sets": 0,
            "cache_errors": 0,
            "total_requests": 0
        }

        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # 연결 테스트
                self.redis_client.ping()
                logger.info(f"Redis cache initialized: {redis_url}")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Caching disabled.")
                self.redis_client = None
        else:
            logger.warning("Redis not available. Caching disabled.")

    def _make_cache_key(self, query: str, params: Dict[str, Any] = None) -> str:
        """
        캐시 키 생성

        Args:
            query: 검색 쿼리
            params: 추가 매개변수 (top_k, threshold 등)

        Returns:
            str: 해시된 캐시 키
        """
        # 쿼리 정규화
        normalized_query = query.strip().lower()

        # 매개변수 정규화
        if params is None:
            params = {}

        cache_params = {
            "query": normalized_query,
            "top_k": params.get("top_k", 10),
            "include_rag": params.get("include_rag_analysis", False),
            "timeout": params.get("timeout_seconds", 30),
            "threshold": params.get("threshold", 0.5)
        }

        # JSON 문자열로 직렬화 (정렬된 키)
        key_str = json.dumps(cache_params, sort_keys=True, ensure_ascii=False)

        # SHA-256 해시 생성
        hash_obj = hashlib.sha256(key_str.encode('utf-8'))
        cache_key = f"{self.key_prefix}{hash_obj.hexdigest()[:16]}"

        return cache_key

    def _compress_data(self, data: Dict[str, Any]) -> str:
        """데이터 압축 (간단한 JSON 압축)"""
        if not self.enable_compression:
            return json.dumps(data, ensure_ascii=False, default=str)

        try:
            import gzip
            import base64

            json_str = json.dumps(data, ensure_ascii=False, default=str)
            compressed = gzip.compress(json_str.encode('utf-8'))
            encoded = base64.b64encode(compressed).decode('ascii')

            return f"gzip:{encoded}"
        except Exception as e:
            logger.warning(f"Compression failed: {e}. Using uncompressed.")
            return json.dumps(data, ensure_ascii=False, default=str)

    def _decompress_data(self, data_str: str) -> Dict[str, Any]:
        """데이터 압축 해제"""
        try:
            if data_str.startswith("gzip:"):
                import gzip
                import base64

                encoded_data = data_str[5:]  # "gzip:" 제거
                compressed = base64.b64decode(encoded_data.encode('ascii'))
                json_str = gzip.decompress(compressed).decode('utf-8')

                return json.loads(json_str)
            else:
                return json.loads(data_str)
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return {}

    async def get_cached_result(
        self,
        query: str,
        params: Dict[str, Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        캐시된 결과 조회

        Args:
            query: 검색 쿼리
            params: 검색 매개변수

        Returns:
            Optional[Dict]: 캐시된 결과 또는 None
        """
        self.stats["total_requests"] += 1

        if not self.redis_client:
            self.stats["cache_misses"] += 1
            return None

        try:
            cache_key = self._make_cache_key(query, params)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                result = self._decompress_data(cached_data)
                if result:
                    self.stats["cache_hits"] += 1

                    # 캐시 메타데이터 추가
                    result["cache_info"] = {
                        "cache_hit": True,
                        "cached_at": result.get("cached_at", "unknown"),
                        "cache_key": cache_key[:8] + "...",  # 보안상 일부만 표시
                        "retrieval_time": datetime.now().isoformat()
                    }

                    logger.info(f"Cache HIT for query: {query[:50]}...")
                    return result

            self.stats["cache_misses"] += 1
            logger.debug(f"Cache MISS for query: {query[:50]}...")
            return None

        except Exception as e:
            self.stats["cache_errors"] += 1
            logger.error(f"Cache retrieval error: {e}")
            return None

    async def set_cached_result(
        self,
        query: str,
        params: Dict[str, Any],
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        결과 캐싱

        Args:
            query: 검색 쿼리
            params: 검색 매개변수
            result: 캐싱할 결과
            ttl: 캐시 유지 시간 (초)

        Returns:
            bool: 캐싱 성공 여부
        """
        if not self.redis_client:
            return False

        try:
            cache_key = self._make_cache_key(query, params)
            ttl = ttl or self.default_ttl

            # 캐시 메타데이터 추가
            cache_data = result.copy()
            cache_data["cached_at"] = datetime.now().isoformat()
            cache_data["cache_ttl"] = ttl
            cache_data["query_hash"] = cache_key

            # 데이터 압축 및 저장
            compressed_data = self._compress_data(cache_data)

            success = self.redis_client.setex(
                cache_key,
                ttl,
                compressed_data
            )

            if success:
                self.stats["cache_sets"] += 1
                logger.info(f"Cache SET for query: {query[:50]}... (TTL: {ttl}s)")
                return True

            return False

        except Exception as e:
            self.stats["cache_errors"] += 1
            logger.error(f"Cache storage error: {e}")
            return False

    def invalidate_cache(self, query: str, params: Dict[str, Any] = None) -> bool:
        """특정 쿼리의 캐시 무효화"""
        if not self.redis_client:
            return False

        try:
            cache_key = self._make_cache_key(query, params)
            result = self.redis_client.delete(cache_key)

            if result:
                logger.info(f"Cache invalidated for query: {query[:50]}...")
                return True

            return False

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            return False

    def clear_all_cache(self) -> int:
        """모든 SANZERO 캐시 삭제"""
        if not self.redis_client:
            return 0

        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)

            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계 조회"""
        hit_rate = 0
        if self.stats["total_requests"] > 0:
            hit_rate = (self.stats["cache_hits"] / self.stats["total_requests"]) * 100

        stats = self.stats.copy()
        stats.update({
            "hit_rate_percent": round(hit_rate, 2),
            "redis_available": self.redis_client is not None,
            "compression_enabled": self.enable_compression,
            "default_ttl": self.default_ttl
        })

        if self.redis_client:
            try:
                # Redis 서버 정보
                info = self.redis_client.info()
                stats["redis_info"] = {
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "uptime_in_seconds": info.get("uptime_in_seconds", 0)
                }
            except Exception as e:
                logger.warning(f"Failed to get Redis info: {e}")

        return stats

    def health_check(self) -> Dict[str, Any]:
        """캐시 시스템 헬스체크"""
        health = {
            "status": "healthy",
            "redis_available": False,
            "connection_test": False,
            "error": None
        }

        if not REDIS_AVAILABLE:
            health.update({
                "status": "unavailable",
                "error": "Redis module not installed"
            })
            return health

        if not self.redis_client:
            health.update({
                "status": "disconnected",
                "error": "Redis client not initialized"
            })
            return health

        try:
            # 연결 테스트
            self.redis_client.ping()
            health["redis_available"] = True
            health["connection_test"] = True

            # 간단한 쓰기/읽기 테스트
            test_key = f"{self.key_prefix}health_test"
            test_value = f"test_{int(time.time())}"

            self.redis_client.setex(test_key, 10, test_value)
            retrieved = self.redis_client.get(test_key)

            if retrieved == test_value:
                health["status"] = "healthy"
            else:
                health["status"] = "degraded"
                health["error"] = "Read/write test failed"

            # 테스트 키 정리
            self.redis_client.delete(test_key)

        except Exception as e:
            health.update({
                "status": "unhealthy",
                "error": str(e)
            })

        return health

# 전역 캐시 인스턴스
_cache_instance: Optional[SearchCache] = None

def get_cache_instance(
    redis_url: str = "redis://localhost:6379/0",
    **kwargs
) -> SearchCache:
    """전역 캐시 인스턴스 반환"""
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = SearchCache(redis_url=redis_url, **kwargs)

    return _cache_instance

def init_cache(redis_url: str = "redis://localhost:6379/0", **kwargs):
    """캐시 초기화 (앱 시작 시 호출)"""
    global _cache_instance
    _cache_instance = SearchCache(redis_url=redis_url, **kwargs)

    health = _cache_instance.health_check()
    if health["status"] == "healthy":
        logger.info("Cache system initialized successfully")
    else:
        logger.warning(f"Cache system initialization issues: {health['error']}")

    return _cache_instance

# 편의 함수들
async def cache_search_result(
    query: str,
    result: Dict[str, Any],
    params: Dict[str, Any] = None,
    ttl: int = 3600
) -> bool:
    """검색 결과 캐싱"""
    cache = get_cache_instance()
    return await cache.set_cached_result(query, params or {}, result, ttl)

async def get_cached_search_result(
    query: str,
    params: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """캐시된 검색 결과 조회"""
    cache = get_cache_instance()
    return await cache.get_cached_result(query, params or {})

def get_cache_statistics() -> Dict[str, Any]:
    """캐시 통계 조회"""
    cache = get_cache_instance()
    return cache.get_cache_stats()

def clear_cache() -> int:
    """모든 캐시 삭제"""
    cache = get_cache_instance()
    return cache.clear_all_cache()