"""
Comunidad de Telegram (26/10)

  1. Concurso semanal «el pick de los seguidores»: cualquiera escribe al bot por privado
     /pick Más de 2,5 goles en Inter–Fiorentina
     (1 pick por persona y día, de partidos de las ligas del bot que no hayan empezado). El bot lo entiende
     con el mismo lector que los posts, lo corrige solo cuando acaba el partido y lleva el ranking.
     /ranking muestra la clasificación de la semana. /start explica cómo va.
  (13/11: quitados el ranking del domingo, el anuncio del lunes y la encuesta en el canal; Marcos 11/11: «quitar los
  tres», en Telegram solo pick del día, escalera y una combi.)

Las respuestas a seguidores las da asistente.py (llama a responder() y guarda en datos/comunidad_picks.json);
corregir se ejecuta en el bucle cada ~10 min con main() y va a datos/comunidad.json.
Solo se guarda el nombre que el usuario tiene en Telegram, para el ranking.
"""
import json
from datetime import datetime, timedelta

from bot import DATOS, EXTRA, MADRID, PARTIDOS, leer
from publicados import buscar_partido, entender, evaluar

ESTADO = DATOS / "comunidad.json"            # lo escribe el bucle: resultados
PICKS = DATOS / "comunidad_picks.json"       # lo escribe solo el asistente (los /pick de los seguidores)
FT = {"FT", "AET", "PEN"}

AYUDA = ("🏆 CONCURSO COMBILOCAS · el pick de los seguidores\n\n"
         "Cada día puedes mandarme 1 pick de las grandes ligas (antes de que empiece el partido):\n"
         "/pick Más de 2,5 goles en Inter–Fiorentina\n"
         "/pick Gana el Barça\n"
         "/pick Mbappé 1+ tiro a puerta\n\n"
         "Lo corrijo yo solo cuando acaba el partido 🏅\n/ranking para ver cómo vas.\n\nSolo es un juego: no hace falta apostar.")


def semana(fecha):
    d = datetime.fromisoformat(fecha[:10])
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def partidos_abiertos(ahora):
    out = []
    for f in EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
            continue
        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        if ahora < ini < ahora + timedelta(days=3):
            out.append({"id": pa["fixture"]["id"], "local": pa["teams"]["home"]["name"],
                        "visitante": pa["teams"]["away"]["name"], "inicio": ini})
    return sorted(out, key=lambda x: x["inicio"])


def guardar(est):
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


def clave(p):
    return f"{p['uid']}|{p['fecha']}"


def todos_picks():
    est, res = leer(PICKS, []) or [], (leer(ESTADO, {}) or {}).get("resultados", {})
    return [dict(p, resultado=res.get(clave(p))) for p in est]


def ranking(picks, sem):
    tabla = {}
    for p in picks:
        if semana(p["fecha"]) != sem:
            continue
        t = tabla.setdefault(p["uid"], {"nombre": p["nombre"], "ok": 0, "jugados": 0, "pendientes": 0})
        t["nombre"] = p["nombre"]
        if p.get("resultado") in ("verde", "rojo"):
            t["jugados"] += 1
            t["ok"] += p["resultado"] == "verde"
        else:
            t["pendientes"] += 1
    return sorted(tabla.values(), key=lambda t: (-t["ok"], t["jugados"], t["nombre"]))


def responder(texto, usuario, ahora=None):
    """Respuesta del bot a un seguidor por privado (texto del mensaje, usuario de Telegram)."""
    ahora = ahora or datetime.now(MADRID)
    texto = (texto or "").strip()
    if texto.startswith("/ranking"):
        filas = ranking(todos_picks(), semana(ahora.strftime("%Y-%m-%d")))
        if not filas:
            return "Aún no hay picks corregidos esta semana. ¡Manda el tuyo con /pick!"
        return "🏆 Ranking de la semana\n\n" + "\n".join(
            f"{i}. {f['nombre']} · {f['ok']}/{f['jugados']}" + (f" (+{f['pendientes']} en juego)" if f["pendientes"] else "")
            for i, f in enumerate(filas[:15], 1))
    if not texto.startswith("/pick"):
        return AYUDA
    pick = texto[5:].strip()
    if len(pick) < 4:
        return "Escríbelo así: /pick Más de 2,5 goles en Inter–Fiorentina"
    picks = leer(PICKS, []) or []
    hoy = ahora.strftime("%Y-%m-%d")
    uid = usuario.get("id")
    if any(p["uid"] == uid and p["fecha"][:10] == hoy for p in picks):
        return "Hoy ya tienes tu pick 😉 Mañana puedes mandar otro."
    spec, ctx = entender(pick)
    if not spec:
        return ("No lo he entendido 🤔 Prueba con algo como:\n/pick Más de 2,5 goles en Inter–Fiorentina\n"
                "/pick Gana el Barça\n/pick Ambos marcan en Milan–Roma")
    abiertos = partidos_abiertos(ahora)
    pa = (buscar_partido(abiertos, *ctx) if ctx else None) or \
        (buscar_partido(abiertos, equipo=spec.get("eq")) if spec.get("eq") else None)
    if not pa and spec.get("t") == "jugador":
        return "Para picks de jugador dime también el partido: /pick Mbappé 1+ tiro a puerta en PSG–Lyon"
    if not pa:
        return "No encuentro ese partido entre los próximos de las grandes ligas (o ya ha empezado)."
    nombre = usuario.get("first_name") or usuario.get("username") or "Anónimo"
    picks.append({"uid": uid, "nombre": nombre[:24], "texto": pick[:120], "spec": spec,
                                        "partido_id": pa["id"], "partido": f"{pa['local']} – {pa['visitante']}",
                                        "fecha": ahora.strftime("%Y-%m-%dT%H:%M"),
                                        "inicio": pa["inicio"].strftime("%Y-%m-%dT%H:%M")})
    corte = (ahora - timedelta(days=21)).strftime("%Y-%m-%d")
    PICKS.write_text(json.dumps([p for p in picks if p["fecha"] >= corte], ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return (f"✅ Apuntado: «{pick}»\n⚽ {pa['local']} – {pa['visitante']} · {pa['inicio']:%d/%m %H:%M}\n\n"
            "Te lo corrijo cuando acabe. /ranking para ver la clasificación.")


def corregir(est):
    cambios = 0
    res = est.setdefault("resultados", {})
    for p in leer(PICKS, []) or []:
        if res.get(clave(p)) in ("verde", "rojo"):
            continue
        d = leer(PARTIDOS / f"{p['partido_id']}.json")
        if not d or d.get("estado") not in FT:
            continue
        r = evaluar(p["spec"], d)
        if r in ("verde", "rojo"):
            res[clave(p)] = r
            cambios += 1
    return cambios


def main():
    ahora = datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    # 11/11 (Marcos: «quitar los tres»): ni encuesta, ni concurso, ni ranking en el canal (en Telegram solo pick del
    # día, escalera y una combi). Los picks que manden los seguidores por privado se siguen corrigiendo
    try:
        corregir(est)
    except Exception as e:
        print("comunidad:", str(e)[:200])
    vivos = {clave(p) for p in leer(PICKS, []) or []}
    est["resultados"] = {k: v for k, v in (est.get("resultados") or {}).items() if k in vivos}
    guardar(est)


if __name__ == "__main__":
    main()
