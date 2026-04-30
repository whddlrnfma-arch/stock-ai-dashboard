"""
config.py
---------
환경변수 기반 전역 설정 모듈.
pydantic-settings를 사용하여 타입 안전성을 보장한다.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Oracle DB
    DB_USER: str = "system"
    DB_PASS: str = ""
    DB_IP: str = "127.0.0.1"
    DB_PORT: int = 1521
    DB_SID: str = "XE"

    # Connection Pool
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10
    DB_POOL_INCREMENT: int = 1

    # TTLCache (단타 종목 대기 시간, 초 단위)
    CACHE_TTL_SECONDS: int = 600
    CACHE_MAX_SIZE: int = 1000

    # 뉴스 스케줄러 (분 단위)
    NEWS_POLL_INTERVAL_MINUTES: int = 5

    # entry_strength 최소 임계값 (미만 시 Drop)
    ENTRY_STRENGTH_THRESHOLD: float = 70.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_dsn(self) -> str:
        """oracledb thin 모드 DSN 문자열 반환"""
        return f"{self.DB_IP}:{self.DB_PORT}/{self.DB_SID}"


# 싱글턴 인스턴스
settings = Settings()
