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

GRAVES = ("mercado", "cuota", "choca", "repetido", "estrella", "caido", "texto", "crear")


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
    caido = partido_caido(p)
    if caido:
        fallos.append(("caido", caido))
    if re.search(r"segur|asegur|sin riesgo", texto, re.I):
        fallos.append(("texto", "dice «seguro/asegurado/sin riesgo»"))
    if re.search(r"\bNone\b|\bnan\b|\{[a-z_]+\}", texto):
        fallos.append(("texto", "restos de plantilla en el texto"))
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
