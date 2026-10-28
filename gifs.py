"""
28/10 (Marcos): GIF en el canal de Telegram según el momento (GIPHY, clave gratis en el secreto GIPHY_API_KEY).

Cuándo (como mucho 4 al día y nunca dos GIF seguidos sin un post en medio):
  - 💚 verde   → justo después de un post de verde (celebración)
  - 😤 roja    → cuando una combi publicada se cae (una vez por combi, como mucho 1 al día)
  - ⚽ previa  → 20 min antes del primer partido de la noche (19:00–22:00) que lleva combi publicada
  - ☀️ mañana  → 10:30 los lunes, viernes y días de Champions/Europa League
Busca GIF de reacciones y gente (no jugadas de partidos, que tienen derechos), con contenido apto («g»).
Lo ya hecho se guarda en datos/gifs.json. Sin clave no hace nada.
"""
import json
import os
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

from bot import DATOS, MADRID, RAIZ, leer

ESTADO = DATOS / "gifs.json"
ACTIVO = False   # 28/10: no sale ningún GIF al canal hasta que Marcos vea las muestras y diga que sí
MAX_DIA = 4
BUSQUEDAS = {
    "verde": ["football celebration", "celebration dance", "lets go celebration", "money rain", "winner celebration"],
    "roja": ["so close", "frustrated football fan", "next time", "facepalm", "disappointed"],
    "previa": ["nervous", "lets go football", "game time", "popcorn waiting", "here we go"],
    "manana": {"lunes": ["monday motivation", "monday coffee"], "viernes": ["friday weekend", "its friday"],
               "europa": ["champions league night", "big game night"]},
}
TEXTOS = {
    "verde": ["💚💚💚", "¡VERDEEEE! 💚", "Así se celebra en COMBILOCAS 💚🍀"],
    "roja": ["Esta se escapó por poco 😤 A por la siguiente 💪", "Hoy no… pero volvemos 💪🍀"],
    "previa": ["Empieza lo bueno ⚽🔥", "Nervios… ¿cómo vais? ⚽👀", "Hora de partido ⚽🍀"],
    "manana": {"lunes": "☀️ Lunes de combis 🍀", "viernes": "☀️ ¡Viernes! Se viene finde de fútbol ⚽🔥",
               "europa": "☀️ Hoy hay noche europea ⭐⚽"},
}
EUROPA = {2, 3, 848}   # Champions, Europa League, Conference


def buscar(clave, termino, rnd=random):
    q = urlencode({"api_key": clave, "q": termino, "limit": 25, "rating": "g", "lang": "es"})
    with urlopen(f"https://api.giphy.com/v1/gifs/search?{q}", timeout=20) as r:
        datos = json.load(r).get("data") or []
    if not datos:
        return None
    g = rnd.choice(datos[:15])
    img = (g.get("images") or {})
    return (img.get("downsized_medium") or img.get("original") or {}).get("url")


def momentos(ahora, cola, auto, env, app, est):
    """Lista de (clave_unica, tipo, termino_opciones, texto) que tocan ahora."""
    hoy = ahora.strftime("%Y-%m-%d")
    ya = ahora.strftime("%Y-%m-%dT%H:%M")
    hace15 = (ahora - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
    hecho = set(est.get("hechos", []))
    salida = []
    # 💚 verdes recién publicados en el canal
    for p in cola:
        if "verde" in p["id"] and p.get("mensaje_id") and hace15 <= (p.get("enviado") or "") <= ya and f"v-{p['id']}" not in hecho:
            salida.append((f"v-{p['id']}", "verde", BUSQUEDAS["verde"], random.choice(TEXTOS["verde"])))
    # 😤 combis publicadas que se caen (1 al día como mucho)
    if not any(h.startswith(f"r-{hoy}") for h in hecho):
        for p in app.get("publicados_hoy", []):
            if p["fecha"][:10] == hoy and p.get("estado") == "rojo" and not p.get("lista") and "verde" not in p["id"]:
                salida.append((f"r-{hoy}-{p['id']}", "roja", BUSQUEDAS["roja"], random.choice(TEXTOS["roja"])))
                break
    # ⚽ previa: 20 min antes del primer partido de la noche con combi publicada hoy
    ids = {p["id"] for p in cola}
    posts = cola + [dict(p, **env.get(p["id"], {})) for p in auto if p["id"] not in ids]
    inicios = sorted({s.split("|")[0]: None for p in posts if p["fecha"][:10] == hoy and p.get("mensaje_id")
                      for s in p.get("sel") or []})
    horas = []
    for fid in inicios:
        pa = (leer(DATOS / "proximos" / f"{fid}.json") or {}).get("partido")
        if pa:
            h = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
            if h.strftime("%Y-%m-%d") == hoy and 19 <= h.hour <= 22:
                horas.append(h)
    if horas:
        h = min(horas) - timedelta(minutes=20)
        if h <= ahora <= h + timedelta(minutes=15) and f"p-{hoy}" not in hecho:
            salida.append((f"p-{hoy}", "previa", BUSQUEDAS["previa"], random.choice(TEXTOS["previa"])))
    # ☀️ mañana: lunes, viernes o día europeo, a las 10:30
    m = ahora.replace(hour=10, minute=30, second=0, microsecond=0)
    if m <= ahora <= m + timedelta(minutes=15) and f"m-{hoy}" not in hecho:
        europa = any((leer(f) or {}).get("partido", {}).get("league", {}).get("id") in EUROPA
                     and (leer(f) or {}).get("partido", {}).get("fixture", {}).get("date", "")[:10] == hoy
                     for f in (DATOS / "proximos").glob("*.json"))
        dia = "europa" if europa else "lunes" if ahora.weekday() == 0 else "viernes" if ahora.weekday() == 4 else None
        if dia:
            salida.append((f"m-{hoy}", "manana", BUSQUEDAS["manana"][dia], TEXTOS["manana"][dia]))
    return salida


def puede(ahora, est, cola, env):
    """Tope diario y nada de dos GIF seguidos: tiene que haber salido un post después del último GIF."""
    hoy = ahora.strftime("%Y-%m-%d")
    if sum(1 for x in est.get("enviados", []) if x["fecha"][:10] == hoy) >= MAX_DIA:
        return False
    ultimo = max((x["fecha"] for x in est.get("enviados", [])), default="")
    if not ultimo:
        return True
    posts = [p.get("enviado") or "" for p in cola] + [v.get("enviado") or "" for v in env.values()]
    return any(e > ultimo for e in posts)


def main(ahora=None, enviar=None, rnd=random):
    clave, token, canal = os.environ.get("GIPHY_API_KEY"), os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not (clave and token and canal):
        print("GIF: falta la clave de GIPHY")
        return
    ahora = ahora or datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    auto = leer(RAIZ / "publicaciones" / "auto.json", []) or []
    env = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    app = leer(RAIZ / "docs" / "datos.json", {}) or {}
    if (leer(RAIZ / "publicaciones" / "control.json", {}) or {}).get("pausa") or not ACTIVO:
        return
    for k, tipo, terminos, texto in momentos(ahora, cola, auto, env, app, est)[:1]:   # uno por vuelta
        if not puede(ahora, est, cola, env):
            break
        est.setdefault("hechos", []).append(k)   # aunque falle, no se reintenta en bucle
        try:
            url = buscar(clave, rnd.choice(terminos), rnd)
            if url:
                if enviar:
                    enviar(url, texto)
                else:
                    from publicar_telegram import api
                    api(token, "sendAnimation", {"chat_id": canal, "animation": url, "caption": texto})
                est.setdefault("enviados", []).append({"fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "tipo": tipo, "url": url})
                print(f"GIF {tipo}: enviado")
        except Exception as e:
            print("GIF:", str(e)[:150])
    est["hechos"] = est.get("hechos", [])[-300:]
    est["enviados"] = est.get("enviados", [])[-200:]
    ESTADO.write_text(json.dumps(est, ensure_ascii=False), encoding="utf-8")


def muestra():
    """Busca 3 GIF de cada momento y los deja en datos/gifs_muestra.json (no publica nada)."""
    clave = os.environ.get("GIPHY_API_KEY")
    sal = {}
    for tipo, b in BUSQUEDAS.items():
        terminos = [t for v in b.values() for t in v] if isinstance(b, dict) else b
        sal[tipo] = []
        for t in terminos[:3]:
            try:
                sal[tipo].append({"busqueda": t, "url": buscar(clave, t)})
            except Exception as e:
                sal[tipo].append({"busqueda": t, "error": str(e)[:120]})
    (DATOS / "gifs_muestra.json").write_text(json.dumps(sal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(sal, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    import sys
    muestra() if "--muestra" in sys.argv else main()
