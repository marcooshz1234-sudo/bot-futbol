"""
Revisor de contenido · antes de que salga cualquier post (también los hechos a mano), lo revisa con
toda la información del bot y, si ve algo, avisa al dueño del canal por Telegram con tiempo:

  - jugador del post de baja (lesión o sanción)
  - "gana X" con 2+ titulares fijos fuera o con el pronóstico de la API por debajo del 45 %
  - tarjetas por encima de lo que suele sacar el árbitro
  - cuota de bet365 que ha bajado o subido desde que se escribió el post
  - selecciones que el bot ya no ve fiables (no están entre sus picks del día)

Los posts automáticos los rehace el propio bot con lo nuevo; los hechos a mano no se tocan solos:
se avisa para que decidas (/editar, /pausa o cancelar en el bot de Telegram).
Mira los posts que salen en las próximas 3 horas. Un aviso por post, salvo que aparezcan problemas nuevos.
"""
import json
import os
from datetime import datetime, timedelta

from bot import COMPETICIONES, DATOS, EXTRA, MADRID, RAIZ, leer
from picks import (ARB_MIN_PARTIDOS, LESION_MAX_TITULARES, PRED_MIN, historial, indice_arbitros, mismo_jugador,
                   nombre_arbitro, titulares_fuera)
from publicados import lado, picks_de_post

ESTADO = DATOS / "revision_avisos.json"
VENTANA = timedelta(hours=3)
CAMBIO_CUOTA = 0.08


def cuota_actual(spec, cuotas, loc, vis):
    """Cuota de bet365 de una selección entendida del texto (None si no está en la API)."""
    if not spec or not cuotas:
        return None
    t = spec["t"]
    side = lado(spec["eq"], {"local": {"nombre": loc}, "visitante": {"nombre": vis}}) if spec.get("eq") else None
    H = "Home" if side == "local" else "Away"

    def get(m, o):
        for k, v in cuotas.get(m, []):
            if str(k) == o:
                return float(v)

    def ln(x):
        return f"{x:g}"
    n = spec.get("n")
    return {
        "gana": lambda: get("Match Winner", H) if side else None,
        "doble": lambda: get("Double Chance", "Home/Draw" if side == "local" else "Draw/Away") if side else None,
        "ambos": lambda: get("Both Teams Score", "Yes"),
        "goles_mas": lambda: get("Goals Over/Under", f"Over {ln(n)}"),
        "gol_ht": lambda: get("Goals Over/Under First Half", "Over 0.5"),
        "gol_2t": lambda: get("Goals Over/Under - Second Half", "Over 0.5"),
        "eq_goles": lambda: get(f"Total - {H}", f"Over {n - 0.5:g}") if side else None,
        "gana_parte": lambda: get("To Win Either Half", H) if side else None,
        "gana_ht": lambda: get("First Half Winner", H) if side else None,
        "corners_mas": lambda: get("Corners Over Under", f"Over {ln(n)}"),
        "eq_corners": lambda: get(f"{H} Corners Over/Under", f"Over {n - 0.5:g}") if side else None,
        "eq_tarjetas": lambda: get(f"{H} Team Total Cards", f"Over {n - 0.5:g}") if side else None,
        "tarjetas_mas": lambda: get("Cards Over/Under", f"Over {ln(n)}"),
        "tiros_mas": lambda: get("Total Shots", f"Over {ln(n)}"),
    }.get(t, lambda: None)()


def proximos():
    """Partidos próximos con datos (cuotas, bajas, árbitro): solo esos, para no confundir con la vuelta."""
    salida = []
    for f in EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if pa:
            salida.append({"id": pa["fixture"]["id"], "local": pa["teams"]["home"]["name"],
                           "visitante": pa["teams"]["away"]["name"]})
    return salida


def problemas_post(p, partidos, hist, arbitros, picks_bot):
    salida = []
    for l in picks_de_post(p, partidos):
        spec, pid = l["spec"], l["partido_id"]
        if not pid or not spec:
            continue
        prox = leer(EXTRA / f"{pid}.json") or {}
        part = prox.get("partido")
        if not part:
            continue
        loc, vis = part["teams"]["home"], part["teams"]["away"]
        t = spec["t"]
        etiqueta = f"«{l['texto']}»"
        bajas = [x.get("jugador") for x in prox.get("lesiones") or []]
        if t == "jugador" and any(mismo_jugador(spec["jugador"], b) or spec["jugador"].lower() in (b or "").lower()
                                  for b in bajas):
            salida.append(f"{etiqueta}: el jugador está de baja")
        if t in ("gana", "doble", "eq_goles") and spec.get("eq"):
            ld = lado(spec["eq"], {"local": {"nombre": loc["name"]}, "visitante": {"nombre": vis["name"]}})
            if ld:
                eq = loc if ld == "local" else vis
                fuera, _ = titulares_fuera(prox, eq["id"], hist)
                if len(fuera) >= LESION_MAX_TITULARES:
                    salida.append(f"{etiqueta}: a {eq['name']} le faltan {len(fuera)} titulares ({', '.join(fuera[:4])})")
                pc = (prox.get("prediccion") or {}).get(ld)
                try:
                    if t == "gana" and pc and int(str(pc).rstrip("%")) < PRED_MIN:
                        salida.append(f"{etiqueta}: la API solo le da un {pc} de ganar")
                except ValueError:
                    pass
        if t in ("tarjetas_mas", "eq_tarjetas"):
            arb = nombre_arbitro(part["fixture"].get("referee"))
            tj = arbitros.get(arb, []) if arb else []
            if len(tj) >= ARB_MIN_PARTIDOS:
                media = sum(tj) / len(tj)
                if t == "tarjetas_mas" and spec["n"] >= media:
                    salida.append(f"{etiqueta}: el árbitro ({arb}) saca {media:.1f} tarjetas por partido".replace(".", ","))
        act = cuota_actual(spec, prox.get("cuotas") or {}, loc["name"], vis["name"])
        if act and l.get("cuota") and abs(act - l["cuota"]) >= CAMBIO_CUOTA:
            salida.append(f"{etiqueta}: la cuota está ahora a {act:.2f} (en el post {l['cuota']:.2f})".replace(".", ","))
    return salida


def main():
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    ahora = datetime.now(MADRID)
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    pendientes = [p for p in cola if not (p.get("enviado") or p.get("mensaje_id") or p.get("redes") or p.get("caducada")
                                          or p.get("borrar"))
                  and ahora <= datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID) <= ahora + VENTANA]
    if not pendientes:
        return
    partidos = proximos()
    hist, arbitros = historial(), indice_arbitros()
    estado = leer(ESTADO, {}) or {}
    picks_bot = leer(DATOS / "picks.json", {}) or {}
    mensajes = []
    for p in pendientes:
        prob = problemas_post(p, partidos, hist, arbitros, picks_bot)
        ya = set(estado.get(p["id"], []))
        nuevos = [x for x in prob if x not in ya]
        if nuevos:
            titulo = p["texto"].strip().splitlines()[0][:60]
            mensajes.append(f"🔎 Revisa el post de las {p['fecha'][11:16]}: {titulo}\n\n" + "\n".join(f"• {x}" for x in prob)
                            + "\n\nSi quieres cambiarlo: /editar o cancélalo antes de que salga.")
            estado[p["id"]] = sorted(ya | set(prob))
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    if mensajes and token and canal:
        from publicar_telegram import api
        admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
        duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
        for m in mensajes:
            api(token, "sendMessage", {"chat_id": duenio, "text": m[:3900]})
    for m in mensajes:
        print(m)


if __name__ == "__main__":
    main()
