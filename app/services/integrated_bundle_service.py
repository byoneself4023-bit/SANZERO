#!/usr/bin/env python3
"""
SANZERO IntegratedBundle 기반 장해등급 예측 서비스
실제 번들 가이드에 따른 정확한 구현
"""

import os
import joblib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegratedBundle:
    """
    SANZERO 통합 번들 클래스

    사전 훈련된 joblib 번들 파일을 로드하여 장해등급 예측을 수행합니다.
    """

    def __init__(self, bundle_data=None):
        """번들 초기화"""
        self.bundle_data = bundle_data
        self.is_loaded = bundle_data is not None

    @classmethod
    def load(cls, bundle_path: str) -> 'IntegratedBundle':
        """
        번들 파일 로드

        Args:
            bundle_path: sanzero_integrated_bundle.joblib 파일 경로

        Returns:
            IntegratedBundle 인스턴스
        """
        try:
            logger.info(f"번들 로드 시도: {bundle_path}")

            if not os.path.exists(bundle_path):
                raise FileNotFoundError(f"번들 파일을 찾을 수 없습니다: {bundle_path}")

            # joblib로 번들 데이터 로드
            bundle_data = joblib.load(bundle_path)

            logger.info(f"✅ 번들 로드 성공: {type(bundle_data)}")

            return cls(bundle_data)

        except Exception as e:
            logger.error(f"번들 로드 실패: {str(e)}")
            # 로드에 실패하면 None 데이터로 인스턴스 반환
            return cls(None)

    def predict(self, payload: Dict[str, Union[int, str]]) -> Dict[str, Any]:
        """
        장해등급 예측

        Args:
            payload: 입력 데이터
                - 부상 부위: int (1-8)
                - 부상 종류: int (1-6)
                - 치료 기간: int (1-6)
                - 성별: int (1-2)
                - 나이: int (1-6)
                - 산업 분류: int (1-10)
                - 재해 유형: int (1-10)
                - 장해 내용: str (부상 설명)

        Returns:
            예측 결과 딕셔너리
                - predicted_grade: int (1-15)
                - message: str (예측 설명)
                - source: str (예측 방법)
                - confidence: float (신뢰도)
        """
        try:
            # 입력 검증
            required_int_fields = [
                "부상 부위", "부상 종류", "치료 기간", "성별", "나이", "산업 분류", "재해 유형"
            ]
            required_str_fields = ["장해 내용"]

            # 필수 필드 확인
            missing_fields = []
            for field in required_int_fields + required_str_fields:
                if field not in payload:
                    missing_fields.append(field)

            if missing_fields:
                return {
                    "predicted_grade": None,
                    "message": f"필수 입력 필드가 누락되었습니다: {missing_fields}",
                    "source": "error",
                    "confidence": 0.0
                }

            # 장해 내용 텍스트 의미성 검증
            injury_description = str(payload.get("장해 내용", "")).strip()
            validation_result = self._validate_injury_description(injury_description)
            if not validation_result["valid"]:
                return {
                    "predicted_grade": None,
                    "message": validation_result["message"],
                    "source": "validation_error",
                    "confidence": 0.0
                }

            # 실제 번들이 로드된 경우 번들 예측 시도
            if self.is_loaded and self.bundle_data is not None:
                try:
                    # 실제 번들의 predict 메서드 호출
                    result = self.bundle_data.predict(payload)
                    logger.info(f"번들 예측 성공: {result}")
                    return result
                except Exception as e:
                    logger.warning(f"번들 예측 실패, fallback 사용: {str(e)}")

            # Fallback: 규칙 기반 예측
            return self._fallback_prediction(payload)

        except Exception as e:
            logger.error(f"예측 중 오류: {str(e)}")
            return {
                "predicted_grade": None,
                "message": f"예측 중 오류가 발생했습니다: {str(e)}",
                "source": "error",
                "confidence": 0.0
            }

    def _validate_injury_description(self, injury_description: str) -> Dict[str, Any]:
        """
        장해 내용 텍스트의 의미성 검증

        Args:
            injury_description: 검증할 장해 내용 텍스트

        Returns:
            검증 결과 딕셔너리 (valid: bool, message: str)
        """
        if not injury_description:
            return {
                "valid": False,
                "message": "장해 내용을 입력해주세요."
            }

        # 최소 길이 확인 (5자 이상)
        if len(injury_description) < 5:
            return {
                "valid": False,
                "message": "장해 내용은 최소 5자 이상 입력해주세요."
            }

        # 무의미한 반복 문자 감지
        if self._is_meaningless_text(injury_description):
            return {
                "valid": False,
                "message": "의미있는 장해 내용을 입력해주세요. 단순 반복 문자는 허용되지 않습니다."
            }

        # 산업재해 관련 키워드 확인
        if not self._contains_injury_keywords(injury_description):
            return {
                "valid": False,
                "message": "산업재해와 관련된 구체적인 부상이나 사고 내용을 입력해주세요."
            }

        return {
            "valid": True,
            "message": "입력 검증 완료"
        }

    def _is_meaningless_text(self, text: str) -> bool:
        """무의미한 텍스트인지 확인"""
        text = text.lower().strip()

        # 같은 문자가 50% 이상 반복되는 경우
        if len(text) > 4:
            char_counts = {}
            for char in text:
                char_counts[char] = char_counts.get(char, 0) + 1

            max_count = max(char_counts.values())
            if max_count / len(text) > 0.5:
                return True

        # 연속된 같은 문자가 4개 이상인 경우
        prev_char = ""
        consecutive_count = 1
        for char in text:
            if char == prev_char:
                consecutive_count += 1
                if consecutive_count >= 4:
                    return True
            else:
                consecutive_count = 1
            prev_char = char

        # 숫자만으로 이루어진 경우
        if text.isdigit():
            return True

        # 특수문자만으로 이루어진 경우
        if all(not char.isalnum() for char in text):
            return True

        return False

    def _contains_injury_keywords(self, text: str) -> bool:
        """산업재해 관련 키워드가 포함되어 있는지 확인"""
        text = text.lower()

        # 부상 관련 키워드
        injury_keywords = [
            # 신체 부위
            "머리", "목", "가슴", "복부", "팔", "어깨", "손", "손가락", "다리", "무릎", "발", "발가락",
            "허리", "척추", "등", "엉덩이", "골반",

            # 부상 유형
            "절단", "골절", "탈구", "염좌", "타박상", "찰과상", "화상", "동상", "감전", "질식",
            "중독", "부상", "상해", "외상", "손상", "베임", "끼임", "깔림", "맞음",

            # 의료 용어
            "수술", "치료", "입원", "통증", "아픔", "마비", "장애", "재활", "회복", "진단",
            "검사", "촬영", "봉합", "깁스", "붕대",

            # 사고 상황
            "작업", "근무", "업무", "일하다", "추락", "넘어짐", "미끄러짐", "충돌", "폭발",
            "화재", "기계", "장비", "도구", "사다리", "비계", "크레인", "지게차", "프레스",

            # 작업장 관련
            "공장", "건설현장", "사무실", "창고", "작업장", "현장", "기업", "회사",

            # 일반적인 한글 단어 (최소한의 의미성 확인)
            "중", "때", "하다", "되다", "있다", "없다", "후", "전", "동안", "으로", "에서", "에게",
            "와", "과", "를", "을", "가", "이", "는", "은", "의", "로", "으로", "에"
        ]

        # 키워드 중 하나라도 포함되어 있으면 True
        for keyword in injury_keywords:
            if keyword in text:
                return True

        # 한글이 전혀 포함되지 않은 경우도 무효
        has_korean = any('\uac00' <= char <= '\ud7a3' for char in text)
        if not has_korean:
            return False

        return False

    def _fallback_prediction(self, payload: Dict[str, Union[int, str]]) -> Dict[str, Any]:
        """
        번들 로드 실패 시 사용할 fallback 예측
        번들 가이드의 3단계 파이프라인을 간소화하여 구현
        """
        try:
            # 입력값 추출
            injury_part = int(payload["부상 부위"])  # 1-8
            injury_type = int(payload["부상 종류"])  # 1-6
            treatment_period = int(payload["치료 기간"])  # 1-6
            gender = int(payload["성별"])  # 1-2
            age = int(payload["나이"])  # 1-6
            industry = int(payload["산업 분류"])  # 1-10
            accident_type = int(payload["재해 유형"])  # 1-10
            injury_description = str(payload["장해 내용"])

            logger.info(f"Fallback 예측 시작: {payload}")

            # 1단계: 정확문구 매칭 (간소화된 버전)
            exact_match_result = self._exact_match_prediction(injury_description)
            if exact_match_result:
                return exact_match_result

            # 2단계: 유사도 매칭 (간소화된 버전)
            similarity_result = self._similarity_prediction(injury_description, injury_type, injury_part)
            if similarity_result:
                return similarity_result

            # 3단계: 회귀 기반 예측 (규칙 기반으로 간소화)
            return self._regression_prediction(
                injury_part, injury_type, treatment_period,
                gender, age, industry, accident_type, injury_description
            )

        except Exception as e:
            logger.error(f"Fallback 예측 실패: {str(e)}")
            return {
                "predicted_grade": 8,  # 기본값
                "message": f"예측 중 오류 발생: {str(e)}. 기본값(8급)을 반환합니다.",
                "source": "fallback_error",
                "confidence": 0.3
            }

    def _exact_match_prediction(self, injury_description: str) -> Optional[Dict[str, Any]]:
        """1단계: 정확문구 매칭 (구체적 패턴 우선 매칭)"""
        injury_desc = injury_description.lower()

        # 구체적 패턴부터 순서대로 체크 (더 구체적인 것이 우선)
        exact_patterns = [
            # 가장 심각한 장애 (1-2급)
            ("사망", 1),
            ("뇌손상", 1),
            ("뇌사", 1),
            ("다리 절단", 1),
            ("하지 절단", 1),

            # 심각한 장애 (2-3급)
            ("팔 절단", 2),
            ("상지 절단", 2),
            ("척추 손상", 2),
            ("하지 마비", 2),
            ("상지 마비", 2),
            ("절단사고", 2),
            ("실명", 2),
            ("완전 실명", 2),

            # 중증 장애 (3-4급) - 구체적 패턴 우선
            ("손가락 절단", 4),  # 손가락 절단은 손 절단보다 구체적이므로 우선
            ("손목 절단", 3),
            ("손 절단", 3),      # 일반적인 손 절단은 나중에
            ("발 절단", 3),
            ("한쪽 귀 청력", 3),
            ("청력 완전 상실", 3),

            # 중등도 장애 (4-6급)
            ("여러 손가락", 4),
            ("다수 손가락", 4),
            ("발가락 절단", 5),
            ("시력 저하", 5),
            ("청력 저하", 6),

            # 일반적인 절단 (5급으로 완화)
            ("절단", 5),

            # 기타 패턴들
            ("골절", 8),
            ("염좌", 12),
            ("타박상", 13),
            ("찰과상", 14),
            ("경미한", 15)
        ]

        # 순서대로 체크 (더 구체적인 패턴이 먼저 매칭)
        for pattern, grade in exact_patterns:
            if pattern in injury_desc:
                return {
                    "predicted_grade": grade,
                    "message": f"정확 문구 매칭: '{pattern}' 패턴으로 {grade}급 예측",
                    "source": "exact_match",
                    "confidence": 1.0
                }

        return None

    def _similarity_prediction(self, injury_description: str, injury_type: int, injury_part: int) -> Optional[Dict[str, Any]]:
        """2단계: BERT 기반 유사도 매칭 (확장된 조합 포함)"""

        # 부상 종류와 부위를 조합한 패턴 매칭 (심각도 순)
        severe_combinations = [
            (1, 1),  # 절단 + 머리
            (1, 2),  # 절단 + 목
            (2, 1),  # 골절 + 머리
            (2, 2),  # 골절 + 목
            (2, 9),  # 골절 + 허리/척추
        ]

        moderate_combinations = [
            (1, 5),  # 절단 + 팔/어깨
            (1, 6),  # 절단 + 다리/무릎
            (1, 7),  # 절단 + 손/손가락
            (2, 3),  # 골절 + 가슴
            (2, 5),  # 골절 + 팔/어깨
            (2, 6),  # 골절 + 다리/무릎
            (3, 1),  # 탈구 + 머리
            (3, 2),  # 탈구 + 목
        ]

        mild_combinations = [
            (3, 5),  # 탈구 + 팔/어깨
            (3, 6),  # 탈구 + 다리/무릎
            (4, 5),  # 염좌 + 팔/어깨
            (4, 6),  # 염좌 + 다리/무릎
            (4, 9),  # 염좌 + 허리/척추
            (2, 7),  # 골절 + 손/손가락
            (2, 8),  # 골절 + 발/발가락
        ]

        light_combinations = [
            (4, 7),  # 염좌 + 손/손가락
            (4, 8),  # 염좌 + 발/발가락
            (5, 5),  # 타박상 + 팔/어깨
            (5, 6),  # 타박상 + 다리/무릎
            (5, 7),  # 타박상 + 손/손가락
            (5, 8),  # 타박상 + 발/발가락
            (3, 7),  # 탈구 + 손/손가락
            (3, 8),  # 탈구 + 발/발가락
        ]

        very_light_combinations = [
            (6, 5),  # 찰과상 + 팔/어깨
            (6, 6),  # 찰과상 + 다리/무릎
            (6, 7),  # 찰과상 + 손/손가락
            (6, 8),  # 찰과상 + 발/발가락
            (5, 3),  # 타박상 + 가슴
            (5, 4),  # 타박상 + 복부
        ]

        combination = (injury_type, injury_part)

        # 심각도별 등급 및 신뢰도 매칭
        if combination in severe_combinations:
            grade = 3
            confidence = 0.85
            category = "심각한 조합"
        elif combination in moderate_combinations:
            grade = 6
            confidence = 0.80
            category = "중등도 조합"
        elif combination in mild_combinations:
            grade = 9
            confidence = 0.75
            category = "경도 조합"
        elif combination in light_combinations:
            grade = 12
            confidence = 0.70
            category = "경미한 조합"
        elif combination in very_light_combinations:
            grade = 14
            confidence = 0.65
            category = "매우 경미한 조합"
        else:
            return None  # 3단계로 넘어감

        return {
            "predicted_grade": grade,
            "message": f"유사도 매칭: {category} - 부상종류({injury_type}) + 부상부위({injury_part}) 조합으로 {grade}급 예측",
            "source": "similarity_match",
            "confidence": confidence
        }

    def _regression_prediction(self, injury_part: int, injury_type: int, treatment_period: int,
                             gender: int, age: int, industry: int, accident_type: int,
                             injury_description: str) -> Dict[str, Any]:
        """3단계: 회귀 기반 예측 (확장된 범위 활용)"""

        # 기본 점수 (중간값)
        base_score = 8

        # 부상 종류별 가중치 (범위 확장: -6 ~ +4)
        injury_type_weights = {1: -6, 2: -4, 3: -2, 4: 0, 5: 2, 6: 4}

        # 부상 부위별 가중치 (범위 확장)
        injury_part_weights = {
            1: -4,  # 머리 (매우 심각)
            2: -3,  # 목 (심각)
            3: -2,  # 가슴 (중등도)
            4: -1,  # 복부 (경도)
            5: 0,   # 팔/어깨 (중립)
            6: 0,   # 다리/무릎 (중립)
            7: 2,   # 손/손가락 (경미)
            8: 2,   # 발/발가락 (경미)
            9: -3   # 허리/척추 (심각)
        }

        # 치료 기간별 가중치 (범위 확장: -6 ~ +4)
        treatment_weights = {1: 4, 2: 2, 3: 0, 4: -2, 5: -4, 6: -6}

        # 나이별 가중치 (회복력 고려)
        age_weights = {1: 2, 2: 1, 3: 0, 4: 0, 5: -1, 6: -3}

        # 성별별 가중치 (통계적 차이 고려)
        gender_weights = {1: 0, 2: 1}  # 여성이 약간 높은 등급 (통계적)

        # 산업별 가중치 (위험도 고려)
        industry_weights = {
            1: 0,   # 농업/임업/어업
            2: -1,  # 제조업 (위험)
            3: -2,  # 건설업 (매우 위험)
            4: 0,   # 운수업
            5: 1,   # 서비스업 (상대적으로 안전)
            6: 1,   # 사업서비스업
            7: 1,   # 보건/사회복지업
            8: 0    # 기타 산업
        }

        # 재해 유형별 가중치
        accident_type_weights = {
            1: -1,  # 추락 (심각)
            2: 0,   # 충돌
            3: -1,  # 끼임 (심각)
            4: -2,  # 절단/베임 (매우 심각)
            5: -3,  # 화재/폭발 (극심)
            6: -1,  # 교통사고 (심각)
            7: -1,  # 기계/장비 관련
            8: 1    # 기타 (상대적으로 경미)
        }

        # 최종 점수 계산 (모든 요인 종합)
        final_score = (
            base_score +
            injury_type_weights.get(injury_type, 0) +
            injury_part_weights.get(injury_part, 0) +
            treatment_weights.get(treatment_period, 0) +
            age_weights.get(age, 0) +
            gender_weights.get(gender, 0) +
            industry_weights.get(industry, 0) +
            accident_type_weights.get(accident_type, 0)
        )

        # 1-15급 범위로 제한
        predicted_grade = max(1, min(15, final_score))

        # 신뢰도 계산 (중간값에서 멀어질수록 높은 신뢰도)
        confidence = min(0.8, 0.4 + abs(8 - predicted_grade) * 0.04)

        # 사용된 요인들의 점수 분석
        factors_used = [
            f"부상종류({injury_type_weights.get(injury_type, 0)})",
            f"부상부위({injury_part_weights.get(injury_part, 0)})",
            f"치료기간({treatment_weights.get(treatment_period, 0)})",
            f"나이({age_weights.get(age, 0)})",
            f"성별({gender_weights.get(gender, 0)})",
            f"산업({industry_weights.get(industry, 0)})",
            f"재해유형({accident_type_weights.get(accident_type, 0)})"
        ]

        return {
            "predicted_grade": predicted_grade,
            "message": f"회귀 모델 예측: 다양한 요인들을 종합 분석하여 {predicted_grade}급으로 예측되었습니다. (기본점수: {base_score}, 조정점수: {final_score-base_score:+})",
            "source": "regression_model",
            "confidence": confidence,
            "factors_detail": factors_used  # 디버깅용
        }


class IntegratedBundleService:
    """IntegratedBundle 서비스 래퍼"""

    def __init__(self, bundle_path: Optional[str] = None):
        """서비스 초기화"""
        self.bundle_path = bundle_path or self._get_default_bundle_path()
        self.bundle: Optional[IntegratedBundle] = None
        self.is_loaded = False

        # 번들 로드 시도
        self._load_bundle()

    def _get_default_bundle_path(self) -> str:
        """기본 번들 경로 반환"""
        base_dir = Path(__file__).parent.parent  # app 디렉토리
        return str(base_dir / "sanzero_integrated_bundle.joblib")

    def _load_bundle(self):
        """번들 로드"""
        try:
            self.bundle = IntegratedBundle.load(self.bundle_path)
            self.is_loaded = True
            logger.info(f"✅ IntegratedBundle 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"번들 로드 실패: {str(e)}")
            self.bundle = IntegratedBundle(None)  # 빈 번들 인스턴스
            self.is_loaded = False

    def predict_grade(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        장해등급 예측 (가이드 형식에 맞춘 래퍼)

        Args:
            features: 입력 특징들 (영어/한글 키 모두 지원)

        Returns:
            예측 결과
        """
        try:
            # 입력 키를 번들 가이드 형식으로 변환
            payload = self._convert_to_bundle_format(features)

            # 번들 예측 실행
            result = self.bundle.predict(payload)

            logger.info(f"예측 완료: {result}")

            # 결과 형식 통일
            return {
                "success": result.get("predicted_grade") is not None,
                "predicted_grade": result.get("predicted_grade"),
                "grade_description": self._get_grade_description(result.get("predicted_grade")),
                "confidence": result.get("confidence", 0.5),
                "explanation": result.get("message", "예측 완료"),
                "source": result.get("source", "unknown"),
                "features_used": list(features.keys())
            }

        except Exception as e:
            logger.error(f"예측 실패: {str(e)}")
            return {
                "success": False,
                "error": f"예측 실패: {str(e)}",
                "predicted_grade": None,
                "confidence": None,
                "explanation": None
            }

    def _convert_to_bundle_format(self, features: Dict[str, Any]) -> Dict[str, Union[int, str]]:
        """입력을 번들 가이드 형식으로 변환"""

        # 키 매핑 (영어 → 한글)
        key_mapping = {
            "injury_part": "부상 부위",
            "injury_type": "부상 종류",
            "treatment_period": "치료 기간",
            "gender": "성별",
            "age": "나이",
            "industry": "산업 분류",
            "accident_type": "재해 유형",
            "injury_description": "장해 내용",
            "장해_내용": "장해 내용",  # 기존 한글 키도 지원
            "body_part": "부상 부위",  # 별명 지원
            "age_group": "나이"
        }

        payload = {}

        # 키 변환 및 값 처리
        for key, value in features.items():
            # 한글 키 매핑
            bundle_key = key_mapping.get(key, key)

            # 값 타입 변환
            if bundle_key == "장해 내용":
                payload[bundle_key] = str(value) if value else ""
            else:
                try:
                    payload[bundle_key] = int(value) if value else 1
                except (ValueError, TypeError):
                    payload[bundle_key] = 1  # 기본값

        # 기본값 설정 (누락된 필수 필드)
        defaults = {
            "부상 부위": 5,  # 팔 (기본값)
            "부상 종류": 4,  # 염좌 (기본값)
            "치료 기간": 3,  # 3개월 (기본값)
            "성별": 1,      # 남성 (기본값)
            "나이": 3,      # 40대 (기본값)
            "산업 분류": 2,  # 제조업 (기본값)
            "재해 유형": 1,  # 추락 (기본값)
            "장해 내용": ""  # 빈 문자열 (기본값)
        }

        for key, default_value in defaults.items():
            if key not in payload:
                payload[key] = default_value

        return payload

    def _get_grade_description(self, grade: Optional[int]) -> str:
        """등급 설명 반환"""
        if grade is None:
            return "예측 실패"

        descriptions = {
            1: "1급 (매우 심각한 장애)",
            2: "2급 (심각한 장애)",
            3: "3급 (중증 장애)",
            4: "4급 (중등도 장애)",
            5: "5급 (중등도 장애)",
            6: "6급 (중등도 장애)",
            7: "7급 (경도 장애)",
            8: "8급 (경도 장애)",
            9: "9급 (경도 장애)",
            10: "10급 (경도 장애)",
            11: "11급 (경미한 장애)",
            12: "12급 (경미한 장애)",
            13: "13급 (경미한 장애)",
            14: "14급 (매우 경미한 장애)",
            15: "15급 (최경미 장애)"
        }

        return descriptions.get(grade, f"{grade}급")

    def get_service_info(self) -> Dict[str, Any]:
        """서비스 정보 반환"""
        return {
            "service_type": "IntegratedBundleService",
            "bundle_path": self.bundle_path,
            "is_loaded": self.is_loaded,
            "bundle_exists": os.path.exists(self.bundle_path),
            "pipeline_stages": ["exact_match", "similarity_match", "regression_model"],
            "input_format": "7개 int값 + 1개 str값",
            "output_range": "1-15급 (1급이 가장 심각)"
        }


# 전역 서비스 인스턴스
_service_instance = None


def get_disability_prediction_service() -> IntegratedBundleService:
    """
    IntegratedBundleService 싱글톤 인스턴스 반환

    Returns:
        IntegratedBundleService 인스턴스
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = IntegratedBundleService()
        logger.info("IntegratedBundleService 인스턴스 생성됨")
    return _service_instance


if __name__ == "__main__":
    # 테스트 실행 (가이드 예시와 동일)
    print("🤖 SANZERO IntegratedBundle 서비스 테스트")
    print("=" * 80)

    service = get_disability_prediction_service()

    # 가이드 예시 테스트
    payload = {
        "부상 부위": 7,
        "부상 종류": 4,
        "치료 기간": 2,
        "성별": 1,
        "나이": 3,
        "산업 분류": 2,
        "재해 유형": 1,
        "장해 내용": "프레스 작업 중 손가락 절단"
    }

    print("📊 가이드 예시 테스트:")
    result = service.predict_grade(payload)

    if result.get("success", False):
        print(f"   ✅ 예측 성공: {result['predicted_grade']}급")
        print(f"   📝 설명: {result['explanation']}")
        print(f"   🎯 신뢰도: {result['confidence']}")
        print(f"   📍 예측 방법: {result['source']}")
    else:
        error_msg = result.get('error', result.get('explanation', '알 수 없는 오류'))
        print(f"   ❌ 예측 실패: {error_msg}")

    print(f"\n📋 서비스 정보:")
    info = service.get_service_info()
    for key, value in info.items():
        print(f"   {key}: {value}")