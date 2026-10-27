"""
Publicador de Telegram para el canal Combilocas.

Lee publicaciones/cola.json y publica en el canal las que ya han llegado a su
hora. Cada publicación enviada se marca con el id del mensaje para que nunca
salga dos veces. Lo lanza GitHub Actions cada 15 minutos.

Formato de cada publicación en la cola:
{
  "id": "2026-10-27-picks-manana",      # único
  "fecha": "2026-10-27T23:00",          # hora de España
  "texto": "🔥 9 PICKS PARA MAÑANA ...",
  "foto": "publicaciones/fotos/x.jpg"   # opcional (o null)
}
"""

import json
import re
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from incidencias import ambiguo

RAIZ = Path(__file__).resolve().parent
COLA = RAIZ / "publicaciones" / "cola.json"        # posts manuales (estado dentro)
# Regla (23/10): lo que sale en un sitio sale en todos (Threads, Instagram, Facebook y Telegram).
# Los posts automáticos de El Analista solo podrían ir a Telegram, así que no se publican solos:
# se usan como borrador y se programan a la vez en todas las redes.
AUTOS = [RAIZ / "publicaciones" / "auto.json"]   # posts del bot (plantillas.py); alineaciones.json ya no
ENVIADOS = RAIZ / "publicaciones" / "enviados.json"  # estado de los de auto.json
CONTROL = RAIZ / "publicaciones" / "control.json"    # decisiones desde el móvil (asistente)
MADRID = ZoneInfo("Europe/Madrid")
PIE = "🔞 +18 | Juega con responsabilidad"
MAX_RETRASO = timedelta(minutes=45)   # más tarde ya no se publica: podría haber empezado el partido
LIMITE_TEXTO = 4096
LIMITE_PIE_FOTO = 1024


def api(token, metodo, datos=None, archivo=None):
    url = f"https://api.telegram.org/bot{token}/{metodo}"
    if archivo:
        frontera = uuid.uuid4().hex
        cuerpo = b""
        for k, v in datos.items():
            cuerpo += (f"--{frontera}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
        nombre = Path(archivo).name
        cuerpo += (f"--{frontera}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{nombre}\"\r\n"
                   f"Content-Type: image/jpeg\r\n\r\n").encode()
        cuerpo += Path(archivo).read_bytes() + f"\r\n--{frontera}--\r\n".encode()
        req = Request(url, data=cuerpo, headers={"Content-Type": f"multipart/form-data; boundary={frontera}"})
    else:
        req = Request(url, data=json.dumps(datos).encode(), headers={"Content-Type": "application/json"})
    for intento in range(3):
        try:
            with urlopen(req, timeout=60) as r:
                return json.load(r)
        except HTTPError as e:
            resp = json.loads(e.read() or b"{}")
            espera = resp.get("parameters", {}).get("retry_after")
            if e.code == 429 and espera:
                time.sleep(espera + 1)
                continue
            raise RuntimeError(f"Telegram {e.code}: {resp.get('description')}")
        except (URLError, TimeoutError):
            if metodo in ("sendMessage", "sendPhoto"):
                raise RuntimeError("Envío sin confirmación: comprueba el canal antes de repetir") from None
            time.sleep(5)
    raise RuntimeError("Telegram no responde")


def preparar_texto(texto):
    # 27/10: sin el aviso de +18 (lo pidió Marcos)
    texto = texto.replace("jugarbien.es", "")
    texto = re.sub(r"\n*🔞 \+18 \| Jueg[ao] (?:con )?responsab\w*", "", texto).rstrip()
    return texto


def comprobar(token, canal, ahora):
    """Guarda en publicaciones/estado.json si el bot funciona y es admin del canal."""
    estado = {"comprobado": ahora.strftime("%Y-%m-%d %H:%M")}
    try:
        yo = api(token, "getMe", {})["result"]
        estado["bot"] = "@" + yo["username"]
        miembro = api(token, "getChatMember", {"chat_id": canal, "user_id": yo["id"]})["result"]
        estado["rol"] = miembro.get("status")
        estado["puede_publicar"] = bool(miembro.get("can_post_messages"))
    except Exception as e:
        estado["error"] = str(e)
    ruta = RAIZ / "publicaciones" / "estado.json"
    anterior = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    if {k: v for k, v in anterior.items() if k != "comprobado"} != {k: v for k, v in estado.items() if k != "comprobado"}:
        ruta.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Estado:", estado)


def main(objetivo=None):
    token = os.environ.get("TELEGRAM_TOKEN")
    canal = os.environ.get("TELEGRAM_CANAL")
    if not token or not canal:
        sys.exit("Faltan TELEGRAM_TOKEN o TELEGRAM_CANAL")
    ahora = datetime.now(MADRID)
    comprobar(token, canal, ahora)
    cola = json.loads(COLA.read_text(encoding="utf-8")) if COLA.exists() else []
    auto = [p for ruta in AUTOS if ruta.exists() for p in json.loads(ruta.read_text(encoding="utf-8"))]
    enviados = json.loads(ENVIADOS.read_text(encoding="utf-8")) if ENVIADOS.exists() else {}
    for p in auto:  # el estado de los automáticos vive en enviados.json
        p.update(enviados.get(p["id"], {}))
        p["_auto"] = True
    control = json.loads(CONTROL.read_text(encoding="utf-8")) if CONTROL.exists() else {}
    if control.get("pausa"):
        print("En pausa (desde el asistente): no se publica nada")
        return
    def guardar_estado():
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for p in auto:
            estado = {k: p[k] for k in ("enviado", "mensaje_id", "caducada", "error", "foto_tg") if k in p}
            if estado:
                enviados[p["id"]] = estado
        ENVIADOS.write_text(json.dumps(enviados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cambios = 0
    # correcciones de posts ya publicados: "editar_texto" en cola.json → se edita el mensaje del canal
    for p in cola:   # posts ya publicados que hay que quitar del canal: "borrar": true
        if not objetivo and p.get("borrar") and p.get("mensaje_id") and not p.get("borrado"):
            try:
                api(token, "deleteMessage", {"chat_id": canal, "message_id": p["mensaje_id"]})
                p["borrado"] = ahora.strftime("%Y-%m-%dT%H:%M")
                print(f"Borrado del canal: {p['id']}")
            except Exception as e:
                p["error_borrado"] = str(e)
            cambios += 1
    for p in cola:
        nuevo = p.get("editar_texto")
        if objetivo or not nuevo or not p.get("mensaje_id"):
            continue
        metodo, campo = ("editMessageCaption", "caption") if p.get("foto") or p.get("foto_tg") else ("editMessageText", "text")
        try:
            api(token, metodo, {"chat_id": canal, "message_id": p["mensaje_id"], campo: preparar_texto(nuevo)})
            p["texto"], p["editado"] = nuevo, ahora.strftime("%Y-%m-%dT%H:%M")
            p.pop("editar_texto")
            print(f"Editado en el canal: {p['id']}")
        except Exception as e:
            p["error_edicion"] = str(e)
            print(f"ERROR al editar {p['id']}: {e}")
        cambios += 1
    ids_cola = {p['id'] for p in cola}
    for p in sorted(cola + [p for p in auto if p['id'] not in ids_cola], key=lambda x: x["fecha"]):
        if objetivo and (p['id'], 'telegram') != objetivo:
            continue
        if p.get("enviado") or p.get("mensaje_id") or p.get("caducada") or p.get("solo_redes") or p.get("borrar"):
            continue
        if ambiguo(p.get("error")):
            continue
        if p["id"] in control.get("cancelados", []):
            p["caducada"] = "cancelado"
            cambios += 1
            continue
        cuando = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
        if cuando > ahora:
            continue
        if ahora - cuando > MAX_RETRASO:
            p["caducada"] = True
            cambios += 1
            print(f"Caducada (no se publica): {p['id']}")
            continue
        if p.get("tarjeta") and not (RAIZ / "publicaciones" / "media" / f"{p['id']}.tarjeta.jpg").exists():
            print(f"Esperando la foto del partido: {p['id']}")   # 28/10 (Marcos): combi de partido SIEMPRE con foto
            continue
        texto = preparar_texto(control.get("textos", {}).get(p["id"], p["texto"]))
        foto = p.get("foto")
        # 27/10 (Marcos): las combis de un partido también van con su foto (escudos y hora) en Telegram
        tarjeta = RAIZ / "publicaciones" / "media" / f"{p['id']}.tarjeta.jpg"
        if not foto and p.get("tarjeta") and tarjeta.exists() and len(texto) <= LIMITE_PIE_FOTO:
            foto = str(tarjeta.relative_to(RAIZ))
            p["foto_tg"] = foto
        try:
            if foto:
                if len(texto) > LIMITE_PIE_FOTO:
                    raise RuntimeError(f"pie de foto de {len(texto)} caracteres (máx {LIMITE_PIE_FOTO})")
                r = api(token, "sendPhoto", {"chat_id": canal, "caption": texto}, archivo=RAIZ / foto)
            else:
                if len(texto) > LIMITE_TEXTO:
                    raise RuntimeError(f"texto de {len(texto)} caracteres (máx {LIMITE_TEXTO})")
                r = api(token, "sendMessage", {"chat_id": canal, "text": texto,
                                                "link_preview_options": {"is_disabled": True}})
        except Exception as e:
            p["error"] = str(e)
            cambios += 1
            print(f"ERROR en {p['id']}: {e}")
            guardar_estado()
            continue
        p["enviado"] = ahora.strftime("%Y-%m-%dT%H:%M")
        p["mensaje_id"] = r["result"]["message_id"]
        p.pop("error", None)
        cambios += 1
        print(f"Publicada: {p['id']}")
        guardar_estado()
        time.sleep(2)
    if cambios:
        guardar_estado()
    print(f"Hecho. Cambios: {cambios}")


if __name__ == "__main__":
    main()
