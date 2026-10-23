"""
Picks de las publicaciones (también las hechas a mano) → partido + apuesta, para seguirlos en directo.

Lee el texto de cada post publicado, saca cada línea con cuota ("✅ Gana el Alavés · 1,61"),
entiende la apuesta (gana, ambos marcan, +N goles, córners, tarjetas, tiros, paradas de un
jugador...) y el partido (por el título "A 🆚 B", por "en A–B" o por el equipo nombrado),
y la corrige con los datos del partido (en directo o terminado).
"""

import re
import unicodedata

ALIAS = {"niza": "nice", "gladbach": "monchengladbach", "forest": "nottingham", "atleti": "atletico",
         "betis": "betis", "barca": "barcelona", "inter": "inter", "milan": "ac milan", "psg": "paris saint germain",
         "bayern": "bayern", "leverkusen": "leverkusen", "dortmund": "dortmund", "spurs": "tottenham",
         "man city": "manchester city", "city": "manchester city", "united": "manchester united",
         "brest": "brestois", "roma": "roma", "athletic": "athletic", "real sociedad": "real sociedad"}
EN_JUEGO = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}
FIN = {"FT", "AET", "PEN"}


def norm(t):
    t = (t or "").replace("–", " - ").replace("—", " - ")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9+.,/ ()\-:]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def lineas(texto):
    """Líneas de apuesta de un post: las que acaban en '· cuota'."""
    salida = []
    for l in texto.splitlines():
        m = re.search(r"·\s*~?(\d+[.,]\d+)\s*$", l.strip())
        if not m or re.search(r"(?i)cuota|→|€", l):
            continue
        cuerpo = l.strip()[:m.start()].strip()
        cuerpo = re.sub(r"^[^A-Za-zÁÉÍÓÚáéíóúÑñ]*", "", cuerpo)              # ✅1. 🔴 1️⃣ banderas...
        cuerpo = re.sub(r"^(\d+[.)]\s*)", "", cuerpo)
        salida.append({"texto": cuerpo, "cuota": float(m.group(1).replace(",", "."))})
    return salida


def equipos_titulo(texto):
    for l in texto.splitlines()[:3]:
        if "🆚" in l or " VS " in l.upper():
            a, b = re.split(r"🆚|\bVS\b", l, maxsplit=1, flags=re.I)[:2]
            return norm(a), norm(b)
    return None


def num(x):
    return float(x.replace(",", "."))


def entender(t):
    """Texto de la apuesta → (spec, contexto de partido o None)."""
    n = norm(t)
    ctx = None
    m = re.match(r"^([a-z0-9 .]+?) - ([a-z0-9 .]+?)\s*:\s*(.+)$", n)      # "Rayo–Elche: +1,5 goles"
    if m:
        ctx, n = (m.group(1).strip(), m.group(2).strip()), m.group(3)
    elif " - " in n:
        izq, _, der = n.rpartition(" - ")
        k = max(izq.rfind(" en "), izq.rfind(" del "), izq.rfind(" de "))
        if k >= 0:
            w = izq.find(" ", k + 1)
            ctx = (re.sub(r"^(el|la) ", "", izq[w + 1:].strip()), der.strip())
            n = izq[:k].strip()
    par = re.search(r"\(([^)]*)\)", n)       # "(portero Gladbach)" → equipo del jugador
    eq_par = re.sub(r"^(portero|lateral|delantero|extremo|central|mediocentro|del|de)\s+", "", par.group(1)).strip() if par else None
    n = re.sub(r"\s*\([^)]*\)", "", n)
    n = re.sub(r"^(el|la|los) ", "", n).strip()
    n = re.sub(r"^\+(\d)", r"mas de \1", n)
    n = re.sub(r"^marca (?:el |la )?(.+)$", r"\1 marca", n)
    n = {"sin empate": "no hay empate"}.get(n, n)
    P = [
        (r"^gol (?:en la )?(?:2a|segunda) parte$", lambda g: {"t": "gol_2t"}),
        (r"^(.+?) gana una parte$", lambda g: {"t": "gana_parte", "eq": g}),
        (r"^(?:gana )?(?:el )?(.+?) gana al descanso$|^gana (?:el )?(.+?) al descanso$", lambda g: {"t": "gana_ht", "eq": g}),
        (r"^gana (?:el |la )?(.+)$", lambda g: {"t": "gana", "eq": g}),
        (r"^(.+?) o empate$", lambda g: {"t": "doble", "eq": g}),
        (r"^no hay empate$", lambda g: {"t": "no_empate"}),
        (r"^ambos marcan$", lambda g: {"t": "ambos"}),
        (r"^gol en la (?:1a?|primera) parte$", lambda g: {"t": "gol_ht"}),
        (r"^mas de (\d+(?:[.,]\d+)?) goles$", lambda g: {"t": "goles_mas", "n": num(g)}),
        (r"^menos de (\d+(?:[.,]\d+)?) goles$", lambda g: {"t": "goles_menos", "n": num(g)}),
        (r"^mas de (\d+(?:[.,]\d+)?) corners?$", lambda g: {"t": "corners_mas", "n": num(g)}),
        (r"^mas de (\d+(?:[.,]\d+)?) tarjetas$", lambda g: {"t": "tarjetas_mas", "n": num(g)}),
        (r"^mas de (\d+(?:[.,]\d+)?) tiros$", lambda g: {"t": "tiros_mas", "n": num(g)}),
        (r"^(.+?) marca (\d+) o mas$", None),
        (r"^(.+?) marca$", lambda g: {"t": "eq_goles", "eq": g, "n": 1}),
        (r"^(.+?) (?:saca|tiene|hace) (\d+)\+ corners?$", None),
        (r"^(.+?) saca mas de (\d+(?:[.,]\d+)?) corners?$", None),
        (r"^(.+?) ve (\d+)\+ tarjetas?$", None),
        (r"^(.+?) ve mas de (\d+(?:[.,]\d+)?) tarjetas?$", None),
        (r"^(.+?) hace mas tiros$", lambda g: {"t": "mas_tiros", "eq": g}),
        (r"^(.+?)(?: \(.*?\))? (\d+)\+ (tiros?|remates? a puerta|tiros? a puerta|paradas)$", None),
    ]
    for pat, f in P:
        m = re.match(pat, n)
        if not m:
            continue
        g = [x for x in m.groups() if x is not None]
        if f:
            return f(g[0] if g else None), ctx
        if "marca (" in pat:
            return {"t": "eq_goles", "eq": g[0], "n": int(g[1])}, ctx
        if "corner" in pat:
            v = num(g[1]); return {"t": "eq_corners", "eq": g[0], "n": v if "+" in pat else int(v) + 1}, ctx
        if "tarjeta" in pat:
            v = num(g[1]); return {"t": "eq_tarjetas", "eq": g[0], "n": v if "+" in pat else int(v) + 1}, ctx
        campo = "paradas" if "parada" in g[2] else "a_puerta" if "puerta" in g[2] else "tiros"
        return {"t": "jugador", "jugador": g[0], "campo": campo, "n": int(g[1]), "eq": eq_par}, ctx
    return None, ctx


def casa(nombre_corto, nombre_equipo):
    a = ALIAS.get(nombre_corto, nombre_corto)
    e = norm(nombre_equipo)
    return bool(a) and (a in e or e in a or any(len(w) > 3 and w in e.split() for w in a.split()))


def buscar_partido(partidos, a=None, b=None, equipo=None):
    for p in partidos:
        if a and b and (casa(a, p["local"]) and casa(b, p["visitante"]) or casa(a, p["visitante"]) and casa(b, p["local"])):
            return p
    if equipo:
        for p in partidos:
            if casa(equipo, p["local"]) or casa(equipo, p["visitante"]):
                return p
    return None


def picks_de_post(post, partidos):
    """[{texto, cuota, spec, partido_id, partido}] de un post publicado. partidos: [{id, local, visitante}]"""
    tit = equipos_titulo(post["texto"])
    salida = []
    for l in lineas(post["texto"]):
        spec, ctx = entender(l["texto"])
        p = None
        if ctx:
            p = buscar_partido(partidos, *ctx)
        if not p and tit:
            p = buscar_partido(partidos, *tit)
        if not p and spec and spec.get("eq"):
            p = buscar_partido(partidos, equipo=spec["eq"])
        salida.append(dict(l, spec=spec, partido_id=p["id"] if p else None,
                           partido=f"{p['local']} – {p['visitante']}" if p else None))
    return salida


def lado(spec_eq, d):
    if casa(spec_eq, d["local"]["nombre"]):
        return "local"
    if casa(spec_eq, d["visitante"]["nombre"]):
        return "visitante"
    return None


def evaluar(spec, d):
    """→ 'verde' | 'rojo' | 'va_bien' | 'va_mal' | 'pendiente' | 'sin_datos'"""
    if not spec or not d:
        return "sin_datos"
    est = d.get("estado")
    if est not in EN_JUEGO and est not in FIN:
        return "pendiente"
    fin = est in FIN
    g = d.get("goles") or [0, 0]
    g = [x or 0 for x in g]
    ht = d.get("descanso") or [None, None]
    st = d.get("stats") or {}
    s = {k: st.get(str(d[k]["id"]), {}) or {} for k in ("local", "visitante")}
    t = spec["t"]

    def final(ok_ya, ok_ahora):
        """ok_ya: ya cumplido para siempre; ok_ahora: se cumple ahora mismo."""
        if ok_ya:
            return "verde"
        if fin:
            return "verde" if ok_ahora else "rojo"
        return "va_bien" if ok_ahora else "va_mal"

    def total(k):
        return sum((s[x].get(k) or 0) for x in s)

    if t in ("gana_parte",):
        pass
    if t in ("gana", "doble", "gana_ht", "gana_parte", "eq_goles", "eq_corners", "eq_tarjetas", "mas_tiros"):
        ld = lado(spec["eq"], d)
        if not ld:
            return "sin_datos"
        otro = "visitante" if ld == "local" else "local"
        i, j = (0, 1) if ld == "local" else (1, 0)
    if t == "gana":
        return final(False, g[i] > g[j])
    if t == "doble":
        return final(False, g[i] >= g[j])
    if t == "gana_ht":
        if est == "1H":
            return "va_bien" if g[i] > g[j] else "va_mal"
        if ht[0] is None:
            return "sin_datos"
        return "verde" if ht[i] > ht[j] else "rojo"
    if t == "gol_2t":
        if est in ("1H", "HT") or ht[0] is None:
            return "pendiente" if est in ("1H", "HT") else "sin_datos"
        return final(sum(g) > (ht[0] or 0) + (ht[1] or 0), False)
    if t == "gana_parte":
        if ht[0] is None:
            return "va_bien" if g[i] > g[j] else "va_mal"
        if ht[i] > ht[j]:
            return "verde"
        if est in ("1H", "HT"):
            return "va_mal"
        return final(False, g[i] - ht[i] > g[j] - ht[j])
    if t == "no_empate":
        return final(False, g[0] != g[1])
    if t == "ambos":
        return final(g[0] > 0 and g[1] > 0, False)
    if t == "gol_ht":
        if est == "1H":
            return "verde" if sum(g) > 0 else "va_mal"
        if ht[0] is None:
            return "sin_datos"
        return "verde" if (ht[0] or 0) + (ht[1] or 0) > 0 else "rojo"
    if t == "goles_mas":
        return final(sum(g) > spec["n"], False)
    if t == "goles_menos":
        return "rojo" if sum(g) > spec["n"] else final(False, True)
    if t == "corners_mas":
        return final(total("corners") > spec["n"], False)
    if t == "tarjetas_mas":
        return final(total("amarillas") + total("rojas") > spec["n"], False)
    if t == "tiros_mas":
        return final(total("tiros") > spec["n"], False)
    if t == "eq_goles":
        return final(g[i] >= spec["n"], False)
    if t == "eq_corners":
        return final((s[ld].get("corners") or 0) >= spec["n"], False)
    if t == "eq_tarjetas":
        return final((s[ld].get("amarillas") or 0) + (s[ld].get("rojas") or 0) >= spec["n"], False)
    if t == "mas_tiros":
        return final(False, (s[ld].get("tiros") or 0) > (s[otro].get("tiros") or 0))
    if t == "jugador":
        ap = norm(spec["jugador"]).split()[-1]
        for lista in (d.get("jugadores") or {}).values():
            for jg in lista:
                if ap and ap in norm(jg.get("nombre", "")).split()[-1:] + [norm(jg.get("nombre", ""))]:
                    return final((jg.get(spec["campo"]) or 0) >= spec["n"], False)
                if ap and norm(jg.get("nombre", "")).endswith(ap):
                    return final((jg.get(spec["campo"]) or 0) >= spec["n"], False)
        return "sin_datos" if not fin else "pendiente"
    return "sin_datos"
