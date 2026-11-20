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
LIGAS = ("LaLiga", "Premier League", "Serie A", "Bundesliga", "Ligue 1", "Eredivisie", "Champions League",
         "Europa League", "Segunda División", "Primeira Liga")
BANDERA = {"LaLiga": "🇪🇸", "Segunda División": "🇪🇸", "Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Serie A": "🇮🇹",
           "Bundesliga": "🇩🇪", "Ligue 1": "🇫🇷", "Eredivisie": "🇳🇱", "Primeira Liga": "🇵🇹",
           "Champions League": "⭐", "Europa League": "🟠"}
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


def equipos_partido(pid):
    t = ((leer(DATOS / "proximos" / f"{pid}.json", {}) or {}).get("partido") or {}).get("teams") or {}
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
                          (cumple + 1) / (de + 2) + 0.05,   # suavizado (5/6 → 0,80) + 0,05 por ser titular fijo
                          f"cumple {cumple}/{de} siendo titular · {coma(p90)} por 90' ({'-'.join(map(str, vals))})")
            if x:
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
    return [x for x in out if x]


def generar(desde, hasta, partidos=None, h=None, max_combis=6, fuera=(), empieza_despues=None):
    """Combis por liga con los partidos entre desde y hasta (fechas AAAA-MM-DD, ambas incluidas).
    20/11 (Marcos: «no quiero las cosas 20.000 veces repetidas»): sin las selecciones de «fuera» (lo ya subido) y
    cada partido en una sola combi; si la mejor pata de un partido ya salió, va la siguiente."""
    if partidos is None:
        d = leer(DATOS / "resumen_proximos.json", []) or []
        partidos = d if isinstance(d, list) else d.get("partidos", [])
    h = historial() if h is None else h
    combis = []
    for liga in LIGAS:
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
                patas.append(dict(b, partido=f"{p['local']}–{p['visitante']}", hora=ini.strftime("%Y-%m-%dT%H:%M")))
        if len(patas) < 4:
            continue
        patas = sorted(sorted(patas, key=lambda x: -x["nota"])[:MAX_PATAS], key=lambda x: x["hora"])
        tot = 1.0
        for x in patas:
            tot *= x["cuota"]
        combis.append({"liga": liga, "patas": patas, "cuota": round(tot, 2), "media": sum(x["nota"] for x in patas) / len(patas)})
    return sorted(combis, key=lambda c: -c["media"])[:max_combis]


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
    lineas = [f"{BANDERA.get(c['liga'], '⚽')} COMBI {c['liga'].upper()} · UNA POR PARTIDO 🔥", ""]
    for x in c["patas"]:
        lineas.append(f"🍀 {x['texto']} ({x['partido']})")
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
    guardadas = guardadas if guardadas is not None else (leer(SALIDA, {}) or {}).get("combis") or []
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
    cs = generar(*rango, fuera=ya_subidas(ahora, g), empieza_despues=ahora + timedelta(minutes=30))
    g = {"dia": ahora.strftime("%Y-%m-%d"), "generado": ahora.isoformat(timespec="minutes"), "rango": list(rango),
         "combis": cs, "subidas": subidas[-300:], "n_subidas": len(subidas[-300:])}
    SALIDA.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"combis_semana: {len(cs)} combis ({', '.join(c['liga'] for c in cs)})")
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
