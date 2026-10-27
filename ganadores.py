"""
«Quién gana hoy» (27/10, idea de Marcos): de todos los partidos del día, los equipos que según NUESTROS
datos ganan, sin mirar la cuota. Formato de lista como los que más gustan en Threads.

Probabilidad de ganar = media de dos modelos + la tabla:
  - forma: % de victorias del equipo y de derrotas del rival en los últimos 10
  - xG: Poisson con los goles esperados de los dos (con un poco de ventaja para el que juega en casa)
  - tabla: un empujón al que va mejor clasificado (contexto.py)
Prueba con 509 partidos ya jugados (solo con lo que se sabía antes de cada uno):
  umbral 55 % → 62 % de aciertos · 60 % → 72 % · 65 % → 77 %
Se publican los que pasan del 60 %, de más a menos seguro.
27/10: entre el 45 % y el 60 % van como «gana o empata» (en la misma prueba aciertan el 74-76 %).
"""
import math
from datetime import datetime, timedelta

from bot import EXTRA, MADRID, leer

UMBRAL = 0.60          # «Gana»
UMBRAL_DOBLE = 0.45    # «Gana o empata»
MIN_EQUIPOS, MAX_EQUIPOS = 3, 10
CASA, FUERA = 1.10, 0.92
PESO_TABLA = 0.15


def forma(eq, hist, n=10):
    out = []
    for p in hist.get(eq, [])[:n]:
        g = p.get("goles")
        if not g or None in g:
            continue
        a, b = (g if p["local"]["id"] == eq else g[::-1])
        out.append("G" if a > b else "E" if a == b else "P")
    return out


def pois(k, lam):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def prob_ganar(loc, vis, liga, fecha, hist):
    """(P gana local, P gana visitante) o None si faltan datos."""
    import contexto
    import prueba_xg
    a, b = forma(loc, hist), forma(vis, hist)
    lam = prueba_xg.lambdas(hist, loc, vis)
    if len(a) < 5 or len(b) < 5 or not lam:
        return None
    fl = (a.count("G") / len(a) + b.count("P") / len(b)) / 2
    fv = (a.count("P") / len(a) + b.count("G") / len(b)) / 2
    ll, lv = lam[0] * CASA, lam[1] * FUERA
    xl = sum(pois(i, ll) * pois(j, lv) for i in range(9) for j in range(9) if i > j)
    xv = sum(pois(i, ll) * pois(j, lv) for i in range(9) for j in range(9) if j > i)
    pl, pv = (fl + xl) / 2, (fv + xv) / 2
    pos = contexto.posiciones(liga, fecha, loc, vis)
    if pos:
        d = (pos[1] - pos[0]) / pos[2]
        pl, pv = pl + PESO_TABLA * d, pv - PESO_TABLA * d
    return pl, pv


def ganadores(dia, hist=None):
    """[(prob, equipo, liga, rival, hora)] de los que ganan según los datos, de más a menos seguro."""
    from picks import historial
    hist = hist if hist is not None else historial()
    out = []
    for f in EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
            continue
        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        if ini.strftime("%Y-%m-%d") != dia:
            continue
        loc, vis = pa["teams"]["home"], pa["teams"]["away"]
        pr = prob_ganar(loc["id"], vis["id"], pa["league"]["id"], pa["fixture"]["date"], hist)
        if not pr:
            continue
        pl, pv = pr
        if max(pl, pv) >= UMBRAL_DOBLE:
            eq, rival = (loc, vis) if pl >= pv else (vis, loc)
            out.append((round(max(pl, pv), 3), eq["name"], pa["league"]["id"], rival["name"], f"{ini:%H:%M}"))
    return sorted(out, reverse=True)[:MAX_EQUIPOS]


def post(dia, hist=None):
    """(tipo, hora, texto) o None. Sale a las 10:30 del día."""
    from picks import COMPETICION
    from plantillas import BANDERA
    g = ganadores(dia, hist)
    if len(g) < MIN_EQUIPOS:
        return None
    lineas = [f"✅{i}. {BANDERA.get(COMPETICION.get(liga), '⚽')} {eq} — {'Gana' if pr >= UMBRAL else 'Gana o empata'}"
              for i, (pr, eq, liga, _, _) in enumerate(g, 1)]
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    return ("ganadores", f.replace(hour=10, minute=30),
            "⚽ QUIÉN GANA HOY · COMBILOCAS ⚽\n\n" + "\n".join(lineas)
            + "\n\n📊 Según nuestros datos, no las cuotas\n\n🍀 ¿LA PINTAMOS DE VERDE? 👀💚")
