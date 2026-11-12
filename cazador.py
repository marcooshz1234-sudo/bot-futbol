"""11/11 (Marcos: «un bot más en la oficina que esté buscando los errores de bet365: si en Pinnacle lo justo es 1,40
y en bet365 está a 1,60, que me avise rápido para subirlo: “corred, que hay cuotaza”»).

EL CAZADOR (rol de la Oficina). En cada vuelta del bucle repasa los partidos que empiezan en las próximas 30 h:
  1) la probabilidad «justa» de cada salida: la de Pinnacle sin margen si la hay (sharp.py) y si no, la del
     consenso de las otras casas (datos/proximos → cuotas_otras) quitándole el margen;
  2) si bet365 paga bastante más que eso (valor esperado ≥ umbral, por defecto +8 %), es una cuotaza:
     prepara un post «🚨 CUOTAZA» que NO sale solo: te llega al bot del móvil con «✅ Publicar / ❌ No sale»
     (como los verdes). Si le das a Publicar, sale enseguida en Telegram y redes.
Sin mercados prohibidos (más de 2,5 goles del partido, 1ª parte, descanso, tiros del partido, «menos de»).
Las cuotas tienen la hora a la que se bajaron: si son viejas, el aviso lo dice («compruébala en bet365»).
Como mucho 4 avisos al día y nunca dos veces el mismo, salvo que la cuota suba más.
"""
import hashlib
import json
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer

ESTADO = DATOS / "cazador.json"
COLA = RAIZ / "publicaciones" / "cola.json"
MAX_DIA = 4
MAX_PETICIONES = 15        # por vuelta (la API da ~7.500 al día y el bot gasta ~1.200)
REFRESCO = timedelta(minutes=40)
CADA = timedelta(minutes=20)
GRUPOS_LINEA = ("Goals Over/Under", "Goals Over/Under - Second Half", "Total - Home", "Total - Away")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def justas_consenso(otras):
    """{(mercado, opcion): prob} sin margen, de las cuotas de las otras casas."""
    out = {}
    mw = otras.get("Match Winner") or {}
    if all(_f(mw.get(k)) for k in ("Home", "Draw", "Away")):
        inv = {k: 1 / _f(mw[k]) for k in ("Home", "Draw", "Away")}
        t = sum(inv.values())
        for k, v in inv.items():
            out[("Match Winner", k)] = v / t
        out[("Double Chance", "Home/Draw")] = (inv["Home"] + inv["Draw"]) / t
        out[("Double Chance", "Draw/Away")] = (inv["Draw"] + inv["Away"]) / t
    bt = otras.get("Both Teams Score") or {}
    if _f(bt.get("Yes")) and _f(bt.get("No")):
        a, b = 1 / _f(bt["Yes"]), 1 / _f(bt["No"])
        out[("Both Teams Score", "Yes")], out[("Both Teams Score", "No")] = a / (a + b), b / (a + b)
    for m in GRUPOS_LINEA:
        g = otras.get(m) or {}
        for o, c in g.items():
            if not str(o).startswith("Over"):
                continue
            linea = str(o).split()[-1]
            u = _f(g.get(f"Under {linea}"))
            if _f(c) and u:
                a, b = 1 / _f(c), 1 / u
                out[(m, f"Over {linea}")], out[(m, f"Under {linea}")] = a / (a + b), b / (a + b)
    return out


def refrescar(ahora):
    """Cuotas frescas (bet365, Pinnacle y el resto de casas) de los partidos de las próximas 12 h."""
    import os
    from bot import API, recortar_cuotas_casas
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        return 0
    api, n = None, 0
    cands = []
    for f in (DATOS / "proximos").glob("*.json"):
        ex = leer(f, {}) or {}
        pa = ex.get("partido") or {}
        try:
            ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
            hora = datetime.fromisoformat(ex["cuotas_hora"]).astimezone(MADRID) if ex.get("cuotas_hora") else None
        except (KeyError, ValueError):
            continue
        if ahora + timedelta(minutes=20) < ini < ahora + timedelta(hours=12) and (hora is None or ahora - hora > REFRESCO):
            cands.append((ini, f, ex))
    for ini, f, ex in sorted(cands, key=lambda x: x[0])[:MAX_PETICIONES]:
        api = api or API(clave)
        resp = api.get("odds", fixture=ex["partido"]["fixture"]["id"])
        n += 1
        if not resp:
            continue
        b365, otras = recortar_cuotas_casas(resp)
        if b365:
            ex["cuotas"], ex["cuotas_otras"] = b365, otras
            ex["cuotas_hora"] = ahora.isoformat()
            pin = {}
            for item in resp:   # 11/11: Pinnacle, si la API lo trae, como referencia de lo justo
                for casa in item.get("bookmakers") or []:
                    if str(casa.get("name", "")).lower() == "pinnacle":
                        for b in casa.get("bets") or []:
                            pin[b["name"]] = {str(v.get("value")): v.get("odd") for v in b.get("values") or []}
            if pin:
                ex["cuotas_pinnacle"] = pin
            f.write_text(json.dumps(ex, ensure_ascii=False) + "\n", encoding="utf-8")
    return n


def buscar(ahora=None, umbral=0.08, cuota_min=1.40):
    """Lista de cuotazas [{partido_id, local, visitante, inicio, mercado, opcion, cuota, justa, ev, fuente, edad_h}]."""
    import picks as P
    import sharp
    ahora = ahora or datetime.now(MADRID)
    out = []
    for f in (DATOS / "proximos").glob("*.json"):
        ex = leer(f, {}) or {}
        pa = ex.get("partido") or {}
        try:
            ini = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
        except (KeyError, ValueError):
            continue
        if pa["fixture"]["status"]["short"] not in ("NS", "TBD") or not (ahora + timedelta(minutes=20) < ini < ahora + timedelta(hours=30)):
            continue
        try:
            edad = (ahora - datetime.fromisoformat(ex.get("cuotas_hora")).astimezone(MADRID)).total_seconds() / 3600
        except (TypeError, ValueError):
            edad = None
        if edad is None or edad > 8:   # cuotas viejas: no se fía
            continue
        fid = pa["fixture"]["id"]
        cons = justas_consenso(ex.get("cuotas_otras") or {})
        pin_api = justas_consenso(ex.get("cuotas_pinnacle") or {})
        for m, lista in (ex.get("cuotas") or {}).items():
            for o, c in lista or []:
                c = _f(c)
                if not c or c < cuota_min or c > 5 or P.excluido(m, o):   # 11/11 (Marcos): mínimo 1,40
                    continue
                pj, fuente = sharp.prob_justa(fid, m, o) or pin_api.get((m, str(o))), "Pinnacle"
                if not pj:
                    pj, fuente = cons.get((m, str(o))), "las otras casas"
                if not pj or pj < 0.3:
                    continue
                ev = c * pj - 1
                if ev >= umbral:
                    loc, vis = pa["teams"]["home"]["name"], pa["teams"]["away"]["name"]
                    out.append({"partido_id": fid, "local": loc, "visitante": vis, "inicio": ini.strftime("%Y-%m-%dT%H:%M"),
                                "liga": pa["league"].get("name"), "mercado": m, "opcion": str(o), "cuota": c,
                                "justa": round(1 / pj, 2), "ev": round(ev, 3), "fuente": fuente, "edad_h": round(edad, 1),
                                "texto": P.texto_pick(m, o, loc, vis)})
    return sorted(out, key=lambda x: -x["ev"])


def num(x):
    return f"{x:.2f}".replace(".", ",")


def texto_post(x):
    from combis_dia import texto_es
    t = texto_es(x["texto"], x["local"], x["visitante"])
    return "\n".join([
        "🚨 CUOTAZA EN BET365 🚨", "", f"⚽ {x['local']} – {x['visitante']} · {x['inicio'][11:16]}", "",
        f"🍀 {t} @{num(x['cuota'])}", "",
        f"👀 Lo normal sería @{num(x['justa'])}: está mal puesta. Corred antes de que la bajen ⚡",
        "", "🔞 Juega con cabeza", "🔔 Activad las notificaciones, que vienen más combis 👀"])


def main(ahora=None):
    import ajustes as AJ
    c = AJ._control()
    if AJ.pausado("cazador", c):
        print("Cazador: en pausa")
        return []
    umbral = float(AJ.valor("cazador_umbral", c)) / 100
    ahora = ahora or datetime.now(MADRID)
    hoy = ahora.strftime("%Y-%m-%d")
    est = leer(ESTADO, {}) or {}
    avisos = est.setdefault("avisos", {})
    try:
        ult = datetime.fromisoformat((est.get("ultima") or {}).get("hora"))
        ult = ult.replace(tzinfo=MADRID) if ult.tzinfo is None else ult
    except (TypeError, ValueError):
        ult = None
    if ult and ahora - ult < CADA:
        return []
    try:
        print(f"Cazador: {refrescar(ahora)} partidos con cuotas refrescadas")
    except Exception as e:
        print("Cazador (refrescar):", str(e)[:150])
    hoy_n = sum(1 for v in avisos.values() if v.get("dia") == hoy)
    cuota_min = float(AJ.valor("cazador_cuota_min", c))
    hallazgos = buscar(ahora, umbral, cuota_min)
    try:   # para la Oficina: las mejores de la vuelta aunque no lleguen al umbral
        est["top"] = [dict({k: x[k] for k in ("local", "visitante", "inicio", "texto", "cuota", "justa", "ev", "fuente", "edad_h")})
                      for x in buscar(ahora, -0.02, cuota_min)[:8]]
    except Exception as e:
        print("Cazador (top):", str(e)[:120])
    est["ultima"] = {"hora": ahora.strftime("%Y-%m-%dT%H:%M"), "revisadas": len(hallazgos),
                     "mejor": hallazgos[0] if hallazgos else None}
    cola = leer(COLA, []) or []
    # 11/11: una cuotaza que Marcos no aprueba en 60 min ya no vale (la cuota se mueve): se caduca sola
    caducadas = 0
    for p in cola:
        if "-cuotaza-" in p.get("id", "") and p.get("requiere_ok") and not (p.get("enviado") or p.get("mensaje_id")
                                                                             or p.get("redes") or p.get("caducada")):
            try:
                if ahora - datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID) > timedelta(minutes=60):
                    p["caducada"] = True
                    p["nota"] = (p.get("nota") or "") + " · caducada sola: 60 min sin aprobar"
                    caducadas += 1
            except (KeyError, ValueError):
                pass
    if caducadas:
        print(f"Cazador: {caducadas} cuotazas caducadas (60 min sin aprobar)")
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    nuevos = []
    for x in hallazgos:
        if hoy_n >= MAX_DIA:
            break
        k = f"{x['partido_id']}|{x['mercado']}|{x['opcion']}"
        prev = avisos.get(k)
        if prev and x["cuota"] < prev["cuota"] + 0.05:
            continue
        pid = f"{hoy}-cuotaza-{x['partido_id']}-{hashlib.md5(k.encode()).hexdigest()[:6]}"
        if any(p["id"] == pid for p in cola):
            pid += f"-{int(x['cuota'] * 100)}"
        aviso = (f"🚨 CUOTAZA: {x['local']} – {x['visitante']} ({x['inicio'][11:16]})\n{x['texto']} @{num(x['cuota'])} en bet365; "
                 f"lo justo según {x['fuente']} es @{num(x['justa'])} ({x['ev']:+.0%}).\n"
                 + (f"⚠️ Cuotas de hace {x['edad_h']:.0f} h: compruébala en bet365 antes.\n" if x["edad_h"] >= 2 else "")
                 + "¿La subimos? Solo sale si le das a Publicar.")
        cola.append({"id": pid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto_post(x), "foto": None,
                     "origen": "cazador", "directo": True, "requiere_ok": True, "aviso": aviso, "sin_instagram": True,
                     "sel": [k], "cuotas": [x["cuota"]], "cuotaza": x})
        avisos[k] = {"dia": hoy, "cuota": x["cuota"], "ev": x["ev"], "post": pid}
        hoy_n += 1
        nuevos.append(pid)
    if nuevos:
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    est["historial"] = (est.get("historial") or [])[-60:] + [
        {"hora": ahora.strftime("%Y-%m-%dT%H:%M"), "t": f"{x['texto']} @{num(x['cuota'])} (justa {num(x['justa'])}, {x['ev']:+.0%})"}
        for x in hallazgos[:3] if f"{x['partido_id']}|{x['mercado']}|{x['opcion']}" in avisos
        and avisos[f"{x['partido_id']}|{x['mercado']}|{x['opcion']}"].get("post") in nuevos]
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Cazador: {len(hallazgos)} cuotas por encima de lo justo (+{umbral:.0%}), {len(nuevos)} avisos nuevos")
    for x in hallazgos[:5]:
        print(f"  {x['ev']:+.0%} {x['local']}–{x['visitante']} · {x['texto']} @{x['cuota']} (justa {x['justa']}, {x['fuente']}, {x['edad_h']} h)")
    return nuevos


if __name__ == "__main__":
    main()
