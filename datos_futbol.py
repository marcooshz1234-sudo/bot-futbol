"""
Posts de fútbol SIN apuesta (26/10) · ~30 % del contenido.

Meta reparte menos lo que huele a apuestas; los datos de fútbol llegan a más gente y la traen a la
cuenta. Ni cuotas, ni picks, ni «apuesta»: solo datos que el bot ya tiene.

  - 🔥 Rachas vivas de equipos que juegan hoy (todos los días, 10:00)
  - 🤓 ¿Sabías que…? con el xG de un equipo de hoy: marca más (o menos) de lo que dicen sus ocasiones (16:00)
  - ⚽ Pichichis de las 5 grandes ligas (martes 12:30)
  - 📋 Lo que dicen los datos del finde: un dato de cada partido grande del sábado y domingo (viernes 18:00)

plantillas.py llama a posts_del_dia(dia). Cada post sale solo si hay datos de verdad.
"""
from datetime import datetime, timedelta

from bot import DATOS, EXTRA, MADRID, leer
from picks import historial

GRANDES = ("real madrid", "barcelona", "atletico madrid", "manchester city", "arsenal", "liverpool", "chelsea",
           "manchester united", "tottenham", "inter", "ac milan", "juventus", "napoli", "roma", "bayern",
           "borussia dortmund", "bayer leverkusen", "paris saint germain", "marseille", "atalanta", "newcastle",
           "benfica", "porto", "sporting cp", "ajax", "psv", "feyenoord", "sevilla", "villarreal", "athletic",
           "real sociedad", "lazio", "aston villa", "lyon", "monaco")
CORTO = {"paris saint germain": "PSG", "manchester united": "Man. United", "manchester city": "Man. City",
         "bayern münchen": "Bayern", "borussia dortmund": "Dortmund", "bayer leverkusen": "Leverkusen",
         "atletico madrid": "Atlético", "ac milan": "Milan"}


def corto(n):
    return CORTO.get(n.lower(), n)


def grande(n):
    return any(g in n.lower() for g in GRANDES)


def num(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def partidos_del_dia(dia):
    out = []
    for f in EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if not pa:
            continue
        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        if ini.strftime("%Y-%m-%d") == dia:
            out.append({"id": pa["fixture"]["id"], "inicio": ini, "liga": pa["league"]["name"],
                        "local": pa["teams"]["home"], "visitante": pa["teams"]["away"], "h2h": (leer(f) or {}).get("h2h")})
    return sorted(out, key=lambda x: x["inicio"])


def racha(lista, eq, cond):
    """Partidos seguidos (del más reciente hacia atrás) que cumplen cond(goles_favor, goles_contra)."""
    n = 0
    for p in lista:
        g = p.get("goles") or [None, None]
        if None in g:
            break
        local = p["local"]["id"] == eq
        gf, gc = (g[0], g[1]) if local else (g[1], g[0])
        if not cond(gf, gc):
            break
        n += 1
    return n


RACHAS = [("ha ganado sus últimos {n} partidos", lambda f, c: f > c, 4),
          ("lleva {n} partidos seguidos sin perder", lambda f, c: f >= c, 7),
          ("ha marcado en sus últimos {n} partidos", lambda f, c: f > 0, 8),
          ("no encaja desde hace {n} partidos", lambda f, c: c == 0, 3),
          ("lleva {n} partidos seguidos con 3 o más goles en total", lambda f, c: f + c >= 3, 5),
          ("encadena {n} partidos sin ganar", lambda f, c: f <= c, 5)]


def rachas_vivas(dia, hist):
    filas = []
    for pa in partidos_del_dia(dia):
        for lado, rival in (("local", "visitante"), ("visitante", "local")):
            eq = pa[lado]
            for texto, cond, minimo in RACHAS:
                n = racha(hist.get(eq["id"], []), eq["id"], cond)
                if n >= minimo:
                    filas.append((grande(eq["name"]), n / minimo, f"El {corto(eq['name'])} {texto.format(n=n)} "
                                  f"(hoy, ante el {corto(pa[rival]['name'])})", eq["id"]))
    filas.sort(key=lambda x: (x[0], x[1]), reverse=True)
    vistos, elegidas = set(), []
    for g, _, t, eq in filas:
        if eq in vistos:
            continue
        vistos.add(eq)
        elegidas.append(t)
        if len(elegidas) == 4:
            break
    return elegidas


def xg_raro(dia, hist):
    """El equipo de hoy que más se aleja de su xG en los últimos 8 partidos con xG (al menos ±0,4 por partido)."""
    mejor = None
    for pa in partidos_del_dia(dia):
        for lado in ("local", "visitante"):
            eq = pa[lado]
            g, x, n = 0, 0.0, 0
            for p in hist.get(eq["id"], []):
                st = (p.get("stats") or {}).get(str(eq["id"])) or {}
                if st.get("xg") is None or None in (p.get("goles") or [None]):
                    continue
                g += p["goles"][0] if p["local"]["id"] == eq["id"] else p["goles"][1]
                x += st["xg"]
                n += 1
                if n == 8:
                    break
            if n < 6:
                continue
            dif = (g - x) / n
            if abs(dif) >= 0.4 and (not mejor or (grande(eq["name"]), abs(dif)) > (grande(mejor[0]), abs(mejor[1]))):
                mejor = (eq["name"], dif, g / n, x / n, n)
    return mejor


def pichichis():
    d = (leer(DATOS / "goleadores.json", {}) or {}).get("ligas") or {}
    filas = []
    for liga, v in d.items():
        top = (v.get("goles") or [])[:1]
        for j in top:
            filas.append(f"{liga}: {j['jugador']} ({j['equipo']}) · {j['goles']} goles en {j['partidos']} partidos")
    return filas


def dato_partido(pa, hist):
    """Un dato llamativo de un partido (h2h, rachas o xG), sin hablar de apuestas."""
    loc, vis = pa["local"], pa["visitante"]
    h2h = [h for h in pa.get("h2h") or [] if None not in (h.get("goles") or [None])]
    if len(h2h) >= 4:
        goles = sum(sum(h["goles"]) for h in h2h) / len(h2h)
        ambos = sum(1 for h in h2h if min(h["goles"]) > 0)
        if goles >= 3:
            return f"Sus últimos {len(h2h)} cara a cara promedian {num(goles)} goles."
        if ambos >= len(h2h) - 1:
            return f"Marcaron los dos en {ambos} de sus últimos {len(h2h)} enfrentamientos."
    for eq, rival in ((loc, vis), (vis, loc)):
        for texto, cond, minimo in RACHAS:
            n = racha(hist.get(eq["id"], []), eq["id"], cond)
            if n >= minimo:
                return f"El {corto(eq['name'])} {texto.format(n=n)}."
    return None


def posts_del_dia(dia):
    """[(tipo, hora, texto)] para plantillas.py."""
    hist = historial()
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    posts = []
    r = rachas_vivas(dia, hist)
    if len(r) >= 3:
        posts.append(("datos-rachas", f.replace(hour=10, minute=0),
                      f"🔥 {len(r)} RACHAS QUE SIGUEN VIVAS HOY 🔥\n\n" + "\n\n".join(f"• {x}" for x in r)
                      + "\n\n👇 ¿Cuál se rompe hoy?"))
    x = xg_raro(dia, hist)
    if x:
        eq, dif, g, xg, n = x
        if dif > 0:
            cuerpo = (f"El {corto(eq)} marca {num(g)} goles por partido, pero sus ocasiones (xG) solo dan para {num(xg)}.\n\n"
                      f"En sus últimos {n} partidos ha metido {num(dif * n, 0)} goles más de lo que \"tocaba\".")
            pregunta = "👇 ¿Pegada de equipo grande o racha que se va a acabar?"
        else:
            cuerpo = (f"El {corto(eq)} genera {num(xg)} de xG por partido, pero solo marca {num(g)}.\n\n"
                      f"En sus últimos {n} partidos le faltan {num(-dif * n, 0)} goles para lo que merecían sus ocasiones.")
            pregunta = "👇 ¿Hoy se le abre la portería?"
        posts.append(("datos-xg", f.replace(hour=16, minute=0), f"🤓 ¿SABÍAS QUE…? 🤓\n\n{cuerpo}\n\n{pregunta}"))
    if f.weekday() == 1:
        p = pichichis()
        if len(p) >= 3:
            posts.append(("datos-pichichis", f.replace(hour=12, minute=30),
                          "⚽ LOS PICHICHIS DE EUROPA ⚽\n\n" + "\n".join(f"• {x}" for x in p)
                          + "\n\n👇 ¿Quién acaba la temporada arriba?"))
    if f.weekday() == 4:
        lineas = []
        for d in (f + timedelta(days=1), f + timedelta(days=2)):
            for pa in partidos_del_dia(d.strftime("%Y-%m-%d")):
                if not (grande(pa["local"]["name"]) or grande(pa["visitante"]["name"])):
                    continue
                dt = dato_partido(pa, hist)
                if dt:
                    lineas.append(f"⚽ {corto(pa['local']['name'])} – {corto(pa['visitante']['name'])} "
                                  f"({['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom'][pa['inicio'].weekday()]} "
                                  f"{pa['inicio']:%H:%M})\n{dt}")
                if len(lineas) == 6:
                    break
            if len(lineas) == 6:
                break
        if len(lineas) >= 3:
            posts.append(("datos-finde", f.replace(hour=18, minute=0),
                          f"📋 LO QUE DICEN LOS DATOS DEL FINDE · {len(lineas)} PARTIDOS 📋\n\n" + "\n\n".join(lineas)
                          + "\n\n👇 ¿Qué partido no te pierdes?"))
    return posts
