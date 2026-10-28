"""
28/10 (Marcos): «que aprenda qué partidos tienen más probabilidad de gol / qué tipo de partido es».
Caso real: el bot puso «más de 1,5 goles» en Parma–Udinese y acabó 0-0.

1. TIPO DE PARTIDO (datos/goles_tipo.json): con todos los partidos ya jugados (datos/partidos), mira cómo
   llegaba cada equipo (goles a favor y en contra en sus últimos 10 partidos, solo con lo que se sabía antes)
   y cuántos goles se esperaban. Lo agrupa por «tramo de goles esperados» y por liga y apunta lo que pasó
   de verdad: +1,5, +2,5, ambos marcan, marca el local, marca el visitante, gol en la 1ª parte.
   Así sabe, por ejemplo, que en la Serie A un partido de equipos que marcan poco sale +1,5 mucho menos.
2. CUOTAS DE ANTES (datos/goles_previos.json): guarda los goles esperados según bet365 de cada partido antes
   de empezar (no se guardaban); cuando haya bastantes terminados, aprende también por ese tramo.
3. prob_goles(pick, ex): probabilidad de un pick de goles = media entre lo aprendido del bot, lo que dice
   bet365 (modelo de goles con sus cuotas) y lo que pasó en partidos del mismo tipo.
"""
import json
import math
from collections import defaultdict
from datetime import datetime

from bot import DATOS, EXTRA, PARTIDOS, leer

TIPO = DATOS / "goles_tipo.json"
PREVIOS = DATOS / "goles_previos.json"
ULTIMOS, MIN_PREVIOS = 10, 5
TRAMOS = (2.2, 2.6, 3.0, 3.4)          # goles esperados en el partido
TRAMOS_EQ = (0.9, 1.2, 1.5, 1.8)       # goles esperados de un equipo
K = 40                                 # con pocos partidos, la liga/tramo pesa poco frente al total
FT = ("FT", "AET", "PEN")
SALIDAS = ("o15", "o25", "btts", "marca_l", "marca_v", "gol_1p")


def tramo(x, cortes=TRAMOS):
    for i, c in enumerate(cortes):
        if x < c:
            return f"<{c}"
    return f"≥{cortes[-1]}"


def _goles_90(p):
    import picks as P
    q = P.a_90(p) or p
    g = q.get("goles") or [None, None]
    return None if None in g else g


def forma(previos, eq):
    """(goles a favor, en contra) por partido en los últimos partidos del equipo, o None."""
    gf = gc = n = 0
    for p, g in previos:
        if p["local"]["id"] == eq:
            gf, gc = gf + g[0], gc + g[1]
        else:
            gf, gc = gf + g[1], gc + g[0]
        n += 1
    return (gf / n, gc / n) if n >= MIN_PREVIOS else None


def esperado(fl, fv):
    """Goles esperados de local y visitante con la forma de los dos."""
    return (fl[0] + fv[1]) / 2, (fv[0] + fl[1]) / 2


def resultados(g, d):
    h1 = d.get("descanso") or [None, None]
    r = {"o15": sum(g) >= 2, "o25": sum(g) >= 3, "btts": min(g) > 0, "marca_l": g[0] > 0, "marca_v": g[1] > 0}
    if None not in h1:
        r["gol_1p"] = sum(h1) > 0
    return r


def aprender():
    partidos = []
    for f in PARTIDOS.glob("*.json"):
        d = leer(f)
        if d and d.get("estado") in FT and d.get("local") and d.get("visitante"):
            g = _goles_90(d)
            if g:
                partidos.append((d, g))
    partidos.sort(key=lambda x: x[0]["fecha"])
    hist = defaultdict(list)
    cuentas = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    previos_bet = leer(PREVIOS, {}) or {}
    for d, g in partidos:
        hl, hv = d["local"]["id"], d["visitante"]["id"]
        fl, fv = forma(hist[hl][-ULTIMOS:], hl), forma(hist[hv][-ULTIMOS:], hv)
        if fl and fv:
            el, ev = esperado(fl, fv)
            liga = str(d.get("liga"))
            claves = ["todo", f"tramo|{tramo(el + ev)}", f"liga|{liga}", f"liga_tramo|{liga}|{tramo(el + ev)}",
                      f"local|{tramo(el, TRAMOS_EQ)}", f"visit|{tramo(ev, TRAMOS_EQ)}"]
            pb = previos_bet.get(str(d["id"]))
            if pb:
                claves.append(f"bet365|{tramo(pb['l'] + pb['v'])}")
            for k, v in resultados(g, d).items():
                for c in claves:
                    cuentas[c][k][0] += 1
                    cuentas[c][k][1] += int(v)
        hist[hl].append((d, g))
        hist[hv].append((d, g))
    tabla = {c: {k: {"n": n, "real": round(s / n, 3)} for k, (n, s) in v.items()} for c, v in cuentas.items()}
    salida = {"generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "partidos": len(partidos), "tabla": tabla}
    TIPO.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return salida


def guardar_previos():
    """Goles esperados según bet365 de los partidos que aún no han empezado (para aprender después)."""
    import modelo_goles as M
    prev = leer(PREVIOS, {}) or {}
    nuevos = 0
    for f in EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido") or {}
        try:
            if pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
                continue
        except (KeyError, TypeError):
            continue
        lam = M.lambdas(f.stem)
        if lam:
            prev[f.stem] = {"l": round(lam[0], 2), "v": round(lam[1], 2), "liga": pa["league"]["id"]}
            nuevos += 1
    PREVIOS.write_text(json.dumps(prev, ensure_ascii=False) + "\n", encoding="utf-8")
    return nuevos


# ------------------------------------------------------------------ uso al elegir picks
_T = {}


def _tabla():
    if "t" not in _T:
        _T["t"] = (leer(TIPO, {}) or {}).get("tabla") or {}
    return _T["t"]


def que_mide(m, o):
    """Qué resultado de la tabla corresponde a un pick de goles (o None si no es de goles)."""
    o = str(o)
    if m == "Goals Over/Under" and o == "Over 1.5":
        return "o15"
    if m == "Goals Over/Under" and o == "Over 2.5":
        return "o25"
    if m == "Both Teams Score" and o == "Yes":
        return "btts"
    if m == "Total - Home" and o == "Over 0.5":
        return "marca_l"
    if m == "Total - Away" and o == "Over 0.5":
        return "marca_v"
    if m == "Goals Over/Under First Half" and o == "Over 0.5":
        return "gol_1p"
    return None


def prob_tipo(clave, el, ev, liga):
    """Lo que pasó en partidos del mismo tipo: tramo de goles esperados, afinado con la liga (si hay casos)."""
    t = _tabla()
    total = (t.get("todo") or {}).get(clave)
    if not total:
        return None
    base = total["real"]
    if clave in ("marca_l", "marca_v"):
        cand = [t.get(f"{'local' if clave == 'marca_l' else 'visit'}|{tramo(el if clave == 'marca_l' else ev, TRAMOS_EQ)}")]
    else:
        cand = [t.get(f"tramo|{tramo(el + ev)}")]
    cand.append(t.get(f"liga_tramo|{liga}|{tramo(el + ev)}"))
    for c in cand:   # cada nivel corrige al anterior según los casos que tenga
        x = (c or {}).get(clave)
        if x:
            base += (x["real"] - base) * x["n"] / (x["n"] + K)
    return base


def prob_bet365(clave, lam):
    """Probabilidad según las cuotas de bet365 (goles de cada equipo como Poisson)."""
    if not lam:
        return None
    lh, la = lam

    def p0(x):
        return math.exp(-x)
    if clave == "o15":
        t = lh + la
        return 1 - math.exp(-t) * (1 + t)
    if clave == "o25":
        t = lh + la
        return 1 - math.exp(-t) * (1 + t + t * t / 2)
    if clave == "btts":
        return (1 - p0(lh)) * (1 - p0(la))
    if clave == "marca_l":
        return 1 - p0(lh)
    if clave == "marca_v":
        return 1 - p0(la)
    if clave == "gol_1p":
        return 1 - math.exp(-0.45 * (lh + la))   # ~45 % de los goles caen en la 1ª parte
    return None


def prob_goles(p, hist, lam, loc=None, vis=None):
    """Media entre lo aprendido por el bot, bet365 y los partidos del mismo tipo. None si no es de goles."""
    clave = que_mide(p["mercado"], p["opcion"])
    if not clave:
        return None
    partes = [p.get("prob_aprendida") or p.get("frecuencia")]
    pb = prob_bet365(clave, lam)
    if pb is not None:
        partes.append(pb)
    fl = fv = None
    if loc and vis and hist:
        fl = forma_hist(hist.get(loc, [])[:ULTIMOS], loc)
        fv = forma_hist(hist.get(vis, [])[:ULTIMOS], vis)
    pt = None
    if fl and fv:
        el, ev = esperado(fl, fv)
        pt = prob_tipo(clave, el, ev, p.get("liga_id"))
        if pt is not None:
            partes.append(pt)
    partes = [x for x in partes if x is not None]
    return {"prob": sum(partes) / len(partes), "bet365": pb, "tipo": pt}


def forma_hist(lista, eq):
    """Igual que forma() pero con el historial que usa picks.py (partidos de datos/partidos, el más reciente primero)."""
    previos = []
    for p in lista:
        g = _goles_90(p)
        if g:
            previos.append((p, g))
    return forma(previos, eq)


def main():
    s = aprender()
    n = guardar_previos()
    t = s["tabla"]
    print(f"Tipo de partido: {s['partidos']} partidos · +1,5 en total {t['todo']['o15']['real']:.0%} · "
          + " · ".join(f"{k.split('|')[1]}: {v['o15']['real']:.0%} ({v['o15']['n']})"
                       for k, v in sorted(t.items()) if k.startswith("tramo|")) + f" · {n} partidos con cuotas guardados")


if __name__ == "__main__":
    main()
