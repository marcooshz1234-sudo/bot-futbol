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
TITULOS = {5: "NATIONS LEAGUE", 2: "CHAMPIONS LEAGUE", 3: "EUROPA LEAGUE", 848: "CONFERENCE LEAGUE", 140: "LALIGA", 39: "PREMIER LEAGUE",
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


def posts(dia):
    """07/11: los dos del día: madrugada (02:00) y mañana (10:00) sin repetir partidos."""
    import json
    from bot import DATOS
    salida = []
    p1 = post(dia, hora=HORA_NOCHE)
    try:   # si el de madrugada ya está en la cola (subido a mano), cuentan sus partidos
        cola = json.loads((DATOS.parent / "publicaciones" / "cola.json").read_text())
        p1 = next((x for x in cola if x.get("id") == f"{dia}-ganadores-win"), None) or p1
    except Exception:
        pass
    if p1:
        salida.append(p1)
    usados = {int(x.split("|")[0]) for x in (p1 or {}).get("sel", [])}
    p2 = post(dia, hora=HORA, excluir=usados, sufijo="-2")
    if p2:
        salida.append(p2)
    return salida


def post(dia, hora=HORA, excluir=(), sufijo=""):
    """Dict de post para la cola (o None)."""
    import semana
    c = candidatos(dia, excluir=excluir)
    por_liga = {}
    for x in c:
        por_liga.setdefault(x["liga"], []).append(x)
    llenas = [l for l, v in por_liga.items() if len(v) >= N]
    if llenas:
        liga = max(llenas, key=lambda l: (len(por_liga[l]), -PRIORIDAD.index(l) if l in PRIORIDAD else -99))
        sel, titulo = por_liga[liga], TITULOS.get(liga) or ""
    else:
        liga, sel, titulo = None, c, "PARTIDOS DE HOY"
        if len(sel) < MIN_N:   # 05/11 (Marcos): días con pocos partidos (viernes) → todos juntos, el favorito de cada uno
            sel = candidatos(dia, MIN_PROB_POCOS, excluir)
    if len(sel) < (MIN_N if llenas else 5) or not titulo:
        return None
    sel = sorted(sel, key=lambda x: -(x["prob"] + (0.06 if x["grande"] else 0)))[:N]   # los grandes llaman más
    sel.sort(key=lambda x: (x["ini"], x["equipo"]["name"]))
    filas, lineas = [], []
    for i, x in enumerate(sel, 1):
        n = x["equipo"]["name"]
        pais = semana.pais_equipo(n)
        bandera = semana.BANDERAS.get(pais, "⚽")
        nombre = CORTO.get(n, n)
        filas.append({"pais": pais, "bandera": bandera, "escudo_url": x["equipo"].get("logo"), "nombre": nombre, "pick": "WIN"})
        lineas.append(f"{i}. {bandera} {nombre} - Win")
    texto = f"🏆 {titulo} - GANADORES\n\n" + "\n".join(lineas) + "\n\n🍀 ¿LA PINTAMOS DE VERDE? 👀💚"
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID, hour=hora[0], minute=hora[1])
    f = min(f, sel[0]["ini"] - timedelta(hours=1))
    return {"id": f"{dia}-ganadores-win{sufijo}", "fecha": f.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
            "origen": "analista", "directo": True, "solo_redes": True, "sin_instagram": True, "forzar": True,
            "sel": [f"{x['fid']}|Match Winner|{x['lado']}" for x in sel], "cuotas": [x["cuota"] for x in sel],
            "ganadores_img": {"titulo": titulo, "liga": liga, "filas": filas}}


def hacer_imagen(p):
    """Tarjeta de Threads (publicaciones/media/<id>.tarjeta.jpg) con la plantilla oro."""
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
        l = MEDIA / "escudos" / f"liga-{g['liga']}.png"
        liga = str(l) if l.exists() else G.logo_liga(g["liga"])
    return G.generar(filas, g["titulo"], MEDIA / f"{p['id']}.tarjeta.jpg", "oro", liga=liga)
