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
import sys

from bot import cuota_baja, leer, mercado_prohibido, partido_caido, RAIZ

GRAVES = ("mercado", "cuota", "cuota_alta", "choca", "repetido", "estrella", "caido", "texto", "crear", "logica", "escudos", "dia")
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
    return p.get("origen") == "tipster" or "-tip-" in p.get("id", "")


def es_resultado(p):
    pid = p.get("id", "")
    return bool(p.get("verde_de") or p.get("resultado") or any(k in pid for k in ("verde", "rojo", "balance")))


def comprobar(p, texto=None, otros=None):
    """Lista de (regla, motivo) que incumple el post. Vacía = se puede publicar."""
    if es_resultado(p):
        return []
    texto = texto if texto is not None else p.get("texto") or ""
    fallos = []
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
        altas = [c for c in (p.get("cuotas") or []) if float(c) > CUOTA_MAXIMA_PATA]
        if altas:   # 13/11 (Marcos: «patas de máximo 1,8»)
            fallos.append(("cuota_alta", f"pata de más de {CUOTA_MAXIMA_PATA:.2f} (@{max(altas):.2f})".replace(".", ",")))
    if sels and "ganadores" not in pid and "marcadores" not in pid:
        from plantillas import choca
        if otros is None:
            otros = _sin_este(p)
        otros = dict(otros)
        loca = "loca" in pid
        for s in sels:
            rival = [o for o in otros if o not in sels and choca(s, [o])]
            if rival and not (loca and s.split("|")[1] == "Double Chance"):
                fallos.append(("choca", f"{s.split('|', 1)[1]} choca con {rival[0].split('|', 1)[1]} (mismo partido)"))
            if otros.get(s, 0) >= 2:
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


def bloquea(p, texto=None):
    """Motivo para NO publicar (las reglas graves), o None. Lo usan publicar_telegram y redes."""
    try:
        f = [x for x in comprobar(p, texto, otros=_sin_este(p)) if x[0] in GRAVES and x[0] not in ("repetido", "choca")
             or (x[0] in ("repetido", "choca") and not es_copia(p) and p.get("origen") == "claude")]
    except Exception as e:
        print("comprobar_post:", e)
        return None
    return "; ".join(m for _, m in f) or None


def _sin_este(p):
    from combis_dia import ya_publicadas
    return ya_publicadas(p.get("id", "")[:10], excluir=p.get("id"))


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
