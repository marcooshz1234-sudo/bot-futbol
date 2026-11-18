"""
18/11 (Marcos: «igual lo suyo es que tenga yo una app y desde la propia app lo pueda gestionar todo»).
Pestaña 📲 Telegram del panel (docs/panel/index.html): lo de hoy en el canal, lo que espera su OK, lo próximo,
los avisos del vigilante de Telegram y lo que no sale. Lo llama panel_datos.main() → datos.json["telegram"].

Aquí solo se lee. Los botones de la app («✅ Publicar», «❌ No sale», «Cancelar», «Recuperar») escriben ellos
mismos en publicaciones/control.json con el token de GitHub que Marcos guarda en su móvil (nunca pasa por aquí):
  ✅ Publicar  → control["aprobados"][id] = "AAAA-MM-DDTHH:MM" (igual que el «✅ Publicar» del bot)
  ❌ No sale / Cancelar → id a control["cancelados"];  Recuperar → se quita de ahí.
"""
from datetime import datetime, timedelta

MEDIA = "https://raw.githubusercontent.com/marcooshz1234-sudo/bot-futbol/main/publicaciones/media/"


def va_a_telegram(p):
    """El mismo filtro que publicar_telegram.py: lo que el bucle mandaría al canal."""
    if p.get("solo_redes") or p.get("borrar"):
        return False
    solo = p.get("solo_en")
    return not solo or "telegram" in solo


def _es(t):
    try:
        from nombres import espanol
        return espanol(t or "")
    except Exception:
        return t or ""


def tipo(pid):
    for k, n in (("verde", "Verde"), ("rojo", "Rojo"), ("balance", "Resumen de la noche"), ("escalera", "Escalera"),
                 ("pick-seguro", "Pick del día"), ("pick-tip", "Copia de canal"), ("pick-claude", "Pick de Claude"),
                 ("buenos", "Buenos días"), ("combi", "Combi"), ("personal", "Mi combinada"), ("info-top", "Información top"),
                 ("cuotaza", "Cuotaza")):
        if k in pid:
            return n
    return "Post"


def foto(p, raiz=None):
    """La foto con la que sale (o salió) en Telegram."""
    f = p.get("foto_tg") or p.get("foto")
    if f:
        return MEDIA + str(f).rsplit("/", 1)[-1]
    if raiz is not None:
        for ext in ("tg.jpg", "tarjeta.jpg"):
            if (raiz / "publicaciones" / "media" / f"{p['id']}.{ext}").exists():
                return MEDIA + f"{p['id']}.{ext}"
    return None


def titulo(texto):
    lineas = [x.strip() for x in (texto or "").splitlines() if x.strip()]
    for i, l in enumerate(lineas):   # escalera: la apuesta va justo encima de «📈 Cuota»
        if l.startswith("📈 Cuota") and i:
            return lineas[i - 1].lstrip("✅ ").strip()[:80]
    for l in (texto or "").splitlines():
        l = l.strip()
        if l.startswith(("🍀", "✅")):
            return l.lstrip("🍀✅ ").strip()[:80]
    l = [x.strip() for x in (texto or "").splitlines() if x.strip()]
    return (l[0] if l else "")[:80]


def partido(texto):
    for l in (texto or "").splitlines():
        if l.strip().startswith("⚽") and "–" in l:
            return l.strip().lstrip("⚽ ").split(" · ")[0].strip()
    return None


SIN_DIRECTO = {"Verde", "Rojo", "Resumen de la noche", "Buenos días"}


def directo(x):
    """Estado en directo de un post (de docs/datos.json → publicados_hoy) para la tarjeta."""
    if not x:
        return None
    picks = [{"texto": _es(y.get("texto")), "partido": _es(y.get("partido")), "estado": y.get("estado"),
              "marcador": y.get("marcador"), "minuto": y.get("minuto"), "fin": y.get("estado_partido") in ("FT", "AET", "PEN"),
              "progreso": _es((y.get("progreso") or {}).get("texto"))} for y in x.get("picks") or []]
    est = x.get("estado")
    if est not in ("verde", "rojo"):
        e = [y["estado"] for y in picks]
        est = ("va_mal" if "va_mal" in e or "rojo" in e else
               "va_bien" if any(s in ("va_bien", "en_juego", "verde") for s in e) else "pendiente")
    return {"estado": est, "picks": picks}


def avisos_tg(vigilante, posts, hoy):
    """Avisos del vigilante que son de Telegram (el mismo filtro que el privado): los abiertos ahora y los de hoy."""
    try:
        from privado import aviso_vigilante_tg
    except Exception:
        return []
    por_id = {p["id"]: p for p in posts}
    out, vistos = [], set()
    for a in vigilante.get("abiertos") or []:
        if aviso_vigilante_tg(a.get("clave", ""), por_id):
            out.append({"hora": "ahora", "t": a.get("t"), "abierto": True})
            vistos.add(a.get("t"))
    for h in vigilante.get("historial") or []:   # 18/11: el historial guarda la clave («k») desde hoy
        if (h.get("hora") or "").startswith(hoy) and h.get("k") and h.get("t") not in vistos \
                and aviso_vigilante_tg(h["k"], por_id):
            out.append({"hora": h["hora"][11:16], "t": h.get("t")})
    return out


def datos(posts, control, publicados_hoy, vigilante, ahora, raiz=None):
    hoy = ahora.strftime("%Y-%m-%d")
    ya = ahora.strftime("%Y-%m-%dT%H:%M")
    textos = control.get("textos") or {}
    cancelados = set(control.get("cancelados") or [])
    aprobados = control.get("aprobados") or {}
    cuota_dada = control.get("cuota_dada") or {}
    vivo = {x["id"]: x for x in publicados_hoy or []}

    def ficha(p, **kw):
        texto = _es(textos.get(p["id"], p.get("texto")))
        d = {"id": p["id"], "fecha": p["fecha"], "tipo": tipo(p["id"]), "titulo": _es(titulo(texto)),
             "partido": _es(partido(texto)), "texto": texto.strip(), "foto": foto(p, raiz)}
        d.update(kw)
        return d

    enviados, aprobar, proximo, no_salen = [], [], [], []
    for p in sorted(posts, key=lambda x: x.get("fecha") or ""):
        if not p.get("fecha") or not va_a_telegram(p):
            continue
        salido = p.get("enviado") or p.get("mensaje_id")
        if salido:
            cuando = str(p.get("enviado") or p["fecha"])
            if cuando.startswith(hoy) and cuando[:16] <= ya:
                d = directo(vivo.get(p["id"])) if tipo(p["id"]) not in SIN_DIRECTO else None
                f = ficha(p, hora=cuando[11:16], mid=p.get("mensaje_id"), directo=d)
                if not f["partido"] and d and d["picks"]:
                    f["partido"] = d["picks"][0]["partido"]
                enviados.append(f)
            continue
        fuera = p["id"] in cancelados or p.get("caducada")
        if p.get("requiere_ok") and not fuera and p["id"] not in aprobados:
            if p["fecha"] >= (ahora - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M"):
                falta = bool(p.get("pide_cuota")) and p["id"] not in cuota_dada
                aprobar.append(ficha(p, por=p.get("aviso") or "Espera tu OK.", falta_cuota=falta))
            continue
        if fuera:
            if p["fecha"].startswith(hoy):
                c = p.get("caducada")
                motivo = ("Cancelado" if p["id"] in cancelados or c == "cancelado" else
                          "Pasó la hora sin salir" if c is True else str(c))
                no_salen.append(ficha(p, motivo=motivo, cancelado=p["id"] in cancelados, se_puede=p["fecha"] > ya))
            continue
        if (ahora - timedelta(minutes=45)).strftime("%Y-%m-%dT%H:%M") <= p["fecha"] <= \
                (ahora + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M"):
            proximo.append(ficha(p, aprobado=aprobados.get(p["id"])))
    picks = [e for e in enviados if e.get("directo")]
    cuenta = {k: sum(1 for e in picks if e["directo"]["estado"] == k) for k in ("verde", "rojo", "va_bien", "va_mal", "pendiente")}
    return {"hoy": hoy, "enviados": enviados[::-1], "aprobar": aprobar, "proximo": proximo, "no_salen": no_salen,
            "avisos": avisos_tg(vigilante or {}, posts, hoy), "picks": len(picks), "cuenta": cuenta,
            "pausa": bool(control.get("pausa"))}


def main(posts=None, control=None, ahora=None):
    from bot import DATOS, MADRID, RAIZ, leer
    from incidencias import publicaciones
    ahora = ahora or datetime.now(MADRID)
    posts = posts if posts is not None else publicaciones(RAIZ)
    control = control if control is not None else (leer(RAIZ / "publicaciones" / "control.json", {}) or {})
    vivo = (leer(RAIZ / "docs" / "datos.json", {}) or {}).get("publicados_hoy") or []
    return datos(posts, control, vivo, leer(DATOS / "vigilante.json", {}) or {}, ahora, RAIZ)
