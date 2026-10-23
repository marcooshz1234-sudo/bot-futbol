"""
Avisos al móvil por Telegram (privado, solo al dueño del canal):
  - combi en verde (segura, cuota 3, loca) y resultado de la escalera
  - escalera publicada (arranca el día)
  - fallos del bot al publicar (Telegram o redes)
Lo ya avisado se guarda en datos/avisos.json. Se ejecuta en el bucle cada ~10 min.
"""
import json
import os
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer
from publicar_telegram import api

ESTADO = DATOS / "avisos.json"
NOMBRE = {"segura": "COMBI SEGURA", "cuota_3": "COMBI CUOTA 3", "loca": "COMBI LOCA"}


def main():
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not (token and canal):
        return
    ahora = datetime.now(MADRID)
    hecho = set(leer(ESTADO, []) or [])
    avisos = []
    reg = leer(DATOS / "registro_aciertos.json", {}) or {}
    clave = lambda p: f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"
    desde = (ahora - timedelta(days=2)).strftime("%Y-%m-%d")

    for dia, d in ((leer(DATOS / "picks.json", {}) or {}).get("dias") or {}).items():
        if dia < desde:
            continue
        for k, c in (d.get("combis") or {}).items():
            if not c or f"combi-{dia}-{k}" in hecho:
                continue
            r = [reg.get(clave(p), {}).get("acierto") for p in c["picks"]]
            if r and all(x is True for x in r):
                avisos.append((f"combi-{dia}-{k}", f"✅💚 VERDE la {NOMBRE.get(k, k)} del {dia[8:]}/{dia[5:7]} · cuota {c['cuota']:.2f}\n"
                               + "\n".join(f"✅ {p['texto']}" for p in c["picks"])))
            elif any(x is False for x in r):
                hecho.add(f"combi-{dia}-{k}")   # roja: no se avisa

    esc = leer(DATOS / "escalera.json", {}) or {}
    for h in (esc.get("historial") or [])[-3:]:
        k = f"escalera-{h['dia']}"
        if h.get("resultado") and k not in hecho and h["dia"] >= desde:
            avisos.append((k, f"🪜 Escalera día {h['escalon']}: " + ("✅ VERDE, mañana se sube de escalón 🚀" if h["resultado"] == "verde"
                                                                    else "❌ roja, mañana se vuelve al día 1")))
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    hoy = ahora.strftime("%Y-%m-%d")
    if (enviados.get(f"{hoy}-escalera") or {}).get("enviado") and f"escalera-sale-{hoy}" not in hecho:
        a = esc.get("actual") or {}
        avisos.append((f"escalera-sale-{hoy}", f"🪜 Ya ha salido la escalera de hoy · día {a.get('escalon', '?')}/7 · "
                                               f"{a.get('stake', 0):.0f}€ x{a.get('cuota', 0):.2f}"))

    est_redes = leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {}
    for p in (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + [
            dict(x, **enviados.get(x["id"], {}), **est_redes.get(x["id"], {})) for x in leer(RAIZ / "publicaciones" / "auto.json", []) or []]:
        if p["fecha"][:10] < desde:
            continue
        fallos = dict(p.get("errores_redes") or {})
        if p.get("error"):
            fallos["telegram"] = p["error"]
        if p.get("caducada") is True:
            fallos["telegram"] = "no salió a su hora"
        for red, e in fallos.items():
            k = f"fallo-{p['id']}-{red}"
            if k not in hecho:
                avisos.append((k, f"⚠️ Fallo publicando en {red}:\n{p['texto'].splitlines()[0][:50]}\n{str(e)[:200]}"))

    if not ESTADO.exists():   # primera vez: no se avisa de lo viejo
        hecho |= {k for k, _ in avisos}
        avisos = []
    if not avisos:
        ESTADO.write_text(json.dumps(sorted(hecho)[-1000:]), encoding="utf-8")
        return
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    for k, texto in avisos[:8]:
        try:
            api(token, "sendMessage", {"chat_id": duenio, "text": texto})
            hecho.add(k)
        except Exception as e:
            print("aviso no enviado:", e)
    ESTADO.write_text(json.dumps(sorted(hecho)[-1000:]), encoding="utf-8")
    print(f"Avisos enviados: {len(avisos[:8])}")


if __name__ == "__main__":
    main()
