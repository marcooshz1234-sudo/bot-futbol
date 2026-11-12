"""12/11 (Marcos: «sale el nombre del árbitro pero no la media de amarillas»).

Solo teníamos tarjetas de los árbitros de las ligas que sigue el bot (picks.indice_arbitros). Para los de los
partidos de hoy y mañana que no conocemos (selecciones, Copa, Champions femenina…), se buscan en API-Football sus
últimos partidos pitados (hasta 8) y las tarjetas de cada uno. Se guarda en datos/arbitros_ext.json y no se vuelve
a pedir en 7 días. Tope de peticiones por pasada para no comerse la cuota.
"""
import os
from datetime import datetime, timedelta

from bot import API, DATOS, EXTRA, MADRID, LimiteAlcanzado, leer

SALIDA = DATOS / "arbitros_ext.json"
MAX_PETICIONES_PASADA = 90
POR_ARBITRO = 8


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
    usadas = 0
    vistos = set()
    try:
        for arb, crudo in arbitros_pendientes(ahora):
            if arb in vistos or usadas >= MAX_PETICIONES_PASADA:
                continue
            vistos.add(arb)
            partidos = []
            # 12/11: con «Nombre» a secas la API devolvía 0 partidos de todos; se prueba también el nombre tal cual
            # viene en el partido («Nombre, País») y sin temporada
            for nombre, temporada in ((crudo, ahora.year), (arb, ahora.year), (crudo, ahora.year - 1), (arb, None)):
                if usadas >= MAX_PETICIONES_PASADA:
                    break
                params = {"referee": nombre, **({"season": temporada} if temporada else {})}
                r = api.get("fixtures", **params) or []
                usadas += 1
                partidos += [x for x in r if (x.get("fixture") or {}).get("status", {}).get("short") in ("FT", "AET", "PEN")]
                if len(partidos) >= POR_ARBITRO:
                    break
            partidos = list({x["fixture"]["id"]: x for x in partidos}.values())   # sin repetidos
            partidos.sort(key=lambda x: x["fixture"]["date"], reverse=True)
            tarjetas = []
            for x in partidos[:POR_ARBITRO]:
                if usadas >= MAX_PETICIONES_PASADA:
                    break
                t = tarjetas_partido(api, x["fixture"]["id"])
                usadas += 1
                if t is not None:
                    tarjetas.append(t)
            if tarjetas:   # si no sale nada, se vuelve a probar en la siguiente pasada
                datos[arb] = {"tarjetas": tarjetas, "act": ahora.strftime("%Y-%m-%d")}
            print(f"Árbitro {arb}: {len(tarjetas)} partidos, "
                  f"{round(sum(tarjetas) / len(tarjetas), 1) if tarjetas else '—'} tarjetas de media")
    except LimiteAlcanzado:
        print("arbitros_ext: límite de peticiones")
    SALIDA.write_text(__import__("json").dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"arbitros_ext: {usadas} peticiones")


if __name__ == "__main__":
    main()
