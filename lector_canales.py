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
        posts.append({"id": pid.group(1), "fecha": fecha.group(1)[:16] if fecha else None,
                      "texto": limpiar(texto.group(1)) if texto else "",
                      "foto": "tgme_widget_message_photo" in bloque})
    return posts


CANALES_PRIVADOS = {"TIPSTER PÉREZ": "Tipster Pérez"}   # título del canal en Telegram → nombre (con la cuenta de Marcos)
FOTOS = DATOS / "tipsters_fotos"


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
    with TelegramClient(StringSession(os.environ["TG_SESSION"]), int(os.environ["TG_API_ID"]),
                        os.environ["TG_API_HASH"], receive_updates=False) as cli:
        for d in cli.iter_dialogs():
            nombre = next((v for k, v in CANALES_PRIVADOS.items() if k.lower() in (d.name or "").lower()), None)
            if not nombre:
                continue
            lista = datos.setdefault(nombre, [])
            ya = {p["id"] for p in lista}
            for m in cli.iter_messages(d.entity, limit=30):
                pid = f"{d.id}/{m.id}"
                if pid in ya:
                    continue
                p = {"id": pid, "fecha": m.date.astimezone(MADRID).strftime("%Y-%m-%dT%H:%M"),
                     "texto": m.message or "", "foto": bool(m.photo),
                     "visto": datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")}
                if m.photo:
                    ruta = FOTOS / f"{nombre.replace(' ', '_')}_{m.id}.jpg"
                    try:
                        cli.download_media(m, file=str(ruta))
                        p["foto_ruta"] = str(ruta.relative_to(DATOS.parent))
                    except Exception as e:
                        print("foto:", e)
                lista.append(p)
                nuevos += 1
            lista.sort(key=lambda p: p["fecha"] or "")
            datos[nombre] = lista[-200:]
            print(f"{nombre} (cuenta): {nuevos} nuevos")
    return nuevos


def main():
    marca = DATOS / "tipsters_raw.visto"   # cada 30 min como mucho (el bucle lo llama cada pocos minutos)
    try:
        if marca.exists() and (datetime.now(MADRID) - datetime.fromisoformat(marca.read_text().strip())).total_seconds() < 1800:
            return
    except ValueError:
        pass
    marca.write_text(datetime.now(MADRID).isoformat())
    datos = leer(SALIDA, {}) or {}
    nuevos = 0
    for usuario, nombre in CANALES.items():
        try:
            posts = leer_canal(usuario)
        except Exception as e:
            print(f"{usuario}: {e}")
            continue
        lista = datos.setdefault(nombre, [])
        ya = {p["id"] for p in lista}
        for p in posts:
            if p["id"] not in ya:
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
    main()
