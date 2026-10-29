"""
Estadísticas para el widget del móvil/Mac · publicaciones/estadisticas.json

Se ejecuta en el bucle de Telegram cada ~10 min. Apunta seguidores de cada red,
lo ganado hoy, la tendencia de 7 días, likes de hoy, próximo post, cómo fue ayer
y la escalera. Si una red no da un dato (permisos), ese dato se queda en null.
"""

import json
import os
from datetime import datetime, timedelta

from publicar_telegram import AUTOS, COLA, ENVIADOS, MADRID, RAIZ, api
from redes import FACEBOOK, INSTAGRAM, THREADS, llamar, pagina_facebook

SALIDA = RAIZ / "publicaciones" / "estadisticas.json"


def leer(ruta, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def intentar(f):
    try:
        return f()
    except Exception as e:
        print("estadísticas:", str(e)[:150])
        return None


def titulo_corto(texto):
    """29/10 (widget): título legible del próximo post: «Combi Everton vs Newcastle», «Combi del jueves x2,40»."""
    import re
    lineas = [l for l in texto.strip().splitlines() if l.strip()]
    limpio = lambda s: re.sub(r"\s+", " ", "".join(c for c in s if c.isalnum() or c in " ·-–,.()/+%|")).strip(" |·-–")
    t = limpio(lineas[0])
    if "COMBI LOCAS" in t.upper() and len(lineas) > 1:   # combi de partido: el partido de la 2ª línea
        t = "Combi " + limpio(lineas[1]).title().replace(" Vs ", " vs ")
    else:
        t = re.sub(r"^COMBILOCAS\s*[-–|·]*\s*", "", t, flags=re.I)
        t = re.sub(r"\s*[·|-]\s*COMBILOCAS$", "", t, flags=re.I)
        t = t[:1].upper() + t[1:].lower()
    return t[:38]


def main():
    ahora = datetime.now(MADRID)
    hoy, ayer = ahora.strftime("%Y-%m-%d"), (ahora - timedelta(days=1)).strftime("%Y-%m-%d")
    ig, th, fb = (os.environ.get(k) for k in ("INSTAGRAM_TOKEN", "THREADS_TOKEN", "FACEBOOK_TOKEN"))
    tg, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    seg, likes, seg_tipos = {}, 0, None

    if ig:
        seg["instagram"] = intentar(lambda: llamar("GET", f"{INSTAGRAM}/me", {"fields": "followers_count",
                                                                                "access_token": ig})["followers_count"])
        medios = intentar(lambda: llamar("GET", f"{INSTAGRAM}/me/media",
                                         {"fields": "like_count,timestamp", "limit": 30, "access_token": ig})["data"]) or []
        tipos = {}
        for m in intentar(lambda: llamar("GET", f"{INSTAGRAM}/me/media", {"fields": "caption,like_count,comments_count,media_type",
                                                                          "limit": 60, "access_token": ig})["data"]) or []:
            t = (m.get("caption") or "").upper()
            tipo = ("Combi loca" if "LOCA" in t else "Combi segura" if "SEGURA" in t else "Cuota 3" if "CUOTA 3" in t
                    else "Escalera" if "ESCALERA" in t else "Picks" if "PICKS" in t else "Verdes/balance"
                    if ("VERDE" in t[:40] or "BALANCE" in t or "ASÍ FUE" in t) else "Combi de partido" if "🆚" in (m.get("caption") or "") else "Otros")
            if m.get("media_type") == "VIDEO":
                tipo += " (reel)"
            x = tipos.setdefault(tipo, [0, 0, 0])
            x[0] += 1; x[1] += m.get("like_count", 0); x[2] += m.get("comments_count", 0)
        seg_tipos = {k: {"posts": v[0], "likes_media": round(v[1] / v[0], 1), "comentarios_media": round(v[2] / v[0], 1)}
                     for k, v in tipos.items()}
        likes += sum(m.get("like_count", 0) for m in medios if m.get("timestamp", "")[:10] >= ayer
                     and datetime.fromisoformat(m["timestamp"].replace("+0000", "+00:00")).astimezone(MADRID)
                     .strftime("%Y-%m-%d") == hoy)
    if th:
        seg["threads"] = intentar(lambda: llamar("GET", f"{THREADS}/me/threads_insights",
                                                 {"metric": "followers_count", "access_token": th})
                                  ["data"][0]["total_value"]["value"])
    if fb:
        def facebook():
            pag, tok = pagina_facebook(fb, os.environ.get("FACEBOOK_PAGINA"))
            r = llamar("GET", f"{FACEBOOK}/{pag}", {"fields": "followers_count,fan_count", "access_token": tok})
            return r.get("followers_count") or r.get("fan_count")
        seg["facebook"] = intentar(facebook)
    if tg and canal:
        seg["telegram"] = intentar(lambda: api(tg, "getChatMemberCount", {"chat_id": canal})["result"])

    previo = leer(SALIDA, {})
    historial = previo.get("historial", {})          # {día: {red: seguidores}} (último valor del día)
    historial[hoy] = {r: v for r, v in seg.items() if v is not None} or historial.get(hoy, {})
    historial = {d: historial[d] for d in sorted(historial)[-400:]}
    base = historial.get(ayer, {})
    redes = {}
    for r, v in seg.items():
        serie = [historial[d].get(r) for d in sorted(historial)[-7:] if historial[d].get(r) is not None]
        redes[r] = {"seguidores": v, "hoy": (v - base[r]) if (v is not None and r in base) else None, "serie": serie}

    # próximo post (a mano o automático)
    enviados = leer(ENVIADOS, {})
    posts = leer(COLA, []) + [dict(p, **enviados.get(p["id"], {})) for r in AUTOS if r.exists() for p in leer(r, [])]
    futuros = sorted((p for p in posts if p["fecha"] > ahora.strftime("%Y-%m-%dT%H:%M")
                      and not p.get("caducada") and not p.get("borrar")), key=lambda p: p["fecha"])
    proximo = None
    if futuros:
        p = futuros[0]
        proximo = {"hora": p["fecha"][11:16], "dia": p["fecha"][:10], "titulo": titulo_corto(p["texto"])}

    # cómo fueron ayer los picks del bot
    reg = leer(RAIZ / "datos" / "registro_aciertos.json", {})
    de_ayer = [p for p in reg.values() if p.get("fecha", "")[:10] == ayer and p.get("acierto") is not None]
    balance = {"aciertos": sum(p["acierto"] for p in de_ayer), "total": len(de_ayer)} if de_ayer else None

    esc = (leer(RAIZ / "datos" / "escalera.json", {}) or {}).get("actual")
    escalera = None
    if esc:
        escalera = {"dia": esc["escalon"], "de": 7, "stake": esc["stake"],
                    "objetivo": round(esc["stake"] * esc["cuota"], 2), "fecha": esc["dia"]}

    datos = {"actualizado": ahora.strftime("%Y-%m-%d %H:%M"), "redes": redes,
             "total": sum(v for v in seg.values() if v) or None,
             "total_hoy": sum(x["hoy"] for x in redes.values() if x["hoy"] is not None),
             "likes_hoy": likes if ig else None, "proximo": proximo, "ayer": balance,
             "escalera": escalera, "historial": historial,
             "tipos_instagram": seg_tipos if ig else None}
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("Estadísticas:", {r: v["seguidores"] for r, v in redes.items()})


if __name__ == "__main__":
    main()
