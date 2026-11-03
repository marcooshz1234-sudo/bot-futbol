"""
03/11 (Marcos: «el bot no puede equivocarse tanto, tiene que saber quién puede jugar y quién no»): cada 30 min,
para los partidos de las próximas 30 h, vuelve a pedir a la API los lesionados, sancionados y dudosos y:

- los guarda en datos/proximos/<id>.json (así las combis nuevas ya no los meten);
- en los posts que aún no han salido (auto.json y cola.json) con una pata de un jugador de baja: le quita esa pata
  (si quedan 2 o más) o lo cancela, y avisa al móvil;
- en los que ya han salido: avisa al móvil para que decidas (bet365 anula la pata si no juega).

Bajas que la API no da: datos/bajas_manuales.json (las dices tú y se aplican igual).
"""
import json
import os
from datetime import datetime, timedelta

from bot import API, DATOS, EXTRA, MADRID, RAIZ, leer

ESTADO = DATOS / "bajas_hoy.json"
CADA = timedelta(minutes=30)
VENTANA = timedelta(hours=30)
TIPOS = ("Missing Fixture", "Questionable")


def baja(ex, jugador, manuales):
    import picks as P
    nombres = [l["jugador"] for l in ex.get("lesiones") or [] if l.get("tipo") in TIPOS] + manuales
    return next((n for n in nombres if P.mismo_jugador(jugador, n)), None)


def main():
    import picks as P
    from alineaciones_posts import cuotas_sel, dm, quitar_patas, rehacer_imagen
    ahora = datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    clave = os.environ.get("API_FOOTBALL_KEY")
    # 1) refrescar lesiones (cada 30 min)
    if clave and (not est.get("ultima") or ahora - datetime.fromisoformat(est["ultima"]) >= CADA):
        api = API(clave)
        n = 0
        for f in EXTRA.glob("*.json"):
            ex = leer(f) or {}
            pa = ex.get("partido")
            if not pa or pa["fixture"]["status"]["short"] not in ("NS", "TBD"):
                continue
            ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
            if not ahora <= ini <= ahora + VENTANA:
                continue
            try:
                ex["lesiones"] = [{"equipo": l["team"]["id"], "jugador": l["player"]["name"],
                                   "tipo": l["player"].get("type"), "motivo": l["player"].get("reason")}
                                  for l in api.get("injuries", fixture=pa["fixture"]["id"]) or []]
                ex["lesiones_hora"] = ahora.isoformat()
                f.write_text(json.dumps(ex, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                n += 1
            except Exception as e:
                print("bajas:", pa["fixture"]["id"], str(e)[:120])
        est["ultima"] = ahora.isoformat()
        print(f"Bajas: lesiones refrescadas en {n} partidos")
    # 2) revisar los posts de hoy y mañana
    manuales = list((leer(DATOS / "bajas_manuales.json", {}) or {}).get("jugadores") or [])
    avisados = set(est.get("avisados", []))
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    cancelar = []
    en_cola = {p["id"] for p in leer(RAIZ / "publicaciones" / "cola.json", []) or []}
    for nombre in ("auto.json", "cola.json"):
        ruta = RAIZ / "publicaciones" / nombre
        lista = leer(ruta, []) or []
        cambio = False
        for p in lista:
            if p.get("caducada") or p.get("borrar") or p["id"] in control.get("cancelados", []) or not p.get("sel"):
                continue
            if nombre == "auto.json" and p["id"] in en_cola:   # la de la cola manda
                continue
            if not (ahora - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M") <= p.get("fecha", "") \
                    <= (ahora + VENTANA).strftime("%Y-%m-%dT%H:%M"):
                continue   # los de otros días se rehacen solos con las bajas ya quitadas
            fuera = []
            for k, s in enumerate(p["sel"]):
                fid, m, o = s.split("|", 2)
                if m not in P.JUG_MERCADOS:
                    continue
                ex = leer(EXTRA / f"{fid}.json") or {}
                pa = ex.get("partido") or {}
                if pa.get("fixture", {}).get("status", {}).get("short") not in ("NS", "TBD", None):
                    continue
                j = o.rsplit(" - ", 1)[0]
                b = baja(ex, j, manuales)
                if b:
                    fuera.append((k, j))
            if not fuera:
                continue
            nuevos = [(k, j) for k, j in fuera if f"{p['id']}|{j}" not in avisados]
            if not nuevos:
                continue
            avisados |= {f"{p['id']}|{j}" for _, j in nuevos}
            titulo = p["texto"].strip().splitlines()[0][:60]
            nombres = ", ".join(j for _, j in fuera)
            enviado = bool(p.get("enviado") or p.get("mensaje_id") or (enviados.get(p["id"]) or {}).get("enviado"))
            if enviado:
                dm(f"🚑 Bajas: «{titulo}» ({p['fecha'][11:16]}) ya está publicado y lleva a {nombres}, que está de baja "
                   "(lesión, sanción o duda). bet365 anula esa pata si no juega. Si quieres, bórralo y lo rehago.")
                continue
            r = quitar_patas(p, {k for k, _ in fuera}, cuotas_sel())
            if r == "cancelar":
                cancelar.append(p["id"])
                dm(f"🚑 Bajas: he cancelado «{titulo}» ({p['fecha'][11:16]}): lleva a {nombres}, que está de baja.")
            elif r is None:
                dm(f"🚑 Bajas: «{titulo}» ({p['fecha'][11:16]}) lleva a {nombres}, que está de baja, y no he podido quitarlo "
                   "solo. Cámbialo con /editar o cancélalo antes de que salga; en la próxima pasada se rehace sin él.")
            else:
                p.update(r)
                p["revisado_bajas"] = ahora.strftime("%Y-%m-%dT%H:%M")
                cambio = True
                rehacer_imagen(p)
                dm(f"🚑 Bajas: he quitado a {nombres} de «{titulo}» ({p['fecha'][11:16]}): está de baja. Así sale:\n\n{p['texto']}")
        if cambio:
            ruta.write_text(json.dumps(lista, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if cancelar:
        control.setdefault("cancelados", []).extend(x for x in cancelar if x not in control["cancelados"])
        (RAIZ / "publicaciones" / "control.json").write_text(json.dumps(control, ensure_ascii=False, indent=1), encoding="utf-8")
    est["avisados"] = sorted(avisados)[-500:]
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
