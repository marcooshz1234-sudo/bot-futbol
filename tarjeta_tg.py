"""13/11 (Marcos: «en Telegram sube un poco más de fotos, no tanto texto» → eligió «tarjeta con escudos» y dio el
visto bueno al ejemplo de la combi de la noche).

Los posts que salían en Telegram solo con texto (copias de tipsters, picks, cuotazas, combis de varios partidos) van
con una tarjeta nuestra (plantilla «estadio»: logo, título con la cuota, una fila por pata con bandera/escudo y la
apuesta corta, y la hora abajo) y un texto corto: la entrada, las patas y la cuota (la hora y el partido ya van en
la foto; el argumento largo se queda para Threads).

No toca: combis de un partido (su tarjeta de escudos), verdes, rojos, escalera y pick del día (imagen de marca),
balances y resúmenes.
"""
import re

from bot import RAIZ

MEDIA = RAIZ / "publicaciones" / "media"
CON_TARJETA = re.compile(r"-(pick-tip|combi-tip|pick-extra|cuotaza|combi-noche|combi-tarde|combi-dia|pick)(-|$)")
NO = re.compile(r"verde|rojo|balance|resumen|escalera|pick-seguro|ganadores|marcador|exactos|lista|boleto|directo")
CUOTA = re.compile(r"@\s*(\d+[.,]\d+)")
MAX_NOMBRE = 20
PATA = re.compile(r"\s*(🍀|[\U0001F1E6-\U0001F1FF]|🏴|\d+[.)] )")   # las patas empiezan por 🍀 o una bandera


def toca(p):
    pid = p.get("id", "")
    return bool(CON_TARJETA.search(pid)) and not NO.search(pid) and not p.get("tarjeta") and not p.get("verde_de")


def _pais(nombre):
    """Selección en español → país en inglés (para la bandera dibujada)."""
    import semana
    from combis_dia import nombre_es
    for k in semana.BANDERAS:
        if nombre.lower() in (k.lower(), nombre_es(k).lower()):
            return k
    return None


def fila(pata):
    """('Gana Suiza (Eslovenia – Suiza)', cuota) → {'nombre': 'Suiza', 'pick': 'GANA', …}."""
    t = re.sub(r"\s*\([^)]*\)\s*", " ", pata).strip()
    reglas = ((r"^Gana (?:el |la |los |las )?(.+)$", lambda m: "GANA"),
              (r"^(.+?) gana$", lambda m: "GANA"),
              (r"^(.+?) marca (\d+) o más$", lambda m: f"{m.group(2)}+ GOLES"),
              (r"^(.+?) marca$", lambda m: "MARCA"),
              (r"^(.+?) (?:marca o asiste|anotará o asistirá)$", lambda m: "GOL O ASIST."),
              (r"^(.+?) no pierde$", lambda m: "NO PIERDE"))
    if re.search(r"crear apuesta", pata, re.I):   # varias condiciones juntas: el detalle va en el texto
        c = CUOTA.search(pata)
        return {"nombre": "CREAR APUESTA", "pick": f"@{c.group(1)}" if c else "BET365", "pais": None, "bandera": "⚽",
                "seleccion": False, "escudo": ""}
    for patron, pick, n in ((r"^Más de (\d+[,.]5) goles en (.+)$", lambda m: f"+{m.group(1)} GOLES", 2),
                            (r"^Ambos marcan en (.+)$", lambda m: "AMBOS MARCAN", 1)):
        m = re.match(patron, t, re.I)
        if m:
            p = re.sub(r"\s*–\s*", " – ", re.sub(r" Sub-(\d\d)", r" S\1", m.group(n)))
            return {"nombre": p if len(p) <= 26 else p[:25].rstrip() + "…", "pick": pick(m), "pais": None,
                    "bandera": "⚽", "seleccion": False, "escudo": ""}
    for patron, pick in reglas:
        m = re.match(patron, t, re.I)
        if m and len(m.group(1)) <= MAX_NOMBRE:
            nombre = m.group(1).strip()
            pais = _pais(nombre)
            import semana
            return {"nombre": nombre, "pick": pick(m), "pais": pais, "bandera": semana.BANDERAS.get(pais, "⚽"),
                    "seleccion": bool(pais), "escudo": ""}
    c = CUOTA.search(pata)
    corto = t if len(t) <= 26 else t[:25].rstrip() + "…"
    return {"nombre": corto, "pick": f"@{c.group(1)}" if c else "✓", "pais": None, "bandera": "⚽", "seleccion": False,
            "escudo": ""}


def patas(texto):
    """Las líneas de pata (con @cuota) del texto, sin el emoji del principio ni la cuota."""
    out = []
    for l in texto.splitlines():
        if CUOTA.search(l) and PATA.match(l):
            limpio = re.sub(r"^[^\wÀ-ÿ¡¿]+", "", CUOTA.sub("", l)).strip(" ·-")
            if limpio:
                out.append(limpio)
    return out


def titulo(p, texto):
    pid = p["id"]
    m = re.search(r"Cuota\s*@?\s*(\d+[.,]\d+)", texto) or (CUOTA.search(texto) if len(patas(texto)) == 1 else None)
    cuota = f" · @{m.group(1).replace('.', ',')}" if m else ""
    nombre = ("CUOTAZA" if "cuotaza" in pid else "COMBI DE LA NOCHE" if "noche" in pid
              else "COMBINADA" if "combi" in pid else "PICK")
    return nombre + cuota


def lema(texto):
    m = re.search(r"(?:hoy|mañana|\d\d/\d\d)?\s*(\d{1,2}:\d\d)", texto)
    return f"HOY {m.group(1)}" if m and re.search(r"\bhoy\b|esta noche", texto, re.I) else (m.group(1) if m else None)


def texto_corto(texto):
    """Lo que va debajo de la foto: sin argumento ni partido/hora (ya están en la foto o sobran en Telegram)."""
    fuera = re.compile(r"^\s*(👨‍💻|⚽|⏰|🕘|🕗|🕙)")
    lineas = [l for l in texto.splitlines() if not fuera.match(l)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas)).strip()


def hacer(p, texto):
    """Ruta (relativa a RAIZ) de la tarjeta de Telegram, o None si no toca o no se puede (sin Chromium: sale en texto)."""
    if not toca(p):
        return None
    ps = patas(texto)
    if not ps or len(ps) > 8:
        return None
    out = MEDIA / f"{p['id']}.tg.jpg"
    if not out.exists():
        try:
            import ganadores_img as G
            MEDIA.mkdir(parents=True, exist_ok=True)
            G.generar([fila(x) for x in ps], titulo(p, texto), out, "estadio", lema=lema(texto))
        except Exception as e:
            print(f"Tarjeta de Telegram de {p['id']}: {e}")
            return None
    return str(out.relative_to(RAIZ))
