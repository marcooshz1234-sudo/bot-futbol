"""11/11 07:19 (Marcos: «que esté pendiente al Pérez, a TipsAnalistas y a Pablo Analista, a ver qué suben, y
copiárselo»). Opciones que eligió: Telegram + redes, directo (sin esperar su OK), también las combinadas.

Cada pick suyo apuntado en datos/tipsters.json (lo apunta el bot solo si viene en texto claro —tipsters_auto.py— o
Claude en sus revisiones si viene en foto) sale como un pick NUESTRO: sin su nombre ni su boleto, con nuestro estilo
(«🍀 pick @cuota», «👨‍💻 argumento», stake) y la foto CL del pick del día. Las combinadas salen como combi nuestra.

- Solo partidos que aún no han empezado (al menos 35 min antes) y de hoy o mañana.
- Sale a los 20 min (da tiempo a que imagenes.py haga la foto).
- Registro de lo ya copiado: datos/tipsters_copiados.json.
"""
import json
import re
from datetime import datetime, timedelta

from bot import DATOS, MADRID, leer

COPIAR = ("TipsAnalistas", "Tipster Pérez", "PABLO ANALISTA")   # los primeros; desde el 12/11, todos los de fútbol
# 12/11 (Marcos: «siempre que podamos, los picks que suban los canales de Telegram que seguimos, que se los copiemos…
# la mayoría los aciertan»): se copian los de TODOS los canales que seguimos, menos los de baloncesto y tenis
NO_FUTBOL = re.compile(r"nba|basquet|basket|tenis|tennis", re.I)
CUOTA_SOLA = 1.35   # por debajo, un pick suelto NUNCA sale solo (Marcos 12/11: «¿quién va a coger eso?»): se junta
#                    con otros en una combi que llegue a 1,35; si no tiene con quién, no se sube
ESPERA_PAREJA = timedelta(hours=3)   # los bajos esperan a juntarse hasta 3 h antes del primer partido


def es_de_futbol(tipster):
    return bool(tipster) and not NO_FUTBOL.search(tipster)


def sel_de(x):
    return f"{x['partido_id']}|{x.get('mercado')}|{x.get('opcion')}" if x.get("partido_id") else None


VARIAS = re.compile(r"crear apuesta|mymatch|bet ?builder", re.I)
PROHIBIDO_TEXTO = re.compile(r"1ª parte|1a parte|primera parte|1er tiempo|primer tiempo|\b1T\b|descanso|medio tiempo"
                             r"|fuera de juego|tiros totales|remates totales", re.I)


def motivo_no(x, usos):
    """12/11: por qué NO se copia esta pata (o None): choca con lo nuestro de ese partido («nunca chocar»), ya va en
    2 posts (máx. 2) o va a favor de un equipo al que le falta su estrella (Mbappé)."""
    s = sel_de(x)
    if not s:
        return None
    from plantillas import choca
    if choca(s, list(usos)):
        return "choca con un post nuestro de ese partido"
    if usos[s] >= 2:
        return "ya va en 2 posts"
    try:
        import revision
        sin = revision.lados_sin_estrella(x["partido_id"])
        if any(revision.favorece(s, lado) for lado in sin):
            return "a su equipo le falta una estrella (prensa)"
    except Exception as e:
        print("copiar_tipsters (estrellas):", e)
    return None
REGISTRO = DATOS / "tipsters_copiados.json"
COLA = DATOS.parent / "publicaciones" / "cola.json"
MARGEN = timedelta(minutes=15)
ESPERA = timedelta(minutes=2)   # 11/11 15:37 (Marcos: «subirlo rápido, las casas bajan la cuota»): la foto la hace este mismo script


ABRE_PICK = ["Otro pick que nos gusta mucho familia 🔥", "Vamos con otro pick, familia 👇", "Este nos encanta para hoy 🔥",
             "Os dejo otro pick que pinta muy bien 👀", "Pick que no podía faltar hoy ⚽"]
ABRE_COMBI = ["Combinada que nos gusta mucho familia 🔥", "Vamos con una combinada cortita 👇",
              "Os dejo una combinada que pinta bien 👀", "Combinada para hoy, con cabeza ⚽"]


def abrir(lista, semilla):
    """11/11 (Marcos: «no quiero un canal repetitivo»): la primera frase cambia de un post a otro."""
    import hashlib
    return lista[int(hashlib.sha1(semilla.encode()).hexdigest(), 16) % len(lista)]


def coma(c):
    return f"{float(c):.2f}".replace(".", ",")


def inicio(pk):
    """Hora de inicio (Madrid) del partido del pick, de nuestros datos."""
    fid = pk.get("partido_id")
    if not fid:   # 11/11: partidos que no seguimos (EFL Trophy…): la hora que apunta Claude («hora»: "20:00")
        if pk.get("hora") and pk.get("dia"):
            return datetime.fromisoformat(f"{pk['dia']}T{pk['hora']}").replace(tzinfo=MADRID)
        return None
    pa = (leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("partido") or {}
    f = (pa.get("fixture") or {}).get("date")
    if not f:
        for c in DATOS.glob("calendario_*.json"):
            x = next((x for x in leer(c, []) or [] if x["fixture"]["id"] == fid), None)
            if x:
                f = x["fixture"]["date"]
                break
    return datetime.fromisoformat(f).astimezone(MADRID) if f else None


def cuota_bet365(pk):
    """11/11 (Marcos: «comprueba las cuotas, no te fíes de lo que pongan ellos»): la de bet365 que tenemos ahora
    (datos/cuotas_frescas.json o la del partido), si la hay; si no, la suya."""
    fid = str(pk.get("partido_id") or "")
    if VARIAS.search(pk.get("texto") or ""):   # 12/11: un «Crear apuesta» no es la cuota de su primera pata (1,54 ≠ 1,27)
        return pk.get("cuota"), False
    if fid:
        for c in ((leer(DATOS / "cuotas_frescas.json", {}) or {}).get(fid, {}).get("cuotas"),
                  ((leer(DATOS / "proximos" / f"{fid}.json", {}) or {}).get("cuotas") or {})):
            try:
                v = float((c or {})[pk["mercado"]][pk["opcion"]])
                if 1.01 < v < 50:
                    return v, True
            except (KeyError, TypeError, ValueError):
                pass
    return pk.get("cuota"), False


def texto_pata(pk):
    t = re.sub(r"\s+", " ", pk["texto"]).strip()
    return f"🍀 {t} @{coma(pk['cuota'])}" if pk.get("cuota") else f"🍀 {t}"


def stake(pk):
    s = pk.get("stake")
    return s if isinstance(s, int) and 1 <= s <= 5 else 2


def post_suelto(pk, ini, ahora, n):
    from plantillas import etiqueta
    arg = next((a for a in pk.get("argumento") or [] if len(a) > 25), None)
    try:
        from combis_dia import nombre_es
    except Exception:
        nombre_es = str
    dia = "hoy" if ini.date() == ahora.date() else "mañana" if (ini.date() - ahora.date()).days == 1 else f"{ini:%d/%m}"
    et = etiqueta("cabeza", f"{pk['dia']}-pick-tip-{n}")   # 11/11: no siempre la misma etiqueta
    lineas = [abrir(ABRE_PICK, f"{pk['dia']}-pick-tip-{n}")] + ([et] if et else []) + ["", texto_pata(pk), "",
              f"⚽ {nombre_es(pk['local'])} – {nombre_es(pk['visitante'])} · {dia} {ini:%H:%M}"]
    if arg:
        lineas += ["", f"👨‍💻 {arg}"]
    lineas += ["", f"Stake {stake(pk)}/10"]
    return {"id": f"{pk['dia']}-pick-tip-{n}", "fecha": (ahora + ESPERA).strftime("%Y-%m-%dT%H:%M"),
            "texto": re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", "\n".join(lineas), flags=re.M),
            "foto": None, "origen": "tipster", "directo": True, "forzar": True,
            # 12/11: un «Crear apuesta»/MyMatch (gana Inglaterra + goles en la 1ª parte…) lleva varias condiciones y
            # solo tenemos una apuntada: sin sel, para que no salga el verde con una pata (lo corrige Claude a mano)
            "sel": [f"{pk['partido_id']}|{pk.get('mercado')}|{pk.get('opcion')}"]
                   if pk.get("partido_id") and not VARIAS.search(pk.get("texto") or "") else [],
            "cuotas": [pk.get("cuota")] if pk.get("partido_id") and pk.get("cuota")
                      and not VARIAS.search(pk.get("texto") or "") else [],   # sin cuotas la app no lo corrige
            "nota": "copiado de un tipster (Marcos 11/11: sí o sí, sin su nombre)"}


def post_combi(patas, ahora, n):
    from plantillas import etiqueta
    patas = sorted(patas, key=lambda x: x["_ini"])   # Marcos: siempre por hora
    total = 1.0
    for p in patas:
        total *= float(p["cuota"]) if p.get("cuota") else 1
    et = etiqueta("cabeza", f"{patas[0]['dia']}-combi-tip-{n}")
    lineas = [abrir(ABRE_COMBI, f"{patas[0]['dia']}-combi-tip-{n}")] + ([et] if et else []) + [""] + [texto_pata(p) for p in patas]
    if all(p.get("cuota") for p in patas):
        lineas += ["", f"📈 Cuota @{coma(total)}"]
    lineas += ["", f"Stake {min(stake(patas[0]), 2)}/10"]
    return {"id": f"{patas[0]['dia']}-combi-tip-{n}", "fecha": (ahora + ESPERA).strftime("%Y-%m-%dT%H:%M"),
            "texto": re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", "\n".join(lineas), flags=re.M),
            "foto": None, "origen": "tipster", "directo": True, "forzar": True,
            # 11/11: si alguna pata es de un partido que no seguimos, NADA de corrección automática: con patas a medias
            # el verde saldría aunque la pata sin seguir fallase (el verde/rojo lo prepara Claude a mano)
            "sel": [f"{p['partido_id']}|{p.get('mercado')}|{p.get('opcion')}" for p in patas]
                   if all(p.get("partido_id") for p in patas) else [],
            "cuotas": [p.get("cuota") for p in patas]
                      if all(p.get("partido_id") and p.get("cuota") for p in patas) else [],
            "nota": "combinada copiada de un tipster (Marcos 11/11: sí o sí, sin su nombre)"}


def main(ahora=None):
    ahora = ahora or datetime.now(MADRID)
    hoy, manana = ahora.strftime("%Y-%m-%d"), (ahora + timedelta(days=1)).strftime("%Y-%m-%d")
    hechos = set(leer(REGISTRO, []) or [])
    lista = [x for x in leer(DATOS / "tipsters.json", []) or []
             if es_de_futbol(x.get("tipster")) and x.get("dia") in (hoy, manana) and (x.get("partido_id") or x.get("hora"))]
    from combis_dia import ya_publicadas
    usos = {d: ya_publicadas(d) for d in (hoy, manana)}   # lo nuestro de ese día (publicado y programado)
    clave = lambda x: f"{x.get('fuente') or x['tipster'] + '|' + x['dia'] + '|' + x['local']}|{x.get('mercado')}|{x.get('opcion')}"
    sueltos, combis = [], {}
    rotas = set()
    for x in lista:
        if clave(x) in hechos:
            continue
        # 12/11 (Marcos: «esos mercados sí los puedes usar, y más si lo dicen ellos»): lo de los canales se copia
        # aunque sea más de 2,5 goles, 1ª parte, descanso… (los prohibidos son solo para las combis del bot)
        ini = inicio(x)
        if not ini or ini - ahora < MARGEN + ESPERA:
            hechos.add(clave(x))   # ya empezado o muy justo: no se copia (y no se vuelve a mirar)
            continue
        por = motivo_no(x, usos[x["dia"]])
        if por:
            print(f"Copiar tipsters: {x['texto']} no ({por})")
            hechos.add(clave(x))
            if x.get("combinada"):   # 12/11: sin una pata ya no es su combinada (y su cuota conjunta no vale): fuera entera
                rotas.add(f"{x['tipster']}|{x['combinada']}")
            continue
        cu, comprobada = cuota_bet365(x)
        if not cu:   # 12/11: sin cuota no se sube (podría ser un 1,12); se vuelve a mirar en la siguiente pasada
            print(f"Copiar tipsters: {x['texto']} sin cuota, espera")
            continue
        from bot import CUOTA_MINIMA_PATA, CUOTA_PATA_ELITE, pata_de_elite
        elite = x.get("combinada") and float(cu) >= CUOTA_PATA_ELITE and pata_de_elite(x)   # «España gana es muy, muy buena»
        if float(cu) < CUOTA_MINIMA_PATA and not elite:   # 12/11 (Marcos): ni sola ni en combi por debajo de 1,20
            print(f"Copiar tipsters: {x['texto']} no (cuota {cu} < {CUOTA_MINIMA_PATA})")
            hechos.add(clave(x))
            if x.get("combinada"):
                rotas.add(f"{x['tipster']}|{x['combinada']}")
            continue
        if comprobada and x.get("cuota") and cu < float(x["cuota"]) - 0.001:
            print(f"Cuota bajada en bet365: {x['texto']} {x['cuota']} → {cu}")
        x = dict(x, _ini=ini, cuota=cu, cuota_comprobada=comprobada)
        if x.get("combinada"):
            combis.setdefault(f"{x['tipster']}|{x['combinada']}", []).append(x)
        else:
            sueltos.append(x)
    cola = leer(COLA, []) or []
    ids = {p["id"] for p in cola}
    nuevos = []

    def siguiente(base):
        n = 1
        while f"{base}-{n}" in ids:
            n += 1
        ids.add(f"{base}-{n}")
        return n
    from plantillas import choca
    # 12/11 (Marcos: «si ves que son pocas cosas o picks bajos, que los combines; si no, los subes como ellos»):
    # los de cuota baja (< 1,35) se juntan en UNA combi de partidos distintos y sin chocar (hasta 4 patas). Se espera
    # a tener 3, o a que falten menos de 3 h para el primero; entonces se juntan los que haya (mínimo 2 y @1,35)
    bajos = sorted([x for x in sueltos if x.get("cuota") and float(x["cuota"]) < CUOTA_SOLA and sel_de(x)],
                   key=lambda x: x["_ini"])
    usados = set()
    for dia_ in sorted({x["dia"] for x in bajos}):
        grupo = []
        for x in (x for x in bajos if x["dia"] == dia_):
            if len(grupo) < 4 and all(x["partido_id"] != g["partido_id"] for g in grupo) \
                    and not choca(sel_de(x), [sel_de(g) for g in grupo]):
                grupo.append(x)
        tot = 1.0
        for g in grupo:
            tot *= float(g["cuota"])
        listo = len(grupo) >= 3 or (grupo and grupo[0]["_ini"] - ahora <= ESPERA_PAREJA)
        if len(grupo) >= 2 and tot >= CUOTA_SOLA and listo:
            usados |= {id(g) for g in grupo}
            nuevos.append(post_combi(grupo, ahora, siguiente(f"{dia_}-combi-tip")))
            hechos.update(clave(g) for g in grupo)
            for g in grupo:
                usos[dia_][sel_de(g)] += 1
    for x in sueltos:
        if id(x) in usados:
            continue
        if x in bajos or (x.get("cuota") and float(x["cuota"]) < CUOTA_SOLA):
            print(f"Copiar tipsters: {x['texto']} espera pareja (cuota {x['cuota']}, sola no sale)")
            continue   # no se apunta en «hechos»: si sale otra de cuota baja, se juntan
        p = post_suelto(x, x["_ini"], ahora, siguiente(f"{x['dia']}-pick-tip"))
        nuevos.append(p)
        hechos.add(clave(x))
        if sel_de(x):
            usos[x["dia"]][sel_de(x)] += 1
    for nombre_combi, patas in combis.items():
        from bot import CUOTA_MINIMA_POST
        if nombre_combi in rotas:
            print(f"Copiar tipsters: combinada {nombre_combi} no (le falta una pata)")
            hechos.update(clave(x) for x in patas)
            continue
        tot = 1.0
        for x in patas:
            tot *= float(x.get("cuota") or 0) or 1
        from bot import COMBI_CON_ELITE, CUOTA_MINIMA_PATA
        bajas_ = [x for x in patas if x.get("cuota") and float(x["cuota"]) < CUOTA_MINIMA_PATA]
        if bajas_ and (len(bajas_) > 1 or tot < COMBI_CON_ELITE):   # la de élite, una y en combis de 1,50 o más
            print(f"Copiar tipsters: combinada @{tot:.2f} no (pata de élite baja en combi corta o más de una)")
            hechos.update(clave(x) for x in patas)
            continue
        if tot < CUOTA_MINIMA_POST:   # 12/11: una combinada suya (o lo que queda de ella) por debajo de 1,35, no
            print(f"Copiar tipsters: combinada @{tot:.2f} no (menos de {CUOTA_MINIMA_POST})")
            hechos.update(clave(x) for x in patas)
            continue
        if len(patas) == 1:   # una sola pata apuntada de la combinada: sale como pick suelto
            p = post_suelto(patas[0], patas[0]["_ini"], ahora, siguiente(f"{patas[0]['dia']}-pick-tip"))
        else:
            p = post_combi(patas, ahora, siguiente(f"{patas[0]['dia']}-combi-tip"))
        nuevos.append(p)
        hechos.update(clave(x) for x in patas)
    if nuevos:
        cola += nuevos
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:   # foto y reel al momento (Instagram no espera a la pasada de imagenes.py); solo en el bot de GitHub
            import os
            if os.environ.get("GITHUB_ACTIONS") != "true":
                raise RuntimeError("fuera del bot: las fotos las hará imagenes.py")
            import imagenes
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                nav = pw.chromium.launch()
                pg = nav.new_page()
                for p in nuevos:
                    imagenes.generar(p, pg)
                    (imagenes.MEDIA / f"{p['id']}.huella").write_text(imagenes.huella(p))
                nav.close()
        except Exception as e:
            print("copiar_tipsters (fotos):", e)
        for p in nuevos:
            print(f"Copiado de tipster: {p['id']} a las {p['fecha'][11:]} · {p['texto'].splitlines()[3]}")
    REGISTRO.write_text(json.dumps(sorted(hechos)[-2000:], ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Copiar tipsters: {len(nuevos)} posts nuevos")
    return nuevos


if __name__ == "__main__":
    main()
