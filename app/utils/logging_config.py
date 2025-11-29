"""
SANZERO 통합 로깅 설정
표준 Python logging 모듈을 사용한 일관된 로깅 시스템
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime


def setup_logging(level: str = "INFO") -> None:
    """
    애플리케이션 전체 로깅 설정 초기화

    Args:
        level: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 로그 파일 경로
    log_file = log_dir / "app.log"
    error_log_file = log_dir / "error.log"

    # 로깅 레벨 설정
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 포매터 설정
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 기존 핸들러 제거 (중복 방지)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # 일반 로그 파일 핸들러
    file_handler = logging.FileHandler(
        log_file,
        mode='a',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # 에러 로그 파일 핸들러 (ERROR 이상만)
    error_handler = logging.FileHandler(
        error_log_file,
        mode='a',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)

    # 외부 라이브러리 로그 레벨 조정
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # 초기화 완료 로그
    logger = logging.getLogger(__name__)
    logger.info(f"Logging system initialized - Level: {level}")


def get_logger(name: str) -> logging.Logger:
    """
    모듈별 로거 반환

    Args:
        name: 보통 __name__ 사용

    Returns:
        logging.Logger: 설정된 로거 인스턴스
    """
    return logging.getLogger(name)


# 편의 함수들
def log_exception(logger: logging.Logger, message: str = "Unhandled exception"):
    """예외 정보와 함께 로그 기록"""
    logger.exception(message)


def log_performance(logger: logging.Logger, operation: str, duration: float):
    """성능 측정 로그"""
    if duration > 1.0:
        logger.warning(f"Slow operation: {operation} took {duration:.2f}s")
    else:
        logger.info(f"Operation: {operation} completed in {duration:.2f}s")