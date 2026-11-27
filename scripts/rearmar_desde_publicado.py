"""Uso: python scripts/rearmar_desde_publicado.py .

Rearma 2026-10/index.html SIN la captura local: toma las cifras de la última corrida automática
(el DATA del index.html publicado) y le aplica la config y la plantilla actuales.

- Métricas de cada publicación ya publicada: las del OptiPlex (no se tocan).
- Publicaciones nuevas en la config (sin cifra del OptiPlex): las de la config.
- Comparación con reels, seguidores, conversación y gráficas: las publicadas.
- captured_on se conserva, así el candado del OptiPlex sigue funcionando.
"""
import copy
import json
import re
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
sys.path.insert(0, str(REPO))
from pipeline.metrics import build_data  # noqa: E402
from pipeline.util.config import load_campaign, load_client  # noqa: E402

out = REPO / "2026-10" / "index.html"
html = out.read_text(encoding="utf-8")
pub = json.loads(re.search(r"var DATA = (\{.*?\});\s*\n", html, re.S).group(1))

camp = load_campaign("2026-10")
client = load_client()

# 1) Métricas publicadas → config (por id de publicación)
pubposts = {p["id"]: p for c in pub["creators"] for p in c["posts"]}
for c in camp["creators"]:
    for p in c["publications"]:
        q = pubposts.get(p["id"])
        if q:
            # Solo suben: la cifra más alta entre la publicada (OptiPlex) y la de la config (lectura manual)
            cfg = p.get("metrics") or {}
            p["metrics"] = {k: max(q.get(k) or 0, cfg.get(k) or 0) for k in ("views", "likes", "comments", "shares", "saves")
                            if q.get(k) is not None or cfg.get(k) is not None}
            if q.get("aprox"):
                p["aprox"] = list(q["aprox"])

data = build_data(client, camp, None)
data["campaign"]["captured_on"] = pub["campaign"]["captured_on"]

# 2) Campos que dependen de la captura del OptiPlex → los publicados
# Influencers cuya ventana de comparación vive en la config (el OptiPlex no la captura)
VENTANAS_DE_CONFIG = {"zambo.design"}
KEEP = ("followers", "reels", "lci", "marks", "med", "idx", "isMin", "charts", "talk", "talkLine", "top")
pubc = {c["handle"]: c for c in pub["creators"]}
for c in data["creators"]:
    old = pubc.get(c["handle"])
    # Solo si el publicado trae ventana de reels (viene de la captura del OptiPlex);
    # si no la trae, se usa la ventana de la config (p. ej. Juliana, 27-nov-2026).
    if not old or not old.get("reels") or c["handle"] in VENTANAS_DE_CONFIG:
        continue
    for k in KEEP:
        if k in old:
            c[k] = old[k]
    c["reach"] = c["t"]["views"] / c["followers"] if c["followers"] else 0
data["totals"]["fol"] = sum(c["followers"] for c in data["creators"] if c["summary"])

tpl = (REPO / "templates" / "reporte.html").read_text(encoding="utf-8")
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
out.write_text(tpl.replace("/*__DATA__*/null", payload), encoding="utf-8")

T, P = data["totals"], pub["totals"]
print("captured_on", data["campaign"]["captured_on"])
print(f"EMV {P['emv']:,} -> {T['emv']:,} | inversión {P['pay']:,} -> {T['pay']:,} | ROI {P['roi']*100:.1f}% -> {T['roi']*100:.1f}% | salidas {P['done']} -> {T['done']}")
for c in data["creators"]:
    o = pubc.get(c["handle"], {"t": {"emv": 0, "views": 0}, "done": 0})
    print(f"  {c['name']:20} EMV {o['t']['emv']:>13,} -> {c['t']['emv']:>13,} | vistas {o['t']['views']:>9,} -> {c['t']['views']:>9,} | salidas {o['done']}->{c['done']}/{c['actions']} | formatos {[p['format'] for p in c['posts']]}")
