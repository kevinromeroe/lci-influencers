#!/usr/bin/env python3
"""build_reporte.py — Genera el reporte web de cada campaña.

Lee config/cliente.yaml y config/campanas/<id>.yaml, calcula las métricas con
pipeline/metrics.py y escribe <id>/index.html a partir de templates/reporte.html.
La raíz del sitio (index.html) redirige a la campaña más reciente.

Uso:
    python scripts/build_reporte.py            # todas las campañas
    python scripts/build_reporte.py 2026-10    # una campaña
    python scripts/build_reporte.py --forzar   # saltar el candado (solo con una razón clara)

Candado: el reporte lo publica la corrida automática del OptiPlex con su captura más
reciente. Si la captura de este equipo es más vieja que la del reporte ya construido,
el build se detiene: construir aquí bajaría las cifras publicadas (pasó el 26-nov-2026).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.metrics import build_data  # noqa: E402
from pipeline.util.config import PROJECT_ROOT, campaign_ids, latest_capture, load_campaign, load_client  # noqa: E402
from pipeline.util.log import get_logger  # noqa: E402

log = get_logger("build_reporte")
TEMPLATE = PROJECT_ROOT / "templates" / "reporte.html"
MARKER = "/*__DATA__*/null"


class CapturaVieja(RuntimeError):
    """La captura local es más vieja que la del reporte ya construido."""


def captura_del_reporte(path: Path) -> str | None:
    """Fecha de captura con la que se construyó el reporte existente (None si no hay)."""
    if not path.exists():
        return None
    m = re.search(r'"captured_on"\s*:\s*"(\d{4}-\d{2}-\d{2})"', path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def verificar_frescura(local: str | None, publicada: str | None) -> None:
    """Detiene el build si los datos de este equipo son más viejos que los del reporte construido."""
    if publicada and (local is None or local < publicada):
        raise CapturaVieja(
            f"La captura de este equipo ({local or 'ninguna'}) es más vieja que la del reporte "
            f"construido ({publicada}). El reporte lo construye la corrida automática del OptiPlex: "
            "sube solo los cambios de config, plantilla o cálculo y deja que la próxima corrida publique. "
            "Ver docs/RUNBOOK.md («Corrida automática»). Para saltar el candado: --forzar.")


def build(campaign_id: str, client: dict, forzar: bool = False) -> Path:
    capture = latest_capture(campaign_id)
    out = PROJECT_ROOT / campaign_id / "index.html"
    if not forzar:
        verificar_frescura(capture["captured_on"] if capture else None, captura_del_reporte(out))
    data = build_data(client, load_campaign(campaign_id), capture)
    html = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in html:
        raise RuntimeError(f"La plantilla no tiene el marcador {MARKER}")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html.replace(MARKER, payload), encoding="utf-8")
    log.info("reporte_ok", extra={"campaign": campaign_id, "creators": len(data["creators"]),
                                   "emv_total": data["totals"]["emv"],
                                   "captura": capture["captured_on"] if capture else "config"})
    return out


def write_root_redirect(latest: str) -> None:
    (PROJECT_ROOT / "index.html").write_text(
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f'<meta http-equiv="refresh" content="0; url=/{latest}/">'
        '<meta name="robots" content="noindex"><title>Reporte de campaña de influencers</title></head>'
        f'<body><a href="/{latest}/">Ir al reporte más reciente</a><script async src="/gc.js"></script></body></html>',
        encoding="utf-8",
    )


def main() -> int:
    client = load_client()
    forzar = "--forzar" in sys.argv[1:]
    ids = [a for a in sys.argv[1:] if not a.startswith("--")] or campaign_ids()
    try:
        for cid in ids:
            build(cid, client, forzar)
    except CapturaVieja as e:
        print(f"[ALTO] {e}", file=sys.stderr)
        return 2
    write_root_redirect(campaign_ids()[-1])
    print(f"[DONE] Reportes generados: {', '.join(ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
