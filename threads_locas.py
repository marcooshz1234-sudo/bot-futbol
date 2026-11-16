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
MIN_PATA, MAX_PATA = 1.40, 9.0   # 16/11 (Marcos): en Threads e Instagram, patas de 1,40 a 9 (el tope de 1,80 es para Telegram)
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
    # cuanto más loca, patas más altas (en 500 caracteres caben 6-8 patas: la cuota tiene que salir de ahí)
    minimo = {50: 1.55, 100: 1.70, 500: 2.10, 1000: 2.40}.get(objetivo, 1.4)
    max_por = 2 if objetivo <= 100 else 3
    cand = []
    for i, pt in enumerate(partidos):
        for j, p in enumerate([p for p in pt["patas"] if p["cuota"] >= minimo][:8]):
            if usados.get((pt["fid"], p["mercado"], p["opcion"]), 0) >= MAX_USOS:
                continue
            ruido = ((rnd >> ((i * 7 + j) % 60)) & 7) / 100   # un poco de variedad
            cand.append((p["prob"] - ruido - 0.04 * usados.get((pt["fid"], p["mercado"], p["opcion"]), 0), pt, p))
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
    return sel, cuota_bet(sel), misma


MAX_CARACTERES = 490   # Threads no deja más de 500
MAX_USOS = 2           # un mismo pick, como mucho en 2 posts del día (norma de Marcos)


def cuota_bet(sel):
    """Cuota como saldría en bet365: entre partidos se multiplica; dentro de un partido, el recorte del «Crear
    apuesta» (combis_dia.cuota_real_sel, la misma cuenta con la que avisos.py revisa las cuotas)."""
    import combis_dia as C
    r = C.cuota_real_sel([f"{pt['fid']}|{p['mercado']}|{p['opcion']}" for pt, p in sel], [p["cuota"] for _, p in sel])
    return r or round(math.prod(p["cuota"] for _, p in sel), 2)


def libre(fid, mercado, opcion, usados):
    return usados.get((fid, mercado, str(opcion)), 0) < MAX_USOS


def _abreviar(t):
    for a, b in ((" gana alguna de las dos partes", " gana una parte"), (" hace más córners", " más córners"),
                 (" hace más de ", " más de "), ("Más de ", "+"), (" goles", " goles"), (" marca 2 o más", " marca 2+")):
        t = t.replace(a, b)
    return t


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
    por = {}
    for pt, p in sorted(sel, key=lambda x: (x[0]["ini"], x[0]["fid"])):
        por.setdefault(pt["fid"], (pt, []))[1].append(p)
    for pt, ps in por.values():
        lineas.append(f"{_bandera(pt['local_en'])} {pt['local']}–{pt['visitante']} {pt['ini'].strftime('%H:%M')}")
        lineas.append(" · ".join(_abreviar(_linea(pt, p)) for p in ps))
    lineas += ["", f"🎯 CUOTA {coma(cuota)}{' aprox.' if misma else ''} 💎 10€ → {coma(cuota * 10)}€",
               CIERRES[rnd % len(CIERRES)]]
    return "\n".join(lineas)


def combi_que_quepa(objetivo, sel, semilla):
    """(sel, cuota, texto) que no pase de 500 caracteres: si no cabe, fuera la pata más baja y se recalcula."""
    sel = list(sel)
    while True:
        cuota = cuota_bet(sel)
        misma = len({pt["fid"] for pt, _ in sel}) < len(sel)
        texto = texto_combi(objetivo, sel, cuota, misma, semilla)
        if len(texto) <= MAX_CARACTERES or len(sel) <= 3:
            return sel, cuota, texto
        sel.remove(min(sel, key=lambda x: x[1]["cuota"]))


def tiros_partido(partidos, semilla, usados):
    """Combi de solo tiros/faltas de jugadores de un partido (3-5 jugadores habituales)."""
    for pt in sorted(partidos, key=lambda pt: -sum(1 for p in pt["patas"] if p["familia"] == "jugador")):
        js = [p for p in pt["patas"] if p["familia"] == "jugador" and libre(pt["fid"], p["mercado"], p["opcion"], usados)]
        if len(js) < 3:
            continue
        js = js[:5]
        cuota = cuota_bet([(pt, p) for p in js])
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
        p = next((p for p in pt["patas"] if p["mercado"] in mercados and p["prob"] >= 0.5
                  and libre(pt["fid"], p["mercado"], p["opcion"], usados)), None)
        if p:
            filas.append((pt, p))
    if len(filas) < 3:
        return None
    filas = filas[:10]
    while True:
        lineas = [titulo, ""]
        for i, (pt, p) in enumerate(filas, 1):
            lineas.append(f"{i}. {_bandera(pt['local_en'])} {pt['local']}–{pt['visitante']} ➜ {_abreviar(_corto(pt, p))} @{coma(p['cuota'])}")
        lineas += ["", "👇 ¿Con cuál os quedáis? 👇"]
        if len("\n".join(lineas)) <= MAX_CARACTERES or len(filas) <= 3:
            break
        filas = filas[:-1]
    cuota = cuota_bet(filas)
    return filas, cuota, "\n".join(lineas)


# 16/11 (Marcos: «mete de vez en cuando gana y ambos marcan en varios partidos; otra de 2 tiros de uno y 2 tiros de
# otro, uno de cada equipo; no tantas combis "por tal" ni repetir el mismo número; invéntate algo llamativo, algo guay»)

def _cuota_de(ex_cuotas, mercado, opcion):
    for o, c in ex_cuotas.get(mercado) or []:
        if str(o) == opcion:
            try:
                return float(c)
            except (TypeError, ValueError):
                return None
    return None


def _ex(fid):
    from bot import EXTRA
    return leer(EXTRA / f"{fid}.json", {}) or {}


def _pata(pt, mercado, opcion, cuota, texto, familia):
    return {"partido_id": pt["fid"], "mercado": mercado, "opcion": opcion, "cuota": cuota, "texto": texto,
            "familia": familia, "prob": 1 / cuota}


def gana_y_ambos(partidos, semilla, usados):
    """⚽🏆 «Gana X y ambos marcan» en 3-4 partidos (el favorito de cada uno)."""
    import combis_dia as C
    filas = []
    for pt in partidos:
        ex = _ex(pt["fid"])
        cu = ex.get("cuotas") or {}
        mw = {o: float(c) for o, c in cu.get("Match Winner") or [] if c}
        if not {"Home", "Away"} <= set(mw):
            continue
        lado = "Home" if mw["Home"] <= mw["Away"] else "Away"
        c = _cuota_de(cu, "Results/Both Teams Score", f"{lado}/Yes")
        if not c or not (MIN_PATA <= c <= 6.0) or not libre(pt["fid"], "Results/Both Teams Score", f"{lado}/Yes", usados):
            continue
        if C.gana_sin_motivo(ex, {"mercado": "Match Winner", "opcion": lado}):
            continue
        eq = pt["local"] if lado == "Home" else pt["visitante"]
        filas.append((pt, _pata(pt, "Results/Both Teams Score", f"{lado}/Yes", c, f"Gana {eq} y ambos marcan", "gana")))
    filas = sorted(sorted(filas, key=lambda x: x[1]["cuota"])[:4], key=lambda x: x[0]["ini"])
    if len(filas) < 3:
        return None
    cuota = cuota_bet(filas)
    lineas = ["⚽🏆 GANA Y AMBOS MARCAN 🏆⚽", ""]
    for pt, p in filas:
        lineas.append(f"{_bandera(pt['local_en'])} {pt['local']} – {pt['visitante']} · {pt['ini'].strftime('%H:%M')}")
        lineas += [f"✅ {p['texto']}", ""]
    lineas.pop()
    lineas += ["", f"🎯 CUOTA {coma(cuota)} 💎 · 10€ → {coma(cuota * 10)}€", "", "🔥 Goles y victoria: así nos gusta 🔥"]
    return filas, cuota, "\n".join(lineas)


def duelo_tiros(partidos, semilla, usados):
    """⚔️ Un jugador de cada equipo con 2+ tiros (los habituales que da bet365), en el mismo partido."""
    for pt in partidos:
        cu = _ex(pt["fid"]).get("cuotas") or {}
        lados = []
        for mercado in ("Home Player Shots", "Away Player Shots"):
            mejor = None
            for o, c in cu.get(mercado) or []:
                try:
                    nombre, n = str(o).rsplit(" - ", 1)
                    n, c = int(float(n)), float(c)
                except (TypeError, ValueError):
                    continue
                if n >= 2 and MIN_PATA <= c <= 3.0 and libre(pt["fid"], mercado, str(o), usados):
                    if not mejor or c < mejor[1]:
                        mejor = (str(o), c, nombre.strip(), n)
            if mejor:
                lados.append((mercado, mejor))
        if len(lados) < 2:
            continue
        sel = [(pt, _pata(pt, m, o, c, f"{nom}: {n}+ tiros", "jugador")) for m, (o, c, nom, n) in lados]
        cuota = cuota_bet(sel)
        lineas = ["⚔️ EL DUELO DE TIROS ⚔️", "", f"⭐ {pt['local']} vs {pt['visitante']} · {pt['ini'].strftime('%H:%M')}", ""]
        lineas += [f"🎯 {p['texto']} ({eq})" for (_, p), eq in zip(sel, (pt["local"], pt["visitante"]))]
        lineas += ["", f"🎯 CUOTA {coma(cuota)} aprox. 💎 · 10€ → {coma(cuota * 10)}€", "", "👇 ¿Quién dispara más? 👇"]
        return sel, cuota, "\n".join(lineas)
    return None


def empates(partidos, semilla, usados):
    """🤝 LA COMBI DE LOS EMPATES: los 3 partidos más igualados, empate."""
    filas = []
    for pt in partidos:
        c = _cuota_de(_ex(pt["fid"]).get("cuotas") or {}, "Match Winner", "Draw")
        if c and MIN_PATA <= c <= 4.2 and libre(pt["fid"], "Match Winner", "Draw", usados):
            filas.append((pt, _pata(pt, "Match Winner", "Draw", c, "Empate", "empate")))
    filas = sorted(sorted(filas, key=lambda x: x[1]["cuota"])[:3], key=lambda x: x[0]["ini"])
    if len(filas) < 3:
        return None
    cuota = cuota_bet(filas)
    lineas = ["🤝 LA COMBI DE LOS EMPATES 🤝", ""]
    lineas += [f"{_bandera(pt['local_en'])} {pt['local']} – {pt['visitante']} · {pt['ini'].strftime('%H:%M')} ➜ 🤝 Empate @{coma(p['cuota'])}"
               for pt, p in filas]
    lineas += ["", f"🎯 CUOTA {coma(cuota)} 💎 · 10€ → {coma(cuota * 10)}€", "", "😮‍💨 Para valientes 😮‍💨"]
    return filas, cuota, "\n".join(lineas)


def misma_hora(partidos, semilla, usados):
    """⏰ TODO A LAS 20:45: la mejor pata de cada partido que empieza a la misma hora (3 o más)."""
    from collections import Counter
    horas = Counter(pt["ini"] for pt in partidos)
    hora, n = max(horas.items(), key=lambda x: (x[1], -x[0].timestamp())) if horas else (None, 0)
    if n < 3:
        return None
    sel = []
    for pt in [pt for pt in partidos if pt["ini"] == hora]:
        p = next((p for p in pt["patas"] if libre(pt["fid"], p["mercado"], p["opcion"], usados)), None)
        if p:
            sel.append((pt, p))
    if len(sel) < 3:
        return None
    cuota = cuota_bet(sel)
    lineas = [f"⏰ TODO A LAS {hora.strftime('%H:%M')} ⏰", ""]
    lineas += [f"{_bandera(pt['local_en'])} {pt['local']} – {pt['visitante']} ➜ {_linea(pt, p)}" for pt, p in sel]
    lineas += ["", f"🎯 CUOTA {coma(cuota)} 💎 · 10€ → {coma(cuota * 10)}€", "", "⏳ Todo se decide a la vez 🔥"]
    return sel, cuota, "\n".join(lineas)


def tapados(partidos, semilla, usados):
    """🐶 LA DE LOS TAPADOS: el que no es favorito no pierde (doble oportunidad del débil), 3-4 partidos."""
    filas = []
    for pt in partidos:
        cu = _ex(pt["fid"]).get("cuotas") or {}
        mw = {o: float(c) for o, c in cu.get("Match Winner") or [] if c}
        if not {"Home", "Away"} <= set(mw):
            continue
        debil = "Away" if mw["Home"] < mw["Away"] else "Home"
        op = "Draw/Away" if debil == "Away" else "Home/Draw"
        c = _cuota_de(cu, "Double Chance", op)
        import combis_dia as C
        if C.gana_sin_motivo({"partido": _ex(pt["fid"]).get("partido")}, {"mercado": "Double Chance", "opcion": op}):
            continue   # el «tapado» no se juega nada y el favorito sí: no
        if c and 1.6 <= c <= 3.2 and libre(pt["fid"], "Double Chance", op, usados):
            eq = pt["visitante"] if debil == "Away" else pt["local"]
            filas.append((pt, _pata(pt, "Double Chance", op, c, f"{eq} o empate", "doble")))
    filas = sorted(sorted(filas, key=lambda x: x[1]["cuota"])[:4], key=lambda x: x[0]["ini"])
    if len(filas) < 3:
        return None
    cuota = cuota_bet(filas)
    lineas = ["🐶 LA DE LOS TAPADOS 🐶", "", "Hoy vamos con los que nadie ve 👀", ""]
    lineas += [f"{_bandera(pt['local_en'])} {pt['local']} – {pt['visitante']} ➜ 🛡️ {p['texto']} @{coma(p['cuota'])}" for pt, p in filas]
    lineas += ["", f"🎯 CUOTA {coma(cuota)} 💎 · 10€ → {coma(cuota * 10)}€", "", "🤫 Si sale esta, nos retiramos 🤫"]
    return filas, cuota, "\n".join(lineas)


def reto_euro(partidos, semilla, usados):
    """💶 DE 1€ A 1.000€: la x1000 contada como reto."""
    r = combi_cuota(partidos, 1000, semilla + "reto", usados)
    if not r:
        return None
    sel, cuota, t = combi_que_quepa(1000, r[0], semilla)
    misma = len({pt["fid"] for pt, _ in sel}) < len(sel)
    t = t.split("\n")
    t[0] = f"💶 RETO: DE 1€ A {coma(cuota)}€ 💶"
    t = [l if not l.startswith("🎯 CUOTA") else f"🎯 CUOTA {coma(cuota)}{' aprox.' if misma else ''} 💎 1€ → {coma(cuota)}€" for l in t]
    return sel, cuota, "\n".join(t)


ESPECIALES = {"ganaambos": gana_y_ambos, "duelo": duelo_tiros, "empates": empates, "hora": misma_hora,
              "tapados": tapados, "reto": reto_euro, "tiros": lambda v, s, u: (lambda r: r and (r[0], r[1], r[2]))(tiros_partido(v, s, u))}
MAX_DIA = {"x50": 2, "x100": 2, "x500": 2, "x1000": 1, "reto": 1, "empates": 1, "tapados": 2, "hora": 2,
           "ganaambos": 3, "duelo": 3, "tiros": 2, "lista": 6}
ROTACION = ("x100", "ganaambos", "lista", "duelo", "x50", "hora", "tapados", "x500", "lista", "empates", "ganaambos",
            "reto", "tiros", "lista", "duelo", "x100", "hora", "x50", "tapados", "lista", "ganaambos", "x500", "duelo",
            "x1000", "lista")


def plan(dia, desde=None, ya_horas=(), usados_previos=None):
    """[(hora, tipo, texto, sel)] del día. ya_horas: horas que ya tienen post en Threads (no se pisan)."""
    from bot import MADRID
    desde = desde or datetime.now(MADRID)
    todos = partidos_del_dia(dia)
    out, usados, i_lista, n = [], dict(usados_previos or {}), 0, 0
    veces, ultimo, firmas = {}, None, set()
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
            if veces.get(tipo, 0) >= MAX_DIA.get(tipo, 2) or tipo == ultimo:   # variedad: nunca 2 iguales seguidos
                continue
            if tipo in ESPECIALES:
                r = ESPECIALES[tipo](vivos, semilla, usados)
                if r:
                    hecho = (tipo, r[2], r[0])
            elif tipo.startswith("x"):
                r = combi_cuota(vivos, int(tipo[1:]), semilla, usados)
                if r:
                    sel, cuota, texto = combi_que_quepa(int(tipo[1:]), r[0], semilla)
                    hecho = (tipo, texto, sel)
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
        base_tipo = "lista" if tipo.startswith("lista") else tipo
        try:
            from comprobar_post import bloquea
            from bot import mercado_prohibido
            prueba = {"id": f"{dia}-loca-th-{h.strftime('%H%M')}-{tipo}", "fecha": h.strftime("%Y-%m-%dT%H:%M"),
                      "texto": texto, "sel": [f"{pt['fid']}|{p['mercado']}|{p['opcion']}" for pt, p in sel],
                      "cuotas": [p["cuota"] for _, p in sel], "solo_en": ["threads"]}
            motivo = mercado_prohibido(prueba) or bloquea(prueba, texto)
        except Exception as e:
            motivo = None
            print("comprobar:", str(e)[:100])
        if motivo:
            print("No sale", h.strftime("%H:%M"), tipo, "→", motivo)
            continue
        if len(texto) > 500:
            print("No sale", h.strftime("%H:%M"), tipo, "→ más de 500 caracteres")
            continue
        firma = frozenset((pt["fid"], p["mercado"], p["opcion"]) for pt, p in sel)
        if firma in firmas:
            continue   # el mismo post otra vez, no
        firmas.add(firma)
        if any(usados.get((pt["fid"], p["mercado"], p["opcion"]), 0) >= MAX_USOS for pt, p in sel):
            print("No sale", h.strftime("%H:%M"), tipo, "→ un pick ya va en 2 posts")
            continue
        for pt, p in sel:
            k = (pt["fid"], p["mercado"], p["opcion"])
            usados[k] = usados.get(k, 0) + 1
        veces[base_tipo] = veces.get(base_tipo, 0) + 1
        ultimo = base_tipo
        out.append((h, tipo, texto, [f"{pt['fid']}|{p['mercado']}|{p['opcion']}" for pt, p in sel],
                    [p["cuota"] for _, p in sel]))
    return out


def posts(dia, desde=None, sin_locas=False):
    """Los posts para publicaciones/auto.json (solo Threads). sin_locas: no cuentan las locas ya puestas (rehacer)."""
    ya = []
    for f in ("auto.json", "cola.json"):
        for p in leer(PUB / f, []) or []:
            if sin_locas and "-loca-th-" in p["id"] and not any((p.get("redes") or {}).values()):
                continue
            if p.get("fecha", "")[:10] == dia and "threads" in (p.get("solo_en") or ["threads"]) \
                    and not re.search(r"verde|rojo|balance|resumen", p["id"]):
                from bot import MADRID
                ya.append(datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID))
    previos = {}
    for f in ("auto.json", "cola.json"):
        for p in leer(PUB / f, []) or []:
            if p["id"].startswith(dia) and "-loca-th-" not in p["id"] and not p.get("verde_de") \
                    and not re.search(r"verde|rojo|balance|resumen|ganadores", p["id"]):
                for s_ in set(p.get("sel") or []):
                    f_, m_, o_ = (str(s_).split("|") + ["", ""])[:3]
                    if f_.isdigit():
                        previos[(int(f_), m_, o_)] = previos.get((int(f_), m_, o_), 0) + 1
    salida = []
    for i, (h, tipo, texto, sel, cuotas) in enumerate(plan(dia, desde, ya, previos)):
        salida.append({"id": f"{dia}-loca-th-{h.strftime('%H%M')}-{tipo}", "fecha": h.strftime("%Y-%m-%dT%H:%M"),
                       "texto": texto, "sel": sel, "cuotas": cuotas, "solo_en": ["threads"], "origen": "threads_locas",
                       "cuota_bet365": cuota_txt(texto),
                       "sin_foto": True, "sin_porque": True, "fijo": True, "directo": True,
                       "enlace_telegram": i % ENLACE_CADA == ENLACE_CADA - 1})
    return salida


def cuota_txt(texto):
    m = re.search(r"CUOTA ([\d.]+(?:,\d+)?)", texto)
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def guardar(ps):
    auto = leer(PUB / "auto.json", []) or []
    ids = {p["id"] for p in auto}
    auto += [p for p in ps if p["id"] not in ids]
    (PUB / "auto.json").write_text(json.dumps(auto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    from bot import MADRID
    hoy = datetime.now(MADRID).strftime("%Y-%m-%d")
    if "--auto" in sys.argv:   # en el bucle: una vez al día (en cuanto empieza el día), el plan de hoy
        auto = leer(PUB / "auto.json", []) or []
        if not any(p["id"].startswith(f"{hoy}-loca-th-") for p in auto):
            ps = posts(hoy)
            guardar(ps)
            print(f"threads_locas: {len(ps)} posts para {hoy}")
        raise SystemExit(0)
    dia = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else hoy
    ps = posts(dia, sin_locas="--rehacer" in sys.argv)
    if "--rehacer" in sys.argv:   # quita las locas de ese día que aún no han salido y pone las nuevas
        auto = [p for p in leer(PUB / "auto.json", []) or []
                if not (p["id"].startswith(f"{dia}-loca-th-") and not any((p.get("redes") or {}).values()))]
        (PUB / "auto.json").write_text(json.dumps(auto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        guardar(ps)
        print(f"{len(ps)} posts locos rehechos para {dia}")
        raise SystemExit(0)
    if "--guardar" in sys.argv:
        guardar(ps)
        print(f"{len(ps)} posts locos guardados para {dia}")
    else:
        for p in ps:
            print(f"\n===== {p['fecha'][11:]} · {p['id'][11:]}{' · 📲 enlace' if p['enlace_telegram'] else ''}\n{p['texto']}")
        print(f"\n{len(ps)} posts")
