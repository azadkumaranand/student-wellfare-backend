from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def parse_csv_env(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


load_env_file()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Studentwellfare API")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./studentwellfare.db")
    cors_origins: tuple[str, ...] = parse_csv_env("BACKEND_CORS_ORIGINS", "*")
    seed_parent_name: str = os.getenv("SEED_PARENT_NAME", "Parent Admin")
    seed_parent_email: str = os.getenv("SEED_PARENT_EMAIL", "parent@example.com")
    seed_parent_password: str = os.getenv("SEED_PARENT_PASSWORD", "parent123")
    seed_parent_pin: str = os.getenv("SEED_PARENT_PIN", "1234")
    seed_student_id: str = os.getenv("SEED_STUDENT_ID", "stu_001")
    seed_student_name: str = os.getenv("SEED_STUDENT_NAME", "Aarav Sharma")
    seed_organization_id: str = os.getenv("SEED_ORGANIZATION_ID", "org_internal")
    seed_pairing_code: str = os.getenv("SEED_PAIRING_CODE", "SAFE-2048")
    alert_email_enabled: bool = os.getenv("ALERT_EMAIL_ENABLED", "false").lower() == "true"
    alert_email_from: str = os.getenv("ALERT_EMAIL_FROM", "alerts@studentwellfare.local")
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    fcm_enabled: bool = os.getenv("FCM_ENABLED", "false").lower() == "true"
    fcm_server_key: str = os.getenv("FCM_SERVER_KEY", "")


settings = Settings()
