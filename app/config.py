"""Runtime settings, read from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    db_path: Path
    aw_url: str
    aw_timeout: float


def load_settings() -> Settings:
    return Settings(
        db_path=Path(os.environ.get("PRESENCE_DB", ROOT / "data" / "presence.db")),
        aw_url=os.environ.get("PRESENCE_AW_URL", "http://localhost:5600").rstrip("/"),
        aw_timeout=float(os.environ.get("PRESENCE_AW_TIMEOUT", "10")),
    )
