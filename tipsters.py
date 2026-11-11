"""
09/11 (Marcos): los picks de TipsAnalistas y Tipster Pérez, «sí o sí».

- datos/tipsters.json: los picks que apunta Claude al leer sus canales (en las sesiones con Marcos):
  [{"tipster", "dia", "local", "visitante", "texto", "mercado", "opcion", "cuota", "argumento": [...]}]
  (mercado/opcion como los de API-Football: «Match Winner» Home/Away, «Double Chance» Home/Draw…;
  «Home/Away» = empate no válido; «Asian Handicap» «Home -0.25» = 0/-0,5).
- Este script casa cada pick con nuestro partido, lo corrige cuando acaba y aprende de ellos:
  qué mercados y equipos eligen, qué razones dan (diferencia de categoría, racha, bajas, casa…) y cuánto aciertan
  → datos/tipsters_aprendizaje.json.
- combis_dia.py usa picks_del_dia(): el pick del día sale de los suyos si el modelo no lo ve claramente mal,
  y la combi del día lleva uno suyo si encaja. Nunca se dice su nombre en los posts.
"""
import json
import re
import unicodedata
from collections import defaultdict

from bot import DATOS, leer

FICHERO = DATOS / "tipsters.json"
APRENDIZAJE = DATOS / "tipsters_aprendizaje.json"
TERMINADO = {"FT", "AET", "PEN"}
RAZONES = {   # palabras de su «argumento» → tipo de razón (para saber qué lógica funciona)
    "categoría": r"categor|divisi[oó]n|federaci|primera rfef|segunda rfef|tercera",
    "racha": r"racha|seguid|invict|victorias|sin perder|sin ganar|arranque",
    "bajas": r"baja|lesi[oó]n|no tiene|sanci|no est[aá]|duda|al 100",
    "casa/fuera": r"casa|local|campo|metropolitano|fuera de casa|visitante|lejos",
    "clasificación": r"\d+º|puesto|clasificaci|l[ií]der|tabla|zona|descenso",
    "goles": r"gol|encaja|marca|defens",
    "motivación": r"copa|primera vez|ilusi|se juega|necesita|motiva|l[ií]der antes",
}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    for x in (" fc", "fc ", " cf", "cf ", "real ", "club ", "cd ", "ud ", "sd ", "rcd ", " w"):
        s = s.replace(x, " ")
    return " ".join(s.replace(".", " ").replace("-", " ").split())


def casar(pk):
    """Busca nuestro partido (id de API-Football) por nombres y día en los calendarios."""
    l, v = norm(pk["local"]), norm(pk["visitante"])
    for f in DATOS.glob("calendario_*.json"):
        for p in leer(f, []) or []:
            if p["fixture"]["date"][:10] != pk["dia"]:
                continue
            hl, hv = norm(p["teams"]["home"]["name"]), norm(p["teams"]["away"]["name"])
            if (l[:5] in hl or hl[:5] in l) and (v[:5] in hv or hv[:5] in v):
                return p
    return None


def resultado(pk, goles):
    """verde / rojo / nulo (devuelven) / medio_verde / medio_rojo, con el marcador a los 90'."""
    gl, gv = goles
    m, o = pk.get("mercado"), str(pk.get("opcion") or "")
    if m == "Match Winner":
        return "verde" if (o == "Home" and gl > gv) or (o == "Away" and gv > gl) or (o == "Draw" and gl == gv) else "rojo"
    if m == "Double Chance":
        ok = {"Home/Draw": gl >= gv, "Draw/Away": gv >= gl, "Home/Away": gl != gv}.get(o)
        return None if ok is None else "verde" if ok else "rojo"
    if m == "Home/Away":   # empate no válido
        return "nulo" if gl == gv else "verde" if (o == "Home") == (gl > gv) else "rojo"
    if m == "Asian Handicap":
        lado, linea = o.split()
        d = (gl - gv) if lado == "Home" else (gv - gl)
        x = d + float(linea)
        if float(linea) * 4 % 2:   # línea partida (0/-0,5 = -0,25): media a cada lado
            a, b = x - 0.25, x + 0.25
            r = [("verde" if y > 0 else "nulo" if y == 0 else "rojo") for y in (a, b)]
            if r[0] == r[1]:
                return r[0]
            return "medio_rojo" if "rojo" in r else "medio_verde"
        return "verde" if x > 0 else "nulo" if x == 0 else "rojo"
    if m == "Goals Over/Under":
        n = float(o.split()[-1])
        return "verde" if (gl + gv > n) == o.startswith("Over") else "rojo"
    if m == "Both Teams Score":
        return "verde" if (gl > 0 and gv > 0) == (o == "Yes") else "rojo"
    if m in ("Total - Home", "Total - Away"):   # 11/11: goles de un equipo
        g = gl if m == "Total - Home" else gv
        n = float(o.split()[-1])
        return "verde" if (g > n) == o.startswith("Over") else "rojo"
    return None


def beneficio(estado, cuota):
    return {"verde": cuota - 1, "rojo": -1, "nulo": 0, "medio_verde": (cuota - 1) / 2,
            "medio_rojo": -0.5}.get(estado, 0)


def analizar(pk):
    """11/11: lo que ve el bot de cada pick de un tipster (para aprender por qué lo eligen):
    cuota de bet365, probabilidad que da la cuota, la justa de Pinnacle si la hay y la liga."""
    a = {}
    ex = leer(DATOS / "proximos" / f"{pk['partido_id']}.json", {}) or {}
    pa = ex.get("partido") or {}
    if pa.get("league"):
        a["liga"] = pa["league"].get("name")
    for o, c in (ex.get("cuotas") or {}).get(pk.get("mercado"), []) or []:
        if str(o) == str(pk.get("opcion")):
            try:
                a["cuota_bet365"] = float(c)
            except (TypeError, ValueError):
                pass
    cuota = pk.get("cuota") or a.get("cuota_bet365")
    if cuota:
        a["prob_cuota"] = round(1 / float(cuota), 3)
    try:
        import sharp
        pj = sharp.prob_justa(pk["partido_id"], pk.get("mercado"), pk.get("opcion"))
        if pj:
            a["prob_pinnacle"] = round(pj, 3)
            if cuota:
                a["valor_pinnacle"] = round(float(cuota) * pj - 1, 3)
    except Exception:
        pass
    return a


def bonus(p):
    """Ventaja para una pata del bot que coincide con el pick de un tipster ese día (mismo partido, mercado y opción).
    Más si ese tipster ya ha demostrado ganar (20+ picks resueltos en positivo); nada si ha demostrado perder."""
    if not hasattr(bonus, "hoy"):
        bonus.hoy = {}
        for pk in leer(FICHERO, []) or []:
            if pk.get("partido_id") and not pk.get("estado"):
                bonus.hoy.setdefault((pk["partido_id"], pk.get("mercado"), str(pk.get("opcion"))), []).append(pk["tipster"])
        bonus.ap = (leer(APRENDIZAJE, {}) or {}).get("tipster") or {}
    quienes = bonus.hoy.get((p.get("partido_id"), p.get("mercado"), str(p.get("opcion"))))
    if not quienes:
        return 0.0, []
    mejor = 0.0
    for t in quienes:
        c = bonus.ap.get(t) or {}
        resueltos = c.get("verdes", 0) + c.get("rojos", 0)
        mejor = max(mejor, 0.0 if resueltos >= 20 and c.get("unidades", 0) < 0 else
                    0.05 if resueltos >= 20 else 0.02)
    return mejor, quienes


def actualizar():
    lista = leer(FICHERO, []) or []
    for pk in lista:
        if not pk.get("partido_id"):
            p = casar(pk)
            if p:
                pk["partido_id"] = p["fixture"]["id"]
        if pk.get("partido_id") and "analisis" not in pk:
            pk["analisis"] = analizar(pk)
        if pk.get("estado") or not pk.get("partido_id"):
            continue
        pa = leer(DATOS / "partidos" / f"{pk['partido_id']}.json", {}) or {}
        g = pa.get("goles_90") or pa.get("goles")
        if pa.get("estado") in TERMINADO and g and None not in g:
            pk["estado"] = resultado(pk, g)
            pk["marcador"] = g
    FICHERO.write_text(json.dumps(lista, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return lista


def aprender(lista):
    """Qué eligen y por qué, y cuánto aciertan (por tipster, mercado, equipo elegido y tipo de razón)."""
    def caja():
        return {"n": 0, "verdes": 0, "rojos": 0, "nulos": 0, "unidades": 0.0}
    por = {k: defaultdict(caja) for k in ("tipster", "mercado", "equipo", "razon", "cuota", "liga", "lado", "por_que",
                                          "valor_pinnacle")}
    for pk in lista:
        claves = {"tipster": [pk["tipster"]], "mercado": [f"{pk.get('mercado')} {pk.get('opcion')}"],
                  "equipo": [pk["local"] if str(pk.get("opcion", "")).startswith("Home") else
                             pk["visitante"] if str(pk.get("opcion", "")).startswith(("Away", "Draw/Away")) else "—"],
                  "razon": [k for k, rx in RAZONES.items() if re.search(rx, " ".join(pk.get("argumento") or []), re.I)]
                  or ["sin razón"],
                  "cuota": ["?" if not pk.get("cuota") else "<1,50" if pk["cuota"] < 1.5 else "1,50-1,80" if pk["cuota"] < 1.8 else "1,80-2,20"
                            if pk["cuota"] < 2.2 else ">2,20"],
                  # 11/11: más cosas para entender cómo eligen
                  "liga": [(pk.get("analisis") or {}).get("liga") or "?"],
                  "lado": ["local" if str(pk.get("opcion", "")).startswith(("Home", "Over")) and pk.get("mercado") in
                           ("Match Winner", "Double Chance", "Asian Handicap", "Total - Home", "Home/Away") or pk.get("mercado") == "Total - Home"
                           else "visitante" if str(pk.get("opcion", "")).startswith(("Away", "Draw/Away")) or pk.get("mercado") == "Total - Away"
                           else "partido"],
                  "por_que": [k for k, rx in RAZONES.items() if re.search(rx, " ".join(pk.get("por_que") or []), re.I)]
                  or ["—"],
                  "valor_pinnacle": ["?" if (pk.get("analisis") or {}).get("valor_pinnacle") is None else
                                     "con valor" if pk["analisis"]["valor_pinnacle"] >= 0 else "sin valor"]}
        for dim, ks in claves.items():
            for k in ks:
                c = por[dim][k]
                c["n"] += 1
                e = pk.get("estado")
                if e in ("verde", "medio_verde"):
                    c["verdes"] += 1
                elif e in ("rojo", "medio_rojo"):
                    c["rojos"] += 1
                elif e == "nulo":
                    c["nulos"] += 1
                if e and pk.get("cuota"):
                    c["unidades"] = round(c["unidades"] + beneficio(e, pk["cuota"]), 2)
                if e in ("verde", "rojo", "medio_verde", "medio_rojo") and pk.get("cuota"):
                    c["resueltos_con_cuota"] = c.get("resueltos_con_cuota", 0) + 1
                    c["prob_cuota"] = round(c.get("prob_cuota", 0) + 1 / pk["cuota"], 3)   # suma: aciertos esperados según la cuota
    salida = {dim: dict(sorted(v.items(), key=lambda x: -x[1]["n"])) for dim, v in por.items()}
    APRENDIZAJE.write_text(json.dumps(salida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return salida


def picks_del_dia(dia):
    """Los picks de los tipsters para ese día (ya casados con nuestro partido)."""
    return [pk for pk in leer(FICHERO, []) or [] if pk.get("dia") == dia and pk.get("partido_id")]


if __name__ == "__main__":
    l = actualizar()
    a = aprender(l)
    for k, c in a["tipster"].items():
        print(f"{k}: {c['n']} picks · {c['verdes']} ✅ {c['rojos']} ❌ {c['nulos']} nulos · {c['unidades']:+.2f} u")
