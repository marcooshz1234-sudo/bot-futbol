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

AUTO = RAIZ / "publicaciones" / "auto.json"
AUTO_DESDE = "2026-10-26"                       # días anteriores ya estaban programados en Metricool
ESCALERA_DESDE = "2026-10-24"                   # la escalera ya sale sola desde el sábado
REGISTRO = DATOS / "registro_aciertos.json"
MARGEN_ANTES_PARTIDO = timedelta(minutes=60)
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]


def num(c):
    return f"{c:.2f}".replace(".", ",")


def lista(picks):
    """27/10: como los posts que más gustaron: una línea por selección con la bandera, sin cuota por pata
    ni números (la cuota de cada pata va en el post como dato aparte: "cuotas")."""
    return "\n".join(f"✅ {BANDERA.get(p.get('competicion'), '⚽')} {p['texto']}" for p in picks)


VERDE = "🍀 ¿LA PINTAMOS DE VERDE? 👀💚"
FORMATO_27 = True          # el formato del martes 27/10 (combis_dia.py)
FORMATO_27_DESDE = "2026-10-28"   # poner "9999" para volver al de antes
GANADORES_ACTIVO = True
DATOS_ACTIVO = False       # posts de fútbol sin apuesta (datos_futbol.py): quitados por Marcos el 27/10    # «quién gana hoy» (activado por Marcos el 27/10)   # el cierre de los posts con más likes


def combi(titulo, picks, cuota):
    """Post de combi corto: título, selecciones, cuota y cierre. Nada más (27/10: menos texto = más likes)."""
    return f"{titulo}\n\n{lista(picks)}\n\n🎯 CUOTA {num(cuota)} 💎\n\n{VERDE}"


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
           "Coppa Italia": "🇮🇹", "DFB-Pokal": "🇩🇪", "Coupe de France": "🇫🇷", "Taça de Portugal": "🇵🇹", "KNVB Beker": "🇳🇱"}
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
    lineas = [f"✅ COMBI LOCAS | {liga}", f"{band} {cp['local'].upper()} vs {cp['visitante'].upper()} {band}", ""]
    partido = f"{cp['local']}–{cp['visitante']}"
    for i, p in enumerate(cp["picks"]):
        t = p["texto"].replace(f" en el {partido}", "").replace(f" del {partido}", "").replace(f" en {partido}", "")
        lineas.append(f"{'🎯' if i == 0 else '✅'} {t.upper()} [x{p['cuota']:.2f}]")
    rp = resultados_probables(cp, tj) if tj else []
    lineas.append("")
    if rp:
        lineas.append(f"🔥 Resultado probable: {' | '.join(rp)}")
    lineas += [f"💥 Cuota total aprox.: {num(cuota)}", "🟢 VERDE A VERDE 🟢"]
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


def posts_del_dia(dia, d):
    global FORMATO_27
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
    if FORMATO_27:
        # 27/10: el formato de ese martes (combis_dia.py): combi de cada partido con foto, x3 a las 13:30 y loca a las 16:00
        try:
            import combis_dia
            cd = combis_dia.del_dia(dia)
        except Exception as e:
            print("combis del día:", str(e)[:200])
            cd = {"partidos": []}
        for cp, cuota, tj, hora in cd["partidos"]:
            pid = f"combi-partido-{cp['picks'][0]['partido_id']}"
            tarjetas[pid] = tj
            posts.append((pid, hora, cp["picks"], texto_combi_partido(cp, tj, cuota)))
            apuntar(cp["picks"])   # 27/10: cuentan para el «máx. 2 posts por selección» (la lista de picks)
        for cp, cuota, tj, hora in cd.get("noche") or []:   # 28/10: prueba de combis de madrugada
            pid = f"combi-partido-{cp['picks'][0]['partido_id']}"
            tarjetas[pid] = tj
            posts.append((pid, hora, cp["picks"], texto_combi_partido(cp, tj, cuota)))
            apuntar(cp["picks"])
        for clave_m, titulo in (("tres", "🔥⚽ COMBILOCAS — ¡COMBI DEL {n} x{c}! 🍀"), ("loca", "🤪🔥 COMBILOCAS — ¡LA LOCA DEL {n} x{c}! 🤪")):
            r = cd.get(clave_m)
            if r:
                sel, cuota, hora = r
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
        if not ant or ant.get("resultado") != "verde":
            ayer = (f - timedelta(days=1)).strftime("%Y-%m-%d")
            cuando = "Ayer" if ant and ant.get("dia") == ayer else \
                f"El {DIAS[datetime.fromisoformat(ant['dia']).weekday()].lower()}" if ant else ""
            intro = (f"❌ {cuando} se cayó el día {ant.get('escalon')}. Aquí no se borra nada: otra vez desde 20€ 💪"
                     if ant else "Empezamos con 20€ y subimos un escalón cada día 🚀")
        else:
            intro = f"✅ Día {ant['escalon']} superado: {num(ant['stake'])}€ → {num(ant.get('retorno', ant['stake'] * ant['cuota']))}€"
        apuntar(act["picks"])
        posts.append(("escalera", f.replace(hour=11, minute=0), act["picks"],
                      f"🪜 RETO ESCALERA · DÍA {act['escalon']}/7 · x{num(act['cuota'])} 🍀\n\n{intro}\n\n"
                      f"{lista(act['picks'])}\n\n🎯 CUOTA {num(act['cuota'])} 💎 · "
                      f"{num(act['stake'])}€ → {num(act['stake'] * act['cuota'])}€\n\n{VERDE}"))

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
        sel = mejores[:7]
        apuntar(sel)
        posts.append(("picks-manana", (f - timedelta(days=1)).replace(hour=23, minute=0), sel,
                      f"🔥⚽ COMBILOCAS — ¡{len(sel)} PICKS PARA MAÑANA! 🍀\n\n{lista(sel)}\n\n"
                      "⚽ ¡Combina máximo 2 o 3! ✅\n\n💚 Más picks GRATIS en @combilocas"))
    tarde = [p for p in mejores_para_lista(libres(d.get("picks") or [])) if p["fecha"][11:] >= "18:30"]
    if len(tarde) >= MIN_LISTA and not FORMATO_27:
        sel = tarde[:7]
        apuntar(sel)
        posts.append(("picks-hoy", f.replace(hour=17, minute=30), sel,
                      f"🔥⚽ COMBILOCAS — ¡{len(sel)} PICKS PARA HOY! 🍀\n\n{lista(sel)}\n\n"
                      "⚽ ¡Combina máximo 2 o 3! ✅\n\n💚 Más picks GRATIS en @combilocas"))

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
        if DATOS_ACTIVO and not any(t == "picks-manana" for t, *_ in posts):   # sin lista fiable: datos del día siguiente
            pv = datos_futbol.previa(dia)
            if pv:
                posts.append((pv[0], pv[1], [], pv[2]))
    except Exception as e:
        print("datos de fútbol:", str(e)[:150])

    salida = []
    for tipo, hora, picks, texto in posts:
        if any(es_sin_empate(p["mercado"], p["opcion"]) for p in picks):
            continue  # No eliminar patas de una combi conservando su cuota anterior.
        if picks:
            primero = min(datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID) for p in picks)
            hora = min(hora, primero - (timedelta(minutes=50) if tipo == "combi-partido" else MARGEN_ANTES_PARTIDO))
        salida.append({"id": f"{dia}-{tipo}", "fecha": hora.strftime("%Y-%m-%dT%H:%M"),
                       "texto": texto, "foto": None, "origen": "analista", "directo": True,
                       "sel": ["|".join(map(str, clave(p))) for p in picks],
                       "cuotas": [p.get("cuota") for p in picks]})
        if tipo == "combi-partido" and tarjeta:
            salida[-1]["tarjeta"] = tarjeta
        if tipo in tarjetas and tarjetas[tipo]:
            salida[-1]["tarjeta"] = tarjetas[tipo]
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
        lineas.append(f"{'✅' if h['resultado'] == 'verde' else '❌'} Escalera día {h['escalon']}")
    if not lineas:
        return None
    texto = "📋 ASÍ FUE AYER\n\n" + "\n".join(lineas)
    if total:
        texto += f"\n\n🎯 {verdes}/{total} selecciones acertadas"
    texto += "\n\nHoy seguimos 💪🍀"
    return {"id": f"{dia}-balance", "fecha": f"{dia}T10:30", "texto": texto, "foto": None,
            "origen": "analista", "directo": True, "sel": []}


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
    for dia, d in picks["dias"].items():
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
            if p["fecha"] <= ahora:          # su hora ya pasó sin publicarse
                continue
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
