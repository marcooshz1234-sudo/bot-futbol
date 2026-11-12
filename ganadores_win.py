"""
05/11 (Marcos): el post «GANADORES» con escudos (plantilla oro de ganadores_img.py) funcionó muy bien en Threads
(44,5 mil visualizaciones). Lo hace el bot solo cada día, SOLO en Threads, a las 10:00:

- 8 favoritos claros del día (bet365 sin margen ≥ 55 %), ordenados por hora, con «WIN» (no «GANA»).
- Si una competición tiene 8 o más favoritos (Champions, Europa League, Conference, una liga…), el post es de esa
  competición, con su logo arriba si lo tenemos (publicaciones/media/escudos/liga-<id>.png) o su nombre en letras.
- Si no (p. ej. un viernes con uno o dos partidos por liga), se juntan todos: «PARTIDOS DE HOY».

Lo llama plantillas.posts_del_dia; la imagen la hace imagenes.py (tarjeta para Threads) con ganadores_img.py.
"""
from datetime import datetime, timedelta

from bot import EXTRA, MADRID, leer

HORA = (10, 0)
HORA_NOCHE = (2, 0)   # 07/11 (Marcos): uno de madrugada («a las 2») y otro por la mañana con OTROS partidos, todos los días
MIN_PROB, N, MIN_N = 0.55, 8, 6
MIN_PROB_POCOS = 0.40   # 05/11: el viernes 06/11 con 0,45 solo salían 4 y no había post
TITULOS = {525: "CHAMPIONS FEMENINA", 143: "COPA DEL REY", 5: "NATIONS LEAGUE", 2: "CHAMPIONS LEAGUE", 3: "EUROPA LEAGUE", 848: "CONFERENCE LEAGUE", 140: "LALIGA", 39: "PREMIER LEAGUE",
           135: "SERIE A", 78: "BUNDESLIGA", 61: "LIGUE 1", 94: "LIGA PORTUGAL", 88: "EREDIVISIE"}
PRIORIDAD = (5, 2, 3, 848, 140, 39, 135, 78, 61)
CORTO = {"Bayer Leverkusen": "Leverkusen", "AC Milan": "Milan", "NEC Nijmegen": "NEC", "HNK Hajduk Split": "Hajduk Split",
         "FC Lugano": "Lugano", "FC Copenhagen": "Copenhague", "Universitatea Craiova": "Univ. Craiova", "Monaco": "Mónaco",
         "FK Crvena Zvezda": "Estrella Roja", "SC Braga": "Braga", "Paris Saint Germain": "PSG", "Bayern München": "Bayern",
         "Atletico Madrid": "Atlético", "Borussia Dortmund": "Dortmund", "Manchester City": "Man City",
         "Manchester United": "Man United", "Inter": "Inter", "Real Betis": "Betis", "AS Roma": "Roma",
         "PSV Eindhoven": "PSV", "SC Freiburg": "Friburgo", "Sporting CP": "Sporting", "RB Leipzig": "Leipzig",
         "Hamburger SV": "Hamburgo", "Famalicao": "Famalicão", "Cordoba": "Córdoba", "VfB Stuttgart": "Stuttgart", "1899 Hoffenheim": "Hoffenheim", "AZ Alkmaar": "AZ", "Atletico Madrid": "Atlético", "Alaves": "Alavés", "Cadiz": "Cádiz", "Leganes": "Leganés", "Malaga": "Málaga", "Almeria": "Almería", "Atletico Madrid": "Atlético"}


def candidatos(dia, minimo=None, excluir=()):
    import picks as P
    from plantillas import GRANDES
    salida = []
    for f in EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido")
        if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
            continue
        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        if ini.strftime("%Y-%m-%d") != dia or pa["league"]["id"] not in P.COMPETICION and pa["league"]["id"] not in TITULOS:
            continue
        import combis_dia
        if combis_dia.fuera_por_dia_bueno(pa):   # 12/11: día bueno → nada de Segunda ni Copa de equipos pequeños
            continue
        mw = {o: float(c) for o, c in (ex.get("cuotas") or {}).get("Match Winner", [])}
        if not {"Home", "Away", "Draw"} <= set(mw):
            continue
        inv = {k: 1 / v for k, v in mw.items()}
        s = sum(inv.values())
        lado = max(("Home", "Away"), key=lambda k: inv[k])
        prob = inv[lado] / s
        from bot import partidos_fuera
        if prob < (MIN_PROB if minimo is None else minimo) or pa["fixture"]["id"] in excluir \
                or pa["fixture"]["id"] in partidos_fuera():
            continue
        eq = pa["teams"]["home" if lado == "Home" else "away"]
        grande = any(g in eq["name"].lower() for g in GRANDES)
        salida.append({"fid": pa["fixture"]["id"], "liga": pa["league"]["id"], "ini": ini, "lado": lado, "prob": prob,
                       "cuota": mw[lado], "equipo": eq, "grande": grande})
    return salida


# 11/11 05:26 (Marcos): varios «Partidos de hoy» por día, cada uno de UNA competición con su logo cuando se pueda.
# LaLiga y Premier fijas siempre que haya (00:00 y 01:00, Marcos 05:31); Champions, Europa League, Conference (y Nations League,
# Copa del Rey, Champions femenina) siempre que haya; luego las otras grandes, que van rotando de hora cada día; al
# final, «el resto» mezclado. Cada una a su hora (00:00, 01:00, 02:00, 09:00…), como mucho 10 filas.
FIJAS = (("laliga", {140}, 3), ("premier", {39}, 3), ("champions", {2}, 3), ("europa", {3}, 3), ("conference", {848}, 3), ("nations", {5}, 3),
         ("copa", {143}, 3), ("champions-fem", {525}, 3))
ROTAN = (("seriea", {135}, 4), ("bundesliga", {78}, 4), ("ligue1", {61}, 4))
HORAS = ((0, 0), (1, 0), (2, 0), (9, 0), (10, 0), (11, 0), (12, 0), (13, 0))
MAX_FILAS = 10
LLENAR = 8   # 12/11: las competiciones fijas se llenan hasta 8 filas si hay partidos


def grupos(dia, excluir=()):
    """[(clave, partidos)] del día en el orden en que salen."""
    c = candidatos(dia, excluir=excluir)
    rot = list(ROTAN)
    k = datetime.fromisoformat(dia).toordinal() % len(rot)
    rot = rot[k:] + rot[:k]   # cada día empieza otra liga grande
    salida, usados = [], set()
    for clave, ligas, minimo in FIJAS + tuple(rot):
        sel = [x for x in c if x["liga"] in ligas]
        if clave in ("laliga", "premier") and len(sel) < minimo:   # LaLiga y Premier, fijas: se baja un poco el listón
            sel = [x for x in candidatos(dia, 0.45, excluir) if x["liga"] in ligas]
        if (clave, ligas, minimo) in FIJAS and len(sel) < LLENAR:
            # 12/11 (Marcos: «tiene que haber 8-9»): en las fijas se completa con los favoritos más ajustados (≥ 40 %)
            sel = [x for x in candidatos(dia, MIN_PROB_POCOS, excluir) if x["liga"] in ligas]
        if len(sel) >= minimo:
            salida.append((clave, sel))
            usados |= {x["fid"] for x in sel}
    resto = [x for x in c if x["fid"] not in usados]
    if len(resto) < 4:
        resto = [x for x in candidatos(dia, MIN_PROB_POCOS, excluir) if x["fid"] not in usados]
    if len(resto) >= 4:
        salida.append(("resto", resto))
    return salida


def posts(dia):
    """Todos los «Partidos de hoy» del día (ver arriba). Lo subido a mano para ese día no se repite."""
    import json
    from bot import DATOS
    usados = set()
    try:
        cola = json.loads((DATOS.parent / "publicaciones" / "cola.json").read_text())
        for x in cola:
            if x.get("id", "").startswith(f"{dia}-ganadores-win"):
                usados |= {int(s.split("|")[0]) for s in x.get("sel", [])}
    except Exception:
        pass
    salida = []
    for i, (clave, sel) in enumerate(grupos(dia, usados)):
        from plantillas import LEMAS, lema as _lema
        primero = LEMAS.index(_lema(dia))   # 12/11: cada post del día con una frase distinta
        p = post(dia, hora=HORAS[min(i, len(HORAS) - 1)], sufijo=clave, sel=sel, frase=LEMAS[(primero + i) % len(LEMAS)])
        if p:
            salida.append(p)
    return salida


def post(dia, hora=HORA, excluir=(), sufijo="", sel=None, frase=None):
    """Dict de post para la cola (o None). Con sel: esos partidos (un grupo de grupos())."""
    import semana
    if sel is None:   # el de antes: una liga con 8+ favoritos o todos juntos
        c = candidatos(dia, excluir=excluir)
        por_liga = {}
        for x in c:
            por_liga.setdefault(x["liga"], []).append(x)
        llenas = [l for l, v in por_liga.items() if len(v) >= N]
        if llenas:
            liga = max(llenas, key=lambda l: (len(por_liga[l]), -PRIORIDAD.index(l) if l in PRIORIDAD else -99))
            sel = por_liga[liga]
        else:
            sel = c
            if len(sel) < MIN_N:   # 05/11 (Marcos): días con pocos partidos (viernes) → todos juntos
                sel = candidatos(dia, MIN_PROB_POCOS, excluir)
        if len(sel) < (MIN_N if llenas else 5):
            return None
        sufijo = "win" + sufijo
    if not sel:
        return None
    ligas = {x["liga"] for x in sel}
    liga = ligas.pop() if len(ligas) == 1 else None
    titulo = (TITULOS.get(liga) if liga else None) or "PARTIDOS DE HOY"
    sel = sorted(sel, key=lambda x: -(x["prob"] + (0.06 if x["grande"] else 0)))[:MAX_FILAS]   # los grandes llaman más
    sel.sort(key=lambda x: (x["ini"], x["equipo"]["name"]))
    filas, lineas = [], []
    for i, x in enumerate(sel, 1):
        n = x["equipo"]["name"]
        pais = semana.pais_equipo(n)
        if pais in (None, "World") and n.endswith(" W"):   # 11/11: femeninos → el país del club (Lyon W → Francia)
            pais = semana.pais_equipo(n[:-2]) or pais
        bandera = semana.BANDERAS.get(pais, "⚽")
        from combis_dia import nombre_es
        nombre = CORTO.get(n, nombre_es(n))
        seleccion = semana.SELECCIONES.get(n, n) in semana.BANDERAS   # 11/11: selección → solo su bandera, sin escudo
        filas.append({"pais": pais, "bandera": bandera, "escudo_url": x["equipo"].get("logo"), "nombre": nombre, "pick": "WIN",
                      "seleccion": seleccion})
        lineas.append(f"{i}. {bandera} {nombre} - Win")
    from plantillas import lema as _lema
    frase = frase or _lema(f"{dia}-ganadores-{sufijo}")   # 12/11 (Marcos): no siempre «¿LA PINTAMOS DE VERDE?»
    texto = f"🏆 {titulo} - GANADORES\n\n" + "\n".join(lineas) + f"\n\n🍀 {frase} 👀💚"
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID, hour=hora[0], minute=hora[1])
    f = min(f, sel[0]["ini"] - timedelta(hours=1))
    return {"id": f"{dia}-ganadores-{sufijo}", "fecha": f.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
            "origen": "analista", "directo": True, "solo_redes": True, "forzar": True,   # 11/11: también a Instagram (reel)
            "sel": [f"{x['fid']}|Match Winner|{x['lado']}" for x in sel], "cuotas": [x["cuota"] for x in sel],
            "ganadores_img": {"titulo": titulo, "liga": liga, "filas": filas, "lema": frase}}


def datos_imagen(p):
    """(filas con la ruta del escudo, ruta del logo de la competición o None) del post."""
    import ganadores_img as G
    from pathlib import Path
    from imagenes import MEDIA, escudo
    g = p["ganadores_img"]
    filas = []
    for f in g["filas"]:
        ruta = None
        if f.get("escudo_url"):
            escudo(f["escudo_url"], f["nombre"])   # lo descarga y lo deja en publicaciones/media/escudos
            c = MEDIA / "escudos" / Path(f["escudo_url"]).name
            ruta = str(c) if c.exists() else None
        filas.append(dict(f, escudo=ruta or ""))
    liga = None
    if g.get("liga"):
        liga = G.logo_liga(g["liga"])   # 12/11: con el HD si lo hay
    return filas, liga


def hacer_imagen(p):
    """Tarjeta de Threads (publicaciones/media/<id>.tarjeta.jpg). 11/11: plantilla «estadio» (logo nuevo)."""
    import ganadores_img as G
    from imagenes import MEDIA
    filas, liga = datos_imagen(p)
    return G.generar(filas, p["ganadores_img"]["titulo"], MEDIA / f"{p['id']}.tarjeta.jpg", "estadio", liga=liga,
                     lema=p["ganadores_img"].get("lema"))
