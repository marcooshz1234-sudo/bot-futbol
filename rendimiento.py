"""
01/11 (Marcos): informe de rendimiento del canal, un archivo por mes (informes/rendimiento/AAAA-MM.md).
Va a su bóveda de Obsidian (02 Apuestas/Rendimiento) con un Atajo del iPhone cada lunes.

  - ROI con 10 € simulados por combi publicada (verde: +10 × (cuota − 1); roja: −10).
  - Semana a semana, por formato (escudos, x3, loca, 1€ a 500€, escalera, quién gana…) y por tipo de pata.
  - Por equipo y por escenario (favorito claro / igualado, se esperaban goles / cerrado, y lo que pasó).
  - Lecciones propuestas CON SU CONTEXTO (Marcos: «no siempre es el mismo pick: depende del partido, de lo
    esperado y del resultado, igual solo falla con algunos equipos»). No cambian el bot solas: se le preguntan.
Se ejecuta en recoger.yml. También a mano: python rendimiento.py 2026-10
"""
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer

SALIDA = RAIZ / "informes" / "rendimiento"
STAKE = 10.0
FAMILIAS = {"goles": "Goles", "resultado": "Resultado", "corners": "Córners", "jugador": "Jugadores",
            "tarjetas": "Tarjetas", "tiros": "Tiros", "fueras": "Fueras de juego"}
MIN_LECCION = 4        # patas mínimas de un grupo para proponer una lección
MALO, BUENO = 0.35, 0.85


def eur(x):
    return f"{x:+.2f} €".replace(".", ",")


def pct(a, n):
    return f"{round(100 * a / n)} %" if n else "—"


def formato(pid):
    from panel_datos import tipo_post
    t = tipo_post(pid)
    if t != "Otros":
        return t
    resto = pid[11:]
    if "combi-500" in resto:
        return "De 1€ a 500€"
    if re.search(r"loca", resto):
        return "La loca"
    if re.search(r"cuota3|combi-tres", resto):
        return "Combi x3"
    if re.search(r"segura", resto):
        return "La segura"
    if re.match(r"combi-[a-z]+-[a-z-]+$", resto) and resto not in ("combi-dia", "combi-liga", "combi-tema"):
        return "Combi de un partido (antigua)"
    return "Otras combis"


def posts_por_id():
    out = {}
    for f in ("auto.json", "cola.json"):
        for p in leer(RAIZ / "publicaciones" / f, []) or []:
            out.setdefault(p["id"], p)
    return out


def resultado_pata(sel, reg):
    """True / False / None (sin resolver o anulada)."""
    r = reg.get(sel)
    if r and r.get("acierto") is not None:
        return bool(r["acierto"])
    try:
        from app_datos import fila_sel
        e = fila_sel(sel, None, {}, [])["estado"]
        return True if e == "verde" else False if e == "rojo" else None
    except Exception:
        return None


def escenario(pid):
    """(favorito, esperado, real) del partido: con los goles esperados de bet365 (datos/goles_previos.json) y
    el resultado a los 90 min (datos/partidos)."""
    g = (leer(DATOS / "goles_previos.json", {}) or {}).get(str(pid)) or {}
    d = leer(DATOS / "partidos" / f"{pid}.json", {}) or {}
    fav = esp = real = None
    if g.get("l") is not None and g.get("v") is not None:
        dif = g["l"] - g["v"]
        fav = "local favorito claro" if dif >= 0.6 else "visitante favorito claro" if dif <= -0.6 else "igualado"
        esp = "se esperaban goles" if g["l"] + g["v"] >= 2.8 else "se esperaba cerrado" if g["l"] + g["v"] <= 2.2 else "normal"
    goles = d.get("goles") or [None, None]
    if None not in goles:
        t = goles[0] + goles[1]
        real = "con goles (3+)" if t >= 3 else "cerrado (0-1)" if t <= 1 else "2 goles"
    nombres = ((d.get("local") or {}).get("nombre"), (d.get("visitante") or {}).get("nombre"))
    return fav, esp, real, nombres, goles


def datos_mes(mes):
    resumenes = leer(RAIZ / "docs" / "resumenes.json", {}) or {}
    posts = posts_por_id()
    reg = leer(DATOS / "registro_aciertos.json", {}) or {}
    combis, patas = [], []
    for dia, r in sorted(resumenes.items()):
        if not dia.startswith(mes):
            continue
        for c in r.get("combis") or []:
            if c.get("estado") not in ("verde", "rojo") or not c.get("cuota"):
                continue
            ganancia = STAKE * (c["cuota"] - 1) if c["estado"] == "verde" else -STAKE
            p = posts.get(c["id"]) or {}
            combis.append({"id": c["id"], "dia": dia, "formato": formato(c["id"]), "cuota": c["cuota"],
                           "estado": c["estado"], "ganancia": ganancia, "titulo": c.get("titulo", ""),
                           "texto": p.get("texto", "")})
            for s in p.get("sel") or []:
                if s.split("|")[0] in ("0", ""):
                    continue
                ok = resultado_pata(s, reg)
                if ok is None:
                    continue
                import mis_datos
                fam = mis_datos.familia_sel(s)[0]
                pid = int(s.split("|")[0])
                fav, esp, real, nombres, goles = escenario(pid)
                try:
                    from picks import texto_pick
                    texto = texto_pick(*s.split("|", 2)[1:], *(n or "" for n in nombres))
                except Exception:
                    texto = s.split("|", 1)[1]
                patas.append({"sel": s, "ok": ok, "familia": fam, "fav": fav, "esp": esp, "real": real,
                              "equipos": [n for n in nombres if n], "texto": texto, "combi": c["id"]})
    return combis, patas


def tabla(filas, cab):
    out = ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
    out += ["| " + " | ".join(str(x) for x in f) + " |" for f in filas]
    return "\n".join(out)


def grupos(patas, clave):
    g = defaultdict(lambda: [0, 0])
    for p in patas:
        for k in clave(p):
            if k:
                g[k][0] += p["ok"]
                g[k][1] += 1
    return g


def lecciones(patas):
    """Grupos con contexto (tipo de pata × escenario, tipo de pata × equipo) que fallan o aciertan mucho."""
    props = []
    combos = {
        "tipo de partido": lambda p: [(p["familia"], p["fav"])] if p["fav"] else [],
        "lo esperado": lambda p: [(p["familia"], p["esp"])] if p["esp"] and p["esp"] != "normal" else [],
        "equipo": lambda p: [(p["familia"], e) for e in p["equipos"]],
    }
    for nombre, f in combos.items():
        for (fam, ctx), (a, n) in grupos(patas, f).items():
            if n < MIN_LECCION:
                continue
            tasa = a / n
            if tasa <= MALO or tasa >= BUENO:
                ejemplos = [p["texto"] for p in patas if p["familia"] == fam and (ctx in p["equipos"] or ctx in (p["fav"], p["esp"], p["real"]))]
                ejemplos = list(dict.fromkeys(ejemplos))[:3]
                props.append((tasa, fam, nombre, ctx, a, n, ejemplos))
    props.sort(key=lambda x: (x[0] > 0.5, x[0] if x[0] <= 0.5 else -x[0], -x[5]))
    return props


def esperado_vs_real(combis):
    """Combis de escudos: ¿el resultado fue uno de los «probables» del post?"""
    a = n = 0
    for c in combis:
        m = re.search(r"Resultado probable: ([\d\- |]+)", c["texto"])
        pid = re.search(r"combi-partido-(\d+)", c["id"])
        if not m or not pid:
            continue
        d = leer(DATOS / "partidos" / f"{pid.group(1)}.json", {}) or {}
        g = d.get("goles_90") if None not in (d.get("goles_90") or [None]) else d.get("goles")
        if not g or None in g:
            continue
        probables = [x.strip() for x in m.group(1).split("|")]
        n += 1
        a += f"{g[0]}-{g[1]}" in probables
    return a, n


def informe(mes):
    combis, patas = datos_mes(mes)
    hoy = datetime.now(MADRID)
    l = [f"---\ntipo: rendimiento\nmes: {mes}\nactualizado: {hoy:%Y-%m-%d %H:%M}\n---",
         f"# Rendimiento · {mes}", "",
         f"Canal @combilocas · **{STAKE:.0f} € simulados por combi publicada** · se actualiza solo cada lunes "
         "(lo genera el bot: `rendimiento.py`). Lecciones: [[Lecciones]].", ""]
    if not combis:
        return "\n".join(l + ["Todavía no hay combis resueltas este mes."]) + "\n"
    v = sum(c["estado"] == "verde" for c in combis)
    gan = sum(c["ganancia"] for c in combis)
    apostado = STAKE * len(combis)
    l += ["## Resumen", tabla([[len(combis), v, len(combis) - v, f"{apostado:.0f} €", f"{apostado + gan:.2f} €".replace(".", ","),
                                 eur(gan), f"{100 * gan / apostado:+.1f} %".replace(".", ",")]],
                                ["Combis", "✅", "❌", "Apostado", "Devuelto", "Beneficio", "ROI"]), ""]
    # semanas
    sem = defaultdict(list)
    for c in combis:
        d = date.fromisoformat(c["dia"])
        sem[d - timedelta(days=d.weekday())].append(c)
    l += ["## Semana a semana", tabla([[f"{k:%d/%m}–{k + timedelta(days=6):%d/%m}", len(cs), sum(c['estado'] == 'verde' for c in cs),
                                        eur(sum(c['ganancia'] for c in cs)),
                                        f"{100 * sum(c['ganancia'] for c in cs) / (STAKE * len(cs)):+.0f} %"]
                                       for k, cs in sorted(sem.items())], ["Semana", "Combis", "✅", "Beneficio", "ROI"]), ""]
    # formatos
    fmt = defaultdict(list)
    for c in combis:
        fmt[c["formato"]].append(c)
    l += ["## Por formato", tabla(sorted([[k, len(cs), pct(sum(c['estado'] == 'verde' for c in cs), len(cs)),
                                           eur(sum(c['ganancia'] for c in cs))] for k, cs in fmt.items()],
                                         key=lambda x: -float(x[3].split()[0].replace(",", "."))),
                                  ["Formato", "Combis", "Acierto", "Beneficio"]), ""]
    # tipo de pata
    if patas:
        g = grupos(patas, lambda p: [p["familia"]])
        l += ["## Por tipo de pata", f"{len(patas)} patas resueltas de las combis publicadas.", "",
              tabla(sorted([[FAMILIAS.get(k, k), n, a, pct(a, n)] for k, (a, n) in g.items()], key=lambda x: -x[1]),
                    ["Tipo", "Patas", "✅", "Acierto"]), ""]
        # equipos
        ge = {k: x for k, x in grupos(patas, lambda p: p["equipos"]).items() if x[1] >= 4}
        if ge:
            orden = sorted(ge.items(), key=lambda kv: kv[1][0] / kv[1][1])
            l += ["## Por equipo (patas de sus partidos, mínimo 4)",
                  "**Donde más fallamos**", "", tabla([[k, n, pct(a, n)] for k, (a, n) in orden[:8]], ["Equipo", "Patas", "Acierto"]), "",
                  "**Donde más acertamos**", "", tabla([[k, n, pct(a, n)] for k, (a, n) in orden[::-1][:8]], ["Equipo", "Patas", "Acierto"]), ""]
        # escenarios
        l += ["## Por escenario"]
        for titulo, f in (("Tipo de partido", lambda p: [p["fav"]]), ("Lo esperado", lambda p: [p["esp"]]),
                          ("Lo que pasó", lambda p: [p["real"]])):
            g = grupos(patas, f)
            if g:
                l += [f"**{titulo}**", "", tabla([[k, n, pct(a, n)] for k, (a, n) in sorted(g.items(), key=lambda kv: -kv[1][1])],
                                                  ["", "Patas", "Acierto"]), ""]
    a, n = esperado_vs_real(combis)
    if n:
        l += [f"**Resultado probable de las combis de escudos:** acertado en {a} de {n} ({pct(a, n)}).", ""]
    # mejor y peor
    verdes = sorted([c for c in combis if c["estado"] == "verde"], key=lambda c: -c["cuota"])
    if verdes:
        l += [f"**Mejor combi:** {verdes[0]['titulo']} · x{verdes[0]['cuota']:.2f} ({verdes[0]['dia']})".replace(".", ",", 1)]
    l += [""]
    # lecciones
    props = lecciones(patas)
    l += ["## Lecciones propuestas", "Con su contexto (tipo de partido, lo esperado o el equipo): se sabe ANTES del partido, "
          "así que se pueden aplicar. Solo en ese contexto. "
          "No cambian el bot hasta que Marcos dice que sí (se pasan a [[Lecciones]]).", ""]
    if not props:
        l += ["Aún no hay ningún grupo con datos suficientes (mínimo 4 patas) que falle o acierte claramente."]
    for tasa, fam, nombre, ctx, a, n, ej in props[:10]:
        icono = "🔴" if tasa <= 0.5 else "🟢"
        l += [f"- {icono} **{FAMILIAS.get(fam, fam)} · {nombre}: {ctx}** → {a} de {n} ({pct(a, n)})"
              + (f"  \n  Ejemplos: {'; '.join(ej)}" if ej else "")]
    return "\n".join(l) + "\n"


def main(meses=None):
    hoy = datetime.now(MADRID).date()
    if not meses:
        meses = [f"{hoy:%Y-%m}"] + ([f"{hoy - timedelta(days=7):%Y-%m}"] if (hoy - timedelta(days=7)).month != hoy.month else [])
    SALIDA.mkdir(parents=True, exist_ok=True)
    for mes in meses:
        (SALIDA / f"{mes}.md").write_text(informe(mes), encoding="utf-8")
        print(f"Rendimiento: informes/rendimiento/{mes}.md")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
