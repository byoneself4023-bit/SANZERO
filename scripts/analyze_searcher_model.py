#!/usr/bin/env python3
"""
searcher_model.pkl 파일 구조 상세 분석 스크립트
AI 판례 분석 시스템 통합을 위한 파일 내용 분석
"""

import pickle
import pandas as pd
import numpy as np
import sys
import os
import zlib
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def analyze_searcher_model():
    """searcher_model.pkl 파일의 구조와 내용을 상세히 분석합니다."""

    pkl_path = project_root / "app" / "searcher_model.pkl"

    print("🔍 searcher_model.pkl 파일 분석을 시작합니다...\n")

    # 1. 파일 존재 여부 및 크기 확인
    if not pkl_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {pkl_path}")
        return

    file_size_mb = pkl_path.stat().st_size / (1024 * 1024)
    print(f"📁 파일 경로: {pkl_path}")
    print(f"📊 파일 크기: {file_size_mb:.2f} MB\n")

    try:
        # 2. 압축된 pkl 파일 로드
        print("⏳ 압축된 pkl 파일을 로드 중...")
        with open(pkl_path, 'rb') as f:
            compressed_data = f.read()

        print("📦 zlib 압축 해제 중...")
        decompressed_data = zlib.decompress(compressed_data)

        print("🔓 pickle 데이터 로드 중...")
        # DataFrame 모듈 의존성 문제 해결
        import pandas as pd
        sys.modules['DataFrame'] = pd.DataFrame

        model_data = pickle.loads(decompressed_data)

        print("✅ pkl 파일 로드 완료!\n")

        # 3. 최상위 구조 분석
        print("📋 최상위 키 구조:")
        if isinstance(model_data, dict):
            for key in model_data.keys():
                print(f"  - {key}: {type(model_data[key])}")
        else:
            print(f"  타입: {type(model_data)}")
        print()

        # 4. 각 구성요소 상세 분석
        if isinstance(model_data, dict):

            # DataFrame 분석
            if 'df' in model_data:
                analyze_dataframe(model_data['df'])

            # Vectorizer 분석
            if 'vectorizer' in model_data:
                analyze_vectorizer(model_data['vectorizer'])

            # TF-IDF Matrix 분석
            if 'tfidf_matrix' in model_data:
                analyze_tfidf_matrix(model_data['tfidf_matrix'])

            # Config 분석
            if 'config' in model_data:
                analyze_config(model_data['config'])

            # 기타 키들 분석
            for key, value in model_data.items():
                if key not in ['df', 'vectorizer', 'tfidf_matrix', 'config']:
                    print(f"🔧 추가 구성요소 '{key}':")
                    print(f"  타입: {type(value)}")
                    if hasattr(value, 'shape'):
                        print(f"  형태: {value.shape}")
                    print()

        # 5. 메모리 사용량 분석
        analyze_memory_usage(model_data)

        # 6. 샘플 데이터 확인
        if isinstance(model_data, dict) and 'df' in model_data:
            analyze_sample_data(model_data['df'])

        print("🎉 분석 완료!")

    except Exception as e:
        print(f"❌ 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def analyze_dataframe(df):
    """DataFrame 구조 분석"""
    print("📊 DataFrame 분석:")
    print(f"  행 수: {len(df):,}개")
    print(f"  열 수: {len(df.columns)}개")
    print(f"  컬럼: {list(df.columns)}")
    print(f"  메모리 사용량: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")

    # 각 컬럼의 데이터 타입과 샘플 확인
    print("\n  📋 컬럼 상세 정보:")
    for col in df.columns:
        print(f"    {col}:")
        print(f"      타입: {df[col].dtype}")
        print(f"      결측값: {df[col].isnull().sum()}개")
        if not df[col].empty:
            sample_val = str(df[col].iloc[0])
            if len(sample_val) > 100:
                sample_val = sample_val[:100] + "..."
            print(f"      샘플: {sample_val}")
    print()

def analyze_vectorizer(vectorizer):
    """TF-IDF Vectorizer 분석"""
    print("🔤 TF-IDF Vectorizer 분석:")
    print(f"  타입: {type(vectorizer)}")

    if hasattr(vectorizer, 'vocabulary_'):
        vocab_size = len(vectorizer.vocabulary_)
        print(f"  어휘 크기: {vocab_size:,}개")

    # Vectorizer 설정 확인
    if hasattr(vectorizer, 'get_params'):
        params = vectorizer.get_params()
        print(f"  주요 설정:")
        for key, value in params.items():
            if key in ['max_features', 'ngram_range', 'min_df', 'max_df', 'sublinear_tf', 'use_idf']:
                print(f"    {key}: {value}")

    # 상위 빈도 단어들 확인 (가능한 경우)
    if hasattr(vectorizer, 'vocabulary_'):
        vocab_items = list(vectorizer.vocabulary_.items())
        if vocab_items:
            print(f"  어휘 샘플 (처음 10개):")
            for word, idx in sorted(vocab_items, key=lambda x: x[1])[:10]:
                print(f"    '{word}' -> {idx}")
    print()

def analyze_tfidf_matrix(tfidf_matrix):
    """TF-IDF 매트릭스 분석"""
    print("📈 TF-IDF 매트릭스 분석:")
    print(f"  타입: {type(tfidf_matrix)}")
    print(f"  형태: {tfidf_matrix.shape}")
    print(f"  데이터 타입: {tfidf_matrix.dtype}")

    if hasattr(tfidf_matrix, 'nnz'):
        total_elements = np.prod(tfidf_matrix.shape)
        sparsity = (total_elements - tfidf_matrix.nnz) / total_elements * 100
        print(f"  희소성: {sparsity:.2f}% (0이 아닌 값: {tfidf_matrix.nnz:,}개)")

    # 메모리 사용량 추정
    if hasattr(tfidf_matrix, 'data'):
        memory_mb = (tfidf_matrix.data.nbytes + tfidf_matrix.indices.nbytes +
                    tfidf_matrix.indptr.nbytes) / 1024 / 1024
        print(f"  메모리 사용량: {memory_mb:.2f} MB")
    print()

def analyze_config(config):
    """Config 설정 분석"""
    print("⚙️ Config 설정 분석:")
    print(f"  타입: {type(config)}")

    if isinstance(config, dict):
        for key, value in config.items():
            print(f"  {key}:")
            if isinstance(value, (list, tuple)):
                print(f"    개수: {len(value)}개")
                if len(value) <= 10:
                    print(f"    내용: {value}")
                else:
                    print(f"    샘플: {value[:5]}... (총 {len(value)}개)")
            else:
                print(f"    값: {value}")
    print()

def analyze_memory_usage(model_data):
    """메모리 사용량 분석"""
    print("💾 메모리 사용량 분석:")

    if isinstance(model_data, dict):
        total_size = 0
        for key, value in model_data.items():
            size_mb = estimate_object_size(value)
            total_size += size_mb
            print(f"  {key}: {size_mb:.2f} MB")

        print(f"  📊 총 예상 메모리: {total_size:.2f} MB")
    print()

def estimate_object_size(obj):
    """객체의 대략적인 메모리 사용량 추정 (MB 단위)"""
    if isinstance(obj, pd.DataFrame):
        return obj.memory_usage(deep=True).sum() / 1024 / 1024
    elif hasattr(obj, 'data') and hasattr(obj, 'indices'):  # 희소 행렬
        return (obj.data.nbytes + obj.indices.nbytes + obj.indptr.nbytes) / 1024 / 1024
    elif isinstance(obj, (list, dict, str)):
        return sys.getsizeof(obj) / 1024 / 1024
    else:
        return sys.getsizeof(obj) / 1024 / 1024

def analyze_sample_data(df):
    """샘플 데이터 확인"""
    print("📝 샘플 데이터 (첫 3건):")

    if not df.empty:
        for i in range(min(3, len(df))):
            print(f"\n  📄 판례 {i+1}:")
            row = df.iloc[i]
            for col in df.columns:
                value = str(row[col])
                if len(value) > 150:
                    value = value[:150] + "..."
                print(f"    {col}: {value}")
    print()

if __name__ == "__main__":
    analyze_searcher_model()