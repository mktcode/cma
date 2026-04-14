from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_DATABASE = "website_agent"
DEFAULT_SOCKET = "/run/mysqld/mysqld.sock"
SYSTEM_CONFIG = Path("/etc/website-cli.json")
USER_CONFIG = Path.home() / ".config" / "website-cli.json"


@dataclass(frozen=True)
class DatabaseConfig:
    user: str = "root"
    password: str | None = None
    host: str = "127.0.0.1"
    port: int = 3306
    database: str | None = DEFAULT_DATABASE
    unix_socket: str | None = DEFAULT_SOCKET


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_database_config() -> DatabaseConfig:
    settings: dict[str, Any] = {}

    settings.update(_load_json(SYSTEM_CONFIG))
    settings.update(_load_json(USER_CONFIG))

    custom_path = os.environ.get("WEBSITE_CONFIG")
    if custom_path:
        settings.update(_load_json(Path(custom_path)))

    env_overrides = {
        "user": os.environ.get("WEBSITE_DB_USER"),
        "password": os.environ.get("WEBSITE_DB_PASSWORD"),
        "host": os.environ.get("WEBSITE_DB_HOST"),
        "port": os.environ.get("WEBSITE_DB_PORT"),
        "database": os.environ.get("WEBSITE_DB_NAME"),
        "unix_socket": os.environ.get("WEBSITE_DB_SOCKET"),
    }

    for key, value in env_overrides.items():
        if value is not None:
            settings[key] = value

    port = int(settings.get("port", 3306))
    return DatabaseConfig(
        user=settings.get("user", "root"),
        password=settings.get("password"),
        host=settings.get("host", "127.0.0.1"),
        port=port,
        database=settings.get("database", DEFAULT_DATABASE),
        unix_socket=settings.get("unix_socket", DEFAULT_SOCKET),
    )
