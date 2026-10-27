"""
Datos de la app de Combilocas · docs/datos.json

Junta en un solo archivo todo lo que enseña la app (docs/index.html):
partidos de hoy y mañana con su ficha, picks, combis, escalera, en directo,
clasificaciones, patrones, alertas de cuota, aciertos y beneficio, redes,
publicaciones (calendario, archivo, muro de verdes, ideas) y estado del bot.
Se ejecuta tras plantillas.py y en el bucle de Telegram cada ~10 min. No usa la API.
"""

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

from bot import COMPETICIONES, DATOS, MADRID, PARTIDOS, RAIZ, leer
from picks import evaluar_pick, texto_pick, es_sin_empate
from plantillas import atractivo
from publicados import evaluar, picks_de_post, progreso, entender
from resumen_dia import balance
from incidencias import identificador, motivo_bloqueo

SALIDA = RAIZ / "docs" / "datos.json"
CUOTAS_INICIO = DATOS / "cuotas_inicio.json"
LIGAS = [140, 39, 135, 78, 61]
FT = {"FT", "AET", "PEN"}
EN_JUEGO = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}


def resumen_modelo():
    """Lo que el bot ha aprendido (aprender.py), para el panel."""
    ap = leer(DATOS / "aprendizaje.json", {}) or {}
    if not ap:
        return None
    filas = [(k, v) for t in ("tipos", "ligas") for k, v in (ap.get(t) or {}).items() if v.get("n", 0) >= 3]
    return {"aciertos": ap.get("aciertos"), "picks": ap.get("picks_usados"), "prometido": ap.get("prometido_medio"),
            "cuota": ap.get("implicita_media"), "peso": ap.get("w_frecuencia"), "generado": ap.get("generado"),
            "castigos": [{"que": k, "ajuste": v["ajuste"], "n": v["n"]} for k, v in sorted(filas, key=lambda x: x[1]["ajuste"])[:5]
                         if v["ajuste"] < -0.01],
            "premios": [{"que": k, "ajuste": v["ajuste"], "n": v["n"]} for k, v in sorted(filas, key=lambda x: -x[1]["ajuste"])[:3]
                        if v["ajuste"] > 0.01]}


def resumen_comunidad(ahora):
    picks = leer(DATOS / "comunidad_picks.json", []) or []
    lunes = (ahora - timedelta(days=ahora.weekday())).strftime("%Y-%m-%d")
    sem = [p for p in picks if p["fecha"] >= lunes]
    return {"participantes": len({p["uid"] for p in sem}), "picks": len(sem)}


def datos_partido(fid):
    final = leer(PARTIDOS / f"{fid}.json")
    if final and final.get("estado") in FT:
        return final
    return leer(DATOS / "en_directo" / f"{fid}.json") or final


def estado_seleccion(p, d, registro=None):
    if registro and registro.get("acierto") is not None:
        return "verde" if registro["acierto"] else "rojo"
    if not d or d.get("estado") not in FT | EN_JUEGO:
        return "pendiente"
    bien = evaluar_pick(p, d)
    if bien is None:
        return "pendiente" if d.get("estado") in FT else "en_juego"
    if d.get("estado") in FT:
        return "verde" if bien else "rojo"
    mercado, opcion = p.get("mercado", ""), p.get("opcion", "")
    if ("First Half" in mercado or "(1st Half)" in mercado) and d.get("estado") != "1H":
        return "verde" if bien else "rojo"
    if mercado == "To Win Either Half" and bien:
        descanso = d.get("descanso") or [None, None]
        if None not in descanso:
            a, b = descanso if opcion == "Home" else descanso[::-1]
            if a > b:
                return "verde"
    acumulativo = (opcion.startswith("Over ") or opcion == "Yes" or p.get("tipo") == "jugador"
                   or mercado == "To Score In Both Halves By Teams")
    # Un ganador provisional no es un acierto. Los mercados acumulativos sí pueden cumplirse antes del final.
    if bien and acumulativo:
        return "verde"
    return "va_bien" if bien else "va_mal"


SUBEN = ("Over", "Yes")   # mercados que, una vez cumplidos, ya no se pueden perder


def fila_sel(sel, cuota, directo, conocidos=None):
    """Estado de una selección guardada como 'partido|mercado|opción' (verde en cuanto se cumple si ya no
    se puede perder; si no, al final del partido)."""
    pid, mercado, opcion = sel.split("|", 2)
    d = datos_partido(int(pid))
    vivo = directo.get(str(pid)) or {}
    nombres = (d or {}).get("local", {}).get("nombre", ""), (d or {}).get("visitante", {}).get("nombre", "")
    if not all(nombres):   # 27/10: partido sin empezar → el nombre sale del calendario, no «sin datos»
        c = next((x for x in conocidos or [] if str(x["id"]) == str(pid)), None)
        if c:
            nombres = c["local"], c["visitante"]
    try:
        texto = texto_pick(mercado, opcion, *nombres) if all(nombres) else f"{mercado} {opcion}"
    except Exception:
        texto = f"{mercado} {opcion}"
    if mercado == "?":   # pata de un boleto que no se ha podido reconocer: se enseña tal cual y no se corrige sola
        texto = opcion
    estado = "pendiente"
    if d and d.get("estado") not in (None, "NS", "TBD", "PST"):
        r = evaluar_pick({"mercado": mercado, "opcion": opcion}, d)
        fin = d.get("estado") in FT
        sube = str(opcion).startswith(SUBEN) or " - " in str(opcion)
        if fin:
            estado = "verde" if r is True else "rojo" if r is False else "sin_datos"
        elif r is True and sube:
            estado = "verde"
        else:
            estado = "va_bien" if r is True else "va_mal" if r is False else "pendiente"
    return {"texto": texto, "cuota": cuota, "partido": " – ".join(nombres) if all(nombres) else None,
            "partido_id": int(pid), "estado": estado, "definitivo": estado in ("verde", "rojo"), "progreso": None,
            "actualizado_iso": fecha_iso(vivo.get("visto")), "marcador": (d or {}).get("goles") or vivo.get("goles"),
            "minuto": vivo.get("minuto"), "estado_partido": (d or {}).get("estado") or vivo.get("estado")}


def tipo_combi(c):
    i, t = c.get("id", ""), c.get("titulo", "")
    if "combi-partido" in i or "COMBI LOCAS" in t or "🆚" in t:
        return "partido", "⚽ Combi de partido"
    if i.endswith("-combi-tres") or "combi-tres" in i:
        return "tres", "🔥 Combi x3"
    if i.endswith("-combi-loca") or "combi-loca" in i or "LOCA" in t:
        return "loca", "🤪 La loca"
    if "escalera" in i:
        return "escalera", "🪜 Escalera"
    return "otras", "📊 Otras combis"


FORMATOS = [("⚽ Combi de partido", r"COMBI LOCAS|🆚| VS "), ("✅ Verdes", r"VERDE"), ("⚽ Quién gana", r"QUIÉN GANA"),
            ("🔥 Picks / listas", r"PICKS|OPCIONES"), ("🪜 Escalera", r"ESCALERA"), ("🤪 La loca", r"\bLA LOCA\b|COMBI LOCA\b"),
            ("🔥 Combis", r"COMBI\b|COMBINADA|COMBI DEL|COMBI X|\bX\d+[,.]\d+|CUOTA"), ("📊 Datos sin apuesta", r"RACHAS|SABÍAS|PICHICHIS|DATOS|PREVIA"),
            ("📋 Balances", r"BALANCE|ASÍ FUE|PLENO")]


def formatos_redes(ahora):
    """27/10: qué formato se ve más en Threads (últimos 30 días), con las métricas de threads_analisis.py."""
    import statistics as st
    d = leer(DATOS / "threads_analisis.json", {}) or {}
    desde = (ahora - timedelta(days=30)).strftime("%Y-%m-%d")
    grupos = {}
    for p in d.get("posts", []):
        if p.get("timestamp", "")[:10] < desde or not p.get("text"):
            continue
        cab = p["text"].strip().splitlines()[0].upper()
        nombre = next((n for n, rx in FORMATOS if re.search(rx, cab)), "📝 Otros")
        m = p.get("metricas") or {}
        grupos.setdefault(nombre, []).append((m.get("views", 0), m.get("likes", 0), m.get("replies", 0), cab[:60], p.get("permalink")))
    filas = []
    for nombre, l in grupos.items():
        mejor = max(l)
        filas.append({"formato": nombre, "posts": len(l), "vistas": int(st.median(x[0] for x in l)),
                      "likes": st.median(x[1] for x in l), "respuestas": st.median(x[2] for x in l),
                      "mejor": mejor[3], "mejor_vistas": mejor[0], "mejor_link": mejor[4]})
    return sorted(filas, key=lambda f: -f["vistas"])


def rentabilidad(resumenes):
    """27/10: cuántas sale de cada tipo de combi y lo que habría dado apostar 1 € a cada una."""
    tabla = {}
    for dia, b in sorted(resumenes.items()):
        for c in b.get("combis", []):
            if c.get("estado") not in ("verde", "rojo") or not c.get("cuota"):
                continue
            k, nombre = tipo_combi(c)
            t = tabla.setdefault(k, {"tipo": nombre, "jugadas": 0, "verdes": 0, "beneficio": 0.0, "cuota_media": 0.0})
            t["jugadas"] += 1
            t["cuota_media"] += c["cuota"]
            if c["estado"] == "verde":
                t["verdes"] += 1
                t["beneficio"] += c["cuota"] - 1
            else:
                t["beneficio"] -= 1
    for t in tabla.values():
        t["pct"] = round(100 * t["verdes"] / t["jugadas"])
        t["cuota_media"] = round(t["cuota_media"] / t["jugadas"], 2)
        t["beneficio"] = round(t["beneficio"], 2)
        t["roi"] = round(100 * t["beneficio"] / t["jugadas"])
    orden = ["partido", "tres", "loca", "escalera", "otras"]
    return [tabla[k] for k in orden if k in tabla]


def fecha_iso(iso):
    if not iso:
        return None
    fecha = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    return (fecha if fecha.tzinfo else fecha.replace(tzinfo=MADRID)).isoformat()


def registro_visible(p, ahora):
    # Conservar el historial, sin volver a recomendar un 12 futuro guardado antes del cambio.
    return not (es_sin_empate(p.get("mercado"), p.get("opcion")) and p.get("fecha")
                and datetime.fromisoformat(fecha_iso(p["fecha"])) > ahora)


def hora(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(MADRID)


def clave(p):
    return f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"


# ------------------------------------------------------------------ equipos

def historial_equipos():
    por = defaultdict(list)
    for f in PARTIDOS.glob("*.json"):
        p = leer(f)
        if not p or p.get("estado") not in FT:
            continue
        for lado in ("local", "visitante"):
            por[p[lado]["id"]].append(p)
    for l in por.values():
        l.sort(key=lambda p: p["fecha"], reverse=True)
    return por


def fila_equipo(eq, p):
    casa = p["local"]["id"] == eq
    rival = p["visitante" if casa else "local"]
    gf, gc = (p["goles"] if casa else p["goles"][::-1]) if p.get("goles") else (None, None)
    s = (p.get("stats") or {}).get(str(eq)) or {}
    sr = (p.get("stats") or {}).get(str(rival["id"])) or {}
    res = None if gf is None else "G" if gf > gc else "E" if gf == gc else "P"
    return {"fecha": p["fecha"][:10], "rival": rival["nombre"], "casa": casa, "gf": gf, "gc": gc, "res": res,
            "corners": s.get("corners"), "corners_total": (s.get("corners") or 0) + (sr.get("corners") or 0),
            "tarjetas": (s.get("amarillas") or 0) + (s.get("rojas") or 0),
            "tarjetas_total": sum((x.get("amarillas") or 0) + (x.get("rojas") or 0) for x in (s, sr)),
            "tiros": s.get("tiros"), "a_puerta": s.get("a_puerta"), "paradas": s.get("paradas")}


def media(l, k):
    v = [x[k] for x in l if x.get(k) is not None]
    return round(sum(v) / len(v), 1) if v else None


def ficha_equipo(eq, nombre, hist, n=10):
    filas = [fila_equipo(eq, p) for p in hist.get(eq, [])[:n]]
    return {"id": eq, "nombre": nombre, "partidos": len(filas),
            "forma": "".join(f["res"] or "-" for f in filas[:5]),
            "medias": {k: media(filas, k) for k in ("gf", "gc", "corners", "corners_total", "tarjetas",
                                                      "tarjetas_total", "tiros", "a_puerta", "paradas")},
            "pct": {"mas25": pct(filas, lambda f: f["gf"] is not None and f["gf"] + f["gc"] > 2.5),
                    "ambos": pct(filas, lambda f: f["gf"] and f["gc"]),
                    "marca": pct(filas, lambda f: f["gf"]),
                    "corners9": pct(filas, lambda f: f["corners_total"] >= 9)},
            "ultimos": filas[:6], "tramos": tramos_gol(eq, hist.get(eq, [])[:n])}


_ARB = None


def extra_partido(f, hist):
    """Árbitro (tarjetas por partido), pronóstico de la API y bajas de cada equipo."""
    global _ARB
    from bot import EXTRA
    from picks import indice_arbitros, nombre_arbitro
    if _ARB is None:
        _ARB = indice_arbitros()
    prox = leer(EXTRA / f"{f['fixture']['id']}.json") or {}
    arb = nombre_arbitro(f["fixture"].get("referee"))
    t = _ARB.get(arb, []) if arb else []
    bajas = {}
    for l in prox.get("lesiones") or []:
        lado = "local" if l.get("equipo") == f["teams"]["home"]["id"] else "visitante"
        if not any(b["jugador"] == l.get("jugador") for b in bajas.get(lado, [])):
            bajas.setdefault(lado, []).append({"jugador": l.get("jugador"), "motivo": l.get("motivo"), "tipo": l.get("tipo")})
    from picks import habituales, mismo_jugador
    importantes = {}
    for lado, eq in (("local", f["teams"]["home"]), ("visitante", f["teams"]["away"])):
        fijos = habituales(eq["id"], hist)
        for b in bajas.get(lado, []):
            fj = next((d for d in fijos.values() if mismo_jugador(b["jugador"], d["nombre"])), None)
            if fj:
                b["titular"] = True
                b["impacto"] = impacto_baja(eq["id"], fj["nombre"], hist)
                importantes.setdefault(lado, []).append(b["jugador"])
    return {"arbitro": {"nombre": arb, "partidos": len(t), "tarjetas": round(sum(t) / len(t), 1) if t else None,
                        "mas5": round(100 * sum(x >= 5 for x in t) / len(t)) if t else None} if arb else None,
            "prediccion": prox.get("prediccion"), "bajas": bajas, "bajas_importantes": importantes,
            "bot_1x2": bot_1x2(f["teams"]["home"]["id"], f["teams"]["away"]["id"], hist)}


def impacto_baja(eq, nombre, hist):
    """Goles a favor por partido del equipo con y sin ese jugador (temporada guardada)."""
    from picks import mismo_jugador
    con, sin = [], []
    for p in hist.get(eq, []):
        if not p.get("goles"):
            continue
        gf = p["goles"][0] if p["local"]["id"] == eq else p["goles"][1]
        jugo = any(mismo_jugador(nombre, j.get("nombre")) and (j.get("min") or 0) >= 45
                   for j in (p.get("jugadores") or {}).get(str(eq)) or [])
        (con if jugo else sin).append(gf)
    if len(con) < 3 or len(sin) < 2:
        return None
    return {"con": round(sum(con) / len(con), 2), "sin": round(sum(sin) / len(sin), 2), "partidos_sin": len(sin)}


def bot_1x2(loc, vis, hist, n=10):
    """Probabilidad 1X2 del bot: % de victorias/empates/derrotas del local y del visitante (al revés), juntos."""
    def res(eq):
        out = []
        for p in hist.get(eq, [])[:n]:
            if not p.get("goles"):
                continue
            a, b = (p["goles"] if p["local"]["id"] == eq else p["goles"][::-1])
            out.append("G" if a > b else "E" if a == b else "P")
        return out
    a, b = res(loc), res(vis)
    if len(a) < 4 or len(b) < 4:
        return None
    l = (a.count("G") / len(a) + b.count("P") / len(b)) / 2
    e = (a.count("E") / len(a) + b.count("E") / len(b)) / 2
    v = (a.count("P") / len(a) + b.count("G") / len(b)) / 2
    tot = l + e + v or 1
    return {"local": round(100 * l / tot), "empate": round(100 * e / tot), "visitante": round(100 * v / tot)}


def ranking_arbitros(partidos):
    """Árbitros ordenados por tarjetas por partido; marca los que pitan en los próximos partidos."""
    from picks import indice_arbitros, nombre_arbitro
    idx = indice_arbitros()
    proximos = {}
    for p in partidos:
        if p.get("arbitro_nombre") and p.get("estado") in ("NS", "TBD"):
            proximos.setdefault(p["arbitro_nombre"], []).append(f"{p['local']} – {p['visitante']} · {p['fecha'][8:10]}/{p['fecha'][5:7]} {p['fecha'][11:]}")
    filas = [{"nombre": a, "partidos": len(t), "media": round(sum(t) / len(t), 1), "mas5": round(100 * sum(x >= 5 for x in t) / len(t)),
              "max": max(t), "proximo": proximos.get(a)} for a, t in idx.items() if len(t) >= 4]
    return sorted(filas, key=lambda x: -x["media"])


def tramos_por_liga():
    """% de goles de cada liga por tramos de 15' (mapa de calor)."""
    from bot import COMPETICIONES, PARTIDOS
    tram = {}
    for fp in PARTIDOS.glob("*.json"):
        p = leer(fp)
        if not p or p.get("liga") not in (140, 39, 135, 78, 61):
            continue
        t = tram.setdefault(COMPETICIONES[p["liga"]], [0] * 6)
        for e in p.get("eventos") or []:
            if e.get("tipo") == "Goal" and e.get("detalle") != "Missed Penalty" and e.get("min") is not None:
                t[min(max((e["min"] - 1) // 15, 0), 5)] += 1
    return {l: {"goles": v, "pct": [round(100 * x / (sum(v) or 1)) for x in v]} for l, v in tram.items()}


def goleadores_que_juegan(partidos, hoy, manana):
    """Los 10 mejores goleadores de cada gran liga que juegan hoy o mañana, con su media y la cuota
    de bet365 de 'marca en cualquier momento' si la hay. Para picks de goleador."""
    from bot import EXTRA
    from picks import mismo_jugador
    g = (leer(DATOS / "goleadores.json", {}) or {}).get("ligas", {})
    salida = []
    for p in partidos:
        if p["fecha"][:10] not in (hoy, manana) or p.get("estado") not in ("NS", "TBD"):
            continue
        cuotas = ((leer(EXTRA / f"{p['id']}.json") or {}).get("cuotas") or {})
        anytime = cuotas.get("Anytime Goal Scorer") or []
        for liga in g.values():
            for i, r in enumerate((liga.get("goles") or [])[:10]):
                if r.get("equipo") not in (p["local"], p["visitante"]) or not r.get("partidos"):
                    continue
                c = next((float(v) for n, v in anytime if mismo_jugador(n, r["jugador"])), None)
                media = (r.get("goles") or 0) / r["partidos"]
                salida.append({"jugador": r["jugador"], "equipo": r["equipo"], "puesto": i + 1, "goles": r.get("goles"),
                               "partidos": r["partidos"], "media": round(media, 2), "cuota": c,
                               "valor": round(media * c - 1, 2) if c else None,
                               "partido": f"{p['local']} – {p['visitante']}", "fecha": p["fecha"]})
    return sorted(salida, key=lambda x: (-(x["valor"] or -9), -x["media"]))[:15]


def tramos_gol(eq, partidos):
    """Goles a favor y en contra por tramos de 15 minutos (90+ cuenta en 76-90)."""
    tram = {"favor": [0] * 6, "contra": [0] * 6}
    for p in partidos:
        for e in p.get("eventos") or []:
            if e.get("tipo") != "Goal" or e.get("detalle") == "Missed Penalty" or e.get("min") is None:
                continue
            i = min(max((e["min"] - 1) // 15, 0), 5)
            propio = (e.get("equipo") == eq) != (e.get("detalle") == "Own Goal")
            tram["favor" if propio else "contra"][i] += 1
    return tram


def pct(filas, cond):
    return round(100 * sum(1 for f in filas if cond(f)) / len(filas)) if filas else None


# ------------------------------------------------------------------ clasificaciones

def clasificaciones():
    tablas = {}
    for liga in LIGAS:
        cal = leer(DATOS / f"calendario_{liga}.json", []) or []
        t = defaultdict(lambda: {"pj": 0, "g": 0, "e": 0, "p": 0, "gf": 0, "gc": 0, "pts": 0, "forma": [], "logo": None})
        for f in sorted(cal, key=lambda x: x["fixture"]["date"]):
            if f["fixture"]["status"]["short"] not in FT:
                continue
            gl, gv = f["goals"]["home"], f["goals"]["away"]
            for eq, a, b in ((f["teams"]["home"], gl, gv), (f["teams"]["away"], gv, gl)):
                r = t[eq["name"]]
                r["logo"] = eq.get("logo")
                r["pj"] += 1; r["gf"] += a; r["gc"] += b
                res = "G" if a > b else "E" if a == b else "P"
                r[{"G": "g", "E": "e", "P": "p"}[res]] += 1
                r["pts"] += {"G": 3, "E": 1, "P": 0}[res]
                r["forma"].append(res)
        filas = []
        for nombre, r in t.items():
            ult = r["forma"][-5:]
            estado = ("racha" if ult.count("G") >= 4 else "crisis" if ult.count("G") == 0 and ult.count("P") >= 3
                      else None)
            filas.append({"equipo": nombre, "logo": r["logo"], "pj": r["pj"], "g": r["g"], "e": r["e"], "p": r["p"],
                          "dg": r["gf"] - r["gc"], "pts": r["pts"], "forma": "".join(ult), "estado": estado})
        filas.sort(key=lambda x: (-x["pts"], -x["dg"], x["equipo"]))
        if filas:
            tablas[COMPETICIONES[liga]] = filas
    return tablas


# ------------------------------------------------------------------ patrones

def patrones(hist, nombres):
    salida = []
    pruebas = [("ve 5+ córners propios", lambda f: (f["corners"] or 0) >= 5),
               ("tiene 9+ córners en el partido", lambda f: f["corners_total"] >= 9),
               ("ve 4+ tarjetas en el partido", lambda f: f["tarjetas_total"] >= 4),
               ("tiene más de 2,5 goles", lambda f: f["gf"] + f["gc"] > 2.5),
               ("marca", lambda f: f["gf"] > 0),
               ("marcan los dos", lambda f: f["gf"] > 0 and f["gc"] > 0),
               ("hace 4+ tiros a puerta", lambda f: (f["a_puerta"] or 0) >= 4)]
    for eq, lista in hist.items():
        if eq not in nombres:
            continue
        filas = [fila_equipo(eq, p) for p in lista[:10]]
        filas = [f for f in filas if f["gf"] is not None]
        if len(filas) < 8:
            continue
        for texto, cond in pruebas:
            n = sum(1 for f in filas if cond(f))
            if n / len(filas) >= 0.9:
                salida.append({"equipo": nombres[eq], "texto": f"{nombres[eq]} {texto} en {n} de sus {len(filas)} últimos partidos",
                               "pct": round(100 * n / len(filas)), "n": n, "de": len(filas)})
    salida.sort(key=lambda x: (-x["pct"], -x["de"], " marca en " in x["texto"]))
    uno, vistos = [], set()
    for x in salida:   # un patrón por equipo, para que haya variedad
        if x["equipo"] not in vistos:
            uno.append(x); vistos.add(x["equipo"])
    return uno[:25]


def pct_real(p):
    """% que se enseña: la probabilidad corregida con lo aprendido y el histórico (la estadística de los
    últimos 10 partidos exagera; ver calibrar_historico.py)."""
    try:
        import aprender
        pr = p.get("prob_aprendida")
        if pr is None:
            pr = aprender.frec_calibrada(p)
        return round(pr * 100)
    except Exception:
        return round(p["frecuencia"] * 100)


def valor_es():
    """Picks con valor del modelo, con el texto en español (sin 'menos de 2,5/3,5 goles')."""
    salida = []
    for v in leer(DATOS / "valor.json", []) or []:
        if es_sin_empate(v["mercado"], v["opcion"]):
            continue
        if str(v["opcion"]).startswith("Under") or v["opcion"] == "No":
            continue   # 26/10: nada de "menos de" en la app
        if v.get("fecha") and hora(v["fecha"]) < datetime.now(MADRID):
            continue   # solo partidos que aún no se han jugado
        l, _, vi = v["partido"].partition(" – ")
        salida.append(dict(v, texto=texto_pick(v["mercado"], v["opcion"], l, vi),
                           hora=hora(v["fecha"]).strftime("%d/%m %H:%M")))
    return salida[:15]


# ------------------------------------------------------------------ versión pública

def copia_publica():
    """docs/publica/ = la misma app sin Contenido ni Bot (la app lo decide por la ruta)."""
    pub = RAIZ / "docs" / "publica"
    pub.mkdir(parents=True, exist_ok=True)
    html = (RAIZ / "docs" / "index.html").read_text(encoding="utf-8")
    html = (html.replace('href="icono-180.png', 'href="../icono-180.png')
            .replace('src="logo.png', 'src="../logo.png')
            )
    (pub / "index.html").write_text(html, encoding="utf-8")
    man = json.loads((RAIZ / "docs" / "manifest.json").read_text(encoding="utf-8"))
    man.update(start_url="./", icons=[dict(i, src="../" + i["src"]) for i in man["icons"]])
    (pub / "manifest.json").write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ main

def main():
    ahora = datetime.now(MADRID)
    hoy, manana = ahora.strftime("%Y-%m-%d"), (ahora + timedelta(days=1)).strftime("%Y-%m-%d")
    ayer = (ahora - timedelta(days=1)).strftime("%Y-%m-%d")
    picks = leer(DATOS / "picks.json", {}) or {}
    reg = leer(DATOS / "registro_aciertos.json", {}) or {}
    directo = leer(DATOS / "en_directo.json", {}) or {}
    hist = historial_equipos()

    # --- partidos de hoy y mañana
    partidos, nombres = [], {}
    for liga in COMPETICIONES:
        for f in leer(DATOS / f"calendario_{liga}.json", []) or []:
            for lado in ("home", "away"):
                nombres[f["teams"][lado]["id"]] = f["teams"][lado]["name"]
            h = hora(f["fixture"]["date"])
            if h.strftime("%Y-%m-%d") not in (ayer, hoy, manana):
                continue
            fid = f["fixture"]["id"]
            vivo = directo.get(str(fid)) or {}
            final = leer(PARTIDOS / f"{fid}.json")
            if final and final.get("estado") in FT:
                vivo = dict(vivo, estado=final["estado"], goles=final["goles"])
            partidos.append({
                "id": fid, "fecha": h.strftime("%Y-%m-%dT%H:%M"), "liga": COMPETICIONES[liga],
                "local": f["teams"]["home"]["name"], "visitante": f["teams"]["away"]["name"],
                "logo_l": f["teams"]["home"].get("logo"), "logo_v": f["teams"]["away"].get("logo"),
                "estado": vivo.get("estado") or f["fixture"]["status"]["short"],
                "minuto": vivo.get("minuto") or f["fixture"]["status"].get("elapsed"),
                "goles": vivo.get("goles") or [f["goals"]["home"], f["goals"]["away"]],
                "arbitro_nombre": (f["fixture"].get("referee") or "").split(",")[0].strip() or None,
                "actualizado": vivo.get("visto"), "actualizado_iso": fecha_iso(vivo.get("visto")),
                "ficha": None if h.strftime("%Y-%m-%d") == ayer else {
                    "local": ficha_equipo(f["teams"]["home"]["id"], f["teams"]["home"]["name"], hist),
                    "visitante": ficha_equipo(f["teams"]["away"]["id"], f["teams"]["away"]["name"], hist),
                    **extra_partido(f, hist)}})
    partidos.sort(key=lambda p: p["fecha"])
    estado_partido = {p["id"]: p for p in partidos}

    # --- picks y su estado (pendiente / en juego bien-mal / verde / rojo)
    def estado_pick(p):
        return estado_seleccion(p, datos_partido(p["partido_id"]), reg.get(clave(p)))

    def serie_cuota(p):
        from bot import EXTRA
        h = ((leer(EXTRA / f"{p['partido_id']}.json") or {}).get("cuotas_hist") or {}).get(f"{p['mercado']}|{p['opcion']}") or []
        return [[x[0], float(x[1])] for x in h[-12:]] if len(h) >= 2 else None

    def a_favor(p):
        """Señales a favor (y en contra) del pick. 'top' si hay 3+ a favor y ninguna en contra."""
        si, no = [], []
        if p["frecuencia"] >= 0.85:
            si.append("datos")
        if p.get("ventaja", 0) >= 0.10:
            si.append("valor")
        vm, mv = p.get("valor_mercado"), p.get("movimiento")
        if vm is not None:
            (si if vm >= 0.03 else no if vm <= -0.05 else []).append("otras casas")
        if mv is not None:
            (si if mv <= -0.05 else no if mv >= 0.08 else []).append("cuota")
        if p.get("temporada"):
            a, b = map(int, p["temporada"].split("/"))
            (si if b and a / b >= 0.8 else no if b and a / b < 0.6 else []).append("temporada")
        return {"si": si, "no": no, "top": len(si) >= 3 and not no}

    def ligero(p):
        return {"id": clave(p), "partido_id": p["partido_id"], "fecha": p["fecha"], "competicion": p.get("competicion"),
                "partido": f"{p['local']} – {p['visitante']}", "texto": p["texto"], "cuota": p["cuota"],
                "frecuencia": round(p["frecuencia"] * 100), "pct_real": pct_real(p), "detalle": p.get("detalle"), "tipo": p.get("tipo"),
                "valor": round(p.get("ventaja", 0) * 100), "estado": estado_pick(p),
                "movimiento": p.get("movimiento"), "cuota_inicial": p.get("cuota_inicial"),
                "valor_mercado": p.get("valor_mercado"), "temporada": p.get("temporada"),
                "progreso": progreso(entender(p["texto"])[0], datos_partido(p["partido_id"])),
                "serie_cuota": serie_cuota(p), "a_favor": a_favor(p),
                "definitivo": p["opcion"].startswith("Over") or p["opcion"] == "Yes" or p.get("tipo") == "jugador"}

    dias = {}
    dias_picks = dict(picks.get("dias") or {})
    for dia in (ayer, hoy, manana):
        dias_picks.setdefault(dia, {})  # Los picks ya empezados desaparecen del selector, pero siguen en el registro.
    for dia, d in dias_picks.items():
        if dia not in (ayer, hoy, manana):
            continue
        combis = {}
        for k, c in (d.get("combis") or {}).items():
            if c:
                legs = [ligero(p) for p in c["picks"]]
                est = ("verde" if all(l["estado"] == "verde" for l in legs) else
                       "rojo" if any(l["estado"] == "rojo" for l in legs) else "pendiente")
                combis[k] = {"cuota": c["cuota"], "picks": legs, "estado": est}
        lista = list(d.get("picks") or [])
        ya = {clave(p) for p in lista}
        lista += [dict(p, detalle=p.get("detalle")) for k, p in reg.items()   # los ya empezados salen de picks.json
                  if p.get("fecha", "")[:10] == dia and k not in ya and "partido_id" in p and registro_visible(p, ahora)]
        dias[dia] = {"picks": [ligero(p) for p in sorted(lista, key=lambda x: x["fecha"])],
                     "combis": combis}

    # --- alertas de cuota: picks fuertes cuya cuota ha subido desde que el bot los vio por primera vez
    inicio = leer(CUOTAS_INICIO, {}) or {}
    alertas = []
    for dia in (hoy, manana):
        for p in ((picks.get("dias") or {}).get(dia) or {}).get("picks", []):
            k = clave(p)
            inicio.setdefault(k, p["cuota"])
            if p["frecuencia"] >= 0.8 and p["cuota"] >= inicio[k] * 1.08 and p["fecha"] > ahora.strftime("%Y-%m-%dT%H:%M"):
                alertas.append(dict(ligero(p), antes=inicio[k], sube=round(100 * (p["cuota"] / inicio[k] - 1))))
    CUOTAS_INICIO.write_text(json.dumps({k: v for k, v in inicio.items() if k.split("|")[0]}, ensure_ascii=False), encoding="utf-8")
    alertas.sort(key=lambda a: -a["sube"])

    # --- escalera
    esc = leer(DATOS / "escalera.json", {}) or {}
    unicos = {}
    for x in esc.get("historial") or []:   # el mismo día y escalón una sola vez (el último)
        unicos[(x.get("dia"), x.get("escalon"))] = x
    escalera = {"actual": esc.get("actual"), "historial": list(unicos.values())[-20:]}
    if escalera["actual"]:
        escalera["actual"] = dict(escalera["actual"], picks=[dict(p, estado=estado_pick(p)) if "mercado" in p else p
                                                             for p in escalera["actual"]["picks"]])

    # --- aciertos y beneficio (10 € por pick)
    hechos = sorted((p for p in reg.values() if p.get("acierto") is not None), key=lambda p: p["fecha"])
    def resumen(lista):
        a = sum(p["acierto"] for p in lista)
        return {"picks": len(lista), "aciertos": a, "pct": round(100 * a / len(lista)) if lista else None,
                "beneficio": round(sum((p["cuota"] - 1) * 10 if p["acierto"] else -10 for p in lista), 2)}
    por_tipo, por_mercado, por_semana, por_mes, por_dia = (defaultdict(list) for _ in range(5))
    for p in hechos:
        por_tipo[p.get("tipo") or "otros"].append(p)
        por_mercado[p["mercado"]].append(p)
        f = datetime.fromisoformat(p["fecha"])
        por_semana[f"{f.isocalendar()[0]}-S{f.isocalendar()[1]:02d}"].append(p)
        por_mes[p["fecha"][:7]].append(p)
        por_dia[p["fecha"][:10]].append(p)
    racha = 0
    for dia in sorted(por_dia, reverse=True):
        r = resumen(por_dia[dia])
        if r["pct"] is not None and r["pct"] >= 70:
            racha += 1
        else:
            break
    aciertos = {"total": resumen(hechos), "racha_dias": racha,
                "por_tipo": {k: resumen(v) for k, v in por_tipo.items()},
                "por_mercado": sorted(({"mercado": k, **resumen(v)} for k, v in por_mercado.items() if len(v) >= 3),
                                      key=lambda x: -x["pct"]),
                "por_semana": [{"semana": k, **resumen(por_semana[k])} for k in sorted(por_semana)[-12:]],
                "por_mes": [{"mes": k, **resumen(por_mes[k])} for k in sorted(por_mes)[-12:]],
                "por_dia": [{"dia": k, **resumen(por_dia[k])} for k in sorted(por_dia)[-14:]]}

    # --- publicaciones: calendario, archivo, muro de verdes
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    est_redes = leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {}
    auto = [dict(p, **enviados.get(p["id"], {}), **est_redes.get(p["id"], {}))
            for p in (leer(RAIZ / "publicaciones" / "auto.json", []) or [])]
    todos = cola + [p for p in auto if p["id"] not in {c["id"] for c in cola}]
    # 27/10: boletos de bet365 que sube el asistente (las patas se leen de la captura)
    todos += [dict(p, fecha=p.get("fecha") or p["enviado"]) for p in leer(RAIZ / "publicaciones" / "asistente.json", []) or []
              if p.get("boleto") and p.get("sel") and p["id"] not in {c["id"] for c in todos}]

    def resultado_post(p):
        sel = p.get("sel")
        if not sel:
            return p.get("resultado")
        r = [reg.get(k, {}).get("acierto") for k in sel]
        return "verde" if r and all(x is True for x in r) else "rojo" if any(x is False for x in r) else None

    def cuota_post(t):
        m = re.search(r"cuota(?: total)?(?: aprox\.)?:?\s*~?(\d+[.,]\d+)", t, re.I) or \
            re.search(r"CREAR APUESTA x(\d+[.,]\d+)", t)   # 27/10: boletos de bet365
        return float(m.group(1).replace(",", ".")) if m else None

    publicados, calendario = [], []
    for p in sorted(todos, key=lambda x: x["fecha"]):
        base = {"id": p["id"], "fecha": p["fecha"], "titulo": p["texto"].strip().splitlines()[0],
                "texto": p["texto"], "foto": p.get("foto"), "cuota": cuota_post(p["texto"]),
                "redes": sorted(k for k, v in (p.get("redes") or {}).items() if v) + (["telegram"] if p.get("mensaje_id") else [])}
        if p.get("enviado") or p.get("mensaje_id") or p.get("redes"):
            if not p.get("borrar"):
                publicados.append(dict(base, resultado=resultado_post(p)))
        elif not p.get("caducada") and p["fecha"] >= ahora.strftime("%Y-%m-%dT%H:%M") and p["fecha"][:10] <= manana:
            # panel de control (26/10): código corto para los botones del bot y si está cancelado o cambiado
            ctl = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
            calendario.append(dict(base, codigo=hashlib.sha1(p["id"].encode()).hexdigest()[:16],
                                   cancelado=p["id"] in ctl.get("cancelados", []),
                                   texto=(ctl.get("textos") or {}).get(p["id"], p["texto"]),
                                   cambiado=p["id"] in (ctl.get("textos") or {}),
                                   destinos=["Telegram"] + (["Threads", "Instagram"] if p.get("directo") else [])))
    publicados = publicados[-300:][::-1]
    semana = (ahora - timedelta(days=7)).strftime("%Y-%m-%d")
    muro = [p for p in publicados if p["resultado"] == "verde" and p["fecha"] >= semana]
    muro += [{"id": f"pick-{p['partido_id']}-{p['opcion']}", "fecha": p["fecha"], "titulo": p["texto"],
              "texto": f"✅ {p['texto']} · {p['cuota']:.2f}", "cuota": p["cuota"], "resultado": "verde", "pick": True,
              "marcador": p.get("marcador"), "partido": f"{p['local']} – {p['visitante']}"}
             for p in hechos if p["acierto"] and p["fecha"] >= semana and p["cuota"] >= 1.5]
    muro.sort(key=lambda p: -(p.get("cuota") or 0))

    # --- ideas de posts: los 3 picks más vendibles de hoy/mañana que aún no han salido en combis
    usados = {k for d in dias.values() for c in d["combis"].values() for k in (l["id"] for l in c["picks"])}
    ideas = []
    for dia in (hoy, manana):
        cand = [p for p in ((picks.get("dias") or {}).get(dia) or {}).get("picks", [])
                if clave(p) not in usados and p["fecha"] > ahora.strftime("%Y-%m-%dT%H:%M")]
        vistos = set()
        for p in sorted(cand, key=atractivo, reverse=True):
            if p["partido_id"] in vistos or len([i for i in ideas if i["dia"] == dia]) >= 3:
                continue
            vistos.add(p["partido_id"])
            txt = (f"🔥 PICK DEL DÍA 🔥\n\n⚽ {p['local']} 🆚 {p['visitante']} · {p['fecha'][11:]}\n\n"
                   f"✅ {p['texto']} · {p['cuota']:.2f}".replace(".", ",") + f"\n\n📊 {p['detalle']} en sus últimos partidos\n\n"
                   "¿Entramos? 👇💚")
            ideas.append({"dia": dia, "texto_post": txt, **ligero(p)})

    # --- picks de lo publicado (también posts a mano), para el directo
    conocidos = [{"id": p["id"], "local": p["local"], "visitante": p["visitante"], "fecha": p["fecha"],
                  "logo_l": p.get("logo_l"), "logo_v": p.get("logo_v")} for p in partidos]
    ya = {p["id"] for p in conocidos}
    for x in (leer(DATOS / "fixtures_dia.json", {}) or {}).get("partidos", []):
        if x["id"] not in ya:
            conocidos.append(dict(x, fecha=hora(x["fecha"]).strftime("%Y-%m-%dT%H:%M")))
    publicados_hoy = []
    desde36 = (ahora - timedelta(days=1)).strftime("%Y-%m-%dT00:00")   # 27/10: ayer entero (la app enseña Ayer/Hoy)
    for p in todos:
        if not (p.get("enviado") or p.get("mensaje_id") or p.get("redes")) or p.get("borrar") or p["fecha"] < desde36:
            continue
        if p.get("cuotas") and p.get("sel") and len(p["cuotas"]) == len(p["sel"]):
            # 27/10: los posts nuevos del bot se corrigen con sus selecciones guardadas (partido|mercado|opción),
            # no leyendo el texto (las combis de partido van en mayúsculas y con [x1.40])
            filas = [fila_sel(s, c, directo, conocidos) for s, c in zip(p["sel"], p["cuotas"])]
            for f, t, pa in zip(filas, p.get("textos") or [], p.get("partidos") or []):   # boletos: el texto de bet365
                f["texto"], f["partido"] = t, f["partido"] or pa
            est = p.get("resultado") or ("verde" if filas and all(x["estado"] == "verde" for x in filas) else
                   "rojo" if any(x["estado"] == "rojo" for x in filas) else "pendiente")
            publicados_hoy.append({"id": p["id"], "titulo": p["texto"].strip().splitlines()[0], "fecha": p["fecha"],
                                   "cuota": cuota_post(p["texto"]), "estado": est, "picks": filas})
            continue
        legs = picks_de_post(p, conocidos)
        if not any(l["partido_id"] for l in legs):
            continue
        filas = []
        for l in legs:
            d = None
            if l["partido_id"]:
                d = datos_partido(l['partido_id'])
            e = evaluar(l["spec"], d) if l["partido_id"] else "sin_datos"
            if e == "sin_datos" and not d and l["partido_id"]:
                e = "pendiente"
            vivo = directo.get(str(l["partido_id"])) or {}
            if d:
                vivo = dict(vivo, goles=d.get("goles"), estado=d.get("estado"))
            filas.append({"texto": l["texto"], "cuota": l["cuota"], "partido": l["partido"], "partido_id": l["partido_id"],
                          "estado": e, "definitivo": e in ("verde", "rojo"), "progreso": progreso(l["spec"], d),
                          "actualizado_iso": fecha_iso(vivo.get("visto")),
                          "marcador": vivo.get("goles"), "minuto": vivo.get("minuto"), "estado_partido": vivo.get("estado")})
        est = p.get("resultado") or ("verde" if all(x["estado"] == "verde" for x in filas) else
               "rojo" if any(x["estado"] == "rojo" for x in filas) else "pendiente")
        lista = bool(re.search(r"QUIÉN GANA|RESULTADOS EXACTOS|PICKS PARA|OPCIONES|RACHAS|DATOS PARA", filas and p["texto"].splitlines()[0].upper() or ""))
        publicados_hoy.append({"id": p["id"], "titulo": p["texto"].strip().splitlines()[0], "fecha": p["fecha"],
                               "cuota": cuota_post(p["texto"]), "estado": est, "picks": filas, "lista": lista})

    # --- redes
    stats = leer(RAIZ / "publicaciones" / "estadisticas.json", {}) or {}

    # --- estado del bot
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    errores = []
    for p in todos:
        if p["fecha"][:10] >= ayer:
            for red, e in (p.get("errores_redes") or {}).items():
                if not (p.get("redes") or {}).get(red):
                    motivo = motivo_bloqueo(p, red, control, ahora)
                    errores.append({"clave": identificador(p["id"], red), "post_id": p["id"],
                                    "post": p["texto"].splitlines()[0][:60], "red": red, "error": str(e)[:160],
                                    "fecha": p["fecha"], "bloqueo": motivo, "reintentable": motivo is None})
            if p.get("error") and not (p.get("enviado") or p.get("mensaje_id")):
                motivo = motivo_bloqueo(p, "telegram", control, ahora)
                errores.append({"clave": identificador(p["id"], "telegram"), "post_id": p["id"],
                                "post": p["texto"].splitlines()[0][:60], "red": "telegram", "error": p["error"][:160],
                                "fecha": p["fecha"], "bloqueo": motivo, "reintentable": motivo is None})
    bot = {"pausa": bool(control.get("pausa")), "redes": leer(RAIZ / "publicaciones" / "estado_redes.json", {}),
           "claves_caducan": "2026-12-21", "errores": errores[-30:],
           "reintentos": list((leer(RAIZ / "publicaciones/reintentos_estado.json", {}) or {}).values())[-10:],
           "spam": (leer(DATOS / "moderacion.json", {}) or {}).get("quitados", [])[-10:][::-1],
           "picks_generados": picks.get("generado"),
           "modelo": resumen_modelo(), "estilos": (leer(DATOS / "estilos.json", {}) or {}).get("estilos", {}),
           "comunidad": resumen_comunidad(ahora)}

    resumenes_ruta = RAIZ / "docs/resumenes.json"
    resumenes = leer(resumenes_ruta, {}) or {}
    for dia in (ayer, hoy):
        anteriores = {p['id']: dict(p, fecha=dia) for p in resumenes.get(dia, {}).get('combis', [])}
        anteriores.update({p['id']: p for p in publicados_hoy if p['fecha'][:10] == dia})
        b = balance(list(anteriores.values()), dia)
        if b["total"]:
            resumenes[dia] = b
    resumenes = {k: resumenes[k] for k in sorted(resumenes)[-30:]}
    resumenes_ruta.write_text(json.dumps(resumenes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    datos = {"generado": ahora.strftime("%Y-%m-%d %H:%M"), "generado_iso": ahora.isoformat(), "hoy": hoy, "manana": manana,
             "resumenes": resumenes, "rentabilidad": rentabilidad(resumenes), "formatos_redes": formatos_redes(ahora),
             "partidos": partidos, "dias": dias, "alertas": alertas[:10], "escalera": escalera,
             "valor": valor_es(), "clasificaciones": clasificaciones(),
             "patrones": patrones(hist, nombres), "aciertos": aciertos, "calendario": calendario,
             "goleadores": (leer(DATOS / "goleadores.json", {}) or {}).get("ligas", {}),
             "goleadores_hoy": goleadores_que_juegan(partidos, hoy, manana),
             "arbitros": ranking_arbitros(partidos), "tramos_liga": tramos_por_liga(),
             "revision": leer(DATOS / "revision_avisos.json", {}) or {}, "publicados": publicados, "publicados_hoy": publicados_hoy, "muro": muro[:20], "ideas": ideas, "redes": stats, "bot": bot}
    SALIDA.parent.mkdir(exist_ok=True)
    copia_publica()
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    # 26/10: la versión pública lee su propio archivo, sin lo interno (estado del bot, calendario, ideas, avisos)
    publico = {k: v for k, v in datos.items() if k not in ("bot", "calendario", "revision", "ideas", "redes")}
    (RAIZ / "docs" / "publica" / "datos.json").write_text(json.dumps(publico, ensure_ascii=False, separators=(",", ":")),
                                                         encoding="utf-8")
    print(f"App: {len(partidos)} partidos · {sum(len(d['picks']) for d in dias.values())} picks · "
          f"{len(publicados)} publicados · {SALIDA.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
