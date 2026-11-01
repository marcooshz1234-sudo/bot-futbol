"""
01/11 (Marcos): informe de redes del mes (informes/redes/AAAA-MM.md) para su Obsidian (03 Redes/Rendimiento redes).
Seguidores, top posts de Threads con su gancho (primera línea), visitas por pilar, por hora y por día de la semana.
Lo llama recoger.yml; un Atajo del iPhone lo guarda en la bóveda cada lunes. A mano: python redes_informe.py 2026-10
"""
import re
import sys
from collections import defaultdict
from datetime import datetime

from bot import DATOS, MADRID, RAIZ, leer

SALIDA = RAIZ / "informes" / "redes"
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
PILARES = [  # (pilar, patrón de la primera línea / texto) · ver «Pilares y calendario» en Obsidian
    ("Prueba social", r"¡VERDE|OTRO VERDE|VERDE DEL D|POR UN C[ÓO]RNER|A UN (GOL|EMPATE)|PLENO|CASH OUT"),
    ("Lo que juego yo", r"PERSONAL|LA LLEVO YO|VERDADERA COMBILOCA|MI COMBI|CREAR APUESTA|MONTADA EN BET365|SUPERAUMENTO|SOÑADORA"),
    ("Combis con escudos", r"COMBI LOCAS \|"),
    ("Utilidad", r"PICKS PARA|QUIÉN GANA|OPCIONES|PARTIDOS SUELTOS|UN PICK POR PARTIDO|MEJORES CUOTAS"),
    ("Retos", r"ESCALERA|500€|LA LOCA|COMBI LOCA|LA GRANDE|LA LARGA|x\d{2,}"),
    ("Partido estrella", r"🆚|RADAR|PARTIDO TRAMPA|JUGADOR DEL D"),
    ("Temáticos del día", r"(LUNES|MARTES|MIÉRCOLES|JUEVES|VIERNES|SÁBADO|DOMINGO) DE |GOLEADORES|ASISTENTES|PORTEROS|TARJETAS|AMBOS MARCAN|MITADES|PARTES"),
    ("Vidilla / comunidad", r"PREGUNTA|^@|GUÍA|BALANCE|RESUMEN|ASÍ FUE"),
]


def pilar(texto):
    t = (texto or "").upper()
    for nombre, patron in PILARES:
        if re.search(patron, t):
            return nombre
    return "Combis (otras)"


def posts_threads():
    """[(visitas, fecha Madrid, texto)] de los posts de Threads con visitas guardadas."""
    vistas = leer(DATOS / "threads_vistas.json", {}) or {}
    textos = {}
    for p in (leer(DATOS / "threads_analisis.json", {}) or {}).get("posts") or []:
        try:
            f = datetime.fromisoformat(p["timestamp"].replace("+0000", "+00:00")).astimezone(MADRID)
        except Exception:
            continue
        textos[p["id"]] = (f, p.get("text") or "")
    for nombre in ("auto.json", "cola.json"):
        for p in leer(RAIZ / "publicaciones" / nombre, []) or []:
            tid = str((p.get("redes") or {}).get("threads") or "")
            if tid and tid not in textos and p.get("fecha"):
                textos[tid] = (datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID), p.get("texto") or "")
    return [(v, *textos[k]) for k, v in vistas.items() if k in textos and isinstance(v, (int, float))]


def mediana(x):
    x = sorted(x)
    return x[len(x) // 2] if x else 0


def tabla(filas, cab):
    return "\n".join(["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
                     + ["| " + " | ".join(str(c) for c in f) + " |" for f in filas])


def informe(mes):
    ahora = datetime.now(MADRID)
    todos = posts_threads()
    posts = [p for p in todos if p[1].strftime("%Y-%m") == mes]
    l = [f"---\ntipo: redes\nmes: {mes}\nactualizado: {ahora:%Y-%m-%d %H:%M}\n---", f"# Redes · {mes}", "",
         "Lo genera el bot (`redes_informe.py`) y llega solo cada lunes. Pilares: [[Pilares y calendario]] · "
         "Ganchos: [[Banco de hooks]].", ""]
    est = leer(RAIZ / "publicaciones" / "estadisticas.json", {}) or {}
    seg = {k: v for k, v in (est.get("redes") or {}).items() if k != "facebook"}
    if seg:
        l += ["## Seguidores (ahora)", tabla([[k.capitalize(), (v.get("seguidores") if isinstance(v, dict) else v)]
                                              for k, v in seg.items()], ["Red", "Seguidores"]), ""]
    if not posts:
        return "\n".join(l + ["Todavía no hay visitas de Threads guardadas de este mes."]) + "\n"
    l += [f"## Threads · {len(posts)} posts · {sum(p[0] for p in posts):,} visitas".replace(",", "."), ""]
    top = sorted(posts, key=lambda p: -p[0])[:15]
    l += ["## Top 15 (ganchos que han funcionado)",
          tabla([[f"{v:,}".replace(",", "."), f"{f:%d/%m %H:%M}", pilar(t), (t.strip().splitlines() or [""])[0][:70]]
                 for v, f, t in top], ["Visitas", "Cuándo", "Pilar", "Primera línea"]), ""]
    g = defaultdict(list)
    for v, f, t in posts:
        g[pilar(t)].append(v)
    l += ["## Por pilar (mediana de visitas)", tabla(sorted([[k, len(x), f"{mediana(x):,}".replace(",", "."), f"{max(x):,}".replace(",", ".")]
                                                             for k, x in g.items()], key=lambda r: -int(r[2].replace(".", ""))),
                                                      ["Pilar", "Posts", "Mediana", "Máximo"]), ""]
    h = defaultdict(list)
    for v, f, t in posts:
        h[f.hour].append(v)
    l += ["## Por hora", tabla([[f"{k:02d}:00", len(x), f"{mediana(x):,}".replace(",", ".")] for k, x in sorted(h.items())],
                               ["Hora", "Posts", "Mediana"]), ""]
    d = defaultdict(list)
    for v, f, t in posts:
        d[f.weekday()].append(v)
    l += ["## Por día", tabla([[DIAS[k], len(x), f"{mediana(x):,}".replace(",", ".")] for k, x in sorted(d.items())],
                              ["Día", "Posts", "Mediana"]), ""]
    peor = sorted(posts, key=lambda p: p[0])[:5]
    l += ["## Lo que menos ha funcionado", tabla([[v, f"{f:%d/%m %H:%M}", pilar(t), (t.strip().splitlines() or [""])[0][:70]]
                                                  for v, f, t in peor], ["Visitas", "Cuándo", "Pilar", "Primera línea"]), ""]
    return "\n".join(l) + "\n"


def main(meses=None):
    hoy = datetime.now(MADRID)
    meses = meses or [f"{hoy:%Y-%m}"]
    SALIDA.mkdir(parents=True, exist_ok=True)
    for mes in meses:
        (SALIDA / f"{mes}.md").write_text(informe(mes), encoding="utf-8")
        print(f"Redes: informes/redes/{mes}.md")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
