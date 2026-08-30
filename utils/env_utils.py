"""Shared environment (.env) helpers, usable from any package/module."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent


def load_env(base_dir: Path | None = None) -> None:
    """Load the repo-root .env (or a custom path) into os.environ.

    Existing environment variables are NOT overwritten, so values injected
    by Docker / the OS always win.
    """
    env_path = (base_dir or ROOT_DIR) / ".env"
    load_dotenv(env_path, override=False)


def get_env(key: str, default: str = "") -> str:
    """Read a config value; falls back to <default> when unset/blank."""
    return os.environ.get(key) or default