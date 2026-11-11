"""11/11 (Marcos: «sí», opción B): el bot apunta SOLO, al momento y sin gastar IA, los picks de fútbol de los tipsters
que vienen claros en texto («🍀 Betis o empate @1,45», «➡️ Gana el Jaén», «🍀 +2.5 goles Trival Valderas - Leganés»).

- Lee los posts nuevos de datos/tipsters_raw.json (de los 2 últimos días).
- Busca el partido entre los nuestros de ese día o el siguiente (calendarios y datos/proximos) por los nombres.
- Entiende: «X o empate», «gana X» / «victoria de X», «empate», «ambos marcan», «más de N,5 goles» / «+N.5»,
  «X marca» / «X marca N o más». Cuota (@1,45 / cuota 1.45) y stake si vienen.
- Si no está claro (fotos de boletos, combinadas raras, baloncesto, tenis, publicidad), NO se apunta: lo hace Claude
  en su turno de Ojeador. Lo apuntado aquí lleva "auto": true y el «por qué» lo añade Claude después.
Registro de lo ya mirado: datos/tipsters_auto.json.
"""
import json
import re
import unicodedata
from datetime import datetime, timedelta

from bot import DATOS, MADRID, leer

VISTOS = DATOS / "tipsters_auto.json"
MARCA_PICK = ("🍀", "➡️", "▪️", "👉", "🎯", "⚽")
NO_FUTBOL = re.compile(r"\b(nba|puntos|triples|rebotes|asistencias|tenis|atp|wta|set|juegos|basket|euroliga|acb)\b", re.I)
PUBLI = re.compile(r"https?://|comprar|precio|desbloquea|reserva tu plaza|vip|premium", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9+.,/ ]", " ", s)
    return " ".join(s.split())


VACIAS = {"real", "club", "city", "united", "fc", "cf", "cd", "ud", "sd", "rcd", "sporting", "atletico", "athletic", "deportivo",
          "union", "racing", "olympique", "inter", "sc", "ac", "as", "ss", "us", "w", "fem", "women", "de", "del", "la", "el"}


def fichas(nombre):
    """Formas de reconocer un equipo en un texto: el nombre entero y sus palabras propias (≥4 letras)."""
    n = norm(nombre).replace(" w", "")
    out = {n}
    out |= {w for w in n.split() if len(w) >= 4 and w not in VACIAS}
    try:
        from combis_dia import nombre_es
        out.add(norm(nombre_es(nombre)).replace(" w", ""))
    except Exception:
        pass
    return {x for x in out if len(x) >= 4}


def partidos(dias):
    """[(fid, fecha Madrid, local, visitante)] de esos días (calendarios y próximos)."""
    out = {}
    for f in DATOS.glob("calendario_*.json"):
        for x in leer(f, []) or []:
            d = datetime.fromisoformat(x["fixture"]["date"]).astimezone(MADRID)
            if d.strftime("%Y-%m-%d") in dias:
                out[x["fixture"]["id"]] = (x["fixture"]["id"], d, x["teams"]["home"]["name"], x["teams"]["away"]["name"])
    for f in (DATOS / "proximos").glob("*.json"):
        pa = (leer(f, {}) or {}).get("partido") or {}
        try:
            d = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        except (KeyError, ValueError):
            continue
        if d.strftime("%Y-%m-%d") in dias:
            out[pa["fixture"]["id"]] = (pa["fixture"]["id"], d, pa["teams"]["home"]["name"], pa["teams"]["away"]["name"])
    return list(out.values())


def contiene(texto, fs):
    return any(re.search(rf"(?<![a-z]){re.escape(f)}(?![a-z])", texto) for f in fs)


def buscar_partido(linea, todo, cands):
    """El único partido del que habla la línea (o, si la línea solo nombra un equipo, el post entero)."""
    for txt in (linea, todo):
        hits = []
        for fid, d, loc, vis in cands:
            fl, fv = fichas(loc), fichas(vis)
            l, v = contiene(txt, fl), contiene(txt, fv)
            if l or v:
                hits.append(((fid, d, loc, vis), l, v))
        if len(hits) == 1:
            return hits[0]
        dobles = [h for h in hits if h[1] and h[2]]
        if len(dobles) == 1:
            return dobles[0]
        if hits:
            return None   # ambiguo: que lo mire Claude
    return None


def mercado(l, lado_l, lado_v):
    """(mercado, opcion) como API-Football, o None si no está claro."""
    lado = "Home" if lado_l and not lado_v else "Away" if lado_v and not lado_l else None
    if re.search(r"ambos marcan|btts|ambos equipos marcan", l):
        return "Both Teams Score", "Yes"
    if re.search(r"[a-z]{3,}\s*[+-]\s*\d(?:[.,]\d+)?(?!\s*goles?)\b", l) and not re.search(r"(?:mas de|over)\s*\d", l):
        return None   # 11/11: «Accrington +1,5» es hándicap del equipo, no «más de 1,5 goles»: que lo mire Claude
    m = re.search(r"(?:mas de|over|\+)\s*(\d)[.,]5\s*goles?|(?:mas de|over|\+)\s*(\d)[.,]5\b", l)
    if m and not re.search(r"\bmarca", l):
        if re.search(r"1\s*(?:a|era|ª)?\s*parte|primera parte|descanso|1t\b", l):
            return None
        return "Goals Over/Under", f"Over {m.group(1) or m.group(2)}.5"
    if lado and re.search(r"\bmarca", l):
        n = re.search(r"marca\s*(?:mas de\s*)?(\d)(?:[.,]5)?\s*(?:o mas|\+)?", l)
        k = int(n.group(1)) if n else 1
        if n and "." not in n.group(0) and "," not in n.group(0):
            k -= 1   # «marca 2 o más» = más de 1,5
        return (f"Total - {lado}", f"Over {max(k, 0)}.5")
    if lado and re.search(r"o empate|\b1x\b|\bx2\b|doble oportunidad", l):
        return "Double Chance", "Home/Draw" if lado == "Home" else "Draw/Away"
    if lado and re.search(r"\bgana\b|victoria|\bwin\b|\bganador\b", l) and "clasifica" not in l:
        return "Match Winner", lado
    if re.search(r"^\W*empate\W*$|\bempate\b(?! no)", l) and not lado:
        return "Match Winner", "Draw"
    return None


def lineas_pick(texto):
    ls = [x.strip() for x in texto.splitlines() if x.strip()]
    picks = [x for x in ls if x.startswith(MARCA_PICK) or re.match(r"(?i)mi (selecci[oó]n|parte)\s*:", x)]
    return picks or ([ls[0]] if len(ls) <= 3 and ls else [])


def argumentos(texto):
    return [re.sub(r"^[•\-▪️\s]+", "", x).strip() for x in texto.splitlines() if x.strip().startswith(("•", "-", "▪"))][:4]


def analizar_post(canal, p, cands):
    t = p.get("texto") or ""
    if not t.strip() or NO_FUTBOL.search(t) or PUBLI.search(t) or "✅" in t[:3]:
        return []
    todo = norm(t)
    out = []
    for lp in lineas_pick(t):
        l = norm(lp)
        # varias cosas en la misma pata («gana y marca más de 1 y Jaén marca») o de 1ª parte: que lo mire Claude
        if re.search(r"\by\b|&|\bmitad\b|1 ?a parte|1era parte|primera parte|descanso", l):
            continue
        hit = buscar_partido(l, todo, cands)
        if not hit:
            continue
        (fid, d, loc, vis), hl, hv = hit
        lado_l, lado_v = contiene(l, fichas(loc)), contiene(l, fichas(vis))
        mo = mercado(l, lado_l, lado_v)
        if not mo:
            continue
        cu = re.search(r"(?:@|cuota\s*:?\s*)(\d+[.,]\d+)", lp, re.I) or re.search(r"(?:@|cuota\s*:?\s*)(\d+[.,]\d+)", t, re.I)
        st = re.search(r"stake\s*:?\s*(\d+)", t, re.I)
        out.append({"tipster": canal, "fuente": p.get("id"), "dia": d.strftime("%Y-%m-%d"), "local": loc, "visitante": vis,
                    "partido_id": fid, "texto": re.sub(r"^[^\wÀ-ÿ+]+", "", lp).strip()[:120], "mercado": mo[0], "opcion": mo[1],
                    "cuota": float(cu.group(1).replace(",", ".")) if cu else None, "stake": int(st.group(1)) if st else None,
                    "argumento": argumentos(t), "auto": True})
    return out


def main(ahora=None):
    import anotar_tipster
    ahora = ahora or datetime.now(MADRID)
    raw = leer(DATOS / "tipsters_raw.json", {}) or {}
    vistos = set(leer(VISTOS, []) or [])
    ya = leer(anotar_tipster.FICHERO, []) or []
    clave = lambda x: (x["tipster"], x.get("dia"), norm(x.get("local"))[:6], x.get("mercado"), str(x.get("opcion")))
    hechos = {clave(x) for x in ya}
    desde = (ahora - timedelta(days=2)).strftime("%Y-%m-%d")
    cache = {}
    nuevos = 0
    for canal, lista in raw.items():
        for p in lista:
            pid = p.get("id")
            if not pid or pid in vistos or (p.get("fecha") or "")[:10] < desde:
                continue
            vistos.add(pid)
            dia = (p.get("fecha") or ahora.isoformat())[:10]
            if dia not in cache:
                d0 = datetime.fromisoformat(dia)
                cache[dia] = partidos({dia, (d0 + timedelta(days=1)).strftime("%Y-%m-%d")})
            for pk in analizar_post(canal, p, cache[dia]):
                if clave(pk) in hechos:
                    continue
                if anotar_tipster.anotar(pk):
                    hechos.add(clave(pk))
                    nuevos += 1
                    print(f"Tipster (auto): {canal} · {pk['local']} – {pk['visitante']} · {pk['texto']} → {pk['mercado']} {pk['opcion']}")
    VISTOS.write_text(json.dumps(sorted(vistos)[-3000:], ensure_ascii=False) + "\n", encoding="utf-8")
    if nuevos:
        import tipsters
        tipsters.aprender(tipsters.actualizar())
    print(f"Tipsters (auto): {nuevos} picks apuntados solos")
    return nuevos


if __name__ == "__main__":
    main()
