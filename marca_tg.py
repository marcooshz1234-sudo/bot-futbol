"""12/11 (Marcos: «activa todo menos el balance de la noche»; «el muñeco no me gusta, quítalo»).

Posts de Telegram con las imágenes de la marca (publicaciones/media/marca, hechas con ChatGPT):
  - buenos_dias:   9:30–10:20, una vez al día. Una de las 3 fotos (cambia cada día) y lo que sale hoy con su hora.
  - noche_europea: días de Champions / Europa League / Conference, 17:00–18:30, una vez.
  - en_directo:    cuando empieza un partido de un post nuestro de Telegram (pick del día, escalera, combi…),
                   como mucho 2 al día y no más de uno cada 45 min.
  - pleno:         si todos los posts de hoy en Telegram con picks han salido en verde (3 o más): la animación.
(La escalera, el pick del día y los rojos llevan su foto desde publicar_telegram.foto_de_marca.)
Estado en datos/marca_tg.json para no repetir.
"""
import hashlib
import json
import os
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer

MARCA = RAIZ / "publicaciones" / "media" / "marca"
ESTADO = DATOS / "marca_tg.json"
EUROPA = {2, 3, 848}
MAX_DIRECTO = 2
SALUDOS = [
    "☀️ ¡Buenos días, familia!\n\n¿Estáis listos para hoy? 🍀",
    "☀️ Buenos días a todos 👋\n\nHoy hay fútbol y hay que pintarlo de verde ✅",
    "☕ ¡Buenos días, familia!\n\nCafé en mano y a por el día 🔥",
    "☀️ ¡Arriba, familia!\n\nHoy venimos a por todas 💪🍀",
    "🌅 Buenos días 👋\n\n¿Preparados? Hoy hay mucho que sacar 👀",
]
# 12/11 (Marcos: «y añade: lo que vaya saliendo lo iremos subiendo también… dale tu toque»): cambia cada día
EXTRA = [
    "⚡ Y si durante el día sale algo bueno, aquí lo tendréis al momento",
    "📲 Lo que vaya cayendo a lo largo del día, lo subimos sobre la marcha 🔥",
    "👀 Y atentos, que lo que salga bueno durante el día también va para vosotros",
    "🔥 Y esto es solo el principio: lo que aparezca, lo iréis viendo aquí",
    "💚 Y si encontramos algo que merezca la pena, os lo dejamos al instante",
]
NOMBRES = [("pick-seguro-2", "Segundo pick"), ("pick-seguro", "Pick del día"), ("escalera", "Reto escalera"),
           ("combi-tres", "Combi del día"), ("combi-partido", "Combi de partido"), ("combi-loca", "La loca"),
           ("combi-multi", "Combi larga")]


def elegir(lista, semilla):
    return lista[int(hashlib.sha1(semilla.encode()).hexdigest(), 16) % len(lista)]


def posts_de(dia):
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    auto = leer(RAIZ / "publicaciones" / "auto.json", []) or []
    env = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    fuera = set(control.get("cancelados") or [])
    out = []
    for p in cola + auto:
        if not p["id"].startswith(dia) or p["id"] in fuera or p.get("caducada") or p.get("verde_de"):
            continue
        if any(k in p["id"] for k in ("verde", "rojo", "balance")):
            continue
        en_tg = not p.get("solo_redes") and (not p.get("solo_en") or "telegram" in p["solo_en"])
        if en_tg:
            out.append(dict(p, **{k: v for k, v in (env.get(p["id"]) or {}).items() if k in ("enviado", "mensaje_id")}))
    return out


def agenda(dia):
    """«⏰ 10:30 · Pick del día» de lo que sale hoy en Telegram (sin las copias de canales ni ganadores)."""
    lineas = []
    for p in sorted(posts_de(dia), key=lambda p: p["fecha"]):
        nombre = next((n for k, n in NOMBRES if k in p["id"]), None)
        if nombre and not any(nombre in l for l in lineas):
            lineas.append(f"⏰ {p['fecha'][11:16]} · {nombre}")
    return lineas


def enviar(foto, texto, animacion=False):
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    print(("ANIMACIÓN " if animacion else "FOTO ") + foto.name + "\n" + texto)
    if not (token and canal):
        return None
    from publicar_telegram import api
    if animacion:
        return api(token, "sendAnimation", {"chat_id": canal, "caption": texto}, archivo=foto,
                   campo="animation", tipo="video/mp4")
    return api(token, "sendPhoto", {"chat_id": canal, "caption": texto}, archivo=foto)


def buenos_dias(ahora, est):
    dia = ahora.strftime("%Y-%m-%d")
    if est.get("buenos_dias") == dia or not (ahora.replace(hour=9, minute=30) <= ahora <= ahora.replace(hour=10, minute=20)):
        return None
    ag = agenda(dia)
    if not ag:
        return None
    foto = MARCA / f"buenos-dias-{ahora.toordinal() % 3 + 1}.jpg"
    texto = (elegir(SALUDOS, dia) + "\n\n📋 Hoy en el canal:\n" + "\n".join(ag[:6])
             + "\n\n" + elegir(EXTRA, dia + "x") + "\n\n🔔 Activad las notificaciones")
    enviar(foto, texto)
    est["buenos_dias"] = dia
    return texto


def partidos_hoy(dia):
    out = []
    for f in (DATOS / "proximos").glob("*.json"):
        pa = (leer(f, {}) or {}).get("partido") or {}
        fx = pa.get("fixture") or {}
        if fx.get("date") and datetime.fromisoformat(fx["date"]).astimezone(MADRID).strftime("%Y-%m-%d") == dia:
            out.append(pa)
    return out


def noche_europea(ahora, est):
    dia = ahora.strftime("%Y-%m-%d")
    if est.get("noche_europea") == dia or not (ahora.replace(hour=17) <= ahora <= ahora.replace(hour=18, minute=30)):
        return None
    eu = [p for p in partidos_hoy(dia) if (p.get("league") or {}).get("id") in EUROPA]
    if not eu:
        return None
    from plantillas import es
    comps = sorted({p["league"]["name"].replace("UEFA ", "") for p in eu})
    destacados = sorted(eu, key=lambda p: p["fixture"]["date"])[:4]
    texto = (f"⭐ ¡NOCHE EUROPEA! ⭐\n\nHoy hay {len(eu)} partidos de {' y '.join(comps)} 🔥\n\n"
             + "\n".join(f"⚽ {es(p['teams']['home']['name'])} – {es(p['teams']['away']['name'])} · "
                         f"{datetime.fromisoformat(p['fixture']['date']).astimezone(MADRID):%H:%M}" for p in destacados)
             + "\n\n🍀 Nuestros picks, en el canal")
    enviar(MARCA / "noche-europea.jpg", texto)
    est["noche_europea"] = dia
    return texto


def en_directo(ahora, est):
    dia = ahora.strftime("%Y-%m-%d")
    hechos = est.setdefault("directo", {}).setdefault(dia, [])
    if len(hechos) >= MAX_DIRECTO:
        return None
    ultimo = est.get("directo_ultimo")
    if ultimo and ahora - datetime.fromisoformat(ultimo) < timedelta(minutes=45):
        return None
    vivos = leer(DATOS / "en_directo.json", {}) or {}
    from plantillas import es
    for p in sorted(posts_de(dia), key=lambda p: (0 if "pick-seguro" in p["id"] or "escalera" in p["id"] else 1, p["fecha"])):
        if not p.get("enviado") or "ganadores" in p["id"]:
            continue
        for s in p.get("sel") or []:
            fid = str(s).split("|")[0]
            v = vivos.get(fid) or {}
            if fid in hechos or v.get("estado") not in ("1H",) or (v.get("minuto") or 99) > 12:
                continue
            pa = (leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("partido") or {}
            if not pa:
                continue
            titulo = (p.get("texto") or "").strip().splitlines()[0][:70]
            texto = (f"🔴 ¡EMPIEZA {es(pa['teams']['home']['name']).upper()} – {es(pa['teams']['away']['name']).upper()}!\n\n"
                     f"Lo llevamos en: {titulo}\n\n🍀 ¡Vamos a por el verde!")
            enviar(MARCA / "en-directo.jpg", texto)
            hechos.append(fid)
            est["directo_ultimo"] = ahora.isoformat()
            return texto
    return None


def pleno(ahora, est):
    dia = ahora.strftime("%Y-%m-%d")
    if est.get("pleno") == dia:
        return None
    ids = {p["id"] for p in posts_de(dia) if p.get("enviado") and p.get("sel") and "ganadores" not in p["id"]}
    pub = {p["id"]: p for p in (leer(RAIZ / "docs" / "datos.json", {}) or {}).get("publicados_hoy", [])}
    estados = [pub.get(i, {}).get("estado") for i in ids]
    if len(ids) < 3 or not all(e == "verde" for e in estados):
        return None
    texto = f"🏆 ¡PLENO! 🏆\n\n✅ {len(ids)} de {len(ids)} en verde hoy\n\n💚 ¡Gracias por estar ahí, familia! Mañana, más 🍀"
    enviar(MARCA / "pleno.mp4", texto, animacion=True)
    est["pleno"] = dia
    return texto


def main(ahora=None):
    ahora = ahora or datetime.now(MADRID)
    try:
        import ajustes as AJ
        if not AJ.valor("marca_tg"):
            print("marca_tg apagado en ajustes")
            return
    except Exception:
        pass
    est = leer(ESTADO, {}) or {}
    for f in (buenos_dias, noche_europea, en_directo, pleno):
        try:
            f(ahora, est)
        except Exception as e:
            print(f"marca_tg ({f.__name__}):", e)
    limite = (ahora - timedelta(days=3)).strftime("%Y-%m-%d")
    est["directo"] = {d: v for d, v in (est.get("directo") or {}).items() if d >= limite}
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
