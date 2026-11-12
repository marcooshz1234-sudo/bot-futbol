"""11/11 (Marcos: «crea un bot que revise todo constantemente a ver qué fallos pueden salir»).

Va en el bucle cada 10 min. No cambia nada: solo mira y avisa (Marcos: «nunca cambiar nada sin enseñárselo»).
Cada problema se avisa UNA vez (datos/vigilante.json) al móvil de Marcos, todos juntos en un mensaje, y queda en la
pestaña 🛠️ Vigilante de la Oficina. Claude lo lee en sus revisiones y lo arregla.

Lo que mira (cada cosa es un fallo que ya pasó alguna vez):
  1. publicado     — post ya publicado con un partido aplazado/suspendido (10/11-11/11 Benfica)
  2. retraso_redes — post de hace 20 min-6 h que no ha salido en Threads o Instagram (o salió con error)
  3. sin_directo   — post de la cola de hoy/mañana sin «directo»: no saldría nunca en redes (11/11 logo)
  4. foto          — post que sale en <40 min sin su foto o con una foto vieja (huella distinta)
  5. prohibido     — post pendiente con un mercado que Marcos no quiere (más de 2,5, 1ª parte…)
  6. repetido      — un mismo pronóstico en más de 2 posts del día (11/11 «máx. 2 veces»)
  7. texto         — nombre de otro tipster, restos de plantilla (None, nan, {…}) o ✅ en patas sin jugar
  8. cuotas        — post con «sel» y sin «cuotas» (la app no lo corrige ni salen sus verdes)
  9. bucle         — un paso del bucle que falla 3+ veces en la última hora
 10. escalera      — a las 12:00 no hay escalera de hoy
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer

ESTADO = DATOS / "vigilante.json"
PUB = RAIZ / "publicaciones"
TIPSTERS = ("Tipster Pérez", "Tipster Perez", "TipsAnalistas", "PABLO ANALISTA", "Pablo Analista", "INSIDER",
            "CRIMINALPICKS", "Lafiebredelpick", "TRADER FOOTBALL", "TipsPro", "MAX ANALISTA", "CREAR APUESTA CUOTA")
RESTOS = re.compile(r"\bNone\b|\bnan\b|\{[a-z_]+\}|\bundefined\b|@0,00\b")
CADUCAN_META = "2026-12-21"   # cambiar cuando Marcos las renueve (y en comprobar_redes.py)
AVISO_CLAVES = ("2026-12-01", "2026-12-15", "2026-12-19", "2026-12-20")
NO_CUENTAN = ("ganadores", "lista-europa", "verde", "rojo", "balance", "logo")


def todos():
    """Cola + auto con su estado (Telegram y redes), como los ve el bot."""
    cola = leer(PUB / "cola.json", []) or []
    tg = leer(PUB / "enviados.json", {}) or {}
    meta = leer(PUB / "enviados_redes.json", {}) or {}
    ids = {p["id"] for p in cola}
    auto = [dict(p, **dict(tg.get(p["id"], {}), **meta.get(p["id"], {})))
            for p in leer(PUB / "auto.json", []) or [] if p["id"] not in ids]
    return [dict(p, _cola=True) for p in cola] + auto


def cuando(p):
    try:
        return datetime.fromisoformat(p["fecha"][:16]).replace(tzinfo=MADRID)
    except (KeyError, ValueError):
        return None


def vivo(p, control):
    """Post que debe salir (no cancelado, ni caducado, ni pendiente de OK, ni borrado)."""
    if p.get("caducada") or p.get("borrar") or p.get("borrado") or p["id"] in (control.get("cancelados") or []):
        return False
    if p.get("requiere_ok") and p["id"] not in (control.get("aprobados") or {}):
        return False
    return True


def publicado(p):
    r = p.get("redes") or {}
    return bool(p.get("enviado") or p.get("mensaje_id") or any(v for v in r.values()))


def revisar(ahora=None):
    """[(clave, texto)] de todo lo que está mal ahora mismo."""
    ahora = ahora or datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")
    control = leer(PUB / "control.json", {}) or {}
    borrados = set(leer(PUB / "borrados.json", []) or [])   # los que Marcos borró: ni se cuentan ni se avisa
    posts = [p for p in todos() if p["id"] not in borrados]
    out = []
    from bot import partido_caido

    for p in posts:
        t = cuando(p)
        if not t or t < ahora - timedelta(days=1) or t > ahora + timedelta(days=2):
            continue
        cab = (p.get("texto") or "").strip().splitlines()[0][:60] if p.get("texto") else p["id"]
        es_resultado = any(k in p["id"] for k in ("verde", "rojo", "balance")) or p.get("verde_de") or p.get("resultado")

        # 1. publicado con un partido aplazado, suspendido, movido de día o bloqueado en bet365
        if publicado(p) and not es_resultado and not p.get("borrar") and p.get("sel"):
            motivo = partido_caido(dict(p, fecha=p["fecha"]))
            if motivo and "terminado" not in motivo:
                out.append((f"publicado-{p['id']}-{motivo[:30]}",
                            f"🛑 Ya publicado y su {motivo}: {cab}. Hay que avisar o borrarlo"))

        if not vivo(p, control):
            continue

        # 2. no ha salido en redes (o ha salido con error)
        if p.get("directo") and ahora - timedelta(hours=6) <= t <= ahora - timedelta(minutes=20) and not partido_caido(p):
            r, err = p.get("redes") or {}, p.get("errores_redes") or {}
            solo = p.get("solo_en")
            faltan = [red for red in ("threads", "instagram")
                      if (not solo or red in solo) and not (red == "instagram" and p.get("sin_instagram"))
                      and (red not in r or (r.get(red) is None and err.get(red)))]
            if faltan:
                out.append((f"redes-{p['id']}-{'-'.join(faltan)}",
                            f"⏰ No ha salido en {' ni '.join(faltan)} ({p['fecha'][11:16]}): {cab}"
                            + (f" · error: {str(next(iter(err.values())))[:80]}" if err else "")))

        pendiente = t > ahora and not publicado(p)

        # 3. de la cola, sin «directo»: no sale nunca en redes
        if p.get("_cola") and pendiente and not p.get("directo") and t < ahora + timedelta(days=1):
            out.append((f"directo-{p['id']}", f"⚠️ Sin «directo» (no saldría en Threads ni Instagram): {cab} ({p['fecha'][11:16]})"))

        # 4. foto de Instagram sin hacer o vieja
        if pendiente and p.get("directo") and not p.get("sin_instagram") and t < ahora + timedelta(minutes=40) \
                and (not p.get("solo_en") or "instagram" in p["solo_en"]):
            jpg, h = PUB / "media" / f"{p['id']}.jpg", PUB / "media" / f"{p['id']}.huella"
            try:
                import imagenes
                texto = (control.get("textos") or {}).get(p["id"], p["texto"])   # como imagenes.pendientes_de
                bien = jpg.exists() and h.exists() and h.read_text().strip() == imagenes.huella(dict(p, texto=texto))
            except Exception:
                bien = jpg.exists()
            if not bien and t < ahora + timedelta(minutes=15):
                out.append((f"foto-{p['id']}", f"🖼️ Sale a las {p['fecha'][11:16]} y su foto no está hecha (o es vieja): {cab}"))

        # 4b. foto con escudos (combi de partido, Partidos de hoy): sin ella no sale ni en Telegram ni en redes
        if pendiente and (p.get("tarjeta") or p.get("ganadores_img")) and t < ahora + timedelta(minutes=15) \
                and not (PUB / "media" / f"{p['id']}.tarjeta.jpg").exists():
            out.append((f"tarjeta-{p['id']}", f"🖼️ Sale a las {p['fecha'][11:16]} y falta su foto con escudos (sin ella no sale): {cab}"))

        if not pendiente or es_resultado:
            continue
        # 5. mercados prohibidos
        try:
            from picks import excluido
            malos = [s for s in p.get("sel") or [] if s.count("|") >= 2 and excluido(*str(s).split("|")[1:3])]
            if malos:
                out.append((f"prohibido-{p['id']}", f"🚫 Lleva un mercado prohibido ({malos[0].split('|', 1)[1]}): {cab}"))
        except ImportError:
            pass
        # 7. texto
        tx = p.get("texto") or ""
        nombre = next((n for n in TIPSTERS if n.lower() in tx.lower()), None)
        if nombre:
            out.append((f"tipster-{p['id']}", f"🙊 El texto lleva el nombre de otro tipster ({nombre}): {cab}"))
        if re.search(r"segur|asegur|sin riesgo", tx, re.I):   # 12/11 (Marcos): nunca «seguro»
            out.append((f"seguro-{p['id']}", f"🚫 El texto dice «seguro/asegurado» (Marcos: nunca): {cab}"))
        m = RESTOS.search(tx)
        if m:
            out.append((f"resto-{p['id']}", f"🧩 Texto roto («{m.group(0)}»): {cab}"))
        if re.search(r"^\s*✅ (?!D[ií]a )", tx, re.M) and not any(k in p["id"] for k in ("ganadores", "recuerdo", "pleno")):
            out.append((f"check-{p['id']}", f"✅ Lleva ✅ en patas que aún no se han jugado (parece ganada): {cab}"))
        # 8. sin cuotas
        if p.get("sel") and len(p.get("cuotas") or []) != len(p["sel"]):
            out.append((f"cuotas-{p['id']}", f"📉 Sin «cuotas» (la app no lo sigue y no saldría su verde): {cab}"))

    # 6. repetidos en el día
    for dia in (hoy, (ahora + timedelta(days=1)).strftime("%Y-%m-%d")):
        usos, donde = Counter(), defaultdict(list)
        for p in posts:
            if p["id"].startswith(dia) and vivo(p, control) and not any(k in p["id"] for k in NO_CUENTAN) \
                    and not p.get("verde_de"):
                for s in set(p.get("sel") or []):
                    usos[s] += 1
                    donde[s].append(p["id"][11:])
        for s, n in usos.items():
            if n > 2:
                out.append((f"repe-{dia}-{s}", f"🔁 {dia[8:]}/{dia[5:7]}: el mismo pronóstico en {n} posts ({', '.join(donde[s])})"))

    # 9. pasos del bucle que fallan
    log = DATOS / "bucle_log.txt"
    if log.exists():
        from zoneinfo import ZoneInfo
        hace = (ahora - timedelta(hours=1)).astimezone(ZoneInfo("UTC")).strftime("%H:%M:%S")   # el log va en UTC
        ya = ahora.astimezone(ZoneInfo("UTC")).strftime("%H:%M:%S")
        fallos = Counter()
        for linea in log.read_text(encoding="utf-8").splitlines()[-400:]:
            x = linea.split()
            dentro = x and (x[0] >= hace if hace <= ya else (x[0] >= hace or x[0] <= ya))   # pasada la medianoche
            if len(x) >= 3 and dentro and x[2] not in ("0", "-"):
                fallos[x[1]] += 1
        for paso, n in fallos.items():
            if n >= 3:
                out.append((f"bucle-{paso}-{ahora:%Y%m%d%H}", f"🔧 El paso «{paso}» del bot ha fallado {n} veces en la última hora"))

    # 11. escalón sin resolver a las 30 h (Marcos 11/11: «esperar y avisarme»)
    act = (leer(DATOS / "escalera.json", {}) or {}).get("actual") or {}
    try:
        ult = max(datetime.fromisoformat(x["fecha"][:16]).replace(tzinfo=MADRID) for x in act.get("picks") or [])
        if ahora - ult > timedelta(hours=30):
            out.append((f"escalon-{act.get('dia')}", f"🪜 El escalón del {act.get('dia', '')[8:]}/{act.get('dia', '')[5:7]} "
                        "lleva más de 30 h sin resultado de alguna pata: hay que mirarlo a mano (datos/escalera.json)"))
    except (ValueError, KeyError):
        pass

    # 12. cuota diaria de la API de fútbol (bot.guardar_cuota_api)
    q = leer(DATOS / "api_cuota.json", {}) or {}
    if q.get("limite") and q.get("restantes") is not None and (q.get("hora") or "")[:10] == hoy \
            and q["restantes"] < q["limite"] * 0.10:
        out.append((f"api-{hoy}", f"📉 Quedan {q['restantes']} de {q['limite']} peticiones a la API de fútbol hoy: "
                    "si se acaban, el bot no tendrá cuotas ni resultados hasta mañana"))

    # 13. claves de Meta (Threads e Instagram): caducan; las renueva Marcos (Claude nunca las ve)
    if hoy >= AVISO_CLAVES[0]:
        cual = max(d for d in AVISO_CLAVES if d <= hoy)
        out.append((f"claves-{cual}", f"🔑 Las claves de Threads e Instagram caducan el {CADUCAN_META[8:]}/{CADUCAN_META[5:7]}. "
                    "Si no se renuevan, ese día dejan de salir los posts en redes. Dile a Claude «renovar claves» y te "
                    "guía paso a paso (las pones tú en GitHub)"))

    # 10. escalera de hoy
    if ahora.hour >= 12 and not any(p["id"].startswith(f"{hoy}-escalera") for p in posts) \
            and not (leer(DATOS / "escalera.json", {}) or {}).get("pausa"):
        out.append((f"escalera-{hoy}", "🪜 Son más de las 12:00 y no hay escalera de hoy"))
    return out


def main(ahora=None, avisar=True):
    ahora = ahora or datetime.now(MADRID)
    try:
        problemas = revisar(ahora)
    except Exception as e:   # el vigilante no puede tumbar el bucle
        print("vigilante:", repr(e))
        return []
    est = leer(ESTADO, {}) or {}
    vistos = est.get("vistos") or {}
    nuevos = [(k, t) for k, t in problemas if k not in vistos]
    for k, _ in nuevos:
        vistos[k] = ahora.strftime("%Y-%m-%dT%H:%M")
    limite = (ahora - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M")
    est = {"vistos": {k: v for k, v in vistos.items() if v >= limite},
           "abiertos": [{"clave": k, "t": t} for k, t in problemas],
           "revisado": ahora.strftime("%Y-%m-%dT%H:%M"),
           "historial": ([{"hora": ahora.strftime("%Y-%m-%dT%H:%M"), "t": t} for _, t in nuevos]
                         + (est.get("historial") or []))[:60]}
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Vigilante: {len(problemas)} problemas ({len(nuevos)} nuevos)")
    for _, t in problemas:
        print(" ", t)
    if nuevos and avisar:
        try:
            from ajustes import valor
            if valor("aviso_vigilante", control=leer(PUB / "control.json", {}) or {}):
                from alineaciones_posts import dm
                dm("🛠️ Vigilante: he visto esto\n\n" + "\n".join(f"• {t}" for _, t in nuevos[:12])
                   + (f"\n…y {len(nuevos) - 12} más" if len(nuevos) > 12 else "") + "\n\nClaude lo revisa en su próxima pasada.")
        except Exception as e:
            print("vigilante (aviso):", e)
    return nuevos


if __name__ == "__main__":
    import sys
    main(avisar="--sin-aviso" not in sys.argv)
