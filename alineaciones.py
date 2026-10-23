"""
El Analista · combis de jugadores cuando salen las alineaciones.

Se ejecuta cada 15 minutos. Para los partidos que empiezan dentro de 15-95
minutos (cuando ya suelen estar las alineaciones):
1. Pide a la API las alineaciones confirmadas y las cuotas de jugador de Bet365
   (paradas del portero, remates, remates a puerta y faltas).
2. Solo mira a los TITULARES. Para cada cuota "Jugador - N" (N o más) cuenta en
   cuántos de sus últimos partidos (jugando 60 min o más; porteros 80) llegó a N.
3. Entra si la cuota está entre 1,25 y 2,00, se cumplió en el 75 % o más (mínimo
   5 partidos) y hay valor sobre la cuota (sin pasarse de +30 puntos).
4. Monta hasta dos posts: 🧤 COMBI DE PORTEROS y 🎯 COMBI DE JUGADORES, siempre
   con un pick por partido (así la cuota total es la real de una combinada).
   Si solo hay un partido en la ventana, publica los picks sin cuota total.

Escribe en publicaciones/alineaciones.json (lo publica El Publicador al momento)
y recuerda lo ya mirado en datos/alineaciones_hechas.json.
"""

import json
import os
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from bot import API, DATOS, EXTRA, MADRID, PARTIDOS, RAIZ, leer

HECHAS = DATOS / "alineaciones_hechas.json"
SALIDA = RAIZ / "publicaciones" / "alineaciones.json"
PRUEBA = RAIZ / "publicaciones" / "alineaciones_prueba.json"   # antes de DESDE: se guarda sin publicar
DESDE = "2026-10-27"
VENTANA = (timedelta(minutes=15), timedelta(minutes=95))   # GitHub lanza el cron cada ~45 min, no cada 15
CUOTA_MIN, CUOTA_MAX = 1.25, 2.00
# Igual que picks.py tras la prueba con 186 partidos: solo remates (2+ acertó el 90 %) y con ≥ 90 %.
# Faltas (2+: 33 %) y remates a puerta (59 %) fuera; porteros, a mano en bet365.
FREC_MIN, MIN_PARTIDOS, ULTIMOS, VENTAJA_MAX = 0.90, 5, 10, 0.30

MERCADOS = {  # nombre en bet365 → (dato del jugador, texto)
    "Home Player Shots": ("tiros", "hace {n}+ remates"),
    "Away Player Shots": ("tiros", "hace {n}+ remates"),
}


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return " ".join(t.replace("-", " ").replace(".", " ").split())


def mismo_jugador(nombre_cuota, nombre_api):
    a, b = norm(nombre_cuota).split(), norm(nombre_api).split()
    if not a or not b:
        return False
    if a == b:
        return True
    # mismo apellido y misma inicial (p. ej. "T. Courtois" / "Thibaut Courtois")
    return a[-1] == b[-1] and a[0][0] == b[0][0]


def historial_jugadores():
    idx = defaultdict(list)
    for f in PARTIDOS.glob("*.json"):
        p = leer(f)
        if not p or p.get("estado") not in ("FT", "AET", "PEN"):
            continue
        for eq, lista in (p.get("jugadores") or {}).items():
            paradas_equipo = ((p.get("stats") or {}).get(eq) or {}).get("paradas")
            for j in lista:
                reg = dict(j)
                if j.get("pos") == "G" and not j.get("paradas") and paradas_equipo is not None and j.get("min", 0) >= 80:
                    reg["paradas"] = paradas_equipo  # datos antiguos: paradas del equipo con el portero los 90'
                reg["fecha"] = p["fecha"]
                idx[j["id"]].append(reg)
    for l in idx.values():
        l.sort(key=lambda r: r["fecha"], reverse=True)
    return idx


def picks_partido(api, prox, hist):
    partido = prox["partido"]
    fid = partido["fixture"]["id"]
    loc, vis = partido["teams"]["home"]["name"], partido["teams"]["away"]["name"]
    alineaciones = api.get("fixtures/lineups", fixture=fid)
    titulares = []
    for eq in alineaciones or []:
        for x in eq.get("startXI") or []:
            j = x.get("player") or {}
            titulares.append({"id": j.get("id"), "nombre": j.get("name"), "pos": j.get("pos")})
    if len(titulares) < 22:
        return None  # todavía no están
    cuotas = {}
    for it in api.get("odds", fixture=fid, bookmaker=8) or []:
        for bk in it.get("bookmakers") or []:
            for b in bk.get("bets") or []:
                if b.get("name") in MERCADOS:
                    cuotas.setdefault(b["name"], []).extend(b.get("values") or [])
    salida = []
    for mercado, valores in cuotas.items():
        campo, plantilla = MERCADOS[mercado]
        for v in valores:
            try:
                nombre, n = str(v["value"]).rsplit(" - ", 1)
                n, cuota = int(n.strip()), float(v["odd"])
            except (ValueError, KeyError):
                continue
            if not (CUOTA_MIN <= cuota <= CUOTA_MAX):
                continue
            jug = next((t for t in titulares if mismo_jugador(nombre, t["nombre"])), None)
            if not jug or (campo == "paradas") != (jug["pos"] == "G"):
                continue
            minimo = 80 if campo == "paradas" else 60
            partidos = [r for r in hist.get(jug["id"], []) if r.get("min", 0) >= minimo][:ULTIMOS]
            if len(partidos) < MIN_PARTIDOS:
                continue
            si = sum(1 for r in partidos if (r.get(campo) or 0) >= n)
            frec = si / len(partidos)
            if frec < FREC_MIN or not (0 < frec - 1 / cuota <= VENTAJA_MAX):
                continue
            salida.append({
                "partido_id": fid, "partido": f"{loc}–{vis}", "inicio": partido["fixture"]["date"],
                "jugador": nombre.strip(), "mercado": mercado, "campo": campo, "n": n, "cuota": cuota,
                "frecuencia": round(frec, 3), "detalle": f"{si}/{len(partidos)}",
                "texto": f"{nombre.strip()} {plantilla.format(n=n)} ({loc}–{vis})",
            })
    # por jugador y mercado, la línea más alta que cumple (más cuota con la misma fiabilidad)
    mejor = {}
    for p in salida:
        k = (p["jugador"], p["campo"])
        if k not in mejor or (p["frecuencia"], p["n"]) > (mejor[k]["frecuencia"], mejor[k]["n"]):
            mejor[k] = p
    return list(mejor.values())


def num(c):
    return f"{c:.2f}".replace(".", ",")


def combi(picks, titulo, min_cuota, max_cuota, max_patas):
    elegidos, usados, total = [], set(), 1.0
    for p in sorted(picks, key=lambda x: (-x["frecuencia"], -x["cuota"])):
        if p["partido_id"] in usados or total * p["cuota"] > max_cuota:
            continue
        elegidos.append(p)
        usados.add(p["partido_id"])
        total *= p["cuota"]
        if len(elegidos) >= max_patas:
            break
    if len(elegidos) < 2 or total < min_cuota:
        return None
    lineas = "\n".join(f"✅{i}. {p['texto']}" for i, p in enumerate(elegidos, 1))
    top = max(elegidos, key=lambda x: x["frecuencia"])
    return (f"{titulo}\n\n{lineas}\n\n🎯 Cuota total: {num(total)}\n💶 10€ → {num(total * 10)}€\n\n"
            f"📊 {top['jugador']} lo cumplió en {top['detalle']} de sus últimos partidos\n\n"
            "🍀 ¿LA PINTAMOS DE VERDE? 👀💚")


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        raise SystemExit("Falta API_FOOTBALL_KEY")
    ahora = datetime.now(timezone.utc)
    hechas = leer(HECHAS, {}) or {}
    pendientes = []
    for f in EXTRA.glob("*.json"):
        prox = leer(f)
        if not prox or not prox.get("partido"):
            continue
        fx = prox["partido"]["fixture"]
        inicio = datetime.fromisoformat(fx["date"])
        if str(fx["id"]) in hechas or not (VENTANA[0] <= inicio - ahora <= VENTANA[1]):
            continue
        pendientes.append(prox)
    if not pendientes:
        print("Ningún partido en la ventana de alineaciones")
        return
    api = API(clave)
    hist = historial_jugadores()
    todos = []
    for prox in pendientes:
        fid = str(prox["partido"]["fixture"]["id"])
        res = picks_partido(api, prox, hist)
        if res is None:
            print(f"Sin alineaciones aún: {fid}")
            continue
        hechas[fid] = {"mirado": ahora.isoformat(), "picks": len(res)}
        todos.extend(res)
    HECHAS.write_text(json.dumps(hechas, ensure_ascii=False, indent=1), encoding="utf-8")
    if not todos:
        print("Sin picks de jugadores que cumplan")
        return

    destino = SALIDA if datetime.now(MADRID).strftime("%Y-%m-%d") >= DESDE else PRUEBA
    posts = leer(destino, []) or []
    hora = datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")
    clave_post = datetime.now(MADRID).strftime("%Y-%m-%d-%H%M")
    porteros = [p for p in todos if p["campo"] == "paradas"]
    nuevos = []
    if len({p["partido_id"] for p in todos}) >= 2:
        t = combi(porteros, "🧤 COMBI DE PORTEROS 🧤", 1.6, 6.0, 3)
        if t:
            nuevos.append(("porteros", t))
        resto = [p for p in todos if p["campo"] != "paradas"] or todos
        t = combi(resto, "🎯 COMBI DE JUGADORES · ALINEACIONES CONFIRMADAS 🎯", 2.0, 8.0, 4)
        if t:
            nuevos.append(("jugadores", t))
    else:  # un solo partido: picks sueltos (en el mismo partido la cuota total no sería real)
        sel = sorted(todos, key=lambda x: -x["frecuencia"])[:4]
        if porteros and porteros[0] not in sel:
            sel[-1] = porteros[0]
        lineas = "\n".join(f"✅{i}. {p['texto']} · {num(p['cuota'])}" for i, p in enumerate(sel, 1))
        nuevos.append(("jugadores", f"🎯 PICKS DE JUGADORES · {sel[0]['partido'].upper()} 🎯\n\n"
                                    f"Alineaciones confirmadas ✅\n\n{lineas}\n\n¡Combina máximo 2 o 3! 🍀"))
    for tipo, texto in nuevos:
        posts.append({"id": f"{clave_post}-{tipo}", "fecha": hora, "texto": texto, "foto": None,
                      "origen": "alineaciones"})
    destino.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Posts de jugadores: {len(nuevos)} → {destino.name}")


if __name__ == "__main__":
    main()
