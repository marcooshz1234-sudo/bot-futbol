"""12/11 (Marcos: «asegúrate de que no van a haber fallos… jugadores que no jueguen, lesionados, equipos que no
jueguen, cualquier cosa» → «Todas» las mejoras).

Lo que antes revisaba Claude a mano, ahora lo mira el bot:
  - bajas_prensa: la API no da lesionados de selecciones (Mbappé, Van Dijk, Xhaka no salían). Se miran los titulares
    de noticias.py de los partidos con posts pendientes y se avisa de las bajas y dudas.
  - estrellas: si el que falta es de los máximos goleadores/asistentes de las 5 grandes o el titular dice capitán/
    estrella, y se sabe de qué equipo es, los picks A FAVOR de ese equipo se marcan. combis_dia no los mete en
    combis nuevas; en los posts ya hechos solo se avisa (Marcos: «nunca cambiar nada sin enseñárselo»).
  - cuotas_movidas: un pick cuya cuota de bet365 se ha movido un 15 % o más desde que se hizo el post (suele haber
    una noticia detrás).
  - informe: la revisión de la mañana (9:00, al privado de Marcos): choques, aplazados, bajas, cuotas y textos.
"""
import re
from datetime import datetime, timedelta

from bot import DATOS, MADRID, leer

MOVIMIENTO = 0.15
PALABRAS_ESTRELLA = r"\bcapitan\b|\bcaptain\b|\bestrella\b|\bstar\b|maximo goleador|top scorer|\bcrack\b"
CONTRA = r"(?:against|ante|contra|frente a|vs\.?|v\.?)\s+(?:el |la |los |the )?$"


def norm(s):
    from noticias import norm as n
    return n(s)


def estrellas():
    """{apellido normalizado: nombre} de los 15 máximos goleadores y asistentes de las 5 grandes."""
    out = {}
    for liga in ((leer(DATOS / "goleadores.json", {}) or {}).get("ligas") or {}).values():
        for clave in ("goles", "asistencias"):
            for j in liga.get(clave) or []:
                ap = norm(j.get("jugador", "")).replace(".", " ").split()
                if ap and len(ap[-1]) > 3:
                    out[ap[-1]] = j["jugador"]
    return out


def nombres_equipo(nombre):
    from noticias import corto
    from plantillas import es
    return {norm(x) for x in (nombre, corto(nombre), es(nombre)) if x and len(x) > 2}


def lado_de(titulo, partido):
    """'home'/'away' si el titular habla de UN equipo (no cuenta el rival en «ante Italia», «against Italy»)."""
    t = norm(titulo)
    lados = set()
    for lado in ("home", "away"):
        for n in nombres_equipo(partido["teams"][lado]["name"]):
            for m in re.finditer(rf"\b{re.escape(n)}\b", t):
                if not re.search(CONTRA, t[max(0, m.start() - 14):m.start()]):
                    lados.add(lado)
    return lados.pop() if len(lados) == 1 else None


def favorece(sel, lado):
    """¿El pick «fid|mercado|opción» va a favor de ese equipo (gana, no pierde, marca)?"""
    _, m, o = str(sel).split("|", 2)
    casa = "Home" if lado == "home" else "Away"
    return ((m in ("Match Winner", "To Win Either Half", "Win to Nil", "Win Both Halves") and o == casa)
            or (m == "Double Chance" and o in (f"{casa}/Draw", f"Draw/{casa}"))
            or (m == f"Total - {casa}" and o.startswith("Over"))
            or (m == "Team To Score" and o == casa))


def bajas_partido(fid):
    """[{titulo, fuente, link, tipo, lado, estrella}] de las bajas/dudas en prensa de ese partido."""
    pa = (leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("partido")
    if not pa:
        return []
    ests = estrellas()
    out = []
    for n in (leer(DATOS / "noticias.json", {}) or {}).get(str(fid), []):
        from noticias import tipos as clasificar
        tipos = set(clasificar(n["titulo"]))   # con las palabras de ahora (no las de cuando se guardó)
        if not ({"baja", "duda"} & tipos) or "vuelve" in tipos:
            continue
        t = norm(n["titulo"])
        jugador = next((nom for ap, nom in ests.items() if re.search(rf"\b{re.escape(ap)}\b", t)), None)
        # que hable de ESTE partido: nombra a uno de los dos equipos o a una estrella (si no, «Laporte, baja en
        # España» salía en Armenia–Chipre porque Google lo daba en la búsqueda de Chipre)
        equipos = nombres_equipo(pa["teams"]["home"]["name"]) | nombres_equipo(pa["teams"]["away"]["name"])
        if not jugador and not any(re.search(rf"\b{re.escape(e)}\b", t) for e in equipos):
            continue
        estrella = bool(jugador or re.search(PALABRAS_ESTRELLA, t))
        out.append({"titulo": n["titulo"], "fuente": n.get("fuente", ""), "link": n.get("link"),
                    "tipo": "baja" if "baja" in tipos else "duda", "lado": lado_de(n["titulo"], pa),
                    "estrella": estrella, "jugador": jugador})
    return out


def lados_sin_estrella(fid):
    """Lados ('home'/'away') del partido a los que les falta una estrella (baja, no duda) según la prensa."""
    return {b["lado"] for b in bajas_partido(fid) if b["estrella"] and b["tipo"] == "baja" and b["lado"]}


def cuota_actual(fid, mercado, opcion):
    cu = ((leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("cuotas") or {}).get(mercado) or []
    for o, c in cu:
        if o == opcion:
            try:
                return float(c)
            except (TypeError, ValueError):
                return None
    return None


def cuotas_movidas(p):
    """[(sel, antes, ahora, cambio)] de las patas del post cuya cuota se ha movido un 15 % o más."""
    out = []
    for s, antes in zip(p.get("sel") or [], p.get("cuotas") or []):
        if str(s).count("|") != 2:
            continue
        try:
            antes = float(antes)
        except (TypeError, ValueError):
            continue
        ya = cuota_actual(*str(s).split("|"))
        if antes > 1 and ya and abs(ya / antes - 1) >= MOVIMIENTO:
            out.append((s, antes, ya, ya / antes - 1))
    return out


def nombre_partido(fid):
    from plantillas import es
    pa = (leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("partido")
    if not pa:
        return str(fid)
    return f"{es(pa['teams']['home']['name'])}–{es(pa['teams']['away']['name'])}"


def informe(ahora=None):
    """Texto de la revisión de la mañana (lo manda vigilante.main a las 9:00)."""
    import vigilante as V
    from bot import partido_caido
    from plantillas import choca
    ahora = ahora or datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")
    control = leer(V.PUB / "control.json", {}) or {}
    borrados = set(leer(V.PUB / "borrados.json", []) or [])
    posts = [p for p in V.todos() if p["id"] not in borrados and p["id"].startswith(hoy) and not p.get("verde_de")
             and not any(k in p["id"] for k in ("verde", "rojo", "balance"))]
    pend = [p for p in posts if V.vivo(p, control) and not V.publicado(p)]
    lineas = [f"☀️ Revisión de la mañana · {hoy[8:]}/{hoy[5:7]}", f"{len(pend)} posts por salir hoy"]

    sels = {}
    for p in posts:
        if V.vivo(p, control) or V.publicado(p):
            for s in p.get("sel") or []:
                sels.setdefault(s, []).append(p["id"][11:])
    lista = sorted(s for s in sels if str(s).count("|") == 2)
    choques = [(s, o) for i, s in enumerate(lista) for o in lista[i + 1:] if choca(s, [o])
               and not (any("loca" in x for x in sels[s] + sels[o])
                        and "Double Chance" in (s.split("|")[1], o.split("|")[1]))]
    lineas.append("⚔️ Choques: ninguno" if not choques else "⚔️ Se contradicen:\n" + "\n".join(
        f"  • {nombre_partido(s.split('|')[0])}: {s.split('|', 2)[2]} ({', '.join(sels[s])}) ↔ "
        f"{o.split('|', 2)[2]} ({', '.join(sels[o])})" for s, o in choques))

    caidos = [(p, partido_caido(p)) for p in pend]
    caidos = [(p, m) for p, m in caidos if m]
    lineas.append("🛑 Partidos aplazados o bloqueados: ninguno" if not caidos else "🛑 Partidos caídos:\n" + "\n".join(
        f"  • {p['id'][11:]}: {m}" for p, m in caidos))

    fids = sorted({str(s).split("|")[0] for p in pend for s in p.get("sel") or [] if str(s).count("|") == 2})
    bajas = []
    for fid in fids:
        for b in bajas_partido(fid):
            afect = [p["id"][11:] for p in pend if any(favorece(s, b["lado"]) for s in p.get("sel") or []
                                                       if s.startswith(f"{fid}|"))] if b["lado"] else []
            bajas.append(f"  • {nombre_partido(fid)}: «{b['titulo'][:110]}» ({b['fuente']})"
                         + (" ⭐" if b["estrella"] else "") + (f" → a favor: {', '.join(afect)}" if afect else ""))
    lineas.append("📰 Bajas en prensa: ninguna" if not bajas else "📰 Bajas y dudas en prensa:\n" + "\n".join(bajas[:12]))

    mov = [(p, x) for p in pend for x in cuotas_movidas(p)]
    lineas.append("📉 Cuotas movidas: ninguna" if not mov else "📉 Cuotas que se han movido (≥15 %):\n" + "\n".join(
        f"  • {p['id'][11:]}: {nombre_partido(s.split('|')[0])} {s.split('|', 2)[2]} {a:.2f} → {b:.2f} ({c:+.0%})"
        for p, (s, a, b, c) in mov[:10]))

    textos = []
    for p in pend:
        tx = (control.get("textos") or {}).get(p["id"], p.get("texto") or "")
        if re.search(r"segur|asegur|sin riesgo", tx, re.I) or V.RESTOS.search(tx):
            textos.append(p["id"][11:])
    lineas.append("✍️ Textos: bien" if not textos else f"✍️ Textos para mirar: {', '.join(textos)}")
    if not (choques or caidos or bajas or mov or textos):
        lineas.append("\n✅ Todo en orden")
    else:
        lineas.append("\nSi quieres quitar alguno, dímelo (o ❌ Cancelar en el panel)")
    return "\n".join(lineas)
