"""
El Publicador en redes · Threads, Instagram y Facebook directos (sin Metricool).

Se ejecuta en el mismo bucle que publicar_telegram.py (cada minuto). Para cada post
de publicaciones/cola.json con "directo": true que ya ha llegado a su hora:
  - Threads: solo texto (máx. 500 caracteres).
  - Instagram: la imagen publicaciones/media/<id>.jpg y, REEL_TRAS minutos después, el
    reel <id>.mp4 (si existe).
  - Facebook: foto o texto, según "facebook": "foto" | "texto" (si no se dice, alterna).
El estado de cada red se guarda dentro del post: p["redes"] = {"threads": id, ...}.
Si una red falla, se apunta el error y se reintenta en la siguiente vuelta (hasta
MAX_RETRASO); las demás siguen. Las imágenes se sirven desde GitHub (repo público).

Claves (GitHub → Settings → Secrets): THREADS_TOKEN, INSTAGRAM_TOKEN, FACEBOOK_TOKEN
(token de página) y FACEBOOK_PAGINA. Si falta la de una red, esa red se salta.
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

RAIZ = Path(__file__).resolve().parent
COLA = RAIZ / "publicaciones" / "cola.json"
AUTO = RAIZ / "publicaciones" / "auto.json"            # posts del bot (plantillas.py)
ESTADO_AUTO = RAIZ / "publicaciones" / "enviados_redes.json"   # su estado en redes
CAMPOS = ("redes", "errores_redes", "facebook_tipo")
MADRID = ZoneInfo("Europe/Madrid")
RAW = "https://raw.githubusercontent.com/marcooshz1234-sudo/bot-futbol/main/publicaciones/media/"
PIE = "🔞 +18 | Juego responsable"
MAX_RETRASO = timedelta(minutes=45)
REEL_TRAS = timedelta(minutes=10)
LIMITE_THREADS = 500

THREADS = "https://graph.threads.net/v1.0"
INSTAGRAM = "https://graph.instagram.com/v21.0"
FACEBOOK = "https://graph.facebook.com/v21.0"


def llamar(metodo, url, params):
    datos = urlencode(params).encode()
    req = Request(url if metodo == "POST" else f"{url}?{datos.decode()}",
                  data=datos if metodo == "POST" else None, method=metodo)
    try:
        with urlopen(req, timeout=90) as r:
            return json.load(r)
    except HTTPError as e:
        cuerpo = e.read().decode(errors="replace")
        try:
            msg = json.loads(cuerpo).get("error", {}).get("message", cuerpo)
        except ValueError:
            msg = cuerpo
        raise RuntimeError(f"{e.code}: {msg[:300]}") from None


def texto_final(p):
    t = p["texto"].replace("jugarbien.es", "").rstrip()
    if PIE not in t:
        t += "\n\n" + PIE
    return t


_PAGINA = {}


def pagina_facebook(token_usuario, pagina=None):
    """Con el token de usuario (larga duración) saca la página y su token de página.
    Si no se dice qué página, coge la primera que administra (Combilocas)."""
    if "id" not in _PAGINA:
        cuentas = llamar("GET", f"{FACEBOOK}/me/accounts", {"fields": "id,name,access_token", "access_token": token_usuario})
        lista = cuentas.get("data", [])
        if pagina:
            lista = [c for c in lista if c["id"] == str(pagina)] or lista
        if not lista:
            raise RuntimeError("el token no administra ninguna página de Facebook")
        _PAGINA.update(id=lista[0]["id"], nombre=lista[0]["name"], token=lista[0]["access_token"])
    return _PAGINA["id"], _PAGINA["token"]


def url_media(p, ext):
    f = RAIZ / "publicaciones" / "media" / f"{p['id']}.{ext}"
    if not f.exists():
        return None
    return f"{RAW}{p['id']}.{ext}?v={int(f.stat().st_mtime)}"   # cambia si se regenera


# ------------------------------------------------------------------ cada red

def threads(p, token):
    t = texto_final(p)
    if len(t) > LIMITE_THREADS:   # sin la frase del dato si no cabe
        t = "\n".join(l for l in t.split("\n") if not l.startswith("📊")).replace("\n\n\n", "\n\n")
    if len(t) > LIMITE_THREADS:
        raise RuntimeError(f"{len(t)} caracteres (máx. {LIMITE_THREADS})")
    c = llamar("POST", f"{THREADS}/me/threads", {"media_type": "TEXT", "text": t, "access_token": token})
    time.sleep(3)
    return llamar("POST", f"{THREADS}/me/threads_publish", {"creation_id": c["id"], "access_token": token})["id"]


def esperar_contenedor(base, cid, token, intentos=40):
    for _ in range(intentos):
        st = llamar("GET", f"{base}/{cid}", {"fields": "status_code,status", "access_token": token})
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"contenedor {st.get('status_code')}: {st.get('status')}")
        time.sleep(6)
    raise RuntimeError("el vídeo no terminó de procesarse a tiempo")


def instagram(p, token, reel=False):
    url = url_media(p, "mp4" if reel else "jpg")
    if not url:
        raise RuntimeError("falta la imagen/vídeo en publicaciones/media")
    params = {"caption": texto_final(p), "access_token": token}
    params.update({"media_type": "REELS", "video_url": url, "share_to_feed": "true",
                   "thumb_offset": "500"}   # portada = el post entero (primer fotograma)
                  if reel else {"image_url": url})
    c = llamar("POST", f"{INSTAGRAM}/me/media", params)
    esperar_contenedor(INSTAGRAM, c["id"], token, 40 if reel else 10)
    return llamar("POST", f"{INSTAGRAM}/me/media_publish", {"creation_id": c["id"], "access_token": token})["id"]


def facebook(p, token_usuario, pagina, con_foto):
    pagina, token = pagina_facebook(token_usuario, pagina)
    if con_foto and url_media(p, "jpg"):
        r = llamar("POST", f"{FACEBOOK}/{pagina}/photos",
                   {"url": url_media(p, "jpg"), "caption": texto_final(p), "access_token": token})
        return r.get("post_id") or r["id"]
    return llamar("POST", f"{FACEBOOK}/{pagina}/feed", {"message": texto_final(p), "access_token": token})["id"]


# ------------------------------------------------------------------ bucle

def main():
    claves = {"threads": os.environ.get("THREADS_TOKEN"), "instagram": os.environ.get("INSTAGRAM_TOKEN"),
              "facebook": os.environ.get("FACEBOOK_TOKEN")}
    pagina = os.environ.get("FACEBOOK_PAGINA")
    if not any(claves.values()):
        print("Redes: sin claves de Meta todavía (se publica solo en Telegram)")
        return
    cola = json.loads(COLA.read_text(encoding="utf-8"))
    auto = json.loads(AUTO.read_text(encoding="utf-8")) if AUTO.exists() else []
    est_auto = json.loads(ESTADO_AUTO.read_text(encoding="utf-8")) if ESTADO_AUTO.exists() else {}
    for p in auto:
        p.update(est_auto.get(p["id"], {}))
    ids_cola = {p["id"] for p in cola}
    cola_total = cola + [p for p in auto if p["id"] not in ids_cola]
    ahora = datetime.now(MADRID)
    ultimo_fb = next((p.get("facebook_tipo") for p in sorted(cola_total, key=lambda x: x["fecha"], reverse=True)
                      if p.get("facebook_tipo")), "texto")
    cambios = 0
    for p in sorted(cola_total, key=lambda x: x["fecha"]):
        if not p.get("directo") or p.get("caducada") or p.get("borrar"):
            continue
        cuando = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
        if cuando > ahora or ahora - cuando > MAX_RETRASO + REEL_TRAS:
            continue
        hecho = p.setdefault("redes", {})
        errores = p.setdefault("errores_redes", {})
        tareas = []
        if claves["threads"] and "threads" not in hecho:
            tareas.append(("threads", lambda: threads(p, claves["threads"])))
        if claves["instagram"] and "instagram" not in hecho and not p.get("sin_instagram"):
            tareas.append(("instagram", lambda: instagram(p, claves["instagram"])))
        if (claves["instagram"] and "instagram_reel" not in hecho and url_media(p, "mp4")
                and ahora >= cuando + REEL_TRAS and "instagram" in hecho):
            tareas.append(("instagram_reel", lambda: instagram(p, claves["instagram"], reel=True)))
        if claves["facebook"] and "facebook" not in hecho:
            tipo = p.get("facebook") or ("foto" if ultimo_fb == "texto" else "texto")
            tareas.append(("facebook", lambda tipo=tipo: facebook(p, claves["facebook"], pagina, tipo == "foto")))
        for red, hacer in tareas:
            if ahora - cuando > MAX_RETRASO and red != "instagram_reel":
                errores[red] = "caducado: no salió a tiempo"
                hecho[red] = None
                cambios += 1
                continue
            try:
                hecho[red] = hacer()
                errores.pop(red, None)
                if red == "facebook":
                    p["facebook_tipo"] = ultimo_fb = p.get("facebook") or ("foto" if ultimo_fb == "texto" else "texto")
                print(f"{red}: publicado {p['id']}")
            except Exception as e:
                errores[red] = str(e)
                print(f"{red}: ERROR en {p['id']}: {e}")
            cambios += 1
        if not errores:
            p.pop("errores_redes", None)
    if cambios:
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for p in auto:
            if any(k in p for k in CAMPOS):
                est_auto[p["id"]] = {k: p[k] for k in CAMPOS if k in p}
        ESTADO_AUTO.write_text(json.dumps(est_auto, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Redes: {cambios} cambios")


if __name__ == "__main__":
    main()
