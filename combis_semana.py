"""
20/11 (Marcos, con capturas de cuentas de X: «Aumento Athletic vs Espanyol: 2 faltas G. Bauza: cumple en 3/4…»):
combis de UN PARTIDO POR PATA, cada pata ~@1,50, con el dato del jugador detrás. Las prepara el bot con días de
antelación (las cuotas bajan durante el finde: Bauza recibirá falta 1,50 → 1,15), Marcos las monta en bet365, manda
la captura y se suben a Threads, X y Telegram (Telegram, 1 al día como mucho).

  · viernes ≥ 10:00: las del finde (sábado a lunes), una por liga
  · martes ≥ 10:00: las de entre semana (martes a jueves)

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
            out.append({"sel": f"{p['id']}|{m}|{o}", "texto": f"{nombre}: {plant.format(n=umbral, s='' if umbral == 1 else 's')}",
                        "cuota": c, "dato": f"cumple {cumple}/{de} siendo titular · {coma(p90)} por 90' ({'-'.join(map(str, vals))})",
                        "nota": cumple / de - abs(c - OBJETIVO) * 0.3})
    return out


def _pct(x):
    try:
        return int(str(x or 0).rstrip("%") or 0)
    except ValueError:
        return 0


def patas_equipo(p):
    out, c = [], p.get("cuotas_bet365") or {}
    sl, sv = p.get("stats_local") or {}, p.get("stats_visitante") or {}
    g = lambda m, k: next((float(v) for n_, v in c.get(m, []) if n_ == k), None)
    L, V = p["local"], p["visitante"]
    for lado, k, eq, s, r in (("l", "Home", L, sl, sv), ("v", "Away", V, sv, sl)):
        cu = g("Match Winner", k)
        if cu and CUOTA_MIN <= cu <= CUOTA_MAX and s.get("forma", "").count("V") >= 3:
            out.append({"sel": f"{p['id']}|Match Winner|{k}", "texto": f"Gana {eq}", "cuota": cu,
                        "dato": f"{eq}: {s.get('forma')} en sus últimos 5", "nota": 0.72 - abs(cu - OBJETIVO) * 0.3})
        cu = g("Total - Home" if lado == "l" else "Total - Away", "Over 1.5")
        if cu and CUOTA_MIN <= cu <= CUOTA_MAX and (s.get("gf") or 0) >= 1.8 and (r.get("gc") or 0) >= 1.3:
            out.append({"sel": f"{p['id']}|{'Total - Home' if lado == 'l' else 'Total - Away'}|Over 1.5",
                        "texto": f"{eq} marca 2 o más", "cuota": cu,
                        "dato": f"{eq} marca {coma(s.get('gf'), 1)} goles por partido y el rival encaja {coma(r.get('gc'), 1)}",
                        "nota": 0.7 - abs(cu - OBJETIVO) * 0.3})
    cu = g("Both Teams Score", "Yes")
    a, b = _pct(sl.get("btts")), _pct(sv.get("btts"))
    if cu and CUOTA_MIN <= cu <= 1.75 and min(a, b) >= 60:
        out.append({"sel": f"{p['id']}|Both Teams Score|Yes", "texto": "Ambos marcan", "cuota": cu,
                    "dato": f"marcan los dos en el {a}% y el {b}% de sus partidos", "nota": min(a, b) / 100 - abs(cu - OBJETIVO) * 0.3})
    cu = g("Goals Over/Under", "Over 2.5")
    a, b = _pct(sl.get("o25")), _pct(sv.get("o25"))
    if cu and CUOTA_MIN <= cu <= CUOTA_MAX and min(a, b) >= 60:
        out.append({"sel": f"{p['id']}|Goals Over/Under|Over 2.5", "texto": "Más de 2,5 goles", "cuota": cu,
                    "dato": f"más de 2,5 goles en el {a}% y el {b}% de sus partidos", "nota": min(a, b) / 100 - abs(cu - OBJETIVO) * 0.3})
    return out


def generar(desde, hasta, partidos=None, h=None, max_combis=4):
    """Combis por liga con los partidos entre desde y hasta (fechas AAAA-MM-DD, ambas incluidas)."""
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
            cands = patas_jugador(p, h) + patas_equipo(p)
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


if __name__ == "__main__":
    import sys
    ahora = datetime.now(MADRID)
    rango = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else de_hoy(ahora)
    if rango:
        for i, c in enumerate(generar(*rango), 1):
            print(texto_aviso(c, i, 4), "\n")
