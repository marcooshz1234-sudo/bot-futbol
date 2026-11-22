"""
22/11 (Marcos: «cuando entre una combi de cuota 10, 11, 12… de ahí para arriba, quiero una publicación de que hemos
acertado esa combi, cuál era y todo el rollo, y que me la fije en el canal para que se vea lo último acertado»).
Mira docs/datos.json → publicados_hoy (ayer y hoy, lo publicado en Telegram o en redes, ya corregido por la app):
combi entera en verde, de @CUOTA_MIN o más y de 2+ patas → post en el canal de Telegram con sus patas ✅ y se fija.
Una vez por combi (datos/grandes_aciertos.json). Interruptor: control.json "grandes_aciertos": false lo apaga.
"""
import json
import os
from datetime import datetime
from pathlib import Path

from bot import DATOS, MADRID, RAIZ, leer

CUOTA_MIN = 10.0
ESTADO = DATOS / "grandes_aciertos.json"


def coma(x):
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def candidatas(publicados, hechos):
    out = []
    for c in publicados or []:
        if (c.get("estado") == "verde" and (c.get("cuota") or 0) >= CUOTA_MIN and not c.get("lista")
                and "-verde" not in c["id"] and len(c.get("picks") or []) >= 2 and c["id"] not in hechos
                and all(x.get("estado") == "verde" for x in c["picks"])):
            out.append(c)
    return out


def texto(c, post=None):
    donde = "en Threads" if "-th-" in c["id"] or (post or {}).get("solo_redes") else "aquí en el canal"
    patas = "\n".join(f"✅ {x['texto']}" + (f" ({x['partido']})" if x.get("partido") and x["partido"] not in x["texto"] else "")
                      for x in c["picks"])
    return (f"🏆💚 ¡COMBI ACERTADA @{coma(c['cuota'])}! 💚🏆\n\n"
            f"Os la dejamos {donde} y ha entrado ENTERA 👇\n\n{patas}\n\n"
            f"💶 10€ → {coma(10 * c['cuota'])}€\n\n"
            f"📌 La dejo fijada: la última gorda acertada 🔥\n🔔 Activad las notificaciones, que vienen más 👀")


def main(ahora=None):
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    if not (token and canal) or control.get("grandes_aciertos") is False:
        return 0
    from publicar_telegram import api
    from incidencias import publicaciones
    ahora = ahora or datetime.now(MADRID)
    hechos = leer(ESTADO, {}) or {}
    app = leer(RAIZ / "docs" / "datos.json", {}) or {}
    posts = {p["id"]: p for p in publicaciones(RAIZ)}
    n = 0
    for c in candidatas(app.get("publicados_hoy"), hechos)[:2]:
        p = posts.get(c["id"]) or {}
        t = texto(c, p)
        foto = p.get("foto") or p.get("foto_tg")
        try:
            if foto and (RAIZ / foto).exists():
                r = api(token, "sendPhoto", {"chat_id": canal, "caption": t}, archivo=RAIZ / foto)
            else:
                r = api(token, "sendMessage", {"chat_id": canal, "text": t})
            mid = r["result"]["message_id"]
        except Exception as e:
            print("grandes_aciertos: no enviado", c["id"], e)
            hechos[c["id"]] = {"error": str(e)[:200], "hora": ahora.strftime("%Y-%m-%dT%H:%M")}   # no repetir a ciegas
            continue
        fijado = True
        try:
            api(token, "pinChatMessage", {"chat_id": canal, "message_id": mid, "disable_notification": True})
        except Exception as e:
            fijado = False
            print("grandes_aciertos: no se pudo fijar", e)
        hechos[c["id"]] = {"mensaje_id": mid, "cuota": c["cuota"], "fijado": fijado, "hora": ahora.strftime("%Y-%m-%dT%H:%M")}
        print(f"grandes_aciertos: {c['id']} @{c['cuota']} publicado y {'fijado' if fijado else 'SIN fijar'}")
        n += 1
    ESTADO.write_text(json.dumps(hechos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return n


if __name__ == "__main__":
    main()
