"""
20/11 (Marcos, con capturas de cuentas de X: «Aumento Athletic vs Espanyol: 2 faltas G. Bauza: cumple en 3/4…»):
combis de UN PARTIDO POR PATA, cada pata ~@1,50, con el dato del jugador detrás. Las prepara el bot con días de
antelación (las cuotas bajan durante el finde: Bauza recibirá falta 1,50 → 1,15), Marcos las monta en bet365, manda
la captura y se suben a Threads, X y Telegram (Telegram, 1 al día como mucho).

  · en la app (pestaña 🧮 Combis), siempre al día: próximos 3 días, cada 30 min (refrescar), sin lo ya subido
    y sin repetir partido ni selección entre combis
  · al privado: viernes ≥ 10:00 (el finde) y martes ≥ 10:00 (entre semana)

Patas que valen (sin «recibirá falta»: la API no trae su cuota):
  · jugador (comete falta, remates, remates a puerta, paradas): lo cumple en ≥ 80 % de sus últimos partidos de
    TITULAR (≥ 60'), con 4 como mínimo, y es de uno de los dos equipos
  · equipo: gana (≥ 3 victorias en sus 5 últimos), marca 2 o más, ambos marcan, más de 2,5 goles (con sus %)
Cuota de cada pata entre 1,38 y 1,70; se queda la que mejor cumple y más cerca de 1,50.
"""
import glob
import json
import re
import unicodedata
from datetime import datetime, timedelta

from bot import DATOS, MADRID, leer

SALIDA = DATOS / "combis_semana.json"
CUOTA_MIN, CUOTA_MAX, OBJETIVO = 1.38, 1.70, 1.50
MAX_PATAS = 7
TODO_DIA_MAX = 14   # 22/11: «Todo el día», como mucho 14 patas
# 20/11 (Marcos: «solo de las 5 grandes ligas»): las 5 grandes, las europeas, sus copas y las selecciones. Solo si en
# esos días no hay nada de eso, se tira de las demás ligas que sigue el bot (nunca femenino).
GRANDES5 = ("LaLiga", "Premier League", "Serie A", "Bundesliga", "Ligue 1")
EUROPA = ("Champions League", "Europa League", "Conference League", "UEFA Super Cup")
COPAS = ("Copa del Rey", "Supercopa de España", "FA Cup", "League Cup", "EFL Cup", "Community Shield", "Coppa Italia",
         "Supercoppa Italiana", "DFB Pokal", "Super Cup", "Coupe de France", "Trophée des Champions")
SELECCIONES = ("World Cup", "World Cup - Qualification Europe", "UEFA Nations League", "Euro Championship",
               "Euro Championship - Qualification", "Friendlies")
LIGAS = GRANDES5 + EUROPA + COPAS + SELECCIONES   # en este orden salen en la app
NO_VALEN = ("Liga F",)
BANDERA = {"LaLiga": "🇪🇸", "Segunda División": "🇪🇸", "Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Serie A": "🇮🇹",
           "Bundesliga": "🇩🇪", "Ligue 1": "🇫🇷", "Eredivisie": "🇳🇱", "Primeira Liga": "🇵🇹",
           "Champions League": "⭐", "Europa League": "🟠", "Conference League": "🟢",
           "Copa del Rey": "🇪🇸", "FA Cup": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "League Cup": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Coppa Italia": "🇮🇹", "DFB Pokal": "🇩🇪",
           "Coupe de France": "🇫🇷", "World Cup": "🌍", "UEFA Nations League": "🌍", "Friendlies": "🌍"}
JUGADOR = {  # mercado bet365 → (dato del jugador, texto)
    "Player Fouls Committed": ("faltas_c", "comete {n}+ falta{s}"),
    "Home Player Fouls Committed": ("faltas_c", "comete {n}+ falta{s}"),
    "Away Player Fouls Committed": ("faltas_c", "comete {n}+ falta{s}"),
    "Home Player Shots": ("tiros", "{n}+ remate{s}"), "Away Player Shots": ("tiros", "{n}+ remate{s}"),
    "Home Player Shots Total": ("tiros", "{n}+ remate{s}"), "Away Player Shots Total": ("tiros", "{n}+ remate{s}"),
    "Player Shots Total": ("tiros", "{n}+ remate{s}"),
    "Home Player Shots On Target Total": ("a_puerta", "{n}+ remate{s} a puerta"),
    "Away Player Shots On Target Total": ("a_puerta", "{n}+ remate{s} a puerta"),
    "Player Shots On Target Total": ("a_puerta", "{n}+ remate{s} a puerta"),
    "Goalkeeper Saves": ("paradas", "{n}+ parada{s}"),
    "Home Goalkeeper Saves": ("paradas", "{n}+ parada{s}"), "Away Goalkeeper Saves": ("paradas", "{n}+ parada{s}"),
}


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return " ".join(t.replace("-", " ").replace(".", " ").split())


def historial():
    """nombre normalizado → [{…stats del partido, eq, fecha}] en orden de fecha."""
    ps = []
    for f in glob.glob(str(DATOS / "partidos" / "*.json")):
        p = leer(f, None)
        if p and p.get("jugadores"):
            ps.append(p)
    ps.sort(key=lambda p: p.get("fecha", ""))
    h = {}
    for p in ps:
        for eq, lista in p["jugadores"].items():
            for j in lista:
                h.setdefault(norm(j["nombre"]), []).append(dict(j, eq=eq, fecha=p.get("fecha", "")))
    return h


def buscar(h, nombre):
    k = norm(nombre)
    if k in h:
        return h[k]
    partes = k.split()
    if not partes:
        return None
    cands = [x for x in h if x.split()[-1:] == partes[-1:] and x[:1] == partes[0][:1]]
    return h[cands[0]] if len(cands) == 1 else None


def _teams(pid):
    return ((leer(DATOS / "proximos" / f"{pid}.json", {}) or {}).get("partido") or {}).get("teams") or {}


def equipos_partido(pid):
    t = _teams(pid)
    return {str((t.get("home") or {}).get("id")), str((t.get("away") or {}).get("id"))} - {"None"}


def serie_jugador(hist_j, campo, umbral, n=6):
    """(cumple, de, por90, valores) en sus últimos n partidos de titular, o None si no hay 4."""
    tit = [j for j in hist_j if (j.get("min") or 0) >= 60 and campo in j][-n:]
    if len(tit) < 4:
        return None
    vals = [j[campo] or 0 for j in tit]
    mins = sum(j["min"] for j in tit)
    return sum(v >= umbral for v in vals), len(vals), (sum(vals) / mins * 90 if mins else 0), vals


def coma(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def patas_jugador(p, h):
    out, eqs = [], equipos_partido(p["id"])
    if not eqs:
        return out
    for m, (campo, plant) in JUGADOR.items():
        for o, c in (p.get("cuotas_bet365") or {}).get(m, []):
            try:
                c = float(c)
            except (TypeError, ValueError):
                continue
            mm = re.match(r"(.+?) - (\d+)$", o)
            if not (CUOTA_MIN <= c <= CUOTA_MAX) or not mm:
                continue
            nombre, umbral = mm.group(1), int(mm.group(2))
            hj = buscar(h, nombre)
            if not hj or hj[-1]["eq"] not in eqs:   # tiene que ser de uno de los dos equipos
                continue
            s = serie_jugador(hj, campo, umbral)
            if not s or s[0] / s[1] < 0.8:
                continue
            cumple, de, p90, vals = s
            x = candidata(f"{p['id']}|{m}|{o}", f"{nombre}: {plant.format(n=umbral, s='' if umbral == 1 else 's')}", c,
                          min(0.88, (cumple + 1) / (de + 2) + 0.05),   # suavizado (5/6 → 0,80) + 0,05 por ser titular fijo; tope 88 % (puede no jugar)
                          f"cumple {cumple}/{de} siendo titular · {coma(p90)} por 90' ({'-'.join(map(str, vals))})")
            if x:   # 20/11 (Marcos: «saber rápido de qué partido es cada línea»): equipo del jugador
                t = _teams(p["id"])
                x["equipo"] = next((e.get("name") for e in (t.get("home") or {}, t.get("away") or {})
                                    if str(e.get("id")) == hj[-1]["eq"]), None)
                x["lado"] = "L" if str((t.get("home") or {}).get("id")) == hj[-1]["eq"] else "V"
                out.append(x)
    return out


def _pct(x):
    try:
        return int(str(x or 0).rstrip("%") or 0)
    except ValueError:
        return 0


def poisson_al_menos(lam, k):
    """P(X ≥ k) con X ~ Poisson(lam)."""
    import math
    if lam <= 0:
        return 0.0
    return 1 - sum(math.exp(-lam) * lam ** i / math.factorial(i) for i in range(int(k)))


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def candidata(sel, texto, cuota, p, dato):
    """Pata con su probabilidad estimada p: vale si p ≥ 0,68 y no es mala cuota (p·cuota ≥ 1)."""
    if cuota is None or not (CUOTA_MIN <= cuota <= CUOTA_MAX) or p < 0.68 or p * cuota < 1.0:
        return None
    return {"sel": sel, "texto": texto, "cuota": cuota, "p": round(p, 3), "dato": dato,
            "nota": p + 0.5 * (p * cuota - 1) - abs(cuota - OBJETIVO) * 0.2}


def patas_equipo(p):
    """20/11 (Marcos: «faltan cosas, tenemos muchísimos datos»): goles del equipo, ambos marcan, más de 2,5,
    goles en la 1ª parte, gana / gana alguna parte / doble oportunidad, córners (equipo y totales), tarjetas del equipo
    y remates a puerta del partido. Probabilidad con Poisson sobre las medias de los dos equipos (lo que hace uno y
    lo que concede el otro) y, si hay, el % real de partidos que lo cumplieron."""
    c = p.get("cuotas_bet365") or {}
    sl = p.get("stats_local_casa") or p.get("stats_local") or {}
    sv = p.get("stats_visitante_fuera") or p.get("stats_visitante") or {}
    g = lambda m, k: next((_num(v) for n_, v in c.get(m, []) if n_ == k), None)
    L, V = p["local"], p["visitante"]
    f = lambda d, k: _num(d.get(k)) or 0.0
    lam_l = (f(sl, "gf") + f(sv, "gc")) / 2
    lam_v = (f(sv, "gf") + f(sl, "gc")) / 2
    pid = p["id"]
    out = []
    # goles de cada equipo
    for eq, lam, lado, s in ((L, lam_l, "Home", sl), (V, lam_v, "Away", sv)):
        m = "Total - Home" if lado == "Home" else "Total - Away"
        for linea, k, txt in (("Over 0.5", 1, f"{eq} marca"), ("Over 1.5", 2, f"{eq} marca 2 o más")):
            pr = poisson_al_menos(lam, k)
            if k == 1 and s.get("sin_marcar"):
                pr = (pr + 1 - _pct(s["sin_marcar"]) / 100) / 2
            out.append(candidata(f"{pid}|{m}|{linea}", txt, g(m, linea), pr,
                                 f"marca {coma(f(s, 'gf'), 1)} por partido y el rival encaja {coma(f(sv if s is sl else sl, 'gc'), 1)}"))
    # ganador, gana alguna parte, doble oportunidad (Poisson de los dos equipos)
    import math
    pl = pe = 0.0
    for i in range(10):
        for j in range(10):
            pij = math.exp(-lam_l) * lam_l ** i / math.factorial(i) * math.exp(-lam_v) * lam_v ** j / math.factorial(j)
            pl += pij if i > j else 0
            pe += pij if i == j else 0
    pv = 1 - pl - pe
    for eq, pw, k, s in ((L, pl, "Home", sl), (V, pv, "Away", sv)):
        forma = s.get("forma", "")
        out.append(candidata(f"{pid}|Match Winner|{k}", f"Gana {eq}", g("Match Winner", k), (pw + forma.count("V") / 5) / 2 if forma else pw,
                             f"{eq}: {forma} en sus últimos 5" if forma else f"{eq} favorito"))
        out.append(candidata(f"{pid}|To Win Either Half|{k}", f"{eq} gana alguna de las dos partes", g("To Win Either Half", k),
                             min(0.95, pw + 0.12), f"{eq}: {forma} en sus últimos 5"))
        dc = "Home/Draw" if k == "Home" else "Draw/Away"
        out.append(candidata(f"{pid}|Double Chance|{dc}", f"{eq} o empate", g("Double Chance", dc), pw + pe,
                             f"{eq}: {forma} en sus últimos 5"))
    # ambos marcan y más de 2,5 (Poisson + % real)
    pb = poisson_al_menos(lam_l, 1) * poisson_al_menos(lam_v, 1)
    a, b = _pct(sl.get("btts")), _pct(sv.get("btts"))
    if a and b:
        pb = (pb + min(a, b) / 100) / 2
    out.append(candidata(f"{pid}|Both Teams Score|Yes", "Ambos marcan", g("Both Teams Score", "Yes"), pb,
                         f"marcan los dos en el {a}% y el {b}% de sus partidos"))
    po = poisson_al_menos(lam_l + lam_v, 3)
    a, b = _pct(sl.get("o25")), _pct(sv.get("o25"))
    if a and b:
        po = (po + min(a, b) / 100) / 2
    out.append(candidata(f"{pid}|Goals Over/Under|Over 2.5", "Más de 2,5 goles", g("Goals Over/Under", "Over 2.5"), po,
                         f"más de 2,5 goles en el {a}% y el {b}% de sus partidos"))
    lam_1p = (f(sl, "gf_1p") + f(sv, "gc_1p") + f(sv, "gf_1p") + f(sl, "gc_1p")) / 2
    out.append(candidata(f"{pid}|Goals Over/Under First Half|Over 0.5", "Gol en la 1ª parte", g("Goals Over/Under First Half", "Over 0.5"),
                         poisson_al_menos(lam_1p, 1), f"{coma(lam_1p, 1)} goles de media en las primeras partes de los dos"))
    # córners
    lam_c = (f(sl, "corners_total") + f(sv, "corners_total")) / 2
    for o, cu in c.get("Corners Over Under", []):
        mm = re.match(r"Over (\d+)(?:\.5)?$", o)
        if mm:
            k = int(float(o.split()[1]) + 0.5) if ".5" in o else int(o.split()[1]) + 1
            out.append(candidata(f"{pid}|Corners Over Under|{o}", f"Más de {o.split()[1].replace('.', ',')} córners",
                                 _num(cu), poisson_al_menos(lam_c, k), f"{coma(lam_c, 1)} córners de media en los partidos de los dos"))
    for eq, s, r, m in ((L, sl, sv, "Home Corners Over/Under"), (V, sv, sl, "Away Corners Over/Under")):
        lam = (f(s, "corners") + f(r, "corners_c")) / 2
        for o, cu in c.get(m, []):
            if o.startswith("Over ") and o.endswith(".5"):
                k = int(float(o.split()[1]) + 0.5)
                out.append(candidata(f"{pid}|{m}|{o}", f"{eq}: más de {o.split()[1].replace('.', ',')} córners", _num(cu),
                                     poisson_al_menos(lam, k), f"{eq} saca {coma(f(s, 'corners'), 1)} córners y el rival concede {coma(f(r, 'corners_c'), 1)}"))
    # tarjetas del equipo
    for eq, s, r, m in ((L, sl, sv, "Home Team Total Cards"), (V, sv, sl, "Away Team Total Cards")):
        lam = (f(s, "amarillas") + f(r, "amarillas_c")) / 2
        for o, cu in c.get(m, []):
            if o.startswith("Over ") and o.endswith(".5"):
                k = int(float(o.split()[1]) + 0.5)
                out.append(candidata(f"{pid}|{m}|{o}", f"{eq} ve más de {o.split()[1].replace('.', ',')} tarjetas", _num(cu),
                                     poisson_al_menos(lam, k), f"{eq} ve {coma(f(s, 'amarillas'), 1)} amarillas por partido"))
    # remates a puerta del partido
    lam_t = (f(sl, "a_puerta") + f(sv, "a_puerta_c")) / 2 + (f(sv, "a_puerta") + f(sl, "a_puerta_c")) / 2
    for o, cu in c.get("Total ShotOnGoal", []):
        if o.startswith("Over ") and o.endswith(".5"):
            k = int(float(o.split()[1]) + 0.5)
            out.append(candidata(f"{pid}|Total ShotOnGoal|{o}", f"Más de {o.split()[1].replace('.', ',')} remates a puerta en el partido",
                                 _num(cu), poisson_al_menos(lam_t, k), f"{coma(lam_t, 1)} remates a puerta de media entre los dos"))
    # 20/11 (Marcos: «quiero más cosas»): más mercados
    def mas_que(la, lb, N=30):   # P(X > Y) con X~Poisson(la), Y~Poisson(lb)
        px = [math.exp(-la) * la ** i / math.factorial(i) for i in range(N)]
        py = [math.exp(-lb) * lb ** i / math.factorial(i) for i in range(N)]
        return sum(px[i] * sum(py[:i]) for i in range(N))
    po15 = poisson_al_menos(lam_l + lam_v, 2)
    a, b = _pct(sl.get("o15")), _pct(sv.get("o15"))
    if a and b:
        po15 = (po15 + min(a, b) / 100) / 2
    out.append(candidata(f"{pid}|Goals Over/Under|Over 1.5", "Más de 1,5 goles", g("Goals Over/Under", "Over 1.5"), po15,
                         f"más de 1,5 goles en el {a}% y el {b}% de sus partidos"))
    lam_2p = (f(sl, "gf_2p") + f(sv, "gc_2p") + f(sv, "gf_2p") + f(sl, "gc_2p")) / 2
    for o, k, txt in (("Over 0.5", 1, "Gol en la 2ª parte"), ("Over 1.5", 2, "Más de 1,5 goles en la 2ª parte")):
        out.append(candidata(f"{pid}|Goals Over/Under - Second Half|{o}", txt, g("Goals Over/Under - Second Half", o),
                             poisson_al_menos(lam_2p, k), f"{coma(lam_2p, 1)} goles de media en las segundas partes de los dos"))
    cl, cv = (f(sl, "corners") + f(sv, "corners_c")) / 2, (f(sv, "corners") + f(sl, "corners_c")) / 2
    tl, tv = (f(sl, "tiros") + f(sv, "tiros_c")) / 2, (f(sv, "tiros") + f(sl, "tiros_c")) / 2
    al, av = (f(sl, "a_puerta") + f(sv, "a_puerta_c")) / 2, (f(sv, "a_puerta") + f(sl, "a_puerta_c")) / 2
    for eq, k, mine, suyo, m, txt, que in ((L, "Home", cl, cv, "Corners 1x2", "saca más córners", "córners"),
                                           (V, "Away", cv, cl, "Corners 1x2", "saca más córners", "córners"),
                                           (L, "Home", tl, tv, "Shots.1x2", "remata más que el rival", "remates"),
                                           (V, "Away", tv, tl, "Shots.1x2", "remata más que el rival", "remates"),
                                           (L, "Home", al, av, "ShotOnTarget 1x2", "remata más a puerta", "remates a puerta"),
                                           (V, "Away", av, al, "ShotOnTarget 1x2", "remata más a puerta", "remates a puerta")):
        if mine and suyo:
            out.append(candidata(f"{pid}|{m}|{k}", f"{eq} {txt}", g(m, k), mas_que(mine, suyo),
                                 f"{coma(mine, 1)} {que} de {eq} contra {coma(suyo, 1)} del rival"))
    lam_ct = (f(sl, "corners_total_1p") + f(sv, "corners_total_1p")) / 2
    for o, cu in c.get("Total Corners (1st Half)", []):
        mm = re.match(r"Over (\d+)$", o)
        if mm and lam_ct:
            out.append(candidata(f"{pid}|Total Corners (1st Half)|{o}", f"Más de {mm.group(1)} córners en la 1ª parte", _num(cu),
                                 poisson_al_menos(lam_ct, int(mm.group(1)) + 1), f"{coma(lam_ct, 1)} córners de media en las primeras partes"))
    lam_ts = tl + tv
    for o, cu in c.get("Total Shots", []):
        if o.startswith("Over ") and o.endswith(".5") and lam_ts:
            out.append(candidata(f"{pid}|Total Shots|{o}", f"Más de {o.split()[1].replace('.', ',')} remates en el partido", _num(cu),
                                 poisson_al_menos(lam_ts, int(float(o.split()[1]) + 0.5)), f"{coma(lam_ts, 1)} remates de media entre los dos"))
    lam_tj = (f(sl, "amarillas") + f(sv, "amarillas_c")) / 2 + (f(sv, "amarillas") + f(sl, "amarillas_c")) / 2
    for o, cu in c.get("Cards Over/Under", []):
        if o.startswith("Over ") and o.endswith(".5") and lam_tj:
            out.append(candidata(f"{pid}|Cards Over/Under|{o}", f"Más de {o.split()[1].replace('.', ',')} tarjetas en el partido", _num(cu),
                                 poisson_al_menos(lam_tj, int(float(o.split()[1]) + 0.5)), f"{coma(lam_tj, 1)} tarjetas de media entre los dos"))
    return [x for x in out if x]


def patas_ganador(p):
    """20/11 (Marcos: «otra de quién gana»): el favorito de cada partido gana, de @1,20 a @1,80 (máximo de pata)."""
    import math
    c = p.get("cuotas_bet365") or {}
    sl = p.get("stats_local_casa") or p.get("stats_local") or {}
    sv = p.get("stats_visitante_fuera") or p.get("stats_visitante") or {}
    f = lambda d, k: _num(d.get(k)) or 0.0
    lam_l, lam_v = (f(sl, "gf") + f(sv, "gc")) / 2, (f(sv, "gf") + f(sl, "gc")) / 2
    if not (lam_l or lam_v):
        return []
    pl = pe = 0.0
    for i in range(10):
        for j in range(10):
            pij = math.exp(-lam_l) * lam_l ** i / math.factorial(i) * math.exp(-lam_v) * lam_v ** j / math.factorial(j)
            pl += pij if i > j else 0
            pe += pij if i == j else 0
    out = []
    for eq, pw, k, s in ((p["local"], pl, "Home", sl), (p["visitante"], 1 - pl - pe, "Away", sv)):
        cu = next((_num(v) for n_, v in c.get("Match Winner", []) if n_ == k), None)
        forma = s.get("forma", "")
        pr = (pw + 1 / cu) / 2 if cu else pw          # mezcla nuestro cálculo con lo que dice la casa
        if forma:
            pr = (2 * pr + forma.count("V") / 5) / 3
        if cu and 1.20 <= cu <= 1.80 and pr >= 0.6:
            out.append({"sel": f"{p['id']}|Match Winner|{k}", "texto": f"Gana {eq}", "cuota": cu, "p": round(pr, 3),
                        "dato": f"{eq}: {forma} en sus últimos 5 · {'en casa' if k == 'Home' else 'fuera'}" if forma else f"{eq} favorito",
                        "nota": pr + 0.5 * (pr * cu - 1), "lado": "L" if k == "Home" else "V", "ganador": True})
    return out


def _dia(p):
    return datetime.fromisoformat(p["fecha"]).astimezone(MADRID).strftime("%Y-%m-%d")


def ligas_elegidas(partidos, desde, hasta):
    """Las competiciones buenas (LIGAS) que tienen partido esos días; si no hay ninguna, las demás que sigue el bot."""
    hay = [p.get("competicion") for p in partidos if desde <= _dia(p) <= hasta]
    buenas = [l for l in LIGAS if l in hay]
    if buenas:
        return buenas
    return sorted({l for l in hay if l and l not in NO_VALEN})


def generar(desde, hasta, partidos=None, h=None, max_combis=12, fuera=(), empieza_despues=None):
    """Combis por liga con los partidos entre desde y hasta (fechas AAAA-MM-DD, ambas incluidas).
    20/11 (Marcos: «no quiero las cosas 20.000 veces repetidas»): sin las selecciones de «fuera» (lo ya subido) y
    cada partido en una sola combi; si la mejor pata de un partido ya salió, va la siguiente."""
    if partidos is None:
        d = leer(DATOS / "resumen_proximos.json", []) or []
        partidos = d if isinstance(d, list) else d.get("partidos", [])
    h = historial() if h is None else h
    combis = []
    for liga in ligas_elegidas(partidos, desde, hasta):
        ms = sorted([p for p in partidos if p.get("competicion") == liga
                     and desde <= datetime.fromisoformat(p["fecha"]).astimezone(MADRID).strftime("%Y-%m-%d") <= hasta],
                    key=lambda p: p["fecha"])
        patas = []
        for p in ms:
            if empieza_despues and datetime.fromisoformat(p["fecha"]).astimezone(MADRID) < empieza_despues:
                continue
            cands = [x for x in patas_jugador(p, h) + patas_equipo(p) if x["sel"] not in set(fuera)]
            if cands:
                b = max(cands, key=lambda x: x["nota"])
                ini = datetime.fromisoformat(p["fecha"]).astimezone(MADRID)
                t = _teams(p["id"])
                patas.append(dict(b, partido=f"{p['local']}–{p['visitante']}", hora=ini.strftime("%Y-%m-%dT%H:%M"),
                                  logo_l=(t.get("home") or {}).get("logo"), logo_v=(t.get("away") or {}).get("logo")))
        if len(patas) < 4:
            continue
        patas = sorted(sorted(patas, key=lambda x: -x["nota"])[:MAX_PATAS], key=lambda x: x["hora"])
        tot = 1.0
        for x in patas:
            tot *= x["cuota"]
        combis.append({"liga": liga, "patas": patas, "cuota": round(tot, 2), "media": sum(x["nota"] for x in patas) / len(patas)})
    orden = ligas_elegidas(partidos, desde, hasta)   # 20/11: en orden fijo (LaLiga, Premier, Serie A…), no por nota
    return sorted(sorted(combis, key=lambda c: -c["media"])[:max_combis], key=lambda c: orden.index(c["liga"]))


def lado_pata(x):
    """De qué equipo es una pata: «L», «V» o None si es del partido (ambos marcan, córners totales…)."""
    if x.get("lado"):
        return x["lado"]
    m, o = x["sel"].split("|")[1:3]
    if m in ("Total - Home", "Home Corners Over/Under", "Home Team Total Cards") or o in ("Home", "Home/Draw"):
        return "L"
    if m in ("Total - Away", "Away Corners Over/Under", "Away Team Total Cards") or o in ("Away", "Draw/Away"):
        return "V"
    return None


def tipo_pata(x):
    """Para no repetir lo mismo en una combi de equipo: un resultado, un goles, unos córners, unas tarjetas, un jugador."""
    m = x["sel"].split("|")[1]
    if m in ("Match Winner", "To Win Either Half", "Double Chance"):
        return "resultado"
    if m.startswith("Total - "):
        return "goles"
    if "Corners" in m:
        return "corners"
    if "Cards" in m:
        return "tarjetas"
    if m in ("Shots.1x2", "ShotOnTarget 1x2"):
        return "remates"
    return "jugador:" + x["texto"].split(":")[0]


def generar_equipos(desde, hasta, partidos=None, h=None, fuera=(), empieza_despues=None, max_patas=5):
    """20/11 (Marcos: «un apartado de combis de cada equipo»): por cada equipo que juega, una combi de su partido
    solo con cosas suyas (sus goles, resultado, córners, tarjetas y sus jugadores), sin lo ya subido. Para Crear apuesta."""
    if partidos is None:
        d = leer(DATOS / "resumen_proximos.json", []) or []
        partidos = d if isinstance(d, list) else d.get("partidos", [])
    h = historial() if h is None else h
    out, ligas = [], ligas_elegidas(partidos, desde, hasta)
    for p in sorted(partidos, key=lambda p: (ligas.index(p["competicion"]) if p.get("competicion") in ligas else 99, p["fecha"])):
        if p.get("competicion") not in ligas:
            continue
        ini = datetime.fromisoformat(p["fecha"]).astimezone(MADRID)
        if not (desde <= ini.strftime("%Y-%m-%d") <= hasta) or (empieza_despues and ini < empieza_despues):
            continue
        cands = [x for x in patas_jugador(p, h) + patas_equipo(p) if x and x["sel"] not in set(fuera)]
        t = _teams(p["id"])
        for lado, eq, tt in (("L", p["local"], t.get("home") or {}), ("V", p["visitante"], t.get("away") or {})):
            patas, tipos = [], set()
            for x in sorted((x for x in cands if lado_pata(x) == lado), key=lambda x: -x["nota"]):
                if tipo_pata(x) in tipos:
                    continue
                tipos.add(tipo_pata(x))
                patas.append(x)
                if len(patas) == max_patas:
                    break
            if len(patas) < 2:
                continue
            tot = 1.0
            for x in patas:
                tot *= x["cuota"]
            out.append({"equipo": eq, "liga": p["competicion"], "partido": f"{p['local']}–{p['visitante']}",
                        "hora": ini.strftime("%Y-%m-%dT%H:%M"), "logo": tt.get("logo"),
                        "patas": [dict(x, partido=f"{p['local']}–{p['visitante']}", hora=ini.strftime("%Y-%m-%dT%H:%M")) for x in patas],
                        "cuota": round(tot, 2)})
    return out


def _es_top(x):
    from plantillas import GRANDES
    return any(g in x["partido"].lower() for g in GRANDES)


DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
JUG = lambda x: bool(x.get("lado") and ":" in x["texto"])
DESTACADAS = (   # (clave, título, explicación, filtro de pata, nº de patas, orden)
    ("todas", "🌍 Lo mejor de todas las ligas", "La mejor pata de cada partido, mezclando ligas", lambda x: True, 7, "nota"),
    ("segura", "🛡️ La segura", "Las 3 patas más probables de todo", lambda x: True, 3, "p"),
    ("ganan", "🏆 Quién gana", "El favorito de cada partido gana, de @1,20 a @1,80", lambda x: x["sel"].split("|")[1] == "Match Winner", 6, "p"),
    ("ganan-larga", "🏆 Quién gana · larga", "Todos los favoritos claros, hasta 12 (puede llevar los de la de arriba)",
     lambda x: x["sel"].split("|")[1] == "Match Winner", 12, "p"),
    ("top", "🏟️ Partidos top", "Solo partidos de los grandes", _es_top, 4, "nota"),
    ("faltas", "🦵 Faltas", "Jugadores que cometen faltas siempre que son titulares", lambda x: JUG(x) and "falta" in x["texto"], 5, "nota"),
    ("remates", "🔫 Remates y paradas", "Rematadores fijos y porteros con trabajo",
     lambda x: JUG(x) and ("remate" in x["texto"] or "parada" in x["texto"]), 5, "nota"),
    ("goles", "⚽ Goles", "Marca, ambos marcan, más de 1,5 / 2,5 y gol en cada parte",
     lambda x: any(m in x["sel"] for m in ("|Total - ", "|Both Teams Score|", "|Goals Over/Under")), 5, "nota"),
    ("corners", "🚩 Córners", "Córners de equipos, del partido, de la 1ª parte y quién saca más", lambda x: "Corners" in x["sel"], 4, "nota"),
    ("tarjetas", "🟨 Tarjetas y remates de equipo", "Tarjetas y quién remata más",
     lambda x: any(m in x["sel"] for m in ("Cards", "Shots", "ShotOnGoal", "ShotOnTarget")) and not JUG(x), 4, "nota"),
    ("larga", "🚀 La larga", "10 patas para soñar, con lo que queda", lambda x: True, 10, "nota"),
)


def generar_destacadas(desde, hasta, partidos=None, h=None, fuera=(), empieza_despues=None):
    """20/11 (Marcos: «combinadas de todas las ligas en una y algo más»; «quiero más cosas»): combis que mezclan ligas,
    cada una de un tipo, más una por día. Ninguna selección sale en dos destacadas y cada partido una vez por combi."""
    if partidos is None:
        d = leer(DATOS / "resumen_proximos.json", []) or []
        partidos = d if isinstance(d, list) else d.get("partidos", [])
    h = historial() if h is None else h
    ligas = ligas_elegidas(partidos, desde, hasta)
    pool = []   # (partido, candidatas)
    for p in sorted(partidos, key=lambda p: p["fecha"]):
        ini = datetime.fromisoformat(p["fecha"]).astimezone(MADRID)
        if p.get("competicion") not in ligas or not (desde <= _dia(p) <= hasta) or (empieza_despues and ini < empieza_despues):
            continue
        t = _teams(p["id"])
        cands = [dict(x, partido=f"{p['local']}–{p['visitante']}", hora=ini.strftime("%Y-%m-%dT%H:%M"), liga=p["competicion"],
                      logo_l=(t.get("home") or {}).get("logo"), logo_v=(t.get("away") or {}).get("logo"))
                 for x in patas_jugador(p, h) + patas_equipo(p) + patas_ganador(p) if x and x["sel"] not in set(fuera)]
        if cands:
            pool.append((p, cands))
    tipos = list(DESTACADAS)
    dias = sorted({_dia(p) for p, _ in pool})
    # 22/11 (Marcos: «quiero también una del día mezclando todos los partidos que pueda, o que haga dos diferentes»;
    # «esas dos, cuotas de 30-40 con patas de 1,4-1,6»): por día, las primeras: «Todo el domingo» (una pata de cada
    # partido, hasta TODO_DIA_MAX; no gasta selecciones) y dos más, A y B, de @30-40 con patas de @1,40-1,60 y sin
    # repetir selección entre ellas ni con el resto de destacadas.
    for d in reversed(dias):
        wd = datetime.fromisoformat(d).weekday()
        tipos.insert(0, (f"todo-{d}", f"📅 Todo el {DIAS_ES[wd]}", f"Una pata de cada partido del {DIAS_ES[wd]} {int(d[8:])}",
                         lambda x, d=d: x["hora"][:10] == d, TODO_DIA_MAX, "p"))
    usadas, out = set(), []
    dos = {}
    for d in dias:
        wd = datetime.fromisoformat(d).weekday()
        dos[d] = []
        for letra, otra in (("A", "B"), ("B", "A")):
            c = combi_30_40([(p, cs) for p, cs in pool if _dia(p) == d], usadas,
                            evitar={x["partido"] for c0 in dos[d] for x in c0["patas"]})
            if c:
                usadas |= {x["sel"] for x in c["patas"]}
                dos[d].append(dict(c, clave=f"dia-{d}-{letra.lower()}", titulo=f"📅 La del {DIAS_ES[wd]} · {letra}",
                                   expl=f"@{DOS_DIA_CUOTA[0]}-{DOS_DIA_CUOTA[1]} con patas de @{coma(DOS_DIA_PATA[0])}-"
                                        f"{coma(DOS_DIA_PATA[1])} (la {otra}, otra distinta)", liga="Varias"))
    for clave, titulo, expl, filtro, n, orden in tipos:
        mejores = []
        for p, cands in pool:
            gan = clave.startswith("ganan")
            libre = clave == "ganan-larga" or clave.startswith("todo-")
            cs = [x for x in cands if filtro(x) and (libre or x["sel"] not in usadas) and gan == bool(x.get("ganador"))]
            if cs:
                mejores.append(max(cs, key=lambda x: x[orden]))
        patas = sorted(sorted(mejores, key=lambda x: -x[orden])[:n], key=lambda x: x["hora"])
        if len(patas) < min(3, n):
            continue
        if not clave.startswith("todo-"):
            usadas |= {x["sel"] for x in patas}
        tot = 1.0
        for x in patas:
            tot *= x["cuota"]
        prob = 1.0
        for x in patas:
            prob *= x["p"]
        out.append({"clave": clave, "titulo": titulo, "expl": expl, "liga": "Varias", "patas": patas, "cuota": round(tot, 2),
                    "prob": round(prob, 3)})
        if clave.startswith("todo-"):
            out += dos.get(clave[5:], [])
    return out


DOS_DIA_CUOTA = (30, 40)       # 22/11 (Marcos): las dos del día, de @30 a @40…
DOS_DIA_PATA = (1.40, 1.60)    # …con patas de @1,40 a @1,60


def combi_30_40(pool, usadas, evitar=()):
    """Una combi de @30-40 con patas de @1,40-1,60: la pata más probable de cada partido (los de «evitar», los
    de la otra combi, al final), sin pasar de @40, hasta llegar a @30. Un partido una vez; None si no llega."""
    lo, hi = DOS_DIA_PATA
    partidos = []
    for p, cands in pool:
        cs = sorted([x for x in cands if lo <= x["cuota"] <= hi and x["sel"] not in usadas and not x.get("ganador")],
                    key=lambda x: -x["p"])
        if cs:
            partidos.append(cs)
    partidos.sort(key=lambda cs: (cs[0]["partido"] in evitar, -cs[0]["p"]))
    patas, tot = [], 1.0
    for cs in partidos:
        x = next((x for x in cs if tot * x["cuota"] <= DOS_DIA_CUOTA[1]), None)
        if not x:
            continue
        patas.append(x)
        tot *= x["cuota"]
        if tot >= DOS_DIA_CUOTA[0]:
            break
    if tot < DOS_DIA_CUOTA[0]:
        return None
    prob = 1.0
    for x in patas:
        prob *= x["p"]
    return {"patas": sorted(patas, key=lambda x: x["hora"]), "cuota": round(tot, 2), "prob": round(prob, 3)}


DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def texto_aviso(c, i, n):
    filas = []
    for x in c["patas"]:
        f = datetime.fromisoformat(x["hora"])
        filas.append(f"• {DIAS[f.weekday()]} {f:%H:%M} {x['partido']}\n   {x['texto']} @{coma(x['cuota'])}\n   📊 {x['dato']}")
    return (f"🧮 COMBI {i}/{n} · {BANDERA.get(c['liga'], '⚽')} {c['liga']} · {len(c['patas'])} patas · @{coma(c['cuota'])}\n\n"
            + "\n\n".join(filas) +
            "\n\n👉 Móntala en bet365 (mira las cuotas: bajan con los días) y mándame la captura: se sube a Threads, X y "
            "Telegram (en Telegram, 1 al día como mucho).")


def texto_post(c):
    """El texto del post (con la captura de Marcos): las patas con su dato, como las cuentas de X."""
    if c.get("titulo"):   # destacada (mezcla ligas)
        lineas = [f"{c['titulo'].upper()} 🔥", ""]
    elif c.get("equipo"):   # combi de un equipo (Crear apuesta de su partido)
        lineas = [f"{BANDERA.get(c['liga'], '⚽')} COMBI DEL {c['equipo'].upper()} · {c['partido']} 🔥", ""]
    else:
        lineas = [f"{BANDERA.get(c['liga'], '⚽')} COMBI {c['liga'].upper()} · UNA POR PARTIDO 🔥", ""]
    for x in c["patas"]:
        lineas.append(f"🍀 {x['texto']}" + ("" if c.get("equipo") else f" ({x['partido']})"))
        lineas.append(f"   📊 {x['dato']}")
    lineas += ["", f"📈 Cuota @{coma(c['cuota'])}", "", "🔔 Activad las notificaciones, que vienen más combis 👀"]
    return "\n".join(lineas)


def de_hoy(ahora):
    """Viernes → sábado a lunes; martes → martes a jueves. Otro día: None."""
    wd = ahora.weekday()
    if wd == 4:
        return (ahora + timedelta(days=1)).strftime("%Y-%m-%d"), (ahora + timedelta(days=3)).strftime("%Y-%m-%d")
    if wd == 1:
        return ahora.strftime("%Y-%m-%d"), (ahora + timedelta(days=2)).strftime("%Y-%m-%d")
    return None


def casa_con(patas_boleto, guardadas=None, textos=None):
    """La combi propuesta con la que casa un boleto (≥ 3 patas iguales, por selección o por el nombre del
    jugador/equipo que se lee en la captura), o None."""
    if guardadas is None:
        g = leer(SALIDA, {}) or {}
        guardadas = (g.get("destacadas") or []) + (g.get("combis") or []) + (g.get("equipos") or [])
    sels = {s for s in patas_boleto if s}
    leido = norm(" ".join(textos or []))
    for c in guardadas:
        iguales = len(sels & {x["sel"] for x in c["patas"]})
        if leido:
            iguales = max(iguales, sum(1 for x in c["patas"]
                                       if norm(x["texto"].split(":")[0].replace("Gana ", "")).split()[-1:][0] in leido.split()))
        if iguales >= min(3, len(c["patas"])):
            return c
    return None


def ya_subidas(ahora, guardado=None):
    """Selecciones ya publicadas (posts con su selección de los últimos 3 días) + las de las combis de aquí que
    Marcos ya subió con su captura."""
    from incidencias import publicaciones
    from bot import RAIZ
    desde = (ahora - timedelta(days=3)).strftime("%Y-%m-%d")
    sels = set((guardado or {}).get("subidas") or [])
    for p in publicaciones(RAIZ) + (leer(RAIZ / "publicaciones" / "asistente.json", []) or []):
        if str(p.get("fecha", "")) >= desde and (p.get("mensaje_id") or p.get("enviado") or any((p.get("redes") or {}).values())):
            sels |= {x for x in p.get("sel") or [] if x and not x.startswith("0|")}
    return sels


def refrescar(ahora=None, cada=timedelta(minutes=30)):
    """20/11 (Marcos: «que esté constantemente actualizándose»): las combis de la app para los próximos 3 días, sin
    lo ya subido. Cada 30 min, o al momento si Marcos acaba de subir una (cambian las «subidas»)."""
    ahora = ahora or datetime.now(MADRID)
    g = leer(SALIDA, {}) or {}
    subidas = g.get("subidas") or []
    if g.get("generado") and ahora - datetime.fromisoformat(g["generado"]) < cada and g.get("n_subidas") == len(subidas):
        return g
    rango = (ahora.strftime("%Y-%m-%d"), (ahora + timedelta(days=3)).strftime("%Y-%m-%d"))
    fuera, h = ya_subidas(ahora, g), historial()
    cs = generar(*rango, h=h, fuera=fuera, empieza_despues=ahora + timedelta(minutes=30))
    eqs = generar_equipos(*rango, h=h, fuera=fuera, empieza_despues=ahora + timedelta(minutes=30))
    des = generar_destacadas(*rango, h=h, fuera=fuera, empieza_despues=ahora + timedelta(minutes=30))
    d_ = leer(DATOS / "resumen_proximos.json", []) or []
    otras = not any(l in LIGAS for l in ligas_elegidas(d_ if isinstance(d_, list) else d_.get("partidos", []), *rango))
    g = {"dia": ahora.strftime("%Y-%m-%d"), "generado": ahora.isoformat(timespec="minutes"), "rango": list(rango),
         "combis": cs, "equipos": eqs, "destacadas": des, "otras_ligas": otras, "subidas": subidas[-300:], "n_subidas": len(subidas[-300:])}
    SALIDA.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"combis_semana: {len(cs)} combis ({', '.join(c['liga'] for c in cs)}) y {len(eqs)} de equipo, {len(des)} destacadas")
    return g


def apuntar_subida(c):
    """Las patas de una combi que Marcos ya subió: fuera de las demás desde la próxima vuelta."""
    g = leer(SALIDA, {}) or {}
    g["subidas"] = sorted(set(g.get("subidas") or []) | {x["sel"] for x in c["patas"]})
    SALIDA.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        for i, c in enumerate(generar(sys.argv[1], sys.argv[2]), 1):
            print(texto_aviso(c, i, 4), "\n")
    else:
        refrescar()
