"""
Modelo de goles (Poisson) para calcular la cuota real de «Crear apuesta» de bet365 (28/10).

Las patas de un mismo partido no son independientes: bet365 calcula la probabilidad de que pasen TODAS a la vez.
- Las que van juntas (más de 2,5 + ambos marcan) pagan MENOS que multiplicando.
- Las que van en contra (gana el Milan + Bologna marca) pagan MÁS (Milan 28/10: ~8,6 multiplicando, 10,50 en bet365).

Cómo:
1. Con las cuotas de bet365 del partido (1X2 y más/menos de 2,5, sin el margen) se estiman los goles esperados de
   cada equipo (λ local, λ visitante). 1ª parte = 45 % de los goles, 2ª = 55 %.
2. Con eso, la probabilidad de cada marcador al descanso y al final.
3. Para las patas de goles y resultado se suma la probabilidad de los marcadores que las cumplen TODAS a la vez,
   y se compara con lo que daría multiplicar sus probabilidades sueltas: ese cociente es el ajuste de la cuota.
Las patas que no dependen solo del marcador (tarjetas, córners, tiros, jugadores) siguen con los factores de
combis_dia.pareja().
"""
import math
from functools import lru_cache

from bot import EXTRA, leer

MAX_GOLES = 7          # por parte y equipo
PARTE_1 = 0.45


def _poisson(lam):
    return [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(MAX_GOLES + 1)]


def _sin_margen(cuotas):
    inv = [1 / c for c in cuotas]
    s = sum(inv)
    return [x / s for x in inv]


def _cuotas(pid):
    ex = leer(EXTRA / f"{pid}.json") or {}
    c = ex.get("cuotas") or {}
    ids = ((ex.get("partido") or {}).get("teams") or {})
    return c, ids


def _de(c, mercado, opcion):
    for o, v in c.get(mercado, []):
        if o == opcion:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
    return None


@lru_cache(maxsize=256)
def lambdas(pid):
    """(λ local, λ visitante) que mejor encajan con el 1X2 y el más/menos de 2,5 de bet365; None si faltan."""
    c, _ = _cuotas(pid)
    x = [_de(c, "Match Winner", o) for o in ("Home", "Draw", "Away")]
    ou = [_de(c, "Goals Over/Under", o) for o in ("Over 2.5", "Under 2.5")]
    if None in x:
        return None
    p1, px, p2 = _sin_margen(x)
    pover = _sin_margen(ou)[0] if None not in ou else None
    mejor = None
    pasos = [0.15 + 0.05 * i for i in range(78)]   # 0,15 … 4,0 goles
    tabla = {l: _poisson_total(l) for l in pasos}
    for lh in pasos:
        ph = tabla[lh]
        for la in pasos:
            pa = tabla[la]
            w = d = 0.0
            for i, a in enumerate(ph):
                for j, b in enumerate(pa):
                    if i > j:
                        w += a * b
                    elif i == j:
                        d += a * b
            l2 = 1 - w - d
            err = (w - p1) ** 2 + (l2 - p2) ** 2 + (d - px) ** 2
            if pover is not None:
                menos = sum(ph[i] * pa[j] for i in range(3) for j in range(3 - i))
                err += (1 - menos - pover) ** 2
            if mejor is None or err < mejor[0]:
                mejor = (err, lh, la)
    return mejor[1], mejor[2]


def _poisson_total(lam):
    return [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(2 * MAX_GOLES + 1)]


@lru_cache(maxsize=4096)
def _modelable(mercado, opcion):
    import picks as P
    f = P.evaluador(mercado, opcion, True)
    if not f:
        return False
    prueba = {"local": {"id": 1}, "visitante": {"id": 2}, "goles": [2, 1], "descanso": [1, 0], "eventos": [],
              "stats": {}, "estado": "FT"}
    try:
        return f(prueba, 1) is not None
    except Exception:
        return False


def modelable(p):
    """¿La pata depende solo del marcador (al descanso y al final)?"""
    if p.get("tipo") == "jugador" or p.get("jugador"):
        return False
    return _modelable(p["mercado"], str(p["opcion"]))


@lru_cache(maxsize=256)
def _escenarios(pid):
    """Marcadores posibles (descanso y final) con su probabilidad, para el partido pid."""
    lam = lambdas(pid)
    if not lam:
        return None
    h1, a1 = _poisson(lam[0] * PARTE_1), _poisson(lam[1] * PARTE_1)
    h2, a2 = _poisson(lam[0] * (1 - PARTE_1)), _poisson(lam[1] * (1 - PARTE_1))
    salida = []
    for i in range(MAX_GOLES + 1):
        for j in range(MAX_GOLES + 1):
            for k in range(MAX_GOLES + 1):
                for m in range(MAX_GOLES + 1):
                    pr = h1[i] * a1[j] * h2[k] * a2[m]
                    if pr >= 1e-6:
                        salida.append((pr, (i, j), (i + k, j + m)))
    return salida


@lru_cache(maxsize=8192)
def _cumple(pid, mercado, opcion):
    """Lista de True/False: si la pata se cumple en cada escenario de _escenarios(pid)."""
    import picks as P
    f = P.evaluador(mercado, opcion, True)
    partido = {"local": {"id": 1}, "visitante": {"id": 2}, "eventos": [], "stats": {}, "estado": "FT"}
    res = []
    for _, d, g in _escenarios(pid):
        partido["descanso"], partido["goles"] = list(d), list(g)
        res.append(bool(f(partido, 1)))
    return tuple(res)


@lru_cache(maxsize=16384)
def _ajuste(pid, claves):
    esc = _escenarios(pid)
    if not esc:
        return None
    vect = [_cumple(pid, m, o) for m, o in claves]
    sueltas = [sum(pr for (pr, _, _), ok in zip(esc, v) if ok) for v in vect]
    juntas = sum(pr for n, (pr, _, _) in enumerate(esc) if all(v[n] for v in vect))
    producto = math.prod(sueltas)
    if producto <= 0 or juntas <= 0:
        return None
    # la cuota va al revés que la probabilidad: si juntas pasan menos de lo que daría multiplicar, paga más
    return producto / juntas


def ajuste(patas):
    """Cociente producto de P(cada una) / P(todas a la vez) (multiplica a la cuota) para patas de goles/resultado del mismo partido.
    None si no se puede calcular (sin cuotas del partido o patas que no dependen del marcador)."""
    if len(patas) < 2 or not all(modelable(p) for p in patas) or patas[0].get("partido_id") is None:
        return None
    claves = tuple(sorted((p["mercado"], str(p["opcion"])) for p in patas))
    return _ajuste(str(patas[0]["partido_id"]), claves)
