"""Carga de la configuración del cliente y de las campañas."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def load_client() -> dict[str, Any]:
    return _load(CONFIG_DIR / "cliente.yaml")


def load_campaign(campaign_id: str) -> dict[str, Any]:
    return _load(CONFIG_DIR / "campanas" / f"{campaign_id}.yaml")


def campaign_ids() -> list[str]:
    return sorted(p.stem for p in (CONFIG_DIR / "campanas").glob("*.yaml"))


CAPTURES_DIR = PROJECT_ROOT / "datos" / "capturas"


def latest_capture(campaign_id: str) -> dict[str, Any] | None:
    """Captura más reciente de la campaña (datos/capturas/<id>/<fecha>.json), si existe.

    Las capturas son locales: la carpeta datos/ no se versiona.
    """
    files = sorted((CAPTURES_DIR / campaign_id).glob("*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text(encoding="utf-8"))


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"Required env var {name} not set. See .env.example and docs/RUNBOOK.md."
        )
    return val
