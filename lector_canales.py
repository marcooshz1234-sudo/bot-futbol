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
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
