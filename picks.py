"""
El Analista · selección de picks y combis.

Se ejecuta después de bot.py. Para cada partido próximo coge las cuotas de
Bet365 y las compara con lo que han hecho de verdad los dos equipos (y sus
jugadores) en sus últimos partidos: porcentaje de veces que se cumplió cada
apuesta. No usa ningún modelo inventado: solo cuotas reales y hechos contados.

Un pick de equipo/partido entra si:
- la cuota de Bet365 está entre CUOTA_MIN (1,25) y CUOTA_MAX (1,80),
- se cumplió en >= FREC_MIN (75 %) de los partidos de los dos equipos juntos,
- y en cada equipo por separado en >= FREC_EQUIPO (70 %),
- con al menos MIN_PARTIDOS de cada equipo,
- y la frecuencia real es mayor que la probabilidad que da la cuota (hay valor),
  pero no por más de VENTAJA_MAX (si no, suele ser una muestra engañosa).

Un pick de jugador entra si el jugador es titular fijo (60'+ en 4 de los 5
últimos partidos de su equipo, incluido el último), la cuota está entre 1,25 y
2,00 y lo cumplió en >= 75 % de sus últimos partidos jugando 60'+ (porteros 80').

Mercados: resultado, goles (también por partes y por equipo), ambos marcan,
córners (total, por equipo, por partes, 1x2), tarjetas (total, por equipo,
amarillas), tiros y tiros a puerta (total, por equipo, 1x2), faltas, fueras de
juego, paradas y jugadores (tiros, a puerta, faltas, amonestado, paradas, gol).
Nunca "menos de X goles" ni "sin empate" (doble oportunidad 12).

Cada pick lleva un "tipo" (goles, corners, tarjetas, tiros, faltas, jugador...)
y las combis no repiten tipo, para que no salgan todas del mismo mercado.

Genera:
- datos/picks.json  → picks, combis del día y combi de cada partido (cuota 9-11)
- PICKS.md          → lo mismo para leerlo
"""

import json
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

from bot import DATOS, EXTRA, MADRID, PARTIDOS, RAIZ, leer

CUOTA_MIN = 1.25
CUOTA_MAX = 1.80      # por encima, la muestra suele engañar (rivales de distinto nivel)
VENTAJA_MAX = 0.30    # si la estadística supera a la cuota por más de esto, se desconfía
FREC_MIN = 0.75
FREC_EQUIPO = 0.70
MIN_PARTIDOS = 5
ULTIMOS = 10          # partidos de cada equipo que se miran
JUG_CUOTA_MAX = 2.00
# Prueba con 186 partidos jugados (informes/prueba_mercados.md): los picks de jugador fallan más
# que los de equipo. Con ≥ 90 % aguantan los tiros (2+) y las paradas; tiros a puerta (1+) y
# faltas de jugador se quedan en ~70 % y fuera. Faltas de equipo: se pide más (85 %).
JUG_FREC_MIN = 0.80
# Más variedad (petición 25/10): tiros, tiros a puerta y faltas de jugador. Paradas fuera (a mano en bet365).
JUG_CAMPOS = {"tiros", "a_puerta", "faltas_c"}
JUG_FREC_CAMPO = {"tiros": 0.85, "a_puerta": 0.80, "faltas_c": 0.80}
FREC_TIPO = {"faltas": 0.85}
# Además de los últimos partidos, el local en casa y el visitante fuera (lecciones 9 y 10):
# con 3+ partidos en ese campo, cada uno tiene que cumplirlo al menos en este %.
FREC_CAMPO = 0.60
MIN_CAMPO = 3

# Para la combi del partido (cuota 9-11) se aceptan patas algo menos seguras
PARTIDO_CUOTA_MAX = 2.60
PARTIDO_FREC_MIN = 0.65
PARTIDO_RANGO = (10.0, 13.5)   # cuota "sumada"; bet365 la rebaja al ser del mismo partido → ~9-11

COMPETICION = {140: "LaLiga", 39: "Premier", 135: "Serie A", 78: "Bundesliga",
               61: "Ligue 1", 2: "Champions", 3: "Europa League", 848: "Conference"}

TERMINADOS = {"FT", "AET", "PEN"}

# Nunca "menos de X goles" (ni del partido, ni de un equipo, ni por partes).
MERCADOS_GOLES = {"Goals Over/Under", "Goals Over/Under First Half", "Goals Over/Under - Second Half",
                  "Total - Home", "Total - Away"}


def es_sin_empate(mercado, opcion):
    """Solo excluye el 12; ganador, empate, 1X y X2 siguen permitidos."""
    mercado = str(mercado or "").strip().casefold()
    opcion = "".join(str(opcion or "").casefold().split())
    return (mercado == "double chance" and opcion in ("home/away", "away/home", "12", "1/2", "homeoraway")) or mercado in ("no draw", "sin empate")


def excluido(mercado, opcion):
    """Fuera los 'menos de' (se entienden mal en redes y no le gustan) y los 'no'."""
    if es_sin_empate(mercado, opcion):
        return True
    o = str(opcion).strip()
    if o.startswith("Under") or o == "No":
        return True
    if "Saves" in mercado or "Goalkeeper" in mercado:   # porteros: se miran a mano en bet365 (la API a veces trae la línea desplazada)
        return True
    if mercado == "Total Goals/Both Teams To Score" and not o.startswith("o/yes"):
        return True
    return False


# ------------------------------------------------------------ hechos por partido

def lado(p, eq):
    """Devuelve (goles a favor, goles en contra, 1ª parte a favor, 1ª parte en contra, id rival)."""
    loc = p["local"]["id"] == eq
    gf, gc = (p["goles"][0], p["goles"][1]) if loc else (p["goles"][1], p["goles"][0])
    d = p.get("descanso") or [None, None]
    hf, hc = (d[0], d[1]) if loc else (d[1], d[0])
    rival = p["visitante"]["id"] if loc else p["local"]["id"]
    return gf, gc, hf, hc, rival


def partes(p, eq):
    """Goles (a favor, en contra) en la 1ª y en la 2ª parte desde eq, o None."""
    gf, gc, hf, hc, _ = lado(p, eq)
    if hf is None or hc is None:
        return None
    return (hf, hc), (gf - hf, gc - hc)


def stat_eq(p, eq, campo):
    v = ((p.get("stats") or {}).get(str(eq)) or {}).get(campo)
    if v is None and campo == "rojas" and (p.get("stats") or {}).get(str(eq)):
        return 0
    return v


def stat_rival(p, eq, campo):
    return stat_eq(p, lado(p, eq)[4], campo)


def stat_total(p, campo):
    s = p.get("stats") or {}
    if len(s) < 2:
        return None
    vals = [(v or {}).get(campo) for v in s.values()]
    if any(v is None for v in vals) and campo != "rojas":
        return None
    return sum(v or 0 for v in vals)


def tarjetas(p):
    a = stat_total(p, "amarillas")
    if a is None:
        return None
    return a + (stat_total(p, "rojas") or 0)


def tarjetas_eq(p, eq):
    a = stat_eq(p, eq, "amarillas")
    return None if a is None else a + (stat_eq(p, eq, "rojas") or 0)


def corners_parte(p, eq, parte):
    cp = (p.get("corners_partes") or {}).get(str(eq)) or {}
    return cp.get(f"statistics_{parte}")


# Mercados de estadística "Over/Under": nombre bet365 → (campo, ámbito)
#   ámbito: "total" (los dos equipos), "home"/"away" (el equipo local/visitante del próximo partido)
STATS_OU = {
    "Corners Over Under": ("corners", "total"),
    "Home Corners Over/Under": ("corners", "home"), "Away Corners Over/Under": ("corners", "away"),
    "Cards Over/Under": ("tarjetas", "total"),
    "Home Team Total Cards": ("tarjetas", "home"), "Away Team Total Cards": ("tarjetas", "away"),
    "Yellow Over/Under": ("amarillas", "total"),
    "Home Team Yellow Cards": ("amarillas", "home"), "Away Team Yellow Cards": ("amarillas", "away"),
    "Total ShotOnGoal": ("a_puerta", "total"),
    "Home Total ShotOnGoal": ("a_puerta", "home"), "Away Total ShotOnGoal": ("a_puerta", "away"),
    "Home Shots On Target": ("a_puerta", "home"), "Away Shots On Target": ("a_puerta", "away"),
    "Total Shots": ("tiros", "total"),
    "Shots. Home Total": ("tiros", "home"), "Shots. Away Total": ("tiros", "away"),
    "Fouls. Total": ("faltas", "total"),
    "Fouls. Home Total": ("faltas", "home"), "Fouls. Away Total": ("faltas", "away"),
    "Offsides Total": ("fueras_juego", "total"),
    "Offsides Home Total": ("fueras_juego", "home"), "Offsides Away Total": ("fueras_juego", "away"),
    "Saves O/U Home": ("paradas", "home"), "Saves O/U Away": ("paradas", "away"),
    "Total Corners (1st Half)": ("corners_1h", "total"), "Total Corners (2nd Half)": ("corners_2h", "total"),
}
STATS_1X2 = {"Corners 1x2": "corners", "ShotOnTarget 1x2": "a_puerta", "Shots.1x2": "tiros"}

TIPO_CAMPO = {"corners": "corners", "corners_1h": "corners", "corners_2h": "corners",
              "tarjetas": "tarjetas", "amarillas": "tarjetas", "a_puerta": "tiros a puerta",
              "tiros": "tiros", "faltas": "faltas", "fueras_juego": "fueras de juego", "paradas": "paradas"}


def valor_stat(p, eq, campo, propio):
    """Valor de la estadística en el partido p: del equipo eq (propio) o de su rival."""
    quien = eq if propio else lado(p, eq)[4]
    if campo == "tarjetas":
        return tarjetas_eq(p, quien)
    if campo in ("corners_1h", "corners_2h"):
        return corners_parte(p, quien, campo[-2:])
    return stat_eq(p, quien, campo)


def valor_total(p, campo):
    if campo == "tarjetas":
        return tarjetas(p)
    if campo in ("corners_1h", "corners_2h"):
        vals = [(v or {}).get(f"statistics_{campo[-2:]}") for v in (p.get("corners_partes") or {}).values()]
        return sum(vals) if len(vals) == 2 and None not in vals else None
    return stat_total(p, campo)


def tipo_de(mercado):
    if mercado in STATS_OU:
        return TIPO_CAMPO[STATS_OU[mercado][0]]
    if mercado in STATS_1X2:
        return TIPO_CAMPO[STATS_1X2[mercado]]
    if mercado in ("Match Winner", "Double Chance", "First Half Winner", "To Win Either Half", "Win Both Halves"):
        return "resultado"
    if mercado == "Results/Both Teams Score":
        return "resultado"
    return "goles"


PAGO_ANTICIPADO = {140, 39, 135, 78, 61}
GANADOR_FREC_MIN = 0.60
GANADOR_CUOTA_MAX = 2.30   # "gana X" entra con menos % que el resto, siempre que la cuota tenga valor   # LaLiga, Premier, Serie A, Bundesliga, Ligue 1


def lidero_por_2(p, equipo):
    """¿El equipo llegó a ir 2 goles por delante en algún momento? (pago anticipado de bet365).
    Los goles en propia puerta se cuentan como cuadre el marcador final."""
    goles = sorted((e for e in p.get("eventos") or [] if e.get("tipo") == "Goal" and e.get("detalle") != "Missed Penalty"),
                   key=lambda e: ((e.get("min") or 0), (e.get("extra") or 0)))
    if not goles or equipo is None:
        return False
    ids = [p["local"]["id"], p["visitante"]["id"]]
    final = p.get("goles") or []

    def recorrido(propia_al_rival):
        m, maximo = {ids[0]: 0, ids[1]: 0}, {ids[0]: 0, ids[1]: 0}
        for e in goles:
            t = e.get("equipo")
            if t not in m:
                return None
            if e.get("detalle") == "Own Goal" and propia_al_rival:
                t = ids[1] if t == ids[0] else ids[0]
            m[t] += 1
            for x, y in ((ids[0], ids[1]), (ids[1], ids[0])):
                maximo[x] = max(maximo[x], m[x] - m[y])
        return (m, maximo)

    for opcion in (False, True):
        r = recorrido(opcion)
        if r and (len(final) != 2 or [r[0][ids[0]], r[0][ids[1]]] == list(final)):
            return r[1].get(equipo, 0) >= 2
    return False


def calidad(p):
    """Nota de un pick para ordenarlo: lo fiable que es (frecuencia y ventaja sobre la cuota) más
    las señales del mercado: bet365 paga más que el resto de casas (+) y la cuota que baja porque
    entra dinero (+) o sube (−). Así las combis y listas cogen primero las mejores apuestas."""
    nota = p["frecuencia"] + 0.5 * p.get("ventaja", 0)
    vm = p.get("valor_mercado")
    if vm is not None:
        nota += max(min(vm, 0.10), -0.10) * 0.8
    mv = p.get("movimiento")
    if mv is not None:
        nota -= max(min(mv, 0.15), -0.15) * 0.5
    return nota


def evaluador(mercado, opcion, es_local):
    """Devuelve una función f(p, eq) que dice si la apuesta se habría cumplido en un
    partido pasado p, visto desde el equipo eq. es_local indica si eq es el local del
    partido próximo (para mercados de 'local'/'visitante')."""
    o = str(opcion).strip()
    linea = None
    if o.startswith(("Over ", "Under ")):
        try:
            linea = float(o.split()[1])
        except (IndexError, ValueError):
            return None
    mas = o.startswith("Over ")

    def cmp(valor):
        if valor is None or linea is None:
            return None
        return valor > linea if mas else valor < linea

    def es_propio(lado_mercado):
        """¿El equipo del mercado ('home'/'away') es eq?"""
        return (lado_mercado == "home") == es_local

    # ---- goles
    if mercado == "Goals Over/Under":
        return lambda p, eq: cmp(sum(p["goles"]))
    if mercado == "Goals Over/Under First Half":
        return lambda p, eq: cmp(sum(p["descanso"])) if p.get("descanso") and None not in p["descanso"] else None
    if mercado == "Goals Over/Under - Second Half":
        return lambda p, eq: (cmp(sum(p["goles"]) - sum(p["descanso"]))
                              if p.get("descanso") and None not in p["descanso"] else None)
    if mercado == "Both Teams Score":
        si = o == "Yes"
        return lambda p, eq: (min(p["goles"]) > 0) == si
    if mercado in ("Both Teams Score - First Half", "Both Teams To Score - Second Half"):
        if o != "Yes":
            return None
        i = 0 if "First" in mercado else 1
        return lambda p, eq: (min(partes(p, eq)[i]) > 0) if partes(p, eq) else None
    if mercado in ("Total - Home", "Total - Away"):
        propio = es_propio("home" if mercado == "Total - Home" else "away")
        return lambda p, eq: cmp(lado(p, eq)[0] if propio else lado(p, eq)[1])
    if mercado in ("Home Team Score a Goal", "Away Team Score a Goal"):
        if o != "Yes":
            return None
        propio = es_propio("home" if mercado.startswith("Home") else "away")
        return lambda p, eq: (lado(p, eq)[0] if propio else lado(p, eq)[1]) > 0
    if mercado.endswith(("(1st Half)", "(2nd Half)")) and "Score a Goal" in mercado:
        if o != "Yes":
            return None
        propio = es_propio("home" if mercado.startswith("Home") else "away")
        i = 0 if "1st" in mercado else 1

        def f(p, eq):
            pt = partes(p, eq)
            if not pt:
                return None
            return (pt[i][0] if propio else pt[i][1]) > 0
        return f
    if mercado in ("To Score In Both Halves By Teams", "To Win Either Half", "Win Both Halves"):
        if o not in ("Home", "Away"):
            return None
        propio = es_propio(o.lower())

        def f(p, eq):
            pt = partes(p, eq)
            if not pt:
                return None
            (a1, c1), (a2, c2) = pt
            if not propio:
                a1, c1, a2, c2 = c1, a1, c2, a2
            if mercado == "To Score In Both Halves By Teams":
                return a1 > 0 and a2 > 0
            if mercado == "To Win Either Half":
                return a1 > c1 or a2 > c2
            return a1 > c1 and a2 > c2
        return f
    if mercado == "Total Goals/Both Teams To Score":
        try:
            n = float(o.split()[-1])
        except ValueError:
            return None
        return lambda p, eq: sum(p["goles"]) > n and min(p["goles"]) > 0

    # ---- resultado
    def res(p, eq):
        gf, gc = lado(p, eq)[:2]
        return "G" if gf > gc else "E" if gf == gc else "P"

    def validos(op):
        v = {"Home": {"G"}, "Draw": {"E"}, "Away": {"P"},
             "Home/Draw": {"G", "E"}, "Home/Away": {"G", "P"}, "Draw/Away": {"E", "P"}}.get(op)
        if v is None:
            return None
        if es_local:
            return v
        inv = {"G": "P", "P": "G", "E": "E"}
        return {inv[x] for x in v}

    if mercado == "Match Winner":
        ok = validos(o)
        if not ok:
            return None
        if ok in ({"G"}, {"P"}):   # pago anticipado de bet365: 2 goles arriba en las 5 grandes = ganada
            def f(p, eq):
                r = res(p, eq)
                if r is None:
                    return None
                if r in ok:
                    return True
                if p.get("liga") not in PAGO_ANTICIPADO:
                    return False
                ganador = eq if ok == {"G"} else next((p[l]["id"] for l in ("local", "visitante") if p[l]["id"] != eq), None)
                return lidero_por_2(p, ganador)
            return f
        return lambda p, eq: res(p, eq) in ok
    if mercado == "Double Chance":
        ok = validos(o)
        return (lambda p, eq: res(p, eq) in ok) if ok else None
    if mercado == "First Half Winner":
        ok = validos(o)

        def f(p, eq):
            pt = partes(p, eq)
            if not pt:
                return None
            a, c = pt[0]
            return ("G" if a > c else "E" if a == c else "P") in ok
        return f if ok else None
    if mercado == "Results/Both Teams Score":
        try:
            r, b = o.split("/")
        except ValueError:
            return None
        ok = validos(r)
        if not ok:
            return None
        return lambda p, eq: res(p, eq) in ok and (min(p["goles"]) > 0) == (b == "Yes")

    # ---- estadísticas
    if mercado in STATS_OU:
        campo, ambito = STATS_OU[mercado]
        if ambito == "total":
            return lambda p, eq: cmp(valor_total(p, campo))
        propio = es_propio(ambito)
        return lambda p, eq: cmp(valor_stat(p, eq, campo, propio))
    if mercado in STATS_1X2:
        campo = STATS_1X2[mercado]
        ok = validos(o)
        if not ok:
            return None

        def f(p, eq):
            a, b = valor_stat(p, eq, campo, True), valor_stat(p, eq, campo, False)
            if a is None or b is None:
                return None
            return ("G" if a > b else "E" if a == b else "P") in ok
        return f
    if mercado == "Both Teams to Receive a Card":
        if o != "Yes":
            return None

        def f(p, eq):
            a, b = tarjetas_eq(p, eq), tarjetas_eq(p, lado(p, eq)[4])
            return None if a is None or b is None else (a > 0 and b > 0)
        return f
    return None


def media_esperada(mercado, h_loc, h_vis):
    """Media histórica de la estadística de un mercado Over/Under para este partido.
    Sirve para descartar mercados mal etiquetados (la línea central de bet365 debe
    parecerse a lo que suele pasar)."""
    if mercado not in STATS_OU:
        return None
    campo, ambito = STATS_OU[mercado]
    vals = []
    if ambito == "total":
        for p, eq in h_loc + h_vis:
            v = valor_total(p, campo)
            if v is not None:
                vals.append(v)
        return sum(vals) / len(vals) if vals else None
    # equipo del mercado: lo suyo a favor + lo que concede el rival
    suyo, rival = (h_loc, h_vis) if ambito == "home" else (h_vis, h_loc)
    a = [valor_stat(p, eq, campo, True) for p, eq in suyo]
    b = [valor_stat(p, eq, campo, False) for p, eq in rival]
    a, b = [x for x in a if x is not None], [x for x in b if x is not None]
    if not a or not b:
        return None
    return (sum(a) / len(a) + sum(b) / len(b)) / 2


def linea_central(opciones):
    """Línea Over/Under con la cuota del Over más cerca de 1,90 (la 'línea justa' de bet365)."""
    mejor = None
    for op, c in opciones:
        op = str(op)
        if not op.startswith("Over "):
            continue
        try:
            n, c = float(op.split()[1]), float(c)
        except (IndexError, ValueError):
            continue
        if mejor is None or abs(c - 1.9) < abs(mejor[1] - 1.9):
            mejor = (n, c)
    return mejor[0] if mejor else None


def mercado_fiable(mercado, opciones, h_loc, h_vis):
    if mercado not in STATS_OU:
        return True
    media, centro = media_esperada(mercado, h_loc, h_vis), linea_central(opciones)
    if media is None:
        return False
    if centro is None:
        return True
    return abs(centro - media) <= max(1.5, 0.4 * media)


# ------------------------------------------------------------ textos

def texto_pick(mercado, opcion, local, visit):
    o = str(opcion)
    partido = f"{local}–{visit}"
    n = mm = None
    if o.startswith(("Over ", "Under ")):
        n = o.split()[1].replace(".", ",")
        mm = "Más" if o.startswith("Over") else "Menos"
    eqm = {"home": local, "away": visit}
    if mercado == "Goals Over/Under":
        return f"{mm} de {n} goles en {partido}"
    if mercado == "Goals Over/Under First Half":
        return (f"Gol en la 1ª parte del {partido}" if o == "Over 0.5"
                else f"{mm} de {n} goles en la 1ª parte del {partido}")
    if mercado == "Goals Over/Under - Second Half":
        return (f"Gol en la 2ª parte del {partido}" if o == "Over 0.5"
                else f"{mm} de {n} goles en la 2ª parte del {partido}")
    if mercado == "Both Teams Score":
        return f"Ambos marcan en {partido}" if o == "Yes" else f"No marcan los dos en {partido}"
    if mercado == "Both Teams Score - First Half":
        return f"Ambos marcan en la 1ª parte del {partido}"
    if mercado == "Both Teams To Score - Second Half":
        return f"Ambos marcan en la 2ª parte del {partido}"
    if mercado in ("Total - Home", "Total - Away"):
        eq = local if mercado == "Total - Home" else visit
        if o.startswith("Over "):
            k = int(float(o.split()[1]) + 0.5)
            return f"{eq} marca" if k == 1 else f"{eq} marca {k} o más"
        return f"{eq} marca {mm.lower()} de {n} goles"
    if mercado in ("Home Team Score a Goal", "Away Team Score a Goal"):
        return f"{local if mercado.startswith('Home') else visit} marca"
    if "Score a Goal (" in mercado:
        eq = local if mercado.startswith("Home") else visit
        return f"{eq} marca en la {'1ª' if '1st' in mercado else '2ª'} parte"
    if mercado == "To Score In Both Halves By Teams":
        return f"{eqm[o.lower()]} marca en las dos partes"
    if mercado == "To Win Either Half":
        return f"{eqm[o.lower()]} gana alguna de las dos partes"
    if mercado == "Win Both Halves":
        return f"{eqm[o.lower()]} gana las dos partes"
    if mercado == "Total Goals/Both Teams To Score":
        return f"Ambos marcan y más de {o.split()[-1].replace('.', ',')} goles en {partido}"
    if mercado == "Match Winner":
        return {"Home": f"Gana el {local}", "Away": f"Gana el {visit}", "Draw": f"Empate en {partido}"}[o]
    if mercado == "Double Chance":
        return {"Home/Draw": f"{local} o empate", "Draw/Away": f"{visit} o empate",
                "Home/Away": f"No hay empate en {partido}"}[o]
    if mercado == "First Half Winner":
        return {"Home": f"{local} gana al descanso", "Away": f"{visit} gana al descanso",
                "Draw": f"Empate al descanso en {partido}"}[o]
    if mercado == "Results/Both Teams Score":
        r, b = o.split("/")
        base = {"Home": f"Gana el {local}", "Away": f"Gana el {visit}", "Draw": f"Empate en {partido}"}[r]
        return f"{base} y ambos marcan" if b == "Yes" else f"{base} y no marcan los dos"
    if mercado == "Both Teams to Receive a Card":
        return f"Los dos equipos ven tarjeta en {partido}"
    nombres = {"corners": "córners", "corners_1h": "córners en la 1ª parte", "corners_2h": "córners en la 2ª parte",
               "tarjetas": "tarjetas", "amarillas": "amarillas", "a_puerta": "tiros a puerta",
               "tiros": "tiros", "faltas": "faltas", "fueras_juego": "fueras de juego", "paradas": "paradas"}
    if mercado in STATS_OU:
        campo, ambito = STATS_OU[mercado]
        if ambito == "total":
            return f"{mm} de {n} {nombres[campo]} en {partido}"
        quien = local if ambito == "home" else visit
        if campo == "paradas":
            return f"Portero del {quien}: {mm.lower()} de {n} paradas"
        verbo = "ve" if campo in ("tarjetas", "amarillas") else "comete" if campo == "faltas" else "hace"
        return f"{quien} {verbo} {mm.lower()} de {n} {nombres[campo]}"
    if mercado in STATS_1X2:
        campo = nombres[STATS_1X2[mercado]]
        return {"Home": f"{local} hace más {campo}", "Away": f"{visit} hace más {campo}",
                "Draw": f"Mismos {campo} en {partido}"}.get(o, f"{mercado} {o}")
    return f"{mercado} {o}"


# ------------------------------------------------------------ jugadores

JUG_MERCADOS = {  # nombre bet365 → (campo del jugador, plantilla)
    "Player Shots On Target Total": ("a_puerta", "{j}: {n}+ tiros a puerta"),
    "Home Player Shots On Target Total": ("a_puerta", "{j}: {n}+ tiros a puerta"),
    "Away Player Shots On Target Total": ("a_puerta", "{j}: {n}+ tiros a puerta"),
    "Player Shots On Target": ("a_puerta", "{j}: {n}+ tiros a puerta"),
    "Player Shots Total": ("tiros", "{j}: {n}+ tiros"),
    "Home Player Shots Total": ("tiros", "{j}: {n}+ tiros"),
    "Away Player Shots Total": ("tiros", "{j}: {n}+ tiros"),
    "Home Player Shots": ("tiros", "{j}: {n}+ tiros"),
    "Away Player Shots": ("tiros", "{j}: {n}+ tiros"),
    "Player Fouls Committed": ("faltas_c", "{j} comete {n}+ faltas"),
    "Home Player Fouls Committed": ("faltas_c", "{j} comete {n}+ faltas"),
    "Away Player Fouls Committed": ("faltas_c", "{j} comete {n}+ faltas"),
    "Goalkeeper Saves": ("paradas", "{j}: {n}+ paradas"),
    "Home Goalkeeper Saves": ("paradas", "{j}: {n}+ paradas"),
    "Away Goalkeeper Saves": ("paradas", "{j}: {n}+ paradas"),
    "Player to be booked": ("amarillas", "{j} ve tarjeta"),
    "Anytime Goal Scorer": ("goles", "{j} marca"),
    "Player to Score or Assist": ("gol_o_asist", "{j} marca o da asistencia"),
}


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return " ".join(t.replace("-", " ").replace(".", " ").split())


def mismo_jugador(a, b):
    a, b = norm(a).split(), norm(b).split()
    if not a or not b:
        return False
    return a == b or (a[-1] == b[-1] and a[0][0] == b[0][0])


def plantilla_fija(eq, hist):
    """Jugadores titulares fijos de eq: 60'+ en 4 de sus 5 últimos partidos, incluido el último.
    Devuelve {id: {"nombre", "pos", "partidos": [registros con 60'+ (80' porteros), recientes primero]}}."""
    ult = hist.get(eq, [])[:5]
    if len(ult) < 4:
        return {}
    cuenta, info = defaultdict(int), {}
    for i, p in enumerate(ult):
        for j in (p.get("jugadores") or {}).get(str(eq)) or []:
            if (j.get("min") or 0) >= 60:
                cuenta[j["id"]] += 1
                if i == 0:
                    info[j["id"]] = j
    fijos = {pid: {"nombre": info[pid]["nombre"], "pos": info[pid].get("pos")}
             for pid in info if cuenta[pid] >= 4}
    for pid, d in fijos.items():
        regs = []
        for p in hist.get(eq, []):
            for j in (p.get("jugadores") or {}).get(str(eq)) or []:
                if j["id"] != pid:
                    continue
                minimo = 80 if d["pos"] == "G" else 60
                if (j.get("min") or 0) >= minimo:
                    r = dict(j)
                    if d["pos"] == "G" and not r.get("paradas"):
                        r["paradas"] = stat_eq(p, eq, "paradas")
                    r["gol_o_asist"] = (r.get("goles") or 0) + (r.get("asist") or 0)
                    regs.append(r)
        d["partidos"] = regs[:ULTIMOS]
    return fijos


def picks_jugadores(prox, hist, base, cuota_max=JUG_CUOTA_MAX, frec_min=FREC_MIN):
    partido = prox["partido"]
    loc, vis = partido["teams"]["home"], partido["teams"]["away"]
    fijos = {"home": plantilla_fija(loc["id"], hist), "away": plantilla_fija(vis["id"], hist)}
    salida = []
    for mercado, opciones in (prox.get("cuotas") or {}).items():
        if mercado not in JUG_MERCADOS:
            continue
        campo, plantilla = JUG_MERCADOS[mercado]
        if campo not in JUG_CAMPOS:
            continue
        lados = ["home"] if mercado.startswith("Home") else ["away"] if mercado.startswith("Away") else ["home", "away"]
        for valor, cuota in opciones:
            try:
                cuota = float(cuota)
            except (TypeError, ValueError):
                continue
            if not (CUOTA_MIN <= cuota <= cuota_max):
                continue
            valor = str(valor).strip()
            if campo in ("amarillas", "goles", "gol_o_asist"):
                nombre, n = valor, 1
            else:
                if " - " not in valor:
                    continue
                nombre, n = valor.rsplit(" - ", 1)
                try:
                    n = int(float(n))
                except ValueError:
                    continue
            for ld in lados:
                jug = next(((pid, d) for pid, d in fijos[ld].items() if mismo_jugador(nombre, d["nombre"])), None)
                if not jug:
                    continue
                pid, d = jug
                if (campo == "paradas") != (d["pos"] == "G"):
                    break
                regs = d["partidos"]
                if len(regs) < MIN_PARTIDOS:
                    break
                si = sum(1 for r in regs if (r.get(campo) or 0) >= n)
                frec = si / len(regs)
                if frec < max(frec_min, JUG_FREC_CAMPO.get(campo, 0)) or not (0 < frec - 1 / cuota <= VENTAJA_MAX):
                    break
                equipo = loc["name"] if ld == "home" else vis["name"]
                salida.append(dict(base, mercado=mercado, opcion=valor, cuota=cuota, frecuencia=round(frec, 3),
                                   ventaja=round(frec - 1 / cuota, 3), tipo="jugador", jugador=nombre.strip(),
                                   equipo=equipo, jugador_id=pid, campo=campo, n=n,
                                   texto=plantilla.format(j=nombre.strip(), n=n),
                                   detalle=f"{nombre.strip()} {si}/{len(regs)}"))
                break
    # por jugador y dato, la línea más alta que cumple
    mejor = {}
    for p in salida:
        k = (p["jugador"], p["campo"])
        if k not in mejor or (p["frecuencia"], p["n"]) > (mejor[k]["frecuencia"], mejor[k]["n"]):
            mejor[k] = p
    return list(mejor.values())


# ------------------------------------------------------------ cálculo

def sustituto_de(partido, j):
    """El jugador que entró por j (eventos 'subst'); None si no lo cambiaron o no se sabe."""
    todos = [x for lista in (partido.get("jugadores") or {}).values() for x in lista]
    for e in partido.get("eventos") or []:
        if e.get("tipo") != "subst":
            continue
        a, b = e.get("jugador"), e.get("otro")
        for este, otro in ((a, b), (b, a)):
            if este and otro and mismo_jugador(este, j.get("nombre")):
                cand = [x for x in todos if mismo_jugador(otro, x.get("nombre")) and x is not j]
                # solo si j es el que SALE: jugó hasta el minuto del cambio
                if len(cand) == 1 and abs((j.get("min") or 0) - (e.get("min") or 0)) <= 5:
                    return cand[0]
    return None


def evaluar_pick(pick, partido):
    """Evalúa una selección estructurada; None significa que faltan datos, no un fallo."""
    mercado = pick.get("mercado")
    if pick.get("tipo") == "jugador" or pick.get("jugador_id") or mercado in JUG_MERCADOS:
        campo = pick.get("campo") or (JUG_MERCADOS.get(mercado) or (None,))[0]
        nombre = pick.get("jugador")
        n = pick.get("n")
        if (nombre is None and not pick.get("jugador_id")) or n is None:
            opcion = str(pick.get("opcion") or "")
            if campo in ("amarillas", "goles", "gol_o_asist"):
                nombre, n = nombre or opcion, 1 if n is None else n
            else:
                try:
                    jugador, linea = opcion.rsplit(" - ", 1)
                    nombre, n = nombre or jugador, int(float(linea)) if n is None else n
                except ValueError:
                    return None
        candidatos = [j for lista in (partido.get("jugadores") or {}).values() for j in lista
                      if (j.get("id") == pick["jugador_id"] if pick.get("jugador_id")
                          else mismo_jugador(nombre, j.get("nombre")))]
        if len(candidatos) != 1 or not campo:
            return None
        j = candidatos[0]
        if not j.get("min"):
            return None  # No convertir un jugador sin participación en un acierto o una pérdida.
        valor = j.get(campo)
        if valor is not None and valor < n and campo != "gol_o_asist":
            # bet365: si al jugador lo cambian, lo que haga el que entra por él también cuenta
            sustituto = sustituto_de(partido, j)
            if sustituto and sustituto.get(campo) is not None:
                valor += sustituto[campo]
        if campo == "gol_o_asist":
            valor = None if j.get("goles") is None or j.get("asist") is None else j["goles"] + j["asist"]
        return None if valor is None else valor >= n
    f = evaluador(mercado, pick.get("opcion"), True)
    return f(partido, partido["local"]["id"]) if f else None


def historial():
    idx = defaultdict(list)
    for f in PARTIDOS.glob("*.json"):
        p = leer(f)
        if not p or p.get("estado") not in TERMINADOS or not p.get("goles") or None in p["goles"]:
            continue
        idx[p["local"]["id"]].append(p)
        idx[p["visitante"]["id"]].append(p)
    for l in idx.values():
        l.sort(key=lambda p: p["fecha"], reverse=True)
    return idx


def frecuencia(func, partidos):
    vals = [func(p, eq) for p, eq in partidos]
    vals = [v for v in vals if v is not None]
    return (sum(vals), len(vals)) if vals else (0, 0)


def campo_ok(f_loc, f_vis, h_loc, h_vis, id_loc, id_vis):
    """El local lo cumple en casa y el visitante fuera (si hay partidos suficientes en ese campo)."""
    casa = [(p, e) for p, e in h_loc if (p.get("local") or {}).get("id") == id_loc]
    fuera = [(p, e) for p, e in h_vis if (p.get("visitante") or {}).get("id") == id_vis]
    for func, lista in ((f_loc, casa), (f_vis, fuera)):
        s, n = frecuencia(func, lista)
        if n >= MIN_CAMPO and s / n < FREC_CAMPO:
            return False
    return True


def picks_partido(prox, hist, ahora, cuota_max=CUOTA_MAX, frec_min=FREC_MIN, frec_eq=FREC_EQUIPO,
                  jugadores=True, antes_de=None):
    """antes_de: fecha ISO; solo usa partidos anteriores (para la prueba con partidos ya jugados)."""
    partido = prox["partido"]
    inicio = datetime.fromisoformat(partido["fixture"]["date"])
    if antes_de is None and (inicio <= ahora or partido["fixture"]["status"]["short"] not in ("NS", "TBD")):
        return []
    loc, vis = partido["teams"]["home"], partido["teams"]["away"]
    if antes_de:
        hist = {k: [p for p in v if p["fecha"] < antes_de] for k, v in hist.items()}
    h_loc = [(p, loc["id"]) for p in hist.get(loc["id"], [])[:ULTIMOS]]
    h_vis = [(p, vis["id"]) for p in hist.get(vis["id"], [])[:ULTIMOS]]
    if len(h_loc) < MIN_PARTIDOS or len(h_vis) < MIN_PARTIDOS:
        return []
    base = {"partido_id": partido["fixture"]["id"],
            "fecha": inicio.astimezone(MADRID).strftime("%Y-%m-%dT%H:%M"),
            "competicion": COMPETICION.get(partido["league"]["id"], partido["league"]["name"]),
            "liga_id": partido["league"]["id"], "local": loc["name"], "visitante": vis["name"]}
    salida = []
    for mercado, opciones in (prox.get("cuotas") or {}).items():
        if mercado in JUG_MERCADOS or not mercado_fiable(mercado, opciones, h_loc, h_vis):
            continue
        for opcion, cuota in opciones:
            try:
                cuota = float(cuota)
            except (TypeError, ValueError):
                continue
            tope = max(cuota_max, GANADOR_CUOTA_MAX) if mercado == "Match Winner" else cuota_max
            if cuota < CUOTA_MIN or cuota > tope or excluido(mercado, opcion):
                continue
            f_loc = evaluador(mercado, opcion, True)
            f_vis = evaluador(mercado, opcion, False)
            if not f_loc:
                continue
            a, na = frecuencia(f_loc, h_loc)
            b, nb = frecuencia(f_vis, h_vis)
            if na < MIN_PARTIDOS or nb < MIN_PARTIDOS:
                continue
            fa, fb = a / na, b / nb
            frec = (a + b) / (na + nb)
            implicita = 1 / cuota
            # campo_ok() (local en casa / visitante fuera) probado el 23/10 con 1.723 picks:
            # los que quitaba acertaban igual (79,7 % frente a 80,9 %), así que no se aplica.
            minimo, min_eq = max(frec_min, FREC_TIPO.get(tipo_de(mercado), 0)), frec_eq
            if mercado == "Match Winner":   # ganador: lo más importante (petición 25/10), con pago anticipado
                minimo, min_eq = GANADOR_FREC_MIN, 0.45   # el rival puede no perder tanto si el favorito gana mucho
            if frec < minimo or min(fa, fb) < min_eq \
                    or not (0 < frec - implicita <= VENTAJA_MAX):
                continue
            en_contra_loc = mercado in ("Total - Away",) or (mercado in STATS_OU and STATS_OU[mercado][1] == "away")
            en_contra_vis = mercado in ("Total - Home",) or (mercado in STATS_OU and STATS_OU[mercado][1] == "home")
            salida.append(dict(
                base, mercado=mercado, opcion=opcion, tipo=tipo_de(mercado),
                texto=texto_pick(mercado, opcion, loc["name"], vis["name"]),
                cuota=cuota, frecuencia=round(frec, 3), ventaja=round(frec - implicita, 3),
                detalle=(f"{loc['name']}{' (en contra)' if en_contra_loc else ''} {a}/{na} · "
                         f"{vis['name']}{' (en contra)' if en_contra_vis else ''} {b}/{nb}")))
    if jugadores and not antes_de:
        salida += picks_jugadores(prox, hist, base, cuota_max=max(cuota_max, JUG_CUOTA_MAX),
                                  frec_min=max(JUG_FREC_MIN, frec_min))
    return salida


def combinar(picks, minimo, maximo, max_patas, min_patas=2, max_por_tipo=1):
    """Elige picks (uno por partido, sin repetir tipo de mercado) empezando por los más
    fiables hasta caer en el rango de cuota."""
    elegidos, usados, tipos, total = [], set(), defaultdict(int), 1.0
    for p in sorted(picks, key=lambda x: -calidad(x)):
        if es_sin_empate(p["mercado"], p["opcion"]):
            continue
        if p["partido_id"] in usados or tipos[p["tipo"]] >= max_por_tipo:
            continue
        if total * p["cuota"] > maximo:
            continue
        elegidos.append(p)
        usados.add(p["partido_id"])
        tipos[p["tipo"]] += 1
        total *= p["cuota"]
        if total >= minimo and len(elegidos) >= min_patas:
            return {"picks": elegidos, "cuota": round(total, 2)}
        if len(elegidos) >= max_patas:
            break
    return None


def combis_del_dia(picks):
    """Tres combis sin repetir selección entre ellas (si no da, la loca puede reutilizar).
    La segura nunca lleva más de 2 patas."""
    reglas = [("segura", 1.45, 1.75, 2, 2, 1), ("cuota_3", 2.9, 3.6, 5, 3, 1), ("loca", 8.0, 20.0, 9, 5, 2)]
    usados, res = set(), {}
    for nombre, mn, mx, patas, min_p, por_tipo in reglas:
        libres = [p for p in picks if (p["partido_id"], p["mercado"], p["opcion"]) not in usados]
        c = (combinar(libres, mn, mx, patas, min_p, por_tipo)
             or combinar(libres, mn, mx, patas, min_p, por_tipo + 1)      # si no hay variedad suficiente
             or None)   # nunca se reutiliza una selección de otra combi
        res[nombre] = c
        if c:
            usados.update((p["partido_id"], p["mercado"], p["opcion"]) for p in c["picks"])
    return res


# Mercados que dicen casi lo mismo dentro de un partido: no se juntan en la combi del partido
FAMILIA = {"Goals Over/Under": "goles_total", "Total Goals/Both Teams To Score": "goles_total",
           "Both Teams Score": "ambos", "Results/Both Teams Score": "resultado",
           "Match Winner": "resultado", "Double Chance": "resultado"}


def combi_partido(picks):
    """Combi de un solo partido de cuota ~9-11 (para aumentos/aseguradas de bet365):
    mezcla resultado/goles, una estadística y al menos un jugador si lo hay. Sin repetir tipo."""
    picks = [p for p in picks if not es_sin_empate(p["mercado"], p["opcion"])]
    if not picks:
        return None
    orden = sorted(picks, key=lambda x: -calidad(x))
    elegidos, tipos, familias, total = [], set(), set(), 1.0
    jugadores_usados = set()
    # 1º el mejor jugador, luego el resto por fiabilidad
    jug = [p for p in orden if p["tipo"] == "jugador"]
    resto = [p for p in orden if p["tipo"] != "jugador"]
    for p in jug[:1] + resto + jug[1:]:
        fam = FAMILIA.get(p["mercado"], p["mercado"])
        clave_tipo = p["tipo"] if p["tipo"] != "jugador" else f"jugador-{p['campo']}"
        if clave_tipo in tipos or fam in familias or p.get("jugador") in jugadores_usados - {None}:
            continue
        if total * p["cuota"] > PARTIDO_RANGO[1]:
            continue
        elegidos.append(p)
        tipos.add(clave_tipo)
        familias.add(fam)
        if p.get("jugador"):
            jugadores_usados.add(p["jugador"])
        total *= p["cuota"]
        if total >= PARTIDO_RANGO[0]:
            return {"picks": elegidos, "cuota_sumada": round(total, 2)}
        if len(elegidos) >= 6:
            break
    return None


# ------------------------------------------------------------ información extra (25/10)
# árbitro (tarjetas), lesionados y sancionados, temporada del jugador, otras casas, movimiento de
# cuota y pronóstico de la API. Se aplica a cada pick después de calcularlo.
ARB_MIN_PARTIDOS = 4
ARB_FREC_MIN = 0.60        # un "más de X tarjetas" necesita que el árbitro lo cumpla en ≥ 60 % de sus partidos
LESION_MAX_TITULARES = 2   # con 2+ titulares fijos fuera, nada de "gana" ni "marca" para ese equipo
TEMPORADA_MARGEN = 0.10    # el jugador también tiene que cumplirlo en la temporada (con 10 puntos de margen)
PRED_MIN = 45              # el pronóstico de la API tiene que darle al equipo ≥ 45 % para un "gana"


def nombre_arbitro(r):
    return (r or "").split(",")[0].strip()


def indice_arbitros():
    """{árbitro: [tarjetas totales de cada partido que pitó]} con el calendario y los partidos guardados."""
    idx = defaultdict(list)
    for cal in DATOS.glob("calendario_*.json"):
        for fx in leer(cal, []) or []:
            arb = nombre_arbitro(fx["fixture"].get("referee"))
            if not arb or fx["fixture"]["status"]["short"] not in TERMINADOS:
                continue
            p = leer(PARTIDOS / f"{fx['fixture']['id']}.json")
            if not p or not p.get("stats"):
                continue
            t = [(s.get("amarillas") or 0) + (s.get("rojas") or 0) for s in p["stats"].values()]
            if len(t) == 2:
                idx[arb].append(sum(t))
    return idx


def habituales(equipo_id, hist, ultimos=8, minimo=4):
    """Titulares habituales: 60'+ en al menos 4 de los últimos 8 partidos (aunque no jugaran el último,
    que es justo lo que pasa con un lesionado)."""
    cuenta, info = defaultdict(int), {}
    for p in hist.get(equipo_id, [])[:ultimos]:
        for j in (p.get("jugadores") or {}).get(str(equipo_id)) or []:
            if (j.get("min") or 0) >= 60:
                cuenta[j["id"]] += 1
                info.setdefault(j["id"], {"nombre": j["nombre"], "pos": j.get("pos")})
    return {pid: info[pid] for pid, n in cuenta.items() if n >= minimo}


def titulares_fuera(prox, equipo_id, hist):
    fijos = habituales(equipo_id, hist)
    fuera = [l["jugador"] for l in prox.get("lesiones") or [] if l.get("equipo") == equipo_id]
    return [d["nombre"] for d in fijos.values() if any(mismo_jugador(n, d["nombre"]) for n in fuera)], fuera


def temporada_jugador(hist, equipo_id, jugador_id, campo, n):
    si = tot = 0
    for p in hist.get(equipo_id, []):
        for j in (p.get("jugadores") or {}).get(str(equipo_id)) or []:
            if j.get("id") == jugador_id and (j.get("min") or 0) >= 60:
                tot += 1
                si += (j.get(campo) or 0) >= n
    return si, tot


def enriquecer(picks, prox, hist, arbitros):
    partido = prox["partido"]
    loc, vis = partido["teams"]["home"], partido["teams"]["away"]
    arb = nombre_arbitro(partido["fixture"].get("referee"))
    tarj_arb = arbitros.get(arb, []) if arb else []
    pred = prox.get("prediccion") or {}
    otras = prox.get("cuotas_otras") or {}
    hist_c = prox.get("cuotas_hist") or {}
    fuera = {loc["id"]: titulares_fuera(prox, loc["id"], hist), vis["id"]: titulares_fuera(prox, vis["id"], hist)}
    salida = []
    for p in picks:
        m, o = p["mercado"], p["opcion"]
        eq_id = None
        if m == "Match Winner" or m in ("Total - Home", "Total - Away"):
            eq_id = loc["id"] if (o == "Home" or m == "Total - Home") else vis["id"] if (o == "Away" or m == "Total - Away") else None
        # lesionados / sancionados
        if p.get("tipo") == "jugador" and any(mismo_jugador(n, p.get("jugador")) for _, l in fuera.values() for n in l):
            continue
        if eq_id and len(fuera[eq_id][0]) >= LESION_MAX_TITULARES and (m == "Match Winner" or o.startswith("Over")):
            continue
        # pronóstico de la API para el ganador
        if m == "Match Winner" and o in ("Home", "Away"):
            pc = pred.get("local" if o == "Home" else "visitante")
            try:
                if pc and int(str(pc).rstrip("%")) < PRED_MIN:
                    continue
            except ValueError:
                pass
        # árbitro: tarjetas totales
        if m == "Cards Over/Under" and o.startswith("Over") and len(tarj_arb) >= ARB_MIN_PARTIDOS:
            linea = float(o.split()[1])
            fa = sum(t > linea for t in tarj_arb) / len(tarj_arb)
            if fa < ARB_FREC_MIN:
                continue
            p = dict(p, detalle=f"{p.get('detalle', '')} · árbitro {arb} {sum(t > linea for t in tarj_arb)}/{len(tarj_arb)}")
        # temporada entera del jugador
        if p.get("tipo") == "jugador" and p.get("jugador_id") and p.get("campo") and p.get("n"):
            eq_j = loc["id"] if p.get("equipo") == loc["name"] else vis["id"]
            si, tot = temporada_jugador(hist, eq_j, p["jugador_id"], p["campo"], p["n"])
            if tot >= MIN_PARTIDOS and si / tot < p["frecuencia"] - TEMPORADA_MARGEN and si / tot < JUG_FREC_CAMPO.get(p["campo"], FREC_MIN) - TEMPORADA_MARGEN:
                continue
            if tot:
                p = dict(p, temporada=f"{si}/{tot}")
        # otras casas y movimiento de cuota
        med = (otras.get(m) or {}).get(str(o))
        if med:
            p = dict(p, valor_mercado=round(p["cuota"] / med - 1, 3))
        serie = hist_c.get(f"{m}|{o}") or []
        if len(serie) >= 2:
            p = dict(p, movimiento=round(float(serie[-1][1]) / float(serie[0][1]) - 1, 3), cuota_inicial=float(serie[0][1]))
        if arb:
            p = dict(p, arbitro=arb, arbitro_tarjetas=round(sum(tarj_arb) / len(tarj_arb), 1) if tarj_arb else None)
        salida.append(p)
    return salida


# ------------------------------------------------------------ combi "gana o empata" (25/10)
DOBLE_FREC_MIN, DOBLE_FREC_EQ, DOBLE_CUOTA_MIN, DOBLE_RANGO = 0.70, 0.55, 1.25, (5.0, 20.0)
DOBLE_PATAS = (5, 6)   # 5-6 equipos (petición 25/10)


def candidatos_doble(prox, hist, arbitros):
    """'X o empate' (1X / X2) de un partido que se cumplen en ≥ 80 % (y ≥ 65 % en cada equipo), cuota ≥ 1,25."""
    partido = prox["partido"]
    if partido["fixture"]["status"]["short"] not in ("NS", "TBD") or \
            datetime.fromisoformat(partido["fixture"]["date"]) <= datetime.now(timezone.utc):
        return []
    loc, vis = partido["teams"]["home"], partido["teams"]["away"]
    h_loc = [(p, loc["id"]) for p in hist.get(loc["id"], [])[:ULTIMOS]]
    h_vis = [(p, vis["id"]) for p in hist.get(vis["id"], [])[:ULTIMOS]]
    if len(h_loc) < MIN_PARTIDOS or len(h_vis) < MIN_PARTIDOS:
        return []
    inicio = datetime.fromisoformat(partido["fixture"]["date"])
    base = {"partido_id": partido["fixture"]["id"], "fecha": inicio.astimezone(MADRID).strftime("%Y-%m-%dT%H:%M"),
            "competicion": COMPETICION.get(partido["league"]["id"], partido["league"]["name"]),
            "liga_id": partido["league"]["id"], "local": loc["name"], "visitante": vis["name"]}
    salida = []
    for opcion, cuota in (prox.get("cuotas") or {}).get("Double Chance", []):
        if opcion not in ("Home/Draw", "Draw/Away"):
            continue
        try:
            cuota = float(cuota)
        except (TypeError, ValueError):
            continue
        if cuota < DOBLE_CUOTA_MIN:
            continue
        a, na = frecuencia(evaluador("Double Chance", opcion, True), h_loc)
        b, nb = frecuencia(evaluador("Double Chance", opcion, False), h_vis)
        if na < MIN_PARTIDOS or nb < MIN_PARTIDOS:
            continue
        frec = (a + b) / (na + nb)
        if frec < DOBLE_FREC_MIN or min(a / na, b / nb) < DOBLE_FREC_EQ or frec <= 1 / cuota:
            continue
        eq = loc["name"] if opcion == "Home/Draw" else vis["name"]
        salida.append(dict(base, mercado="Double Chance", opcion=opcion, cuota=cuota, frecuencia=round(frec, 3),
                           ventaja=round(frec - 1 / cuota, 3), tipo="resultado", texto=f"{eq} o empate",
                           detalle=f"{loc['name']} {a}/{na} · {vis['name']} {b}/{nb}"))
    return enriquecer(salida, prox, hist, arbitros)


def combi_doble(cands):
    """5-6 'gana o empata' de partidos distintos, cuota total entre 5 y 20, los de más calidad primero."""
    elegidos, vistos, total = [], set(), 1.0
    for p in sorted(cands, key=lambda x: -calidad(x)):
        if p["partido_id"] in vistos or total * p["cuota"] > DOBLE_RANGO[1] or len(elegidos) >= DOBLE_PATAS[1]:
            continue
        elegidos.append(p)
        vistos.add(p["partido_id"])
        total *= p["cuota"]
    if len(elegidos) >= DOBLE_PATAS[0] and total >= DOBLE_RANGO[0]:
        return {"picks": elegidos, "cuota": round(total, 2)}
    return None


def main():
    ahora = datetime.now(timezone.utc)
    hist = historial()
    arbitros = indice_arbitros()
    todos, por_partido, dobles = [], {}, {}
    for f in sorted(EXTRA.glob("*.json")):
        prox = leer(f)
        if not (prox and prox.get("partido")):
            continue
        todos.extend(enriquecer(picks_partido(prox, hist, ahora), prox, hist, arbitros))
        for c in candidatos_doble(prox, hist, arbitros):
            dobles.setdefault(c["fecha"][:10], []).append(c)
        flojos = enriquecer(picks_partido(prox, hist, ahora, cuota_max=PARTIDO_CUOTA_MAX,
                                          frec_min=PARTIDO_FREC_MIN, frec_eq=PARTIDO_FREC_MIN - 0.05), prox, hist, arbitros)
        if flojos:
            por_partido[prox["partido"]["fixture"]["id"]] = flojos

    por_dia = defaultdict(list)
    for p in todos:
        por_dia[p["fecha"][:10]].append(p)
    combis_dia = {dia: combis_del_dia(sorted(l, key=lambda x: -calidad(x)))
                  for dia, l in por_dia.items()}
    partidos_dia = defaultdict(list)
    for fid, flojos in por_partido.items():
        dia = flojos[0]["fecha"][:10]
        # una selección va como mucho en 2 posts: si ya está en una combi del día, fuera de la del partido
        en_combis = {(p["partido_id"], p["mercado"], p["opcion"])
                     for c in (combis_dia.get(dia) or {}).values() if c for p in c["picks"]}
        c = combi_partido([p for p in flojos if (p["partido_id"], p["mercado"], p["opcion"]) not in en_combis])
        if c:
            partidos_dia[dia].append(dict(c, partido_id=fid, fecha=c["picks"][0]["fecha"],
                                          local=c["picks"][0]["local"], visitante=c["picks"][0]["visitante"],
                                          competicion=c["picks"][0]["competicion"]))

    salida = {"generado": datetime.now(MADRID).strftime("%Y-%m-%d %H:%M"),
              "criterios": {"cuota_min": CUOTA_MIN, "frecuencia_min": FREC_MIN,
                            "frecuencia_equipo_min": FREC_EQUIPO, "ultimos_partidos": ULTIMOS},
              "dias": {}}
    for dia in sorted(set(por_dia) | set(partidos_dia)):
        picks = sorted(por_dia[dia], key=lambda x: -calidad(x))
        mejores, vistos = [], set()
        for p in picks:
            if p["partido_id"] not in vistos:
                mejores.append(p)
                vistos.add(p["partido_id"])
        salida["dias"][dia] = {
            "picks": picks,
            "mejores_por_partido": mejores,
            "combis": dict(combis_dia.get(dia) or combis_del_dia(picks), doble=combi_doble(dobles.get(dia, []))),
            "combis_partido": sorted(partidos_dia[dia], key=lambda c: c["fecha"]),
        }

    (DATOS / "picks.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir_md(salida)
    tipos = defaultdict(int)
    for p in todos:
        tipos[p["tipo"]] += 1
    print(f"Picks: {len(todos)} en {len(por_dia)} días · por tipo: {dict(tipos)} · "
          f"combis de partido: {sum(len(v) for v in partidos_dia.values())}")


def num(c):
    return f"{c:.2f}".replace(".", ",")


def escribir_md(s):
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    out = ["# Picks del Analista", "",
           f"_Generado el {s['generado']} (hora España). Cuotas de Bet365. Criterio: cuota ≥ "
           f"{CUOTA_MIN:.2f}, cumplido en ≥ {FREC_MIN:.0%} de los últimos {ULTIMOS} partidos de los dos "
           f"equipos (≥ {FREC_EQUIPO:.0%} en cada uno) y por encima de lo que dice la cuota. Jugadores: "
           f"titulares fijos, ≥ {FREC_MIN:.0%} en sus últimos partidos._", ""]
    for dia, d in s["dias"].items():
        f = datetime.fromisoformat(dia)
        out += [f"## {dias_es[f.weekday()]} {f.strftime('%d/%m')}", ""]
        for nombre, titulo in (("segura", "🔒 Combi segura"), ("cuota_3", "💥 Combi cuota 3-4"), ("loca", "🤪 Combi loca")):
            c = d["combis"][nombre]
            if c:
                out.append(f"**{titulo} · cuota {num(c['cuota'])}**")
                out += [f"- {p['texto']} ({num(p['cuota'])}) · {p['detalle']}" for p in c["picks"]]
                out.append("")
        for c in d.get("combis_partido") or []:
            out.append(f"**🎯 Combi del partido {c['local']}–{c['visitante']} · cuota sumada {num(c['cuota_sumada'])}**")
            out += [f"- {p['texto']} ({num(p['cuota'])}) · {p['detalle']}" for p in c["picks"]]
            out.append("")
        out += ["| Hora | Pick | Tipo | Cuota | Se cumplió | Detalle |", "|---|---|---|---|---|---|"]
        for p in d["picks"]:
            out.append(f"| {p['fecha'][11:]} | {p['texto']} | {p['tipo']} | {p['cuota']:.2f} | "
                       f"{p['frecuencia']:.0%} | {p['detalle']} |")
        out.append("")
    (RAIZ / "PICKS.md").write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    main()
