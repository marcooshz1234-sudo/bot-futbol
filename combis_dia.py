"""
Combis del día con el formato que pidió Marcos el 27/10 (las de ese martes son el modelo):

1. COMBI DE CADA PARTIDO («✅ COMBI LOCAS | LIGA», con la foto del partido): una por partido, de 4 a 7
   selecciones de ESE partido, cuota total entre 7 y 10, cada pata ≥ 1,25 y con ≥ 45 % de probabilidad.
   Se elige la que más devuelve a la larga (probabilidad de que salga × cuota). Las patas de resultado
   van todas a favor del mismo equipo y tiene que existir algún marcador que las cumpla todas.
   Partidos: primero los de equipos grandes, luego los demás; entre 5 y 8 al día (los que haya).
   Hora: 50 min antes del partido; si coinciden, cada 30 min hacia atrás.
2. COMBI x3 (13:30) y LA LOCA (16:00), con el mejor pick de cada partido del día (≥ 60 %, cuota ≥ 1,25):
   x3 = 2-4 patas entre 2,5 y 4 · loca = 4-7 patas entre 7 y 10. Solo partidos que empiezan después.

Datos: los dos equipos con al menos 5 partidos; en copa contra uno de categoría que no seguimos, solo
mercados de nuestro equipo (con sus datos). Probabilidad = la aprendida (aprender.py).
"""
import itertools
import math
from datetime import datetime, timedelta

from bot import EXTRA, MADRID, leer

CUOTA_MIN_PATA = 1.25
PARTIDO = {"patas": (4, 7), "cuota": (7.0, 10.0), "prob_min": 0.45, "max": 8}
TRES = {"patas": (2, 4), "cuota": (2.5, 4.0), "hora": (13, 30)}
LOCA = {"patas": (4, 7), "cuota": (7.0, 10.0), "hora": (16, 0)}
PROB_MIN_MULTI = 0.60
RESULTADO = ("Match Winner", "Double Chance", "To Win Either Half", "First Half Winner", "Win Both Halves")


def pool_partido(ex, hist, ap):
    """Picks posibles de un partido con su probabilidad aprendida. [] si no hay datos."""
    import aprender
    import picks as P
    pa = ex.get("partido")
    if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
        return []
    loc, vis = pa["teams"]["home"], pa["teams"]["away"]
    h_loc = [(p, loc["id"]) for p in hist.get(loc["id"], [])[:P.ULTIMOS]]
    h_vis = [(p, vis["id"]) for p in hist.get(vis["id"], [])[:P.ULTIMOS]]
    lok, vok = len(h_loc) >= P.MIN_PARTIDOS, len(h_vis) >= P.MIN_PARTIDOS
    if not (lok or vok) or (not (lok and vok) and pa["league"]["id"] not in P.COPAS):
        return []
    inicio = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
    base = {"partido_id": pa["fixture"]["id"], "fecha": inicio.strftime("%Y-%m-%dT%H:%M"),
            "competicion": P.COMPETICION.get(pa["league"]["id"], pa["league"]["name"]), "liga_id": pa["league"]["id"],
            "local": loc["name"], "visitante": vis["name"]}
    pool = []
    for m, ops in (ex.get("cuotas") or {}).items():
        if m in P.JUG_MERCADOS:
            continue
        for o, c in ops:
            try:
                c = float(c)
            except (TypeError, ValueError):
                continue
            if c < CUOTA_MIN_PATA or c > 3.0 or P.excluido(m, o) or str(o).startswith("Under") or o == "No" \
                    or P.es_sin_empate(m, o):
                continue
            if lok and vok:
                fl, fv = P.evaluador(m, o, True), P.evaluador(m, o, False)
                if not fl:
                    continue
                a, na = P.frecuencia(fl, h_loc)
                b, nb = P.frecuencia(fv, h_vis)
                if na < P.MIN_PARTIDOS or nb < P.MIN_PARTIDOS or min(a / na, b / nb) < 0.4:
                    continue
                frec, det = (a + b) / (na + nb), f"{loc['name']} {a}/{na} · {vis['name']} {b}/{nb}"
            else:   # copa contra uno de abajo: solo lo de nuestro equipo
                if P.lado_pick({"mercado": m, "opcion": o}) != ("local" if lok else "visitante"):
                    continue
                fn = P.evaluador(m, o, lok)
                if not fn:
                    continue
                a, na = P.frecuencia(fn, h_loc if lok else h_vis)
                if na < P.MIN_PARTIDOS:
                    continue
                frec, det = a / na, f"{loc['name'] if lok else vis['name']} {a}/{na}"
            if frec < 0.5:
                continue
            p = dict(base, mercado=m, opcion=o, tipo=P.tipo_de(m), texto=P.texto_pick(m, o, loc["name"], vis["name"]),
                     cuota=c, frecuencia=round(frec, 3), ventaja=round(frec - 1 / c, 3), detalle=det)
            pool.append(p)
    for p in P.picks_jugadores(ex, hist, base, frec_min=0.6):
        if p.get("campo") in ("faltas_c", "amarillas"):
            continue   # "X comete 1+ faltas" es relleno: en el histórico prometen 77 % y salen 66 %
        if p["cuota"] >= CUOTA_MIN_PATA and ((lok and vok) or p.get("equipo") == (loc["name"] if lok else vis["name"])):
            pool.append(p)
    for p in pool:
        p["prob_aprendida"] = aprender.prob_aprendida(p, ap) or p["frecuencia"]
    # una por mercado (o por jugador y dato): la más probable
    mejor = {}
    for p in pool:
        k = (p["mercado"].replace("Home ", "").replace("Away ", ""), p.get("jugador"), p.get("campo"))
        if k not in mejor or p["prob_aprendida"] > mejor[k]["prob_aprendida"]:
            mejor[k] = p
    return sorted(mejor.values(), key=lambda p: -p["prob_aprendida"])


def coherente(comb):
    import picks as P
    from plantillas import cumple
    lados = {P.lado_pick(p) for p in comb if p["mercado"] in RESULTADO} - {None}
    if len(lados) > 1:
        return False
    jug = [p.get("jugador") for p in comb if p.get("jugador")]
    if len(set(jug)) < len(jug):
        return False
    return any(all(cumple(p, gl, gv) is not False for p in comb) for gl in range(7) for gv in range(7))


def mejor_combi(pool, patas, cuota, prob_min=0.0, una_por_partido=False):
    """La combinación que más devuelve a la larga (prob × cuota) dentro de los límites."""
    best = None
    cand = [p for p in pool if p["prob_aprendida"] >= prob_min][:16]
    for n in range(patas[0], patas[1] + 1):
        for comb in itertools.combinations(cand, n):
            c = math.prod(p["cuota"] for p in comb)
            if not cuota[0] <= c <= cuota[1]:
                continue
            if una_por_partido and len({p["partido_id"] for p in comb}) < n:
                continue
            if not una_por_partido and not coherente(comb):
                continue
            s = math.prod(p["prob_aprendida"] for p in comb) * c
            if not best or s > best[0]:
                best = (s, list(comb), round(c, 2))
    return best


def del_dia(dia, hist=None, ap=None):
    """{'partidos': [(cp, cuota, tarjeta, hora)], 'tres': (picks, cuota), 'loca': (picks, cuota)}"""
    import picks as P
    from bot import DATOS
    from plantillas import datos_tarjeta, grandeza
    hist = hist if hist is not None else P.historial()
    ap = ap if ap is not None else (leer(DATOS / "aprendizaje.json") or {})
    pools = []
    for f in EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido")
        if not pa or datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID).strftime("%Y-%m-%d") != dia:
            continue
        pool = pool_partido(ex, hist, ap)
        if pool:
            pools.append(pool)
    # 1) combi de cada partido: grandes primero
    partidos = []
    for pool in pools:
        r = mejor_combi(pool, PARTIDO["patas"], PARTIDO["cuota"], PARTIDO["prob_min"])
        if r:
            b = pool[0]
            cp = {k: b[k] for k in ("partido_id", "fecha", "competicion", "liga_id", "local", "visitante")}
            cp["picks"] = r[1]
            partidos.append((grandeza(cp), r[0], cp, r[2]))
    partidos.sort(key=lambda x: (-x[0], -x[1]))
    elegidos = [(cp, c) for _, _, cp, c in partidos[:PARTIDO["max"]]]
    # horas: 50 min antes; si chocan, cada 30 min hacia atrás
    usadas, salida = [], []
    for cp, c in sorted(elegidos, key=lambda x: x[0]["fecha"], reverse=True):
        h = datetime.fromisoformat(cp["fecha"]).replace(tzinfo=MADRID) - timedelta(minutes=50)
        while any(abs((h - u).total_seconds()) < 30 * 60 for u in usadas):
            h -= timedelta(minutes=30)
        usadas.append(h)
        salida.append((cp, c, datos_tarjeta(cp), h))
    salida.sort(key=lambda x: x[3])
    # 2) multis con el mejor pick de cada partido que empiece después de la hora del post
    res = {"partidos": salida}
    f0 = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    for clave, cfg in (("tres", TRES), ("loca", LOCA)):
        hora = f0.replace(hour=cfg["hora"][0], minute=cfg["hora"][1])
        mejores = []
        for pool in pools:
            ok = [p for p in pool if p["prob_aprendida"] >= PROB_MIN_MULTI
                  and datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID) >= hora + timedelta(minutes=60)]
            if ok:
                mejores.append(ok[0])
        mejores.sort(key=lambda p: -p["prob_aprendida"])
        r = mejor_combi(mejores, cfg["patas"], cfg["cuota"], una_por_partido=True)
        res[clave] = (r[1], r[2], hora) if r else None
    return res
