"""
02/11 (Marcos, viendo el post de carlabetss «LOS PICKS POTENTES WEEK», que funcionó muy bien): las semanas con
Champions / Europa League / Conference, el lunes por la noche sale «LOS PICKS DE LA SEMANA» con los favoritos
de cada día y competición (GANA o GANA O EMPATA), y el viernes el resultado («X DE Y»).

Elección: favorito de bet365 (probabilidad sin margen) ≥ 58 % → GANA; entre 48 y 58 % y que haya ganado 6 de sus
últimos 10 → GANA O EMPATA. Hasta 4 por día y competición (solo si hay 2 o más) y 16 en total.
Lo llama plantillas.py (post del lunes y resultado del viernes).
"""
from datetime import datetime, timedelta

from bot import EXTRA, MADRID, PARTIDOS, RAIZ, leer

COMPES = {2: "CHAMPIONS LEAGUE", 3: "EUROPA LEAGUE", 848: "CONFERENCE LEAGUE"}
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
GANA, DOBLE, VICTORIAS = 0.58, 0.48, 6
POR_GRUPO, MAX_TOTAL, MIN_TOTAL = 4, 16, 6
HORA = (23, 30)          # lunes
HORA_RESULTADO = (12, 0)  # viernes

# nombres cortos para el post
CORTO = {"Paris Saint Germain": "PSG", "Bayer Leverkusen": "LEVERKUSEN", "Lask Linz": "LASK", "Bayern München": "BAYERN",
         "Borussia Dortmund": "DORTMUND", "Atletico Madrid": "ATLÉTICO", "Manchester City": "MANCHESTER CITY",
         "Manchester United": "MANCHESTER UNITED", "FK Crvena Zvezda": "ESTRELLA ROJA", "FC Copenhagen": "COPENHAGUE"}


def pais_equipo(nombre):
    """País del equipo por su liga (calendarios guardados); si no se sabe, None."""
    from bot import DATOS
    if not hasattr(pais_equipo, "idx"):
        idx = {}
        for f in DATOS.glob("calendario_*.json"):
            for x in leer(f, []) or []:
                if x["league"]["id"] in COMPES:
                    continue
                for lado in ("home", "away"):
                    idx.setdefault(x["teams"][lado]["name"], x["league"].get("country"))
        idx.update(leer(DATOS / "paises_equipos.json", {}) or {})   # 03/11: equipos de copas europeas (bot.py los pide a la API)
        pais_equipo.idx = idx
    sel = SELECCIONES.get(nombre, nombre)   # 08/11: selecciones (Nations League): el país es el propio equipo
    if sel in BANDERAS:
        return sel
    return pais_equipo.idx.get(nombre)


SELECCIONES = {"Czech Republic": "Czech-Republic", "Czechia": "Czech-Republic", "Türkiye": "Turkey",
               "North Macedonia": "North-Macedonia", "Faroe Islands": "Faroe-Islands",
               "Bosnia and Herzegovina": "Bosnia", "Bosnia & Herzegovina": "Bosnia", "Republic of Ireland": "Ireland",
               "Northern Ireland": "Northern-Ireland"}


BANDERAS = {"Slovakia": "🇸🇰", "Hungary": "🇭🇺", "Slovenia": "🇸🇮", "Kazakhstan": "🇰🇿", "Cyprus": "🇨🇾", "Armenia": "🇦🇲",
            "Lithuania": "🇱🇹", "Georgia": "🇬🇪", "Gibraltar": "🇬🇮", "Andorra": "🇦🇩", "Azerbaijan": "🇦🇿", "Bulgaria": "🇧🇬",
            "Sweden": "🇸🇪", "Israel": "🇮🇱", "Romania": "🇷🇴", "Finland": "🇫🇮", "Ireland": "🇮🇪", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
            "Iceland": "🇮🇸", "Latvia": "🇱🇻", "Estonia": "🇪🇪", "Albania": "🇦🇱", "Montenegro": "🇲🇪", "Bosnia": "🇧🇦",
            "Moldova": "🇲🇩", "Kosovo": "🇽🇰", "Belarus": "🇧🇾", "Russia": "🇷🇺", "Malta": "🇲🇹", "Luxembourg": "🇱🇺",
            "Faroe-Islands": "🇫🇴", "North-Macedonia": "🇲🇰", "Brazil": "🇧🇷", "Argentina": "🇦🇷", "USA": "🇺🇸", "Mexico": "🇲🇽",
            "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Italy": "🇮🇹", "Germany": "🇩🇪", "France": "🇫🇷", "Portugal": "🇵🇹",
            "Netherlands": "🇳🇱", "Austria": "🇦🇹", "Belgium": "🇧🇪", "Turkey": "🇹🇷", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
            "Norway": "🇳🇴", "Denmark": "🇩🇰", "Greece": "🇬🇷", "Switzerland": "🇨🇭", "Serbia": "🇷🇸",
            "Croatia": "🇭🇷", "Czech-Republic": "🇨🇿", "Ukraine": "🇺🇦", "Poland": "🇵🇱"}


def picks_semana(lunes, hist=None, por_grupo=None):
    """[(fecha, liga, texto, pick)] de martes a jueves de la semana del lunes dado."""
    import combis_dia as C
    import picks as P
    hist = hist if hist is not None else P.historial()
    grupos = {}
    for f in EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido")
        if not pa or pa["league"]["id"] not in COMPES or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
            continue
        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        d = (ini.date() - datetime.fromisoformat(lunes).date()).days
        if not 1 <= d <= 3:
            continue
        fav = C.favorito(ex) or {}
        lado, pr = max((("home", fav.get("Home", 0)), ("away", fav.get("Away", 0))), key=lambda x: x[1])
        eq = pa["teams"][lado]
        ult = hist.get(eq["id"], [])[:10]
        gan = sum(1 for p in ult if (p.get("goles_90") or p["goles"])[0] != (p.get("goles_90") or p["goles"])[1]
                  and (((p.get("goles_90") or p["goles"])[0] > (p.get("goles_90") or p["goles"])[1]) == (p["local"]["id"] == eq["id"])))
        o1x2 = "Home" if lado == "home" else "Away"
        if pr >= GANA:
            m, o, txt = "Match Winner", o1x2, "GANA"
        elif pr >= DOBLE and gan >= VICTORIAS:
            m, o, txt = "Double Chance", ("Home/Draw" if lado == "home" else "Draw/Away"), "GANA O EMPATA"
        else:
            continue
        cuota = next((float(c) for oo, c in (ex.get("cuotas") or {}).get(m, []) if oo == o), None)
        nombre = CORTO.get(eq["name"], eq["name"].upper())
        linea = f"{BANDERAS.get(pais_equipo(eq['name']), '⚽')} {nombre} — {txt}"
        pick = {"partido_id": pa["fixture"]["id"], "mercado": m, "opcion": o, "cuota": cuota,
                "fecha": ini.strftime("%Y-%m-%dT%H:%M")}
        grupos.setdefault((ini.strftime("%Y-%m-%d"), pa["league"]["id"]), []).append((pr, linea, pick))
    salida = []
    for (dia, liga), l in sorted(grupos.items(), key=lambda x: (x[0][0], list(COMPES).index(x[0][1]))):
        if len(l) < 2:
            continue
        for pr, linea, pick in sorted(l, key=lambda x: -x[0])[:por_grupo or POR_GRUPO]:
            salida.append((dia, liga, linea, pick))
    return salida[:MAX_TOTAL]


def post(dia, hist=None):
    """(tipo, hora, picks, texto) el lunes de una semana europea, o None."""
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    if f.weekday() != 0:
        return None
    for por in (POR_GRUPO, 3, 2):   # que quepa en Threads (500)
        sel = picks_semana(dia, hist, por)
        if len(sel) < MIN_TOTAL:
            return None
        lineas = ["🏆🔥 LOS PICKS DE LA SEMANA · COMBILOCAS 🔥🏆"]
        actual = None
        for d, liga, linea, _ in sel:
            if (d, liga) != actual:
                actual = (d, liga)
                lineas += ["", f"🏆 {DIAS[datetime.fromisoformat(d).weekday()]} — {COMPES[liga]}"]
            lineas.append(linea)
        lineas += ["", "📊 ¿Cuántos aciertas tú? 👇💚"]
        texto = "\n".join(lineas)
        if len(texto) <= 490:
            break
    return ("semana-europa", f.replace(hour=HORA[0], minute=HORA[1]), [p for *_, p in sel], texto)


def acierto(sel_txt):
    """True/False/None (sin terminar) de «fid|mercado|opción» (solo ganador y doble oportunidad)."""
    fid, m, o = sel_txt.split("|", 2)
    p = leer(PARTIDOS / f"{fid}.json")
    if not p or p.get("estado") not in ("FT", "AET", "PEN"):
        return None
    gl, gv = (p.get("goles_90") or p["goles"])[:2]
    res = "Home" if gl > gv else "Away" if gv > gl else "Draw"
    if m == "Match Winner":
        return res == o
    return res in o.split("/")


def resultado(dia):
    """(tipo, hora, [], texto) el viernes, con el resultado del post del lunes (si ya han terminado todos)."""
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    if f.weekday() != 4:
        return None
    lunes = (f - timedelta(days=4)).strftime("%Y-%m-%d")
    post_lunes = None
    for nombre in ("cola.json", "auto.json"):
        for p in leer(RAIZ / "publicaciones" / nombre, []) or []:
            if p.get("id") == f"{lunes}-semana-europa" and p.get("sel"):
                post_lunes = p
    if not post_lunes:
        return None
    lineas_post = [l for l in post_lunes["texto"].splitlines() if " — GANA" in l]
    res = [acierto(s) for s in post_lunes["sel"]]
    if any(r is None for r in res) or len(lineas_post) != len(res):
        return None
    ok = sum(res)
    cab = "✅💚 ¡PLENO" if ok == len(res) else "📊 RESULTADO"
    lineas = [f"{cab} · LOS PICKS DE LA SEMANA: {ok} DE {len(res)}! 🏆", ""]
    lineas += [("✅ " if r else "❌ ") + l for l, r in zip(lineas_post, res)]
    lineas += ["", "🔥 El lunes, los de la semana que viene 👀"]
    return ("semana-europa-resultado", f.replace(hour=HORA_RESULTADO[0], minute=HORA_RESULTADO[1]), [], "\n".join(lineas))
