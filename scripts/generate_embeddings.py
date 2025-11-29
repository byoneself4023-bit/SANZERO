#!/usr/bin/env python3
"""
판례 임베딩 생성 스크립트
기존 precedents 테이블의 판례들에 대해 SBERT 임베딩을 생성하고 업데이트합니다.
"""

import sys
import os
import asyncio
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sentence_transformers import SentenceTransformer
from app.utils.database import supabase
from app.utils.security import security
from loguru import logger

class EmbeddingGenerator:
    """판례 임베딩 생성기"""

    def __init__(self):
        # SBERT 모델 초기화 (384차원)
        logger.info("SBERT 모델 로딩 중...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("SBERT 모델 로딩 완료")

    async def get_precedents_without_embeddings(self):
        """임베딩이 없는 판례들 조회"""
        try:
            response = await asyncio.to_thread(
                lambda: supabase.table("precedents")
                .select("id, title, summary, full_text")
                .is_("embedding", "null")
                .eq("is_active", True)
                .execute()
            )

            logger.info(f"임베딩이 없는 판례 {len(response.data)}건 발견")
            return response.data

        except Exception as e:
            logger.error(f"판례 조회 실패: {e}")
            return []

    def generate_embedding(self, text: str) -> list:
        """텍스트를 벡터로 임베딩"""
        try:
            # 텍스트 전처리
            cleaned_text = security.sanitize_text(text)
            if not cleaned_text.strip():
                return None

            # 임베딩 생성
            embedding = self.embedding_model.encode(cleaned_text)
            return embedding.tolist()

        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            return None

    async def update_precedent_embedding(self, precedent_id: str, embedding: list):
        """판례의 임베딩 업데이트"""
        try:
            response = await asyncio.to_thread(
                lambda: supabase.table("precedents")
                .update({"embedding": embedding})
                .eq("id", precedent_id)
                .execute()
            )

            if response.data:
                logger.info(f"판례 {precedent_id} 임베딩 업데이트 완료")
                return True
            else:
                logger.error(f"판례 {precedent_id} 임베딩 업데이트 실패")
                return False

        except Exception as e:
            logger.error(f"임베딩 업데이트 실패 {precedent_id}: {e}")
            return False

    async def process_all_precedents(self):
        """모든 판례에 대해 임베딩 생성 및 업데이트"""
        logger.info("=== 판례 임베딩 생성 시작 ===")

        # 임베딩이 없는 판례들 조회
        precedents = await self.get_precedents_without_embeddings()

        if not precedents:
            logger.info("처리할 판례가 없습니다.")
            return

        success_count = 0
        failed_count = 0

        for i, precedent in enumerate(precedents, 1):
            precedent_id = precedent["id"]
            title = precedent.get("title", "")
            summary = precedent.get("summary", "")
            full_text = precedent.get("full_text", "")

            logger.info(f"[{i}/{len(precedents)}] 처리 중: {precedent_id}")

            # 임베딩할 텍스트 준비 (제목 + 요약 + 전문의 일부)
            embedding_text = f"{title}\n{summary}"
            if full_text:
                # 전문이 너무 길면 앞부분만 사용 (토큰 제한 고려)
                embedding_text += f"\n{full_text[:500]}"

            # 임베딩 생성
            embedding = self.generate_embedding(embedding_text)

            if embedding:
                # 데이터베이스 업데이트
                success = await self.update_precedent_embedding(precedent_id, embedding)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            else:
                logger.error(f"판례 {precedent_id} 임베딩 생성 실패")
                failed_count += 1

        logger.info("=== 판례 임베딩 생성 완료 ===")
        logger.info(f"성공: {success_count}건, 실패: {failed_count}건")

        # 최종 확인
        await self.verify_embeddings()

    async def verify_embeddings(self):
        """임베딩 생성 결과 확인"""
        try:
            response = await asyncio.to_thread(
                lambda: supabase.table("precedents")
                .select("id, embedding")
                .eq("is_active", True)
                .execute()
            )

            total_count = len(response.data)
            with_embeddings = sum(1 for p in response.data if p.get("embedding"))

            logger.info(f"임베딩 생성 결과:")
            logger.info(f"  전체 판례: {total_count}건")
            logger.info(f"  임베딩 있음: {with_embeddings}건")
            logger.info(f"  임베딩 없음: {total_count - with_embeddings}건")

            if with_embeddings == total_count:
                logger.info("✅ 모든 판례에 임베딩이 생성되었습니다!")
            else:
                logger.warning(f"⚠️ {total_count - with_embeddings}건의 판례에 임베딩이 없습니다.")

        except Exception as e:
            logger.error(f"임베딩 검증 실패: {e}")


async def main():
    """메인 실행 함수"""
    try:
        generator = EmbeddingGenerator()
        await generator.process_all_precedents()
    except Exception as e:
        logger.error(f"스크립트 실행 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 로거 설정
    logger.add(
        "logs/embedding_generation.log",
        rotation="1 MB",
        retention="7 days",
        level="INFO"
    )

    logger.info("판례 임베딩 생성 스크립트 시작")

    # 비동기 실행
    asyncio.run(main())