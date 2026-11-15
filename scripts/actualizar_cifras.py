#!/usr/bin/env python3
"""actualizar_cifras.py: crea la captura nueva de una campaña a partir de las lecturas del día.

Uso (desde la raíz del repo):
    python scripts/actualizar_cifras.py 2026-10 lecturas.json            # escribe la captura
    python scripts/actualizar_cifras.py 2026-10 lecturas.json --prueba   # solo muestra los cambios

Después: python scripts/build_reporte.py y python -m unittest discover tests (ver docs/RUNBOOK.md).

Reglas validadas por Kevin (13-nov-2026). No se cambian sin su aprobación:
1. Las campañas no se congelan: se actualizan aunque el cliente las haya aprobado.
2. Una cifra de una publicación SOLO se actualiza si SUBE. Si la lectura nueva es menor, se conserva
   la anterior y se informa (Apify, la API y la pantalla de Instagram pueden dar cifras distintas).
3. Instagram muestra los me gusta redondeados desde ~1.000 («4.9K»). La cifra redondeada se usa solo
   si es MAYOR que la anterior, y queda marcada como aproximada: el reporte la muestra con «≈».
4. Los seguidores sí reflejan la cuenta hoy (pueden bajar).
5. Nada se borra: las publicaciones que no se leyeron conservan su última cifra.

Formato de lecturas.json (lo escribe Claude al leer las redes; ver docs/RUNBOOK.md):
{
  "fecha": "2026-11-13",
  "fuente": "Chrome del OptiPlex (perfil kevinromeroe) + Apify (vistas de Instagram)",
  "publicaciones": {
    "DeMoyRYOinH": {"likes": "4.9K", "comments": "42", "shares": "363", "views": 81248},
    "7695240858781715718": {"views": 284700, "likes": 61900, "comments": 311, "shares": 901, "saves": 3817}
  },
  "seguidores": {"estebango__": 510234}
}
Las cifras pueden venir como número o como el texto que muestra la red («4.9K», «1,234», «85.9K»).
Vacío o null = la red no mostró el número: no se toca.
"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.util.config import CAPTURES_DIR  # noqa: E402

CAMPOS = ("views", "likes", "comments", "shares", "saves")


def cifra(v):
    """Devuelve (número, es_aproximado) o None. «4.9K» → (4900, True); «1,234» → (1234, False)."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v), False
    t = str(v).strip().replace(" ", " ")
    if not t:
        return None
    m = re.fullmatch(r"([\d.,]+)\s*(K|M|mil|mill\.?|millones)?", t, re.I)
    if not m:
        raise ValueError(f"Cifra no reconocida: {v!r}")
    num, suf = m.group(1), (m.group(2) or "").lower()
    if suf:
        base = float(num.replace(",", "."))
        mult = 1_000 if suf in ("k", "mil") else 1_000_000
        return int(round(base * mult)), True
    return int(num.replace(",", "").replace(".", "")), False


def base_config(campana: str) -> dict:
    """Publicaciones de config/campanas/<id>.yaml: fecha y cifras iniciales de las que aún no están en la captura."""
    import yaml
    cfg = yaml.safe_load((ROOT / "config" / "campanas" / f"{campana}.yaml").read_text(encoding="utf-8"))
    out = {}
    for c in cfg.get("creators", []):
        for p in c.get("publications", []):
            m = p.get("metrics") or {}
            out[str(p["id"])] = {"posted_on": str(p["posted_on"]), **{k: m[k] for k in CAMPOS if k in m}}
    return out


def aplicar(captura: dict, lecturas: dict, config: dict | None = None) -> tuple[dict, list[str]]:
    """Aplica las reglas a una copia de la captura. Devuelve (captura nueva, cambios legibles).

    config: publicaciones de la configuración (base_config) para las que aún no están en la captura.
    """
    cap = copy.deepcopy(captura)
    cambios = []
    pubs = cap.setdefault("publications", {})
    for pid, med in (lecturas.get("publicaciones") or {}).items():
        if str(pid) not in pubs and config and str(pid) in config:
            pubs[str(pid)] = copy.deepcopy(config[str(pid)])
        actual = pubs.setdefault(str(pid), {})
        aprox = set(actual.get("aprox", []))
        for k in CAMPOS:
            c = cifra(med.get(k))
            if c is None:
                continue
            v, es_aprox = c
            antes = actual.get(k)
            if antes is None or v > antes:
                actual[k] = v
                aprox.discard(k)
                if es_aprox:
                    aprox.add(k)
                cambios.append(f"{pid} {k}: {antes} → {'≈' if es_aprox else ''}{v}")
            elif v < antes:
                cambios.append(f"{pid} {k}: se conserva {antes} (lectura menor: {v})")
        if aprox:
            actual["aprox"] = sorted(aprox)
        else:
            actual.pop("aprox", None)
    creadores = cap.setdefault("creators", {})
    for h, f in (lecturas.get("seguidores") or {}).items():
        c = cifra(f)
        if c is None:
            continue
        if h not in creadores:  # creador sin perfil en la captura (p. ej. solo historias): no se crea nada nuevo
            cambios.append(f"@{h} seguidores: no está en la captura, no se agrega")
            continue
        antes = creadores[h].get("followers")
        if antes != c[0]:
            cambios.append(f"@{h} seguidores: {antes} → {c[0]}")
        creadores[h]["followers"] = c[0]
    return cap, cambios


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("campana")
    ap.add_argument("lecturas")
    ap.add_argument("--prueba", action="store_true", help="no escribe nada")
    a = ap.parse_args()
    lect = json.loads(Path(a.lecturas).read_text(encoding="utf-8"))
    fecha = lect["fecha"]
    previas = sorted(p for p in (CAPTURES_DIR / a.campana).glob("*.json") if p.stem < fecha)
    if not previas:
        sys.exit("No hay captura previa: la primera captura se arma a mano (ver docs/RUNBOOK.md).")
    base = json.loads(previas[-1].read_text(encoding="utf-8"))  # la última ANTES de la fecha de las lecturas
    print(f"Base: {previas[-1].name}")
    cfg = base_config(a.campana)
    desconocidas = [p for p in (lect.get("publicaciones") or {}) if str(p) not in cfg]
    if desconocidas:
        sys.exit(f"Publicaciones que no están en config/campanas/{a.campana}.yaml: {desconocidas}. "
                 "Una publicación nueva se agrega primero a la configuración (ver docs/RUNBOOK.md).")
    cap, cambios = aplicar(base, lect, cfg)
    cap["captured_on"] = fecha
    cap["source"] = lect.get("fuente", cap.get("source"))
    cap["notes"] = list(base.get("notes", [])) + [
        f"{fecha}: actualización con scripts/actualizar_cifras.py (solo suben; «≈» = cifra redondeada de Instagram)."]
    print("\n".join(cambios) or "Sin cambios.")
    if a.prueba:
        return
    out = CAPTURES_DIR / a.campana / f"{fecha}.json"
    out.write_text(json.dumps(cap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Captura escrita: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
