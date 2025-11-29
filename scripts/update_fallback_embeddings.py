#!/usr/bin/env python3
"""
판례 Fallback 임베딩 업데이트 스크립트
기존 판례들에 대해 fallback 임베딩을 생성하고 업데이트합니다.
"""

import sys
import os
import asyncio
import hashlib
import math
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.utils.database import supabase
from app.utils.security import security
from loguru import logger

def generate_fallback_embedding(text: str) -> list:
    """Fallback 임베딩 생성 (ML 라이브러리 없이)"""
    try:
        # 텍스트 전처리
        cleaned_text = security.sanitize_text(text)
        if not cleaned_text.strip():
            return [0.0] * 1536

        # 간단한 특징 벡터 생성 (384차원)
        features = []

        # 1. 텍스트 길이 특징
        features.append(len(cleaned_text) / 1000.0)

        # 2. 해시 기반 특징 (안전한 방식)
        hash_obj = hashlib.md5(cleaned_text.encode())
        hash_bytes = hash_obj.digest()

        # 16바이트 해시에서 안전하게 특징 추출
        for i in range(min(16, len(hash_bytes))):
            features.append((hash_bytes[i] % 256) / 255.0)

        # 3. 키워드 기반 특징 (산재 관련)
        keywords = [
            '산업재해', '산재', '사고', '부상', '절단', '골절', '화상', '타박상',
            '제조업', '건설업', '서비스업', '기계', '안전', '보상금', '승인', '거부',
            '병원', '치료', '수술', '재활', '장해', '등급', '노무사', '상담',
            '프레스', '추락', '화학', '물류', '식당', '주방', '허리', '디스크'
        ]

        for keyword in keywords:
            features.append(1.0 if keyword in cleaned_text else 0.0)

        # 4. 나머지 차원을 0으로 안전하게 패딩
        target_dim = 1536  # OpenAI text-embedding-ada-002 차원
        current_len = len(features)

        # 간단한 패딩
        for i in range(target_dim - current_len):
            features.append(0.1 * (i % 10))  # 간단한 패턴

        # 정확히 1536차원으로 자르기
        result = features[:target_dim]

        # 차원 확인
        if len(result) != target_dim:
            logger.error(f"임베딩 차원 오류: {len(result)} != {target_dim}")
            return [0.0] * target_dim

        return result

    except Exception as e:
        logger.error(f"임베딩 생성 오류: {e}")
        return [0.0] * 1536

async def update_precedent_embeddings():
    """모든 판례에 대해 fallback 임베딩 생성 및 업데이트"""
    logger.info("=== 판례 Fallback 임베딩 업데이트 시작 ===")

    try:
        # 임베딩이 없는 판례들 조회
        response = await asyncio.to_thread(
            lambda: supabase.table("precedents")
            .select("id, title, summary")
            .is_("embedding", "null")
            .eq("is_active", True)
            .execute()
        )

        precedents = response.data
        if not precedents:
            logger.info("업데이트할 판례가 없습니다.")
            return

        logger.info(f"총 {len(precedents)}건의 판례를 처리합니다.")

        success_count = 0
        for i, precedent in enumerate(precedents, 1):
            precedent_id = precedent["id"]
            title = precedent.get("title", "")
            summary = precedent.get("summary", "")

            logger.info(f"[{i}/{len(precedents)}] 처리 중: {title[:50]}...")

            # 임베딩할 텍스트 준비 (제목 + 요약)
            embedding_text = f"{title}\n{summary}"

            # Fallback 임베딩 생성
            embedding = generate_fallback_embedding(embedding_text)

            if embedding and len(embedding) == 1536:
                # 데이터베이스 업데이트
                try:
                    update_response = await asyncio.to_thread(
                        lambda: supabase.table("precedents")
                        .update({"embedding": embedding})
                        .eq("id", precedent_id)
                        .execute()
                    )

                    if update_response.data:
                        logger.info(f"✅ 판례 {precedent_id} 임베딩 업데이트 완료")
                        success_count += 1
                    else:
                        logger.error(f"❌ 판례 {precedent_id} 업데이트 실패")

                except Exception as e:
                    logger.error(f"❌ 판례 {precedent_id} 업데이트 오류: {e}")
            else:
                logger.error(f"❌ 판례 {precedent_id} 임베딩 생성 실패")

        logger.info("=== 판례 임베딩 업데이트 완료 ===")
        logger.info(f"성공: {success_count}건 / 전체: {len(precedents)}건")

        # 최종 확인
        await verify_embeddings()

    except Exception as e:
        logger.error(f"스크립트 실행 오류: {e}")

async def verify_embeddings():
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

        logger.info(f"📊 임베딩 생성 결과:")
        logger.info(f"  전체 판례: {total_count}건")
        logger.info(f"  임베딩 있음: {with_embeddings}건")
        logger.info(f"  임베딩 없음: {total_count - with_embeddings}건")

        if with_embeddings == total_count:
            logger.info("🎉 모든 판례에 임베딩이 생성되었습니다!")
        else:
            logger.warning(f"⚠️ {total_count - with_embeddings}건의 판례에 임베딩이 없습니다.")

    except Exception as e:
        logger.error(f"임베딩 검증 실패: {e}")

async def main():
    """메인 실행 함수"""
    await update_precedent_embeddings()

if __name__ == "__main__":
    # 로거 설정
    logger.add(
        "logs/fallback_embedding_update.log",
        rotation="1 MB",
        retention="7 days",
        level="INFO"
    )

    logger.info("판례 Fallback 임베딩 업데이트 스크립트 시작")
    asyncio.run(main())