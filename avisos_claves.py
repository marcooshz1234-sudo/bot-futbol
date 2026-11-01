"""
01/11 (Marcos): aviso al móvil (bot del canal → chat con el dueño) antes de que caduque una clave.
Aquí solo van el NOMBRE de la clave y su fecha de caducidad, nunca el valor (las claves están en los Secrets de
GitHub y las pone Marcos). Avisa a falta de 14, 7, 3 y 1 días, una vez cada aviso. Lo llama recoger.yml (cada 6 h).
Cuando Marcos renueve una clave, se cambia aquí la fecha.
"""
import json
import os
from datetime import date, datetime

from bot import DATOS, MADRID, leer

CADUCAN = {
    "THREADS_TOKEN (Threads)": "2026-12-21",
    "INSTAGRAM_TOKEN (Instagram)": "2026-12-21",
}
AVISOS = (14, 7, 3, 1)
ESTADO = DATOS / "avisos_claves.json"


def pendientes(hoy=None):
    hoy = hoy or datetime.now(MADRID).date()
    hechos = set(leer(ESTADO, []) or [])
    out = []
    for clave, fecha in CADUCAN.items():
        faltan = (date.fromisoformat(fecha) - hoy).days
        for n in AVISOS:
            if faltan <= n and f"{clave}|{fecha}|{n}" not in hechos:
                out.append((clave, fecha, faltan, f"{clave}|{fecha}|{n}"))
                break
    return out


def main():
    lista = pendientes()
    if not lista:
        return
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    texto = "🔑 Claves a punto de caducar:\n" + "\n".join(
        f"• {c}: {'caducada' if f < 0 else 'hoy' if f == 0 else f'en {f} días'} ({d[8:]}/{d[5:7]})" for c, d, f, _ in lista) \
        + "\n\nRenuévala en Meta for Developers y ponla en GitHub → Settings → Secrets (eso lo haces tú). " \
          "Luego dime la fecha nueva y la cambio."
    print(texto)
    if not (token and canal):
        return
    from publicar_telegram import api
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    api(token, "sendMessage", {"chat_id": duenio, "text": texto})
    hechos = set(leer(ESTADO, []) or []) | {k for *_, k in lista}
    ESTADO.write_text(json.dumps(sorted(hechos), ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
