"""
core/config.py
──────────────
애플리케이션 전역 설정 및 환경변수 관리.
pydantic-settings 를 이용해 .env 파일을 자동 로드합니다.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Oracle DB ───────────────────────────────────────────────
    DB_USER: str = "system"
    DB_PASS: str = ""
    DB_IP: str = "127.0.0.1"
    DB_PORT: int = 1521
    DB_SID: str = "XE"

    # ── Connection Pool ─────────────────────────────────────────
    DB_POOL_MIN: int = 2
    DB_POOL_MAX: int = 10
    DB_POOL_INCREMENT: int = 1

    # ── Business Rules ──────────────────────────────────────────
    ENTRY_STRENGTH_THRESHOLD: float = 70.0   # 이 값 미만은 DB 저장 거부
    CACHE_TTL_SECONDS: int = 600             # 이탈 종목 메모리 보존 시간 (10분)
    CACHE_MAX_SIZE: int = 1000

    # ── News Polling ─────────────────────────────────────────────
    NEWS_POLL_INTERVAL_SECONDS: int = 300    # 5분
    NEWS_API_KEY: str = ""                   # NewsAPI key (선택)

    model_config = SettingsConfigDict(
        env_file="d:/STOCK AI/.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
