"""
El Analista · selección de picks y combis.

Se ejecuta después de bot.py. Para cada partido próximo coge las cuotas de
Bet365 y las compara con lo que han hecho de verdad los dos equipos en sus
últimos partidos (porcentaje de veces que se cumplió cada apuesta). No usa
ningún modelo inventado: solo cuotas reales y hechos contados.

Un pick entra si:
- la cuota de Bet365 está entre CUOTA_MIN (1,25) y CUOTA_MAX (1,80),
- se cumplió en >= FREC_MIN (75 %) de los partidos de los dos equipos juntos,
- y en cada equipo por separado en >= FREC_EQUIPO (70 %),
- con al menos MIN_PARTIDOS de cada equipo,
- y la frecuencia real es mayor que la probabilidad que da la cuota (hay valor),
  pero no por más de VENTAJA_MAX (si no, suele ser una muestra engañosa).

Genera:
- datos/picks.json  → picks y combis por día (lo usarán las plantillas de posts)
- PICKS.md          → lo mismo para leerlo
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from bot import DATOS, EXTRA, MADRID, PARTIDOS, RAIZ, leer

CUOTA_MIN = 1.25
CUOTA_MAX = 1.80      # por encima, la muestra suele engañar (rivales de distinto nivel)
VENTAJA_MAX = 0.30    # si la estadística supera a la cuota por más de esto, se desconfía
FREC_MIN = 0.75
FREC_EQUIPO = 0.70
MIN_PARTIDOS = 5
ULTIMOS = 10          # partidos de cada equipo que se miran

COMPETICION = {140: "LaLiga", 39: "Premier", 135: "Serie A", 78: "Bundesliga",
               61: "Ligue 1", 2: "Champions", 3: "Europa League", 848: "Conference"}

TERMINADOS = {"FT", "AET", "PEN"}


# ------------------------------------------------------------ hechos por partido

def lado(p, eq):
    """Devuelve (goles a favor, goles en contra, 1ª parte a favor, 1ª parte en contra, id rival)."""
    loc = p["local"]["id"] == eq
    gf, gc = (p["goles"][0], p["goles"][1]) if loc else (p["goles"][1], p["goles"][0])
    d = p.get("descanso") or [None, None]
    hf, hc = (d[0], d[1]) if loc else (d[1], d[0])
    rival = p["visitante"]["id"] if loc else p["local"]["id"]
    return gf, gc, hf, hc, rival


def stat_total(p, campo):
    s = p.get("stats") or {}
    if len(s) < 2:
        return None
    vals = [(v or {}).get(campo) for v in s.values()]
    if any(v is None for v in vals) and campo != "rojas":
        return None
    return sum(v or 0 for v in vals)


def tarjetas(p):
    a = stat_total(p, "amarillas")
    if a is None:
        return None
    return a + (stat_total(p, "rojas") or 0)


# Cada mercado: (nombre bet365, opción) -> función(p, eq, es_local_en_el_proximo) -> True/False/None
def evaluador(mercado, opcion, es_local):
    """Devuelve una función que dice si la apuesta se habría cumplido en un partido
    pasado, visto desde el equipo eq. es_local indica si eq es el local del partido
    próximo (para mercados de 'local'/'visitante')."""
    o = opcion
    linea = None
    if o.startswith(("Over ", "Under ")):
        linea = float(o.split()[1])
    mas = o.startswith("Over ")

    def cmp(valor):
        if valor is None:
            return None
        return valor > linea if mas else valor < linea

    if mercado == "Goals Over/Under":
        return lambda p, eq: cmp(sum(p["goles"]))
    if mercado == "Goals Over/Under First Half":
        return lambda p, eq: cmp(sum(p["descanso"])) if p.get("descanso") and None not in p["descanso"] else None
    if mercado == "Corners Over Under":
        return lambda p, eq: cmp(stat_total(p, "corners"))
    if mercado == "Cards Over/Under":
        return lambda p, eq: cmp(tarjetas(p))
    if mercado == "Both Teams Score":
        si = o == "Yes"
        return lambda p, eq: (min(p["goles"]) > 0) == si
    if mercado in ("Total - Home", "Total - Away"):
        # equipo del mercado marca más/menos de X. Para el propio equipo: sus goles a favor;
        # para el rival: lo que encaja.
        propio = (mercado == "Total - Home") == es_local
        return lambda p, eq: cmp(lado(p, eq)[0] if propio else lado(p, eq)[1])
    if mercado in ("Match Winner", "Double Chance"):
        # resultado visto desde el equipo eq: 'G', 'E', 'P'
        def res(p, eq):
            gf, gc = lado(p, eq)[:2]
            return "G" if gf > gc else "E" if gf == gc else "P"
        # traducir la opción a resultados válidos para el local y para el visitante del próximo
        valid_local = {"Home": {"G"}, "Draw": {"E"}, "Away": {"P"},
                       "Home/Draw": {"G", "E"}, "Home/Away": {"G", "P"}, "Draw/Away": {"E", "P"}}[o]
        if es_local:
            ok = valid_local
        else:  # para el visitante, G/P se invierten
            inv = {"G": "P", "P": "G", "E": "E"}
            ok = {inv[x] for x in valid_local}
        return lambda p, eq: res(p, eq) in ok
    return None


# ------------------------------------------------------------ textos

def texto_pick(mercado, opcion, local, visit):
    o = opcion
    if o.startswith(("Over ", "Under ")):
        n = o.split()[1].replace(".", ",")
        mm = "Más" if o.startswith("Over") else "Menos"
    if mercado == "Goals Over/Under":
        return f"{mm} de {n} goles en {local}–{visit}"
    if mercado == "Goals Over/Under First Half":
        return f"{mm} de {n} goles en la 1ª parte del {local}–{visit}"
    if mercado == "Corners Over Under":
        return f"{mm} de {n} córners en {local}–{visit}"
    if mercado == "Cards Over/Under":
        return f"{mm} de {n} tarjetas en {local}–{visit}"
    if mercado == "Both Teams Score":
        return f"Ambos marcan en {local}–{visit}" if o == "Yes" else f"No marcan los dos en {local}–{visit}"
    if mercado == "Total - Home":
        return f"{local} marca {mm.lower()} de {n} goles"
    if mercado == "Total - Away":
        return f"{visit} marca {mm.lower()} de {n} goles"
    if mercado == "Match Winner":
        return {"Home": f"Gana el {local}", "Away": f"Gana el {visit}", "Draw": f"Empate en {local}–{visit}"}[o]
    if mercado == "Double Chance":
        return {"Home/Draw": f"{local} o empate", "Draw/Away": f"{visit} o empate",
                "Home/Away": f"No hay empate en {local}–{visit}"}[o]
    return f"{mercado} {o}"


# ------------------------------------------------------------ cálculo

def historial():
    idx = defaultdict(list)
    for f in PARTIDOS.glob("*.json"):
        p = leer(f)
        if not p or p.get("estado") not in TERMINADOS or not p.get("goles") or None in p["goles"]:
            continue
        idx[p["local"]["id"]].append(p)
        idx[p["visitante"]["id"]].append(p)
    for l in idx.values():
        l.sort(key=lambda p: p["fecha"], reverse=True)
    return idx


def frecuencia(func, partidos):
    vals = [func(p, eq) for p, eq in partidos]
    vals = [v for v in vals if v is not None]
    return (sum(vals), len(vals)) if vals else (0, 0)


def picks_partido(prox, hist, ahora):
    partido = prox["partido"]
    inicio = datetime.fromisoformat(partido["fixture"]["date"])
    if inicio <= ahora or partido["fixture"]["status"]["short"] not in ("NS", "TBD"):
        return []
    loc, vis = partido["teams"]["home"], partido["teams"]["away"]
    h_loc = [(p, loc["id"]) for p in hist.get(loc["id"], [])[:ULTIMOS]]
    h_vis = [(p, vis["id"]) for p in hist.get(vis["id"], [])[:ULTIMOS]]
    if len(h_loc) < MIN_PARTIDOS or len(h_vis) < MIN_PARTIDOS:
        return []
    salida = []
    for mercado, opciones in (prox.get("cuotas") or {}).items():
        for opcion, cuota in opciones:
            try:
                cuota = float(cuota)
            except (TypeError, ValueError):
                continue
            if cuota < CUOTA_MIN or cuota > CUOTA_MAX:
                continue
            f_loc = evaluador(mercado, opcion, True)
            f_vis = evaluador(mercado, opcion, False)
            if not f_loc:
                continue
            a, na = frecuencia(f_loc, h_loc)
            b, nb = frecuencia(f_vis, h_vis)
            if na < MIN_PARTIDOS or nb < MIN_PARTIDOS:
                continue
            fa, fb = a / na, b / nb
            frec = (a + b) / (na + nb)
            implicita = 1 / cuota
            if frec < FREC_MIN or min(fa, fb) < FREC_EQUIPO or not (0 < frec - implicita <= VENTAJA_MAX):
                continue
            salida.append({
                "partido_id": partido["fixture"]["id"],
                "fecha": inicio.astimezone(MADRID).strftime("%Y-%m-%dT%H:%M"),
                "competicion": COMPETICION.get(partido["league"]["id"], partido["league"]["name"]),
                "local": loc["name"], "visitante": vis["name"],
                "mercado": mercado, "opcion": opcion,
                "texto": texto_pick(mercado, opcion, loc["name"], vis["name"]),
                "cuota": cuota,
                "frecuencia": round(frec, 3),
                "detalle": f"{loc['name']} {a}/{na} · {vis['name']} {b}/{nb}",
                "ventaja": round(frec - implicita, 3),
            })
    return salida


def combinar(picks, minimo, maximo, max_patas, min_patas=2):
    """Elige picks (uno por partido) empezando por los más fiables hasta caer en el rango de cuota."""
    elegidos, usados, total = [], set(), 1.0
    for p in sorted(picks, key=lambda x: (-x["frecuencia"], -x["ventaja"])):
        if p["partido_id"] in usados:
            continue
        if total * p["cuota"] > maximo:
            continue
        elegidos.append(p)
        usados.add(p["partido_id"])
        total *= p["cuota"]
        if total >= minimo and len(elegidos) >= min_patas:
            return {"picks": elegidos, "cuota": round(total, 2)}
        if len(elegidos) >= max_patas:
            break
    return None


def combis_del_dia(picks):
    """Tres combis sin repetir selección entre ellas (si no da, la loca puede reutilizar)."""
    reglas = [("segura", 1.45, 1.75, 4, 2), ("cuota_3", 3.0, 4.5, 6, 3), ("loca", 8.0, 20.0, 10, 5)]
    usados, res = set(), {}
    for nombre, mn, mx, patas, min_p in reglas:
        libres = [p for p in picks if (p["partido_id"], p["mercado"], p["opcion"]) not in usados]
        c = combinar(libres, mn, mx, patas, min_p) or (nombre == "loca" and combinar(picks, mn, mx, patas, min_p)) or None
        res[nombre] = c
        if c:
            usados.update((p["partido_id"], p["mercado"], p["opcion"]) for p in c["picks"])
    return res


def main():
    ahora = datetime.now(timezone.utc)
    hist = historial()
    todos = []
    for f in sorted(EXTRA.glob("*.json")):
        prox = leer(f)
        if prox and prox.get("partido"):
            todos.extend(picks_partido(prox, hist, ahora))

    por_dia = defaultdict(list)
    for p in todos:
        por_dia[p["fecha"][:10]].append(p)

    salida = {"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"),
              "criterios": {"cuota_min": CUOTA_MIN, "frecuencia_min": FREC_MIN,
                            "frecuencia_equipo_min": FREC_EQUIPO, "ultimos_partidos": ULTIMOS},
              "dias": {}}
    for dia in sorted(por_dia):
        picks = sorted(por_dia[dia], key=lambda x: (-x["frecuencia"], -x["ventaja"]))
        # el mejor pick de cada partido (para listas de "9 picks")
        mejores, vistos = [], set()
        for p in picks:
            if p["partido_id"] not in vistos:
                mejores.append(p)
                vistos.add(p["partido_id"])
        salida["dias"][dia] = {
            "picks": picks,
            "mejores_por_partido": mejores,
            "combis": combis_del_dia(picks),
        }

    (DATOS / "picks.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir_md(salida)
    print(f"Picks: {len(todos)} en {len(por_dia)} días")


def escribir_md(s):
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    out = ["# Picks del Analista", "",
           f"_Generado el {s['generado']} (hora España). Cuotas de Bet365. Criterio: cuota ≥ "
           f"{CUOTA_MIN:.2f}, cumplido en ≥ {FREC_MIN:.0%} de los últimos {ULTIMOS} partidos de los dos "
           f"equipos (≥ {FREC_EQUIPO:.0%} en cada uno) y por encima de lo que dice la cuota._", ""]
    for dia, d in s["dias"].items():
        f = datetime.fromisoformat(dia)
        out += [f"## {dias_es[f.weekday()]} {f.strftime('%d/%m')}", ""]
        for nombre, titulo in (("segura", "🔒 Combi segura"), ("cuota_3", "💥 Combi cuota 3-4"), ("loca", "🤪 Combi loca")):
            c = d["combis"][nombre]
            if c:
                out.append(f"**{titulo} · cuota {c['cuota']:.2f}**".replace(".", ","))
                out += [f"- {p['texto']} ({p['cuota']:.2f})".replace(".", ",") for p in c["picks"]]
                out.append("")
        out += ["| Hora | Pick | Cuota | Se cumplió | Detalle |", "|---|---|---|---|---|"]
        for p in d["picks"]:
            out.append(f"| {p['fecha'][11:]} | {p['texto']} | {p['cuota']:.2f} | {p['frecuencia']:.0%} | {p['detalle']} |")
        out.append("")
    (RAIZ / "PICKS.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
