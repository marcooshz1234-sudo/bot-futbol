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
NO = re.compile(r"verde|rojo|balance|resumen|escalera|pick-seguro$|ganadores|marcador|exactos|lista|boleto|directo")
CUOTA = re.compile(r"@\s*(\d+[.,]\d+)")
MAX_NOMBRE = 20
MAX_SEGUIDAS = 3   # 13/11 (Marcos: «me gusta más con foto, pero no siempre: que el canal no esté solo con fotos»)
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


_ESCUDOS = None


def escudo_club(nombre):
    """13/11 (Marcos: «sí» a poner el escudo de los clubes): ruta del escudo guardado (escudos.py) del equipo, buscando
    su nombre (en inglés o en español) en los partidos de hoy y los próximos."""
    global _ESCUDOS
    if _ESCUDOS is None:
        import json
        from pathlib import Path
        from combis_dia import nombre_es
        _ESCUDOS = {}
        pares = []
        try:
            for x in json.loads((RAIZ / "datos" / "fixtures_dia.json").read_text(encoding="utf-8")).get("partidos", []):
                pares += [(x.get("local"), x.get("logo_l")), (x.get("visitante"), x.get("logo_v"))]
        except Exception:
            pass
        for f in (RAIZ / "datos" / "proximos").glob("*.json"):
            try:
                t = (json.loads(f.read_text(encoding="utf-8")).get("partido") or {}).get("teams") or {}
                pares += [(t[k]["name"], t[k].get("logo")) for k in ("home", "away") if k in t]
            except Exception:
                continue
        for n, url in pares:
            if n and url:
                for clave in (n, nombre_es(n)):
                    _ESCUDOS.setdefault(clave.lower(), url)
    n = nombre.lower()
    url = _ESCUDOS.get(n) or _ESCUDOS.get(re.sub(r"^(el|la|los|las) ", "", n))
    if not url:
        return ""
    from pathlib import Path
    ruta = MEDIA / "escudos" / Path(url).name
    if not ruta.exists():   # en el bot de GitHub hay red: se descarga y se guarda (imagenes.escudo)
        try:
            from imagenes import escudo
            escudo(url, nombre)
        except Exception:
            pass
    return str(ruta) if ruta.exists() else ""


def fila(pata, partido=None, partido_ok=False):
    """('Gana Suiza (Eslovenia – Suiza)', cuota) → {'nombre': 'Suiza', 'pick': 'GANA', …}."""
    t = re.sub(r"\s*\([^)]*\)\s*", " ", pata).strip()
    reglas = ((r"^(.+?) gana alguna (?:de las dos )?partes?$", lambda m: "GANA UNA PARTE"),
              (r"^Gana (?:el |la |los |las )?(.+)$", lambda m: "GANA"),
              (r"^(.+?) gana$", lambda m: "GANA"),
              (r"^(.+?) marca (\d+) o más$", lambda m: f"{m.group(2)}+ GOLES"),
              (r"^(.+?) marca$", lambda m: "MARCA"),
              (r"^(.+?) (?:marca o asiste|anotará o asistirá)$", lambda m: "GOL O ASIST."),
              (r"^(.+?) no pierde$", lambda m: "NO PIERDE"),
              (r"^(.+?) más de (\d+[,.]5) remates(?: totales)?$", lambda m: f"+{m.group(2)} REMATES"),
              (r"^(.+?) más de (\d+[,.]5) córners$", lambda m: f"+{m.group(2)} CÓRNERS"),
              (r"^(.+?) no marca (\d+)$", lambda m: f"NO MARCA {m.group(2)}"),
              (r"^(.+?) (?:más de (\d+[,.]5) goles|marca 2 o más)$", lambda m: f"+{m.group(2) or '1,5'} GOLES"))
    if re.search(r"crear apuesta", pata, re.I) and not partido_ok:
        return None   # se trata en filas(): una fila por condición
    for patron, pick, n in ((r"^Más de (\d+(?:[,.]5)?) (goles|córners|tarjetas) en (.+)$",
                             lambda m: f"+{m.group(1)} {m.group(2).upper()}", 3),
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
                    "seleccion": bool(pais), "escudo": "" if pais else escudo_club(nombre)}
    c = CUOTA.search(pata)
    corto = t if len(t) <= 40 else t[:39].rstrip() + "…"   # 13/11 (Marcos): el pick tiene que verse en la foto
    return {"nombre": corto, "pick": f"@{c.group(1)}" if c else "✓", "pais": None, "bandera": "⚽", "seleccion": False,
            "escudo": ""}


def condiciones(pata):
    """«Serbia más de 6,5 remates y más de 1,5 goles en el partido (Crear apuesta)» → cada condición."""
    t = re.sub(r"\s*\((?:[^)]*Crear apuesta[^)]*)\)\s*", "", pata, flags=re.I).strip()
    partes = [x.strip(" .") for x in re.split(r",\s+|\s+y\s+(?=[a-záéíóú]*\s*(?:más|menos|gana|no |marca|[A-ZÁÉÍÓÚ]))", t) if x.strip()]
    sujeto = None
    out = []
    for x in partes:
        m = re.match(r"^([A-ZÁÉÍÓÚ][\wÁÉÍÓÚáéíóúñ]+(?: [A-ZÁÉÍÓÚ][\wáéíóúñ]+)?) ", x)
        if m and not re.match(r"^(Más|Menos|Ambos|Gana)\b", x):
            sujeto = m.group(1)
        elif re.match(r"^más de \d+[,.]5 goles", x, re.I):
            x = "Partido " + x[0].lower() + x[1:]
        elif sujeto and re.match(r"^(más|menos|gana|marca|no )", x, re.I):
            x = f"{sujeto} {x}"
        out.append(re.sub(r" en el partido$", "", x))
    return out


def filas(ps, partido=None):
    out = []
    for x in ps:
        if re.search(r"crear apuesta", x, re.I):
            out += [fila(c, partido_ok=True) for c in condiciones(x)]
        else:
            out.append(fila(x, partido))
    return out[:8]


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
    crear = any(re.search(r"crear apuesta", x, re.I) for x in patas(texto))
    nombre = ("CREAR APUESTA" if crear else "CUOTAZA" if "cuotaza" in pid else "COMBI DE LA NOCHE" if "noche" in pid
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


def racha_fotos(todos):
    """Cuántos de los últimos posts del canal salieron seguidos con foto."""
    hechos = sorted((p for p in todos or [] if p.get("enviado") and p.get("mensaje_id")), key=lambda p: p["enviado"])
    n = 0
    for p in reversed(hechos):
        if not (p.get("foto") or p.get("foto_tg")):
            break
        n += 1
    return n


def liga_de(p, texto):
    """Id de la competición (para su logo, Marcos 13/11: «acuérdate de poner el logo de la competición»).
    Por los partidos del post (sel) o por los nombres de los equipos del texto; si hay varias, ninguna."""
    import json
    from combis_dia import nombre_es
    ligas = set()
    fids = {s.split("|")[0] for s in p.get("sel") or []}
    nombres = re.findall(r"(?:⚽\s*|\()([^()·\n]+?)\s*[–-]\s*([^()·\n]+?)\s*(?:·|\))", texto)
    for f in (RAIZ / "datos" / "proximos").glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8")).get("partido") or {}
        except Exception:
            continue
        if not d.get("league"):
            continue
        if f.stem in fids:
            ligas.add(d["league"]["id"])
            continue
        h, a = d["teams"]["home"]["name"], d["teams"]["away"]["name"]
        for l, v in nombres:
            if {l.strip().lower(), v.strip().lower()} <= {h.lower(), a.lower(), nombre_es(h).lower(), nombre_es(a).lower()}:
                ligas.add(d["league"]["id"])
    return ligas.pop() if len(ligas) == 1 else None


def hacer(p, texto, todos=None):
    """Ruta (relativa a RAIZ) de la tarjeta de Telegram, o None si no toca o no se puede (sin Chromium: sale en texto).
    Tras MAX_SEGUIDAS posts con foto seguidos, el siguiente sale en texto (mezcla de fotos y texto)."""
    if not toca(p) or racha_fotos(todos) >= MAX_SEGUIDAS:
        return None
    ps = patas(texto)
    if not ps or len(ps) > 8:
        return None
    out = MEDIA / f"{p['id']}.tg.jpg"
    if not out.exists():
        try:
            import ganadores_img as G
            MEDIA.mkdir(parents=True, exist_ok=True)
            m = re.search(r"⚽\s*(.+?)\s*·", texto)
            crear = any(re.search(r"crear apuesta", x, re.I) for x in ps)
            lem = lema(texto)
            if crear and m:   # el partido abajo, con la hora
                lem = f"{m.group(1).upper()} · {lem}" if lem else m.group(1).upper()
            lid = liga_de(p, texto)
            G.generar(filas(ps, m.group(1) if m else None), titulo(p, texto), out, "estadio", lema=lem,
                      liga=G.logo_liga(lid) if lid else None)
        except Exception as e:
            print(f"Tarjeta de Telegram de {p['id']}: {e}")
            return None
    return str(out.relative_to(RAIZ))
