"""
산재 보상금 계산기 서비스

2025년 기준 산재 보상금 계산 로직을 제공합니다.
- 휴업급여 (평균임금의 70%)
- 상병보상연금 (제1급 기준 329일)
- 장해급여 (최저/최고 보상기준 적용)
- 유족급여 (기본 47% + 가산)
- 장례비 (평균임금 × 120일)
"""

from datetime import date, datetime, timezone
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SaturdayWorkType(Enum):
    """토요일 근무 유형"""
    FULL_PAY_8H = "full_8h"      # 토요일 유급 8시간
    HALF_PAY_4H = "half_4h"      # 토요일 유급 4시간
    NO_PAY = "no_pay"            # 토요일 무급


@dataclass
class CompensationStandards:
    """2025년 산재 보상 기준 금액"""

    # 2025년 기준 최저/최고 보상기준금액 (일급 기준)
    MIN_DAILY_AMOUNT: int = 87500    # 최저 보상기준 (일급)
    MAX_DAILY_AMOUNT: int = 350000   # 최고 보상기준 (일급)

    # 최저임금 (2025년 기준)
    MIN_WAGE_HOURLY: int = 10950     # 시간당 최저임금
    MIN_WAGE_DAILY: int = 87600      # 일급 최저임금 (8시간)
    MIN_WAGE_MONTHLY: int = 2289720  # 월급 최저임금 (209시간 기준)

    # 유족급여 관련 기준
    SURVIVOR_BASE_RATE: float = 0.47  # 기본 47%
    SURVIVOR_ADDITIONAL_RATE: float = 0.05  # 추가 가산 5% (유족 1명당)

    # 통상임금 계산 기준 (월 소정근로시간)
    MONTHLY_HOURS_FULL_SATURDAY: int = 243    # 토요일 유급 8시간
    MONTHLY_HOURS_HALF_SATURDAY: int = 226    # 토요일 유급 4시간
    MONTHLY_HOURS_NO_SATURDAY: int = 209      # 토요일 무급

    # 기본 계산 상수
    WEEKS_PER_MONTH: float = 4.345   # 월 평균 주수
    REGULAR_WORK_HOURS: int = 40     # 주 정규근로시간
    DAILY_WORK_HOURS: int = 8        # 일 근로시간


class CompensationCalculatorService:
    """산재 보상금 계산 서비스"""

    @staticmethod
    def calculate_regular_wage(
        method: str,
        amount: int,
        saturday_type: SaturdayWorkType = SaturdayWorkType.NO_PAY
    ) -> Dict[str, Any]:
        """
        통상임금 계산

        Args:
            method: 계산 방법 ('direct', 'monthly', 'skip')
            amount: 입력 금액
            saturday_type: 토요일 근무 유형

        Returns:
            Dict: 통상임금 계산 결과
        """
        try:
            if method == "skip":
                return {
                    "method": "skip",
                    "hourly_wage": 0,
                    "daily_wage": 0,
                    "monthly_wage": 0,
                    "calculation_details": "통상임금 계산을 건너뛰었습니다."
                }

            elif method == "direct":
                # 방법 1: 직접 계산한 통상임금 입력
                daily_wage = amount
                hourly_wage = daily_wage / CompensationStandards.DAILY_WORK_HOURS

                # 월 소정근로시간 계산
                monthly_hours = CompensationCalculatorService._get_monthly_hours(saturday_type)
                monthly_wage = hourly_wage * monthly_hours

                return {
                    "method": "direct",
                    "hourly_wage": int(hourly_wage),
                    "daily_wage": daily_wage,
                    "monthly_wage": int(monthly_wage),
                    "calculation_details": f"일급 통상임금 {amount:,}원을 직접 입력"
                }

            elif method == "monthly":
                # 방법 2: 월 통상임금으로 자동 계산
                monthly_wage = amount
                monthly_hours = CompensationCalculatorService._get_monthly_hours(saturday_type)

                hourly_wage = monthly_wage / monthly_hours
                daily_wage = hourly_wage * CompensationStandards.DAILY_WORK_HOURS

                return {
                    "method": "monthly",
                    "hourly_wage": int(hourly_wage),
                    "daily_wage": int(daily_wage),
                    "monthly_wage": monthly_wage,
                    "monthly_hours": monthly_hours,
                    "saturday_type": saturday_type.value,
                    "calculation_details": f"월 통상임금 {amount:,}원 ÷ {monthly_hours}시간 = 시급 {int(hourly_wage):,}원"
                }

            else:
                raise ValueError(f"지원하지 않는 계산 방법: {method}")

        except Exception as e:
            logger.error(f"통상임금 계산 오류: {e}")
            raise ValueError(f"통상임금 계산 중 오류가 발생했습니다: {str(e)}")

    @staticmethod
    def _get_monthly_hours(saturday_type: SaturdayWorkType) -> int:
        """토요일 근무 유형에 따른 월 소정근로시간 반환"""
        if saturday_type == SaturdayWorkType.FULL_PAY_8H:
            return CompensationStandards.MONTHLY_HOURS_FULL_SATURDAY
        elif saturday_type == SaturdayWorkType.HALF_PAY_4H:
            return CompensationStandards.MONTHLY_HOURS_HALF_SATURDAY
        else:  # NO_PAY
            return CompensationStandards.MONTHLY_HOURS_NO_SATURDAY

    @staticmethod
    def calculate_all_benefits(
        daily_average_wage: int,
        calculation_date: date,
        disability_grade: Optional[str] = None,
        survivors_count: int = 1,
        apply_limits: bool = True
    ) -> Dict[str, Any]:
        """
        모든 산재 보상금 계산

        Args:
            daily_average_wage: 일 평균임금
            calculation_date: 계산 기준일
            disability_grade: 장해등급 (예: "1급", "2급" 등)
            survivors_count: 유족 수
            apply_limits: 최저/최고 한도 적용 여부

        Returns:
            Dict: 모든 보상금 계산 결과
        """
        try:
            # 평균임금 한도 적용 (선택사항)
            limited_wage = daily_average_wage
            if apply_limits:
                limited_wage = max(
                    CompensationStandards.MIN_DAILY_AMOUNT,
                    min(daily_average_wage, CompensationStandards.MAX_DAILY_AMOUNT)
                )

            # 각 보상금 계산
            results = {
                "input_data": {
                    "daily_average_wage": daily_average_wage,
                    "limited_wage": limited_wage,
                    "calculation_date": calculation_date.isoformat(),
                    "disability_grade": disability_grade,
                    "survivors_count": survivors_count,
                    "apply_limits": apply_limits
                },
                "calculations": {}
            }

            # 1. 휴업급여 (평균임금의 70%)
            results["calculations"]["sick_leave_benefit"] = (
                CompensationCalculatorService._calculate_sick_leave_benefit(limited_wage)
            )

            # 2. 상병보상연금 (제1급 기준 329일)
            results["calculations"]["medical_care_pension"] = (
                CompensationCalculatorService._calculate_medical_care_pension(limited_wage)
            )

            # 3. 장해급여 (등급별)
            results["calculations"]["disability_benefit"] = (
                CompensationCalculatorService._calculate_disability_benefit(
                    limited_wage, disability_grade
                )
            )

            # 4. 유족급여
            results["calculations"]["survivor_benefit"] = (
                CompensationCalculatorService._calculate_survivor_benefit(
                    limited_wage, survivors_count
                )
            )

            # 5. 장례비
            results["calculations"]["funeral_benefit"] = (
                CompensationCalculatorService._calculate_funeral_benefit(limited_wage)
            )

            # 총 예상 보상금 (상황에 따라 적용되는 항목만)
            total_amount = 0
            if disability_grade:
                total_amount += results["calculations"]["disability_benefit"]["annual_amount"]
            else:
                # 장해가 없는 경우 휴업급여 기준 (30일)
                total_amount += results["calculations"]["sick_leave_benefit"]["daily_amount"] * 30

            total_amount += results["calculations"]["medical_care_pension"]["total_amount"]
            total_amount += results["calculations"]["funeral_benefit"]["total_amount"]

            results["summary"] = {
                "total_estimated_amount": total_amount,
                "calculation_date": calculation_date.isoformat(),
                "year_standard": 2025,
                "notes": "실제 지급액은 개별 상황과 심사 결과에 따라 달라질 수 있습니다."
            }

            return results

        except Exception as e:
            logger.error(f"보상금 계산 오류: {e}")
            raise ValueError(f"보상금 계산 중 오류가 발생했습니다: {str(e)}")

    @staticmethod
    def _calculate_sick_leave_benefit(daily_wage: int) -> Dict[str, Any]:
        """휴업급여 계산 (평균임금의 70%)"""
        daily_amount = int(daily_wage * 0.7)

        return {
            "name": "휴업급여",
            "description": "업무상 재해로 요양 중인 근로자에게 지급",
            "rate": "70%",
            "daily_amount": daily_amount,
            "calculation": f"{daily_wage:,}원 × 70% = {daily_amount:,}원/일",
            "legal_basis": "산업재해보상보험법 제52조"
        }

    @staticmethod
    def _calculate_medical_care_pension(daily_wage: int) -> Dict[str, Any]:
        """상병보상연금 계산 (제1급 기준 329일)"""
        grade_1_days = 329
        total_amount = daily_wage * grade_1_days

        return {
            "name": "상병보상연금",
            "description": "요양개시 후 2년이 경과한 상병에 대한 연금",
            "grade": "제1급",
            "days": grade_1_days,
            "daily_amount": daily_wage,
            "total_amount": total_amount,
            "calculation": f"{daily_wage:,}원 × {grade_1_days}일 = {total_amount:,}원/년",
            "legal_basis": "산업재해보상보험법 제57조"
        }

    @staticmethod
    def _calculate_disability_benefit(
        daily_wage: int,
        disability_grade: Optional[str]
    ) -> Dict[str, Any]:
        """장해급여 계산"""
        if not disability_grade:
            return {
                "name": "장해급여",
                "description": "장해등급이 확정되지 않아 계산할 수 없습니다.",
                "grade": None,
                "amount": 0,
                "calculation": "장해등급 정보 필요"
            }

        # 장해등급별 지급일수 (2025년 기준)
        grade_days = {
            "1급": 1474, "2급": 1309, "3급": 1155, "4급": 1012,
            "5급": 869, "6급": 737, "7급": 616, "8급": 495,
            "9급": 385, "10급": 286, "11급": 198, "12급": 121,
            "13급": 55, "14급": 22
        }

        days = grade_days.get(disability_grade, 0)
        if days == 0:
            return {
                "name": "장해급여",
                "description": f"지원하지 않는 장해등급: {disability_grade}",
                "grade": disability_grade,
                "amount": 0,
                "calculation": "유효하지 않은 등급"
            }

        # 1-3급은 연금, 4-14급은 일시금
        if disability_grade in ["1급", "2급", "3급"]:
            annual_amount = daily_wage * days
            monthly_amount = annual_amount // 12

            return {
                "name": "장해급여 (연금)",
                "description": "장해등급 1-3급에 대한 연금 지급",
                "grade": disability_grade,
                "days": days,
                "annual_amount": annual_amount,
                "monthly_amount": monthly_amount,
                "calculation": f"{daily_wage:,}원 × {days}일 = {annual_amount:,}원/년 ({monthly_amount:,}원/월)",
                "payment_type": "연금",
                "legal_basis": "산업재해보상보험법 제57조"
            }
        else:
            lump_sum = daily_wage * days

            return {
                "name": "장해급여 (일시금)",
                "description": "장해등급 4-14급에 대한 일시금 지급",
                "grade": disability_grade,
                "days": days,
                "lump_sum": lump_sum,
                "calculation": f"{daily_wage:,}원 × {days}일 = {lump_sum:,}원",
                "payment_type": "일시금",
                "legal_basis": "산업재해보상보험법 제57조"
            }

    @staticmethod
    def _calculate_survivor_benefit(daily_wage: int, survivors_count: int) -> Dict[str, Any]:
        """유족급여 계산 (기본 47% + 가산)"""
        base_rate = CompensationStandards.SURVIVOR_BASE_RATE
        additional_rate = CompensationStandards.SURVIVOR_ADDITIONAL_RATE

        # 기본 47% + 유족 1명당 5% 가산 (최대 67%)
        total_rate = min(base_rate + (additional_rate * survivors_count), 0.67)

        annual_amount = int(daily_wage * 365 * total_rate)
        monthly_amount = annual_amount // 12

        return {
            "name": "유족급여",
            "description": "업무상 재해로 사망한 근로자의 유족에게 지급",
            "base_rate": f"{base_rate * 100:.0f}%",
            "additional_rate": f"{additional_rate * 100:.0f}%",
            "survivors_count": survivors_count,
            "total_rate": f"{total_rate * 100:.1f}%",
            "annual_amount": annual_amount,
            "monthly_amount": monthly_amount,
            "calculation": f"{daily_wage:,}원 × 365일 × {total_rate:.1%} = {annual_amount:,}원/년",
            "legal_basis": "산업재해보상보험법 제61조"
        }

    @staticmethod
    def _calculate_funeral_benefit(daily_wage: int) -> Dict[str, Any]:
        """장례비 계산 (평균임금 × 120일)"""
        days = 120
        total_amount = daily_wage * days

        return {
            "name": "장례비",
            "description": "업무상 재해로 사망한 근로자의 장례비",
            "days": days,
            "total_amount": total_amount,
            "calculation": f"{daily_wage:,}원 × {days}일 = {total_amount:,}원",
            "legal_basis": "산업재해보상보험법 제71조"
        }

    @staticmethod
    def validate_calculation_input(
        wage_method: str,
        wage_amount: int,
        calculation_date: Optional[str] = None,
        saturday_type: str = "no_pay"
    ) -> Tuple[bool, str]:
        """
        계산 입력값 검증

        Returns:
            Tuple[bool, str]: (유효성, 오류 메시지)
        """
        try:
            # 계산 방법 검증
            if wage_method not in ["direct", "monthly", "skip"]:
                return False, "지원하지 않는 통상임금 계산 방법입니다."

            # 금액 검증
            if wage_method != "skip":
                if wage_amount <= 0:
                    return False, "통상임금은 0보다 커야 합니다."

                if wage_amount > 10000000:  # 1천만원 한도
                    return False, "통상임금이 너무 큽니다. (최대 1천만원)"

            # 날짜 검증
            if calculation_date:
                try:
                    parsed_date = datetime.strptime(calculation_date, "%Y-%m-%d").date()
                    if parsed_date.year != 2025:
                        return False, "2025년 기준만 지원됩니다."
                except ValueError:
                    return False, "날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)"

            # 토요일 근무 유형 검증
            if saturday_type not in ["full_8h", "half_4h", "no_pay"]:
                return False, "지원하지 않는 토요일 근무 유형입니다."

            return True, ""

        except Exception as e:
            logger.error(f"입력값 검증 오류: {e}")
            return False, f"입력값 검증 중 오류가 발생했습니다: {str(e)}"