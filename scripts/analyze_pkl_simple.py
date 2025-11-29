#!/usr/bin/env python3
"""
searcher_model.pkl 파일 간단 분석 스크립트
파일 구조만 안전하게 확인
"""

import zlib
import sys
from pathlib import Path

def safe_analyze():
    """안전한 방법으로 pkl 파일 기본 정보 확인"""

    pkl_path = Path(__file__).parent.parent / "app" / "searcher_model.pkl"

    print("🔍 searcher_model.pkl 기본 정보 확인\n")

    if not pkl_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {pkl_path}")
        return

    # 1. 파일 기본 정보
    file_size_mb = pkl_path.stat().st_size / (1024 * 1024)
    print(f"📁 파일 경로: {pkl_path}")
    print(f"📊 파일 크기: {file_size_mb:.2f} MB")

    # 2. 압축 해제 시도
    try:
        print("\n📦 zlib 압축 해제 테스트...")
        with open(pkl_path, 'rb') as f:
            compressed_data = f.read()

        decompressed_data = zlib.decompress(compressed_data)
        decompressed_size_mb = len(decompressed_data) / (1024 * 1024)
        print(f"✅ 압축 해제 성공!")
        print(f"📈 압축 해제 후 크기: {decompressed_size_mb:.2f} MB")
        print(f"📊 압축율: {(1 - file_size_mb / decompressed_size_mb) * 100:.1f}%")

        # 3. 데이터 타입 힌트 확인
        print(f"\n🔍 압축 해제된 데이터 정보:")
        print(f"  타입: {type(decompressed_data)}")
        print(f"  크기: {len(decompressed_data):,} bytes")

        # 첫 100바이트 확인 (pickle 헤더 정보)
        header = decompressed_data[:100]
        print(f"  헤더 (첫 50바이트): {header[:50]}")

        # 텍스트 내용 중 키워드 검색
        text_content = decompressed_data.decode('latin-1', errors='ignore')
        keywords = ['dataframe', 'DataFrame', 'vectorizer', 'tfidf', 'matrix', 'config']

        print(f"\n🔎 내용 키워드 검색:")
        for keyword in keywords:
            count = text_content.lower().count(keyword.lower())
            if count > 0:
                print(f"  '{keyword}': {count}회 발견")

    except Exception as e:
        print(f"❌ 분석 중 오류: {e}")

    # 4. Test_casePedia.ipynb 파일도 확인
    ipynb_path = pkl_path.parent / "Test_casePedia.ipynb"
    if ipynb_path.exists():
        print(f"\n📓 Test_casePedia.ipynb 발견!")
        print(f"  위치: {ipynb_path}")
        print(f"  크기: {ipynb_path.stat().st_size / (1024 * 1024):.2f} MB")
    else:
        print(f"\n❌ Test_casePedia.ipynb 파일을 찾을 수 없습니다.")

    print(f"\n🎯 결론:")
    print(f"  - pkl 파일은 zlib로 압축된 pickle 데이터입니다.")
    print(f"  - 압축 해제 후 크기가 {decompressed_size_mb:.0f}MB로, 대용량 데이터를 포함하고 있습니다.")
    print(f"  - Test_casePedia.ipynb의 WorkInjuryCaseSearcher 클래스를 참조하여")
    print(f"    이 pkl 파일을 안전하게 로드하는 방법을 구현해야 합니다.")

if __name__ == "__main__":
    safe_analyze()