"""
28/10 (Marcos): GIF en el canal de Telegram según el momento (GIPHY, clave gratis en el secreto GIPHY_API_KEY).

Cuándo (como mucho 4 al día y nunca dos GIF seguidos sin un post en medio):
  - justo después de: un verde 💚, la loca 🤪, un boleto 🎟️, la escalera 🪜, la combi del día 🔥, los picks de mañana 🌙
  (28/10: sin GIF de roja, Marcos)
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
# 28/10 (Marcos): muchos GIF por momento (se mezclan varias búsquedas y no se repite uno ya usado) y según el post
BUSQUEDAS = {
    "verde": ["celebration", "lets go", "winner", "victory dance", "yes yes yes", "happy dance", "money rain",
              "we did it", "champions celebration", "fist pump", "jumping celebration", "cheering crowd"],
    "loca": ["crazy", "going crazy", "insane", "mind blown", "lets go crazy", "wild", "explosion", "chaos",
             "crazy dance", "madness", "rollercoaster", "all in"],
    "escalera": ["stairs", "step by step", "climbing", "level up", "one step at a time", "stairway",
                 "to the top", "going up", "next level", "climb"],
    "combi": ["fire", "on fire", "lets go", "here we go", "hype", "ready", "game on", "boom", "lets do this", "bring it on"],
    "boleto": ["money", "jackpot", "dream big", "rich", "make it rain", "lottery", "cash", "big money",
               "millionaire", "pray", "fingers crossed"],
    "previa": ["nervous", "game time", "popcorn", "here we go", "waiting", "excited", "anxious", "nail biting",
               "lets go football", "stadium crowd"],
    "noche": ["good night", "see you tomorrow", "sleep", "tomorrow", "bedtime", "night night", "goodnight wink"],
    "manana": {"lunes": ["monday", "monday motivation", "monday coffee", "monday mood", "new week"],
               "viernes": ["friday", "its friday", "weekend", "friday dance", "tgif", "weekend vibes"],
               "europa": ["champions league", "big night", "lets go", "game night", "under the lights"]},
}
TEXTOS = {
    "verde": ["💚💚💚", "¡VERDEEEE! 💚", "Así se celebra en COMBILOCAS 💚🍀", "¡A COBRAR! 💚💶", "Otra más pa' la saca 💚"],
    "loca": ["La loca de hoy viene así 🤪", "¿Quién se atreve? 🤪🔥", "Modo loco activado 🤪", "Hoy toca soñar 🤪💸"],
    "escalera": ["Escalón a escalón 🪜", "Un peldaño más 🪜💪", "Subiendo… 🪜🔥"],
    "combi": ["Hoy toca 🔥", "Vamos con todo 🔥⚽", "Esta pinta bien 👀🔥"],
    "boleto": ["Hoy soñamos a lo grande 💸🍀", "Que sea lo que tenga que ser 🙏🍀", "Dedos cruzados 🤞💚"],
    "previa": ["Empieza lo bueno ⚽🔥", "Nervios… ¿cómo vais? ⚽👀", "Hora de partido ⚽🍀", "Palomitas listas 🍿⚽"],
    "noche": ["Mañana más 🌙🍀", "A descansar, que mañana hay más 🌙⚽", "Buenas noches, combilocos 🌙💚"],
    "manana": {"lunes": "☀️ Lunes de combis 🍀", "viernes": "☀️ ¡Viernes! Se viene finde de fútbol ⚽🔥",
               "europa": "☀️ Hoy hay noche europea ⭐⚽"},
}
# qué GIF va justo después de cada tipo de post (por su id); los verdes, siempre
TRAS_POST = (("verde", "verde"), ("combi-loca", "loca"), ("boleto", "boleto"), ("escalera", "escalera"),
             ("combi-tres", "combi"), ("picks-manana", "noche"))
EUROPA = {2, 3, 848}   # Champions, Europa League, Conference


def buscar(clave, termino, rnd=random, usados=(), offset=None):
    q = urlencode({"api_key": clave, "q": termino, "limit": 25, "rating": "g", "lang": "es",
                   "offset": rnd.choice((0, 0, 25, 50)) if offset is None else offset})
    with urlopen(f"https://api.giphy.com/v1/gifs/search?{q}", timeout=20) as r:
        datos = [g for g in (json.load(r).get("data") or []) if g.get("id") not in usados]
    if not datos:
        return None
    g = rnd.choice(datos)
    img = (g.get("images") or {})
    return g.get("id"), (img.get("downsized_medium") or img.get("original") or {}).get("url")


def momentos(ahora, cola, auto, env, app, est):
    """Lista de (clave_unica, tipo, termino_opciones, texto) que tocan ahora."""
    hoy = ahora.strftime("%Y-%m-%d")
    ya = ahora.strftime("%Y-%m-%dT%H:%M")
    hace15 = (ahora - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
    hecho = set(est.get("hechos", []))
    salida = []
    # justo después de ciertos posts del canal (verdes, la loca, boletos, escalera, combi del día, picks de mañana)
    ids_c = {p["id"] for p in cola}
    recientes = cola + [dict(p, **env.get(p["id"], {})) for p in auto if p["id"] not in ids_c]
    for p in sorted(recientes, key=lambda x: x.get("enviado") or ""):
        if not (p.get("mensaje_id") and hace15 <= (p.get("enviado") or "") <= ya) or f"t-{p['id']}" in hecho:
            continue
        tipo = next((g for patron, g in TRAS_POST if patron in p["id"]), None)
        if tipo:
            salida.append((f"t-{p['id']}", tipo, BUSQUEDAS[tipo], random.choice(TEXTOS[tipo])))
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
            usados = {x.get("gif") for x in est.get("enviados", [])}
            r = buscar(clave, rnd.choice(terminos), rnd, usados)
            gid, url = r if r else (None, None)
            if url:
                if enviar:
                    enviar(url, texto)
                else:
                    from publicar_telegram import api
                    api(token, "sendAnimation", {"chat_id": canal, "animation": url, "caption": texto})
                est.setdefault("enviados", []).append({"fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "tipo": tipo, "gif": gid, "url": url})
                print(f"GIF {tipo}: enviado")
        except Exception as e:
            print("GIF:", str(e)[:150])
    est["hechos"] = est.get("hechos", [])[-300:]
    est["enviados"] = est.get("enviados", [])[-200:]
    ESTADO.write_text(json.dumps(est, ensure_ascii=False), encoding="utf-8")


def muestra(n=25):
    """Busca n GIF distintos de cada momento y los deja en datos/gifs_muestra.json (no publica nada)."""
    clave = os.environ.get("GIPHY_API_KEY")
    sal = {}
    for tipo, b in BUSQUEDAS.items():
        terminos = [t for v in b.values() for t in v] if isinstance(b, dict) else list(b)
        vistos, lista = set(), []
        for i in range(n * 3):
            if len(lista) >= n:
                break
            t = terminos[i % len(terminos)]
            try:
                r = buscar(clave, t, random, vistos, offset=0)
            except Exception as e:
                print(tipo, t, str(e)[:80])
                continue
            if r and r[1]:
                vistos.add(r[0])
                lista.append({"busqueda": t, "url": r[1]})
        sal[tipo] = lista
    (DATOS / "gifs_muestra.json").write_text(json.dumps(sal, ensure_ascii=False, indent=1), encoding="utf-8")
    nom = {"verde": "💚 Verde", "loca": "🤪 La loca", "escalera": "🪜 Escalera", "combi": "🔥 Combi del día",
           "boleto": "🎟️ Boletos y combi de los 1.000", "previa": "⚽ Previa de la noche", "noche": "🌙 Picks para mañana (buenas noches)",
           "manana": "☀️ Mañanas (lunes, viernes, noche europea)"}
    md = ["# GIF de muestra (no se ha publicado nada)", ""]
    for k, v in sal.items():
        md += [f"## {nom.get(k, k)} · {len(v)}", "", " ".join(f'<img src="{x["url"]}" height="110">' for x in v), ""]
    (DATOS / "gifs_muestra.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    import sys
    muestra() if "--muestra" in sys.argv else main()
