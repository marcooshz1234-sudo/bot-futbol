"""16/11 (Marcos: «sí, el domingo a las 22:00»): resumen semanal por PRIVADO a Marcos (nunca al canal) del acierto
de los picks de Telegram por tipo (gana/doble, goles, córners, tarjetas, jugadores…) y de las copias de tipsters,
para decidir si se sube el listón a algún tipo (⚠️ por debajo del 55 %).

Lee docs/resumenes.json (verde/rojo de cada post) y el mercado de cada post en cola.json / auto.json."""
import json
import re
from collections import Counter
from datetime import datetime, timedelta

from bot import MADRID, RAIZ, leer

ESTADO = RAIZ / "datos" / "resumen_semanal.json"
HORA = "22:00"
AVISO_BAJO = 0.55
NUESTROS = re.compile(r"-pick-(seguro(-\d)?|m\d+)$")
COPIA = re.compile(r"-pick-tip")
TITULOS = [("resultado", "🏆 Gana / doble"), ("goles", "⚽ Goles"), ("corners", "🚩 Córners"),
           ("tarjetas", "🟨 Tarjetas"), ("jugador", "🎯 Jugadores"), ("otros", "➕ Otros")]


def tipo_de(post):
    """Tipo del pick de un post (por su mercado; si no hay, por el texto)."""
    import combis_dia as C
    sel = (post or {}).get("sel") or []
    partes = str(sel[0]).split("|") if sel else []
    if len(partes) == 3:
        t = C.tipo_pick({"mercado": partes[1], "opcion": partes[2]})
        return t if t in dict(TITULOS) else "otros"
    import resumen_dia
    t = resumen_dia.tipo_pick((post or {}).get("texto") or "")
    return {"córners": "corners", "ganadores": "resultado", "tiros": "jugador"}.get(t, t if t in dict(TITULOS) else "otros")


def contar(dias, resumenes, posts):
    """{tipo: [verdes, total]} de nuestros picks y [verdes, total] de las copias."""
    nuestros, copias = {}, [0, 0]
    for dia in dias:
        for c in (resumenes.get(dia) or {}).get("combis") or []:
            pid, est = c.get("id", ""), c.get("estado")
            if est not in ("verde", "rojo"):
                continue
            if NUESTROS.search(pid):
                n = nuestros.setdefault(tipo_de(posts.get(pid)), [0, 0])
            elif COPIA.search(pid):
                n = copias
            else:
                continue
            n[0] += est == "verde"
            n[1] += 1
    return nuestros, copias


def linea(titulo, v, n):
    pct = v / n if n else 0
    aviso = " ⚠️" if n >= 3 and pct < AVISO_BAJO else ""
    return f"{titulo}: {v} de {n} ({pct:.0%}){aviso}"


def texto(desde, hasta, nuestros, copias):
    lineas = [f"📊 Semana del {desde:%d/%m} al {hasta:%d/%m} · picks de Telegram", ""]
    for t, titulo in TITULOS:
        if t in nuestros:
            lineas.append(linea(titulo, *nuestros[t]))
    if not nuestros:
        lineas.append("Nuestros picks: ninguno resuelto esta semana")
    tv, tn = sum(v for v, _ in nuestros.values()), sum(n for _, n in nuestros.values())
    if tn:
        lineas += ["", linea("✅ Nuestros, en total", tv, tn)]
    if copias[1]:
        lineas.append(linea("📋 Copias de tipsters", *copias))
    if any(n >= 3 and v / n < AVISO_BAJO for v, n in list(nuestros.values()) + [copias]):
        lineas += ["", "⚠️ = por debajo del 55 %: dime si le subimos el listón a ese tipo."]
    return "\n".join(lineas)


def main(ahora=None, enviar=None):
    ahora = ahora or datetime.now(MADRID)
    if ahora.weekday() != 6 or ahora.strftime("%H:%M") < HORA:
        return None
    semana = ahora.strftime("%G-W%V")
    estado = leer(ESTADO, {}) or {}
    if estado.get("enviado") == semana:
        return None
    hasta = ahora.date()
    desde = hasta - timedelta(days=6)
    dias = [(desde + timedelta(days=i)).isoformat() for i in range(7)]
    resumenes = leer(RAIZ / "docs" / "resumenes.json", {}) or {}
    pub = RAIZ / "publicaciones"
    posts = {p["id"]: p for p in (leer(pub / "auto.json", []) or []) + (leer(pub / "cola.json", []) or [])}
    t = texto(desde, hasta, *contar(dias, resumenes, posts))
    if enviar is None:
        from alineaciones_posts import dm as enviar
    enviar(t)
    ESTADO.write_text(json.dumps({"enviado": semana, "cuando": ahora.strftime("%Y-%m-%dT%H:%M")}) + "\n", encoding="utf-8")
    return t


if __name__ == "__main__":
    main()
