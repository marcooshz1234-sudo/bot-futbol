"""
Ayudante para crecer en Threads (plan del 26/10). Lo que la API no deja hacer solo (contestar con tu voz,
fijar posts, compartir en comunidades, responder a cuentas grandes) te lo deja preparado por Telegram
para que solo tengas que tocar el enlace. Solo lee de Threads: no publica, no responde, no borra.

  1. Comentarios nuevos en tus posts → aviso al momento con el enlace (contestar en la 1ª hora es lo que
     más empuja un post).
  2. 21:30 → el post del día con más vistas, para compartirlo en las comunidades Fútbol y Soccer Threads.
  3. Verde grande publicado (cuota ≥ 3) → enlace para fijarlo en el perfil.
  4. 2 h antes de un partido grande → 3 datos listos para responder en posts de cuentas grandes.
  5. Domingos 21:00 → informe semanal: vistas por post, seguidores, mejor formato y hora.

Estado en datos/threads_crecer.json. Se ejecuta en el bucle de Telegram cada ~10 min.
"""
import json
import os
import statistics as st
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer
from redes import THREADS, llamar

ESTADO = DATOS / "threads_crecer.json"
GRANDES = ("real madrid", "barcelona", "atletico madrid", "manchester city", "arsenal", "liverpool", "chelsea",
           "manchester united", "tottenham", "inter", "ac milan", "juventus", "napoli", "roma", "bayern",
           "borussia dortmund", "bayer leverkusen", "paris saint germain", "marseille", "benfica", "porto", "sporting cp", "ajax", "psv")


def dm(texto):
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    print(texto)
    if not (token and canal):
        return
    from publicar_telegram import api
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    api(token, "sendMessage", {"chat_id": duenio, "text": texto[:3900], "link_preview_options": {"is_disabled": True}})


def mis_posts(tok, desde):
    r = llamar("GET", f"{THREADS}/me/threads", {"fields": "id,text,timestamp,permalink", "limit": 50, "access_token": tok})
    return [p for p in r.get("data", []) if p.get("timestamp", "") >= desde]


def vistas(tok, pid):
    try:
        r = llamar("GET", f"{THREADS}/{pid}/insights", {"metric": "views,likes,replies", "access_token": tok})
        return {m["name"]: (m.get("values") or [{}])[0].get("value", 0) for m in r.get("data", [])}
    except Exception:
        return {}


def comentarios(tok, est):
    """Respuestas nuevas de otras cuentas a tus posts de las últimas 36 h."""
    desde = (datetime.utcnow() - timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M")
    vistos = set(est.get("comentarios", []))
    nuevos = []
    for p in mis_posts(tok, desde):
        try:
            r = llamar("GET", f"{THREADS}/{p['id']}/replies",
                       {"fields": "id,text,username,timestamp,permalink", "access_token": tok})
        except Exception as e:
            if "permission" in str(e).lower() and not est.get("aviso_permiso"):
                est["aviso_permiso"] = True
                dm("ℹ️ Para avisarte de los comentarios de Threads hace falta el permiso threads_read_replies "
                   "en la app de Meta (y regenerar el token). Cuando quieras lo hacemos.")
            return
        for c in r.get("data", []):
            if c["id"] in vistos or (c.get("username") or "").lower() == "combilocas":
                continue
            vistos.add(c["id"])
            nuevos.append((p, c))
    if nuevos and est.get("comentarios") is not None:   # la primera vez solo se apunta lo que ya había
        for p, c in nuevos[:8]:
            dm(f"💬 @{c.get('username')} ha comentado en «{(p.get('text') or '').splitlines()[0][:50]}»:\n\n"
               f"{(c.get('text') or '')[:300]}\n\nContesta ahora (la 1ª hora es la que más cuenta): "
               f"{c.get('permalink') or p.get('permalink')}")
    est["comentarios"] = sorted(vistos)[-500:]


def compartir(tok, est, ahora):
    hoy = ahora.strftime("%Y-%m-%d")
    if est.get("compartir") == hoy or ahora.strftime("%H:%M") < "21:30":
        return
    desde = (datetime.utcnow() - timedelta(hours=14)).strftime("%Y-%m-%dT%H:%M")
    posts = mis_posts(tok, desde)
    if not posts:
        return
    for p in posts:
        p["m"] = vistas(tok, p["id"])
    mejor = max(posts, key=lambda p: p["m"].get("views", 0))
    est["compartir"] = hoy
    vistas_f = DATOS / "threads_vistas.json"   # para que el bot sepa qué estilos se ven más (aprender.py)
    vis = leer(vistas_f, {}) or {}
    vis.update({p["id"]: p["m"].get("views", 0) for p in posts if p["m"]})
    vistas_f.write_text(json.dumps(dict(list(vis.items())[-1500:]), indent=0), encoding="utf-8")
    dm(f"📣 Tu mejor post de hoy en Threads ({mejor['m'].get('views', 0)} vistas):\n"
       f"«{(mejor.get('text') or '').splitlines()[0][:60]}»\n\n"
       f"Compártelo ahora en las comunidades Fútbol y Soccer Threads (botón de compartir → comunidad):\n"
       f"{mejor.get('permalink')}")


def fijar(tok, est):
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    hechos = set(est.get("fijar", []))
    for p in cola:
        tid = (p.get("redes") or {}).get("threads")
        if not (p.get("resultado") == "verde" and tid and tid not in ("ya-publicado",)) or p["id"] in hechos:
            continue
        hechos.add(p["id"])
        import re
        m = re.search(r"x(\d+),(\d+)", p["texto"].splitlines()[0]) or re.search(r"Cuota (\d+),(\d+)", p["texto"])
        cuota = float(f"{m.group(1)}.{m.group(2)}") if m else 0
        if cuota < 3:
            continue
        try:
            enlace = llamar("GET", f"{THREADS}/{tid}", {"fields": "permalink", "access_token": tok}).get("permalink")
        except Exception:
            enlace = None
        dm(f"📌 Verde x{m.group(1)},{m.group(2)} publicado. Fíjalo en tu perfil (⋯ → Fijar en el perfil) "
           f"para que lo vea todo el que entre:\n{enlace or 'en tu perfil de Threads'}")
    est["fijar"] = sorted(hechos)[-200:]


def partidos_grandes(est, ahora):
    picks = leer(DATOS / "picks.json", {}) or {}
    hechos = set(est.get("grandes", []))
    for d in (picks.get("dias") or {}).values():
        por_partido = {}
        for p in d.get("picks", []):
            por_partido.setdefault(p["partido_id"], []).append(p)
        for pid, lista in por_partido.items():
            x = lista[0]
            if str(pid) in hechos:
                continue
            if sum(any(g in eq.lower() for g in GRANDES) for eq in (x["local"], x["visitante"])) < 1:
                continue
            inicio = datetime.fromisoformat(x["fecha"]).replace(tzinfo=MADRID)
            if not timedelta(0) < inicio - ahora <= timedelta(hours=2):
                continue
            hechos.add(str(pid))
            top = sorted(lista, key=lambda p: -(p.get("prob_aprendida") or p["frecuencia"]))[:3]
            datos = "\n".join(f"• {p['texto']}: {p.get('detalle', '')}".rstrip(": ") for p in top)
            dm(f"⚽ {x['local']}–{x['visitante']} a las {inicio:%H:%M}. Datos para responder en los posts de cuentas "
               f"grandes de fútbol que hablen del partido (busca el partido en Threads y responde en los que "
               f"tengan muchas respuestas):\n\n{datos}\n\nUn dato concreto y corto funciona mejor que una opinión.")
    est["grandes"] = sorted(hechos)[-300:]


def semanal(tok, est, ahora):
    clave = ahora.strftime("%G-%V")
    if ahora.weekday() != 6 or ahora.strftime("%H:%M") < "21:00" or est.get("semanal") == clave:
        return
    est["semanal"] = clave
    r = llamar("GET", f"{THREADS}/me/threads", {"fields": "id,text,timestamp", "limit": 100, "access_token": tok})
    hace7 = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    esta = [p for p in r.get("data", []) if p["timestamp"] >= hace7]
    for p in esta:
        p["m"] = vistas(tok, p["id"])
    prev = est.get("semana_anterior") or {}
    v = [p["m"].get("views", 0) for p in esta]
    try:
        seg = llamar("GET", f"{THREADS}/me/threads_insights", {"metric": "followers_count", "access_token": tok}
                     )["data"][0]["total_value"]["value"]
    except Exception:
        seg = None
    mediana = int(st.median(v)) if v else 0
    mejor = max(esta, key=lambda p: p["m"].get("views", 0)) if esta else None
    horas = {}
    for p in esta:
        h = datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(MADRID).hour // 3 * 3
        horas.setdefault(h, []).append(p["m"].get("views", 0))
    mejor_hora = max(horas, key=lambda h: st.median(horas[h])) if horas else None
    lineas = [f"📈 TU SEMANA EN THREADS",
              f"Posts: {len(esta)} · vistas por post (mediana): {mediana}"
              + (f" (antes {prev.get('mediana')})" if prev.get("mediana") is not None else ""),
              f"Seguidores: {seg}" + (f" ({seg - prev['seguidores']:+d} en la semana)" if seg and prev.get("seguidores") else ""),
              f"Respuestas recibidas: {sum(p['m'].get('replies', 0) for p in esta)}"]
    if mejor:
        lineas.append(f"Mejor post: «{(mejor.get('text') or '').splitlines()[0][:60]}» ({mejor['m'].get('views', 0)} vistas)")
    if mejor_hora is not None:
        lineas.append(f"Mejor franja: {mejor_hora}:00–{mejor_hora + 3}:00")
    dm("\n".join(lineas))
    est["semana_anterior"] = {"mediana": mediana, "seguidores": seg}


def main():
    tok = os.environ.get("THREADS_TOKEN")
    if not tok:
        return
    ahora = datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    for paso in (lambda: comentarios(tok, est), lambda: compartir(tok, est, ahora), lambda: fijar(tok, est),
                 lambda: partidos_grandes(est, ahora), lambda: semanal(tok, est, ahora)):
        try:
            paso()
        except Exception as e:
            print("threads_crecer:", str(e)[:200])
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
