"""Portable filesystem paths for local dev and Docker (Render)."""

from __future__ import annotations

from pathlib import Path

# backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def resolve_data_root() -> Path:
    """
    Resolve the data directory relative to BACKEND_ROOT.

    Prefers sibling ``../data`` (repo layout and Docker /app/data).
    Falls back to ``BACKEND_ROOT/data`` when the sibling folder is absent.
    """
    candidates = (
        BACKEND_ROOT.parent / "data",
        BACKEND_ROOT / "data",
    )
    for path in candidates:
        if path.is_dir():
            return path
    fallback = BACKEND_ROOT / "data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


DATA_ROOT = resolve_data_root()
UPLOADS_ROOT = DATA_ROOT / "uploads"
DEFAULT_DB_PATH = BACKEND_ROOT.parent / "fraudia.db"
