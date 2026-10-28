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
    if c and c.get("xi") and c.get("equipos"):
        return c
    if c and ahora - datetime.fromisoformat(c["hora"]) < REINTENTO:
        return None
    xi, banco, equipos = [], [], {}
    for eq in api.get("fixtures/lineups", fixture=fid) or []:
        xi += [(x.get("player") or {}).get("name") for x in eq.get("startXI") or []]
        banco += [(x.get("player") or {}).get("name") for x in eq.get("substitutes") or []]
        # 28/10: con equipo y posición, para poner a otro titular en el sitio del que no juega
        equipos[str((eq.get("team") or {}).get("id"))] = [{"n": (x.get("player") or {}).get("name"), "pos": (x.get("player") or {}).get("pos")}
                                                          for x in eq.get("startXI") or []]
    est["alineaciones"][str(fid)] = {"hora": ahora.isoformat(), "xi": xi if len(xi) >= 22 else [], "banquillo": banco,
                                     "equipos": equipos}
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
    if any(s not in cuotas for s in sel):
        return None
    import combis_dia   # 27/10: con el recorte de «Crear apuesta» si quedan patas del mismo partido
    total = combis_dia.cuota_real_sel(sel, [cuotas[s] for s in sel])
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
    texto = re.sub(r"(🎯 CUOTA )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    texto = re.sub(r"(Cuota total aprox\.: )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    texto = re.sub(r"(💶 10€ → )\d+,\d\d€", lambda m: m.group(1) + num(total * 10) + "€", texto)
    r = {"texto": texto, "sel": sel}
    if p.get("cuotas") and len(p["cuotas"]) == len(patas):
        r["cuotas"] = [p["cuotas"][k] for k in quedan]
    return r


CUOTA_SUST = (1.20, 2.30)
FREC_SUST = 0.6
CERCANAS = {"F": ("F", "M"), "M": ("M", "F"), "D": ("D",), "G": ("G",)}


_HIST = {}


def historial():
    if "h" not in _HIST:
        import picks as P
        _HIST["h"] = P.historial()
    return _HIST["h"]


def ficha_jugador(nombre):
    """(id del equipo, posición más habitual) del jugador en sus últimos partidos, o (None, None)."""
    import picks as P
    from collections import Counter
    vistos = set()
    for eq, lista in historial().items():
        for part in lista[:10]:
            if part["id"] in vistos:
                continue
            for j in (part.get("jugadores") or {}).get(str(eq), []):
                if P.mismo_jugador(nombre, j.get("nombre")):
                    pos = Counter(x.get("pos") for pp in lista[:10] for x in (pp.get("jugadores") or {}).get(str(eq), [])
                                  if P.mismo_jugador(nombre, x.get("nombre")) and x.get("pos"))
                    return eq, (pos.most_common(1)[0][0] if pos else j.get("pos"))
    return None, None


def frec_jugador(nombre, eq, campo, n):
    """En cuántos de sus últimos 10 partidos (60'+) llegó a n en ese dato."""
    import picks as P
    si = total = 0
    for part in historial().get(eq, [])[:15]:
        for j in (part.get("jugadores") or {}).get(str(eq), []):
            if P.mismo_jugador(nombre, j.get("nombre")) and (j.get("min") or 0) >= 60 and j.get(campo) is not None:
                total += 1
                si += j[campo] >= n
        if total >= 10:
            break
    return (si / total, total) if total else (0, 0)


def sustituto(fid, mercado, opcion, al):
    """28/10 (Marcos): si el jugador de una pata no es titular, otro titular de su equipo y de su posición con
    cuota en el mismo mercado (p. ej. «tiros» de otro delantero). Devuelve (opción, cuota, texto) o None."""
    import picks as P
    if mercado not in P.JUG_MERCADOS or " - " not in str(opcion):
        return None
    nombre, n = str(opcion).rsplit(" - ", 1)
    campo = P.JUG_MERCADOS[mercado][0]
    eq, pos = ficha_jugador(nombre)
    titulares = (al.get("equipos") or {}).get(str(eq)) if eq else None
    if not titulares:
        return None
    ex = leer(EXTRA / f"{fid}.json") or {}
    cuotas = dict((str(o), v) for o, v in (ex.get("cuotas") or {}).get(mercado, []))
    cand = []
    for x in titulares:
        if pos and x.get("pos") not in CERCANAS.get(pos, (pos,)):
            continue
        clave = next((o for o in cuotas if o.rsplit(" - ", 1)[-1] == n and P.mismo_jugador(o.rsplit(" - ", 1)[0], x["n"])), None)
        if not clave:
            continue
        try:
            c = float(cuotas[clave])
        except (TypeError, ValueError):
            continue
        if not CUOTA_SUST[0] <= c <= CUOTA_SUST[1]:
            continue
        f, nf = frec_jugador(clave.rsplit(" - ", 1)[0], eq, campo, int(float(n)))
        if nf < 5 or f < FREC_SUST:
            continue
        cand.append((x.get("pos") == pos, f, -abs(c - 1.45), clave, c))
    if not cand:
        return None
    _, f, _, clave, c = max(cand)
    pa = ex.get("partido") or {}
    loc, vis = ((pa.get("teams") or {}).get("home") or {}).get("name"), ((pa.get("teams") or {}).get("away") or {}).get("name")
    return clave, c, P.texto_pick(mercado, clave, loc, vis)


def poner_total(texto, total):
    texto = re.sub(r"(🎯 Cuota total: )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    texto = re.sub(r"(🎯 Cuota aprox\.: )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    texto = re.sub(r"(🎯 CUOTA )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    texto = re.sub(r"(Cuota total aprox\.: )\d+,\d\d", lambda m: m.group(1) + num(total), texto)
    return re.sub(r"(💶 10€ → )\d+,\d\d€", lambda m: m.group(1) + num(total * 10) + "€", texto)


PATA_X = re.compile(r"^(🎯|✅)(\d+\.)? (.*?)( \[x\d+\.\d\d\])?$")


def cambiar_patas(p, cambios):
    """cambios: {índice: (opción nueva, cuota, texto)}. Cambia esas patas en el texto, sel y cuotas y recalcula."""
    lineas = p["texto"].split("\n")
    patas = [i for i, l in enumerate(lineas) if re.match(r"^(🎯|✅)(\d+\.)? ", l) and "[x" in l]
    if len(patas) != len(p.get("sel") or []) or not p.get("cuotas") or len(p["cuotas"]) != len(patas):
        return None
    sel, cuotas = list(p["sel"]), list(p["cuotas"])
    quitar = {k for k, v in cambios.items() if v is None}   # sin sustituto: la pata se quita
    if len(patas) - len(quitar) < 3:
        return None
    for k, v in cambios.items():
        if v is None:
            continue
        op, c, txt = v
        pid, m, _ = sel[k].split("|", 2)
        sel[k], cuotas[k] = f"{pid}|{m}|{op}", c
        mt = PATA_X.match(lineas[patas[k]])
        viejo = mt.group(3)
        nuevo = txt.upper() if viejo == viejo.upper() else txt
        lineas[patas[k]] = f"{mt.group(1)}{mt.group(2) or ''} {nuevo} [x{c:.2f}]"
    if quitar:
        primera = lineas[patas[0]]
        lineas = [l for i, l in enumerate(lineas) if i not in {patas[k] for k in quitar}]
        sel = [s for k, s in enumerate(sel) if k not in quitar]
        cuotas = [c for k, c in enumerate(cuotas) if k not in quitar]
        if 0 in quitar:   # la primera pata lleva 🎯
            i = next(i for i, l in enumerate(lineas) if re.match(r"^✅(\d+\.)? ", l) and "[x" in l)
            lineas[i] = primera[:1] + lineas[i][1:] if primera.startswith("🎯") else lineas[i]
    import combis_dia
    total = combis_dia.cuota_real_sel(sel, cuotas)
    return {"texto": poner_total("\n".join(lineas), total), "sel": sel, "cuotas": cuotas, "total": total}


def patas_jugador(p, partidos):
    """[(índice, partido, nombre del jugador, texto)] de las patas de jugador; con sel si lo tiene (las combis de
    partido van en mayúsculas y con [x1.40] y leyendo el texto no se reconocían: Isak y Wirtz el 28/10)."""
    import picks as P
    if p.get("sel"):
        out = []
        for k, s in enumerate(p["sel"]):
            try:
                pid, m, o = s.split("|", 2)
                pid = int(pid)
            except ValueError:
                continue
            if m in P.JUG_MERCADOS or "Scorer" in m:
                out.append((k, pid, str(o).rsplit(" - ", 1)[0], P.texto_pick(m, o, "", "")))
        return out
    return [(k, l.get("partido_id"), (l.get("spec") or {}).get("jugador"), l["texto"])
            for k, l in enumerate(picks_de_post(p, partidos)) if (l.get("spec") or {}).get("t") == "jugador"]


def editar_publicado(p, texto, enviados):
    """Edita el post ya publicado en el canal de Telegram (Threads e Instagram no se pueden editar)."""
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    est = enviados.get(p["id"]) or {}
    mid = p.get("mensaje_id") or est.get("mensaje_id")
    if not (token and canal and mid):
        return False
    from publicar_telegram import api, preparar_texto
    foto = p.get("foto") or p.get("foto_tg") or est.get("foto_tg")
    metodo, campo = ("editMessageCaption", "caption") if foto else ("editMessageText", "text")
    try:
        api(token, metodo, {"chat_id": canal, "message_id": mid, campo: preparar_texto(texto)})
        return True
    except Exception as e:
        print("Alineaciones: no se pudo editar", p["id"], str(e)[:150])
        return False


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
    api, cambios_auto, cambios_cola, cancelar, cambios_control = None, False, False, [], []
    for origen, lista in (("auto", auto), ("cola", cola)):
        for p in lista:
            if p.get("caducada") or p.get("borrar") or p["id"] in control.get("cancelados", []):
                continue
            if p["fecha"] < (ahora - timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M"):
                continue
            enviado = bool((enviados.get(p["id"]) or {}).get("enviado") if origen == "auto"
                           else p.get("enviado") or p.get("mensaje_id"))
            fuera, als = [], {}
            for k, fid, jugador, texto_pata in patas_jugador(p, partidos):
                if not fid or fid not in inicio or not jugador:
                    continue
                if not (-timedelta(minutes=10) <= inicio[fid] - ahora <= VENTANA):
                    continue
                api = api or API(clave)
                al = alineacion(api, fid, est, ahora)
                if not al:
                    continue
                als[k] = (fid, al)
                if not any(es_el(jugador, n) for n in al["xi"]):
                    banco = any(es_el(jugador, n) for n in al["banquillo"])
                    fuera.append((k, texto_pata, banco))
            nuevos = [x for x in fuera if f"{p['id']}|{x[1]}" not in avisados]
            if not nuevos:
                continue
            avisados |= {f"{p['id']}|{x[1]}" for x in nuevos}
            nombres = "\n".join(f"• {t}{' (está en el banquillo)' if b else ' (no está convocado)'}" for _, t, b in fuera)
            titulo = p["texto"].strip().splitlines()[0][:60]
            # 28/10 (Marcos): en las combis del bot (también las que van en la cola con sus selecciones) se pone en
            # su sitio a otro titular de la misma posición y se edita sola, aunque ya esté publicada
            cambios = {}
            if p.get("sel") and p.get("cuotas") and "[x" in p["texto"]:
                for k, _, _ in fuera:
                    pid_, m_, o_ = p["sel"][k].split("|", 2)
                    s = sustituto(int(pid_), m_, o_, als[k][1])
                    cambios[k] = s if s and not any(s[0] == x.split("|", 2)[2] for x in p["sel"]) else None
            r = cambiar_patas(p, cambios) if cambios else None
            if r:
                antes = "\n".join(f"• {t} → {cambios[k][2]} (x{num(cambios[k][1])})" if cambios[k] else
                                   f"• {t} → quitada (no hay otro titular de su posición que lo haga casi siempre)"
                                   for k, t, _ in fuera)
                texto_nuevo = control.get("textos", {}).get(p["id"])
                if texto_nuevo:   # si el post estaba editado a mano, se cambian las mismas líneas en esa versión
                    texto_nuevo = cambiar_patas(dict(p, texto=texto_nuevo), cambios)
                    if texto_nuevo:
                        control["textos"][p["id"]] = texto_nuevo["texto"]
                        cambios_control.append(p["id"])
                p.update({k: r[k] for k in ("texto", "sel", "cuotas")})
                p["revisado_alineaciones"] = ahora.strftime("%Y-%m-%dT%H:%M")
                if origen == "auto":
                    cambios_auto = True
                else:
                    cambios_cola = True
                if enviado:
                    ok = editar_publicado(p, (texto_nuevo or r)["texto"], enviados)
                    dm(f"📋 Alineaciones: «{titulo}» ya estaba publicado y no eran titulares:\n{antes}\n\n"
                       + ("He editado el post del canal (Threads e Instagram no se pueden editar). " if ok else
                          "No he podido editar el canal: /editar. ")
                       + f"Cuota nueva: {num(r['total'])}")
                else:
                    rehacer_imagen(p)
                    dm(f"📋 Alineaciones: en «{titulo}» ({p['fecha'][11:16]}) he cambiado a quien no es titular por "
                       f"otro titular de su posición:\n{antes}\n\nCuota nueva: {num(r['total'])}. Así sale:\n\n{p['texto']}")
                continue
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
    if cambios_cola:
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if cambios_control and not cancelar:
        (RAIZ / "publicaciones" / "control.json").write_text(json.dumps(control, ensure_ascii=False, indent=1),
                                                            encoding="utf-8")
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
