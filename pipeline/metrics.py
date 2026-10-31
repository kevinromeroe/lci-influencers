"""Cálculo único de las métricas del reporte.

Todas las cifras que aparecen en el reporte salen de `build_data()`; la
plantilla solo las formatea. Así el mismo número es idéntico en cada pestaña
y en el PDF.

Fórmulas (ver config/cliente.yaml):
  interacciones   = me gusta + comentarios
  engagement      = interacciones ÷ reproducciones
  alcance         = reproducciones ÷ seguidores
  EMV             = me gusta × v.like + comentarios × v.comment
                    + compartidos × v.share + guardados × v.save
  ROI             = (EMV − inversión) ÷ inversión        (solo con pago)
  frente a su contenido = reproducciones del reel de LCI ÷ mediana de
                    sus otros reels recientes no fijados
"""
from __future__ import annotations

import copy
from datetime import date
from statistics import median
from typing import Any

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
NETWORKS = {"ig": "Instagram", "fb": "Facebook", "tt": "TikTok"}


def fecha_corta(iso: str | None) -> str | None:
    if not iso:
        return None
    d = date.fromisoformat(str(iso))
    return f"{d.day} {MESES[d.month - 1]}"


def fecha_larga(iso: str | None) -> str | None:
    if not iso:
        return None
    d = date.fromisoformat(str(iso))
    return f"{d.day} {MESES[d.month - 1]} {d.year}"


def emv(m: dict[str, Any], v: dict[str, int]) -> int:
    return (m.get("likes", 0) * v["like"] + m.get("comments", 0) * v["comment"]
            + m.get("shares", 0) * v["share"] + m.get("saves", 0) * v["save"])


def roi(emv_value: float, payment: float | None) -> float | None:
    return (emv_value - payment) / payment if payment else None


def _publication(p: dict[str, Any], v: dict[str, int]) -> dict[str, Any]:
    m = p["metrics"]
    inter = m.get("likes", 0) + m.get("comments", 0)
    value = emv(m, v)
    return {
        "id": p["id"], "net": p["network"], "netName": NETWORKS[p["network"]],
        "format": p["format"], "date": fecha_larga(p["posted_on"]), "url": p["url"],
        "type": p["type"], "pay": p.get("payment_cop"),
        "views": m["views"], "likes": m.get("likes", 0), "comments": m.get("comments", 0),
        "inter": inter, "er": inter / m["views"], "emv": value,
        "roi": roi(value, p.get("payment_cop")),
    }


def _creator(c: dict[str, Any], v: dict[str, int]) -> dict[str, Any]:
    pubs = [_publication(p, v) for p in c["publications"]]
    t = {k: sum(p[k] for p in pubs) for k in ("views", "likes", "comments", "inter", "emv")}
    pays = [p["pay"] for p in pubs]
    t["pay"] = sum(pays) if all(pays) else None

    base = c["baseline"]
    lci = next(i for i, r in enumerate(base) if r.get("lci"))
    others = [r["views"] for i, r in enumerate(base) if i != lci and not r.get("pinned")]
    med = median(others)
    lci_views = base[lci]["views"]
    return {
        "id": c["handle"].replace("_", "-").strip("-"), "handle": c["handle"], "name": c["name"],
        "niche": c["niche"], "followers": c["followers"], "avatar": c.get("avatar"),
        "posts": pubs, "t": t,
        "er": t["inter"] / t["views"], "reach": t["views"] / c["followers"],
        "roi": roi(t["emv"], t["pay"]),
        "reels": [[r["views"], fecha_corta(r.get("posted_on"))] for r in base],
        "lci": lci, "marks": {str(i): r["mark"] for i, r in enumerate(base) if r.get("mark")},
        "med": med, "idx": lci_views / med, "isMin": lci_views == min(r["views"] for r in base),
        "why": c.get("why", []), "cause": c.get("cause", ""),
        "talk": {k: c["talk"][k] for k in ("read", "pos", "neu", "neg", "note")},
        "talkLine": c["talk"]["line"], "top": c["talk"]["top"],
    }


def _apply_comments(c: dict[str, Any], comments: dict[str, Any]) -> None:
    """Balance de sentimiento y top 3 (comentarios principales, por me gusta) desde la captura."""
    items = [i for p in c["publications"] for i in comments.get(p["id"], {}).get("items", [])]
    if not items:
        return
    count = {s: sum(1 for i in items if i["sentiment"] == s) for s in ("positivo", "neutro", "critico")}
    top = sorted((i for i in items if not i.get("reply_to")), key=lambda i: i["likes"], reverse=True)[:3]
    c["talk"].update(read=len(items), pos=count["positivo"], neu=count["neutro"], neg=count["critico"],
                     top=[[i["text"], i["likes"]] for i in top])


def apply_capture(campaign: dict[str, Any], capture: dict[str, Any], baseline_n: int) -> dict[str, Any]:
    """Superpone una captura a la campaña: seguidores, métricas de publicaciones y reels de comparación.

    Ventana de comparación: los últimos `baseline_n` reels no fijados publicados
    hasta la fecha de corte de la campaña (incluye el reel de LCI).
    Los textos curados (why, cause, talk) no cambian.
    """
    camp = copy.deepcopy(campaign)
    corte = str(camp["campaign"]["corte"])
    for c in camp["creators"]:
        cap = capture["creators"].get(c["handle"])
        pub_ids = {p["id"] for p in c["publications"]}
        for p in c["publications"]:
            m = capture["publications"].get(p["id"])
            if m:
                p["posted_on"] = m["posted_on"]
                p["metrics"] = {k: m[k] for k in ("views", "likes", "comments", "shares", "saves") if k in m}
        _apply_comments(c, capture.get("comments", {}))
        if not cap:
            continue
        c["followers"] = cap["followers"]
        reels = sorted((r for r in cap["reels"] if not r.get("pinned") and r["posted_on"] <= corte),
                       key=lambda r: r["posted_on"])[-baseline_n:]
        if not pub_ids & {r["id"] for r in reels}:
            raise ValueError(f"El reel de LCI de @{c['handle']} no está en su ventana de comparación")
        marks = c.get("marks", {})
        c["baseline"] = [{"views": r["views"], "posted_on": r["posted_on"], "lci": r["id"] in pub_ids,
                          **({"mark": marks[r["id"]]} if r["id"] in marks else {})} for r in reels]
    return camp


def build_data(client: dict[str, Any], campaign: dict[str, Any],
               capture: dict[str, Any] | None = None) -> dict[str, Any]:
    v = client["emv"]["valores"]
    if capture:
        campaign = apply_capture(campaign, capture, client["analytics"]["baseline_reels"])
    creators = [_creator(c, v) for c in campaign["creators"]]

    posts = [dict(p, creator=c["id"]) for c in creators for p in c["posts"]]
    posts.sort(key=lambda p: p["emv"], reverse=True)

    T = {k: sum(p[k] for p in posts) for k in ("views", "likes", "comments", "inter", "emv")}
    pays = [p["pay"] for p in posts]
    T["pay"] = sum(pays) if all(pays) else None
    T["roi"] = roi(T["emv"], T["pay"])
    T["fol"] = sum(c["followers"] for c in creators)

    nets: dict[str, dict[str, Any]] = {}
    for p in posts:
        n = nets.setdefault(p["net"], {"net": p["net"], "name": p["netName"], "views": 0, "inter": 0,
                                        "emv": 0, "creators": set(), "formats": {}})
        n["views"] += p["views"]; n["inter"] += p["inter"]; n["emv"] += p["emv"]
        n["creators"].add(p["creator"])
        n["formats"][p["format"]] = n["formats"].get(p["format"], 0) + 1
    for n in nets.values():
        n["creators"] = len(n["creators"])
        n["er"] = n["inter"] / n["views"]

    return {
        "campaign": {"id": campaign["campaign"]["id"], "name": campaign["campaign"]["name"],
                     "captured_on": capture["captured_on"] if capture else None},
        "values": v,
        "creators": sorted(creators, key=lambda c: c["t"]["emv"], reverse=True),
        "posts": posts,
        "totals": T,
        "networks": list(nets.values()),
    }
