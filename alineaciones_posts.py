"""
Alineaciones confirmadas en los posts · se ejecuta en el bucle cada ~5 min.

Para cada post (del bot o a mano) con alguna pata de jugador cuyo partido empieza en menos de 95 min:
pide la alineación (1 llamada por partido, se guarda) y comprueba que el jugador es titular.

  - Post del bot que aún no ha salido → quita esa pata, recalcula la cuota y rehace la imagen.
    Si se queda con menos de 2 patas, lo cancela. Te avisa por Telegram de lo que ha hecho.
  - Post hecho a mano que aún no ha salido → te avisa para que decidas (/editar o cancelar).
  - Post ya publicado → te avisa (bet365 anula la pata si no juega; con Sustituto+ cuenta el que entre).

Estado en datos/alineaciones_posts.json.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta

from bot import API, DATOS, EXTRA, MADRID, RAIZ, leer
from publicados import picks_de_post
from revisor import proximos

ESTADO = DATOS / "alineaciones_posts.json"
AUTO = RAIZ / "publicaciones" / "auto.json"
COLA = RAIZ / "publicaciones" / "cola.json"
VENTANA = timedelta(minutes=95)
REINTENTO = timedelta(minutes=8)


def norm(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return " ".join(t.replace("-", " ").replace(".", " ").split())


def es_el(nombre_post, nombre_api):
    a, b = norm(nombre_post).split(), norm(nombre_api).split()
    if not a or not b:
        return False
    return a == b or a[-1] == b[-1] or (len(a) == 1 and a[0] in b)


def num(x):
    return f"{x:.2f}".replace(".", ",")


def dm(texto):
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    print(texto)
    if not (token and canal):
        return
    from publicar_telegram import api
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    api(token, "sendMessage", {"chat_id": duenio, "text": texto[:3900]})


def alineacion(api, fid, est, ahora):
    """{'xi': [...], 'banquillo': [...]} o None si todavía no está."""
    c = est.setdefault("alineaciones", {}).get(str(fid))
    if c and c.get("xi"):
        return c
    if c and ahora - datetime.fromisoformat(c["hora"]) < REINTENTO:
        return None
    xi, banco = [], []
    for eq in api.get("fixtures/lineups", fixture=fid) or []:
        xi += [(x.get("player") or {}).get("name") for x in eq.get("startXI") or []]
        banco += [(x.get("player") or {}).get("name") for x in eq.get("substitutes") or []]
    est["alineaciones"][str(fid)] = {"hora": ahora.isoformat(), "xi": xi if len(xi) >= 22 else [], "banquillo": banco}
    return est["alineaciones"][str(fid)] if len(xi) >= 22 else None


def cuotas_sel():
    """Cuota de cada selección del bot ('partido|mercado|opción') sacada de datos/picks.json."""
    d = leer(DATOS / "picks.json", {}) or {}
    out = {}
    for dia in (d.get("dias") or {}).values():
        grupos = [dia.get("picks") or []] + [c.get("picks") or [] for c in dia.get("combis_partido") or []] \
            + [c.get("picks") or [] for c in (dia.get("estilos") or {}).values() if c]
        for g in grupos:
            for p in g:
                out[f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"] = p["cuota"]
    return out


def quitar_patas(p, indices, cuotas):
    """Quita del texto (y de sel) las patas con esos índices; recalcula la cuota. None si no se puede."""
    lineas = p["texto"].split("\n")
    patas = [i for i, l in enumerate(lineas) if re.match(r"^✅(\d+\.)? ", l)]
    if len(patas) != len(p.get("sel") or []) or not patas:
        return None
    quedan = [k for k in range(len(patas)) if k not in indices]
    if len(quedan) < 2:
        return "cancelar"
    sel = [p["sel"][k] for k in quedan]
    total = 1.0
    for s in sel:
        if s not in cuotas:
            return None
        total *= cuotas[s]
    borrar = {patas[k] for k in indices}
    nuevas, n = [], 0
    for i, l in enumerate(lineas):
        if i in borrar:
            continue
        if i in patas and re.match(r"^✅\d+\. ", l):
            n += 1
            l = re.sub(r"^✅\d+\. ", f"✅{n}. ", l)
        nuevas.append(l)
    quitadas = [re.sub(r"^✅(\d+\.)? ", "", lineas[patas[k]]).split(" · ")[0] for k in indices]
    nuevas = [l for l in nuevas if not (l.startswith("📊") and any(q in l for q in quitadas))]
    if nuevas:   # la cuota del título (p. ej. «COMBINADA x3,41»)
        nuevas[0] = re.sub(r"x\d+,\d\d", "x" + num(total), nuevas[0])
    texto = re.sub(r"\n{3,}", "\n\n", "\n".join(nuevas))
    texto = re.sub(r"(🎯 Cuota total: )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    texto = re.sub(r"(🎯 Cuota aprox\.: )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    texto = re.sub(r"(💶 10€ → )\d+,\d\d€", lambda m: m.group(1) + num(total * 10) + "€", texto)
    return {"texto": texto, "sel": sel}


def rehacer_imagen(p):
    try:
        from playwright.sync_api import sync_playwright
        from imagenes import MEDIA, generar
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            generar(p, nav.new_page())
            (MEDIA / f"{p['id']}.huella").write_text(hashlib.sha1((p["texto"] + str(p.get("foto"))).encode()).hexdigest()[:12])
            nav.close()
    except Exception as e:
        print(f"Alineaciones: no se pudo rehacer la imagen de {p['id']} ({e}); se quita la vieja")
        for ext in ("jpg", "mp4"):
            f = RAIZ / "publicaciones" / "media" / f"{p['id']}.{ext}"
            if f.exists():
                f.unlink()


def main():
    clave = os.environ.get("API_FOOTBALL_KEY")
    if not clave:
        return
    ahora = datetime.now(MADRID)
    est = leer(ESTADO, {}) or {}
    avisados = set(est.get("avisados", []))
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    auto = leer(AUTO, []) or []
    cola = leer(COLA, []) or []
    partidos = proximos()
    inicio = {}
    for f in EXTRA.glob("*.json"):
        pa = (leer(f) or {}).get("partido")
        if pa:
            inicio[pa["fixture"]["id"]] = datetime.fromisoformat(pa["fixture"]["date"]).astimezone(MADRID)
    api, cambios_auto, cancelar = None, False, []
    for origen, lista in (("auto", auto), ("cola", cola)):
        for p in lista:
            if p.get("caducada") or p.get("borrar") or p["id"] in control.get("cancelados", []):
                continue
            if p["fecha"] < (ahora - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M"):
                continue
            enviado = bool((enviados.get(p["id"]) or {}).get("enviado") if origen == "auto"
                           else p.get("enviado") or p.get("mensaje_id"))
            patas = picks_de_post(p, partidos)
            fuera = []
            for k, l in enumerate(patas):
                spec, fid = l.get("spec") or {}, l.get("partido_id")
                if spec.get("t") != "jugador" or not fid or fid not in inicio:
                    continue
                if not (-timedelta(minutes=10) <= inicio[fid] - ahora <= VENTANA):
                    continue
                api = api or API(clave)
                al = alineacion(api, fid, est, ahora)
                if not al:
                    continue
                if not any(es_el(spec["jugador"], n) for n in al["xi"]):
                    banco = any(es_el(spec["jugador"], n) for n in al["banquillo"])
                    fuera.append((k, l["texto"], banco))
            nuevos = [x for x in fuera if f"{p['id']}|{x[1]}" not in avisados]
            if not nuevos:
                continue
            avisados |= {f"{p['id']}|{x[1]}" for x in nuevos}
            nombres = "\n".join(f"• {t}{' (está en el banquillo)' if b else ' (no está convocado)'}" for _, t, b in fuera)
            titulo = p["texto"].strip().splitlines()[0][:60]
            if enviado:
                dm(f"📋 Alineaciones: en «{titulo}» (ya publicado) no es titular:\n{nombres}\n\n"
                   "bet365 anula esa pata si no llega a jugar (con Sustituto+ cuenta el que entre por él). "
                   "Si quieres, avisa en el canal.")
            elif origen == "auto" and p.get("sel"):
                r = quitar_patas(p, {k for k, _, _ in fuera}, cuotas_sel())
                if r == "cancelar":
                    cancelar.append(p["id"])
                    dm(f"📋 Alineaciones: «{titulo}» de las {p['fecha'][11:16]} se queda sin patas suficientes "
                       f"(no son titulares):\n{nombres}\n\nLo he cancelado; no saldrá.")
                elif r:
                    p.update(r)
                    p["revisado_alineaciones"] = ahora.strftime("%Y-%m-%dT%H:%M")
                    cambios_auto = True
                    rehacer_imagen(p)
                    dm(f"📋 Alineaciones: he quitado de «{titulo}» ({p['fecha'][11:16]}) a quien no es titular:\n"
                       f"{nombres}\n\nCuota recalculada. Así sale:\n\n{p['texto']}")
                else:
                    dm(f"📋 Alineaciones: en «{titulo}» ({p['fecha'][11:16]}) no es titular:\n{nombres}\n\n"
                       "No he podido recalcular la cuota sola: /editar o cancélalo desde el aviso.")
            else:
                dm(f"📋 Alineaciones: tu post «{titulo}» de las {p['fecha'][11:16]} lleva a quien no es titular:\n"
                   f"{nombres}\n\nCámbialo con /editar o cancélalo antes de que salga.")
    if cambios_auto:
        AUTO.write_text(json.dumps(auto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if cancelar:
        control.setdefault("cancelados", []).extend(cancelar)
        (RAIZ / "publicaciones" / "control.json").write_text(json.dumps(control, ensure_ascii=False, indent=1),
                                                            encoding="utf-8")
    est["avisados"] = sorted(avisados)[-500:]
    limite = (ahora - timedelta(days=2)).isoformat()
    est["alineaciones"] = {k: v for k, v in (est.get("alineaciones") or {}).items() if v["hora"] > limite}
    ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
