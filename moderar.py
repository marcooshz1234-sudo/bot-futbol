"""
Moderación de comentarios · quita el spam de Threads, Instagram y Facebook.

Mira los comentarios de los últimos posts (DIAS_ATRAS) y, si un comentario parece
spam o publicidad, lo quita y avisa al dueño del canal por Telegram:
  - Instagram y Facebook: se BORRA.
  - Threads: se OCULTA (la API de Threads no deja borrar comentarios de otros).
Spam = enlaces, teléfonos, o frases típicas de "escríbeme / gana dinero / grupo VIP".
Las menciones a amigos (@alguien) NO cuentan como spam. Nunca toca nuestros comentarios.
Lo ya revisado se apunta en datos/moderacion.json para no mirarlo dos veces.
"""

import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from redes import FACEBOOK, INSTAGRAM, THREADS, llamar, pagina_facebook

RAIZ = Path(__file__).resolve().parent
ESTADO = RAIZ / "datos" / "moderacion.json"
DIAS_ATRAS = 7
NUESTRAS = {"combilocas"}

ENLACE = re.compile(r"(https?://|www\.|\b[\w-]+\.(com|net|org|io|me|ly|xyz|bet|vip|club|site|link|app|es)\b|"
                    r"t\.me/|wa\.me/|bit\.ly|linktr\.ee)", re.I)
TELEFONO = re.compile(r"(\+?\d[\d\s.-]{8,}\d)")
FRASES = [
    "escribeme", "escribeme al privado", "mandame dm", "manda dm", "al dm", "por dm", "por privado", "al privado",
    "info al dm", "whatsapp", "wasap", "gana dinero", "ganar dinero", "dinero facil", "invierte", "inversion",
    "criptomoneda", "crypto", "bitcoin", "forex", "trading", "grupo vip", "canal vip", "partido arreglado",
    "partidos arreglados", "amañado", "seguidores gratis", "followers", "sigueme y te sigo", "promo en mi perfil",
    "link en mi perfil", "enlace en mi perfil", "mira mi perfil", "revisa mi perfil", "100% seguro", "sin riesgo",
]


def normal(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t)


PERMITIDOS = re.compile(r"\b(bet365|sofascore|flashscore|combilocas)\.(es|com)\b", re.I)   # nombrarlos no es spam


def es_spam(texto):
    n = normal(texto)
    if ENLACE.search(PERMITIDOS.sub("", texto or "")):
        return "enlace"
    if TELEFONO.search(texto or "") and not re.fullmatch(r"[\d\s,.+-]*", (texto or "").strip()):
        return "teléfono"
    for f in FRASES:
        if normal(f) in n:
            return f"«{f}»"
    return None


def reciente(ts):
    try:
        f = datetime.fromisoformat((ts or "").replace("Z", "+00:00").replace("+0000", "+00:00"))
    except ValueError:
        return True
    return f >= datetime.now(timezone.utc) - timedelta(days=DIAS_ATRAS)


def comentarios_threads(token):
    posts = llamar("GET", f"{THREADS}/me/threads", {"fields": "id,timestamp", "limit": 40, "access_token": token})
    for post in posts.get("data", []):
        if not reciente(post.get("timestamp")):
            continue
        r = llamar("GET", f"{THREADS}/{post['id']}/replies",
                   {"fields": "id,text,username,hide_status", "access_token": token})
        for c in r.get("data", []):
            if c.get("hide_status") not in ("HIDDEN", "COVERED"):
                yield "threads", c["id"], c.get("username", ""), c.get("text", "")


def comentarios_instagram(token):
    posts = llamar("GET", f"{INSTAGRAM}/me/media", {"fields": "id,timestamp", "limit": 40, "access_token": token})
    for post in posts.get("data", []):
        if not reciente(post.get("timestamp")):
            continue
        r = llamar("GET", f"{INSTAGRAM}/{post['id']}/comments",
                   {"fields": "id,text,username", "access_token": token})
        for c in r.get("data", []):
            yield "instagram", c["id"], c.get("username", ""), c.get("text", "")


def comentarios_facebook(token_usuario, pagina):
    pagina, token = pagina_facebook(token_usuario, pagina)
    posts = llamar("GET", f"{FACEBOOK}/{pagina}/posts", {"fields": "id,created_time", "limit": 40, "access_token": token})
    for post in posts.get("data", []):
        if not reciente(post.get("created_time")):
            continue
        r = llamar("GET", f"{FACEBOOK}/{post['id']}/comments",
                   {"fields": "id,message,from", "access_token": token})
        for c in r.get("data", []):
            if (c.get("from") or {}).get("id") == pagina:
                continue
            yield "facebook", c["id"], (c.get("from") or {}).get("name", ""), c.get("message", "")


def quitar(red, cid, claves):
    if red == "threads":
        llamar("POST", f"{THREADS}/{cid}/manage_reply", {"hide": "true", "access_token": claves["threads"]})
        return "oculto"
    base, tok = ((INSTAGRAM, claves["instagram"]) if red == "instagram"
                 else (FACEBOOK, pagina_facebook(claves["facebook"], os.environ.get("FACEBOOK_PAGINA"))[1]))
    llamar("DELETE", f"{base}/{cid}", {"access_token": tok})
    return "borrado"


def avisar(lineas):
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not (token and canal and lineas):
        return
    from publicar_telegram import api
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    api(token, "sendMessage", {"chat_id": duenio, "text": "🧹 Spam quitado de las redes:\n\n" + "\n\n".join(lineas)[:3900]})


def main():
    claves = {"threads": os.environ.get("THREADS_TOKEN"), "instagram": os.environ.get("INSTAGRAM_TOKEN"),
              "facebook": os.environ.get("FACEBOOK_TOKEN")}
    pagina = os.environ.get("FACEBOOK_PAGINA")
    if not any(claves.values()):
        print("Moderación: sin claves de Meta todavía")
        return
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {"vistos": [], "quitados": []}
    vistos = set(estado["vistos"])
    fuentes = []
    if claves["threads"]:
        fuentes.append(lambda: comentarios_threads(claves["threads"]))
    if claves["instagram"]:
        fuentes.append(lambda: comentarios_instagram(claves["instagram"]))
    if claves["facebook"]:
        fuentes.append(lambda: comentarios_facebook(claves["facebook"], pagina))
    avisos = []
    for fuente in fuentes:
        try:
            for red, cid, autor, texto in fuente():
                if cid in vistos or autor.lower() in NUESTRAS:
                    continue
                vistos.add(cid)
                motivo = es_spam(texto)
                if not motivo:
                    continue
                try:
                    hecho = quitar(red, cid, claves)
                    estado["quitados"].append({"red": red, "id": cid, "autor": autor, "texto": texto,
                                               "motivo": motivo, "cuando": datetime.now(timezone.utc).isoformat()})
                    avisos.append(f"{red} · {autor} ({motivo}, {hecho}):\n{texto[:200]}")
                    print(f"Moderación: {hecho} en {red} ({motivo})")
                except Exception as e:
                    vistos.discard(cid)   # se reintenta en la siguiente vuelta
                    print(f"Moderación: no se pudo quitar {cid} en {red}: {e}")
        except Exception as e:
            print(f"Moderación: error leyendo comentarios: {e}")
    estado["vistos"] = sorted(vistos)[-5000:]
    estado["quitados"] = estado["quitados"][-500:]
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        avisar(avisos)
    except Exception as e:
        print(f"Moderación: no se pudo avisar por Telegram: {e}")
    print(f"Moderación: {len(avisos)} comentarios quitados")


if __name__ == "__main__":
    main()
