"""
Datos de la app de Combilocas · docs/datos.json

Junta en un solo archivo todo lo que enseña la app (docs/index.html):
partidos de hoy y mañana con su ficha, picks, combis, escalera, en directo,
clasificaciones, patrones, alertas de cuota, aciertos y beneficio, redes,
publicaciones (calendario, archivo, muro de verdes, ideas) y estado del bot.
Se ejecuta tras plantillas.py y en el bucle de Telegram cada ~10 min. No usa la API.
"""

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

from bot import COMPETICIONES, DATOS, MADRID, PARTIDOS, RAIZ, leer
from picks import evaluar_pick, texto_pick
from plantillas import atractivo
from publicados import evaluar, picks_de_post, progreso, entender
from resumen_dia import balance
from incidencias import identificador, motivo_bloqueo

SALIDA = RAIZ / "docs" / "datos.json"
CUOTAS_INICIO = DATOS / "cuotas_inicio.json"
LIGAS = [140, 39, 135, 78, 61]
FT = {"FT", "AET", "PEN"}
EN_JUEGO = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}


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


def fecha_iso(iso):
    if not iso:
        return None
    fecha = datetime.fromisoformat(iso.replace('Z', '+00:00'))
    return (fecha if fecha.tzinfo else fecha.replace(tzinfo=MADRID)).isoformat()


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
            "ultimos": filas[:6]}


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


def valor_es():
    """Picks con valor del modelo, con el texto en español (sin 'menos de 2,5/3,5 goles')."""
    salida = []
    for v in leer(DATOS / "valor.json", []) or []:
        if v["mercado"] == "Goals Over/Under" and v["opcion"] in ("Under 2.5", "Under 3.5"):
            continue
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
            .replace('fetch("datos.json', 'fetch("../datos.json'))
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
                "actualizado": vivo.get("visto"), "actualizado_iso": fecha_iso(vivo.get("visto")),
                "ficha": None if h.strftime("%Y-%m-%d") == ayer else {
                    "local": ficha_equipo(f["teams"]["home"]["id"], f["teams"]["home"]["name"], hist),
                    "visitante": ficha_equipo(f["teams"]["away"]["id"], f["teams"]["away"]["name"], hist)}})
    partidos.sort(key=lambda p: p["fecha"])
    estado_partido = {p["id"]: p for p in partidos}

    # --- picks y su estado (pendiente / en juego bien-mal / verde / rojo)
    def estado_pick(p):
        return estado_seleccion(p, datos_partido(p["partido_id"]), reg.get(clave(p)))

    def ligero(p):
        return {"id": clave(p), "partido_id": p["partido_id"], "fecha": p["fecha"], "competicion": p.get("competicion"),
                "partido": f"{p['local']} – {p['visitante']}", "texto": p["texto"], "cuota": p["cuota"],
                "frecuencia": round(p["frecuencia"] * 100), "detalle": p.get("detalle"), "tipo": p.get("tipo"),
                "valor": round(p.get("ventaja", 0) * 100), "estado": estado_pick(p),
                "progreso": progreso(entender(p["texto"])[0], datos_partido(p["partido_id"])),
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
                  if p.get("fecha", "")[:10] == dia and k not in ya and "partido_id" in p]
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
    escalera = {"actual": esc.get("actual"), "historial": (esc.get("historial") or [])[-20:]}
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

    def resultado_post(p):
        sel = p.get("sel")
        if not sel:
            return p.get("resultado")
        r = [reg.get(k, {}).get("acierto") for k in sel]
        return "verde" if r and all(x is True for x in r) else "rojo" if any(x is False for x in r) else None

    def cuota_post(t):
        m = re.search(r"[Cc]uota(?: total)?:?\s*~?(\d+[.,]\d+)", t)
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
            calendario.append(base)
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
    desde36 = (ahora - timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M")
    for p in todos:
        if not (p.get("enviado") or p.get("mensaje_id") or p.get("redes")) or p.get("borrar") or p["fecha"] < desde36:
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
        publicados_hoy.append({"id": p["id"], "titulo": p["texto"].strip().splitlines()[0], "fecha": p["fecha"],
                               "cuota": cuota_post(p["texto"]), "estado": est, "picks": filas})

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
           "picks_generados": picks.get("generado")}

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
             "resumenes": resumenes,
             "partidos": partidos, "dias": dias, "alertas": alertas[:10], "escalera": escalera,
             "valor": valor_es(), "clasificaciones": clasificaciones(),
             "patrones": patrones(hist, nombres), "aciertos": aciertos, "calendario": calendario,
             "publicados": publicados, "publicados_hoy": publicados_hoy, "muro": muro[:20], "ideas": ideas, "redes": stats, "bot": bot}
    SALIDA.parent.mkdir(exist_ok=True)
    copia_publica()
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"App: {len(partidos)} partidos · {sum(len(d['picks']) for d in dias.values())} picks · "
          f"{len(publicados)} publicados · {SALIDA.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
