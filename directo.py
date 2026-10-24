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

from bot import API, COMPETICIONES, DATOS, MADRID, RAIZ, leer, recortar_partido, extraer_corners_por_parte
from publicados import picks_de_post

CARPETA = DATOS / "en_directo"
FIXTURES = DATOS / "fixtures_dia.json"


def partidos_conocidos(api, hoy):
    """Partidos de hoy y mañana: los del calendario + todos los del día de la API (1 petición al día,
    para los de ligas que el bot no sigue, p. ej. Segunda)."""
    lista = []
    for lg in COMPETICIONES:
        for f in leer(DATOS / f"calendario_{lg}.json", []) or []:
            lista.append({"id": f["fixture"]["id"], "local": f["teams"]["home"]["name"],
                          "visitante": f["teams"]["away"]["name"], "fecha": f["fixture"]["date"],
                          "liga_id": lg})
    fx = leer(FIXTURES, {}) or {}
    if api and fx.get("dia") != hoy:
        dia = []
        for r in api.get("fixtures", date=hoy, timezone="Europe/Madrid"):
            dia.append({"id": r["fixture"]["id"], "local": r["teams"]["home"]["name"],
                        "visitante": r["teams"]["away"]["name"], "fecha": r["fixture"]["date"],
                        "liga": r["league"]["name"], "logo_l": r["teams"]["home"].get("logo"),
                        "logo_v": r["teams"]["away"].get("logo")})
        fx = {"dia": hoy, "partidos": dia}
        FIXTURES.write_text(json.dumps(fx, ensure_ascii=False), encoding="utf-8")
    ids = {p["id"] for p in lista}
    return lista + [p for p in fx.get("partidos", []) if p["id"] not in ids]


def ids_publicados(partidos, ahora):
    """Partidos de las líneas de los posts publicados en las últimas 36 h."""
    desde = (ahora - timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M")
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    posts = [p for p in leer(RAIZ / "publicaciones" / "cola.json", []) or [] if p.get("enviado") or p.get("redes")]
    posts += [dict(p, **enviados.get(p["id"], {})) for p in leer(RAIZ / "publicaciones" / "auto.json", []) or []
              if (enviados.get(p["id"]) or {}).get("enviado")]
    hoy_p = [x for x in partidos if x.get("fecha", "")[:10] in (ahora.strftime("%Y-%m-%d"),
                                                                (ahora + timedelta(days=1)).strftime("%Y-%m-%d"))]
    ids = {}
    for p in posts:
        if p["fecha"] < desde or p.get("borrar"):
            continue
        for l in picks_de_post(p, hoy_p):
            if l["partido_id"]:
                ids[l["partido_id"]] = next(x["fecha"] for x in hoy_p if x["id"] == l["partido_id"])
    return ids


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        print("Directo: sin API_FOOTBALL_KEY")
        return
    ahora = datetime.now(MADRID)
    picks = leer(DATOS / "picks.json", {}) or {}
    api = API(clave)
    partidos = partidos_conocidos(api, ahora.strftime("%Y-%m-%d"))
    resumen = leer(DATOS / "en_directo.json", {}) or {}
    ids = set()
    # Actualizar también los partidos sin picks y recuperar finales que quedaron en juego.
    for p in partidos:
        inicio = datetime.fromisoformat(p["fecha"].replace("Z", "+00:00")).astimezone(MADRID)
        if (p.get("liga_id") in COMPETICIONES and
                ahora - timedelta(hours=30) <= inicio <= ahora + timedelta(minutes=5) and
                (resumen.get(str(p["id"])) or {}).get("estado") not in ("FT", "AET", "PEN")):
            ids.add(p["id"])
    for pid, fecha in ids_publicados(partidos, ahora).items():
        inicio = datetime.fromisoformat(fecha.replace("Z", "+00:00")).astimezone(MADRID)
        if inicio - timedelta(minutes=5) <= ahora <= inicio + timedelta(minutes=150):
            ids.add(pid)
    registro = list((leer(DATOS / "registro_aciertos.json", {}) or {}).values())   # guarda también los ya empezados
    for d in list((picks.get("dias") or {}).values()) + [{"picks": registro}]:
        for p in d.get("picks", []):
            inicio = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
            if inicio - timedelta(minutes=5) <= ahora <= inicio + timedelta(minutes=150):
                ids.add(p["partido_id"])
    resumen = {k: v for k, v in resumen.items() if v.get("visto", "") >= (ahora - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M")}
    if not ids:
        (DATOS / "en_directo.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")
        print("Directo: ningún partido con picks en juego")
        return
    CARPETA.mkdir(exist_ok=True)
    lista = sorted(ids)
    for i in range(0, len(lista), 20):
        for r in api.get("fixtures", ids="-".join(map(str, lista[i:i + 20]))):
            p = recortar_partido(r)
            if p["estado"] in ("1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "FT", "AET", "PEN"):
                mitades = api.get("fixtures/statistics", fixture=p["id"], half="true")
                p["corners_partes"] = extraer_corners_por_parte(mitades)
            (CARPETA / f"{p['id']}.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
            resumen[str(p["id"])] = {"estado": p["estado"], "minuto": r["fixture"]["status"].get("elapsed"),
                                     "goles": p.get("goles"), "visto": ahora.strftime("%Y-%m-%dT%H:%M"),
                                     "corners": [(p.get("stats") or {}).get(str(p[l]["id"]), {}).get("corners") for l in ("local", "visitante")],
                                     "tarjetas": [(p.get("stats") or {}).get(str(p[l]["id"]), {}).get("amarillas") for l in ("local", "visitante")]}
    (DATOS / "en_directo.json").write_text(json.dumps(resumen, ensure_ascii=False), encoding="utf-8")
    print(f"Directo: {len(ids)} partidos actualizados ({api.usadas} peticiones)")


if __name__ == "__main__":
    main()
