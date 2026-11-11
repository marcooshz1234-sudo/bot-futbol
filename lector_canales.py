"""
10/11 (Marcos): lee los canales PÚBLICOS de Telegram de los tipsters que sigue (la vista web t.me/s/<canal>, sin
iniciar sesión) y guarda sus posts nuevos en datos/tipsters_raw.json. No interpreta nada: en cada revisión Claude
lee lo nuevo y apunta los picks (con su argumento) en datos/tipsters.json (tipsters.py los corrige y aprende).
Solo canales públicos; uno privado necesitaría la cuenta de Marcos.
"""
import html
import json
import re
import urllib.request
from datetime import datetime

from bot import DATOS, MADRID, leer

CANALES = {"Tipsanalistas": "TipsAnalistas"}   # usuario público → nombre (Pérez: falta su enlace público)
SALIDA = DATOS / "tipsters_raw.json"


def limpiar(h):
    h = re.sub(r"<br\s*/?>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    return html.unescape(h).strip()


def leer_canal(usuario):
    req = urllib.request.Request(f"https://t.me/s/{usuario}", headers={"User-Agent": "Mozilla/5.0 combilocas-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        pagina = r.read().decode("utf-8", "ignore")
    posts = []
    for bloque in re.split(r'(?=<div class="tgme_widget_message_wrap)', pagina)[1:]:
        pid = re.search(r'data-post="([^"]+)"', bloque)
        fecha = re.search(r'<time[^>]*datetime="([^"]+)"', bloque)
        texto = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', bloque, re.S)
        if not pid:
            continue
        post = {"id": pid.group(1), "fecha": fecha.group(1)[:16] if fecha else None,
                "texto": limpiar(texto.group(1)) if texto else "",
                "foto": "tgme_widget_message_photo" in bloque}
        # 11/11: la URL de la foto (el boleto) para bajarla: antes solo se bajaban las de la cuenta y los boletos
        # de TipsAnalistas (web) se quedaban sin mirar
        url = re.search(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)", bloque)
        if url:
            post["foto_url"] = html.unescape(url.group(1))
        posts.append(post)
    return posts


def bajar_foto_web(p, nombre):
    """11/11: baja la foto de un post de la web (t.me/s) a datos/tipsters_fotos/ y deja su ruta en foto_ruta."""
    url = p.pop("foto_url", None)
    if not url:
        return
    FOTOS.mkdir(parents=True, exist_ok=True)
    ruta = FOTOS / f"{re.sub(r'[^A-Za-z0-9ÁÉÍÓÚáéíóúÑñ]+', '_', nombre)[:40]}_{p['id'].rsplit('/', 1)[-1]}.jpg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 combilocas-bot"})
        with urllib.request.urlopen(req, timeout=30) as r:
            ruta.write_bytes(r.read())
        p["foto_ruta"] = str(ruta.relative_to(DATOS.parent))
    except Exception as e:
        print("foto web:", e)


CANALES_PRIVADOS = {"TIPSTER PÉREZ": "Tipster Pérez"}   # título del canal en Telegram → nombre (con la cuenta de Marcos)
FOTOS = DATOS / "tipsters_fotos"
APAGADOS = set()   # 10/11: canales apagados desde la Oficina (ajustes.canales_off)
NUESTRO = "3953339107"   # nuestro canal (no se lee)
APUESTAS = re.compile(r"pick|tips|tipster|apuest|analist|stake|insider|trader|basquet|cuota|pronost|\bbet", re.I)


def es_de_apuestas(nombre):
    import unicodedata
    plano = unicodedata.normalize("NFKD", nombre or "")   # «𝐌𝐀𝐗 𝐀𝐍𝐀𝐋𝐈𝐒𝐓𝐀» → «MAX ANALISTA»
    return bool(APUESTAS.search(plano))


def leer_con_cuenta(datos):
    """10/11: con la cuenta de Marcos (Telethon; secretos TG_API_ID, TG_API_HASH, TG_SESSION que pone él): lee también
    los canales privados. Guarda texto y las fotos (los boletos) para que Claude las mire en las revisiones.
    Solo LEE: no escribe, no se une a nada, no marca como leído."""
    import os
    if not all(os.environ.get(k) for k in ("TG_API_ID", "TG_API_HASH", "TG_SESSION")):
        return 0
    from telethon.sessions import StringSession
    from telethon.sync import TelegramClient
    nuevos = 0
    FOTOS.mkdir(parents=True, exist_ok=True)
    # 10/11: limpia lo que se cuela al pegar (espacios, saltos, comillas, «TG_SESSION=»). Solo se imprime la
    # longitud (nunca el contenido): una sesión buena mide 353 caracteres y empieza por 1.
    ses = re.sub(r"\s+", "", os.environ["TG_SESSION"]).strip("'\"")
    ses = ses.split("=", 1)[1] if ses.upper().startswith("TG_SESSION=") else ses
    if len(ses) != 353 or not ses.startswith("1"):
        print(f"TG_SESSION no parece completa: {len(ses)} caracteres (debe tener 353 y empezar por 1)")
    with TelegramClient(StringSession(ses), int(os.environ["TG_API_ID"]),
                        os.environ["TG_API_HASH"], receive_updates=False) as cli:
        vistos = []
        for d in cli.iter_dialogs():
            # 10/11 (Marcos: «he metido más canales… míralos todos»): todos los CANALES que sigue (no grupos ni
            # chats privados), menos el nuestro. Los de CANALES_PRIVADOS con su nombre corto; el resto con su título.
            if not getattr(d, "is_channel", False) or getattr(d, "is_group", False):
                continue
            plano = re.sub(r"\W", "", (d.name or "").lower())
            if str(d.id).endswith(NUESTRO) or "combilocas" in plano or "tipsanalistas" == plano:   # este ya va por la web
                continue
            nombre = next((v for k, v in CANALES_PRIVADOS.items() if k.lower() in (d.name or "").lower()), None)
            if not nombre:
                # 10/11: SOLO canales de apuestas (por el nombre). El resto de canales de Marcos (cine, noticias…)
                # ni se lee ni se apunta en ningún sitio: el repo es público.
                if not es_de_apuestas(d.name):
                    continue
                nombre = (d.name or str(d.id)).strip()
            vistos.append(nombre)
            if nombre in APAGADOS:   # 10/11: apagado desde la ficha del Ojeador (sale en la lista para encenderlo)
                continue
            lista = datos.setdefault(nombre, [])
            ya = {p["id"] for p in lista}
            nuevos_canal = 0
            for m in cli.iter_messages(d.entity, limit=30):
                pid = f"{d.id}/{m.id}"
                if pid in ya:
                    continue
                nuevos_canal += 1
                p = {"id": pid, "fecha": m.date.astimezone(MADRID).strftime("%Y-%m-%dT%H:%M"),
                     "texto": m.message or "", "foto": bool(m.photo),
                     "visto": datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")}
                # fotos (boletos) solo de los 2 últimos días: que el repo no crezca con fotos viejas
                if m.photo and (datetime.now(MADRID) - m.date.astimezone(MADRID)).days < 2:
                    ruta = FOTOS / f"{re.sub(r'[^A-Za-z0-9ÁÉÍÓÚáéíóúÑñ]+', '_', nombre)[:40]}_{m.id}.jpg"
                    try:
                        cli.download_media(m, file=str(ruta))
                        p["foto_ruta"] = str(ruta.relative_to(DATOS.parent))
                    except Exception as e:
                        print("foto:", e)
                lista.append(p)
                nuevos += 1
            lista.sort(key=lambda p: p["fecha"] or "")
            datos[nombre] = lista[-200:]
            print(f"{nombre} (cuenta): {nuevos_canal} nuevos")
        (DATOS / "canales_telegram.json").write_text(json.dumps(sorted(vistos), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return nuevos


def main(forzar=False):
    marca = DATOS / "tipsters_raw.visto"   # cada 30 min como mucho (el bucle lo llama cada pocos minutos)
    try:
        if not forzar and marca.exists() and (datetime.now(MADRID) - datetime.fromisoformat(marca.read_text().strip())).total_seconds() < 1800:
            return
    except ValueError:
        pass
    marca.write_text(datetime.now(MADRID).isoformat())
    try:   # 10/11: ficha del Ojeador en la Oficina
        import ajustes as AJ
        if AJ.pausado("ojeador"):
            print("Ojeador en pausa (Oficina): no se leen canales")
            return
        global APAGADOS
        APAGADOS = AJ.canales_off()
    except Exception as e:
        print("ajustes ojeador:", e)
    datos = leer(SALIDA, {}) or {}
    nuevos = 0
    for usuario, nombre in CANALES.items():
        if nombre in APAGADOS:
            continue
        try:
            posts = leer_canal(usuario)
        except Exception as e:
            print(f"{usuario}: {e}")
            continue
        lista = datos.setdefault(nombre, [])
        ya = {p["id"] for p in lista}
        for p in posts:
            if p["id"] not in ya:
                bajar_foto_web(p, nombre)
                p["visto"] = datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")
                lista.append(p)
                nuevos += 1
        datos[nombre] = lista[-200:]
        print(f"{nombre}: {len(posts)} posts en la web, {nuevos} nuevos")
    try:
        leer_con_cuenta(datos)
    except Exception as e:
        print("lector con la cuenta:", e)
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import sys
    main(forzar="--ya" in sys.argv)
