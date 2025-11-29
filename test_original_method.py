#!/usr/bin/env python3
"""
원본 Test_casePedia.ipynb 방식으로 pkl 파일 로딩 테스트
"""

import pickle
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
import zlib

# 프로젝트 루트 설정
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_original_loading():
    """원본 노트북과 동일한 방식으로 로딩 테스트"""

    pkl_path = project_root / "app" / "searcher_model.pkl"
    print(f"📁 모델 경로: {pkl_path}")
    print(f"📊 파일 존재: {pkl_path.exists()}")
    print(f"📏 파일 크기: {pkl_path.stat().st_size / 1024 / 1024:.2f} MB")

    try:
        print("\n⏳ 압축 해제 시도...")

        with open(pkl_path, 'rb') as f:
            compressed_data = f.read()

        print("📦 zlib 압축 해제...")
        decompressed_data = zlib.decompress(compressed_data)

        print(f"✅ 압축 해제 완료: {len(decompressed_data) / 1024 / 1024:.2f} MB")

        # 원본 노트북에서 사용한 방식 그대로 시도
        print("\n🔄 원본 방식 pickle 로드 시도...")

        # 환경 준비 - 노트북 환경과 동일하게
        import warnings
        warnings.filterwarnings('ignore')

        # 모듈 임포트
        import pandas as pd
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        # pickle 로드
        model_data = pickle.loads(decompressed_data)

        print("✅ pickle 로드 성공!")

        # 구성 요소 확인
        print(f"\n📋 모델 구성 요소:")
        for key, value in model_data.items():
            print(f"  - {key}: {type(value)}")
            if hasattr(value, 'shape'):
                print(f"    형태: {value.shape}")

        # DataFrame 상세 확인
        if 'df' in model_data:
            df = model_data['df']
            print(f"\n📊 DataFrame 정보:")
            print(f"  행 수: {len(df):,}")
            print(f"  열 수: {len(df.columns)}")
            print(f"  컬럼: {list(df.columns)}")

            # 샘플 데이터 확인
            print(f"\n📝 샘플 데이터:")
            for i in range(min(3, len(df))):
                row = df.iloc[i]
                print(f"  {i+1}. {row.name}:")
                for col in df.columns[:3]:  # 처음 3개 컬럼만
                    value = str(row[col])[:50]
                    print(f"     {col}: {value}...")

        # Vectorizer 확인
        if 'vectorizer' in model_data:
            vectorizer = model_data['vectorizer']
            print(f"\n🔤 Vectorizer 정보:")
            print(f"  타입: {type(vectorizer)}")
            if hasattr(vectorizer, 'vocabulary_'):
                print(f"  어휘 크기: {len(vectorizer.vocabulary_):,}")

        # TF-IDF Matrix 확인
        if 'tfidf_matrix' in model_data:
            matrix = model_data['tfidf_matrix']
            print(f"\n📈 TF-IDF Matrix 정보:")
            print(f"  타입: {type(matrix)}")
            print(f"  형태: {matrix.shape}")

        return True

    except Exception as e:
        print(f"❌ 로딩 실패: {e}")
        import traceback
        print("상세 오류:")
        traceback.print_exc()
        return False

def test_simple_search():
    """간단한 검색 테스트"""
    print("\n🔍 간단한 검색 기능 테스트")

    pkl_path = project_root / "app" / "searcher_model.pkl"

    try:
        # 로딩
        with open(pkl_path, 'rb') as f:
            compressed_data = f.read()

        decompressed_data = zlib.decompress(compressed_data)
        model_data = pickle.loads(decompressed_data)

        df = model_data['df']
        vectorizer = model_data['vectorizer']
        tfidf_matrix = model_data['tfidf_matrix']

        # 테스트 쿼리
        query = "손가락 절단"
        print(f"📝 검색어: '{query}'")

        # TF-IDF 벡터화
        query_vector = vectorizer.transform([query])

        # 유사도 계산
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()

        # 상위 결과
        top_indices = np.argsort(similarities)[::-1][:5]

        print(f"🎯 검색 결과:")
        for i, idx in enumerate(top_indices, 1):
            similarity = similarities[idx]
            if similarity > 0:
                case_info = df.iloc[idx]
                print(f"  {i}. 유사도: {similarity:.3f}")

                # 컬럼에 따라 제목 추출
                title_cols = ['title', '사건명', '판결제목']
                title = "Unknown"
                for col in title_cols:
                    if col in case_info:
                        title = str(case_info[col])[:50]
                        break

                print(f"     제목: {title}...")

        return True

    except Exception as e:
        print(f"❌ 검색 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("🚀 원본 방식 pkl 로딩 테스트\n")

    # 1. 원본 방식 로딩 테스트
    success = test_original_loading()

    if success:
        # 2. 간단한 검색 테스트
        test_simple_search()

    print("\n🎉 테스트 완료!")