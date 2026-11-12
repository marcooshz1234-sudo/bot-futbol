"""12/11 (Marcos: «sale el nombre del árbitro pero no la media de amarillas»).

Solo teníamos tarjetas de los árbitros de las ligas que sigue el bot (picks.indice_arbitros). Para los de los
partidos de hoy y mañana que no conocemos (selecciones, Copa, Champions femenina…), se buscan sus últimos partidos
pitados (hasta 8) y las tarjetas de cada uno. La API NO deja buscar por árbitro («The Referee field do not exist»,
12/11): se piden los calendarios de las competiciones UEFA y las 5 grandes (una petición cada una) y se filtra. Se guarda en datos/arbitros_ext.json y no se vuelve
a pedir en 7 días. Tope de peticiones por pasada para no comerse la cuota.
"""
import os
from datetime import datetime, timedelta

from bot import API, DATOS, EXTRA, MADRID, LimiteAlcanzado, leer

SALIDA = DATOS / "arbitros_ext.json"
MAX_PETICIONES_PASADA = 90
POR_ARBITRO = 8
# Champions, Europa, Conference, Nations, clasif. Mundial y Euro, Champions femenina y las 5 grandes
COMPETICIONES = (2, 3, 848, 5, 32, 960, 525, 140, 39, 135, 78, 61)


def partidos_pitados(api, ahora, usadas):
    """{árbitro normalizado: [partidos terminados]} de esas competiciones (esta temporada y la anterior)."""
    from picks import nombre_arbitro
    por = {}
    for liga in COMPETICIONES:
        for temporada in (ahora.year, ahora.year - 1):
            if usadas[0] >= MAX_PETICIONES_PASADA // 3:
                return por
            r = api.get("fixtures", league=liga, season=temporada, status="FT-AET-PEN") or []
            usadas[0] += 1
            for x in r:
                if (x.get("fixture") or {}).get("referee"):
                    por.setdefault(nombre_arbitro(x["fixture"]["referee"]), []).append(x)
    return por


def tarjetas_partido(api, fid):
    r = api.get("fixtures/statistics", fixture=fid) or []   # API.get ya devuelve la lista «response»
    total = 0
    for eq in r:
        for s in eq.get("statistics") or []:
            if s.get("type") in ("Yellow Cards", "Red Cards"):
                total += int(s.get("value") or 0)
    return total if len(r) == 2 else None


def arbitros_pendientes(ahora):
    from picks import indice_arbitros, nombre_arbitro
    conocidos = {k for k, v in indice_arbitros().items() if len(v) >= 4}
    hechos = leer(SALIDA, {}) or {}
    limite = (ahora - timedelta(days=7)).strftime("%Y-%m-%d")
    dias = {(ahora + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(3)}
    for f in EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido") or {}
        fx = pa.get("fixture") or {}
        if not fx.get("referee") or not fx.get("date"):
            continue
        if datetime.fromisoformat(fx["date"]).astimezone(MADRID).strftime("%Y-%m-%d") not in dias:
            continue
        arb = nombre_arbitro(fx["referee"])
        if arb in conocidos or (hechos.get(arb) or {}).get("act", "") >= limite:
            continue
        yield arb, fx["referee"]


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        print("arbitros_ext: falta API_FOOTBALL_KEY")
        return
    api = API(clave)
    ahora = datetime.now(MADRID)
    datos = leer(SALIDA, {}) or {}
    usadas = [0]
    vistos = set()
    try:
        pendientes = [(a, c) for a, c in arbitros_pendientes(ahora)]
        pitados = partidos_pitados(api, ahora, usadas) if pendientes else {}
        for arb, crudo in pendientes:
            if arb in vistos or usadas[0] >= MAX_PETICIONES_PASADA:
                continue
            vistos.add(arb)
            partidos = list({x["fixture"]["id"]: x for x in pitados.get(arb, [])}.values())   # sin repetidos
            partidos.sort(key=lambda x: x["fixture"]["date"], reverse=True)
            tarjetas = []
            for x in partidos[:POR_ARBITRO]:
                if usadas[0] >= MAX_PETICIONES_PASADA:
                    break
                t = tarjetas_partido(api, x["fixture"]["id"])
                usadas[0] += 1
                if t is not None:
                    tarjetas.append(t)
            if tarjetas:   # si no sale nada, se vuelve a probar en la siguiente pasada
                datos[arb] = {"tarjetas": tarjetas, "act": ahora.strftime("%Y-%m-%d")}
            print(f"Árbitro {arb}: {len(tarjetas)} partidos, "
                  f"{round(sum(tarjetas) / len(tarjetas), 1) if tarjetas else '—'} tarjetas de media")
    except LimiteAlcanzado:
        print("arbitros_ext: límite de peticiones")
    SALIDA.write_text(__import__("json").dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"arbitros_ext: {usadas[0]} peticiones")


if __name__ == "__main__":
    main()
