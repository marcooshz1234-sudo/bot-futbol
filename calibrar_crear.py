"""
28/10 (Marcos): el bot aprende las cuotas reales de «Crear apuesta» de bet365.

1. MEDIDAS (datos/cuotas_medidas.json): cada vez que Marcos corrige la cuota total de una combi de un partido
   (editándola desde el bot del móvil sin tocar las patas, o con cuota_bet365 en la cola) se guarda:
   patas, cuota de cada una, lo que paga bet365 y cómo lo calculaba el bot (ajuste del modelo de goles y cada
   pareja de patas con su tipo). Se guarda en el momento, antes del partido (luego ya no hay cuotas que mirar).
2. AJUSTE (datos/ajuste_crear.json): con todas las medidas se calcula una corrección por tipo de pareja
   («goles+resultado/contrario», «resultado+tiros/mismo»…) y cuánto hay que fiarse del modelo de goles (beta),
   para que la cuota del bot se acerque a la real. Con pocas medidas las correcciones son pequeñas (se empujan a 0).
combis_dia.factor_crear() las aplica. Se ejecuta en el bucle cada 10 min.
"""
import json
import math
import re

from bot import DATOS, RAIZ, leer

MEDIDAS = DATOS / "cuotas_medidas.json"
AJUSTE = DATOS / "ajuste_crear.json"
SUAVE = 0.6        # cuánto se resiste a cambiar con pocas medidas (más alto = más prudente)
TOPE = 0.6         # corrección máxima por tipo de pareja (en log: ×0,55 … ×1,8)
CUOTA = re.compile(r"Cuota total aprox\.:\s*(\d+(?:[.,]\d+)?)")
PATA = re.compile(r"^(?:🎯|✅) .*\[x\d+\.\d\d\]$")


def medida(sel, cuotas, real, fuente, ident, fecha):
    """Foto del cálculo del bot para esta combi (sin lo aprendido) + lo que paga bet365."""
    import combis_dia as C
    patas = C.patas_de_sel(sel, cuotas)
    if len({p["partido_id"] for p in patas}) != 1 or len(patas) < 2:
        return None
    aj, parejas = C.rasgos(patas)
    return {"id": ident, "fecha": fecha, "fuente": fuente, "sel": sel, "cuotas": cuotas, "real": real,
            "multiplicando": round(math.prod(cuotas), 3), "aj": aj, "parejas": parejas}


def de_texto(t):
    m = CUOTA.search(t or "")
    return float(m.group(1).replace(",", ".")) if m else None


def nuevas(medidas):
    """Busca correcciones de Marcos que aún no estén guardadas."""
    ya = {m["id"]: m for m in medidas}
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    auto = leer(RAIZ / "publicaciones" / "auto.json", []) or []
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    ids_c = {p["id"] for p in cola}
    salida = []
    for p in cola + [p for p in auto if p["id"] not in ids_c]:
        if not p.get("sel") or not p.get("cuotas") or len(p["sel"]) != len(p["cuotas"]):
            continue
        real, fuente = None, None
        if p.get("cuota_bet365"):
            real, fuente = float(p["cuota_bet365"]), "cuota comprobada"
        editado = control.get("textos", {}).get(p["id"])
        if editado and "combi-partido" in p["id"]:
            antes = [l for l in p["texto"].splitlines() if PATA.match(l)]
            ahora = [l for l in editado.splitlines() if PATA.match(l)]
            nueva, vieja = de_texto(editado), de_texto(p["texto"])
            if antes and antes == ahora and nueva and vieja and abs(nueva - vieja) > 0.05:
                real, fuente = nueva, "editada por Marcos"
        if real is None:
            continue
        previo = ya.get(p["id"])
        if previo and abs(previo["real"] - real) < 0.005:
            continue
        try:
            m = medida(p["sel"], p["cuotas"], real, fuente, p["id"], p["fecha"])
        except Exception as e:
            print("medida:", str(e)[:120])
            continue
        if m:
            salida.append(m)
    return salida


def ajustar(medidas):
    """Correcciones por tipo de pareja y beta del modelo de goles (mínimos cuadrados con freno hacia 0)."""
    import numpy as np
    claves = sorted({k for m in medidas for k, _ in m["parejas"]})
    if not medidas:
        return {"claves": {}, "beta": 1.0, "n": 0}
    filas, ys = [], []
    for m in medidas:
        base = sum(math.log(v) for _, v in m["parejas"])
        laj = math.log(m["aj"]) if m.get("aj") else 0.0
        y = math.log(m["real"] / m["multiplicando"]) - base - laj   # lo que falta explicar con beta = 1
        x = [sum(1 for k2, _ in m["parejas"] if k2 == k) for k in claves] + [laj]
        filas.append(x)
        ys.append(y)
    n = len(claves) + 1
    A = np.vstack([np.array(filas, float), math.sqrt(SUAVE) * np.eye(n)])
    b = np.concatenate([np.array(ys, float), np.zeros(n)])
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    corr = {k: round(float(max(-TOPE, min(TOPE, v))), 4) for k, v in zip(claves, sol[:-1]) if abs(v) > 0.005}
    beta = round(float(max(0.3, min(1.5, 1 + sol[-1]))), 3)
    return {"claves": corr, "beta": beta, "n": len(medidas)}


def error_medio(medidas, aj_json):
    """Error medio (en %) entre la cuota del bot y la real, con y sin lo aprendido."""
    def pred(m, ap):
        f = (m["aj"] ** ap.get("beta", 1.0)) if m.get("aj") else 1.0
        for k, v in m["parejas"]:
            f *= v * math.exp((ap.get("claves") or {}).get(k, 0.0))
        return m["multiplicando"] * min(1.6, max(0.45, f))
    if not medidas:
        return None, None
    e0 = sum(abs(pred(m, {}) / m["real"] - 1) for m in medidas) / len(medidas)
    e1 = sum(abs(pred(m, aj_json) / m["real"] - 1) for m in medidas) / len(medidas)
    return round(100 * e0, 1), round(100 * e1, 1)


def main():
    medidas = leer(MEDIDAS, []) or []
    nuevos = nuevas(medidas)
    if nuevos:
        ids = {m["id"] for m in nuevos}
        medidas = [m for m in medidas if m["id"] not in ids] + nuevos
        MEDIDAS.write_text(json.dumps(medidas, ensure_ascii=False, indent=1), encoding="utf-8")
        for m in nuevos:
            print(f"Cuota real aprendida: {m['id']} → {m['real']} ({m['fuente']})")
    previo = leer(AJUSTE, {}) or {}
    if nuevos or not previo or previo.get("n") != len(medidas):
        aj = ajustar(medidas)
        aj["error_antes"], aj["error_ahora"] = error_medio(medidas, aj)
        AJUSTE.write_text(json.dumps(aj, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Ajuste de «Crear apuesta»: {aj['n']} medidas · error medio {aj['error_antes']} % → {aj['error_ahora']} %")


if __name__ == "__main__":
    main()
