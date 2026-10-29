"""
Combis del día con el formato que pidió Marcos el 27/10 (las de ese martes son el modelo):

1. COMBI DE CADA PARTIDO («✅ COMBI LOCAS | LIGA», con la foto del partido): una por partido, de 4 a 6
   selecciones (28/10: bet365 solo deja 6 mercados por partido en «Crear apuesta») de ESE partido, cuota total entre 7 y 10, cada pata ≥ 1,25 y con ≥ 45 % de probabilidad.
   Se elige la que más devuelve a la larga (probabilidad de que salga × cuota). Las patas de resultado
   van todas a favor del mismo equipo y tiene que existir algún marcador que las cumpla todas.
   Partidos: primero los de equipos grandes, luego los demás; entre 5 y 8 al día (los que haya).
   Hora: 50 min antes del partido; si coinciden, cada 30 min hacia atrás.
2. COMBI x3 (13:30) y LA LOCA (16:00), con el mejor pick de cada partido del día (≥ 60 %, cuota ≥ 1,25):
   x3 = 2-4 patas entre 2,5 y 4 · loca = 4-7 patas entre 7 y 10. Solo partidos que empiezan después.

Datos: los dos equipos con al menos 5 partidos; en copa contra uno de categoría que no seguimos, solo
mercados de nuestro equipo (con sus datos). Probabilidad = la aprendida (aprender.py).
"""
import itertools
import math
from datetime import datetime, timedelta

from bot import EXTRA, MADRID, leer

CUOTA_MIN_PATA = 1.25
PARTIDO = {"patas": (6, 6), "cuota": (7.0, 10.0), "prob_min": 0.45, "max": 8}   # 29/10 (Marcos): 6 cosas (bet365 no deja más de 6)   # cuota REAL de bet365
# 28/10 (Marcos, prueba de una semana): 2 combis de partido extra de madrugada (00:30 y 01:30) con los partidos grandes
# del día que no tienen combi a su hora; más cortas si hace falta. La del City a la 01:30 hizo 4,8 mil vistas.
NOCHE = {"horas": ((0, 30), (1, 30)), "patas": (6, 6), "cuota": (7.0, 10.0), "hasta": "2026-11-04"}   # 29/10: también 7-10 y 6 cosas
# 27/10: en «Crear apuesta» bet365 paga menos que multiplicar, según lo relacionadas que estén las patas.
# Medido en bet365: Monza–Napoli (McTominay 2+ remates, gol 1ª parte, Napoli gana alguna mitad, Varela 1+ a
# puerta, Napoli más remates a puerta) multiplica 5,36 y paga 4,60 (0,86); Milan (Ramos marca + Pulisic
# asiste + gana el Milan) multiplica 16,0 y paga 8,50 (0,53); Monza–Napoli (McTominay 2+ remates, Varela 1+
# a puerta, Monza marca, Monza +3 córners, +28,5 remates) multiplica 9,46 y paga 6,00 (0,63). Por eso ya no es un factor fijo: va por parejas.
PROB_MIN_RELAJADA = 0.35   # 29/10 (Marcos): cuota 7-10 siempre; si no sale, patas desde el 35 %
FACTOR_MIN = 0.45
TRES = {"patas": (2, 4), "cuota": (2.5, 4.0), "hora": (13, 30)}
LOCA = {"patas": (4, 7), "cuota": (7.0, 10.0), "hora": (16, 0)}
PROB_MIN_MULTI = 0.60
RESULTADO = ("Match Winner", "Double Chance", "To Win Either Half", "First Half Winner", "Win Both Halves")


TIROS_FREC = {"tiros": 0.75, "a_puerta": 0.70}
TIROS_MEDIA = {"tiros": 0.3, "a_puerta": 0.0}   # media de los últimos partidos ≥ línea + esto


def tiros_jugadores(ex, hist, base, lok, vok):
    """27/10 (Marcos): tiros de jugadores que tiran siempre, sin exigir valor (se busca lo que va a pasar).
    Titulares fijos, que lo cumplan en ≥ 75 % (a puerta ≥ 70 %), con media por encima de la línea y cuyo
    equipo no sea muy inferior (cuota de ganar < 5)."""
    import picks as P
    cuotas = ex.get("cuotas") or {}
    ganar = {str(o): float(c) for o, c in cuotas.get("Match Winner") or [] if c}
    loc, vis = ex["partido"]["teams"]["home"], ex["partido"]["teams"]["away"]
    fijos = {"home": P.plantilla_fija(loc["id"], hist) if lok else {}, "away": P.plantilla_fija(vis["id"], hist) if vok else {}}
    salida = {}
    for mercado, opciones in cuotas.items():
        campo = (P.JUG_MERCADOS.get(mercado) or (None,))[0]
        if campo not in ("tiros", "a_puerta"):
            continue
        lados = ["home"] if mercado.startswith("Home") else ["away"] if mercado.startswith("Away") else ["home", "away"]
        for valor, cuota in opciones:
            try:
                cuota = float(cuota)
                nombre, n = str(valor).rsplit(" - ", 1)
                n = int(float(n))
            except (TypeError, ValueError):
                continue
            if cuota < CUOTA_MIN_PATA or cuota > 2.5:
                continue
            for ld in lados:
                if ganar.get("Home" if ld == "home" else "Away", 0) >= 5.0:   # solo fuera los muy inferiores
                    continue
                jug = next(((pid, d) for pid, d in fijos[ld].items() if P.mismo_jugador(nombre, d["nombre"])), None)
                if not jug or len(jug[1]["partidos"]) < P.MIN_PARTIDOS:
                    continue
                regs = jug[1]["partidos"]
                si = sum(1 for r in regs if (r.get(campo) or 0) >= n)
                media = sum(r.get(campo) or 0 for r in regs) / len(regs)
                if si / len(regs) < TIROS_FREC[campo] or media < n + TIROS_MEDIA[campo]:
                    continue
                equipo = loc["name"] if ld == "home" else vis["name"]
                p = dict(base, mercado=mercado, opcion=valor, cuota=cuota, frecuencia=round(si / len(regs), 3),
                         ventaja=round(si / len(regs) - 1 / cuota, 3), tipo="jugador", jugador=nombre.strip(),
                         equipo=equipo, jugador_id=jug[0], campo=campo, n=n,
                         texto=(f"{nombre.strip()}: {n}+ tiros a puerta" if campo == "a_puerta" else f"{nombre.strip()}: {n}+ tiros"),
                         detalle=f"{nombre.strip()} {si}/{len(regs)}")
                k = (nombre.strip(), campo)
                if k not in salida or (p["frecuencia"], cuota) > (salida[k]["frecuencia"], salida[k]["cuota"]):
                    salida[k] = p
                break
    return list(salida.values())


def pool_partido(ex, hist, ap):
    """Picks posibles de un partido con su probabilidad aprendida. [] si no hay datos."""
    import aprender
    import picks as P
    pa = ex.get("partido")
    if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
        return []
    loc, vis = pa["teams"]["home"], pa["teams"]["away"]
    h_loc = [(p, loc["id"]) for p in hist.get(loc["id"], [])[:P.ULTIMOS]]
    h_vis = [(p, vis["id"]) for p in hist.get(vis["id"], [])[:P.ULTIMOS]]
    lok, vok = len(h_loc) >= P.MIN_PARTIDOS, len(h_vis) >= P.MIN_PARTIDOS
    if not (lok or vok) or (not (lok and vok) and pa["league"]["id"] not in P.COPAS):
        return []
    inicio = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
    base = {"partido_id": pa["fixture"]["id"], "fecha": inicio.strftime("%Y-%m-%dT%H:%M"),
            "competicion": P.COMPETICION.get(pa["league"]["id"], pa["league"]["name"]), "liga_id": pa["league"]["id"],
            "local": loc["name"], "visitante": vis["name"]}
    pool = []
    for m, ops in (ex.get("cuotas") or {}).items():
        if m in P.JUG_MERCADOS:
            continue
        for o, c in ops:
            try:
                c = float(c)
            except (TypeError, ValueError):
                continue
            if c < CUOTA_MIN_PATA or c > 3.0 or P.excluido(m, o) or str(o).startswith("Under") or o == "No" \
                    or P.es_sin_empate(m, o):
                continue
            if lok and vok:
                fl, fv = P.evaluador(m, o, True), P.evaluador(m, o, False)
                if not fl:
                    continue
                a, na = P.frecuencia(fl, h_loc)
                b, nb = P.frecuencia(fv, h_vis)
                if na < P.MIN_PARTIDOS or nb < P.MIN_PARTIDOS or min(a / na, b / nb) < 0.4:
                    continue
                frec, det = (a + b) / (na + nb), f"{loc['name']} {a}/{na} · {vis['name']} {b}/{nb}"
            else:   # copa contra uno de abajo: solo lo de nuestro equipo
                if P.lado_pick({"mercado": m, "opcion": o}) != ("local" if lok else "visitante"):
                    continue
                fn = P.evaluador(m, o, lok)
                if not fn:
                    continue
                a, na = P.frecuencia(fn, h_loc if lok else h_vis)
                if na < P.MIN_PARTIDOS:
                    continue
                frec, det = a / na, f"{loc['name'] if lok else vis['name']} {a}/{na}"
            if frec < 0.5:
                continue
            p = dict(base, mercado=m, opcion=o, tipo=P.tipo_de(m), texto=P.texto_pick(m, o, loc["name"], vis["name"]),
                     cuota=c, frecuencia=round(frec, 3), ventaja=round(frec - 1 / c, 3), detalle=det)
            pool.append(p)
    pool += tiros_jugadores(ex, hist, base, lok, vok)
    for p in P.picks_jugadores(ex, hist, base, frec_min=0.6):
        if p.get("campo") in ("tiros", "a_puerta"):
            continue   # los tiros van por tiros_jugadores (sin exigir que paguen de más)
        if p.get("campo") == "amarillas":
            continue
        # 27/10 (Marcos): falta de jugador solo si la hace SIEMPRE (9 de 10 o más) y solo 1+
        if p.get("campo") == "faltas_c" and (p.get("n", 1) > 1 or p["frecuencia"] < 0.9):
            continue
        if p["cuota"] >= CUOTA_MIN_PATA and ((lok and vok) or p.get("equipo") == (loc["name"] if lok else vis["name"])):
            pool.append(p)
    import goles_partido as G
    import modelo_goles as M
    lam = M.lambdas(pa["fixture"]["id"])
    gana = favorito(ex)
    for p in pool:
        p["prob_aprendida"] = aprender.prob_aprendida(p, ap) or p["frecuencia"]
        # 28/10 (Marcos): en los picks de goles manda también lo que dice bet365 y lo que pasó en partidos
        # del mismo tipo (goles_partido.py), no solo la racha (Parma–Udinese +1,5 acabó 0-0)
        g = G.prob_goles(p, hist, lam, loc["id"], vis["id"])
        if g:
            p["prob_aprendida"], p["prob_bet365"], p["prob_tipo"] = g["prob"], g["bet365"], g["tipo"]
    # 28/10 (Marcos): «gana alguna de las dos partes» acertó 3 de 8: solo para el favorito claro de bet365
    pool = [p for p in pool if not (p["mercado"] == "To Win Either Half" and gana.get(p["opcion"], 0) < FAVORITO_MIN)]
    # 28/10: los tiros a puerta del partido acertaron 1 de 4: solo muy respaldados
    pool = [p for p in pool if not (p["mercado"] == "Total ShotOnGoal" and p["prob_aprendida"] < PROB_MIN_A_PUERTA)]
    # 28/10 (Marcos): +1,5 goles solo si los tres (bot, bet365 y partidos parecidos) lo ven claro
    pool = [p for p in pool if not (p["mercado"] == "Goals Over/Under" and p["opcion"] == "Over 1.5"
                                    and (p["prob_aprendida"] < MAS_15["prob_min"]
                                         or min(x for x in (p.get("prob_bet365"), p.get("prob_tipo"), p["frecuencia"]) if x is not None) < MAS_15["cada_una"]))]
    # 27/10 (Marcos): «más de 2,5 goles» falla mucho: solo si está muy respaldado
    pool = [p for p in pool if not (MAS_25.search(f"{p['mercado']}|{p['opcion']}") and p["prob_aprendida"] < PROB_MIN_25)]
    # una por mercado (o por jugador y dato): la más probable
    mejor = {}
    for p in pool:
        k = (p["mercado"].replace("Home ", "").replace("Away ", ""), p.get("jugador"), p.get("campo"))
        if k not in mejor or p["prob_aprendida"] > mejor[k]["prob_aprendida"]:
            mejor[k] = p
    return sorted(mejor.values(), key=lambda p: -p["prob_aprendida"])


FAVORITO_MIN = 0.55          # probabilidad de ganar (bet365, sin margen) para «gana alguna de las dos partes»
PROB_MIN_A_PUERTA = 0.70
MAS_15 = {"prob_min": 0.80, "cada_una": 0.75, "max_dia": 1}   # 28/10 (Marcos): +1,5 solo uno al día y muy claro


def es_mas15(p):
    return p["mercado"] == "Goals Over/Under" and str(p["opcion"]) == "Over 1.5"


def favorito(ex):
    """Probabilidad de ganar de local y visitante según el 1X2 de bet365 (sin el margen de la casa)."""
    c = dict((o, v) for o, v in (ex.get("cuotas") or {}).get("Match Winner", []))
    try:
        inv = {o: 1 / float(c[o]) for o in ("Home", "Draw", "Away")}
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return {}
    s = sum(inv.values())
    return {o: v / s for o, v in inv.items()}


import re
MAS_25 = re.compile(r"Goals Over/Under\|Over 2\.5|Total Goals/Both Teams To Score\|o/yes 2\.5")
PROB_MIN_25 = 0.70


def familia(p):
    """Tipo de mercado para variar: goles, resultado, córners, tarjetas, tiros del partido, jugador…"""
    m = p["mercado"]
    if p.get("tipo") == "jugador" or p.get("jugador"):
        return f"jugador-{p.get('campo')}"
    if "Corner" in m:
        return "corners"
    if "Card" in m:
        return "tarjetas"
    if "Shot" in m:
        return "tiros"
    if "Offside" in m:
        return "fueras"
    if m in RESULTADO or m.startswith("Results/"):
        return "resultado"
    return "goles"


def variada(comb):
    """27/10 (Marcos): todo tipo de mercados, no siempre lo mismo. Como mucho 2 patas de goles o de
    resultado, 1 de tiros del partido, y al menos 3 tipos distintos en combis de 4 o más."""
    from collections import Counter
    c = Counter(familia(p) for p in comb)
    tope = {"goles": 2, "resultado": 2, "tiros": 1, "jugador-tiros": 3, "jugador-a_puerta": 2}   # tiros de jugadores: hasta 3
    if any(n > tope.get(f, 2) for f, n in c.items()):
        return False
    return len(c) >= min(3, len(comb))


def lado(p):
    """A qué equipo favorece la pata ('local'/'visitante'/None), jugadores y tiros incluidos."""
    import picks as P
    m, o = p["mercado"], str(p["opcion"])
    if m in ("ShotOnTarget 1x2", "Shots.1x2", "Corners 1x2") or m.endswith("1x2"):
        return {"Home": "local", "Away": "visitante"}.get(o)
    return P.lado_pick(p)


def pareja(a, b):
    """Cuánto recorta bet365 al juntar estas dos patas en «Crear apuesta» (1 = nada)."""
    fa, fb = familia(a), familia(b)
    la, lb = lado(a), lado(b)
    goleador = {"jugador-goles", "jugador-gol_o_asist"}
    if fa in goleador or fb in goleador:   # 28/10: un jugador marca va muy ligado a los goles y al resultado
        otra = fb if fa in goleador else fa
        return 0.88 if otra == "goles" else 0.90 if otra == "resultado" else 0.97 if otra != "tarjetas" else 1.0
    if "tarjetas" in (fa, fb) or "fueras" in (fa, fb) or "faltas" in (str(a.get("campo")), str(b.get("campo"))):
        return 1.0
    if la and lb:
        dominio = {"ShotOnTarget 1x2", "Shots.1x2", "Corners 1x2"}
        if la == lb and ({a["mercado"], b["mercado"]} & dominio) and "Match Winner" in {a["mercado"], b["mercado"]}:
            # 28/10: «el Milan hace más tiros a puerta» + «gana el Milan» van muy juntas (con «gana alguna mitad»
            # no tanto: Monza–Napoli del 27/10 sigue cuadrando con el recorte normal). Milan–Bologna
            # (tiros a puerta 1,44 · Bologna marca 1,62 · gana Milan 1,70 · +3,5 tarjetas 1,80) pagaba 8,00 en bet365
            return 0.78
        if la != lb:
            # 28/10: Milan gana + Bologna marca (+ córners, tarjetas, faltas): bet365 pagaba 10,50, MÁS que
            # multiplicando (~8,6). Que gane uno y marque el otro no se recorta.
            return 1.0
        if {fa, fb} == {"resultado", "goles"}:          # gana/o empata + ese equipo marca: van muy juntas
            return 0.80
        if fa == fb == "resultado":                      # o empate + gana alguna parte: casi lo mismo
            return 0.85
        if "goles" in (fa, fb) and (fa.startswith("jugador") or fb.startswith("jugador")):
            return 0.90                                  # Monza marca + Varela 1+ a puerta: 2,26 → 2,05 en bet365
        if "goles" in (fa, fb) and "resultado" not in (fa, fb):   # ese equipo marca + sus córners
            return 0.88
        if "corners" in (fa, fb) and (fa.startswith("jugador") or fb.startswith("jugador")):
            return 0.93
        return 0.97                                      # mismo equipo: córners, tiros, jugadores…
    if fa == "goles" and fb == "goles" and (la or lb):   # 27/10: +2,5 goles + Werder marca: 2,26 → ~1,80 en bet365
        return 0.80
    if fa == "goles" and fb == "goles":                  # más de 1,5 + ambos marcan, gol 1ª parte…
        return 0.90
    if {fa, fb} == {"goles", "resultado"}:
        return 0.97
    # 28/10 (City gana una parte + Brighton marca + 1,5 tarjetas + 9,5 tiros a puerta: 5,18 → 4,25 en bet365):
    # los tiros del partido van muy ligados a que haya goles y a que alguien gane
    tiros_partido = (fa == "tiros" and not la) or (fb == "tiros" and not lb)   # «más de X tiros a puerta» del partido
    if {fa, fb} == {"resultado", "tiros"} and tiros_partido:
        return 0.87
    if {fa, fb} == {"goles", "tiros"} and tiros_partido:
        return 0.96
    if "tiros" in (fa, fb) and {fa, fb} & {"jugador-tiros", "jugador-a_puerta"}:   # tiros del partido + de un jugador
        return 0.94
    if "goles" in (fa, fb) or (fa == fb == "tiros") or {fa, fb} <= {"tiros", "jugador-tiros", "jugador-a_puerta"}:
        return 0.99
    if fa == fb == "corners":
        return 0.95
    return 1.0


FACTOR_MAX = 1.6   # 28/10: patas que van en contra pagan más que multiplicar (Milan), pero con tope


def clave_pareja(a, b):
    """Tipo de pareja para lo aprendido (28/10): «goles+resultado/mismo», «jugador+tiros/partido»…"""
    def fam(p):
        f = familia(p)
        if f in ("jugador-goles", "jugador-gol_o_asist"):
            return "goleador"   # «X marca» va muy ligado a los goles y al resultado; tiros o faltas de un jugador, no
        return "jugador" if f.startswith("jugador") else f
    la, lb = lado(a), lado(b)
    rel = "mismo" if la and la == lb else "contrario" if la and lb else "partido"
    return "+".join(sorted((fam(a), fam(b)))) + "/" + rel


def rasgos(comb):
    """Lo que entra en el cálculo: (ajuste del modelo de goles o None, [(clave, factor base)] de cada pareja)."""
    import modelo_goles
    goles = [p for p in comb if modelo_goles.modelable(p)]
    aj = modelo_goles.ajuste(goles) if len(goles) >= 2 else None
    parejas = [(clave_pareja(a, b), pareja(a, b)) for a, b in itertools.combinations(comb, 2)
               if not (aj and a in goles and b in goles)]
    return aj, parejas


_APRENDIDO = None


def aprendido():
    """Correcciones aprendidas de las cuotas reales de bet365 (calibrar_crear.py → datos/ajuste_crear.json)."""
    global _APRENDIDO
    if _APRENDIDO is None:
        from bot import DATOS
        _APRENDIDO = leer(DATOS / "ajuste_crear.json") or {}
    return _APRENDIDO


def factor_crear(comb, base=False):
    """28/10: las patas de goles y resultado se calculan con el modelo de goles (modelo_goles.py), que sabe si
    van juntas (recorta) o en contra (paga más); el resto de parejas, con los factores medidos de pareja().
    Encima, lo aprendido de las cuotas reales que da Marcos (calibrar_crear.py); base=True lo ignora."""
    aj, parejas = rasgos(comb)
    ap = {} if base else aprendido()
    beta, corr = ap.get("beta", 1.0), ap.get("claves") or {}
    f = aj ** beta if aj else 1.0
    for k, v in parejas:
        f *= v * math.exp(corr.get(k, 0.0))
    return min(FACTOR_MAX, max(FACTOR_MIN, f))


def patas_de_sel(sel, cuotas):
    patas = []
    for s, c in zip(sel, cuotas):
        pid, m, o = s.split("|", 2)
        x = {"partido_id": pid, "mercado": m, "opcion": o, "cuota": float(c)}
        if "Player" in m:
            x.update(tipo="jugador", jugador=o.rsplit(" - ", 1)[0],
                     campo="a_puerta" if "Target" in m else "faltas_c" if "Foul" in m else "tiros")
        elif m in ("Anytime Goal Scorer", "Player to Score or Assist", "Player to be booked"):   # 28/10: goleadores
            x.update(tipo="jugador", jugador=o, campo={"Anytime Goal Scorer": "goles", "Player to be booked": "amarillas"}
                     .get(m, "gol_o_asist"))
        patas.append(x)
    return patas


def cuota_real_sel(sel, cuotas):
    """Cuota real en bet365 de una combi guardada como ['partido|mercado|opción'] + cuotas: por partido se aplica
    el recorte de «Crear apuesta»; entre partidos distintos se multiplica tal cual. None si falta alguna cuota."""
    if not sel or len(sel) != len(cuotas) or any(c is None for c in cuotas):
        return None
    patas = patas_de_sel(sel, cuotas)
    total = 1.0
    for pid in {x["partido_id"] for x in patas}:
        g = [x for x in patas if x["partido_id"] == pid]
        total *= math.prod(x["cuota"] for x in g) * (factor_crear(g) if len(g) > 1 else 1)
    return round(total, 2)


def implica(a, b):
    """¿La pata a ya incluye a b? (si gana el Milan, ya ha ganado alguna parte: meter las dos es inflar la cuota)"""
    ma, oa, mb, ob = a["mercado"], str(a["opcion"]), b["mercado"], str(b["opcion"])
    lado = {"Home": "Home", "Away": "Away"}
    if ma in ("Match Winner", "First Half Winner", "Win Both Halves") and oa in lado:
        if mb == "To Win Either Half" and ob == oa:
            return True
        if mb == "Double Chance" and ob in (f"{oa}/Draw", f"Draw/{oa}"):
            return True
        if mb == ("Total - Home" if oa == "Home" else "Total - Away") and ob == "Over 0.5":
            return True
        if ma == "Win Both Halves" and mb in ("Match Winner", "First Half Winner") and ob == oa:
            return True
    if ma == mb and oa.startswith("Over") and ob.startswith("Over"):
        try:
            return float(oa.split()[-1]) > float(ob.split()[-1])
        except ValueError:
            return False
    return False


def coherente(comb):
    import picks as P
    from plantillas import cumple
    if any(implica(a, b) for a in comb for b in comb if a is not b):
        return False
    lados = {P.lado_pick(p) for p in comb if p["mercado"] in RESULTADO} - {None}
    if len(lados) > 1:
        return False
    jug = [p.get("jugador") for p in comb if p.get("jugador")]
    if len(set(jug)) < len(jug):
        return False
    return any(all(cumple(p, gl, gv) is not False for p in comb) for gl in range(7) for gv in range(7))


def combi_partido(pool, cfg):
    """29/10 (Marcos): combi de un partido con 6 cosas y cuota 7-10. Primero con patas seguras; si no sale, admite
    alguna algo menos segura; y si aun así no hay 6 posibles, con 5."""
    return (mejor_combi(pool, cfg["patas"], cfg["cuota"], PARTIDO["prob_min"])
            or mejor_combi(pool, cfg["patas"], cfg["cuota"], PROB_MIN_RELAJADA)
            or mejor_combi(pool, (5, 5), cfg["cuota"], PROB_MIN_RELAJADA))


def mejor_combi(pool, patas, cuota, prob_min=0.0, una_por_partido=False):
    """La combinación que más devuelve a la larga (prob × cuota) dentro de los límites."""
    best = None
    cand = [p for p in pool if p["prob_aprendida"] >= prob_min][:18]
    # 27/10 (Marcos): los tiros de jugadores le gustan más que los goles: si el partido tiene, la combi lleva
    # al menos 2 (o el único que haya)
    tiros_j = [p for p in pool if familia(p) in ("jugador-tiros", "jugador-a_puerta") and p["prob_aprendida"] >= 0.5]
    min_tiros = 0 if una_por_partido else min(2, len(tiros_j))
    cand = cand + [p for p in tiros_j if p not in cand]
    for n in range(patas[0], patas[1] + 1):
        for comb in itertools.combinations(cand, n):
            c = math.prod(p["cuota"] for p in comb)
            if not una_por_partido:   # 27/10: «Crear apuesta» de bet365 no multiplica (patas del mismo partido)
                c *= factor_crear(comb)
            if not cuota[0] <= c <= cuota[1]:
                continue
            if una_por_partido and len({p["partido_id"] for p in comb}) < n:
                continue
            if una_por_partido:
                from collections import Counter
                if max(Counter(familia(p) for p in comb).values()) > 2:   # no 3 patas del mismo tipo
                    continue
            if not una_por_partido and not (coherente(comb) and variada(comb)):
                continue
            if sum(1 for p in comb if familia(p) in ("jugador-tiros", "jugador-a_puerta")) < min_tiros:
                continue
            s = math.prod(p["prob_aprendida"] for p in comb) * c
            if not best or s > best[0]:
                best = (s, list(comb), round(c, 2))
    return best


def ya_en_otras():
    """Selecciones de las combis de partido metidas a mano en la cola (no las del bot), sin cancelar."""
    from bot import RAIZ
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    out = set()
    for p in leer(RAIZ / "publicaciones" / "cola.json", []) or []:
        if "combi-partido" in p.get("id", "") and p.get("sel") and not p.get("borrar") \
                and p.get("caducada") not in ("quitada", "cancelado") and p["id"] not in control.get("cancelados", []):
            out.update(control.get("sel", {}).get(p["id"], p["sel"]))
    return out


def del_dia(dia, hist=None, ap=None):
    """{'partidos': [(cp, cuota, tarjeta, hora)], 'tres': (picks, cuota), 'loca': (picks, cuota)}"""
    import picks as P
    from bot import DATOS
    from plantillas import datos_tarjeta, grandeza
    hist = hist if hist is not None else P.historial()
    ap = ap if ap is not None else (leer(DATOS / "aprendizaje.json") or {})
    pools = []
    otras = ya_en_otras()
    for f in EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido")
        if not pa or datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID).strftime("%Y-%m-%d") != dia:
            continue
        pool = pool_partido(ex, hist, ap)
        # 29/10 (Marcos): si ya hay otra combi de ese partido puesta a mano (p. ej. la del Everton de las 00:05),
        # la del bot sale diferente: sin repetir ninguna de sus selecciones
        pool = [p for p in pool if f"{p['partido_id']}|{p['mercado']}|{p['opcion']}" not in otras]
        if pool:
            pools.append(pool)
    # 1) combi de cada partido: grandes primero
    partidos = []
    for pool in pools:
        r = combi_partido(pool, PARTIDO)
        if r:
            b = pool[0]
            cp = {k: b[k] for k in ("partido_id", "fecha", "competicion", "liga_id", "local", "visitante")}
            cp["picks"] = r[1]
            partidos.append((grandeza(cp), r[0], cp, r[2]))
    partidos.sort(key=lambda x: (-x[0], -x[1]))
    # 29/10 (Marcos): por la noche SIEMPRE combis con escudos (dan muchos seguidores) de los partidos más grandes del
    # día (la de las 00:30, la del más grande, p. ej. el PSG). Esa combi es la buena; la de su hora del mismo partido
    # se rehace con otras selecciones y, si no da para otra, ese partido solo sale de noche.
    noche_sel = []
    ultima_noche = datetime.fromisoformat(dia).replace(tzinfo=MADRID, hour=NOCHE["horas"][-1][0], minute=NOCHE["horas"][-1][1])
    if dia <= NOCHE["hasta"] and ultima_noche > datetime.now(MADRID):   # si la noche ya pasó, no quita partidos de la tarde
        pool_id = {pool[0]["partido_id"]: pool for pool in pools}
        quedan = []
        for g, s, cp, c in partidos:
            if len(noche_sel) < len(NOCHE["horas"]):
                noche_sel.append((cp, c))
                usadas = {f"{p['partido_id']}|{p['mercado']}|{p['opcion']}" for p in cp["picks"]}
                r2 = combi_partido([p for p in pool_id[cp["partido_id"]]
                                    if f"{p['partido_id']}|{p['mercado']}|{p['opcion']}" not in usadas], PARTIDO)
                if r2:
                    quedan.append((g, r2[0], dict(cp, picks=r2[1]), r2[2]))
            else:
                quedan.append((g, s, cp, c))
        partidos = quedan
    # 27/10 (norma de Marcos): si entre los 3 mejores no hay equipo español, entra el mejor partido español
    # (en España bet365 suele dar aumentos y apuestas aseguradas)
    espanol = lambda cp: cp.get("liga_id") in (140, 141, 143)
    top = partidos[:PARTIDO["max"]]
    if not any(espanol(x[2]) for x in top[:3]):
        esp = next((x for x in partidos if espanol(x[2])), None)
        if esp and esp not in top:
            top = top[:3] + [esp] + top[3:PARTIDO["max"] - 1]
    elegidos = [(cp, c) for _, _, cp, c in top]
    # 28/10 (Marcos): +1,5 goles en una combi de partido como mucho al día; las demás se rehacen sin él
    pool_de = {pool[0]["partido_id"]: pool for pool in pools}
    con15, rehechos = 0, []
    for cp, c in elegidos:
        if any(es_mas15(p) for p in cp["picks"]):
            if con15 >= MAS_15["max_dia"]:
                r = combi_partido([p for p in pool_de[cp["partido_id"]] if not es_mas15(p)], PARTIDO)
                if not r:
                    continue
                cp, c = dict(cp, picks=r[1]), r[2]
            else:
                con15 += 1
        rehechos.append((cp, c))
    elegidos = rehechos
    # horas: 50 min antes; si chocan, cada 30 min hacia atrás
    usadas, salida = [], []
    for cp, c in sorted(elegidos, key=lambda x: x[0]["fecha"], reverse=True):
        h = datetime.fromisoformat(cp["fecha"]).replace(tzinfo=MADRID) - timedelta(minutes=50)
        while any(abs((h - u).total_seconds()) < 30 * 60 for u in usadas):
            h -= timedelta(minutes=30)
        usadas.append(h)
        salida.append((cp, c, datos_tarjeta(cp), h))
    salida.sort(key=lambda x: x[3])
    # 2) multis con el mejor pick de cada partido que empiece después de la hora del post
    res = {"partidos": salida}
    # 28/10: combis de madrugada (prueba): partidos grandes que no salen a su hora, con combis algo más cortas
    res["noche"] = []
    if dia <= NOCHE["hasta"]:
        f0n = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
        cand = [(None, None, cp, c) for cp, c in noche_sel]
        for (h, m), (_, _, cp, c) in zip(NOCHE["horas"], cand):
            res["noche"].append((cp, c, datos_tarjeta(cp), f0n.replace(hour=h, minute=m)))
    f0 = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    # 27/10 (norma de Marcos): una misma selección en 2 posts como mucho (combis de partido, escalera, x3, loca)
    from collections import Counter
    sel = lambda p: f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"
    usos = Counter(sel(p) for cp, _, _, _ in salida for p in cp["picks"])
    esc = (leer(DATOS / "escalera.json") or {}).get("actual") or {}
    if esc.get("dia") == dia:
        usos.update(sel(p) for p in esc.get("picks", []))
    for clave, cfg in (("tres", TRES), ("loca", LOCA)):
        hora = f0.replace(hour=cfg["hora"][0], minute=cfg["hora"][1])
        mejores = []
        for pool in pools:
            ok = [p for p in pool if p["prob_aprendida"] >= PROB_MIN_MULTI and usos[sel(p)] < 2
                  and datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID) >= hora + timedelta(minutes=60)]
            if ok:
                mejores.append(ok[0])
        mejores.sort(key=lambda p: -p["prob_aprendida"])
        r = mejor_combi(mejores, cfg["patas"], cfg["cuota"], una_por_partido=True)
        res[clave] = (r[1], r[2], hora) if r else None
        if r:
            usos.update(sel(p) for p in r[1])
    return res


# ---------------------------------------------------------------- boletos «Crear apuesta» (27/10, Marcos)
# Dos al día: 5–6 partidos, 2 patas de «Crear apuesta» por partido (~2,00 cada uno), total ~20–45.
# Se los manda el bot por privado a las 10:00; él los monta en bet365 y manda la captura al asistente,
# que recorta el dinero y la publica en Telegram y Threads cuando él dice que sí.
BOLETO = {"pareja": (1.70, 2.30), "prob_min": 0.60, "partidos": (4, 6), "total": (20.0, 45.0), "n": 2}
num = lambda x: f"{x:.2f}".replace(".", ",")


def pareja_partido(pool, evitar=(), rango=None):
    """Las 2 patas de un partido para «Crear apuesta»: precio real ~2, lo más probable posible."""
    best = None
    cand = [p for p in pool if p["prob_aprendida"] >= BOLETO["prob_min"] and not MAS_25.search(f"{p['mercado']}|{p['opcion']}")]
    for a, b in itertools.combinations(cand[:25], 2):
        if (a["mercado"], a["opcion"]) in evitar or (b["mercado"], b["opcion"]) in evitar:
            continue
        if familia(a) == familia(b) and familia(a) in ("goles", "resultado"):
            continue
        c = a["cuota"] * b["cuota"] * factor_crear([a, b])
        lo, hi = rango or BOLETO["pareja"]
        if not lo <= c <= hi or not coherente([a, b]):
            continue
        s = a["prob_aprendida"] * b["prob_aprendida"]
        if not best or s > best[0]:
            best = (s, [a, b], round(c, 2))
    return best


def boletos(dia, hist=None, ap=None, desde=None):
    """[{'partidos': [(cabecera, [pata, pata], cuota)], 'cuota': total}] para el día."""
    import picks as P
    from bot import DATOS
    from plantillas import grandeza
    hist = hist if hist is not None else P.historial()
    ap = ap if ap is not None else (leer(DATOS / "aprendizaje.json") or {})
    filas = []
    for f in EXTRA.glob("*.json"):
        ex = leer(f) or {}
        pa = ex.get("partido")
        if not pa or datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID).strftime("%Y-%m-%d") != dia:
            continue
        pool = pool_partido(ex, hist, ap)
        if not pool or (desde and pool[0]["fecha"] < desde):
            continue
        r = pareja_partido(pool)
        if r:
            b = pool[0]
            cab = {k: b[k] for k in ("partido_id", "fecha", "competicion", "liga_id", "local", "visitante")}
            filas.append((grandeza(cab), r[0], cab, r, pool))
    filas.sort(key=lambda x: (-x[0], -x[1]))
    salida, usados = [], set()
    for _ in range(BOLETO["n"]):
        libres = [x for x in filas if x[2]["partido_id"] not in usados]
        if len(libres) < BOLETO["partidos"][0]:   # pocos partidos: el 2º repite partidos con otras patas
            libres = list(libres)
            for g, s, cab, r, pool in filas:
                if cab["partido_id"] in usados:
                    r2 = pareja_partido(pool, evitar={(p["mercado"], p["opcion"]) for p in r[1]}, rango=(1.55, 2.50))
                    if r2:
                        libres.append((g, r2[0], cab, r2, pool))
        elegido, total = [], 1.0
        for g, s, cab, r, pool in libres:
            if len(elegido) >= BOLETO["partidos"][1] or (len(elegido) >= BOLETO["partidos"][0] and total >= BOLETO["total"][0]):
                break
            if total * r[2] > BOLETO["total"][1] and len(elegido) >= BOLETO["partidos"][0]:
                continue
            elegido.append((cab, r[1], r[2]))
            total *= r[2]
        if len(elegido) < BOLETO["partidos"][0]:
            break
        usados |= {cab["partido_id"] for cab, _, _ in elegido}
        salida.append({"partidos": sorted(elegido, key=lambda x: x[0]["fecha"]), "cuota": round(total, 2)})
    return salida


def texto_boleto(b, n):
    from plantillas import corto
    lineas = [f"🎟️ COMBI CREAR APUESTA {n} · x{num(b['cuota'])}", ""]
    for cab, patas, c in b["partidos"]:
        lineas.append(f"⚽ {corto(cab['local'])} vs {corto(cab['visitante'])} · {cab['fecha'][11:16]} · x{num(c)}")
        lineas += [f"   • {p['texto']} ({num(p['cuota'])})" for p in patas]
        lineas.append("")
    return "\n".join(lineas).strip()
