"""
Verdes automáticos · cuando una combi publicada sale verde, el bot sube el post de "¡VERDE!" solo
(Telegram, Threads, Instagram y Facebook), igual que se hacía a mano.

- Lo decide con los resultados de docs/datos.json (publicados_hoy): todas las selecciones en verde.
- Solo combis (combinadas, combis de partido, escalera, gana o empata); no listas de picks ni posts informativos.
- La imagen de Instagram va sin el dinero (norma: nunca dinero ni boleto en imágenes de Instagram).
- Cada combi se celebra una sola vez (datos/verdes_auto.json).
"""
import json
import re
from datetime import datetime, timedelta

from pathlib import Path

from bot import DATOS, MADRID, RAIZ, leer

COLA = RAIZ / "publicaciones" / "cola.json"
ESTADO = DATOS / "verdes_auto.json"
MEDIA = RAIZ / "publicaciones" / "media"
ESPERA = DATOS / "verdes_espera.json"   # 30/10: cuándo se vio cada combi toda en verde por primera vez
ESPERA_MIN = 10                         # minutos en verde antes de celebrarla (gol anulado por el VAR: Espanyol 30/10)
VENTANA_GRUPO = 15                      # 12/11: un verde seguro espera 15 min por si cae otro y salen juntos (ya no, 17/11)
SEPARACION = 10                         # 17/11 (Marcos): los verdes de Telegram, uno a uno, cada 10 min entre ellos
ESPERA_CONFIRMAR = 30                   # 12/11: minutos máximos esperando a que todas las patas estén confirmadas
TERMINADO = {"FT", "AET", "PEN"}
ES_COMBI = re.compile(r"COMBI|COMBINADA|ESCALERA|GANA O EMPATA|🆚|PICK SEGURO|PICK DEL DÍA", re.I)   # 01/11: pick seguro
NO_ES = re.compile(r"¡VERDE|^\s*(📋|🔄|📲)|PICKS PARA|OPCIONES|BALANCE|ASÍ FUE|QUIÉN GANA|RESULTADOS EXACTOS", re.U | re.I)   # 27/10: «✅ COMBI LOCAS» sí


def limpio(t):
    t = re.sub(r"\s*x\d+(,\d+)?", "", t)   # la cuota ya va en "¡VERDE xN!"
    t = re.sub(r"[🔒💥🤪🍀🛡️🎯📊]", "", t).strip()
    return re.sub(r"\s*·\s*$", "", t)          # «LUNES DE GOLES ·» sin el punto suelto


def num(c):
    return f"{c:.2f}".replace(".", ",")


def main():
    try:   # 10/11: Verificador en pausa desde la Oficina
        import ajustes as AJ
        if AJ.pausado("verificador"):
            print("Verificador en pausa (Oficina): sin verdes ni rojos")
            return
    except Exception as e:
        print("ajustes verificador:", e)
    d = leer(RAIZ / "docs" / "datos.json", {}) or {}
    hechos = set(leer(ESTADO, []) or [])
    cola = leer(COLA, []) or []
    ids_cola = {p["id"] for p in cola}
    ahora = datetime.now(MADRID)
    originales = {p["id"]: p for p in (leer(RAIZ / "publicaciones" / "auto.json", []) or []) + cola
                  + (leer(RAIZ / "publicaciones" / "asistente.json", []) or [])}
    nuevos = []
    espera_antes = leer(ESPERA, {}) or {}
    espera = {}
    # 14/11 (Marcos: «va a salir lo mismo dos veces»): el mismo pick copiado de dos canales (Gana el Almería @1,75
    # y @1,83) daba dos verdes y un «2 VERDES». Se celebra una vez por selección: misma(s) pata(s) = mismo verde.
    def clave(p):
        import unicodedata
        norm = lambda t: "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")
        return tuple(sorted(f"{x.get('partido_id')}|{norm(x.get('texto'))}" for x in p.get("picks", [])))
    celebrados = {clave(p) for p in d.get("publicados_hoy", []) if p["id"] in hechos and p.get("picks")}
    for p in d.get("publicados_hoy", []):
        if p.get("picks") and p["id"] not in hechos and clave(p) in celebrados and p.get("estado") == "verde":
            print("Verde repetido (misma selección ya celebrada):", p["id"])
            hechos.add(p["id"])
            continue
        # 26/10: también por id (los estilos, p. ej. «⚽ LUNES DE GOLES», no llevan «COMBI» en el título)
        es_combi = ES_COMBI.search(p["titulo"]) or (re.search(r"-combi-|escalera|-pick-", p["id"]) and "verde-auto" not in p["id"])
        # 17/11 (Marcos: «en Threads, si no es una combi mínimo x5 no se sube»): las locas de Threads también
        # (la centenaria, el duelo, los tapados…), pero no las listas ni los ganadores
        # 18/11 (Marcos): cada acierto de Threads va en el comentario de su post, también las listas
        es_combi = es_combi or (re.search(r"-loca-th-", p["id"]) and not re.search(r"ganadores", p["id"]))   # 10/11: el pick del día ya no lleva «PICK DEL DÍA» en el título
        if p["id"] in hechos or p.get("estado") != "verde" or not es_combi or NO_ES.search(p["titulo"]):
            continue
        legs = [x for x in p.get("picks", []) if x.get("estado") == "verde"]
        # 31/10: una pata anulada (partido aplazado o suspendido) no tumba la combi, como en bet365
        if not legs or not all(x.get("estado") in ("verde", "anulada") for x in p.get("picks", [])):
            continue
        # 30/10: no se celebra al momento. Espera a que terminen los partidos o a que siga en verde 10 min
        # (si el VAR anula el gol, la pata vuelve a pendiente y no sale el verde)
        visto = espera_antes.get(p["id"]) or ahora.strftime("%Y-%m-%dT%H:%M")
        espera[p["id"]] = visto
        terminados = all(x.get("estado_partido") in TERMINADO for x in legs if x.get("estado_partido"))
        minutos = (ahora - datetime.fromisoformat(visto).replace(tzinfo=MADRID)).total_seconds() / 60
        if not terminados and minutos < ESPERA_MIN:
            continue
        # 12/11: espera a que la fuente confirme el resultado (confirmar.py, ~15 min tras el final) para poder subirlo solo
        if not all(x.get("definitivo") for x in legs) and minutos < ESPERA_CONFIRMAR:
            continue
        # 07/11 (Marcos): con una pata anulada (partido aplazado) bet365 paga sin ella: la cuota se rehace
        # 10/11 (Marcos: «si sale acertado, que ponga la cuota de la publicación que hemos hecho»): los picks no
        # traen la cuota en el título; se saca del post publicado («🍀 … @1,57» / «Cuota @x») o de las patas
        orig_txt = (originales.get(p["id"]) or {}).get("texto") or ""
        if not p.get("cuota"):
            m = re.search(r"^🍀 [^\n]*@(\d+,\d+)", orig_txt, re.M) or re.search(r"Cuota @(\d+,\d+)", orig_txt)
            if m:
                p = dict(p, cuota=float(m.group(1).replace(",", ".")))
            elif p.get("picks") and all(x.get("cuota") for x in p["picks"]):
                import math
                p = dict(p, cuota=round(math.prod(float(x["cuota"]) for x in p["picks"]), 2))
        p = dict(p, cuota=cuota_real(p))
        anuladas = [x for x in p.get("picks", []) if x.get("estado") == "anulada"]
        x = f" x{num(p['cuota'])}" if p.get("cuota") else ""   # 26/10: la cuota en la primera línea
        titulo = limpio(p["titulo"])
        if "COMBI LOCAS" in p["titulo"]:   # combi de partido: «COMBI LOCAS · SASSUOLO vs LAZIO»
            orig = originales.get(p["id"], {}).get("texto", "").splitlines()
            partido = re.sub(r"[^\w\s.'·-]", "", orig[1]).strip() if len(orig) > 1 else ""
            titulo = f"COMBI LOCAS · {partido}" if partido else "COMBI LOCAS"
        boleto = "-boleto-" in p["id"]   # 27/10: boleto de bet365 (Marcos): solo la foto y poco texto, sin las patas
        if boleto:
            titulo = "CREAR APUESTA"
        # 09/11 (Marcos: «parecemos un bot»): como los tipsters de verdad: corto y con alegría
        frases = ["Otra más pa' la saca familia 😎", "A cobrar señores 🤑", "Seguimos sumando 📈",
                  "¿Quién la llevaba? 👇💚"]
        # 10/11: en un pick suelto, el pick tal cual lo publicamos («Inter (fem.) marca», no «Inter Milano W marca»)
        trebol = re.search(r"^🍀 ([^\n@]+?)\s*@", orig_txt, re.M)
        if len(legs) == 1 and len(p.get("picks") or []) == 1 and trebol:
            legs = [dict(legs[0], texto=trebol.group(1).strip())]
            p = dict(p, picks=legs)   # también en la imagen del ticket
        legs = [dict(x, texto=re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", x["texto"])) for x in legs]
        texto = "PARA DENTRO SEÑORES ✅🤑" + ("\n\n📲 Montada en bet365, partido a partido 👇" if boleto else
                                            "\n\n" + "\n".join(f"✅ {x['texto']}" for x in legs))
        if anuladas and not boleto:
            texto += "\n" + "\n".join(f"🔵 {x['texto']} (no se jugó: no cuenta)" for x in anuladas)
        if p.get("cuota"):
            texto += f"\n\n📈 Cuota @{num(p['cuota'])}"
            if "escalera" in p["id"]:   # la escalera sí lleva el dinero (en eso consiste el reto)
                texto += f"\n💶 {titulo_escalera(p)}"
        from plantillas import cierre_a_veces   # 12/11 (Marcos): la frase final, solo a veces
        texto = cierre_a_veces(texto + "\n\n" + frases[sum(map(ord, p["id"])) % len(frases)], p["id"])
        pid = f"{ahora:%Y-%m-%d}-verde-auto-{p['id'][-40:]}"
        if pid in ids_cola:
            hechos.add(p["id"])
            continue
        # 12/11 (Marcos: «los acertados que los suba de una ni pregunte, pero tiene que estar seguro; si no, que me lo
        # mande»): si es seguro sale solo; si hay cualquier duda, como antes, con su «✅ Publicar»
        duda = dudas(p, boleto)
        post = {"id": pid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
                "origen": "bot", "directo": True, "facebook": "foto", "resultado": "verde", "verde_de": p["id"],
                "_combi": p}
        solo_threads = (originales.get(p["id"]) or {}).get("solo_en") == ["threads"]
        if duda and not solo_threads:   # 18/11: el comentario del acierto en su post de Threads sale solo
            post.update(requiere_ok=True, aviso=f"💚 ¡VERDE! Te lo paso porque {duda}. Sale cuando le des a Publicar.")
        # 17/11 (Marcos: «que suba ya las que se van acertando, una a una cada 10 min entre ellas»): ya no espera
        # 15 min para juntarlos; escalonar() los separa
        for k in ("solo_en", "solo_redes"):   # 12/11: el verde va donde fue el post (uno solo de Threads → solo Threads)
            if (originales.get(p["id"]) or {}).get(k):
                post[k] = originales[p["id"]][k]
        # 15/11: las copias van partidas (Instagram en «…», Telegram y Threads en «…-e»): el verde, en todas las de la familia
        if post.get("solo_en") == ["instagram"] and any(i.startswith(p["id"] + "-") for i in originales):
            redes_ = {"instagram"} | {r for i, o in originales.items() if i.startswith(p["id"] + "-") for r in (o.get("solo_en") or [])}
            post["solo_en"] = [r for r in ("telegram", "instagram") if r in redes_] or ["telegram", "instagram"]
        foto = (originales.get(p["id"]) or {}).get("imagen") or (originales.get(p["id"]) or {}).get("foto")
        if boleto and isinstance(foto, str) and (RAIZ / foto).exists():   # con la captura recortada
            import shutil
            post["foto"] = foto
            shutil.copy(RAIZ / foto, RAIZ / "publicaciones" / "media" / f"{pid}.tarjeta.jpg")
        nuevos.append(post)
        # 15/11: Inglaterra remates, Bélgica–Italia y Francia córners no llevaron su verde en Threads: en Threads
        # estaban en «…-e» / «…-t» (otro id). Cada post de la familia que salió en Threads lleva su comentario.
        for i, o in originales.items():
            if i.startswith(p["id"] + "-") and (o.get("redes") or {}).get("threads") and not o.get("caducada") \
                    and "threads" not in (post.get("solo_en") or ["threads"]):
                vid = f"{ahora:%Y-%m-%d}-verde-auto-{i[-40:]}"
                if vid not in ids_cola:
                    nuevos.append({**{k: v for k, v in post.items() if k not in ("solo_en", "solo_redes")},
                                   "id": vid, "verde_de": i, "solo_en": ["threads"]})
        if p.get("picks"):
            celebrados.add(clave(p))   # 14/11: la otra copia del mismo pick ya no sale
        hechos.add(p["id"])
    try:
        import ajustes as AJ   # 10/11: ficha del Verificador: rojos del pick del día sí / no
        nuevos_rojos = rojos(d, hechos, ahora, ids_cola) if AJ.valor("rojos_pick") else []
        nuevos_rojos += casi_por_una(d, hechos, ahora, ids_cola)
    except Exception as e:
        print("rojos:", e)
        nuevos_rojos = []
    ESPERA.write_text(json.dumps(espera, ensure_ascii=False) + "\n", encoding="utf-8")
    if nuevos_rojos:
        cola.extend(nuevos_rojos)
        if not nuevos:
            COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not nuevos:
        ESTADO.write_text(json.dumps(sorted(hechos)), encoding="utf-8")
        return
    # 09/11 (Marcos): imagen del verde = ticket de Combilocas (opción 2); si mandó la captura real de su apuesta
    # para ese post, en Telegram y Threads va su captura con la franja «✔ ACERTADO» (opción 1)
    try:
        from playwright.sync_api import sync_playwright
        import ticket_verde as T
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pagina = nav.new_page()
            for post in nuevos:
                combi = post.get("_combi") or {}
                orig = originales.get(post["verde_de"]) or {}
                publicado = (orig.get("enviado") or combi.get("fecha") or "")[11:16]
                post["_ticket"] = str(T.ticket(pagina, combi, publicado, MEDIA / f"{post['id']}.ticket.jpg"))
                captura = T.CAPTURAS / f"{post['verde_de']}.jpg"
                if not captura.exists() and post.get("foto"):   # boleto de bet365 que subió Marcos
                    captura = RAIZ / post["foto"]
                foto = MEDIA / f"{post['id']}.tarjeta.jpg"
                if captura.exists():
                    T.sello(captura, foto)
                else:
                    import shutil
                    shutil.copy(post["_ticket"], foto)
                post["foto"] = str(foto.relative_to(RAIZ))
            nav.close()
    except Exception as e:
        print(f"Verdes: sin ticket ({e})")
    try:   # imagen y reel sin las líneas de dinero
        from playwright.sync_api import sync_playwright
        from imagenes import generar
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pagina = nav.new_page()
            for post in nuevos:
                # sin dinero y sin la foto del boleto (norma de Instagram); la foto solo va a Telegram y Threads
                # (la escalera sí lleva dinero: en eso consiste el reto)
                generar(dict(post, foto=None, tarjeta=None, texto="\n".join(l for l in post["texto"].splitlines()
                                                              if ("€" not in l or "escalera" in post["id"])
                                                              and "Montada en bet365" not in l)), pagina)
                tk = post.get("_ticket")
                if tk and Path(tk).exists():   # 09/11: en Instagram, el ticket (sin dinero) en vez del texto
                    import shutil
                    shutil.copy(tk, MEDIA / f"{post['id']}.jpg")
                    (MEDIA / f"{post['id']}.mp4").unlink(missing_ok=True)   # sin reel: en Instagram, el ticket
            nav.close()
    except Exception as e:
        print(f"Verdes: sin imagen ({e}); se publica sin Instagram")
        for post in nuevos:
            post["sin_instagram"] = True
    for post in nuevos:
        post.pop("_combi", None)
        post.pop("_ticket", None)
    cola.extend(nuevos)
    try:
        escalonar(cola, ahora)
    except Exception as e:
        print("Verdes: sin escalonar:", e)
    COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ESTADO.write_text(json.dumps(sorted(hechos)), encoding="utf-8")
    for post in nuevos:
        print("Verde automático:", post["id"])


NOMBRES = [("pick-seguro-2", "Segundo pick"), ("pick-seguro-3", "Otro pick"), ("pick-seguro-4", "Otro pick"), ("pick-seguro", "Pick del día"), ("escalera", "Reto escalera"),
           ("combi-tres", "Combi del día"), ("combi-partido", "Combi del partido"), ("combi-loca", "La loca"),
           ("combi-multi", "Combi larga"), ("combi-", "Combi"), ("pick-", "Pick")]


def _ya_salio(p):
    env = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    e = env.get(p["id"]) or {}
    return bool(p.get("enviado") or p.get("mensaje_id") or e.get("enviado") or e.get("mensaje_id")
                or any((p.get("redes") or {}).values()))


COMPARTIR = DATOS / "compartir.json"


def compartir(ahora, cada=timedelta(days=4)):
    """15/11 (Marcos: «lo puedes meter pero muy de vez en cuando»): en el post de varios verdes, como mucho una vez
    cada 4 días, se pide compartir el canal (con la gente contenta). Solo Telegram e Instagram (el grupo no va a Threads)."""
    import os
    if os.environ.get("GITHUB_ACTIONS") != "true":   # solo el bot (las pruebas no lo apuntan)
        return ""
    ult = (leer(COMPARTIR, {}) or {}).get("ultimo")
    if ult and ahora - datetime.fromisoformat(ult) < cada:
        return ""
    from redes import ENLACE_TELEGRAM
    COMPARTIR.write_text(json.dumps({"ultimo": ahora.isoformat()}) + "\n", encoding="utf-8")
    return f"\n\n📲 ¿Tienes un colega que apueste? Pásale el canal y que se suba 👉 {ENLACE_TELEGRAM}"


def escalonar(cola, ahora, cada=SEPARACION):
    """17/11 (Marcos: «que suba ya las que se van acertando, una a una cada 10 min entre ellas»; antes, 12/11, iban
    juntas en un post). Los verdes de hoy que van a Telegram y aún no han salido: cada uno al menos `cada` min
    después del anterior (contando el último que ya salió). Devuelve los que ha movido."""
    dia = ahora.strftime("%Y-%m-%d")
    env = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}
    a_tg = lambda p: (p.get("resultado") == "verde" and p.get("verde_de") and p["id"].startswith(dia)
                      and (not p.get("solo_en") or "telegram" in p["solo_en"]) and not p.get("caducada"))
    salidos = [(p.get("enviado") or (env.get(p["id"]) or {}).get("enviado") or "")[:16] for p in cola if a_tg(p) and _ya_salio(p)]
    ultimo = max((s for s in salidos if s), default=None)
    siguiente = datetime.fromisoformat(ultimo).replace(tzinfo=MADRID) + timedelta(minutes=cada) if ultimo else None
    movidos = []
    for p in sorted((p for p in cola if a_tg(p) and not _ya_salio(p) and not p.get("requiere_ok")), key=lambda p: (p["fecha"], p["id"])):
        f = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
        if siguiente and f < siguiente:
            p["fecha"] = siguiente.strftime("%Y-%m-%dT%H:%M")
            movidos.append(p["id"])
            f = siguiente
        siguiente = f + timedelta(minutes=cada)
    return movidos


def agrupar(cola, ahora):
    """12/11 (Marcos: «si hay varias apuestas, que haga una foto en conjunto para que no haya tantas»).
    Si hay 2 o más verdes seguros (sin «✅ Publicar») de hoy que aún no han salido, en Telegram e Instagram sale UN
    post con todos y una sola foto. Cada verde suelto sigue saliendo en Threads como comentario de su post."""
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    fuera = set(control.get("cancelados") or [])
    dia = ahora.strftime("%Y-%m-%d")
    sueltos = [p for p in cola if p.get("resultado") == "verde" and p.get("verde_de") and not p.get("requiere_ok")
               and p["id"].startswith(dia) and not p.get("agrupado_en") and p["id"] not in fuera
               and not p.get("caducada") and not p.get("solo_redes") and "-verde-grupo-" not in p["id"]
               and (not p.get("solo_en") or "telegram" in p["solo_en"]) and not _ya_salio(p)]
    if len(sueltos) < 2:
        return None
    gid = f"{dia}-verde-grupo-{ahora:%H%M}"
    lineas = []
    for p in sorted(sueltos, key=lambda p: p["verde_de"]):
        nombre = next((n for k, n in NOMBRES if k in p["verde_de"]), "Verde")
        patas = re.findall(r"^✅ (.+)$", p["texto"], re.M)
        c = re.search(r"Cuota @(\d+,\d+)", p["texto"])
        lo = patas[0] if len(patas) == 1 else " + ".join(patas) if len(patas) <= 2 else f"{len(patas)} patas"
        lineas.append(f"✅ {nombre} · {lo}" + (f" @{c.group(1)}" if c else ""))
    from plantillas import lema_verde
    texto = (f"🔥 ¡{len(sueltos)} VERDES PARA DENTRO! 🔥\n\n" + "\n".join(lineas)
             + f"\n\n💚 {lema_verde(gid)}") + compartir(ahora)
    grupo = {"id": gid, "fecha": max(p["fecha"] for p in sueltos), "texto": texto, "foto": None, "origen": "bot",
             "directo": True, "resultado": "verde", "verdes": [p["id"] for p in sueltos],
             "solo_en": ["telegram", "instagram"]}
    try:   # una sola foto con todos (la misma plantilla de los verdes de varias patas)
        from playwright.sync_api import sync_playwright
        import fotos
        patas = [{"texto": re.sub(r"^✅ ", "", l), "estado": "verde"} for l in lineas]
        html = fotos.verde_lista(patas, f"{len(sueltos)} VERDES", None, None,
                                 cajas=[("VERDES", str(len(sueltos))), ("DÍA", ahora.strftime("%d/%m"))],
                                 lema=lema_verde(gid) + " 🍀")
        destino = MEDIA / f"{gid}.tarjeta.jpg"
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pagina = nav.new_page(viewport={"width": 1080, "height": 1350})
            pagina.set_content(html)
            pagina.wait_for_timeout(200)
            h = pagina.evaluate("document.documentElement.scrollHeight")
            if h > 1350:
                pagina.evaluate(f"document.body.style.transformOrigin='top center';document.body.style.transform='scale({1350 / h:.4f})'")
            pagina.screenshot(path=str(destino), type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            nav.close()
        import shutil
        shutil.copy(destino, MEDIA / f"{gid}.jpg")   # Instagram
        grupo["foto"] = str(destino.relative_to(RAIZ))
    except Exception as e:
        print("Verdes: grupo sin foto:", e)
        grupo["sin_instagram"] = True
    for p in sueltos:   # el suelto ya no sale en Telegram ni Instagram: solo como comentario en Threads
        p["agrupado_en"] = gid
        p["solo_en"] = ["threads"]
        p["fecha"] = grupo["fecha"]   # 12/11: si no, uno que llevaba rato esperando ya no salía en Threads (>45 min)
    cola.append(grupo)
    print("Verdes agrupados:", gid, [p["id"] for p in sueltos])
    return grupo


def dudas(p, boleto=False):
    """12/11: por qué un verde NO es seguro (y hay que mandárselo a Marcos), o None si puede salir solo."""
    from bot import CUOTA_MINIMA_POST
    picks = p.get("picks") or []
    if boleto:
        return "es un boleto de bet365 (hay que mirarlo a mano)"
    if not picks or any(x.get("estado") != "verde" for x in picks):
        return "alguna pata no está en verde (anulada o sin resultado)"
    if not all(x.get("definitivo") for x in picks):
        return "el resultado de alguna pata aún no está confirmado"
    if not p.get("cuota"):
        return "no sé la cuota con la que se publicó"
    ids = [x.get("partido_id") for x in picks if x.get("partido_id")]
    if len(set(ids)) < len(ids):   # 13/11: varias patas de un mismo partido = «Crear apuesta»: la cuota no se multiplica
        from bot import leer as _leer, RAIZ as _R
        dada = (_leer(_R / "publicaciones" / "control.json", {}) or {}).get("cuota_dada") or {}
        if p.get("id") not in dada:
            return "lleva varias patas del mismo partido y su cuota no está confirmada"
    if p["cuota"] < CUOTA_MINIMA_POST:
        return f"la cuota es muy baja (@{num(p['cuota'])})"
    return None


def titulo_escalera(p):
    """«37€ → 64,01€» del escalón (datos/escalera.json); si no está, solo la cuota."""
    try:
        e = leer(DATOS / "escalera.json", {}) or {}
        for h in [e.get("actual") or {}] + list(e.get("historial") or []):
            if h.get("dia") and h["dia"] in p["id"]:
                return f"{num(h['stake'])}€ → {num(h['stake'] * h['cuota'])}€"
    except Exception:
        pass
    return ""


def rojos(d, hechos, ahora, ids_cola):
    """09/11 (Marcos): el pick del día que falla también se cuenta (da confianza). Pasa por su OK como los verdes."""
    nuevos = []
    for p in d.get("publicados_hoy", []):
        if p["id"] in hechos or p.get("estado") != "rojo" or not re.search(r"-pick-seguro(-\d)?$", p["id"]):
            continue
        if not all(x.get("definitivo") or x.get("estado_partido") in TERMINADO for x in p.get("picks", [])):
            continue
        x = (p.get("picks") or [{}])[0]
        m = x.get("marcador")
        res = f" ({x.get('partido', '')} {m[0]}–{m[1]})" if isinstance(m, list) and len(m) == 2 else ""
        texto = (f"Hoy no ha podido ser ❌\n\n❌ {x.get('texto', '')}{res}\n\n"
                 "Aquí se marcan también los fallos. Mañana volvemos con todo 💪")
        pid = f"{ahora:%Y-%m-%d}-rojo-auto-{p['id'][-40:]}"
        hechos.add(p["id"])
        if pid in ids_cola:
            continue
        nuevos.append({"id": pid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
                       "origen": "bot", "directo": True, "resultado": "rojo", "rojo_de": p["id"], "requiere_ok": True,
                       "sin_instagram": True})
    return nuevos


CASI_MIN = 30   # 16/11 (Marcos: «si alguna muy gorda falla por uno, se sube»): «muy gorda» = cuota 30 o más


def cuota_combi(p):
    """Cuota de la combi: el producto de sus patas si todas la traen; si no, la publicada."""
    import math
    picks = p.get("picks") or []
    if picks and all(x.get("cuota") for x in picks):
        return round(math.prod(float(x["cuota"]) for x in picks), 2)
    return float(p.get("cuota") or 0)


def casi_por_una(d, hechos, ahora, ids_cola):
    """16/11 (Marcos): una combi muy gorda (≥ x30) que se cae por UNA pata se sube a Threads («se escapó por una»).
    Todas las demás en verde, todos los partidos acabados. Pasa por su «✅ Publicar», como los rojos."""
    nuevos = []
    for p in d.get("publicados_hoy", []):
        pid0 = p["id"]
        clave = "casi-" + pid0
        picks = p.get("picks") or []
        if clave in hechos or p.get("estado") != "rojo" or len(picks) < 3 or "-boleto-" in pid0:
            continue
        if not re.search(r"-loca-th-|-combi-", pid0) or re.search(r"lista|ganadores|marcadores", pid0):
            continue
        rojas = [x for x in picks if x.get("estado") == "rojo"]
        resto = [x for x in picks if x.get("estado") != "rojo"]
        if len(rojas) != 1 or not all(x.get("estado") in ("verde", "anulada") for x in resto):
            continue
        if not all(x.get("definitivo") or x.get("estado_partido") in TERMINADO for x in picks):
            continue
        cuota = cuota_combi(p)
        if cuota < CASI_MIN:
            continue
        verdes = sum(x.get("estado") == "verde" for x in resto)
        c = f"{cuota:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        texto = (f"😱 SE NOS ESCAPÓ POR UNA 😱\n\n💎 Combi x{c} · {verdes} de {len(picks)} ✅\n"
                 f"❌ Solo falló: {rojas[0].get('texto', '')}\n\n🔥 La próxima entra. ¿Os subís? 👇")
        hechos.add(clave)
        nid = f"{ahora:%Y-%m-%d}-casi-auto-{pid0[-40:]}"
        if nid in ids_cola:
            continue
        nuevos.append({"id": nid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
                       "origen": "bot", "directo": True, "resultado": "casi", "casi_de": pid0, "requiere_ok": True,
                       "solo_en": ["threads"]})
    return nuevos


def cuota_real(p):
    """Cuota contando solo las patas que no se anularon (como paga bet365). Sin datos, la publicada."""
    import math
    picks = p.get("picks") or []
    anuladas = [x for x in picks if x.get("estado") == "anulada"]
    if not anuladas or not p.get("cuota"):
        return p.get("cuota")
    vivas = [x for x in picks if x.get("estado") != "anulada"]
    if vivas and all(x.get("cuota") for x in vivas):
        return round(math.prod(float(x["cuota"]) for x in vivas), 2)
    if all(x.get("cuota") for x in anuladas):
        return round(p["cuota"] / math.prod(float(x["cuota"]) for x in anuladas), 2)
    return p.get("cuota")


if __name__ == "__main__":
    main()
