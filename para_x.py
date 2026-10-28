"""
28/10 (Marcos): X (Twitter) sin pagar la API. Cuando un post sale en Threads, el bot del móvil le manda a Marcos
el mismo texto con un botón «𝕏 Publicar en X» que abre la app de X con el texto ya escrito (él solo toca Publicar).
Si el post lleva foto (combi de un partido), le llega la foto para adjuntarla.
X deja 280 caracteres (los emojis cuentan doble): si no cabe, se quitan primero las líneas que sobran.
Lo ya mandado se guarda en datos/para_x.json.
"""
import json
import re
from datetime import datetime, timedelta
from urllib.parse import quote

from bot import DATOS, MADRID, RAIZ, leer

ESTADO = DATOS / "para_x.json"
LIMITE_X = 280
# líneas que se pueden quitar si no cabe, de menos a más importante
SOBRAN = (r"^🟢 VERDE A VERDE", r"^🔥 Resultado probable", r"^¿Quién la llevaba", r"^🍀 ¿LA PINTAMOS", r"^📊 Según",
          r"^💚 Más ", r"^⚽ ¡Combina", r"^💶 ")


def largo_x(t):
    """Caracteres como los cuenta X: emojis y letras de otros alfabetos valen 2."""
    return sum(2 if ord(c) > 0x10FF else 1 for c in t)


def texto_x(t):
    t = re.sub(r"\n*🔞 \+18 \| Jueg[ao] (?:con )?responsab\w*", "", t.replace("jugarbien.es", "")).strip()
    for patron in SOBRAN:
        if largo_x(t) <= LIMITE_X:
            break
        t = "\n".join(l for l in t.split("\n") if not re.match(patron, l))
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
    # si aún no cabe, fuera patas desde el final (la primera línea es el título) y se dice cuántas faltan
    ls, quitadas = t.split("\n"), 0
    while largo_x("\n".join(ls)) > LIMITE_X - 12:
        i = max((k for k, l in enumerate(ls) if k > 0 and re.match(r"^(✅|🎯|•)", l) and not re.search(r"cuota", l, re.I)), default=None)
        if i is None:
            break
        ls.pop(i)
        quitadas += 1
    if quitadas:
        i = max((k for k, l in enumerate(ls) if k > 0 and re.match(r"^(✅|🎯|•)", l) and not re.search(r"cuota", l, re.I)), default=0)
        ls.insert(i + 1, f"➕ {quitadas} más")
    return "\n".join(ls)


def boton(t):
    return {"inline_keyboard": [[{"text": "𝕏 Publicar en X", "url": "https://x.com/intent/post?text=" + quote(t)}]]}


def pendientes(ahora, cola, auto, est_redes, control, hecho):
    """Posts ya publicados en Threads en las últimas 2 h que aún no se han mandado para X."""
    desde = (ahora - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
    ids_cola = {p["id"] for p in cola}
    posts = cola + [dict(p, **est_redes.get(p["id"], {})) for p in auto if p["id"] not in ids_cola]
    salida = []
    for p in sorted(posts, key=lambda x: x["fecha"]):
        hilo = str((p.get("redes") or {}).get("threads") or "")
        if not hilo.isdigit() or p["fecha"] < desde or p["id"] in hecho:
            continue
        texto = control.get("textos", {}).get(p["id"], p.get("texto_threads") or p["texto"])
        salida.append((p, texto_x(texto)))
    return salida


def main(token, canal, api, ahora=None):
    ahora = ahora or datetime.now(MADRID)
    hecho = set(leer(ESTADO, []) or [])
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    auto = leer(RAIZ / "publicaciones" / "auto.json", []) or []
    est = leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {}
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    lista = pendientes(ahora, cola, auto, est, control, hecho)
    if not ESTADO.exists():   # la primera vez no se manda lo de antes
        ESTADO.write_text(json.dumps(sorted(hecho | {p["id"] for p, _ in lista})), encoding="utf-8")
        return 0
    if not lista:
        return 0
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    n = 0
    for p, t in lista[:6]:
        aviso = "" if largo_x(t) <= LIMITE_X else "\n\n⚠️ No cabe entero en X (280): recórtalo un poco antes de publicar."
        foto = RAIZ / "publicaciones" / "media" / f"{p['id']}.tarjeta.jpg"
        try:
            if p.get("tarjeta") and foto.exists():
                api(token, "sendPhoto", {"chat_id": duenio, "caption": f"𝕏 Para X (adjunta esta foto):\n\n{t}"[:1024],
                                         "reply_markup": json.dumps(boton(t))}, archivo=str(foto))
            else:
                api(token, "sendMessage", {"chat_id": duenio, "text": f"𝕏 Para X:\n\n{t}{aviso}", "reply_markup": boton(t)})
            hecho.add(p["id"])
            n += 1
        except Exception as e:
            print("para X:", str(e)[:150])
    ESTADO.write_text(json.dumps(sorted(hecho)[-500:]), encoding="utf-8")
    return n
