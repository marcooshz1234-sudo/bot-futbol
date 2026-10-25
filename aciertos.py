"""
Registro de aciertos de los picks del bot.

Se ejecuta después de picks.py:
1. Guarda en datos/registro_aciertos.json cada pick que el bot ha elegido (cuota y
   frecuencia del momento en que se eligió; si cambia antes del partido, se actualiza).
2. Cuando el partido ha terminado (datos/partidos/), lo corrige con el mismo evaluador
   que usa picks.py.
3. Escribe ACIERTOS.md: aciertos por tipo de mercado y por mercado, y el detalle de los
   últimos días (sirve para el balance de las 23:30).
"""

import json
from collections import defaultdict
from datetime import datetime

from bot import DATOS, MADRID, PARTIDOS, RAIZ, leer
from picks import evaluar_pick

REGISTRO = DATOS / "registro_aciertos.json"


def clave(p):
    return f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"


def resultado(p):
    partido = leer(PARTIDOS / f"{p['partido_id']}.json")
    if not partido or partido.get("estado") not in ("FT", "AET", "PEN"):
        return None, None
    r = evaluar_pick(p, partido)
    g = partido.get("goles") or []
    marcador = f"{g[0]}-{g[1]}" if isinstance(g, list) and len(g) == 2 else None
    return (None if r is None else bool(r)), marcador


def main():
    reg = leer(REGISTRO, {}) or {}
    picks = leer(DATOS / "picks.json") or {}
    ahora = datetime.now(MADRID).strftime("%Y-%m-%dT%H:%M")

    for dia in (picks.get("dias") or {}).values():
        for p in dia.get("picks", []):
            k = clave(p)
            if k in reg and reg[k].get("acierto") is not None:
                continue
            if p["fecha"] <= ahora and k in reg:
                continue   # ya empezó: se queda la cuota con la que se eligió
            reg[k] = {c: p.get(c) for c in ("partido_id", "fecha", "competicion", "local", "visitante",
                                             "mercado", "opcion", "tipo", "texto", "cuota", "frecuencia",
                                             "jugador_id", "jugador", "campo", "n", "valor_mercado", "movimiento",
                                             "ventaja", "prob_aprendida")}
            reg[k]["acierto"] = None

    corregidos = 0
    for p in reg.values():
        if p.get("acierto") is None and p["fecha"] < ahora:
            r, marcador = resultado(p)
            if r is not None:
                p["acierto"], p["marcador"] = r, marcador
                corregidos += 1

    REGISTRO.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    escribir_md(reg)
    print(f"Registro de aciertos: {len(reg)} picks · corregidos ahora: {corregidos}")


def pct(s, n):
    return f"{s / n:.0%}" if n else "—"


def escribir_md(reg):
    hechos = [p for p in reg.values() if p.get("acierto") is not None]
    por_tipo, por_mercado = defaultdict(lambda: [0, 0, 0.0]), defaultdict(lambda: [0, 0, 0.0])
    for p in hechos:
        for d, k in ((por_tipo, p["tipo"]), (por_mercado, f"{p['mercado']} · {p['opcion']}")):
            d[k][0] += p["acierto"]
            d[k][1] += 1
            d[k][2] += (p["cuota"] - 1) if p["acierto"] else -1   # beneficio por 1 € apostado
    s = sum(p["acierto"] for p in hechos)
    out = ["# Aciertos de los picks del bot", "",
           f"Picks ya jugados: {len(hechos)} · aciertos: {s} ({pct(s, len(hechos))}) · "
           f"beneficio a 1 € por pick: {sum(v[2] for v in por_tipo.values()):+.2f} €", "",
           "## Por tipo", "", "| Tipo | Aciertos | Picks | % | Beneficio (1 €) |", "|---|---|---|---|---|"]
    for t, (a, n, b) in sorted(por_tipo.items(), key=lambda x: -x[1][0] / x[1][1]):
        out.append(f"| {t} | {a} | {n} | {pct(a, n)} | {b:+.2f} € |")
    out += ["", "## Por mercado (mín. 3 picks)", "", "| Mercado | Aciertos | Picks | % |", "|---|---|---|---|"]
    for m, (a, n, _) in sorted(por_mercado.items(), key=lambda x: -x[1][0] / x[1][1]):
        if n >= 3:
            out.append(f"| {m} | {a} | {n} | {pct(a, n)} |")
    out += ["", "## Últimos días", ""]
    por_dia = defaultdict(list)
    for p in hechos:
        por_dia[p["fecha"][:10]].append(p)
    for dia in sorted(por_dia, reverse=True)[:7]:
        l = por_dia[dia]
        out.append(f"### {dia} · {sum(p['acierto'] for p in l)}/{len(l)}")
        for p in sorted(l, key=lambda x: x["fecha"]):
            out.append(f"- {'✅' if p['acierto'] else '❌'} {p['texto']} · {p['cuota']:.2f} ({p.get('marcador') or ''})")
        out.append("")
    (RAIZ / "ACIERTOS.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
