"""12/11 (Marcos: «lo que quiero es que no vuelvas a cometer estos errores, ¿qué hay que hacer?»).

UN solo sitio con TODAS las reglas de un post. Lo usan:
  - Claude, antes de meter cualquier post a mano en la cola:  python3 comprobar_post.py <id>   (o comprobar(post))
  - publicar_telegram.py y redes.py, justo antes de publicar: si falla una regla grave, el post NO sale.
  - vigilante.py, para avisar a Marcos.
Cada regla nueva que diga Marcos se añade AQUÍ (y su test en tests/test_comprobar_post.py), no en la cabeza de nadie.

Reglas (de Marcos):
  1. mercados prohibidos en lo nuestro: más de 2,5 goles, 1ª parte, descanso, tarjetas y tiros totales…
  2. cuota: un pick solo ≥ 1,35; cada pata de combi ≥ 1,20 (salvo UNA de élite 1,15–1,20 en combis ≥ 1,50)
  3. nunca chocar con otro post del mismo partido (salvo «o empate» en la loca)
  4. un mismo pronóstico en 2 posts como mucho (ganadores no cuenta)
  5. nada a favor de un equipo al que le falta su estrella (salvo que siga siendo favorito claro ≤ 1,35)
  6. partido aplazado, bloqueado o ya jugado
  7. texto: nunca «seguro/asegurado/sin riesgo»; sin restos de plantilla (None, nan, {…})
  8. combi de un partido: la cuota no se multiplica (tiene que llevar la de «Crear apuesta» que da Marcos)
"""
import re
from collections import Counter
import sys

from bot import cuota_baja, leer, mercado_prohibido, partido_caido, RAIZ

GRAVES = ("mercado", "cuota", "cuota_alta", "choca", "repetido", "estrella", "caido", "texto", "crear", "logica", "escudos", "dia", "idioma")
TEXTO_PROHIBIDO = [   # (patrón, motivo) — REGLAS.md, apartado «Textos»
    (r"segur|asegur|sin riesgo", "dice «seguro/asegurado/sin riesgo» (12/11)"),
    (r"\bNone\b|\bnan\b|\{[a-z_]+\}", "restos de plantilla en el texto"),
    (r"jugarbien\.es", "«jugarbien.es» (27/10)"),
    (r"Solo queda rezar", "«Solo queda rezar» (no le gusta)"),
    (r"\bMarcos\b", "el nombre de Marcos (nunca en público)"),
    (r"\+18 \| Jueg[ao] (?:con )?responsab", "«+18 | Juega responsable» (quitado el 27/10)"),
    (r"MyMatch|Bet ?Builder|pata de su|su boleto", "nombres de otras casas o notas internas («MyMatch», «pata de su…») (13/11)"),
]


def _fid(s):
    return str(s).split("|")[0]


def _equipo_marca(s):
    """'home'/'away' si la pata es «X marca» (Total - Home/Away Over 0.5/1.5…)."""
    _, m, o = str(s).split("|", 2)
    if m in ("Total - Home", "Total - Away") and o.startswith("Over"):
        return "home" if m.endswith("Home") else "away"
    return None


def logica_combi(sels):
    """Patas que no tienen lógica juntas en la MISMA combi (REGLAS.md, «Combis»)."""
    out = []
    por_partido = {}
    for s in sels:
        por_partido.setdefault(_fid(s), []).append(s)
    for fid, ps in por_partido.items():
        mercados = [str(s).split("|", 2)[1:] for s in ps]
        marcan = {_equipo_marca(s) for s in ps} - {None}
        btts = any(m == "Both Teams Score" and o == "Yes" for m, o in mercados)
        if btts and marcan:   # 31/10: «ambos marcan» + «X marca» no vale para nada
            out.append("«ambos marcan» junto a «X marca» del mismo partido (31/10)")
        if marcan == {"home", "away"}:   # 02/11: «marca el local» y «marca el visitante» en la misma combi
            out.append("«marca el local» y «marca el visitante» en la misma combi (02/11)")
        for m, o in mercados:   # 02/11: «X o empate» y que le marque el rival
            if m == "Double Chance" and o in ("Home/Draw", "Draw/Away"):
                lado = "home" if o.startswith("Home") else "away"
                rival = "away" if lado == "home" else "home"
                if rival in marcan:
                    out.append("«X o empate» y que le marque el rival en la misma combi (02/11)")
    return out


def orden_por_hora(sels):
    """Las patas de varios partidos tienen que ir por hora de inicio (02/11)."""
    from datetime import datetime
    horas = []
    for s in sels:
        pa = (leer(RAIZ / "datos" / "proximos" / f"{_fid(s)}.json", {}) or {}).get("partido") or {}
        f = (pa.get("fixture") or {}).get("date")
        if f:
            horas.append(datetime.fromisoformat(f))
    return horas == sorted(horas), {h.date() for h in horas}


def es_copia(p):
    # 14/11: los boletos de Marcos (su combinada personal de bet365) tampoco siguen las reglas de NUESTRAS combis
    return p.get("origen") == "tipster" or "-tip-" in p.get("id", "") or "-boleto-" in p.get("id", "")


def es_resultado(p):
    pid = p.get("id", "")
    return bool(p.get("verde_de") or p.get("resultado") or any(k in pid for k in ("verde", "rojo", "balance")))


def comprobar(p, texto=None, otros=None):
    """Lista de (regla, motivo) que incumple el post. Vacía = se puede publicar."""
    if es_resultado(p):
        return []
    texto = texto if texto is not None else p.get("texto") or ""
    fallos = []
    # 15/11 (Marcos: «todo en español siempre» y nunca «el» delante de un país). Se mira el texto tal y como se
    # publica (ya pasado por nombres.espanol): si aun así queda algo, no sale.
    from nombres import espanol, fallos as fallos_idioma
    for f_ in fallos_idioma(espanol(texto)):
        fallos.append(("idioma", f_))
    m = mercado_prohibido(p)
    if m:
        fallos.append(("mercado", m))
    c = cuota_baja(p, texto)
    if c:
        fallos.append(("cuota", c))
    pid, dia = p.get("id", ""), p.get("id", "")[:10]
    sels = [s for s in p.get("sel") or [] if str(s).count("|") == 2]
    # 14/11 (Marcos): la de 1 € a 500 € puede llevar patas más grandes, sin límite (dentro de la lógica)
    if not es_copia(p) and not any(k in pid for k in ("ganadores", "marcadores", "cuotaza", "lista", "exactos", "combi-500", "boleto")):   # 14/11: los boletos de Marcos (bet365) tampoco
        from bot import CUOTA_MAXIMA_PATA
        # 16/11 (Marcos: «para Instagram y Threads no hace falta respetar lo del 1,8: puede ser desde 1,4 hasta 9»)
        solo_redes = p.get("solo_redes") or (p.get("solo_en") and "telegram" not in p["solo_en"])
        tope = TOPE_PATA_REDES if solo_redes else CUOTA_MAXIMA_PATA
        altas = [c for c in (p.get("cuotas") or []) if float(c) > tope]
        if altas and not p.get("excepcion_cuota"):   # 13/11 (Marcos: «patas de máximo 1,8»); 14/11: salvo OK suyo en ese post
            fallos.append(("cuota_alta", f"pata de más de {tope:.2f} (@{max(altas):.2f})".replace(".", ",")))
    if sels and "ganadores" not in pid and "marcadores" not in pid:
        from plantillas import choca
        dado = otros is not None
        if otros is None:
            otros = _sin_este(p)
        otros = dict(otros)
        loca = "loca" in pid
        # 19/11 (Marcos): Threads y Telegram pueden chocar entre ellos; dentro de la misma red, nunca
        misma_red = Counter(otros) if dado else Counter()
        for r_ in ([] if dado else redes_de(p)):   # por red: el máximo, no la suma (un post en 2 redes cuenta 1)
            misma_red = misma_red | Counter(_sin_este(p, red=r_))
        for s in sels:
            rival = [o for o in misma_red if o not in sels and choca(s, [o])]
            if rival and not (loca and s.split("|")[1] == "Double Chance"):
                fallos.append(("choca", f"{s.split('|', 1)[1]} choca con {rival[0].split('|', 1)[1]} (mismo partido)"))
            if misma_red.get(s, 0) >= 2:   # 19/11: el máx. de 2 posts con el mismo pick, también por red
                fallos.append(("repetido", f"{s.split('|', 1)[1]} ya va en 2 posts"))
        if not es_copia(p):
            try:
                import revision
                for s in sels:
                    sin = revision.lados_sin_estrella(s.split("|")[0])
                    if any(revision.favorece(s, lado) for lado in sin):
                        fallos.append(("estrella", f"{s.split('|', 1)[1]}: a ese equipo le falta su estrella"))
            except Exception as e:
                print("comprobar (estrellas):", e)
        if len({s.split("|")[0] for s in sels}) == 1 and len(sels) > 1 and "combi-partido" in pid:
            control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
            if not (p.get("cuota_total") or pid in (control.get("cuota_dada") or {})):
                fallos.append(("crear", "combi de un partido sin la cuota real de «Crear apuesta»"))
    if sels and not es_copia(p) and "ganadores" not in pid and "lista" not in pid and "picks-manana" not in pid:
        for motivo in logica_combi(sels):
            fallos.append(("logica", motivo))
        if "combi-partido" in pid or "estrella" in pid:   # 01/11: las de escudos, sin córners ni tarjetas
            from combis_dia import familia
            raras = [s for s in sels if familia({"mercado": s.split("|")[1], "opcion": s.split("|")[2]})
                     in ("corners", "corners-bajo", "tarjetas")]
            if raras:
                fallos.append(("escudos", "combi con escudos con córners o tarjetas (01/11: sin córners ni tarjetas): "
                                          + ", ".join(s.split("|", 1)[1] for s in raras)))
        if len({_fid(s) for s in sels}) > 1:
            en_orden, dias = orden_por_hora(sels)
            if len(dias) > 1 and "loca" not in pid and "multi" not in pid:
                fallos.append(("dia", "combi con partidos de días distintos (si falla uno, se cae todo)"))
            if not en_orden:
                fallos.append(("orden", "patas no ordenadas por hora de inicio (02/11)"))
    caido = partido_caido(p)
    if caido:
        fallos.append(("caido", caido))
    for patron, motivo in TEXTO_PROHIBIDO:
        if re.search(patron, texto, re.I):
            fallos.append(("texto", motivo))
    if not (p.get("solo_en") and "telegram" not in p["solo_en"]) and not p.get("solo_redes") \
            and re.search(r"@combilocas\b", texto):
        fallos.append(("texto", "«@combilocas» en Telegram lleva a OTRO canal (05/11)"))
    n_picks = len(re.findall(r"^\s*(?:✅|🍀|🇦-🇿|[\U0001F1E6-\U0001F1FF]{2})", texto, re.M))
    if re.search(r"Combina máximo 2 o 3", texto) and n_picks < 5:
        fallos.append(("formato", "«Combina máximo 2 o 3» solo con 5 picks o más (02/11)"))
    if re.search(r"Coged los picks que más", texto) and n_picks < 10:
        fallos.append(("formato", "«Coged los picks que más os gusten» solo en combis de 10+ (05/11)"))
    return fallos


def firma(t):
    """16/11: el mismo pick escrito con otras palabras («más de 2,5 goles y gol en la 1ª parte en Alemania–Países
    Bajos» / «gol en la 1ª parte y más de 2,5 goles en el partido») salió 2 veces en Telegram. Firma = partido (línea
    ⚽) + las condiciones tal y como las lee la tarjeta («+2,5 GOLES», «GOL 1ª PARTE»…). None si no se puede leer."""
    import unicodedata
    try:
        import tarjeta_tg as T
    except Exception:
        return None
    m = re.search(r"⚽\s*(.+?)\s*·", t or "")
    if not m:
        return None
    partido = re.sub(r"[^a-z]+", "", unicodedata.normalize("NFKD", m.group(1)).encode("ascii", "ignore").decode().lower())
    try:
        picks = frozenset(f["pick"] for f in T.filas(T.patas(t), m.group(1)) if f and f.get("pick") not in (None, "✓"))
    except Exception:
        return None
    return (partido, picks) if partido and picks else None


def _picks_txt(t):
    """Las líneas de pick de un texto, normalizadas (sin emoji ni espacios): para ver si dos posts son el mismo."""
    import unicodedata
    out = set()
    for l in (t or "").splitlines():
        if "@" in l and not re.search(r"Cuota\s*@|Historial|💶", l):
            l = unicodedata.normalize("NFKD", l).encode("ascii", "ignore").decode().lower()
            out.add(re.sub(r"[^a-z0-9@,.]+", "", l))
    return out


def redes_de(p):
    return set(p.get("solo_en") or ["telegram", "threads", "instagram"])


TOPE_PATA_REDES = 9.0   # 16/11: en Threads/Instagram, patas de 1,40 a 9


def duplicado(p, texto=None, cola=None):
    """15/11: Madrid CFF y Finlandia salieron 2 veces en Telegram, y Bélgica–Italia e Inglaterra 3 veces en Threads
    (se volvían a subir con otro id). Un post con los mismos picks que otro YA publicado ese día en la misma red no
    sale, salvo que el original esté en borrados.json (Marcos lo borró) o el nuevo diga «repuesto_de» un borrado."""
    if p.get("verde_de") or any(k in p.get("id", "") for k in ("verde", "rojo", "balance", "resumen", "ganadores",
                                                              "marcadores", "lista", "porque")):
        return None
    mios = _picks_txt(texto or p.get("texto"))
    if not mios:
        return None
    mi_firma = firma(texto or p.get("texto"))
    if cola is None:
        cola = (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + (leer(RAIZ / "publicaciones" / "auto.json", []) or [])
    b = leer(RAIZ / "publicaciones" / "borrados.json", []) or []
    borrados = set(b if isinstance(b, list) else b)
    redes = redes_de(p)
    for o in cola:
        if o.get("id") == p.get("id") or o.get("id", "")[:10] != p.get("id", "")[:10] or o.get("id") in borrados:
            continue
        if o.get("id") == p.get("repuesto_de"):
            continue
        if _picks_txt(o.get("texto")) != mios and not (mi_firma and firma(o.get("texto")) == mi_firma):
            continue
        salio = ({"telegram"} if o.get("enviado") else set()) | {k for k, v in (o.get("redes") or {}).items() if v}
        salio = {"instagram" if k.startswith("instagram") else k for k in salio}
        comun = redes & salio
        if comun:
            return f"ya salió como {o['id']} en {', '.join(sorted(comun))} (si Marcos lo borró, apúntalo en borrados.json)"
    return None


TOPE_TARJETAS_TG = 2   # 17/11 (Marcos: «ya hay dos picks de tarjetas hoy, ya no subas ninguno así»)


def _de_tarjetas(p, texto=None):
    t = (texto or p.get("texto") or "") + " " + " ".join(map(str, p.get("sel") or []))
    return bool(re.search(r"tarjeta|Cards", t, re.I))


SIN_TARJETAS_DESDE = "2026-11-18"


def pick_tarjetas_tg(p, texto=None):
    """17/11 (Marcos: «las de las tarjetas van fatal, como pick no lo deberíamos de volver a poner»; 21:47: «solo que lo
    suba si es de un canal que acierte bastante»): un pick de tarjetas en Telegram solo si es copia de un tipster bueno
    (copiar_tipsters.tipster_bueno: ≥ 70 % de acierto suavizado). Los del bot, nunca. Las combis con alguna pata, sí."""
    if p.get("solo_en") and "telegram" not in p["solo_en"]:
        return None
    pid = p.get("id", "")
    if pid[:10] < SIN_TARJETAS_DESDE or not ("-pick-" in pid or p.get("origen") == "tipster"):
        return None
    if p.get("origen") == "tipster" and p.get("tipster_bueno") is True:
        return None
    t = texto or p.get("texto") or ""
    linea = " ".join(re.findall(r"🍀[^\n]*", t)) + " " + " ".join(map(str, p.get("sel") or []))
    if re.search(r"tarjeta|Cards", linea, re.I):
        return "picks de tarjetas en Telegram solo de un canal que acierte bastante (Marcos 17/11)"
    return None


def tarjetas_tg(p, texto=None, posts=None):
    """Motivo si ya salieron TOPE_TARJETAS_TG picks de tarjetas hoy en Telegram y este también lo es."""
    if p.get("solo_en") and "telegram" not in p["solo_en"]:
        return None
    if not _de_tarjetas(p, texto):
        return None
    dia = p.get("id", "")[:10]
    if posts is None:
        env = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
        posts = [{**x, "mensaje_id": x.get("mensaje_id") or (env.get(x["id"]) or {}).get("mensaje_id")}
                 for x in (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + (leer(RAIZ / "publicaciones" / "auto.json", []) or [])]
    n = sum(1 for x in posts if x.get("id", "")[:10] == dia and x.get("id") != p.get("id") and x.get("mensaje_id")
            and _de_tarjetas(x) and not _es_resultado(x))
    return f"ya hay {n} picks de tarjetas hoy en Telegram (tope {TOPE_TARJETAS_TG})" if n >= TOPE_TARJETAS_TG else None


def _clave_pick(t):
    """(partido, palabras del pick) de un post de un solo pick: «⚽ A – B» + la línea 🍀, sin cuota ni adornos."""
    partido = re.search(r"⚽\s*([^·\n]+?–[^·\n]+?)\s*·", t or "")
    pick = re.search(r"🍀\s*([^\n]+)", t or "")
    if not partido or not pick:
        return None
    pk = re.sub(r"@\s*\d+[.,]\d+|\(?crear apuesta\)?:?|[^\w\s,.]", " ", pick.group(1).lower())
    pk = frozenset(w for w in re.sub(r"(\d)[.,](\d)", r"\1\2", pk).replace(",", " ").split() if w not in ("y", "en", "de", "el", "la"))
    return partido.group(1).strip().lower(), pk


def mismo_pick_tg(p, texto=None, posts=None):
    """17/11: Dinamarca–Noruega «ambos marcan + más de 2,5» iba a salir 2 veces (copia del bot sin «sel» y otra a mano)."""
    if p.get("solo_en") and "telegram" not in p["solo_en"]:
        return None
    k = _clave_pick(texto or p.get("texto"))
    if not k:
        return None
    if posts is None:
        env = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
        posts = [{**x, "mensaje_id": x.get("mensaje_id") or (env.get(x["id"]) or {}).get("mensaje_id")}
                 for x in (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + (leer(RAIZ / "publicaciones" / "auto.json", []) or [])]
    for x in posts:
        if x.get("id", "")[:10] == p.get("id", "")[:10] and x.get("id") != p.get("id") and x.get("mensaje_id") \
                and _clave_pick(x.get("texto")) == k:
            return f"el mismo pick ya salió hoy en Telegram ({x['id']})"
    return None


def sin_sel_claude(p):
    """17/11 (Marcos: «mira tú bien lo que se ha subido al canal»): el «Gana Corea» que metió Claude a mano salió sin
    «sel» y el bot no lo siguió (ni su verde). Lo que mete Claude en Telegram, siempre con su sel."""
    if p.get("origen") != "claude" or (p.get("solo_en") and "telegram" not in p["solo_en"]):
        return None
    return None if p.get("sel") else "post de Claude sin «sel»: el bot no lo podría seguir ni sacar su verde"


def _es_resultado(p):
    """17/11: los verdes de las tarjetas de Polonia y Bosnia no salían: el tope de picks de tarjetas los contaba como
    picks nuevos. Los verdes/rojos/resúmenes no son picks: no les tocan esas reglas."""
    return bool(p.get("resultado") or p.get("verde_de") or re.search(r"-(verde|rojo|balance|resumen)-", p.get("id", "")))


def verde_sin_escudos(p):
    """18/11 (Marcos: «no salen los escudos de los equipos, siempre revisa eso»): los 5 aciertos de Threads de ayer que
    metió Claude a mano salieron como comentario sin foto. Un verde (no rojo/balance/resumen) siempre con su foto
    (tarjeta con banderas/escudos); sin ella no sale."""
    pid = p.get("id", "")
    if not (p.get("verde_de") or p.get("resultado") == "verde") or re.search(r"-(rojo|balance|resumen)(-|$)", pid):
        return None
    foto = p.get("foto")
    if foto and (RAIZ / foto).exists():
        return None
    return "verde sin foto con los escudos/banderas del partido"


def bloquea(p, texto=None):
    """Motivo para NO publicar (las reglas graves), o None. Lo usan publicar_telegram y redes."""
    v = verde_sin_escudos(p)
    if v:
        return v
    try:
        m = None if _es_resultado(p) else sin_sel_claude(p) or pick_tarjetas_tg(p, texto) or tarjetas_tg(p, texto) or mismo_pick_tg(p, texto)
        if m:
            return m
    except Exception as e:
        print("comprobar_post tarjetas:", e)
    try:
        d = duplicado(p, texto)
        if d:
            return d
    except Exception as e:
        print("comprobar_post duplicado:", e)
    try:
        f = [x for x in comprobar(p, texto, otros=_sin_este(p)) if x[0] in GRAVES and x[0] not in ("repetido", "choca")
             or (x[0] in ("repetido", "choca") and not es_copia(p) and p.get("origen") == "claude")]
    except Exception as e:
        print("comprobar_post:", e)
        return None
    return "; ".join(m for _, m in f) or None


def _sin_este(p, red=None):
    from combis_dia import ya_publicadas
    return ya_publicadas(p.get("id", "")[:10], excluir=p.get("id"), red=red)


if __name__ == "__main__":
    cola = (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + (leer(RAIZ / "publicaciones" / "auto.json", []) or [])
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    env = {**(leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}),
           **(leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {})}
    from datetime import datetime, timedelta
    from bot import MADRID
    hoy = datetime.now(MADRID).strftime("%Y-%m-%d")
    pendiente = lambda p: p["id"][:10] >= hoy and not (
        p.get("enviado") or any((p.get("redes") or {}).values()) or p.get("caducada")
        or (env.get(p["id"]) or {}).get("enviado") or any(((env.get(p["id"]) or {}).get("redes") or {}).values())
        or p["id"] in (control.get("cancelados") or []))
    ids = sys.argv[1:] or [p["id"] for p in cola if pendiente(p)]   # sin nada: lo que queda por salir desde hoy
    malos = 0
    for p in cola:
        if p["id"] in ids:
            f = comprobar(p, otros=_sin_este(p))
            if f:
                malos += 1
                print(f"❌ {p['id']}:\n   " + "\n   ".join(f"[{r}] {m}" for r, m in f))
            elif len(ids) < 10:
                print(f"✅ {p['id']}")
    sys.exit(1 if malos else 0)
