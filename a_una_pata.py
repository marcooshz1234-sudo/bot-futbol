"""
30/10 (Marcos): aviso al bot del móvil cuando a una combi publicada solo le falta UNA pata y el partido de esa
pata está en juego. Ejemplo: «PSG x9,64 · 5 de 6 ✅ · falta: Le Havre marca (min 70, 0-2)».
Así puede preparar el «casi» o el verde al momento. Un aviso por combi (y otro si la pata que falta cambia).
Lo llama app_datos.py en cada vuelta con los posts de hoy ya corregidos. Estado en datos/a_una_pata.json.
"""
import json
import os
from datetime import datetime, timedelta

from bot import DATOS, MADRID, leer

ESTADO = DATOS / "a_una_pata.json"
EN_JUEGO = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE"}
MIN_PATAS = 3          # combis de 3 patas o más (una x2 de 2 patas no tiene gracia)


def candidatos(publicados_hoy):
    """[(post, pata que falta)] de las combis con todas las patas en verde menos una cuyo partido está en juego."""
    out = []
    for p in publicados_hoy:
        if p.get("lista") or p.get("estado") in ("verde", "rojo"):
            continue
        picks = [x for x in p.get("picks") or [] if not x.get("exacto")]
        if len(picks) < MIN_PATAS:
            continue
        faltan = [x for x in picks if x.get("estado") not in ("verde", "anulada")]
        if len(faltan) == 1 and faltan[0].get("estado_partido") in EN_JUEGO and faltan[0].get("estado") != "rojo":
            out.append((p, faltan[0]))
    return out


def texto_aviso(p, f, n):
    cuota = f" x{p['cuota']:.2f}".replace(".", ",") if p.get("cuota") else ""
    marcador = f.get("marcador") or [None, None]
    sitio = ", ".join(x for x in (f"min {f['minuto']}" if f.get("minuto") else ("descanso" if f.get("estado_partido") == "HT" else ""),
                                   f"{marcador[0]}-{marcador[1]}" if None not in marcador else "") if x)
    prog = (f.get("progreso") or {}).get("texto")
    titulo = f"Combi {f['partido']}" if "COMBI LOCAS" in p["titulo"].upper() and f.get("partido") else p["titulo"][:60]
    return (f"⏳ A UNA PATA · {titulo}{cuota}\n\n✅ {n - 1} de {n} ya en verde\n"
            f"🎯 Falta: {f['texto']}{f' ({sitio})' if sitio else ''}" + (f"\n📊 {prog}" if prog else ""))


def avisar(publicados_hoy, ahora=None):
    ahora = ahora or datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    nuevos = []
    for p, f in candidatos(publicados_hoy):
        clave = f"{p['id']}|{f['texto']}"
        if clave in est:
            continue
        n = len([x for x in p.get("picks") or [] if not x.get("exacto")])
        est[clave] = ahora.strftime("%Y-%m-%dT%H:%M")
        nuevos.append(texto_aviso(p, f, n))
    if not nuevos:
        return []
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not (token and canal):
        return nuevos   # sin claves (pruebas en local): no se manda ni se apunta nada
    if token and canal:
        try:
            from publicar_telegram import api
            admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
            duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
            for t in nuevos:
                api(token, "sendMessage", {"chat_id": duenio, "text": t})
        except Exception as e:
            print("a una pata:", str(e)[:150])
            return []   # no se apunta: se reintenta en la siguiente vuelta
    limite = (ahora - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    est = {k: v for k, v in est.items() if v > limite}
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return nuevos
