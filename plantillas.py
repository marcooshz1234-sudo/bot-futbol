"""
El Analista · escribe los posts con plantillas.

Se ejecuta después de picks.py. Con datos/picks.json monta los posts de cada día
con el formato de Combilocas y los deja en publicaciones/auto.json, con la hora a
la que tienen que salir. El Publicador los publica desde ahí.

- Solo escribe El Analista: El Publicador nunca toca auto.json (guarda lo que
  ya ha publicado en publicaciones/enviados.json), así no se pisan.
- Los posts aún no publicados se reescriben en cada pasada con las cuotas
  nuevas; los ya publicados no se tocan.
- Ningún post sale después de su primer partido: se adelanta a 1 h antes.
- AUTO_DESDE: primer día con posts automáticos (para no duplicar lo que ya
  estaba programado a mano).
"""

import json
import re
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer
from picks import es_sin_empate


def es(nombre):
    """11/11: nombres en español en los textos (Czechia → Chequia, Spain → España, Lyon W → Lyon (fem.))."""
    try:
        from combis_dia import nombre_es
        return nombre_es(nombre)
    except Exception:
        return nombre

AUTO = RAIZ / "publicaciones" / "auto.json"
AUTO_DESDE = "2026-10-26"                       # días anteriores ya estaban programados en Metricool
ESCALERA_DESDE = "2026-10-24"                   # la escalera ya sale sola desde el sábado
REGISTRO = DATOS / "registro_aciertos.json"
MARGEN_ANTES_PARTIDO = timedelta(minutes=60)
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]


def num(c):
    return f"{c:.2f}".replace(".", ",")


ESPERA_TOPE = 35   # 03/11: minutos antes del partido a los que sale sí o sí aunque no haya alineación


def bandera_pick(p):
    """03/11 (Marcos): en los posts de varios partidos, la bandera del país del EQUIPO del pick (Olise → 🇩🇪, Shakhtar →
    🇺🇦). Si el pick es del partido entero, la del local. Si no se sabe, la de la competición."""
    import semana
    import picks as P
    eq = p.get("equipo")
    if not eq:
        m = p.get("mercado", "")
        lado_ = P.lado_pick(p)
        if m in ("Shots.1x2", "ShotOnTarget 1x2"):
            lado_ = {"Home": "local", "Away": "visitante"}.get(p.get("opcion"))
        elif lado_ is None and (" Home" in m or m.startswith("Home")):
            lado_ = "local"
        elif lado_ is None and (" Away" in m or m.startswith("Away")):
            lado_ = "visitante"
        eq = p.get("visitante") if lado_ == "visitante" else p.get("local")
    pais = semana.pais_equipo(eq) if eq else None
    # si no se sabe el país, ✅ (las banderas de competición como ⭐ no las entiende el seguimiento de picks)
    return semana.BANDERAS.get(pais) or "⚽"   # 11/11: con ✅ parecía que la pata ya estaba acertada


def lista(picks):
    """27/10: como los posts que más gustaron: una línea por selección con la bandera, sin cuota por pata
    ni números (la cuota de cada pata va en el post como dato aparte: "cuotas").
    03/11 (Marcos): la bandera es la del país del equipo del pick, en lugar del ✅."""
    return "\n".join(f"{bandera_pick(p)} {con_equipo(p)}" for p in picks)


VERDE = "🍀 ¿LA PINTAMOS DE VERDE? 👀💚"
FORMATO_27 = True          # el formato del martes 27/10 (combis_dia.py)
FORMATO_27_DESDE = "2026-10-28"   # poner "9999" para volver al de antes
GANADORES_ACTIVO = True
DATOS_ACTIVO = False       # posts de fútbol sin apuesta (datos_futbol.py): quitados por Marcos el 27/10    # «quién gana hoy» (activado por Marcos el 27/10)   # el cierre de los posts con más likes


def combi(titulo, picks, cuota):
    """Post de combi corto: título, selecciones, cuota y cierre. Nada más (27/10: menos texto = más likes).
    09/11 (Marcos: «parecemos un bot»): estilo de tipster de verdad: una frase como persona, los picks, «Cuota @x»."""
    return f"{intro(titulo)}\n\n{lista(picks)}\n\n📈 Cuota @{num(cuota)}\n\n{CIERRE_TELEGRAM}"


def intro(titulo):
    """09/11: el título de máquina («🔥⚽ COMBILOCAS — ¡COMBI DEL LUNES x2,73! 🍀») → frase de persona."""
    m = re.search(r"DEL (LUNES|MARTES|MIÉRCOLES|JUEVES|VIERNES|SÁBADO|DOMINGO)", titulo)
    d = m.group(1).lower() if m else "día"
    t = titulo.upper()
    if "LA LOCA" in t:
        return f"Y para los valientes, la loca del {d} 🤪🔥"
    if "GANA O EMPATA" in t:
        return f"Os dejo la de «gana o empata» para el {d} 🛡️"
    if "SEGURA" in t:
        return f"Vamos con la segura del {d} familia 🔒"
    if "COMBILOCAS" in t:
        return f"Vamos con la combi del {d} familia 🔥"
    return titulo


def clave(p):
    return (p["partido_id"], p["mercado"], p["opcion"])


OPCIONALES = ("combi-cuota_3", "combi-liga", "combi-atreve", "picks-hoy")
MAX_OPCIONALES = 2
MAX_POSTS_POR_SELECCION = 2   # una misma selección no sale en más de 2 posts
MAX_COMBIS_POR_PARTIDO = 99   # 27/10: sin tope (Marcos aprobó que un partido salga en varias combis)
MIN_LISTA = 3   # mínimo de picks para una lista (3 para que los días con pocos partidos tengan contenido)


def dato(picks):
    """Frase de respaldo con el dato real del pick más fiable."""
    p = max(picks, key=atractivo)
    pos = p.get("posiciones")   # 26/10: la tabla también cuenta
    tabla = f" · en la liga, {pos[0]}º vs {pos[1]}º" if pos else ""
    return f"📊 {p['texto']} → {p['detalle']} en sus últimos partidos{tabla}"


def atractivo(p):
    """Para las listas de picks se prefieren apuestas 'a favor' (ganar, goles, córners...)
    frente a 'menos de' o 'no marcan', que se entienden peor en redes."""
    o, m = p["opcion"], p["mercado"]
    extra = 0.0
    if o.startswith("Under") or o == "No":
        extra -= 0.08
    if m in ("Match Winner", "Double Chance", "Both Teams Score") and o != "No":
        extra += 0.04
    if m in ("Corners Over Under", "Cards Over/Under") and o.startswith("Over"):
        extra += 0.03
    from picks import calidad
    return calidad(p) + extra


PROB_MIN_LISTA = 0.60


def mejores_para_lista(picks):
    """Un pick por partido y variedad: se van cogiendo por turnos de cada tipo (goles, tiros,
    jugador, tarjetas, córners...) para que la lista no sea casi todo goles."""
    # 26/10: en las listas solo lo que el bot de verdad ve probable (antes salía "Gana el Lazio" con un 47 %)
    candidatos = [p for p in sorted(picks, key=atractivo, reverse=True) if not es_sin_empate(p["mercado"], p["opcion"])
                  and (p.get("prob_aprendida") is None or p["prob_aprendida"] >= PROB_MIN_LISTA)
                  and p.get("campo") not in ("faltas_c",)   # 27/10: nada de "X comete 1+ faltas" en las listas
                  # 27/10 (Marcos): «más de 2,5 goles» (también con «ambos marcan») solo si es muy probable (≥70 %)
                  and not (re.search(r"Over 2\.5|o/yes 2\.5", f"{p['mercado']}|{p['opcion']}")
                           and (p.get("prob_aprendida") or 0) < 0.70)]
    por_tipo = {}
    for p in candidatos:
        por_tipo.setdefault(p.get("tipo") or "otros", []).append(p)
    elegidos, vistos = [], set()
    while any(por_tipo.values()):
        for tipo in sorted(por_tipo, key=lambda t: -atractivo(por_tipo[t][0]) if por_tipo[t] else 0):
            while por_tipo[tipo]:
                p = por_tipo[tipo].pop(0)
                if p["partido_id"] not in vistos:
                    elegidos.append(p)
                    vistos.add(p["partido_id"])
                    break
    return elegidos


# 26/10: las combis de partido grande eran el formato más estable en Threads (mediana 1.236 vistas)
GRANDES = ("real madrid", "barcelona", "atletico madrid", "manchester city", "arsenal", "liverpool", "chelsea",
           "manchester united", "tottenham", "inter", "ac milan", "juventus", "napoli", "roma", "bayern",
           "borussia dortmund", "bayer leverkusen", "paris saint germain", "marseille", "atalanta", "newcastle",
           "benfica", "porto", "sporting cp", "ajax", "psv", "feyenoord")
BANDERA = {"LaLiga": "🇪🇸", "Premier": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Serie A": "🇮🇹", "Bundesliga": "🇩🇪",
           "Ligue 1": "🇫🇷", "Champions League": "⭐", "Europa League": "🟠", "Conference League": "🟢",
           "Champions": "⭐", "Conference": "🟢", "Segunda": "🇪🇸", "Championship": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Eredivisie": "🇳🇱",
           "Primeira Liga": "🇵🇹", "Copa del Rey": "🇪🇸", "Carabao Cup": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "FA Cup": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
           "Coppa Italia": "🇮🇹", "DFB-Pokal": "🇩🇪", "Coupe de France": "🇫🇷", "Taça de Portugal": "🇵🇹", "KNVB Beker": "🇳🇱",
           "Liga F": "🇪🇸", "Segunda Liga": "🇵🇹", "Serie C": "🇮🇹", "Liga I": "🇷🇴", "1. Division": "🇩🇰"}
CORTO = {"paris saint germain": "PSG", "manchester united": "MAN. UNITED", "manchester city": "MAN. CITY",
         "bayern münchen": "BAYERN", "borussia dortmund": "DORTMUND", "bayer leverkusen": "LEVERKUSEN",
         "atletico madrid": "ATLÉTICO", "real madrid": "MADRID", "barcelona": "BARÇA", "ac milan": "MILAN"}


def grandeza(c):
    return sum(any(g in eq.lower() for g in GRANDES) for eq in (c["local"], c["visitante"]))


def corto(eq):
    return CORTO.get(eq.lower(), eq).upper()


def combi_partido_grande(d):
    """La combi de partido del día con más equipos grandes (al menos uno), o None."""
    cands = [c for c in d.get("combis_partido") or [] if grandeza(c) >= 1 and c.get("picks")]
    return max(cands, key=lambda c: (grandeza(c), c.get("cuota_sumada", 0)), default=None)


# 27/10: las combis de un solo partido, con el formato que mejor ha funcionado en Threads (Barça–Madrid):
# texto en mayúsculas con la cuota de cada pata, "resultado probable" y una foto-tarjeta del partido con los
# escudos y la hora (imagenes.tarjeta → {id}.tarjeta.jpg, la que suben Threads e Instagram)
LIGA_NOMBRE = {"LaLiga": "LALIGA", "Premier League": "PREMIER", "Premier": "PREMIER", "Serie A": "SERIE A",
               "Bundesliga": "BUNDESLIGA", "Ligue 1": "LIGUE 1", "Champions League": "CHAMPIONS", "Champions": "CHAMPIONS",
               "Europa League": "EUROPA LEAGUE", "Conference League": "CONFERENCE", "Conference": "CONFERENCE"}


def datos_tarjeta(cp):
    """Escudos, ids y hora del partido de una combi (de datos/extra), o None."""
    from bot import EXTRA
    pa = (leer(EXTRA / f"{cp['picks'][0]['partido_id']}.json") or {}).get("partido")
    if not pa:
        return None
    t = pa["teams"]
    return {"local": cp["local"], "visitante": cp["visitante"], "id_l": t["home"]["id"], "id_v": t["away"]["id"],
            "logo_l": t["home"].get("logo"), "logo_v": t["away"].get("logo"), "fecha": cp["fecha"],
            "liga": cp.get("competicion")}


def cumple(p, gl, gv):
    """¿El marcador gl-gv cumple la pata? None si la pata no depende solo del marcador."""
    m, o = p["mercado"], str(p["opcion"])
    linea = lambda: float(o.split()[-1])
    if m == "Goals Over/Under" and o.startswith("Over"):
        return gl + gv > linea()
    if m == "Both Teams Score":
        return (gl > 0 and gv > 0) == (o == "Yes")
    if m == "Match Winner":
        return {"Home": gl > gv, "Away": gv > gl, "Draw": gl == gv}.get(o)
    if m == "Double Chance":
        return {"Home/Draw": gl >= gv, "Draw/Away": gv >= gl}.get(o)
    if m == "Total - Home" and o.startswith("Over"):
        return gl > linea()
    if m == "Total - Away" and o.startswith("Over"):
        return gv > linea()
    return None


def resultados_probables(cp, tj, n=3):
    """Los n marcadores más probables (Poisson con el xG reciente) que cumplen las patas de la combi."""
    try:
        import math
        import prueba_xg
        from picks import historial
        lam = prueba_xg.lambdas(historial(), tj["id_l"], tj["id_v"])
    except Exception:
        return []
    if not lam:
        return []
    pois = lambda k, l: math.exp(-l) * l ** k / math.factorial(k)
    cands = []
    for gl in range(7):
        for gv in range(7):
            if all(cumple(p, gl, gv) is not False for p in cp["picks"]):
                cands.append((pois(gl, lam[0]) * pois(gv, lam[1]), f"{gl}-{gv}"))
    return [r for _, r in sorted(cands, reverse=True)[:n]]


def texto_combi_partido(cp, tj, cuota):
    liga = LIGA_NOMBRE.get(cp.get("competicion"), str(cp.get("competicion") or "").upper())
    band = BANDERA.get(cp.get("competicion"), "⚽")
    # 09/11 (Marcos): como un tipster de verdad, sin mayúsculas ni «[x1.73]» ni «cuota aprox.»
    lineas = [f"Os dejo la combi del {es(cp['local'])} – {es(cp['visitante'])} {band}🔥", ""]
    partido = f"{cp['local']}–{cp['visitante']}"
    for p in cp["picks"]:
        t = p["texto"].replace(f" en el {partido}", "").replace(f" del {partido}", "").replace(f" en {partido}", "")
        lineas.append(f"🍀 {t}")
    lineas += ["", f"📈 Cuota @{num(cuota)}", "", CIERRE_TELEGRAM]
    return "\n".join(lineas)


def balance_seguro():
    """(verdes, rojas, beneficio con 10 €) de los «pick seguro» ya resueltos (docs/resumenes.json)."""
    res = leer(RAIZ / "docs" / "resumenes.json", {}) or {}
    v = r = 0
    gan = 0.0
    for dia in res.values():
        for c in dia.get("combis") or []:
            if re.search(r"-pick-seguro(-2)?$", c.get("id", "")) and c.get("cuota") and c.get("estado") in ("verde", "rojo"):
                if c["estado"] == "verde":
                    v += 1
                    gan += 10 * (c["cuota"] - 1)
                else:
                    r += 1
                    gan -= 10
    return v, r, gan


def stake(p):
    """09/11: stake sobre 10 según lo probable que lo vemos (nunca «metedle 200 €»)."""
    pr = p.get("prob_aprendida") or 0
    return 4 if pr >= 0.74 else 3 if pr >= 0.66 else 2


def texto_seguro(p, dia=""):
    """01/11 (Marcos): un solo pick, el más seguro del día, con su balance acumulado.
    09/11: desde SEGURO_DESDE, con 2-3 razones reales y stake (como los tipsters grandes), sin «10€ → X€»."""
    band = BANDERA.get(p.get("competicion"), "⚽")
    v, r, gan = balance_seguro()
    import combis_dia as _c
    if dia and dia >= _c.SEGURO_DESDE:
        try:
            import razones as R
            from picks import historial
            motivos = R.razones(p, historial())
            if p.get("tipster") and len(motivos) < 2:   # 09/11: pick de los tipsters: los datos que dan ellos (hechos)
                import tipsters
                tk = next((x for x in tipsters.picks_del_dia(dia) if x["partido_id"] == p["partido_id"]), {})
                tipo_de = lambda t: {k for k, rx in tipsters.RAZONES.items() if re.search(rx, t, re.I)} & {"categoría", "casa/fuera"}
                for a in tk.get("argumento") or []:   # sin repetir lo que ya dicen nuestros datos
                    if not any(tipo_de(a) & tipo_de(m) for m in motivos):
                        motivos.append(a)
                motivos = motivos[:3]
        except Exception as e:
            print("razones:", str(e)[:120])
            motivos = []
        saludo, con_razones, con_stake = "Vamos con el pick de hoy familia 🔥", True, True
        try:   # 10/11: ficha del Redactor en la Oficina (por defecto, lo de siempre)
            import ajustes as AJ
            c = AJ._control()
            saludo = AJ.valor("saludo_pick", c) or saludo
            con_razones, con_stake = bool(AJ.valor("pick_razones", c)), bool(AJ.valor("pick_stake", c))
        except Exception as e:
            print("ajustes redactor:", e)
        # 11/11: fuera los titulares de prensa sueltos («El deporte 'esquiva' la huelga (La Tribuna…)»): no explican el pick
        motivos = [m for m in motivos if not re.search(r"\([A-ZÁÉÍÓÚ][^()]{3,40}\)\s*$", m)]
        if not con_razones:
            motivos = []
        lineas = [saludo, "",
                  f"{band} {es(p['local'])} – {es(p['visitante'])} · {p['fecha'][11:16]}", "",
                  f"🍀 {con_equipo(p)} @{num(p['cuota'])}" + (" (aprox.)" if p.get("cuota_tipster") else "")]
        if con_stake:
            lineas.append(f"🧠 Stake {stake(p)}/10")
        if motivos:
            lineas += [""] + [f"👨‍💻 {m}" for m in motivos]   # 09/11 (Marcos): sin la palabra «Argumento»
        if v + r:
            roi = 100 * gan / (10 * (v + r))
            lineas += ["", f"📊 Historial: {v} ✅ · {r} ❌ · {'+' if roi >= 0 else ''}{roi:.0f} %".replace(".", ",")]
        lineas += ["", "🔞 Juega con cabeza", CIERRE_TELEGRAM]
        return "\n".join(lineas)
    lineas = ["🔒 PICK SEGURO DEL DÍA 🔒", "",
              f"{band} {es(p['local'])} – {es(p['visitante'])} · {p['fecha'][11:16]}",
              f"✅ {con_equipo(p)}", "",
              f"🎯 Cuota {num(p['cuota'])}", f"💶 10€ → {num(p['cuota'] * 10)}€"]
    if v + r:
        roi = 100 * gan / (10 * (v + r))
        lineas += ["", f"📊 Pick seguro: {v} ✅ · {r} ❌ · {'+' if roi >= 0 else ''}{roi:.0f} %".replace(".", ",")]
    lineas += ["", "🍀 Uno al día, sin locuras"]
    return "\n".join(lineas)


def texto_estrella(cp, cuota):
    """01/11 (Marcos): «partido estrella», solo texto (como «🇮🇹 NAPOLI 🆚 ROMA 🇮🇹», 5.643 visitas en Threads)."""
    band = BANDERA.get(cp.get("competicion"), "⚽")
    partido = f"{cp['local']}–{cp['visitante']}"
    lineas = [f"Hoy hay partidazo: {cp['local']} 🆚 {cp['visitante']} {band}⭐", "",
              f"Vamos con la combi del partido estrella ({cp['fecha'][11:16]}) 🔥", ""]
    for p in cp["picks"]:
        t = p["texto"].replace(f" en el {partido}", "").replace(f" del {partido}", "").replace(f" en {partido}", "")
        lineas.append(f"🍀 {t}")
    lineas += ["", f"📈 Cuota @{num(cuota)}", "", CIERRE_TELEGRAM]
    return "\n".join(lineas)


# 26/10: cierres que invitan a responder (las respuestas son lo que más mueve Threads). La pregunta de
# siempre ("¿la pintamos de verde?") rendía menos que no poner nada. Se rotan para no repetir.
CIERRES = ["👇 ¿Qué pata quitarías tú?",
           "👇 ¿La juegas tal cual o le cambias algo? Te leo",
           "👇 ¿Cuál es la que menos te convence?",
           "👇 Dime tu pick para hoy y lo miro con los datos",
           "👇 ¿Le meterías alguna pata más?"]
CIERRES_LISTA = ["👇 ¿Con cuáles 2 o 3 te quedas tú?",
                 "👇 ¿Cuál es tu favorita de la lista?",
                 "👇 Dime cuál falta y la miro con los datos"]


def cierre(dia, tipo, lista_=False):
    opciones = CIERRES_LISTA if lista_ else CIERRES
    return opciones[(sum(map(ord, dia + tipo))) % len(opciones)]


# 31/10 (Marcos): en los posts con muchos picks, que se sepa que no hay que cogerlos todos. Va la última:
# si en Threads no cabe, es lo primero que se quita (redes.threads)
POSTS_LISTA = ("ganadores", "combi-500")
# 05/11 (Marcos): nada de «@combilocas» en los textos: en Telegram ese @ lleva a OTRO canal
MUY_LARGA = 10   # picks a partir de los que se dice «coged los que más os gusten»
CIERRE_TELEGRAM = "🔔 Activad las notificaciones, que vienen más combis 👀"


def con_equipo(p):
    """05/11 (Marcos): los jugadores con su equipo: «Milot Avdyli (Sturm Graz): 1+ tiros»."""
    t, j, eq = p["texto"], p.get("jugador"), p.get("equipo")
    if not j or not eq or eq in t or j not in t:
        return t
    try:
        from ganadores_win import CORTO
        eq = CORTO.get(eq, eq)
    except Exception:
        pass
    return t.replace(j, f"{j} ({eq})", 1)   # 02/11: en picks para hoy/mañana ya lo dice la línea de combinar
def texto_multi(sel, cuota, nombre):
    """03/11: combi de 6-8 partidos con 1-2 cosas de cada uno. Si no cabe en Threads, se quita el último partido."""
    import math
    from collections import OrderedDict
    partidos = OrderedDict()
    for p in sel:
        partidos.setdefault(p["partido_id"], []).append(p)
    while True:
        lista = [p for l in partidos.values() for p in l]
        aprox = any(p.get("estimada") for p in lista)
        lineas = [f"🔥⚽ COMBILOCAS — ¡COMBI DE {len(partidos)} PARTIDOS {'≈' if aprox else ''}x{num(cuota)}! 🍀", ""]
        for l in partidos.values():
            lineas += [f"{bandera_pick(p)} {con_equipo(p)}" for p in l]
        # 05/11 (Marcos): sin la frase de «1 o 2 cosas de cada partido»; solo si es muy larga, que cojan lo que les guste
        if len(lista) >= MUY_LARGA:
            lineas += ["", "👉 ¡Coged los picks que más os gusten! ✅"]
        lineas += ["", CIERRE_TELEGRAM]
        texto = "\n".join(lineas)
        if len(texto) <= 495 or len(partidos) <= 5:
            return texto, lista
        ultimo = list(partidos)[-1]
        quitado = partidos.pop(ultimo)
        cuota = cuota / max(1.0, math.prod(p["cuota"] for p in quitado))


def texto_lista_europa(sel, i, n):
    """02/11: lista de 12-15 picks de Champions/Europa; la gente coge los que más le gusten."""
    from combis_dia import EUROPA
    comps = {p.get("liga_id") for p in sel}
    titulo = "CHAMPIONS" if comps == {2} else "EUROPA LEAGUE" if comps == {3} else "COPAS EUROPEAS"
    import re

    def corto_pick(t):   # para que quepan 12-15 en Threads (500)
        t = re.sub(r"Gol en la 1ª parte del .*", lambda m: "Gol 1ª parte " + m.group(0).split(" del ", 1)[1], t)
        t = re.sub(r"Gol en la 2ª parte del .*", lambda m: "Gol 2ª parte " + m.group(0).split(" del ", 1)[1], t)
        t = t.replace("Paris Saint Germain", "PSG").replace("Manchester United", "Man Utd").replace("Manchester City", "Man City")
        t = t.replace(" gana alguna de las dos partes", " gana una parte").replace(" comete 1+ faltas", ": 1+ falta")
        t = t.replace("tiros a puerta", "a puerta")
        return t
    while True:
        lineas = [f"🏆⚽ {titulo} · {len(sel)} PICKS PARA HOY 🍀" + (f" ({i}/{n})" if n > 1 else ""), ""]
        lineas += [f"{bandera_pick(p)} {corto_pick(con_equipo(p))}" for p in sel]
        lineas += ["", "👉 ¡Coge los que más te gusten! ✅", "", CIERRE_TELEGRAM]
        texto = "\n".join(lineas)
        if len(texto) <= 495 or len(sel) <= 10:
            return texto, sel
        sel = sel[:-1]


def combinar(sel):
    """02/11 (Marcos): «combina máximo 2 o 3» solo si hay 5 picks o más; con menos no tiene sentido."""
    return "⚽ ¡Combina máximo 2 o 3! ✅" if len(sel) >= 5 else "⚽ ¡Cógelos sueltos o combínalos! ✅"


LINEA_LISTA = ("ℹ️ No hace falta coger todos los picks: es info de los que hemos analizado entre todos "
               "los partidos. Quédate con los que más te gusten 👌")


# 11/11 (Marcos: «que especifique cuándo unas son para una cosa y otras por diversión»)
DIVERSION = ("combi-loca", "combi-partido", "estrella", "combi-multi", "lista-europa")
CON_CABEZA = ("pick-seguro", "combi-tres", "escalera", "combi-segura", "combi-doble", "combi-cuota_3")
ETIQUETA_DIVERSION = "🎉 Esta es por diversión: stake mínimo 🤏"
ETIQUETA_CABEZA = "🧠 Esta va con cabeza: analizada"
# 11/11 15:16 (Marcos: «eres muy repetitivo, no pongas "esta va con cabeza" en todas; a veces sí, a veces otra cosa,
# con datos, lo que sea, pero no siempre lo mismo»): la etiqueta cambia y no siempre sale.
ETIQUETAS_CABEZA = [
    ETIQUETA_CABEZA,
    "📊 Con datos detrás, nada de corazonadas",
    "🔎 Mirada a fondo: forma, bajas y cuotas",
    "📈 De las que hemos estudiado bien",
    "🧠 Pensada con calma, sin prisas",
    "📋 Números en la mano antes de meterla",
]
ETIQUETAS_DIVERSION = [
    ETIQUETA_DIVERSION,
    "🤪 Para soñar un poco: con poquito dinero",
    "🎲 De las locas: stake bajito 🤏",
    "🍿 Para darle emoción al día, con calma en el stake",
    "🎢 Cuota grande, stake pequeño 🤏",
]
SIN_ETIQUETA = {"cabeza": 0.5, "diversion": 0.25}   # la mitad de las «con cabeza» y 1 de cada 4 «por diversión», sin etiqueta
ES_ETIQUETA = tuple(x.split(":")[0][:14] for x in ETIQUETAS_CABEZA + ETIQUETAS_DIVERSION)


ORDEN_ETIQUETA = {"pick-seguro": 0, "pick-seguro-2": 1, "combi-tres": 2, "escalera": 3, "combi-segura": 4, "combi-doble": 5,
                  "combi-cuota_3": 5, "combi-loca": 0, "combi-partido": 1, "estrella": 2, "combi-multi": 3, "lista-europa": 4}


def etiqueta(clase, semilla):
    """La etiqueta de este post (o None). Semilla «AAAA-MM-DD-tipo»: dentro del mismo día cada tipo lleva una distinta
    y van alternando con y sin etiqueta; de un día a otro cambia el orden."""
    import hashlib
    import re as _re
    m = _re.match(r"(\d{4}-\d{2}-\d{2})-(.+)", str(semilla))
    dia, tipo = (m.group(1), m.group(2)) if m else ("", str(semilla))
    hd = int(hashlib.sha1(dia.encode()).hexdigest(), 16)
    off = ORDEN_ETIQUETA.get(tipo)
    if off is None:
        off = next((v for k, v in ORDEN_ETIQUETA.items() if tipo.startswith(k + "-")), None)
    if off is None:
        off = int(hashlib.sha1(tipo.encode()).hexdigest(), 16) % 97
    k = hd + off
    lista = ETIQUETAS_CABEZA if clase == "cabeza" else ETIQUETAS_DIVERSION
    if clase == "cabeza" and k % 2 == 0 or clase != "cabeza" and k % 4 == 0:
        return None
    return lista[(k // 2 if clase == "cabeza" else k) % len(lista)]


def etiquetar(tipo, texto, semilla=None):
    """Segunda línea del post: si es para ganar (con cabeza) o para echarse unas risas (diversión). Varía y a veces no va."""
    primera, _, resto = texto.partition("\n")
    if resto.lstrip().startswith(ES_ETIQUETA):
        return texto
    clase = "diversion" if tipo.startswith(DIVERSION) else "cabeza" if tipo.startswith(CON_CABEZA) else None
    if not clase:
        return texto
    et = etiqueta(clase, semilla or f"{tipo}|{primera}")
    if not et:
        return texto
    return f"{primera}\n{et}\n{resto}" if resto else f"{primera}\n{et}"


def posts_del_dia(dia, d):
    global FORMATO_27
    from bot import partidos_fuera
    fuera = partidos_fuera()
    if fuera and isinstance(d, dict):   # 08/11 (Marcos): partidos bloqueados en bet365, fuera de todo
        d = dict(d)
        for k in ("picks", "mejores_por_partido"):
            if isinstance(d.get(k), list):
                d[k] = [p for p in d[k] if not (isinstance(p, dict) and p.get("partido_id") in fuera)]
    FORMATO_27 = dia >= FORMATO_27_DESDE   # el 27 ya está hecho a mano (cola.json)
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    nombre = DIAS[f.weekday()]
    posts = []

    usos = {}   # cuántos posts llevan ya cada selección

    def apuntar(sel):
        for p in sel:
            usos[clave(p)] = usos.get(clave(p), 0) + 1

    combis = d.get("combis") or {}
    tarjetas = {}
    ids_noche = set()   # 03/11: las de madrugada no esperan a la alineación
    if FORMATO_27:
        # 27/10: el formato de ese martes (combis_dia.py): combi de cada partido con foto, x3 a las 13:30 y loca a las 16:00
        try:
            import combis_dia
            cd = combis_dia.del_dia(dia, guardar=True)
        except Exception as e:
            print("combis del día:", str(e)[:200])
            cd = {"partidos": []}
        noche_ids = {cp["picks"][0]["partido_id"] for cp, *_ in cd.get("noche") or []}
        for cp, cuota, tj, hora in cd["partidos"]:
            pid = f"combi-partido-{cp['picks'][0]['partido_id']}"
            if cp["picks"][0]["partido_id"] in noche_ids:   # 03/11: el mismo partido de madrugada y a su hora: ids distintos
                pid += "-2"
            tarjetas[pid] = tj
            posts.append((pid, hora, cp["picks"], texto_combi_partido(cp, tj, cuota)))
            apuntar(cp["picks"])   # 27/10: cuentan para el «máx. 2 posts por selección» (la lista de picks)
        for cp, cuota, tj, hora in cd.get("noche") or []:   # 28/10: prueba de combis de madrugada
            pid = f"combi-partido-{cp['picks'][0]['partido_id']}"
            ids_noche.add(pid)
            tarjetas[pid] = tj
            posts.append((pid, hora, cp["picks"], texto_combi_partido(cp, tj, cuota)))
            apuntar(cp["picks"])
        if cd.get("seguro"):   # 01/11 (Marcos): pick seguro del día (historial para el VIP)
            ps, hs = cd["seguro"]
            posts.append(("pick-seguro", hs, [ps], texto_seguro(ps, dia)))
            apuntar([ps])
        if cd.get("seguro2"):   # 09/11: el 2º de las 18:00
            ps, hs = cd["seguro2"]
            posts.append(("pick-seguro-2", hs, [ps], texto_seguro(ps, dia)))
            apuntar([ps])
        for i, (hora, sel) in enumerate(cd.get("listas_europa") or [], 1):   # 02/11 (Marcos): mucho contenido de Champions
            texto_l, sel = texto_lista_europa(sel, i, len(cd["listas_europa"]))   # sel recortado igual que el texto
            posts.append((f"lista-europa-{i}", hora, sel, texto_l))
        if cd.get("multi"):   # 03/11 (Marcos): 6-8 partidos con 1-2 cosas de cada uno, como las de él y sus colegas
            sel, cuota, hora = cd["multi"]
            texto_m, sel = texto_multi(sel, cuota, nombre)
            posts.append(("combi-multi", hora, sel, texto_m))
            apuntar(sel)
        for cp, cuota, hora in cd.get("estrella") or []:   # 01/11 (Marcos): partido estrella (top 4 de las 5 grandes)
            posts.append((f"estrella-{cp['partido_id']}", hora, cp["picks"], texto_estrella(cp, cuota)))
            try:   # 07/11 (Marcos: «en el partido del City no ha subido los escudos»): el estrella también con escudos
                b = cp["picks"][0]
                tarjetas[f"estrella-{cp['partido_id']}"] = datos_tarjeta(
                    dict({k: b.get(k) for k in ("local", "visitante", "fecha", "competicion")}, picks=cp["picks"]))
            except Exception as e:
                print("tarjeta estrella:", str(e)[:120])
            apuntar(cp["picks"])
        for clave_m, titulo in (("tres", "🔥⚽ COMBILOCAS — ¡COMBI DEL {n} x{c}! 🍀"), ("loca", "🤪🔥 COMBILOCAS — ¡LA LOCA DEL {n} x{c}! 🤪")):
            r = cd.get(clave_m)
            if r:
                sel, cuota, hora = r
                sel = sorted(sel, key=lambda p: p.get("fecha", ""))   # 02/11 (Marcos): siempre en orden de hora
                apuntar(sel)
                posts.append((f"combi-{clave_m}", hora, sel, combi(titulo.format(c=num(cuota), n=nombre), sel, cuota)))
        combis = {}   # las combis de antes (11:00, 12:00, 19:00, víspera…) ya no salen
    # 26/10: la cuota va en la primera línea (los títulos con número se veían el triple)
    for c_clave, hora, titulo in (("cuota_3", (11, 0), "🔥⚽ COMBILOCAS — ¡COMBI DEL {n} x{c}! 🍀"),
                                  ("segura", (12, 0), "🔒⚽ COMBILOCAS — ¡LA SEGURA DEL {n} x{c}! 🍀"),
                                  ("loca", (19, 0), "🤪🔥 COMBILOCAS — ¡LA LOCA DEL {n} x{c}! 🤪")):
        c = combis.get(c_clave)
        if not c:
            continue
        apuntar(c["picks"])
        titulo = titulo.format(c=num(c["cuota"]), n=nombre)
        posts.append((f"combi-{c_clave}", f.replace(hour=hora[0], minute=hora[1]), c["picks"],
                      combi(titulo, c["picks"], c["cuota"])))

    c = combis.get("doble")   # la víspera a las 21:30: "gana o empata" para mañana
    if c:
        apuntar(c["picks"])
        posts.append(("combi-doble", (f - timedelta(days=1)).replace(hour=21, minute=30), c["picks"],
                      combi(f"🛡️ COMBILOCAS — ¡GANA O EMPATA DEL {nombre} x{num(c['cuota'])}! 🛡️", c["picks"], c["cuota"])))

    if not FORMATO_27 and not any(v for k, v in combis.items() if k != "doble"):   # día flojo (pocos partidos): al menos una combi de 2
        cand = sorted(d.get("picks") or [], key=atractivo, reverse=True)
        par = next(([a, b] for i, a in enumerate(cand) for b in cand[i + 1:]
                    if a["partido_id"] != b["partido_id"] and a["cuota"] * b["cuota"] >= 1.5), None)
        if par:
            ct = par[0]["cuota"] * par[1]["cuota"]
            apuntar(par)
            posts.append(("combi-dia", f.replace(hour=12, minute=0), par,
                          combi(f"🔥⚽ COMBILOCAS — ¡LA COMBI DEL {nombre} x{num(ct)}! 🍀", par, ct)))

    cp = None if FORMATO_27 else combi_partido_grande(d)
    tarjeta = None
    if cp:
        cuota = cp.get("cuota_sumada")
        if not cuota:
            cuota = 1
            for p in cp["picks"]:
                cuota *= p["cuota"]
        inicio = datetime.fromisoformat(cp["fecha"]).replace(tzinfo=MADRID)
        apuntar(cp["picks"])
        tarjeta = datos_tarjeta(cp)
        # 50 min antes: ya están las alineaciones (salen ~1 h antes) y alineaciones_posts.py quita a quien no sea titular
        posts.append(("combi-partido", inicio - timedelta(minutes=50), cp["picks"], texto_combi_partido(cp, tarjeta, cuota)))

    esc = leer(DATOS / "escalera.json") or {}
    act = esc.get("actual")
    if act and act["dia"] == dia:
        ant = act.get("anterior")
        if ant and ant.get("resultado") == "anulada":   # 11/11: aplazado: bet365 devuelve, se repite el escalón
            intro_esc = f"🔵 El día {ant['escalon']} se anuló (partido aplazado): repetimos con {num(ant['stake'])}€"
        elif not ant or ant.get("resultado") != "verde":
            ayer = (f - timedelta(days=1)).strftime("%Y-%m-%d")
            cuando = "Ayer" if ant and ant.get("dia") == ayer else \
                f"El {DIAS[datetime.fromisoformat(ant['dia']).weekday()].lower()}" if ant else ""
            intro_esc = (f"❌ {cuando} se cayó el día {ant.get('escalon')}. Aquí no se borra nada: otra vez desde 20€ 💪"
                     if ant else "Empezamos con 20€ y subimos un escalón cada día 🚀")
        else:
            intro_esc = f"✅ Día {ant['escalon']} superado: {num(ant['stake'])}€ → {num(ant.get('retorno', ant['stake'] * ant['cuota']))}€"
        apuntar(act["picks"])
        from panel_datos import ajustes   # 30/10: hora de la escalera desde el panel
        h_esc, m_esc = (int(x) for x in (act.get("hora") or ajustes()["hora_escalera"]).split(":"))   # 29/10: si se prepara tarde, sale tarde
        posts.append(("escalera", f.replace(hour=h_esc, minute=m_esc), act["picks"],
                      f"🪜 Reto escalera · Día {act['escalon']}/7\n\n{intro_esc}\n\n"
                      f"{lista(act['picks'])}\n\n📈 Cuota @{num(act['cuota'])}\n"
                      f"💶 {num(act['stake'])}€ → {num(act['stake'] * act['cuota'])}€\n\n{CIERRE_TELEGRAM}"))

    # ---- estilos (26/10): tema del día, liga, la que nadie se atreve, de 1 € a 500 €
    est = {k: v for k, v in (d.get("estilos") or {}).items() if k == "500"} if FORMATO_27 else (d.get("estilos") or {})
    c = est.get("tema")
    if c:
        apuntar(c["picks"])
        posts.append(("combi-tema", f.replace(hour=13, minute=0), c["picks"],
                      combi(f"{c['titulo']} x{num(c['cuota'])}", c["picks"], c["cuota"])))
    c = est.get("liga")
    if c:
        apuntar(c["picks"])
        posts.append(("combi-liga", f.replace(hour=15, minute=0), c["picks"],
                      combi(f"{c['titulo']} DEL {nombre} x{num(c['cuota'])}", c["picks"], c["cuota"])))
    c = est.get("atreve")
    if c:
        apuntar(c["picks"])
        posts.append(("combi-atreve", f.replace(hour=16, minute=0), c["picks"],
                      combi(f"🔥 COMBILOCAS — ¡LA QUE NADIE SE ATREVE x{num(c['cuota'])}! 🔥", c["picks"], c["cuota"])))
    c = est.get("500")
    if c:
        posts.append(("combi-500", f.replace(hour=12, minute=0), c["picks"],   # 27/10: a las 12:00 (a las 13:30 va la x3)
                      combi(f"🧮 COMBILOCAS — ¡DE 1€ A 500€! x{num(c['cuota'])} 🧮", c["picks"], c["cuota"])))

    def libres(lista_picks):
        return [p for p in lista_picks if usos.get(clave(p), 0) < MAX_POSTS_POR_SELECCION]

    mejores = mejores_para_lista(libres(d.get("picks") or []))
    if len(mejores) < MIN_LISTA:
        # 29/10 (Marcos): si no llega porque los buenos ya van en otras combis, se completa repitiendo pocos
        # (solo los que falten para llegar al mínimo, de los más probables ya usados)
        ya = {clave(p) for p in mejores}
        extra = [p for p in mejores_para_lista(d.get("picks") or []) if clave(p) not in ya
                 and p["partido_id"] not in {q["partido_id"] for q in mejores}]
        mejores = mejores + extra[:MIN_LISTA - len(mejores)]
    if len(mejores) >= MIN_LISTA:
        sel = sorted(mejores[:7], key=lambda p: p.get("fecha", ""))   # 02/11: en orden de hora
        apuntar(sel)
        from panel_datos import ajustes   # 30/10: hora desde el panel
        hp, mp = (int(x) for x in ajustes()["hora_picks"].split(":"))
        posts.append(("picks-manana", (f - timedelta(days=1)).replace(hour=hp, minute=mp), sel,
                      f"🔥⚽ COMBILOCAS — ¡{len(sel)} PICKS PARA MAÑANA! 🍀\n\n{lista(sel)}\n\n"
                      f"{combinar(sel)}\n\n{CIERRE_TELEGRAM}"))
    tarde = [p for p in mejores_para_lista(libres(d.get("picks") or [])) if p["fecha"][11:] >= "18:30"]
    if len(tarde) >= MIN_LISTA and not FORMATO_27:
        sel = sorted(tarde[:7], key=lambda p: p.get("fecha", ""))   # 02/11: en orden de hora
        apuntar(sel)
        posts.append(("picks-hoy", f.replace(hour=17, minute=30), sel,
                      f"🔥⚽ COMBILOCAS — ¡{len(sel)} PICKS PARA HOY! 🍀\n\n{lista(sel)}\n\n"
                      f"{combinar(sel)}\n\n{CIERRE_TELEGRAM}"))

    # 26/10: el bot elige con datos cuáles de los estilos opcionales salen cada día (los 2 que mejor van
    # en vistas de Threads y en verdes, ver aprender.py → datos/estilos.json); el resto sale siempre
    opcionales = [t for t, *_ in posts if t in OPCIONALES]
    if len(opcionales) > MAX_OPCIONALES:
        nota = (leer(DATOS / "estilos.json") or {}).get("estilos", {})
        # a igual nota (al principio no hay datos) se rota por día para probar todos los estilos
        quedan = sorted(opcionales, key=lambda t: (-(nota.get(t) or {}).get("nota", 1.0),
                                                   sum(map(ord, dia + t)) % 7))[:MAX_OPCIONALES]
        posts = [x for x in posts if x[0] not in OPCIONALES or x[0] in quedan]

    # 26/10: un mismo partido en 2 combis como mucho (el 26/10 el Sevilla–Osasuna iba en 3 y, si sale raro,
    # caen todas a la vez). Mandan las que salen antes en la lista de arriba; la de 1€ a 500€ va aparte.
    en_combis, quedan_posts = {}, []
    # la escalera va primero y no se quita nunca: el reto sigue aunque no se publique
    posts = sorted(posts, key=lambda x: x[0] != "escalera")
    for x in posts:
        if x[0].startswith("combi-") or x[0] == "escalera":
            if x[0] != "combi-500":
                partidos = {p["partido_id"] for p in x[2]}
                if x[0] != "escalera" and any(en_combis.get(pid, 0) >= MAX_COMBIS_POR_PARTIDO for pid in partidos):
                    continue
                for pid in partidos:
                    en_combis[pid] = en_combis.get(pid, 0) + 1
        quedan_posts.append(x)
    posts = quedan_posts

    # 26/10: si una combi lleva justo lo mismo que la lista "para mañana" (días con pocos picks), en redes
    # parece un post repetido: se queda solo la lista, que es el formato que más se ve
    listas = [set(map(clave, pk)) for t, _, pk, _ in posts if t.startswith("picks-")]
    posts = [x for x in posts if x[0].startswith("picks-") or set(map(clave, x[2])) not in listas]

    # 26/10: posts de fútbol sin apuesta (rachas, xG, pichichis, previa del finde) → datos_futbol.py
    try:
        import datos_futbol
        if DATOS_ACTIVO:   # 27/10: Marcos quitó los posts que no son apuestas (rachas, pichichis, previas)
            posts += [(t, h, [], x) for t, h, x in datos_futbol.posts_del_dia(dia)]
        if GANADORES_ACTIVO:   # 27/10: «quién gana hoy» con nuestros datos (ganadores.py)
            import ganadores
            g = ganadores.post(dia)
            if g:
                posts.append((g[0], g[1], [], g[2]))
        # 02/11 (Marcos): «los picks de la semana» europea el lunes y su resultado el viernes (semana.py)
        try:
            import semana
            for x in (semana.post(dia), semana.resultado(dia)):
                if x:
                    posts.append(x)
        except Exception as e:
            print("semana europea:", str(e)[:150])
        if DATOS_ACTIVO and not any(t == "picks-manana" for t, *_ in posts):   # sin lista fiable: datos del día siguiente
            pv = datos_futbol.previa(dia)
            if pv:
                posts.append((pv[0], pv[1], [], pv[2]))
    except Exception as e:
        print("datos de fútbol:", str(e)[:150])

    salida = []
    import combis_dia as _cd
    for tipo, hora, picks, texto in posts:
        espera = False
        # 03/11 (Marcos): las combis con escudos y los estrellas con jugadores salen cuando hay alineación
        # (alineaciones_espera.py las publica en cuanto sale); como tarde, 35 min antes del partido
        if (tipo.startswith("combi-partido") or tipo.startswith("estrella")) and tipo not in ids_noche \
                and any(_cd.es_jugador(x) for x in picks):
            ini = min(datetime.fromisoformat(x["fecha"]).replace(tzinfo=MADRID) for x in picks)
            hora, espera = ini - timedelta(minutes=ESPERA_TOPE), True
        if any(es_sin_empate(p["mercado"], p["opcion"]) for p in picks):
            continue  # No eliminar patas de una combi conservando su cuota anterior.
        if picks and not espera:
            primero = min(datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID) for p in picks)
            hora = min(hora, primero - (timedelta(minutes=50) if tipo == "combi-partido" else MARGEN_ANTES_PARTIDO))
        texto = etiquetar(tipo, texto, f"{dia}-{tipo}")
        if tipo in POSTS_LISTA:   # 31/10 (Marcos): no hace falta coger todos los picks
            texto = texto.rstrip() + "\n\n" + LINEA_LISTA
        salida.append({"id": f"{dia}-{tipo}", "fecha": hora.strftime("%Y-%m-%dT%H:%M"),
                       "texto": texto, "foto": None, "origen": "analista", "directo": True,
                       "sel": ["|".join(map(str, clave(p))) for p in picks],
                       "cuotas": [p.get("cuota") for p in picks]})
        if espera:
            salida[-1]["espera_alineacion"] = True
        if tipo == "combi-partido" and tarjeta:
            salida[-1]["tarjeta"] = tarjeta
        if tipo in tarjetas and tarjetas[tipo]:
            salida[-1]["tarjeta"] = tarjetas[tipo]
    # 09/11 (Marcos): desde el 10/11, en Telegram solo los picks del día (1-2), la escalera y UNA combi guapa
    # (la del partido grande con escudos); lo demás sigue en Threads e Instagram
    import combis_dia as _c2
    if dia >= _c2.SEGURO_DESDE:
        def peso(p):
            t = p["id"][11:]
            return (0 if t.startswith("estrella") else 1 if t.startswith("combi-partido") and p.get("tarjeta") else 2,
                    p["fecha"])
        combis = sorted([p for p in salida if re.match(r"(estrella|combi-partido|combi-tres|combi-loca)", p["id"][11:])],
                        key=peso)
        en_tg = {f"{dia}-escalera", f"{dia}-pick-seguro", f"{dia}-pick-seguro-2"} | ({combis[0]["id"]} if combis else set())
        for p in salida:
            if p["id"] not in en_tg:
                p["solo_redes"] = True
    # 05/11 (Marcos): «GANADORES» con escudos cada día, solo en Threads (ganadores_win.py)
    try:
        import ganadores_win
        salida += ganadores_win.posts(dia)   # 07/11: uno a las 02:00 y otro a las 10:00 con otros partidos
    except Exception as e:
        print("ganadores win:", str(e)[:150])
    return salida


def balance(dia, posts_ayer):
    """Post de las 10:30 con cómo salió lo de ayer. Solo si ya está todo corregido."""
    reg = leer(REGISTRO, {}) or {}
    lineas, total, verdes = [], 0, 0
    nombres = {"combi-cuota_3": "Combi cuota 3", "combi-segura": "Combi de datos", "combi-loca": "Combi loca",
               "picks-manana": "Picks del día", "picks-hoy": "Picks de la tarde"}
    for p in posts_ayer:
        tipo = p["id"][11:]
        if tipo not in nombres:
            continue
        res = [reg.get(k, {}).get("acierto") for k in p.get("sel", [])]
        if not res or any(r is None for r in res):
            return None                      # falta algún resultado: aún no se publica
        a = sum(res)
        total, verdes = total + len(res), verdes + a
        if tipo.startswith("combi"):
            lineas.append(f"{'✅' if a == len(res) else '❌'} {nombres[tipo]}")
        else:
            lineas.append(f"{'✅' if a >= len(res) * 0.7 else '❌'} {nombres[tipo]}: {a}/{len(res)}")
    ayer = (datetime.fromisoformat(dia) - timedelta(days=1)).strftime("%Y-%m-%d")
    esc = leer(DATOS / "escalera.json") or {}
    h = next((x for x in reversed(esc.get("historial", [])) if x.get("dia") == ayer), None)
    if h and h.get("resultado"):
        lineas.append(f"{'✅' if h['resultado'] == 'verde' else '🔵' if h['resultado'] == 'anulada' else '❌'} "
                      f"Escalera día {h['escalon']}" + (" (anulada)" if h["resultado"] == "anulada" else ""))
    if not lineas:
        return None
    texto = "📋 ASÍ FUE AYER\n\n" + "\n".join(lineas)
    if total:
        texto += f"\n\n🎯 {verdes}/{total} selecciones acertadas"
    texto += "\n\nHoy seguimos 💪🍀"
    return {"id": f"{dia}-balance", "fecha": f"{dia}T10:30", "texto": texto, "foto": None,
            "origen": "analista", "directo": True, "sel": []}


def _primer_partido_escalera(dia):
    """Hora del primer partido del escalón de ese día ('' si no hay)."""
    act = (leer(DATOS / "escalera.json", {}) or {}).get("actual") or {}
    if act.get("dia") != dia:
        return ""
    return min((x["fecha"] for x in act.get("picks") or []), default="")


def main():
    picks = leer(DATOS / "picks.json")
    if not picks:
        print("Sin datos/picks.json")
        return
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    estados_redes = leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {}
    publicados = {pid for pid, estado in enviados.items() if estado.get("enviado")}
    publicados.update(pid for pid, estado in estados_redes.items()
                      if any((estado.get("redes") or {}).values()))
    anteriores = {p["id"]: p for p in (leer(AUTO, []) or [])}
    ahora = datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")

    # 26/10: a la hora de una combi cambiada a mano no sale otra combi automática (salían dos a las 12:00)
    horas_fijas = {p["fecha"] for p in anteriores.values() if p.get("fijo")}
    nuevos = {}
    # 09/11: en el parón picks.py no saca días (0 picks) y no salía nada, ni la escalera: también los días
    # con partidos en los datos, aunque no tengan picks (las combis salen del pool de bet365)
    dias = dict(picks["dias"])
    try:
        from escalera import dias_con_partidos
        for dia in dias_con_partidos():
            dias.setdefault(dia, {"picks": [], "mejores_por_partido": []})
    except Exception as e:
        print("dias_con_partidos falló:", e)
    hoy = ahora[:10]
    for dia, d in sorted(dias.items()):
        if dia < ESCALERA_DESDE:
            continue
        todos = posts_del_dia(dia, d)
        if dia < AUTO_DESDE:                 # hasta el lunes solo la escalera (lo demás está en Metricool)
            todos = [p for p in todos if p["id"].endswith("-escalera")]
        # 26/10: el balance va solo por la noche (resumen_dia.py); el de las 10:30 lo repetía
        for p in todos:
            if p["id"] in publicados:        # publicado en cualquier destino: conservar texto y selecciones
                continue
            if (anteriores.get(p["id"]) or {}).get("fijo"):   # cambiado a mano: no se regenera
                continue
            if "-combi-" in p["id"] and p["fecha"] in horas_fijas:
                continue
            if p["fecha"] <= ahora and p["id"] == f"{hoy}-escalera":
                # 09/11: la escalera sale todos los días: si su hora pasó sin salir y el partido no ha empezado,
                # sale en 10 minutos
                if _primer_partido_escalera(hoy) > ahora:
                    p["fecha"] = (datetime.now(MADRID) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M")
            if p["fecha"] <= ahora:          # su hora ya pasó sin publicarse
                continue
            # 09/11: femeninas: «Atletico Madrid W» → «Atletico Madrid (fem.)»
            p["texto"] = re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", p["texto"], flags=re.M)
            nuevos[p["id"]] = p
    # conservar los ya publicados para que quede registro, y los fijados a mano
    for pid, p in anteriores.items():
        if pid in publicados or (p.get("fijo") and p["fecha"] > ahora):
            nuevos.setdefault(pid, p)

    lista_final = sorted(nuevos.values(), key=lambda p: p["fecha"])
    AUTO.parent.mkdir(exist_ok=True)
    AUTO.write_text(json.dumps(lista_final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Posts automáticos en cola: {sum(1 for p in lista_final if p['id'] not in publicados)}")


if __name__ == "__main__":
    main()
