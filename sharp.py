"""11/11 (Marcos: «la 1, impleméntala»): Pinnacle como referencia.

Pinnacle es la casa que mejor ajusta (margen bajo, apuestas de profesionales). Quitándole su margen sale la
probabilidad «justa» de cada mercado. Con eso:
  - si bet365 paga MENOS que la cuota justa de Pinnacle (valor esperado < -3 %), la pata no se usa (está cara);
  - si paga igual o más, la pata vale y su probabilidad pasa a ser la de Pinnacle (más fiable que nuestro modelo).
Solo para los partidos que baja fuentes_extra.oddspapi (datos/cuotas_sharp.json, plan gratis: ~5 al día) y para
los mercados cuyo código de OddsPapi está comprobado. En el resto no cambia nada.

Códigos de OddsPapi (comprobados con bet365 y Pinnacle del 10/11, Inter–City y Trival Valderas–Leganés):
  101: 1X2 (101 local, 102 empate, 103 visitante) · 104: ambos marcan (104 sí, 105 no)
  106/108/1010/1012/…: goles más/menos de 0,5/1,5/2,5/3,5/… (par = más, impar = menos)
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
RUTA = RAIZ / "datos" / "cuotas_sharp.json"
UMBRAL = -0.03   # bet365 un 3 % por debajo de la justa → cara
LINEAS = {"0.5": "106", "1.5": "108", "2.5": "1010", "3.5": "1012", "4.5": "1014", "5.5": "1016"}


def _datos():
    if not hasattr(_datos, "c"):
        try:
            _datos.c = json.loads(RUTA.read_text(encoding="utf-8")).get("partidos") or {}
        except Exception:
            _datos.c = {}
    return _datos.c


def _mercado(fid, casa, codigo):
    try:
        m = _datos()[str(fid)]["cuotas"]["bookmakerOdds"][casa]["markets"][codigo]["outcomes"]
    except (KeyError, TypeError):
        return None
    out = {}
    for oid, v in m.items():
        precios = [p.get("price") for p in (v.get("players") or {}).values() if p.get("active", True) and p.get("price")]
        if precios:
            out[oid] = float(precios[0])
    return out


def _justas(fid, codigo, salidas):
    """Probabilidades sin margen de Pinnacle para esas salidas (todas tienen que estar)."""
    m = _mercado(fid, "pinnacle", codigo)
    if not m or any(s not in m for s in salidas):
        return None
    inv = {s: 1 / m[s] for s in salidas}
    tot = sum(inv.values())
    return {s: inv[s] / tot for s in salidas} if tot > 0 else None


def prob_justa(fid, mercado, opcion):
    """Probabilidad justa (Pinnacle sin margen) de la pata, o None si no hay dato fiable."""
    opcion = str(opcion)
    if mercado == "Match Winner":
        j = _justas(fid, "101", ["101", "102", "103"])
        return j and j.get({"Home": "101", "Draw": "102", "Away": "103"}.get(opcion))
    if mercado == "Double Chance":
        j = _justas(fid, "101", ["101", "102", "103"])
        if not j:
            return None
        return {"Home/Draw": j["101"] + j["102"], "Draw/Away": j["102"] + j["103"],
                "Home/Away": j["101"] + j["103"]}.get(opcion)
    if mercado == "Both Teams Score":
        j = _justas(fid, "104", ["104", "105"])
        return j and j.get({"Yes": "104", "No": "105"}.get(opcion))
    if mercado == "Goals Over/Under":
        partes = opcion.split()
        if len(partes) == 2 and partes[1] in LINEAS:
            c = LINEAS[partes[1]]
            otra = str(int(c) + 1)
            j = _justas(fid, c, [c, otra])
            return j and j.get(c if partes[0] == "Over" else otra)
    return None


def veredicto(p):
    """(prob_justa, valor_esperado) de una pata con su cuota de bet365, o (None, None)."""
    pj = prob_justa(p.get("partido_id"), p.get("mercado"), p.get("opcion"))
    if not pj or not p.get("cuota"):
        return None, None
    return pj, float(p["cuota"]) * pj - 1


def filtrar(pool):
    """Quita las patas caras según Pinnacle y pone la probabilidad de Pinnacle en las que valen."""
    salida = []
    for p in pool:
        pj, ev = veredicto(p)
        if pj is None:
            salida.append(p)
            continue
        if ev < UMBRAL:
            print(f"Pinnacle: fuera «{p.get('texto')}» @{p['cuota']} (justa {1 / pj:.2f}, {ev:+.0%})")
            continue
        salida.append(dict(p, prob_aprendida=round(pj, 3), prob_pinnacle=round(pj, 3), ev_pinnacle=round(ev, 3),
                           detalle=(p.get("detalle") or "") + f" · Pinnacle {1 / pj:.2f}"))
    return salida
