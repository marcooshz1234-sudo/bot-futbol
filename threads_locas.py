"""16/11 (Marcos): «En Threads quiero contenido constantemente, a todas horas, hasta de madrugada: de día cada media
hora, de madrugada cada hora… Inventa un montón de cosas diferentes: combi por 50, por 500, por 1000, una combi de
solo tiros de un partido… Los jugadores que más suelen jugar los puedes meter aunque no haya alineaciones. Solo para
Threads e Instagram. Nada de un pick solo con explicación: combinadas, texto, muchas cosas, fotos con muchos escudos.
De vez en cuando el canal de Telegram debajo».

Arma el plan de posts «locos» del día para Threads (solo texto, sin porqué):
- Huecos: cada 30 min de 09:00 a 01:00 y cada 60 min de 01:00 a 09:00 (HUECOS), saltando los que ya tienen post.
- Tipos que van rotando (TIPOS): combis por 50 / 100 / 500 / 1000, tiros de un partido (jugadores habituales, sin
  esperar alineaciones), listas del día (ambos marcan, goles, córners, favoritos), «la de los favoritos»…
- Patas: de bet365, las más probables (probabilidad sin margen), de partidos que empiecen después del post; nada a
  favor de un equipo que no se juega nada contra uno que sí (que_se_juegan); nada de «más goles» en partidos de
  selecciones flojos de goles (combis_dia.partido_flojo_de_goles).
- Cada 4 posts, el enlace del Telegram en el primer comentario (enlace_telegram).

`python3 threads_locas.py 2026-11-16` enseña el plan sin tocar nada; con --guardar lo mete en publicaciones/auto.json.
"""
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).parent
PUB = RAIZ / "publicaciones"
DIA_INI, DIA_FIN = 9, 1          # de 09:00 a 01:00 cada 30 min; de 01:00 a 09:00 cada hora
HUECO_DIA, HUECO_NOCHE = 30, 60
MARGEN_INICIO = 15               # el partido tiene que empezar al menos 15 min después del post
MIN_PATA, MAX_PATA = 1.20, 1.80   # las normas de siempre: ninguna pata por debajo de 1,20 ni por encima de 1,80
ENLACE_CADA = 4
CUOTAS_LOCAS = (50, 100, 500, 1000)

# mercado de bet365 → (opciones que valen, familia)
MERCADOS = {
    "Match Winner": (("Home", "Away"), "gana"),
    "Double Chance": (("Home/Draw", "Draw/Away"), "doble"),
    "Goals Over/Under": (("Over 0.5", "Over 1.5", "Over 2.5", "Under 3.5", "Under 4.5"), "goles"),
    "Both Teams Score": (("Yes",), "ambos"),
    "Total - Home": (("Over 0.5", "Over 1.5"), "marca"),
    "Total - Away": (("Over 0.5", "Over 1.5"), "marca"),
    "Corners Over Under": (None, "corners"),
    "Corners 1x2": (("Home", "Away"), "corners"),
    "Home Corners Over/Under": (None, "corners"),
    "Away Corners Over/Under": (None, "corners"),
    "Cards Over/Under": (None, "tarjetas"),
    "To Win Either Half": (("Home", "Away"), "gana"),
}
JUGADORES = ("Home Player Shots", "Away Player Shots", "Player Shots", "Player Shots On Target",
             "Home Player Shots On Target", "Away Player Shots On Target", "Player Fouls Committed")


def leer(f, defecto=None):
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except Exception:
        return defecto


def coma(x):
    return f"{x:.2f}".replace(".", ",") if x < 100 else f"{x:,.0f}".replace(",", ".")


def _prob(cuotas, mercado, opcion, cuota):
    """Probabilidad sin margen (con el par del mercado si lo hay)."""
    ops = {str(o): float(c) for o, c in cuotas.get(mercado) or [] if c}
    m = re.match(r"(Over|Under) (\d+(?:\.\d+)?)", str(opcion))
    if m:
        otro = f"{'Under' if m.group(1) == 'Over' else 'Over'} {m.group(2)}"
        if otro in ops:
            return (1 / cuota) / (1 / cuota + 1 / ops[otro])
    if mercado in ("Match Winner", "Corners 1x2") and len(ops) >= 3:
        return (1 / cuota) / sum(1 / c for c in ops.values())
    if mercado == "Both Teams Score" and len(ops) == 2:
        return (1 / cuota) / sum(1 / c for c in ops.values())
    return 1 / cuota / 1.06   # margen típico


def patas_partido(ex):
    """Patas posibles de un partido (de bet365), cada una con su probabilidad sin margen."""
    import combis_dia as C
    from nombres import espanol
    import picks as P
    pa = ex["partido"]
    cuotas = ex.get("cuotas") or {}
    loc, vis = pa["teams"]["home"]["name"], pa["teams"]["away"]["name"]
    flojo = C.partido_flojo_de_goles(ex)
    out = []
    for mercado, (validas, fam) in MERCADOS.items():
        for o, c in cuotas.get(mercado) or []:
            try:
                c = float(c)
            except (TypeError, ValueError):
                continue
            if not (MIN_PATA <= c <= MAX_PATA) or (validas and str(o) not in validas):
                continue
            if P.excluido(mercado, str(o)):   # los mercados prohibidos de siempre (unders, más de 2,5…)
                continue
            if validas is None and not str(o).startswith(("Over", "Under")):
                continue
            p = {"partido_id": pa["fixture"]["id"], "mercado": mercado, "opcion": str(o), "cuota": c, "familia": fam}
            if flojo and C.es_mas_goles(p):
                continue
            if C.gana_sin_motivo(ex, p):
                continue
            try:
                t = P.texto_pick(mercado, o, loc, vis)
            except Exception:
                continue
            p.update(texto=espanol(C.texto_es(t, loc, vis)), prob=_prob(cuotas, mercado, o, c))
            out.append(p)
    # jugadores habituales (titulares en 5 de los últimos 8), sin esperar a las alineaciones
    try:
        for j in C.jugadores_estrella(pa["fixture"]["id"]):
            if MIN_PATA <= float(j["cuota"]) <= MAX_PATA:
                out.append({"partido_id": pa["fixture"]["id"], "mercado": j["mercado"], "opcion": str(j["opcion"]),
                            "cuota": float(j["cuota"]), "familia": "jugador", "texto": j["texto"],
                            "prob": min(0.92, j.get("prob_aprendida") or j.get("frecuencia") or 1 / float(j["cuota"]))})
    except Exception as e:
        print("jugadores:", str(e)[:100])
    ya, sin_rep = set(), []
    for p in sorted(out, key=lambda p: -p["prob"]):
        k = (p["mercado"], p["opcion"])
        if k not in ya:
            ya.add(k)
            sin_rep.append(p)
    return sin_rep


def partidos_del_dia(dia):
    from bot import EXTRA, MADRID
    salida = []
    for f in EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido")
        if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
            continue
        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        if ini.strftime("%Y-%m-%d") != dia:
            continue
        patas = patas_partido(ex)
        if patas:
            from nombres import espanol
            salida.append({"fid": pa["fixture"]["id"], "ini": ini, "local": espanol(pa["teams"]["home"]["name"]),
                           "local_en": pa["teams"]["home"]["name"],
                           "visitante": espanol(pa["teams"]["away"]["name"]), "liga": pa["league"]["name"],
                           "patas": patas})
    return sorted(salida, key=lambda x: x["ini"])


def huecos(dia, desde):
    """Horas de post del día (desde «desde»): cada 30 min de día, cada hora de madrugada."""
    from bot import MADRID
    t = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    fin = t + timedelta(days=1, hours=DIA_FIN)
    out = []
    while t < fin:
        if t >= desde:
            out.append(t)
        noche = DIA_FIN <= t.hour < DIA_INI
        t += timedelta(minutes=HUECO_NOCHE if noche else HUECO_DIA)
    return out


EXTRA_BANDERAS = {"FYR Macedonia": "🇲🇰", "North Macedonia": "🇲🇰", "Gibraltar": "🇬🇮", "Liechtenstein": "🇱🇮",
                  "Luxembourg": "🇱🇺", "Moldova": "🇲🇩", "Faroe Islands": "🇫🇴", "Estonia": "🇪🇪", "Malta": "🇲🇹"}


def _bandera(eq):
    if eq in EXTRA_BANDERAS:
        return EXTRA_BANDERAS[eq]
    try:
        from combis_personales import bandera
        return bandera(eq)
    except Exception:
        return "⚽"


def _corto(pt, p):
    """«Ambos marcan en Alemania–Países Bajos» → «Ambos marcan» (ya va debajo del partido)."""
    return re.sub(r"\s+en\s+" + re.escape(pt["local"]) + r"\s*[–-]\s*" + re.escape(pt["visitante"]) + r"\s*$", "", p["texto"])


def _linea(partido, p):
    from estilo_threads import emoji_pick
    t = _corto(partido, p)
    e = "🦵" if "falta" in t.lower() else emoji_pick(t)
    return f"{e} {t}"


def combi_cuota(partidos, objetivo, semilla, usados):
    """Combi que se acerca a la cuota objetivo con las patas más probables (como mucho 2 por partido, de
    familias distintas), variando cuáles según la semilla para que no salgan siempre las mismas."""
    rnd = int(hashlib.sha1(semilla.encode()).hexdigest(), 16)
    minimo = {50: 1.20, 100: 1.30, 500: 1.40, 1000: 1.45}.get(objetivo, 1.2)   # cuanto más loca, patas más altas
    max_por = 2 if objetivo <= 100 else 3
    cand = []
    for i, pt in enumerate(partidos):
        for j, p in enumerate([p for p in pt["patas"] if p["cuota"] >= minimo][:8]):
            ruido = ((rnd >> ((i * 7 + j) % 60)) & 7) / 100   # un poco de variedad
            cand.append((p["prob"] - ruido - (0.05 if (pt["fid"], p["mercado"], p["opcion"]) in usados else 0), pt, p))
    cand.sort(key=lambda x: -x[0])
    sel, por_partido, fams, cuota = [], {}, {}, 1.0
    for _, pt, p in cand:
        if cuota >= objetivo * 0.85:
            break
        n = por_partido.get(pt["fid"], 0)
        f_ = fams.get(pt["fid"], set())
        if n >= max_por or p["familia"] in f_ or CHOCAN.get(p["familia"], set()) & f_:
            continue
        if cuota * p["cuota"] > objetivo * 1.6 and cuota >= objetivo * 0.5:
            continue
        sel.append((pt, p))
        por_partido[pt["fid"]] = n + 1
        fams.setdefault(pt["fid"], set()).add(p["familia"])
        cuota *= p["cuota"]
    if cuota < objetivo * 0.6:
        return None
    misma = any(v > 1 for v in por_partido.values())
    return sel, round(cuota, 2), misma


# familias que no van juntas en el mismo partido (las normas del 31/10 y 02/11 de comprobar_post)
CHOCAN = {"ambos": {"marca", "doble"}, "marca": {"ambos", "doble"}, "doble": {"ambos", "marca"}}

TITULOS = {50: ["🤑 COMBI x{c} 🤑", "💸 LA DE x{c} 💸"], 100: ["🔥 COMBI POR {c} 🔥", "💯 LA CENTENARIA x{c} 💯"],
           500: ["🤪 LA LOCURA DE x{c} 🤪", "💎 COMBI x{c} 💎"], 1000: ["🚀 COMBI x{c} 🚀", "🎰 LA MILLONARIA x{c} 🎰"]}
CIERRES = ["🍀 ¿LA PINTAMOS DE VERDE? 👀💚", "🔥 ¡A POR ELLA, FAMILIA! 🔥", "✅ ¿QUIÉN SE LA JUEGA CON NOSOTROS? 👇",
           "💚 ¡A POR EL VERDE! 💚", "👇 ¿Cuál quitaríais? 👇"]


def texto_combi(objetivo, sel, cuota, misma, semilla):
    rnd = int(hashlib.sha1(semilla.encode()).hexdigest(), 16)
    t = TITULOS[objetivo][rnd % 2].format(c=coma(cuota))
    lineas = [t, ""]
    actual = None
    for pt, p in sorted(sel, key=lambda x: (x[0]["ini"], x[0]["fid"])):
        if pt["fid"] != actual:
            if actual is not None:
                lineas.append("")
            lineas.append(f"{_bandera(pt['local_en'])} {pt['local']} – {pt['visitante']} · {pt['ini'].strftime('%H:%M')}")
            actual = pt["fid"]
        lineas.append(_linea(pt, p))
    lineas += ["", f"🎯 CUOTA {coma(cuota)}{' aprox.' if misma else ''} 💎 · 10€ → {coma(cuota * 10)}€", "",
               CIERRES[rnd % len(CIERRES)]]
    return "\n".join(lineas)


def tiros_partido(partidos, semilla, usados):
    """Combi de solo tiros/faltas de jugadores de un partido (3-5 jugadores habituales)."""
    for pt in sorted(partidos, key=lambda pt: -sum(1 for p in pt["patas"] if p["familia"] == "jugador")):
        js = [p for p in pt["patas"] if p["familia"] == "jugador" and (pt["fid"], p["mercado"], p["opcion"]) not in usados]
        if len(js) < 3:
            continue
        js = js[:5]
        cuota = round(math.prod(p["cuota"] for p in js) * 0.92, 2)   # mismo partido: aprox. (bet365 la baja algo)
        lineas = [f"🎯 COMBI DE TIROS · {pt['local'].upper()} vs {pt['visitante'].upper()} 🎯", "",
                  f"⭐ {pt['local']} – {pt['visitante']} · {pt['ini'].strftime('%H:%M')}"]
        lineas += [_linea(pt, p) for p in js]
        lineas += ["", f"🎯 CUOTA {coma(cuota)} aprox. 💎 · 10€ → {coma(cuota * 10)}€", "", "🔥 Sin alineaciones aún: van los fijos 🔥"]
        return [(pt, p) for p in js], cuota, "\n".join(lineas)
    return None


LISTAS = (("ambos", "⚽ AMBOS MARCAN HOY ⚽", ("Both Teams Score",)),
          ("goles", "🔥 GOLES HOY: LOS QUE MÁS NOS GUSTAN 🔥", ("Goals Over/Under",)),
          ("corners", "🚩 CÓRNERS DEL DÍA 🚩", ("Corners Over Under", "Corners 1x2", "Home Corners Over/Under", "Away Corners Over/Under")),
          ("gana", "🏆 LOS FAVORITOS DEL DÍA 🏆", ("Match Winner",)))


def lista(partidos, clave, titulo, mercados, usados):
    filas = []
    for pt in partidos:
        p = next((p for p in pt["patas"] if p["mercado"] in mercados and p["prob"] >= 0.5), None)
        if p:
            filas.append((pt, p))
    if len(filas) < 3:
        return None
    filas = filas[:10]
    lineas = [titulo, ""]
    for i, (pt, p) in enumerate(filas, 1):
        lineas.append(f"{i}. {_bandera(pt['local_en'])} {pt['local']} – {pt['visitante']} ➜ {_corto(pt, p)} @{coma(p['cuota'])}")
    lineas += ["", "👇 ¿Con cuál os quedáis? 👇"]
    cuota = round(math.prod(p["cuota"] for _, p in filas), 2)
    return filas, cuota, "\n".join(lineas)


ROTACION = ("x100", "lista", "x50", "tiros", "x500", "lista", "x1000", "x50", "tiros", "x100", "lista", "x500")


def plan(dia, desde=None, ya_horas=()):
    """[(hora, tipo, texto, sel)] del día. ya_horas: horas que ya tienen post en Threads (no se pisan)."""
    from bot import MADRID
    desde = desde or datetime.now(MADRID)
    todos = partidos_del_dia(dia)
    out, usados, i_lista, n = [], set(), 0, 0
    for h in huecos(dia, desde):
        if any(abs((h - y).total_seconds()) < 15 * 60 for y in ya_horas):
            continue
        vivos = [pt for pt in todos if pt["ini"] >= h + timedelta(minutes=MARGEN_INICIO)]
        if len(vivos) < 2:
            continue
        semilla = f"{dia}{h.isoformat()}"
        hecho = None
        for k in range(len(ROTACION)):
            tipo = ROTACION[(n + k) % len(ROTACION)]
            if tipo.startswith("x"):
                r = combi_cuota(vivos, int(tipo[1:]), semilla, usados)
                if r:
                    sel, cuota, misma = r
                    hecho = (tipo, texto_combi(int(tipo[1:]), sel, cuota, misma, semilla), sel)
            elif tipo == "tiros":
                r = tiros_partido(vivos, semilla, usados)
                if r:
                    hecho = (tipo, r[2], r[0])
            else:
                for j in range(len(LISTAS)):
                    clave, titulo, mercados = LISTAS[(i_lista + j) % len(LISTAS)]
                    r = lista(vivos, clave, titulo, mercados, usados)
                    if r:
                        i_lista += j + 1
                        hecho = (f"lista-{clave}", r[2], r[0])
                        break
            if hecho:
                n += k + 1
                break
        if not hecho:
            continue
        tipo, texto, sel = hecho
        try:
            from comprobar_post import bloquea
            from bot import mercado_prohibido
            prueba = {"id": f"{dia}-loca-th-{h.strftime('%H%M')}-{tipo}", "fecha": h.strftime("%Y-%m-%dT%H:%M"),
                      "texto": texto, "sel": [f"{pt['fid']}|{p['mercado']}|{p['opcion']}" for pt, p in sel]}
            motivo = mercado_prohibido(prueba) or bloquea(prueba, texto)
        except Exception as e:
            motivo = None
            print("comprobar:", str(e)[:100])
        if motivo:
            print("No sale", h.strftime("%H:%M"), tipo, "→", motivo)
            continue
        usados |= {(pt["fid"], p["mercado"], p["opcion"]) for pt, p in sel}
        out.append((h, tipo, texto, [f"{pt['fid']}|{p['mercado']}|{p['opcion']}" for pt, p in sel]))
    return out


def posts(dia, desde=None):
    """Los posts para publicaciones/auto.json (solo Threads)."""
    ya = []
    for f in ("auto.json", "cola.json"):
        for p in leer(PUB / f, []) or []:
            if p.get("fecha", "")[:10] == dia and "threads" in (p.get("solo_en") or ["threads"]) \
                    and not re.search(r"verde|rojo|balance|resumen", p["id"]):
                from bot import MADRID
                ya.append(datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID))
    salida = []
    for i, (h, tipo, texto, sel) in enumerate(plan(dia, desde, ya)):
        salida.append({"id": f"{dia}-loca-th-{h.strftime('%H%M')}-{tipo}", "fecha": h.strftime("%Y-%m-%dT%H:%M"),
                       "texto": texto, "sel": sel, "solo_en": ["threads"], "origen": "threads_locas",
                       "sin_foto": True, "sin_porque": True, "enlace_telegram": i % ENLACE_CADA == ENLACE_CADA - 1})
    return salida


if __name__ == "__main__":
    dia = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else datetime.now().strftime("%Y-%m-%d")
    ps = posts(dia)
    if "--guardar" in sys.argv:
        auto = leer(PUB / "auto.json", []) or []
        ids = {p["id"] for p in auto}
        auto += [p for p in ps if p["id"] not in ids]
        (PUB / "auto.json").write_text(json.dumps(auto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(ps)} posts locos guardados para {dia}")
    else:
        for p in ps:
            print(f"\n===== {p['fecha'][11:]} · {p['id'][11:]}{' · 📲 enlace' if p['enlace_telegram'] else ''}\n{p['texto']}")
        print(f"\n{len(ps)} posts")
