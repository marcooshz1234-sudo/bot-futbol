"""
Contexto del partido (26/10, petición de Marcos): no es lo mismo el 1º contra el penúltimo que el 5º contra el 8º.

Clasificación de cada liga calculada con el calendario guardado (datos/calendario_<liga>.json, sin gastar
API), tal y como estaba ANTES de la fecha del partido (así sirve también para el histórico).

Cada pick cae en un "contexto" según la distancia en la tabla y a qué equipo favorece:
  - pick de un equipo (gana, marca, sus córners, tiros de sus jugadores…):
      mejor_igualado / mejor_lejos / mejor_abismo   → favorece al que va por encima en la tabla
      peor_igualado / peor_lejos / peor_abismo      → favorece al que va por debajo (el "menos favorito")
  - pick de los dos (goles totales, ambos marcan, córners totales…): total_igualado / total_lejos / total_abismo
calibrar_historico.py mide cuánto se acierta de verdad en cada contexto y aprender.py lo aplica.
En copas (Champions, Europa, Conference) no hay tabla comparable: sin contexto.
"""
from functools import lru_cache

from bot import DATOS, leer

LIGAS = (140, 39, 135, 78, 61, 141, 40, 88, 94)
FIN = ("FT", "AET", "PEN")
MIN_JUGADOS = 4          # al principio de temporada la tabla no dice nada


@lru_cache(maxsize=512)
def tabla(liga, antes_de):
    """{equipo_id: posición} con los partidos terminados antes de antes_de ('YYYY-MM-DD'); y nº de equipos."""
    cal = leer(DATOS / f"calendario_{liga}.json", []) or []
    filas = {}
    for x in cal:
        for lado in ("home", "away"):
            filas.setdefault(x["teams"][lado]["id"], [0, 0, 0, 0])     # pts, dg, gf, pj
        if x["fixture"]["status"]["short"] not in FIN or x["fixture"]["date"][:10] >= antes_de:
            continue
        gl, gv = x["goals"]["home"], x["goals"]["away"]
        if gl is None or gv is None:
            continue
        for eq, gf, gc in ((x["teams"]["home"]["id"], gl, gv), (x["teams"]["away"]["id"], gv, gl)):
            f = filas[eq]
            f[0] += 3 if gf > gc else 1 if gf == gc else 0
            f[1] += gf - gc
            f[2] += gf
            f[3] += 1
    if not filas:
        return {}, 0, 0
    orden = sorted(filas, key=lambda e: (-filas[e][0], -filas[e][1], -filas[e][2]))
    jugados = min(f[3] for f in filas.values())
    return {e: i + 1 for i, e in enumerate(orden)}, len(orden), jugados


def posiciones(liga, fecha, loc, vis):
    """(pos_local, pos_visitante, nº equipos) o None."""
    if liga not in LIGAS:
        return None
    pos, n, jugados = tabla(liga, str(fecha)[:10])
    if not n or jugados < MIN_JUGADOS or loc not in pos or vis not in pos:
        return None
    return pos[loc], pos[vis], n


def distancia(dif, n):
    d = abs(dif) / n
    return "igualado" if d <= 0.2 else "lejos" if d <= 0.45 else "abismo"


def de_pick(pos, lado):
    """Contexto de un pick. pos = (pos_local, pos_visitante, n); lado = 'local', 'visitante' o None."""
    if not pos:
        return None
    pl, pv, n = pos
    cat = f"{distancia(pl - pv, n)}_{zona(pl, pv, n)}"   # 01/11 (Marcos): no es lo mismo 5º-6º que 12º-13º
    if lado is None:
        return f"total_{cat}"
    mejor = (pl < pv) if lado == "local" else (pv < pl)
    return f"{'mejor' if mejor else 'peor'}_{cat}"


def zona(pl, pv, n):
    """Parte de la tabla donde se juega el partido (media de las dos posiciones): arriba, medio o abajo."""
    m = (pl + pv) / 2 / n
    return "arriba" if m <= 0.3 else "abajo" if m > 0.7 else "medio"


def sin_zona(ctx):
    return ctx.rsplit("_", 1)[0] if ctx and ctx.count("_") >= 2 else ctx


def texto(pos):
    """«3º vs 18º» para los posts."""
    return f"{pos[0]}º vs {pos[1]}º" if pos else None


# ---------- 01/11 (Marcos): forma de los últimos partidos y jugadores clave ----------
FORMA_N = 5          # últimos partidos para la forma
FORMA_DIF = 4        # diferencia de puntos (en esos 5) para decir que uno llega mucho mejor
CLAVES_N = 3         # jugadores clave por equipo


def puntos(partidos, eq):
    """Puntos en los partidos dados (registros de datos/partidos, recientes primero)."""
    pts = 0
    for p in partidos[:FORMA_N]:
        g = p.get("goles_90") or p.get("goles") or [0, 0]
        mio, suyo = (g[0], g[1]) if p["local"]["id"] == eq else (g[1], g[0])
        pts += 3 if mio > suyo else 1 if mio == suyo else 0
    return pts


def de_forma(h_loc, h_vis, loc, vis, lado):
    """Etiqueta de forma para un pick que favorece a `lado`: mejor / igual / peor (o None si es de los dos)."""
    if lado is None or len(h_loc) < FORMA_N or len(h_vis) < FORMA_N:
        return None
    a, b = puntos(h_loc, loc), puntos(h_vis, vis)
    d = (a - b) if lado == "local" else (b - a)
    return "forma_mejor" if d >= FORMA_DIF else "forma_peor" if d <= -FORMA_DIF else "forma_igual"


def impacto(j):
    """Lo que aporta un jugador en un partido: la nota de la API si la hay; si no, una nota hecha con sus datos."""
    if j.get("nota"):
        return float(j["nota"])
    return 6.0 + (j.get("goles") or 0) + 0.7 * (j.get("asist") or 0) + 0.25 * (j.get("a_puerta") or 0) \
        + 0.05 * (j.get("tiros") or 0) + 0.1 * (j.get("faltas_r") or 0)


def claves(eq, partidos, n=CLAVES_N):
    """[(id, nombre)] de los n jugadores clave: titulares habituales (60'+ en 4 de los últimos 8) con mejor nota media."""
    from collections import defaultdict
    reg, nombre = defaultdict(list), {}
    for p in partidos[:8]:
        for j in (p.get("jugadores") or {}).get(str(eq)) or []:
            if (j.get("min") or 0) >= 60:
                reg[j["id"]].append(impacto(j))
                nombre.setdefault(j["id"], j["nombre"])
    hab = [(sum(v) / len(v), pid) for pid, v in reg.items() if len(v) >= 4]
    return [(pid, nombre[pid]) for _, pid in sorted(hab, reverse=True)[:n]]


def de_bajas(fuera_loc, fuera_vis, lado):
    """Etiqueta de bajas de jugadores clave para un pick que favorece a `lado` (nº de claves que faltan)."""
    if lado is None:
        return None
    mio, suyo = (fuera_loc, fuera_vis) if lado == "local" else (fuera_vis, fuera_loc)
    if mio and not suyo:
        return "bajas_mias"
    if suyo and not mio:
        return "bajas_rival"
    return "bajas_ambos" if mio else "bajas_ninguno"
