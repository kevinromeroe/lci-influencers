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
  inversión       = payment_cop de la publicación, o valor del talento ÷ sus salidas
  ROI             = (EMV − inversión) ÷ inversión        (solo con pago)
  CPV / CPE       = inversión ÷ reproducciones / interacciones
  frente a su contenido = reproducciones del reel de LCI ÷ mediana de
                    sus otros reels recientes no fijados
"""
from __future__ import annotations

import copy
import re
from datetime import date
from statistics import median
from typing import Any

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
NETWORKS = {"ig": "Instagram", "fb": "Facebook", "tt": "TikTok", "yt": "YouTube"}


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


def ratio(a: float | None, b: float) -> float | None:
    return a / b if a and b else None


def _publication(p: dict[str, Any], v: dict[str, int], per_action: int | None) -> dict[str, Any]:
    m = p["metrics"]
    pay = p.get("payment_cop") or per_action
    inter = m.get("likes", 0) + m.get("comments", 0)
    value = emv(m, v)
    return {
        "id": p["id"], "net": p["network"], "netName": NETWORKS[p["network"]],
        "format": p["format"], "date": fecha_larga(p["posted_on"]), "url": p["url"],
        "type": p["type"], "pay": pay, "source": p.get("source"),
        "views": m["views"], "likes": m.get("likes", 0), "comments": m.get("comments", 0),
        "shares": m.get("shares", 0), "saves": m.get("saves", 0), "clicks": m.get("link_clicks", 0),
        "inter": inter, "er": inter / m["views"], "emv": value, "aprox": p.get("aprox", []),
        "roi": roi(value, pay), "cpv": ratio(pay, m["views"]), "cpe": ratio(pay, inter),
    }


def _creator(c: dict[str, Any], v: dict[str, int]) -> dict[str, Any]:
    actions = c.get("actions") or len(c["publications"])
    per_action = round(c["value_cop"] / actions) if c.get("value_cop") else None
    # Publicaciones con la misma clave `salida` cuentan como una sola salida y se reparten su valor.
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in c["publications"]:
        groups.setdefault(str(p.get("salida") or p["id"]), []).append(p)
    share: dict[str, int | None] = {}
    for g in groups.values():
        q, r = divmod(per_action, len(g)) if per_action else (None, 0)
        for i, p in enumerate(g):
            share[p["id"]] = q + (1 if i < r else 0) if q is not None else None
    pubs = [_publication(p, v, share[p["id"]]) for p in c["publications"]]
    done = len(groups)
    pending = actions - done
    t = {k: sum(p[k] for p in pubs) for k in ("views", "likes", "comments", "inter", "emv", "clicks")}
    t["aprox"] = sorted({a for p in pubs for a in p.get("aprox", [])})
    pays = [p["pay"] for p in pubs]
    t["pay"] = sum(pays) if all(pays) else None

    # Comparación con sus reels: solo si hay un reel de LCI en su ventana (las historias no tienen historial público)
    base = c.get("baseline") or []
    lci = next((i for i, r in enumerate(base) if r.get("lci")), None)
    med = idx = None
    if lci is not None:
        others = [r["views"] for i, r in enumerate(base) if i != lci and not r.get("pinned")]
        med = median(others)
        idx = base[lci]["views"] / med
    talk = c.get("talk")
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", c["handle"].lower()).strip("-"), "handle": c["handle"], "name": c["name"],
        "summary": c.get("summary", True),
        "niche": c["niche"], "followers": c["followers"], "avatar": c.get("avatar"),
        "posts": pubs, "t": t, "nets": list(dict.fromkeys(p["netName"] for p in pubs)),
        "er": t["inter"] / t["views"], "reach": t["views"] / c["followers"],
        "roi": roi(t["emv"], t["pay"]), "cpv": ratio(t["pay"], t["views"]), "cpe": ratio(t["pay"], t["inter"]),
        "value": c.get("value_cop"), "actions": actions, "perAction": per_action, "done": done,
        "roiNote": (f"aún falta{'n' if pending > 1 else ''} {pending} "
                    f"{'acciones' if pending > 1 else 'acción'} por validar") if pending > 0 else None,
        "reels": [[r["views"], fecha_corta(r.get("posted_on"))] for r in base],
        "lci": lci, "marks": {str(i): r["mark"] for i, r in enumerate(base) if r.get("mark")},
        "med": med, "idx": idx,
        "isMin": lci is not None and base[lci]["views"] == min(r["views"] for r in base),
        "why": c.get("why", []), "cause": c.get("cause", ""), "notes": c.get("notes", []),
        "talk": {k: talk[k] for k in ("read", "pos", "neu", "neg", "note")} if talk else None,
        "talkLine": talk["line"] if talk else None, "top": talk["top"] if talk else [],
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
                p["aprox"] = list(m.get("aprox", []))
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

    # Solo los influencers del presupuesto de la campaña suman al resumen; los demás quedan en su pestaña.
    inside = [c for c in creators if c["summary"]]
    posts = [dict(p, creator=c["id"]) for c in inside for p in c["posts"]]
    posts.sort(key=lambda p: p["emv"], reverse=True)

    T = {k: sum(p[k] for p in posts) for k in ("views", "likes", "comments", "inter", "emv")}
    T["aprox"] = sorted({a for p in posts for a in p.get("aprox", [])})
    pays = [p["pay"] for p in posts]
    T["pay"] = sum(pays) if all(pays) else None
    T["roi"] = roi(T["emv"], T["pay"])
    T["cpv"], T["cpe"] = ratio(T["pay"], T["views"]), ratio(T["pay"], T["inter"])
    budget = campaign["campaign"].get("budget") or {}
    T["budget"], T["budgetActions"] = budget.get("investment_cop"), budget.get("actions")
    T["done"] = sum(c["done"] for c in inside)
    T["fol"] = sum(c["followers"] for c in inside)

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
        "creators": sorted(creators, key=lambda c: (not c["summary"], -c["t"]["emv"])),
        "posts": posts,
        "totals": T,
        "networks": list(nets.values()),
    }
