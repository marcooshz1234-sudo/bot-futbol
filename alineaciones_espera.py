"""
03/11 (Marcos): las combis con escudos y los partidos estrella que llevan jugadores no salen a una hora fija: desde
65 min antes del partido se pide la alineación cada 2 min y, en cuanto sale:
  - los que no son titulares se apuntan en datos/proximos/<id>.json («no_titulares») y cuentan como baja;
  - si el post lleva a alguno, se rehace entero sin él (bajas_hoy.rehacer);
  - y se publica en ese momento (unos 55 min antes).
Si a 35 min del partido sigue sin alineación, sale igual (es su hora tope, la pone plantillas.py).
"""
import json
import os
from datetime import datetime, timedelta

from bot import API, DATOS, EXTRA, MADRID, RAIZ, leer

DESDE = timedelta(minutes=65)
CADA = timedelta(minutes=2)
ESTADO = DATOS / "alineaciones_espera.json"


def main():
    from alineaciones_posts import es_el
    import bajas_hoy
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        return
    ahora = datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    cola = leer(RAIZ / "publicaciones" / "cola.json", []) or []
    ids_cola = {p["id"] for p in cola}
    pendientes = []
    for nombre in ("cola.json", "auto.json"):
        for p in leer(RAIZ / "publicaciones" / nombre, []) or []:
            if not p.get("espera_alineacion") or p.get("alineacion_ok") or p["id"] in control.get("cancelados", []):
                continue
            if nombre == "auto.json" and p["id"] in ids_cola:
                continue
            if p.get("enviado") or (enviados.get(p["id"]) or {}).get("enviado"):
                continue
            pendientes.append(p)
    api, publicar = None, []
    for p in pendientes:
        fids = sorted({int(s.split("|", 1)[0]) for s in p.get("sel") or []})
        if not fids:
            continue
        ex = leer(EXTRA / f"{fids[0]}.json") or {}
        pa = ex.get("partido")
        if not pa:
            continue
        ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        if not ini - DESDE <= ahora < ini:
            continue
        guardada = (est.get("xi") or {}).get(str(fids[0]))
        if guardada:
            ex["xi"], ex["no_titulares"] = guardada["xi"], guardada["no_titulares"]
        c = est.setdefault("pedidas", {}).get(str(fids[0]))
        if c and ahora - datetime.fromisoformat(c) < CADA and not ex.get("xi"):
            continue
        if not ex.get("xi"):
            api = api or API(clave)
            xi, banco = [], []
            for eq in api.get("fixtures/lineups", fixture=fids[0]) or []:
                xi += [(x.get("player") or {}).get("name") for x in eq.get("startXI") or []]
                banco += [(x.get("player") or {}).get("name") for x in eq.get("substitutes") or []]
            est["pedidas"][str(fids[0])] = ahora.isoformat()
            if len(xi) < 22:
                print(f"Alineación de {pa['teams']['home']['name']}–{pa['teams']['away']['name']}: todavía no")
                continue
            # todos los jugadores de los dos equipos que no están en el once
            import picks as P
            hist = P.historial()
            conocidos = set()
            for e in (pa["teams"]["home"], pa["teams"]["away"]):
                for partido in hist.get(e["id"], [])[:8]:
                    conocidos |= {j["nombre"] for j in (partido.get("jugadores") or {}).get(str(e["id"])) or []}
            ex["xi"], ex["banquillo"] = xi, banco
            ex["no_titulares"] = sorted(n for n in conocidos if not any(es_el(n, x) for x in xi))
            # 03/11: en el estado (datos/alineaciones_espera.json), no en datos/proximos
            est.setdefault("xi", {})[str(fids[0])] = {"xi": xi, "no_titulares": ex["no_titulares"]}
            ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
        # ¿algún jugador del post no es titular?
        import picks as P
        fuera = []
        for s in p.get("sel") or []:
            fid, m, o = s.split("|", 2)
            if m in P.JUG_MERCADOS:
                j = o.rsplit(" - ", 1)[0]
                if not any(es_el(j, x) for x in ex["xi"]):
                    fuera.append(j)
        nuevo = dict(p)
        if fuera:
            r = bajas_hoy.rehacer(p, [])
            if r:
                nuevo = r
            print(f"Alineación: {p['id']} llevaba a {', '.join(fuera)} (no titular) → {'rehecho' if r else 'sin cambio posible'}")
        nuevo.update(fecha=ahora.strftime("%Y-%m-%dT%H:%M"), alineacion_ok=True, espera_alineacion=True)
        publicar.append(nuevo)
    if publicar:
        ids = {x["id"] for x in publicar}
        cola = [x for x in cola if x["id"] not in ids] + publicar
        (RAIZ / "publicaciones" / "cola.json").write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        from alineaciones_posts import rehacer_imagen
        for x in publicar:
            rehacer_imagen(x)
        print("Alineaciones confirmadas, salen ya:", ", ".join(sorted(ids)))
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
