"""
Picks de las publicaciones (también las hechas a mano) → partido + apuesta, para seguirlos en directo.

Lee el texto de cada post publicado, saca cada línea con cuota ("✅ Gana el Alavés · 1,61"),
entiende la apuesta (gana, ambos marcan, +N goles, córners, tarjetas, tiros, paradas de un
jugador...) y el partido (por el título "A 🆚 B", por "en A–B" o por el equipo nombrado),
y la corrige con los datos del partido (en directo o terminado).
"""

import re
import unicodedata
from datetime import datetime, timedelta
from picks import mismo_jugador

ALIAS = {"niza": "nice", "gladbach": "monchengladbach", "forest": "nottingham", "atleti": "atletico",
         "betis": "betis", "barca": "barcelona", "inter": "inter", "milan": "ac milan", "psg": "paris saint germain",
         "bayern": "bayern", "leverkusen": "leverkusen", "dortmund": "dortmund", "spurs": "tottenham",
         "man city": "manchester city", "city": "manchester city", "united": "manchester united",
         "brest": "brestois", "roma": "roma", "athletic": "athletic", "real sociedad": "real sociedad"}
EN_JUEGO = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT"}
FIN = {"FT", "AET", "PEN"}


def norm(t):
    t = (t or "").replace("–", " - ").replace("—", " - ").replace("→", ":")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9+.,/ ()\-:]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def lineas(texto):
    """Selecciones con cuota individual o marcadas con ✅, bandera o número."""
    salida = []
    for l in texto.splitlines():
        m = re.search(r"·\s*~?(\d+[.,]\d+)\s*$", l.strip())
        if re.search(r"(?i)cuota|€|🆚|\bVS\b", l):
            continue
        if not m and not re.match(r"^\s*(?:✅|\d[.)]|\d️⃣|[🇦-🇿])", l):
            continue
        cuerpo = l.strip()[:m.start()].strip() if m else l.strip()
        cuerpo = re.sub(r"^[^A-Za-zÁÉÍÓÚáéíóúÑñ]*", "", cuerpo)              # ✅1. 🔴 1️⃣ banderas...
        cuerpo = re.sub(r"^(\d+[.)]\s*)", "", cuerpo)
        salida.append({"texto": cuerpo, "cuota": float(m.group(1).replace(",", ".")) if m else None})
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
    n = n.removesuffix(" en el partido").replace("gana alguna de las dos partes", "gana una parte")
    n = {"sin empate": "no hay empate"}.get(n, n)
    m = re.match(r"^mas de (\d+(?:[.,]\d+)?) (goles|corners) en la (1a|primera|2a|segunda) parte$", n)
    if m:
        return {"t": "goles_parte" if m[2] == "goles" else "corners_parte",
                "n": num(m[1]), "parte": 1 if m[3] in ("1a", "primera") else 2}, ctx
    m = re.match(r"^(.+?) (?:saca|ve) (\d+) o mas (corners|tarjetas)$", n)
    if m:
        return {"t": "eq_corners" if m[3] == "corners" else "eq_tarjetas", "eq": m[1], "n": int(m[2])}, ctx
    m = re.match(r"^mas de (\d+(?:[.,]\d+)?) (tiros a puerta|fueras de juego)$", n)
    if m:
        return {"t": "estadistica_mas", "campo": "a_puerta" if m[2] == "tiros a puerta" else "fueras_juego", "n": num(m[1])}, ctx
    m = re.match(r"^ambos marcan y mas de (\d+(?:[.,]\d+)?) goles$", n)
    if m:
        return {"t": "ambos_goles", "n": num(m[1])}, ctx
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
        (r"^(.+?)(?: hace)? (\d+)\+ (remates? a puerta|tiros? a puerta|tiros?|remates?|paradas)$", None),
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
        return {"t": "jugador", "jugador": g[0].rstrip(": "), "campo": campo, "n": int(g[1]), "eq": eq_par}, ctx
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
    if post.get("fecha"):
        dia = datetime.fromisoformat(post["fecha"][:10])
        if "para manana" in norm(post["texto"].splitlines()[0]):
            dia += timedelta(days=1)
        partidos = [p for p in partidos if not p.get("fecha") or p["fecha"][:10] == dia.strftime("%Y-%m-%d")]
    salida = []
    for i, l in enumerate(lineas(post["texto"])):
        spec, ctx = entender(l["texto"])
        p = None
        claves = post.get("sel") or []
        if i < len(claves):
            fid = str(claves[i]).split("|", 1)[0]
            p = next((x for x in partidos if str(x["id"]) == fid), None)
        if not p and ctx:
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
        valores = [s[x].get(k) for x in s]
        return sum(valores) if all(v is not None for v in valores) else None

    campos = {"corners_mas": ("corners",), "tarjetas_mas": ("amarillas",), "tiros_mas": ("tiros",),
              "eq_corners": ("corners",), "eq_tarjetas": ("amarillas",), "mas_tiros": ("tiros",)}
    if t in campos and any(total(k) is None for k in campos[t]):
        return "sin_datos"

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
    if t == "ambos_goles":
        return final(min(g) > 0 and sum(g) > spec["n"], False)
    if t == "goles_parte":
        if est == "1H":
            return final(sum(g) > spec["n"], False) if spec["parte"] == 1 else "pendiente"
        if ht[0] is None or ht[1] is None:
            return "sin_datos"
        valor = sum(ht) if spec["parte"] == 1 else sum(g) - sum(ht)
        if spec["parte"] == 1 and est != "1H":
            return "verde" if valor > spec["n"] else "rojo"
        return final(valor > spec["n"], False)
    if t == "corners_parte":
        valores = [(d.get("corners_partes", {}).get(str(d[ld]["id"])) or {}).get(f"statistics_{spec['parte']}h")
                   for ld in ("local", "visitante")]
        if any(v is None for v in valores):
            return "sin_datos"
        valor = sum(valores)
        if spec["parte"] == 1 and est != "1H":
            return "verde" if valor > spec["n"] else "rojo"
        return final(valor > spec["n"], False)
    if t == "estadistica_mas":
        valor = total(spec["campo"])
        return "sin_datos" if valor is None else final(valor > spec["n"], False)
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
        return final(total("amarillas") + (total("rojas") or 0) > spec["n"], False)
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
        nombre = norm(spec["jugador"])
        candidatos = [j for lista in (d.get("jugadores") or {}).values() for j in lista
                      if mismo_jugador(nombre, j.get("nombre")) or
                      (len(nombre.split()) == 1 and norm(j.get("nombre")).split()[-1:] == [nombre])]
        if len(candidatos) != 1:
            return "sin_datos"
        if fin and candidatos[0].get("min") == 0:
            return "no_jugo"
        if not candidatos[0].get("min"):
            return "sin_datos"
        valor = candidatos[0].get(spec["campo"])
        return "sin_datos" if valor is None else final(valor >= spec["n"], False)
    return "sin_datos"


def progreso(spec, d):
    """Cuenta observada y objetivo de mercados reconocidos; nunca inventa ceros."""
    if not spec or not d or d.get('estado') not in FIN | EN_JUEGO:
        return None
    t = spec['t']
    stats = d.get('stats') or {}
    equipos = [d['local']['id'], d['visitante']['id']]

    def suma(campo, ids=equipos):
        valores = [(stats.get(str(eq)) or {}).get(campo) for eq in ids]
        return sum(valores) if all(x is not None for x in valores) else None

    valor, objetivo, unidad = None, None, None
    if t == 'jugador':
        nombre = norm(spec['jugador'])
        candidatos = [j for lista in (d.get('jugadores') or {}).values() for j in lista
                      if mismo_jugador(nombre, j.get('nombre')) or
                      (len(nombre.split()) == 1 and norm(j.get('nombre')).split()[-1:] == [nombre])]
        if len(candidatos) != 1 or not candidatos[0].get('min'):
            return None
        valor, objetivo = candidatos[0].get(spec['campo']), spec['n']
        unidad = {'paradas': 'paradas', 'tiros': 'tiros', 'a_puerta': 'tiros a puerta'}.get(spec['campo'], spec['campo'])
    elif t in ('goles_mas', 'corners_mas', 'tarjetas_mas', 'tiros_mas', 'estadistica_mas'):
        campo = {'corners_mas': 'corners', 'tiros_mas': 'tiros', 'estadistica_mas': spec.get('campo')}.get(t)
        if t == 'goles_mas':
            g = d.get('goles') or []
            valor = sum(g) if len(g) == 2 and None not in g else None
        elif t == 'tarjetas_mas':
            a, r = suma('amarillas'), suma('rojas')
            valor = a + r if a is not None and r is not None else None
        else:
            valor = suma(campo)
        objetivo = int(spec['n']) + 1
        unidad = {'goles_mas': 'goles', 'corners_mas': 'córners', 'tarjetas_mas': 'tarjetas', 'tiros_mas': 'tiros'}.get(t,
                  {'a_puerta': 'tiros a puerta', 'fueras_juego': 'fueras de juego'}.get(campo, campo))
    elif t in ('eq_goles', 'eq_corners', 'eq_tarjetas'):
        ld = lado(spec.get('eq'), d)
        if not ld:
            return None
        if t == 'eq_goles':
            valor = (d.get('goles') or [None, None])[0 if ld == 'local' else 1]
        elif t == 'eq_corners':
            valor = suma('corners', [d[ld]['id']])
        else:
            a, r = suma('amarillas', [d[ld]['id']]), suma('rojas', [d[ld]['id']])
            valor = a + r if a is not None and r is not None else None
        objetivo, unidad = spec['n'], {'eq_goles': 'goles', 'eq_corners': 'córners', 'eq_tarjetas': 'tarjetas'}[t]
    elif t in ('gol_ht', 'gol_2t', 'goles_parte', 'corners_parte'):
        parte = spec.get('parte', 1 if t == 'gol_ht' else 2)
        objetivo = int(spec.get('n', 0)) + 1
        if parte == 2 and d.get('estado') in ('1H', 'HT'):
            return None
        if t == 'corners_parte':
            valores = [(d.get('corners_partes', {}).get(str(eq)) or {}).get(f'statistics_{parte}h') for eq in equipos]
            valor = sum(valores) if all(x is not None for x in valores) else None
            unidad = 'córners de la parte'
        else:
            g, ht = d.get('goles') or [], d.get('descanso') or []
            if parte == 1 and d.get('estado') == '1H':
                valor = sum(g) if len(g) == 2 and None not in g else None
            elif len(ht) == 2 and None not in ht:
                valor = sum(ht) if parte == 1 else sum(g) - sum(ht) if len(g) == 2 and None not in g else None
            unidad = 'goles de la parte'
    elif t in ('ambos', 'ambos_goles'):
        g = d.get('goles') or []
        if len(g) == 2 and None not in g:
            valor, objetivo, unidad = sum(x > 0 for x in g), 2, 'equipos que marcan'
            if t == 'ambos_goles':
                goles = int(spec['n']) + 1
                return {'texto': f'{valor} de 2 equipos marcan · {sum(g)} de {goles} goles',
                        'porcentaje': min(100, round(100 * min(valor / 2, sum(g) / goles)))}
    if valor is None or objetivo is None:
        if t in ('gana', 'doble', 'gana_ht', 'gana_parte', 'no_empate'):
            g = d.get('goles') or []
            if len(g) == 2 and None not in g:
                return {'texto': f'Marcador: {g[0]}–{g[1]}', 'sin_barra': True}
        return None
    return {'actual': valor, 'objetivo': objetivo, 'unidad': unidad,
            'texto': f'{valor:g} de {objetivo:g} {unidad}',
            'porcentaje': min(100, round(100 * valor / objetivo)) if objetivo else 0}
