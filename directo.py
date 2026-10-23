"""
En directo · marcador, minuto y estadísticas de los partidos con picks en juego.

Se ejecuta en el bucle de Telegram cada ~5 min. Solo llama a la API si hay algún
partido con picks que haya empezado hace menos de 2 h 30 min (1 petición para todos).
Guarda datos/en_directo.json (resumen) y datos/en_directo/<id>.json (formato de
datos/partidos, para evaluar los picks en vivo).
"""
import json
import os
from datetime import datetime, timedelta

from bot import API, DATOS, MADRID, leer, recortar_partido

CARPETA = DATOS / "en_directo"


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        print("Directo: sin API_FOOTBALL_KEY")
        return
    ahora = datetime.now(MADRID)
    picks = leer(DATOS / "picks.json", {}) or {}
    ids = set()
    registro = list((leer(DATOS / "registro_aciertos.json", {}) or {}).values())   # guarda también los ya empezados
    for d in list((picks.get("dias") or {}).values()) + [{"picks": registro}]:
        for p in d.get("picks", []):
            inicio = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
            if inicio - timedelta(minutes=5) <= ahora <= inicio + timedelta(minutes=150):
                ids.add(p["partido_id"])
    resumen = leer(DATOS / "en_directo.json", {}) or {}
    resumen = {k: v for k, v in resumen.items() if v.get("visto", "") >= (ahora - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M")}
    if not ids:
        (DATOS / "en_directo.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")
        print("Directo: ningún partido con picks en juego")
        return
    CARPETA.mkdir(exist_ok=True)
    api = API(clave)
    lista = sorted(ids)
    for i in range(0, len(lista), 20):
        for r in api.get("fixtures", ids="-".join(map(str, lista[i:i + 20]))):
            p = recortar_partido(r)
            (CARPETA / f"{p['id']}.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
            resumen[str(p["id"])] = {"estado": p["estado"], "minuto": r["fixture"]["status"].get("elapsed"),
                                     "goles": p.get("goles"), "visto": ahora.strftime("%Y-%m-%dT%H:%M"),
                                     "corners": [(p.get("stats") or {}).get(str(p[l]["id"]), {}).get("corners") for l in ("local", "visitante")],
                                     "tarjetas": [(p.get("stats") or {}).get(str(p[l]["id"]), {}).get("amarillas") for l in ("local", "visitante")]}
    (DATOS / "en_directo.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")
    print(f"Directo: {len(ids)} partidos actualizados ({api.usadas} peticiones)")


if __name__ == "__main__":
    main()
