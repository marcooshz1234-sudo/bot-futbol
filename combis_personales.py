"""
15/11 (Marcos: «así quiero dos diferentes todos los días a partir de ahora, pero no en Telegram»).
Dos combinadas largas al día (8–12 partidos) «de las mías»: quién gana, ambos marcan, ambos reciben tarjeta y tiro a
puerta. Solo Threads e Instagram. Se generan solas:
  · A a las 11:30 y B a las 12:30, con los partidos desde las 13:00 repartidos (uno para cada una: no comparten
    partido ni selección). 6–12 patas, hasta @120 más o menos
Con los datos que hay (cuotas de bet365 en resumen_proximos.json): quién gana y ambos marcan con cuota real;
«ambos reciben tarjeta» solo cuando los dos ven ≥2 amarillas por partido y el total de tarjetas sube de 3,5/4,5
(cuota estimada, marcada como aprox.). Tiro a puerta no se pone solo (sin alineaciones es un riesgo).
"""
import json
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer

COLA = RAIZ / "publicaciones" / "cola.json"
ESTADO = DATOS / "personales.json"
TANDAS = {"a": ("11:30", "13:00"), "b": ("12:30", "13:00")}   # los partidos del día se reparten: uno sí, uno no
MIN_PATAS, MAX_PATAS = 6, 12


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _pct(x):
    try:
        return int(str(x).rstrip("%"))
    except ValueError:
        return 0


def opciones(p):
    """Todas las patas que valen de un partido, de la mejor a la peor (sel, texto, cuota, aprox)."""
    from plantillas import es
    c = p.get("cuotas_bet365") or {}
    g = lambda m, k: next((_num(v) for n, v in c.get(m, []) if n == k), None)
    sl, sv = p.get("stats_local") or {}, p.get("stats_visitante") or {}
    L, V = limpio(es(p["local"])), limpio(es(p["visitante"]))
    partido = f"{L}–{V}"
    out = []
    for lado, k, nombre in (("local", "Home", L), ("visitante", "Away", V)):
        cu = g("Match Winner", k)
        forma = (sl if lado == "local" else sv).get("forma", "")
        if cu and 1.15 <= cu <= 1.95 and (forma.count("V") >= 2 or cu <= 1.65):
            art = "" if nombre in _paises() else "el "
            out.append((f"{p['id']}|Match Winner|{k}", f"Gana {art}{nombre}", cu, False, -cu))
    cu = g("Both Teams Score", "Yes")
    if cu and 1.45 <= cu <= 1.85 and _pct(sl.get("btts")) + _pct(sv.get("btts")) >= 100 and min(_pct(sl.get("btts")), _pct(sv.get("btts"))) >= 40:
        out.append((f"{p['id']}|Both Teams Score|Yes", f"Ambos marcan en {partido}", cu, False, -cu - 0.05))
    am_l, am_v = _num(sl.get("amarillas")) or 0, _num(sv.get("amarillas")) or 0
    tot = c.get("Cards Over/Under") or []
    linea_alta = any(n in ("Over 3.5", "Over 4.5") for n, _ in tot)
    if am_l >= 2.0 and am_v >= 2.0 and linea_alta:
        out.append((f"{p['id']}|Ambos tarjeta|Sí", f"Ambos reciben tarjeta en {partido}", 1.40, True, -1.45))
    return sorted(out, key=lambda o: -o[4])


ARREGLOS = {"Cadiz": "Cádiz", "Atletico Madrid": "Atlético", "Atletico": "Atlético", "Deportivo de La Coruña": "Deportivo",
            "Lusitânia Lourosa": "Lourosa", "PRO Vercelli": "Pro Vercelli"}


def limpio(n):
    import re
    n = re.sub(r"\s*\(fem[.,]\)|\s+W$", "", n)
    n = re.sub(r"^(?:AD|CD|UD|SD|CF|FC)\s+|\s+(?:CF|FC|SAD)$", "", n).strip()
    return ARREGLOS.get(n, n)


def _paises():
    from nombres import PAISES
    return PAISES


def montar(partidos, desde, usadas, mitad=None):
    """Una pata por partido (la mejor que no esté usada), por hora, hasta MAX_PATAS. Con «mitad» (0/1) solo coge uno
    de cada dos partidos que tienen pata, para que las dos combis del día no compartan partido."""
    patas = []
    validos = [p for p in sorted(partidos, key=lambda p: p["fecha"])
               if datetime.fromisoformat(p["fecha"]).astimezone(MADRID) >= desde and opciones(p)]
    if mitad is not None:
        validos = validos[mitad::2]
    for p in validos:
        ini = datetime.fromisoformat(p["fecha"]).astimezone(MADRID)
        for sel, txt, cu, aprox, _ in opciones(p):
            if sel not in usadas:
                patas.append({"sel": sel, "texto": txt, "cuota": cu, "aprox": aprox, "ini": ini})
                break
        tot = 1.0
        for x in patas:
            tot *= x["cuota"]
        if len(patas) >= MAX_PATAS or (len(patas) >= 10 and tot >= 120):
            break
    return patas if len(patas) >= MIN_PATAS else None


def texto_post(patas, segunda=False):
    tot = 1.0
    for x in patas:
        tot *= x["cuota"]
    filas = [f"🍀 {x['texto']} ({x['ini']:%H:%M}) @{x['cuota']:.2f}".replace(".", ",") for x in patas]
    redondo = f"{tot:,.0f}".replace(",", ".") if tot >= 100 else f"{tot:.2f}".replace(".", ",")
    gana = f"{tot * 10:,.0f}".replace(",", ".")
    aprox = " aprox." if any(x["aprox"] for x in patas) or tot >= 100 else ""
    titulo = f"💣 MI SEGUNDA COMBINADA · {len(patas)} PARTIDOS 💣" if segunda else f"🔥 MI COMBINADA DE HOY · {len(patas)} PARTIDOS 🔥"
    return (f"{titulo}\n\n" + "\n".join(filas) +
            f"\n\n📈 Cuota @{redondo}{aprox}\n💶 10€ → {gana}€\n\nEsta la llevo yo, partido a partido 👇\n¿Quién se sube conmigo? 💚")


def main(ahora=None):
    ahora = ahora or datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")
    est = leer(ESTADO, {}) or {}
    if est.get("dia") != hoy:
        est = {"dia": hoy, "hechas": [], "usadas": []}
    d = leer(DATOS / "resumen_proximos.json", []) or []
    partidos = [p for p in (d if isinstance(d, list) else d.get("partidos", [])) if p["fecha"][:10] == hoy
                or datetime.fromisoformat(p["fecha"]).astimezone(MADRID).strftime("%Y-%m-%d") == hoy]
    nuevos = []
    for tanda, (hora, desde) in TANDAS.items():
        if tanda in est["hechas"] or ahora.strftime("%H:%M") < hora:
            continue
        inicio = max(datetime.fromisoformat(f"{hoy}T{desde}").replace(tzinfo=MADRID), ahora + timedelta(minutes=45))
        patas = montar(partidos, inicio, set(est["usadas"]), mitad=0 if tanda == "a" else 1)
        est["hechas"].append(tanda)   # una vez al día por tanda, salga o no
        if not patas:
            print(f"Combi personal {tanda}: no hay partidos suficientes")
            continue
        pid = f"{hoy}-combi-personal-{tanda}"
        nuevos.append({"id": pid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto_post(patas, segunda=tanda == "b"),
                       "foto": None, "origen": "bot", "directo": True, "solo_en": ["threads", "instagram"],
                       "sel": [], "cuotas": [], "excepcion_cuota": "combinada personal diaria (Marcos 15/11)",
                       "nota": "patas: " + " · ".join(x["sel"] for x in patas)})
        est["usadas"] += [x["sel"] for x in patas]
    if nuevos:
        cola = leer(COLA, []) or []
        ids = {p["id"] for p in cola}
        nuevos = [p for p in nuevos if p["id"] not in ids]
        COLA.write_text(json.dumps(cola + nuevos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            import os
            if os.environ.get("GITHUB_ACTIONS") == "true":
                import imagenes
                from playwright.sync_api import sync_playwright
                with sync_playwright() as pw:
                    nav = pw.chromium.launch()
                    pg = nav.new_page()
                    for p in nuevos:
                        imagenes.generar(p, pg)
                        (imagenes.MEDIA / f"{p['id']}.huella").write_text(imagenes.huella(p))
                    nav.close()
        except Exception as e:
            print("combis_personales (fotos):", e)
        for p in nuevos:
            print("Combi personal:", p["id"])
    ESTADO.write_text(json.dumps(est, ensure_ascii=False) + "\n", encoding="utf-8")
    return nuevos


if __name__ == "__main__":
    main()
