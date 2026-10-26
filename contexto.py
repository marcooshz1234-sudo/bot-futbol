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
    cat = distancia(pl - pv, n)
    if lado is None:
        return f"total_{cat}"
    mejor = (pl < pv) if lado == "local" else (pv < pl)
    return f"{'mejor' if mejor else 'peor'}_{cat}"


def texto(pos):
    """«3º vs 18º» para los posts."""
    return f"{pos[0]}º vs {pos[1]}º" if pos else None
