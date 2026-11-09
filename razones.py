"""
09/11 (Marcos, como TipsAnalistas): 2-3 razones cortas y reales para el pick seguro del día.
Todo sale de nuestros datos: clasificación (calendario de la liga), forma de los últimos 5, cómo le va en casa o
fuera, goles por partido y bajas. Nunca se inventa nada: si un dato no está, esa razón no sale.
"""
from bot import DATOS, leer


def tabla(liga_id):
    """{team_id: (puesto, puntos, jugados)} con los partidos terminados del calendario de la liga."""
    cal = leer(DATOS / f"calendario_{liga_id}.json", []) or []
    pts, pj = {}, {}
    for f in cal:
        if f.get("fixture", {}).get("status", {}).get("short") not in ("FT", "AET", "PEN"):
            continue
        r = f.get("league", {}).get("round", "")
        if "Regular Season" not in r and "Jornada" not in r:
            continue
        g = f.get("goals") or {}
        gl, gv = g.get("home"), g.get("away")
        if gl is None or gv is None:
            continue
        l, v = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
        for t in (l, v):
            pts.setdefault(t, 0)
            pj[t] = pj.get(t, 0) + 1
        if gl > gv:
            pts[l] += 3
        elif gv > gl:
            pts[v] += 3
        else:
            pts[l] += 1
            pts[v] += 1
    orden = sorted(pts, key=lambda t: -pts[t])
    return {t: (i + 1, pts[t], pj[t]) for i, t in enumerate(orden)}, len(orden)


def ultimos(hist, eq, n=5, sitio=None):
    """[(gf, gc)] de los últimos n partidos (sitio: 'casa' / 'fuera' / None)."""
    out = []
    for p in hist.get(eq, []):
        g = p.get("goles_90") or p.get("goles") or [None, None]
        if None in g or p.get("estado") not in ("FT", "AET", "PEN"):
            continue
        en_casa = p["local"]["id"] == eq
        if sitio == "casa" and not en_casa or sitio == "fuera" and en_casa:
            continue
        out.append((g[0], g[1]) if en_casa else (g[1], g[0]))
        if len(out) >= n:
            break
    return out


def vde(res):
    return sum(a > b for a, b in res), sum(a == b for a, b in res), sum(a < b for a, b in res)


def razones(p, hist, ex=None, maximo=3):
    """p: pick del pool (con partido_id, liga_id, local/visitante, mercado/opcion). → lista de frases."""
    copa = []
    try:   # 09/11: Copa (categoría, arranque, campo, aplazamientos) → copa_contexto.py
        import copa_contexto
        copa = copa_contexto.razones(p["partido_id"])
    except Exception:
        pass
    try:   # 09/11: hechos de los periódicos (campo, aplazamiento, entrenador, crisis)
        import noticias
        copa += noticias.razones(p["partido_id"])
    except Exception:
        pass
    pa = (ex or leer(DATOS / "proximos" / f"{p['partido_id']}.json", {}) or {}).get("partido") or {}
    t = pa.get("teams") or {}
    il, iv = (t.get("home") or {}).get("id"), (t.get("away") or {}).get("id")
    if not il or not iv:
        return [f for _, f in sorted(copa, key=lambda x: -x[0])][:maximo]
    L, V = p["local"], p["visitante"]
    favor_local = p.get("opcion") in ("Home", "Home/Draw", "1X") or p["texto"].startswith(f"Gana el {L}") \
        or p["texto"].startswith(f"Gana {L}") or f"{L} o empate" in p["texto"]
    favor_visit = p.get("opcion") in ("Away", "Draw/Away", "X2") or p["texto"].startswith(f"Gana el {V}") \
        or p["texto"].startswith(f"Gana {V}") or f"{V} o empate" in p["texto"]
    cand = []
    try:
        tb, n = tabla(p.get("liga_id"))
        if il in tb and iv in tb and n >= 10:
            (pl, ptl, _), (pv, ptv, _) = tb[il], tb[iv]
            if abs(pl - pv) >= 5:
                arriba, abajo = (L, V) if pl < pv else (V, L)
                pa_, pb_ = min(pl, pv), max(pl, pv)
                cand.append((3, f"El {arriba} va {pa_}º y el {abajo} {pb_}º en la liga."))
    except Exception:
        pass
    for eq, nombre, sitio in ((il, L, "casa"), (iv, V, "fuera")):
        res = ultimos(hist, eq, 6, sitio)
        if len(res) >= 4:
            v, e, d = vde(res)
            lugar = "en casa" if sitio == "casa" else "fuera"
            if (favor_local and eq == il or favor_visit and eq == iv) and d == 0:
                cand.append((4, f"El {nombre} no ha perdido {lugar} en sus últimos {len(res)} partidos ({v}V {e}E)."))
            elif (favor_local and eq == iv or favor_visit and eq == il) and v == 0:
                cand.append((4, f"El {nombre} no ha ganado {lugar} en sus últimos {len(res)} partidos."))
    for eq, nombre in ((il, L), (iv, V)):
        res = ultimos(hist, eq, 5)
        if len(res) == 5:
            v = vde(res)[0]
            bueno = favor_local and eq == il or favor_visit and eq == iv
            if bueno and v >= 3:
                cand.append((2, f"El {nombre} ha ganado {v} de sus últimos 5 partidos."))
            if not bueno and (favor_local or favor_visit) and v <= 1:
                cand.append((2, f"El {nombre} {'no ha ganado ninguno' if v == 0 else 'solo ha ganado 1'} de sus últimos 5."))
    if p.get("tipo") == "goles" or "goles" in p["texto"].lower() or "marcan" in p["texto"].lower():
        for eq, nombre in ((il, L), (iv, V)):
            res = ultimos(hist, eq, 8)
            if len(res) >= 6:
                media = sum(a + b for a, b in res) / len(res)
                m = str(round(media, 1)).replace(".", ",")
                cand.append((3, f"Los partidos del {nombre} llevan {m} goles de media (últimos {len(res)})."))
    les = (ex or {}).get("lesiones") or []
    rival = iv if favor_local else il if favor_visit else None
    if rival:
        bajas = [x for x in les if (x.get("equipo_id") or x.get("team_id")) == rival]
        if len(bajas) >= 3:
            cand.append((1, f"El {V if rival == iv else L} tiene {len(bajas)} bajas."))
    cand += copa
    cand.sort(key=lambda x: -x[0])
    vistas, out = set(), []
    for _, f in cand:
        if f not in vistas:
            vistas.add(f)
            out.append(f)
    return out[:maximo]
