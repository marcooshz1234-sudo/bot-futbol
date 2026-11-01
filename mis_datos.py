"""
01/11 (Marcos): datos de MIS COMBIS (app solo para Marcos, docs/mis/index.html). Sale en docs/mis/datos.json.
Lo llama app_datos.py en cada vuelta (cada ~3 min), como panel_datos.py con el panel.

  combis    las de datos/mis_combis.json (id, fecha, titulo, cuota, sel, cuotas), cada pata con el motor de
            siempre: fila_sel (estado, marcador, progreso) + confirmar.py (comprobando / anulada)
            y la probabilidad que le queda según el bot (orientativa, ver prob_pata)
  picks     los picks del bot de ayer, hoy y mañana (los mismos que la app), para la pestaña Picks
  partidos  todos los partidos de ayer, hoy y mañana de nuestras ligas (COMPETICIONES), aunque no haya pick
  tipos     % de acierto por tipo de pata: mis patas resueltas + las de datos/apuestas_marcos.json
Sin dinero. Nada de esto va a docs/datos.json ni a docs/publica.
"""
import json
import math
import re
from collections import defaultdict

import confirmar
from bot import DATOS, EXTRA, RAIZ, leer

ENTRADA = DATOS / "mis_combis.json"
APUESTAS = DATOS / "apuestas_marcos.json"
SALIDA = RAIZ / "docs" / "mis" / "datos.json"
CAMPOS_PARTIDO = ("id", "fecha", "liga", "local", "visitante", "logo_l", "logo_v", "estado", "minuto", "goles")
FT = {"FT", "AET", "PEN"}
SIN_EMPEZAR = {None, "NS", "TBD"}
LAMBDAS_MEDIAS = (1.45, 1.15)   # goles esperados local / visitante si no hay cuotas de bet365
MAX_GOLES = 6                   # goles por equipo y tramo que se miran en el Poisson


# ------------------------------------------------------------ probabilidad (orientativa, «según el bot»)

def _poisson(lam, n=MAX_GOLES):
    """P(0..n-1 goles); lo que queda por encima se suma al último."""
    p = [math.exp(-lam) * lam ** k / math.factorial(k) for k in range(n)]
    p[-1] += max(0.0, 1 - sum(p))
    return p


def _al_menos(lam, falta):
    """P(Poisson(lam) >= falta)."""
    if falta <= 0:
        return 1.0
    return max(0.0, 1 - sum(math.exp(-lam) * lam ** k / math.factorial(k) for k in range(int(falta))))


def prob_goles_vivo(mercado, opcion, d, minuto, lam):
    """Picks que dependen solo de los goles: Poisson con lo que queda de cada parte. None si el pick no es de goles."""
    import picks as P
    lh, la = lam or LAMBDAS_MEDIAS
    g = d.get("goles") or [None, None]
    if None in g:
        return None
    ep = d.get("estado")
    if ep == "1H":
        r1, desc = max(45 - minuto, 0) / 90, None
    else:
        r1, desc = 0, d.get("descanso") or (g if ep == "HT" else None)
    r2 = 0.5 if ep in ("1H", "HT") else max(90 - minuto, 0) / 90
    base = dict(d, estado="FT", stats={}, jugadores={}, eventos=[])
    pick = {"mercado": mercado, "opcion": opcion}
    uno = [(0, 0, 1.0)] if not r1 else [(i, j, a * b) for i, a in enumerate(_poisson(lh * r1)) for j, b in enumerate(_poisson(la * r1))]
    dos = [(i, j, a * b) for i, a in enumerate(_poisson(lh * r2)) for j, b in enumerate(_poisson(la * r2))]
    bien = total = 0.0
    for i1, j1, w1 in uno:
        d1 = [g[0] + i1, g[1] + j1] if r1 else desc
        for i2, j2, w2 in dos:
            r = P.evaluar_pick(pick, dict(base, goles=[g[0] + i1 + i2, g[1] + j1 + j2], descanso=d1))
            if r is None:
                return None   # necesita algo más que los goles (córners, tiros, jugadores…)
            total += w1 * w2
            bien += w1 * w2 if r else 0
    return bien / total if total else None


def prob_ritmo(actual, objetivo, minuto):
    """Córners, tiros, tarjetas, faltas, paradas: el ritmo de ahora llevado a 90 min (al principio pesa más la línea)."""
    if actual >= objetivo:
        return 1.0
    w = min(1.0, minuto / 45)
    ritmo = w * actual / max(minuto, 1) + (1 - w) * objetivo / 90
    return _al_menos(ritmo * max(90 - minuto, 0), objetivo - actual)


def prob_comparacion(mercado, opcion, d, minuto):
    """«Más córners / tiros a puerta / tiros que…»: lo que lleva cada uno + su ritmo."""
    import picks as P
    campo = P.STATS_1X2.get(mercado)
    st = d.get("stats") or {}
    a = (st.get(str(d["local"]["id"])) or {}).get(campo)
    b = (st.get(str(d["visitante"]["id"])) or {}).get(campo)
    if campo is None or a is None or b is None or minuto < 10:
        return None
    resto = max(90 - minuto, 0) / max(minuto, 1)
    pa, pb = _poisson(a * resto + 0.01, 20), _poisson(b * resto + 0.01, 20)
    p = {"Home": 0.0, "Draw": 0.0, "Away": 0.0}
    for i, x in enumerate(pa):
        for j, y in enumerate(pb):
            p["Home" if a + i > b + j else "Away" if b + j > a + i else "Draw"] += x * y
    return p.get(opcion)


def prob_pata(f, sel, previa, lam):
    """Probabilidad de que la pata salga: verde 1, roja 0, sin empezar la de antes del partido, en juego con el minuto
    y el marcador. None = anulada (no cuenta)."""
    from app_datos import datos_partido
    e = f.get("confirmando") if f["estado"] == "comprobando" else f["estado"]
    if e == "verde":
        return 1.0
    if e == "rojo":
        return 0.0
    if e == "anulada":
        return None
    ep = f.get("estado_partido")
    if ep in SIN_EMPEZAR or ep in FT:
        return previa
    pid, mercado, opcion = sel.split("|", 2)
    d = datos_partido(int(pid)) or {}
    minuto = f.get("minuto") or (45 if ep == "HT" else 0)
    p = None
    try:
        p = prob_goles_vivo(mercado, opcion, d, minuto, lam)
        x = f.get("progreso") or {}
        if p is None and x.get("objetivo") is not None and x.get("actual") is not None:
            p = prob_ritmo(x["actual"], x["objetivo"], minuto)
        if p is None:
            p = prob_comparacion(mercado, opcion, d, minuto)
    except Exception as e:
        print("prob:", sel, str(e)[:80])
    return previa if p is None else min(0.99, max(0.01, p))


def previas(sels, cache):
    """Probabilidad de antes del partido: la prob_aprendida del bot (pool de combis_dia.py, o picks.json),
    o 1/cuota × 0,95 si no la hay. Se calcula mientras el partido no ha empezado y se guarda (cache)."""
    falta = {s for s, _ in sels if s not in cache}
    if not falta:
        return cache
    bot = {}
    for dia in ((leer(DATOS / "picks.json", {}) or {}).get("dias") or {}).values():
        for p in dia.get("picks") or []:
            if p.get("prob_aprendida"):
                bot[f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"] = p["prob_aprendida"]
    try:
        import combis_dia
        import picks as P
        hist, ap = P.historial(), leer(DATOS / "aprendizaje.json") or {}
        for pid in {s.split("|", 1)[0] for s in falta}:
            for p in combis_dia.pool_partido(leer(EXTRA / f"{pid}.json") or {}, hist, ap):
                bot[f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"] = p["prob_aprendida"]
    except Exception as e:
        print("prob previa:", str(e)[:120])
    for s, cuota in sels:
        if s in falta:
            cache[s] = round(bot.get(s) or (0.95 / cuota if cuota else 0.5), 3)
    return cache


def lambdas(pid, cache):
    """Goles esperados de cada equipo según bet365 (modelo_goles.py); se guardan porque las cuotas se van al empezar."""
    if str(pid) not in cache:
        try:
            import modelo_goles
            lam = modelo_goles.lambdas(int(pid))
        except Exception:
            lam = None
        if lam:
            cache[str(pid)] = list(lam)
    return cache.get(str(pid))


# ------------------------------------------------------------ combis

def combi(c, directo, conocidos, conf, prev, lams):
    """Una combi guardada con el estado de cada pata. conf=None: no pasa por confirmar (días ya cerrados)."""
    from app_datos import fila_sel
    filas = [fila_sel(s, q, directo, conocidos) for s, q in zip(c["sel"], c["cuotas"])]
    if conf:
        filas = [conf.pata(f) for f in filas]
    estado = c.get("resultado") or confirmar.estado_combi(filas)
    for f, s in zip(filas, c["sel"]):
        f["sel"] = s
        if estado == "pendiente":
            f["prob"] = prob_pata(f, s, prev.get(s), lambdas(s.split("|", 1)[0], lams))
    out = {"id": c["id"], "fecha": c["fecha"], "titulo": c.get("titulo") or c["id"], "cuota": c.get("cuota_bet365") or c.get("cuota"),
           "estado": estado, "picks": filas}
    if estado == "pendiente":
        ps = [f["prob"] for f in filas if f.get("prob") is not None]
        if ps and len(ps) == sum(1 for f in filas if f["estado"] != "anulada"):
            a = ajuste(c, prev)
            out["prob"] = round(math.prod(ps) ** a, 4)
            out["cuota_justa"] = round(1 / out["prob"], 2) if out["prob"] > 0 else None
            out["ajuste"] = round(a, 3)
    return out


AJUSTE_MIN = 0.4   # como mucho, la combi cuenta como si tuviera el 40 % de sus patas


def ajuste(c, prev):
    """01/11 (Marcos): las patas del mismo partido van juntas (si hay goles, hay tiros y paradas), así que multiplicarlas
    como si fueran independientes da mucho menos de lo que paga bet365 (2 % frente a ~11 % en Burgos–Castellón).
    Se calibra con la cuota de la combi en bet365 («Crear apuesta» ya lo tiene en cuenta): prob = (producto) ** a, con
    «a» tal que antes del partido sale lo que dice bet365 (0,95 / cuota). Con las patas que ya están en verde (1) el
    exponente no cambia nada, y si el bot ve la combi mejor que bet365 no se sube (a = 1)."""
    ps = [prev.get(s) for s in c["sel"]]
    cuota = c.get("cuota_bet365") or c.get("cuota")   # 01/11: la de bet365 si Marcos la ha dado
    if not cuota or None in ps or not all(0 < p < 1 for p in ps):
        return 1.0
    p_bot, p_bet365 = math.prod(ps), min(0.99, 0.95 / cuota)
    if p_bot >= p_bet365:
        return 1.0
    return max(AJUSTE_MIN, math.log(p_bet365) / math.log(p_bot))


# ------------------------------------------------------------ historial por tipo de pata

FAMILIAS = {"goles": "Goles", "resultado": "Resultado", "corners": "Córners", "jugador": "Jugadores",
            "tarjetas": "Tarjetas", "tiros": "Tiros", "fueras": "Otros"}
CAMPOS_JUGADOR = {"paradas": "Paradas del portero", "faltas_r": "Faltas recibidas", "faltas_c": "Faltas cometidas",
                  "a_puerta": "Tiros a puerta de un jugador", "tiros": "Tiros de un jugador", "gol": "Goleador",
                  "goles": "Goleador", "gol_o_asist": "Gol o asistencia", "amarillas": "Tarjeta a un jugador"}


def subtipo(texto, familia, campo=None):
    """Tipo fino de una pata para el top de lo que más acierta / falla."""
    t = texto.lower()
    if familia == "jugador":
        return CAMPOS_JUGADOR.get(campo, "Jugadores (otros)")
    if familia == "resultado":
        if "ambos" in t or "marcan" in t:
            return "Gana y ambos marcan"
        if "empate" in t:
            return "Doble oportunidad"
        return "Gana"
    if familia == "goles":
        if re.search(r"parte|primeros", t):
            return "Goles por partes"
        if "menos" in t:
            return "Menos goles"
        if "ambos" in t or "marcan" in t:
            return "Ambos marcan"
        if "marca" in t:
            return "Marca un equipo"
        return "Más goles"
    if familia == "corners":
        return "Córners del partido" if re.search(r"más de|mas de|en el partido|–", t) else "Córners de un equipo"
    if familia == "tarjetas":
        if "ambos" in t:
            return "Ambos ven tarjeta"
        return "Menos tarjetas" if "menos" in t else "Más tarjetas"
    return FAMILIAS.get(familia, "Otros")


def familia_sel(sel):
    """Familia de una pata guardada como partido|mercado|opción (la misma idea que combis_dia.familia)."""
    import picks as P
    _, m, o = sel.split("|", 2)
    if m in P.JUG_MERCADOS:
        return "jugador", P.JUG_MERCADOS[m][0]
    if "Corner" in m:
        return "corners", None
    if "Card" in m:
        return "tarjetas", None
    if "Shot" in m:
        return "tiros", None
    if "Offside" in m:
        return "fueras", None
    if m in ("Match Winner", "Double Chance", "To Win Either Half", "Win Both Halves", "First Half Winner") \
            or m.startswith("Results/"):
        return "resultado", None
    return "goles", None


def tipos(combis):
    """% de acierto por familia y top 3 de subtipos (mínimo 3 patas) con mis patas resueltas + apuestas_marcos.json."""
    patas = []
    for c in combis:
        for f in c["picks"]:
            if f["estado"] in ("verde", "rojo") and f.get("sel"):
                fam, campo = familia_sel(f["sel"])
                patas.append((fam, subtipo(f["texto"], fam, campo), f["estado"] == "verde"))
    for p in (leer(APUESTAS, {}) or {}).get("patas", []):
        if p.get("acierto") is not None:
            patas.append((p["familia"], subtipo(p["pata"], p["familia"], p.get("campo")), bool(p["acierto"])))

    def tabla(clave):
        t = defaultdict(lambda: [0, 0])
        for x in patas:
            t[clave(x)][0] += 1
            t[clave(x)][1] += x[2]
        return [{"nombre": k, "n": n, "aciertos": a, "pct": round(100 * a / n)} for k, (n, a) in t.items()]
    familias = sorted(tabla(lambda x: FAMILIAS.get(x[0], "Otros")), key=lambda x: (-x["pct"], -x["n"]))
    sub = [x for x in tabla(lambda x: x[1]) if x["n"] >= 3]
    return {"total": len(patas), "aciertos": sum(x[2] for x in patas), "familias": familias,
            "mejor": sorted(sub, key=lambda x: (-x["pct"], -x["n"]))[:3],
            "peor": sorted(sub, key=lambda x: (x["pct"], -x["n"]))[:3]}


# ------------------------------------------------------------ main

def main(ahora, conf, directo, conocidos, partidos, dias, ayer, hoy, manana):
    """conf es el Confirmador de app_datos (el mismo para que no se pisen el estado guardado en confirmar.json)."""
    antes = leer(SALIDA, {}) or {}
    prev, lams = dict(antes.get("previas") or {}), dict(antes.get("lambdas") or {})
    guardadas = [c for c in leer(ENTRADA, []) or [] if c.get("sel") and c.get("cuotas") and len(c["sel"]) == len(c["cuotas"])]
    for c in leer(ENTRADA, []) or []:
        if c not in guardadas:
            print("mis combis: sin sel/cuotas:", c.get("id"))
    # la previa solo de lo que aún no ha empezado (lo de días cerrados no hace falta)
    previas([(s, q) for c in guardadas if c["fecha"][:10] >= hoy for s, q in zip(c["sel"], c["cuotas"])], prev)
    combis = []
    for c in guardadas:
        try:
            # confirmar.py solo guarda 36 h: lo de antes de ayer ya es definitivo y no pasa por él
            combis.append(combi(c, directo, conocidos, conf if c["fecha"][:10] >= ayer else None, prev, lams))
        except Exception as e:
            print("mis combis:", c.get("id"), str(e)[:120])
    picks = [{"partido_id": p["partido_id"], "fecha": p["fecha"], "partido": p["partido"], "competicion": p.get("competicion"),
              "texto": p["texto"], "cuota": p["cuota"], "pct": p.get("pct_real") or p.get("frecuencia"),
              "estado": p["estado"], "progreso": p.get("progreso")}
             for d in (ayer, hoy, manana) for p in (dias.get(d) or {}).get("picks", [])]
    vivas = {s for c in guardadas if c["fecha"][:10] >= ayer for s in c["sel"]}
    datos = {"generado": ahora.strftime("%Y-%m-%d %H:%M"), "ayer": ayer, "hoy": hoy, "manana": manana,
             "combis": sorted(combis, key=lambda c: c["fecha"]),
             "picks": sorted(picks, key=lambda p: p["fecha"]),
             "partidos": [{k: p.get(k) for k in CAMPOS_PARTIDO} for p in partidos],
             "tipos": tipos(combis),
             # para la vuelta siguiente (las cuotas de antes del partido desaparecen al empezar)
             "previas": {s: v for s, v in prev.items() if s in vivas},
             "lambdas": {k: v for k, v in lams.items() if any(s.startswith(k + "|") for s in vivas)}}
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Mis combis: {len(combis)} combis · {len(picks)} picks · {len(partidos)} partidos")
