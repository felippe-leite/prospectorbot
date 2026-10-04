"""Application settings, loaded explicitly rather than at import time."""

import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    database_path: Path = Path("data/prospector.db")
    geoapify_api_key: SecretStr | None = None
    request_timeout: float = Field(default=10, gt=0, le=60)
    request_interval: float = Field(default=1, ge=1, le=60)
    max_links: int = Field(default=5, ge=0, le=10)
    max_body_bytes: int = Field(default=2_000_000, ge=1024, le=5_000_000)
    scoring_config: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        # Read only the current directory; environment values take precedence.
        # No shell execution, interpolation, or changes to os.environ.
        environment = {**dotenv_values(Path.cwd() / ".env", interpolate=False), **os.environ}
        value = environment.get("PROSPECTOR_DATABASE_PATH")
        if value is not None and not value.strip():
            raise ValueError("PROSPECTOR_DATABASE_PATH cannot be empty")
        values = {"database_path": Path(value).expanduser()} if value else {}
        key = (environment.get("GEOAPIFY_API_KEY") or "").strip()
        if key:
            values["geoapify_api_key"] = key
        for variable, field in {
            "PROSPECTOR_REQUEST_TIMEOUT": "request_timeout",
            "PROSPECTOR_REQUEST_INTERVAL": "request_interval",
            "PROSPECTOR_MAX_LINKS": "max_links",
            "PROSPECTOR_SCORING_CONFIG": "scoring_config",
        }.items():
            if variable in environment and environment[variable] is not None:
                values[field] = environment[variable]
        return cls(**values)
