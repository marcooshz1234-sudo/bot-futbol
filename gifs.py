"""
GIF en el canal de Telegram (28/10, Marcos). Todo de fútbol (futbolistas, entrenadores, aficiones, memes), y verde si se puede.

Solo salen GIF que Marcos ha aprobado: con /gifs en el bot del móvil le llegan candidatos de GIPHY con
👍 / 👎 y los 👍 se guardan por momento en datos/gifs_votos.json (con el file_id de Telegram, que no caduca).

Cuándo (como mucho 4 al día y nunca dos GIF seguidos sin un post en medio):
  justo después de un post:
    💚 verde · 🔥🔥🔥 racha (3.º verde seguido) · 🤪 la loca · 🎟️ boleto · 🪜 escalera (⛰️ días 5–7)
    🔥 combi del día · 🎉 balance del día en positivo · 🌙 picks para mañana
  ⚽ previa: 20 min antes del primer partido de la noche (19–22 h) con combi publicada (🏟️ si es un partidazo)
  ☀️ 10:30 lunes, viernes y días de Champions/Europa League · 🍻 viernes 22:30 «empieza el finde»
  👥 al pasar 2.000, 3.000, 5.000, 10.000… seguidores en Threads
Sin GIF aprobados de un momento, ese momento no sale. Sin clave de GIPHY solo se usan los aprobados.
"""
import json
import os
import random
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

from bot import DATOS, MADRID, RAIZ, leer

ESTADO = DATOS / "gifs.json"
VOTOS = DATOS / "gifs_votos.json"
ACTIVO = False   # 28/10: apagado hasta que Marcos haya aprobado GIF y diga que sí
MAX_DIA = 4
EUROPA = {2, 3, 848}
GRANDES = {"Real Madrid", "Barcelona", "Atletico Madrid", "Manchester City", "Liverpool", "Arsenal", "Chelsea",
           "Manchester United", "Tottenham", "Bayern München", "Borussia Dortmund", "Paris Saint Germain",
           "Inter", "AC Milan", "Juventus", "Napoli", "AS Roma", "Sevilla", "Real Betis", "Athletic Club"}
HITOS = (2000, 3000, 5000, 7500, 10000, 15000, 20000, 30000, 50000, 100000)

MOMENTOS = {   # clave: (nombre en el bot, búsquedas en GIPHY, textos)
    "verde": ("💚 Verde", ["soccer celebration", "football goal celebration", "soccer player celebration", "goal celebration", "ronaldo siuu", "messi celebration", "football fans celebrating", "green soccer celebration", "green football", "soccer win", "football team celebrating", "football coach celebration"],
              ["💚💚💚", "¡VERDEEEE! 💚", "Así se celebra en COMBILOCAS 💚🍀", "¡A COBRAR! 💚💶", "Otra más pa' la saca 💚"]),
    "racha": ("🔥 Racha (3 verdes seguidos)", ["soccer on fire", "football unstoppable", "hat trick celebration", "soccer legend", "football genius", "soccer goat"],
              ["¡IMPARABLES! 🔥🔥🔥", "3 de 3… esto está on fire 🔥💚", "No hay quien nos pare 🔥"]),
    "loca": ("🤪 La loca", ["crazy soccer", "football crazy", "soccer madness", "crazy goal", "football fans crazy", "crazy football celebration", "soccer chaos", "football mind blown", "crazy coach", "bicycle kick"],
             ["La loca de hoy viene así 🤪", "¿Quién se atreve? 🤪🔥", "Modo loco activado 🤪", "Hoy toca soñar 🤪💸"]),
    "boleto": ("🎟️ Boletos", ["football money", "soccer money", "football pray", "soccer fans pray", "football fingers crossed", "soccer jackpot", "football nervous fan"],
               ["Hoy soñamos a lo grande 💸🍀", "Que sea lo que tenga que ser 🙏🍀", "Dedos cruzados 🤞💚"]),
    "escalera": ("🪜 Escalera", ["football training", "soccer training stairs", "football keep going", "soccer step by step", "football level up", "soccer warm up"], ["Escalón a escalón 🪜", "Un peldaño más 🪜💪", "Subiendo… 🪜🔥"]),
    "escalera_alta": ("⛰️ Escalera días 5–7", ["football tension", "soccer nervous", "penalty shootout tension", "football almost", "soccer so close", "football coach nervous"],
                      ["A un paso de la cima ⛰️🪜", "Esto ya quema… 🪜🔥", "Los últimos escalones 😮‍💨🪜"]),
    "combi": ("🔥 Combi del día", ["football lets go", "soccer lets go", "football hype", "soccer fire", "football ready", "soccer kick off", "football warm up"],
              ["Hoy toca 🔥", "Vamos con todo 🔥⚽", "Esta pinta bien 👀🔥"]),
    "fiesta": ("🎉 Balance en positivo", ["football party", "soccer party", "football dressing room celebration", "soccer champagne", "football trophy celebration", "soccer team dancing"],
               ["Día en verde 🎉💚", "¡Así cerramos el día! 🎉", "Hoy se celebra 🍾💚"]),
    "noche": ("🌙 Buenas noches", ["football good night", "soccer sleep", "football tired", "soccer goodnight", "football see you tomorrow"],
              ["Mañana más 🌙🍀", "A descansar, que mañana hay más 🌙⚽", "Buenas noches, combilocos 🌙💚"]),
    "previa": ("⚽ Previa de la noche", ["football nervous", "soccer fans waiting", "football kick off", "soccer stadium", "football fans nervous", "soccer tunnel walk out", "football anthem"],
               ["Empieza lo bueno ⚽🔥", "Nervios… ¿cómo vais? ⚽👀", "Hora de partido ⚽🍀", "Palomitas listas 🍿⚽"]),
    "partidazo": ("🏟️ Partidazo", ["champions league anthem", "el clasico", "soccer derby", "football big match", "champions league", "soccer stadium night", "football rivalry"],
                  ["Hoy hay PARTIDAZO 🏟️🔥", "Noche grande ⭐⚽", "De estos no hay todos los días 🏟️👀"]),
    "lunes": ("☀️ Lunes", ["football monday", "soccer monday", "football tired", "soccer coffee"], ["☀️ Lunes de combis 🍀"]),
    "viernes": ("☀️ Viernes", ["football friday", "soccer weekend", "football weekend", "soccer dance"],
                ["☀️ ¡Viernes! Se viene finde de fútbol ⚽🔥"]),
    "europa": ("⭐ Noche europea", ["champions league", "europa league", "champions league night", "soccer anthem"],
               ["☀️ Hoy hay noche europea ⭐⚽"]),
    "finde": ("🍻 Empieza el finde", ["football weekend", "soccer fans cheers", "football beer fans", "soccer weekend vibes", "football fans singing"],
              ["Empieza el finde de fútbol 🍻⚽", "Mañana hay fútbol del bueno 🍻🔥"]),
    "seguidores": ("👥 Hitos de seguidores", ["football thank you", "soccer fans thank you", "football celebration fans", "soccer crowd cheering"],
                   ["¡Gracias a todos! 💚"]),
}


# ------------------------------------------------------------------ elección automática (28/10)
# Lo que le gustó a Marcos: GIF de canales verificados de fútbol (DAZN, Liverpool, Chelsea, Play Sports, Eleven…).
# Lo que no: dibujos, series, gente bailando, solo letras. Se busca «@canal emoción» en canales de fútbol y se filtra.
CANALES = ["dazn", "lfc", "chelseafc", "playsports", "ElevenSportsBE", "premierleague", "laliga", "seriea",
           "bundesliga", "championsleague", "uefa", "fifaworldcup", "realmadrid", "fcbarcelona", "mancity",
           "manchesterunited", "arsenal", "spurs", "juventus", "acmilan", "inter", "psg", "bvb", "fcbayern",
           "atleticodemadrid", "sevillafc", "realbetis", "athleticclub", "valenciacf", "villarrealcf", "onefootball",
           "433", "brfootball", "espnfc", "goal", "skysports", "beinsports", "eurosport", "mls", "ligue1"]
EMOCION = {
    "verde": ["celebration", "goal celebration", "lets go", "happy", "yes", "winner", "fist pump", "dance"],
    "racha": ["fire", "on fire", "unstoppable", "legend", "goat", "hat trick", "magic"],
    "loca": ["crazy", "wild", "mind blown", "wow", "madness", "omg", "crazy celebration", "shocked"],
    "boleto": ["pray", "nervous", "money", "hope", "please", "fingers crossed", "come on"],
    "escalera": ["training", "keep going", "focus", "work", "warm up", "lets go"],
    "escalera_alta": ["nervous", "tension", "so close", "pressure", "focus", "come on"],
    "combi": ["lets go", "ready", "hype", "fire", "kick off", "come on"],
    "fiesta": ["party", "celebration", "dance", "dressing room", "champagne", "trophy"],
    "noche": ["tired", "sleep", "bye", "night", "rest", "wave"],
    "previa": ["nervous", "walk out", "tunnel", "kick off", "anthem", "warm up", "stadium"],
    "partidazo": ["stadium", "walk out", "anthem", "big game", "derby", "tunnel", "fans"],
    "lunes": ["tired", "monday", "training", "coffee", "morning"],
    "viernes": ["happy", "dance", "weekend", "friday", "party"],
    "europa": ["champions league", "anthem", "stadium", "night", "lets go"],
    "finde": ["fans", "weekend", "party", "cheers", "singing"],
    "seguidores": ["thank you", "fans", "applause", "celebration", "clapping"],
}
VETO = re.compile(r"cartoon|animat|anime|illustrat|drawing|spongebob|simpson|disney|text|typography|lettering|quote|"
                  r"sticker|brazil|brasil|flag|bandera|women|womens|woman|girl|nwsl|\bwsl\b|frauen|femeni|liga f|"
                  r"bikini|sexy|hot\b|kiss", re.I)


def valido(g):
    """GIF de un canal verificado de fútbol, que no sea dibujo, solo letras, bandera ni de fútbol femenino."""
    usuario = (g.get("username") or "").lower()
    if g.get("type") != "gif" or not (g.get("user") or {}).get("is_verified"):
        return False
    if usuario not in {c.lower() for c in CANALES}:
        return False
    texto = " ".join(str(g.get(k) or "") for k in ("title", "alt_text", "slug"))
    return not VETO.search(texto)


def auto(clave, momento, usados=(), vetados=(), rnd=random, intentos=8):
    """(giphy_id, url) elegido solo: «@canal emoción» en canales de fútbol, filtrado. None si no encuentra."""
    for _ in range(intentos):
        canal, emo = rnd.choice(CANALES), rnd.choice(EMOCION[momento])
        q = urlencode({"api_key": clave, "q": f"@{canal} {emo}", "limit": 25, "rating": "g"})
        try:
            with urlopen(f"https://api.giphy.com/v1/gifs/search?{q}", timeout=20) as r:
                datos = json.load(r).get("data") or []
        except Exception as e:
            print("giphy:", str(e)[:100])
            continue
        buenos = [g for g in datos if valido(g) and g["id"] not in usados and g["id"] not in vetados]
        if buenos:
            g = rnd.choice(buenos[:12])
            img = g.get("images") or {}
            return g["id"], (img.get("downsized_medium") or img.get("original") or {}).get("url")
    return None


# ------------------------------------------------------------------ GIPHY (candidatos para votar)
def buscar(clave, termino, offset=0, limite=25):
    q = urlencode({"api_key": clave, "q": termino, "limit": limite, "offset": offset, "rating": "g", "lang": "es"})
    with urlopen(f"https://api.giphy.com/v1/gifs/search?{q}", timeout=20) as r:
        datos = json.load(r).get("data") or []
    salida = []
    for g in datos:
        img = g.get("images") or {}
        url = (img.get("downsized_medium") or img.get("original") or {}).get("url")
        if url:
            salida.append((g["id"], url))
    return salida


def candidatos(clave, momento, n=5, votos=None, rnd=random):
    """n GIF de GIPHY para ese momento que Marcos aún no ha votado."""
    votos = votos if votos is not None else (leer(VOTOS, {}) or {})
    vistos = set(votos.get("no", [])) | {x["giphy"] for xs in (votos.get("si") or {}).values() for x in xs}
    terminos = list(MOMENTOS[momento][1])
    rnd.shuffle(terminos)
    salida = []
    for t in terminos:
        for off in (0, 25, 50):
            for gid, url in buscar(clave, t, off):
                if gid not in vistos and gid not in {g for g, _ in salida}:
                    salida.append((gid, url))
            if len(salida) >= n * 3:
                break
        if len(salida) >= n * 3:
            break
    rnd.shuffle(salida)
    return salida[:n]


def votar(votos, momento, giphy_id, si, file_id=None):
    votos.setdefault("si", {}).setdefault(momento, [])
    votos.setdefault("no", [])
    votos["si"][momento] = [x for x in votos["si"][momento] if x["giphy"] != giphy_id]
    if giphy_id in votos["no"]:
        votos["no"].remove(giphy_id)
    if si:
        votos["si"][momento].append({"giphy": giphy_id, "file_id": file_id})
    else:
        votos["no"].append(giphy_id)
    return votos


# ------------------------------------------------------------------ cuándo sale cada uno
def tipo_tras_post(p, publicados):
    pid, texto = p["id"], p.get("texto", "")
    if "verde" in pid:
        resueltas = [x for x in sorted(publicados, key=lambda x: x["fecha"])
                     if x.get("estado") in ("verde", "rojo") and not x.get("lista") and "verde" not in x["id"]]
        return "racha" if len(resueltas) >= 3 and all(x["estado"] == "verde" for x in resueltas[-3:]) else "verde"
    if "combi-loca" in pid:
        return "loca"
    if "boleto" in pid:
        return "boleto"
    if "escalera" in pid:
        m = re.search(r"DÍA (\d)/7", texto)
        return "escalera_alta" if m and int(m.group(1)) >= 5 else "escalera"
    if "combi-tres" in pid:
        return "combi"
    if "balance" in pid:
        m = re.search(r"✅ (\d+) acertad[oa]s · ❌ (\d+) fallad[oa]s", texto)
        return "fiesta" if m and int(m.group(1)) > int(m.group(2)) else None
    if "picks-manana" in pid:
        return "noche"
    return None


def momentos(ahora, cola, auto, env, app, est):
    """Lista de (clave_unica, momento, texto_extra) que tocan ahora."""
    hoy = ahora.strftime("%Y-%m-%d")
    ya = ahora.strftime("%Y-%m-%dT%H:%M")
    hace15 = (ahora - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M")
    hecho = set(est.get("hechos", []))
    publicados = [x for x in app.get("publicados_hoy", [])]
    salida = []
    ids_c = {p["id"] for p in cola}
    posts = cola + [dict(p, **env.get(p["id"], {})) for p in auto if p["id"] not in ids_c]
    for p in sorted(posts, key=lambda x: x.get("enviado") or ""):
        if not (p.get("mensaje_id") and hace15 <= (p.get("enviado") or "") <= ya) or f"t-{p['id']}" in hecho:
            continue
        tipo = tipo_tras_post(p, publicados)
        if tipo:
            salida.append((f"t-{p['id']}", tipo, None))
    # ⚽ / 🏟️ previa del primer partido de la noche con combi publicada
    fids = {s.split("|")[0] for p in posts if p.get("fecha", "")[:10] == hoy and p.get("mensaje_id") for s in p.get("sel") or []}
    noche = []
    for fid in fids:
        pa = (leer(DATOS / "proximos" / f"{fid}.json") or {}).get("partido")
        if pa:
            h = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
            if h.strftime("%Y-%m-%d") == hoy and 19 <= h.hour <= 22:
                gordo = pa["league"]["id"] in EUROPA or {pa["teams"]["home"]["name"], pa["teams"]["away"]["name"]} <= GRANDES
                noche.append((h, gordo))
    if noche and f"p-{hoy}" not in hecho:
        h = min(x[0] for x in noche) - timedelta(minutes=20)
        if h <= ahora <= h + timedelta(minutes=15):
            salida.append((f"p-{hoy}", "partidazo" if any(g for x, g in noche if x == min(y[0] for y in noche)) else "previa", None))
    # ☀️ 10:30 · 🍻 viernes 22:30
    m = ahora.replace(hour=10, minute=30, second=0, microsecond=0)
    if m <= ahora <= m + timedelta(minutes=15) and f"m-{hoy}" not in hecho:
        europa = any(((leer(f) or {}).get("partido") or {}).get("league", {}).get("id") in EUROPA
                     and ((leer(f) or {}).get("partido") or {}).get("fixture", {}).get("date", "")[:10] == hoy
                     for f in (DATOS / "proximos").glob("*.json"))
        dia = "europa" if europa else "lunes" if ahora.weekday() == 0 else "viernes" if ahora.weekday() == 4 else None
        if dia:
            salida.append((f"m-{hoy}", dia, None))
    f = ahora.replace(hour=22, minute=30, second=0, microsecond=0)
    if ahora.weekday() == 4 and f <= ahora <= f + timedelta(minutes=15) and f"f-{hoy}" not in hecho:
        salida.append((f"f-{hoy}", "finde", None))
    # 👥 hitos de seguidores en Threads
    seg = (((app.get("redes") or {}).get("redes") or {}).get("threads") or {}).get("seguidores")
    if seg:
        for hito in HITOS:
            if seg >= hito and f"s-{hito}" not in hecho:
                salida.append((f"s-{hito}", "seguidores", f"¡Somos {hito:,} en Threads! 💚".replace(",", ".")))
                break
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


def elegir(votos, momento, est, rnd=random):
    """Un GIF aprobado de ese momento, el que lleve más tiempo sin salir (nunca uno de los 10 últimos)."""
    lista = (votos.get("si") or {}).get(momento) or []
    if not lista:
        return None
    usados = [x.get("gif") for x in est.get("enviados", [])]
    recientes = set(usados[-10:])
    libres = [x for x in lista if x["giphy"] not in recientes] or lista
    nunca = [x for x in libres if x["giphy"] not in usados]
    return rnd.choice(nunca or libres)


def muestra_auto(n=10):
    """n GIF elegidos solos de cada momento → datos/gifs_auto.md para que Marcos los vea (no publica nada)."""
    clave = os.environ.get("GIPHY_API_KEY")
    md = ["# GIF que elegiría el bot solo (no se ha publicado nada)", ""]
    for k, (nombre, _, _) in MOMENTOS.items():
        vistos, fila = set(), []
        for _ in range(n * 2):
            r = auto(clave, k, vistos)
            if r and r[1]:
                vistos.add(r[0])
                fila.append(r[1])
            if len(fila) >= n:
                break
        md += [f"## {nombre} · {len(fila)}", "", " ".join(f'<img src="{u}" height="110">' for u in fila), ""]
    (DATOS / "gifs_auto.md").write_text("\n".join(md), encoding="utf-8")


def main(ahora=None, enviar=None, rnd=random):
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not (token and canal) or not ACTIVO:
        return
    ahora = ahora or datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    votos = leer(VOTOS, {}) or {}
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    auto = leer(RAIZ / "publicaciones" / "auto.json", []) or []
    env = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    app = leer(RAIZ / "docs" / "datos.json", {}) or {}
    if (leer(RAIZ / "publicaciones" / "control.json", {}) or {}).get("pausa"):
        return
    for k, momento, extra in momentos(ahora, cola, auto, env, app, est)[:1]:   # uno por vuelta
        if not puede(ahora, est, cola, env) and momento != "seguidores":
            break
        est.setdefault("hechos", []).append(k)
        g = elegir(votos, momento, est, rnd)
        clave = os.environ.get("GIPHY_API_KEY")
        if clave and (not g or rnd.random() < 0.5):   # 28/10: el bot elige solo (como los que gustaron a Marcos)
            usados = {x.get("gif") for x in est.get("enviados", [])}
            r = auto(clave, momento, usados, set(votos.get("no", [])), rnd)
            if r and r[1]:
                g = {"giphy": r[0], "file_id": r[1]}
        if not g:
            print(f"GIF {momento}: no hay ninguno")
            continue
        texto = extra or rnd.choice(MOMENTOS[momento][2])
        try:
            if enviar:
                enviar(g["file_id"], texto)
            else:
                from publicar_telegram import api
                api(token, "sendAnimation", {"chat_id": canal, "animation": g["file_id"], "caption": texto})
            est.setdefault("enviados", []).append({"fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "tipo": momento, "gif": g["giphy"]})
            print(f"GIF {momento}: enviado")
        except Exception as e:
            print("GIF:", str(e)[:150])
    est["hechos"] = est.get("hechos", [])[-300:]
    est["enviados"] = est.get("enviados", [])[-300:]
    ESTADO.write_text(json.dumps(est, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    import sys
    muestra_auto() if "--muestra" in sys.argv else main()
