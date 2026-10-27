"""
Lee las patas de una captura de boleto de bet365 (27/10, Marcos) para seguirlas en la app.
No se publican: solo sirven para que la app sepa cómo va el boleto y avise del verde.

Cada pata del boleto son dos líneas: la principal («Monza - Más de 0 goles») y debajo el mercado
(«Equipo local - Total de goles - 3 opciones»). Después de las patas de un partido vienen los dos
equipos con la fecha y la hora. Con eso se arma la selección del bot: «partido|mercado|opción».
"""
import difflib
import re
import subprocess
import tempfile
import unicodedata
from datetime import datetime

from bot import DATOS, EXTRA, MADRID, leer

ALIAS = {"napoles": "napoli", "bolonia": "bologna", "inter de milan": "inter", "milan": "ac milan",
         "atletico de madrid": "atletico madrid", "bayern munich": "bayern munchen", "colonia": "1. fc koln",
         "turin": "torino", "florencia": "fiorentina", "genova": "genoa", "roma": "as roma", "lazio": "lazio",
         "venecia": "venezia", "manchester city": "manchester city", "man city": "manchester city",
         "wolves": "wolverhampton wanderers", "sporting de portugal": "sporting cp", "oporto": "fc porto"}
MES = r"(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"


def plano(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()
    s = re.sub(r"[^a-z0-9. ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIAS.get(s, s)


def leer_texto(im):
    """OCR de la captura (texto blanco sobre fondo oscuro → se invierte y se agranda)."""
    from PIL import ImageOps
    w, h = im.size
    zona = ImageOps.invert(im.convert("L")).resize((w * 2, h * 2))
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        zona.save(f.name)
        for lang in ("eng",):   # probado con «eng»: las tildes que pierde dan igual (se compara sin tildes)
            r = subprocess.run(["tesseract", f.name, "-", "--psm", "4", "-l", lang], capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout
    return ""


def partidos_conocidos():
    """[(id, local, visitante, fecha)] de los próximos partidos guardados."""
    res = []
    for f in EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if pa:
            res.append((pa["fixture"]["id"], pa["teams"]["home"]["name"], pa["teams"]["away"]["name"], pa["fixture"]["date"]))
    for x in (leer(DATOS / "fixtures_dia.json", {}) or {}).get("partidos", []):
        res.append((x["id"], x["local"], x["visitante"], x["fecha"]))
    return res


def limpiar(t):
    """Quita lo que el OCR mete de más: el escudo de delante, «SUSTITUTO+», la cuota del final…"""
    t = re.sub(r"\s*[|_]*\s*(SUSTITUTO\+?|SUSTIT\S*|sustituto\+?)\s*[|_]*\s*", " ", t, flags=re.I)
    t = re.sub(r"^[^A-Za-zÀ-ÿ0-9]+", "", t)
    t = re.sub(r"\s+\d+[.,]\d{2}\s*[|_]*\s*$", "", t)          # cuota del final («… 1.40»)
    t = re.sub(r"\s*[|_\-]+\s*$", "", t)
    def num(m):   # «MasdeoO» → «Más de 0» (el OCR confunde el 0 con la o)
        x = m.group(1)
        return "Más de " + ("0" if re.fullmatch(r"[oO0]+", x) else x)
    t = re.sub(r"(?i)m[aá]s\s*de\s*([0-9oO]+(?:[.,]\d)?)(?![a-z])", num, t)
    t = re.sub(r"\s*-\s*(?=Más de)", " - ", t)
    return re.sub(r"\s+", " ", t).strip()


def buscar_partido(loc, vis, conocidos):
    def parecido(a, b):
        b = plano(b)
        mejor = 0.0
        pal = plano(a).split()
        for k in range(min(2, len(pal))):              # sin la basura del escudo de delante («allie Juventus»)
            x = ALIAS.get(" ".join(pal[k:]), " ".join(pal[k:]))
            r = 1.0 if x == b or (len(x) > 3 and (x in b or b in x)) else difflib.SequenceMatcher(None, x, b).ratio()
            mejor = max(mejor, r)
        return mejor
    mejor = max(conocidos, key=lambda c: parecido(loc, c[1]) + parecido(vis, c[2]), default=None)
    if mejor and parecido(loc, mejor[1]) >= 0.7 and parecido(vis, mejor[2]) >= 0.7:
        return mejor
    return None


def linea_n(txt, defecto=0.0):
    m = re.search(r"(\d+(?:[.,]\d+)?)", txt)
    return float(m.group(1).replace(",", ".")) if m else defecto


def over(n):
    """«Más de 2» en bet365 (3 opciones) = 3 o más → Over 2.5; «Más de 28.5» se queda igual."""
    return f"Over {n if n % 1 else n + 0.5:g}"


def a_seleccion(principal, sub, loc, vis):
    """(mercado, opción) del bot para una pata del boleto, o None si no la reconoce."""
    p, s = principal.strip(), plano(sub)
    pp = plano(p)
    lado = "Home" if "local" in s else "Away" if "visitante" in s else None
    if lado is None and " - " in p:   # «Monza - Más de 0 goles»: el equipo va delante
        eq = plano(p.split(" - ")[0])
        lado = "Home" if difflib.SequenceMatcher(None, eq, plano(loc)).ratio() > 0.7 else \
            "Away" if difflib.SequenceMatcher(None, eq, plano(vis)).ratio() > 0.7 else None
    jugador = re.match(r"(.+?)\s*[:\-]\s*(?:mas de\s*)?(\d+(?:[.,]\d)?)\+?", pp)
    nombre = re.split(r"\s*[:\-]\s*", p)[0].strip()
    if s.startswith("jugador"):
        n = linea_n(re.split(r"[:\-]", p, 1)[1] if re.search(r"[:\-]", p) else p, 1)
        n = int(n + 0.5) if n % 1 else int(n)          # «Más de 0.5» = 1+
        if "puerta" in s:
            return "Player Shots On Target Total", f"{nombre} - {n}"
        if "remates" in s:
            return "Player Shots Total", f"{nombre} - {n}"
        if "faltas" in s:
            return "Player Fouls Committed", f"{nombre} - {n}"
        return None
    if "total de goles" in s and lado:
        return f"Total - {lado}", over(linea_n(pp.split(" - ")[-1]))
    if "total de tarjetas" in s and lado:
        return f"{lado} Team Total Cards", over(linea_n(pp.split(" - ")[-1]))
    if ("total de corners" in s or "corners" in s) and lado:
        return f"{lado} Corners Over/Under", over(linea_n(pp.split(" - ")[-1]))
    if "cualquier mitad" in s or "cualquier mitad" in pp:
        return ("To Win Either Half", lado) if lado else None
    if "mayor numero de remates a puerta" in s:
        eq = plano(p.split(":")[-1])
        lado = "Home" if difflib.SequenceMatcher(None, eq, plano(loc)).ratio() > 0.7 else "Away"
        return "ShotOnTarget 1x2", lado
    if s.startswith("1 mitad") and "goles" in s or "1 mitad" in pp:
        return "Goals Over/Under First Half", over(linea_n(pp))
    if "encuentro" in s and "remates" in s and "puerta" in s:
        return "Total ShotOnGoal", over(linea_n(pp))
    if "encuentro" in s and "remates" in s:
        return "Total Shots", over(linea_n(pp))
    if "ambos equipos" in s or "ambos equipos" in pp:
        return "Both Teams Score", "Yes"
    if "resultado final" in s:
        eq = re.sub(r"\s*\d+[.,]\d+$", "", pp)
        if "empate" in eq:
            return "Match Winner", "Draw"
        return "Match Winner", "Home" if difflib.SequenceMatcher(None, eq, plano(loc)).ratio() > \
            difflib.SequenceMatcher(None, eq, plano(vis)).ratio() else "Away"
    if "goles" in s and ("mas de" in pp):
        return "Goals Over/Under", over(linea_n(pp))
    return None


SUB = re.compile(r"^(Equipo|Jugador|Encuentro|Resultado final|Ganar[aá] cualquier mitad|1[ªa°] mitad|2[ªa°] mitad|"
                 r"Ambos equipos|Total de goles|Doble oportunidad)", re.I)


def leer_patas(im, conocidos=None):
    """[{"texto", "sel": "partido|mercado|opción" o None, "partido"}] de la captura (ya recortada)."""
    conocidos = conocidos if conocidos is not None else partidos_conocidos()
    lineas = [l.strip() for l in leer_texto(im).splitlines() if l.strip()]
    patas, pendientes, i = [], [], 0
    while i < len(lineas):
        l = lineas[i]
        if re.search(r"\b\d{1,2} " + MES + r"\b", l, re.I) and i + 1 < len(lineas) and re.search(r"\d{1,2}:\d{2}", lineas[i + 1]):
            loc = re.sub(r"\s*(lun|mar|mi[eé]|jue|vie|s[aá]b|dom)\.?\s+\d{1,2} " + MES + r".*$", "", l, flags=re.I).strip()
            vis = re.sub(r"\s*\d{1,2}:\d{2}.*$", "", lineas[i + 1]).strip()
            pa = buscar_partido(loc, vis, conocidos)
            for principal, sub in pendientes:
                principal = limpiar(principal)
                sel = a_seleccion(principal, sub, pa[1], pa[2]) if pa else None
                bonito = principal
                if sel:
                    try:
                        from picks import JUG_MERCADOS, texto_pick
                        if sel[0] in JUG_MERCADOS:
                            j, n = sel[1].rsplit(" - ", 1)
                            bonito = JUG_MERCADOS[sel[0]][1].format(j=j, n=n)
                        else:
                            bonito = texto_pick(sel[0], sel[1], pa[1], pa[2]) or principal
                    except Exception:
                        pass
                patas.append({"texto": principal, "texto_app": bonito,
                              "partido": f"{pa[1]} – {pa[2]}" if pa else f"{limpiar(loc)} – {limpiar(vis)}",
                              "sel": f"{pa[0]}|{sel[0]}|{sel[1]}" if sel else None})
            pendientes = []
            i += 2
            continue
        if SUB.match(l) and i > 0 and not SUB.match(lineas[i - 1]) and not re.match(r"CREAR APUESTA", lineas[i - 1], re.I):
            principal = lineas[i - 1]
            if principal[:1].islower() and i > 1:      # la línea principal partida en dos («…remates a» / «puerta»)
                principal = f"{lineas[i - 2]} {principal}"
            pendientes.append((re.sub(r"^[o°•O]\s+", "", principal), l))
        i += 1
    return patas
