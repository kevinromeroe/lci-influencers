#!/usr/bin/env python3
"""render_pdf.py — Genera un PDF por pestaña del reporte con Chromium.

Por cada campaña escribe <campaña>/pdf/<pestaña>.pdf: "todas.pdf" para la vista
de todas las publicaciones y uno por influencer. El botón "Descargar PDF" del
reporte apunta al PDF de la pestaña abierta.

Requiere un servidor HTTP sirviendo la raíz del repo en localhost:8000
(el workflow lo levanta con `python -m http.server 8000`).

Uso:
    python scripts/render_pdf.py            # todas las campañas
    python scripts/render_pdf.py 2026-10    # una campaña
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("PDF_BASE_URL", "http://localhost:8000")


def campaigns() -> list[str]:
    return sorted(p.stem for p in (ROOT / "config" / "campanas").glob("*.yaml"))


def render(ids: list[str]) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        for cid in ids:
            if not (ROOT / cid / "index.html").exists():
                print(f"  ⚠ {cid}/index.html no existe — lo salto")
                continue
            page.goto(f"{BASE}/{cid}/", wait_until="networkidle", timeout=60000)
            tabs = page.evaluate("() => window.REPORT_TABS")
            outdir = ROOT / cid / "pdf"
            outdir.mkdir(exist_ok=True)
            for tab in tabs:
                page.click(f"#tab-{tab}")
                # Esperar fotos de perfil y fuentes antes de imprimir
                page.evaluate(
                    """() => Promise.all([document.fonts.ready,
                        ...[...document.images].map(i => i.complete ? null
                            : new Promise(r => { i.onload = i.onerror = r; }))])"""
                )
                page.wait_for_timeout(500)
                out = outdir / f"{tab}.pdf"
                page.pdf(path=str(out), format="A4", landscape=True, print_background=True,
                         margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"},
                         prefer_css_page_size=True)
                print(f"  ✓ {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
        browser.close()


def main() -> None:
    ids = sys.argv[1:] or campaigns()
    print(f"Campañas a renderizar: {ids}")
    render(ids)
    print("\n[DONE] PDF(s) generado(s).")


if __name__ == "__main__":
    main()
