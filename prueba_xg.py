"""
Prueba del xG con partidos ya jugados: ¿predice los goles mejor que la frecuencia de los últimos partidos?

Para cada partido, con lo que se sabía antes: goles esperados del partido según el xG reciente
(lo que genera cada equipo y lo que concede el rival, últimos 8 con xG) → probabilidad Poisson de cada
mercado de goles. Se compara con la frecuencia simple y con la mezcla de las dos (error de Brier).
Escribe datos/xg_prueba.json con el peso que mejor funciona por mercado (lo usa aprender.py).
"""
import json
import math
from collections import defaultdict

from bot import DATOS
from picks import MIN_PARTIDOS, ULTIMOS, evaluador, historial

MERCADOS = {"Goals Over/Under|Over 1.5": ("total", 1.5), "Goals Over/Under|Over 2.5": ("total", 2.5),
            "Goals Over/Under|Over 3.5": ("total", 3.5), "Both Teams Score|Yes": ("ambos", None),
            "Total - Home|Over 0.5": ("local", 0.5), "Total - Away|Over 0.5": ("visit", 0.5),
            "Total - Home|Over 1.5": ("local", 1.5), "Total - Away|Over 1.5": ("visit", 1.5)}
N_XG = 8


def poisson_mas(lam, linea):
    k = int(linea + 0.5)          # más de 1,5 → 2 o más
    return 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(k))


def xg_equipo(partidos, eq):
    """(xG a favor medio, xG en contra medio) de los últimos N_XG partidos con xG."""
    f, c = [], []
    for p in partidos:
        st = p.get("stats") or {}
        ids = list(st)
        if len(ids) != 2 or any((st[i] or {}).get("xg") is None for i in ids):
            continue
        rival = ids[1] if ids[0] == str(eq) else ids[0]
        f.append(st[str(eq)]["xg"])
        c.append(st[rival]["xg"])
        if len(f) >= N_XG:
            break
    return (sum(f) / len(f), sum(c) / len(c)) if len(f) >= 5 else None


def prob_xg(clave, lam_l, lam_v):
    tipo, linea = MERCADOS[clave]
    if tipo == "total":
        return poisson_mas(lam_l + lam_v, linea)
    if tipo == "local":
        return poisson_mas(lam_l, linea)
    if tipo == "visit":
        return poisson_mas(lam_v, linea)
    return poisson_mas(lam_l, 0.5) * poisson_mas(lam_v, 0.5)


def lambdas(antes, loc, vis):
    a, b = xg_equipo(antes.get(loc, []), loc), xg_equipo(antes.get(vis, []), vis)
    if not a or not b:
        return None
    return (a[0] + b[1]) / 2, (b[0] + a[1]) / 2


def main():
    hist = historial()
    partidos = {p["id"]: p for l in hist.values() for p in l}
    filas = defaultdict(list)   # clave -> [(frec, pxg, real)]
    for p in partidos.values():
        antes = {k: [x for x in v if x["fecha"] < p["fecha"]] for k, v in hist.items()}
        loc, vis = p["local"]["id"], p["visitante"]["id"]
        lam = lambdas(antes, loc, vis)
        if not lam:
            continue
        h_loc = [(x, loc) for x in antes.get(loc, [])[:ULTIMOS]]
        h_vis = [(x, vis) for x in antes.get(vis, [])[:ULTIMOS]]
        for clave in MERCADOS:
            m, o = clave.split("|")
            fl, fv = evaluador(m, o, True), evaluador(m, o, False)
            a = [v for v in (fl(x, e) for x, e in h_loc) if v is not None]
            b = [v for v in (fv(x, e) for x, e in h_vis) if v is not None]
            real = fl(p, loc)
            if len(a) < MIN_PARTIDOS or len(b) < MIN_PARTIDOS or real is None:
                continue
            frec = (sum(a) + sum(b)) / (len(a) + len(b))
            filas[clave].append((frec, prob_xg(clave, *lam), 1.0 if real else 0.0))
    salida = {}
    for clave, l in filas.items():
        if len(l) < 60:
            continue
        brier = lambda w: sum(((1 - w) * f + w * x - y) ** 2 for f, x, y in l) / len(l)
        mejor = min((w / 10 for w in range(11)), key=brier)
        salida[clave] = {"n": len(l), "brier_frecuencia": round(brier(0), 4), "brier_xg": round(brier(1), 4),
                         "peso_xg": mejor, "brier_mezcla": round(brier(mejor), 4)}
        print(f"{clave:28} n={len(l):4}  frec {brier(0):.4f}  xG {brier(1):.4f}  mejor peso xG {mejor:.1f} → {brier(mejor):.4f}")
    (DATOS / "xg_prueba.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
