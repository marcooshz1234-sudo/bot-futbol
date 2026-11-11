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

COPIAR = ("TipsAnalistas", "Tipster Pérez", "PABLO ANALISTA")
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
            "sel": [f"{pk['partido_id']}|{pk.get('mercado')}|{pk.get('opcion')}"] if pk.get("partido_id") else [],
            "cuotas": [pk.get("cuota")] if pk.get("partido_id") and pk.get("cuota") else [],   # sin cuotas la app no lo corrige
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
            "sel": [f"{p['partido_id']}|{p.get('mercado')}|{p.get('opcion')}" for p in patas if p.get("partido_id")],
            "cuotas": [p.get("cuota") for p in patas if p.get("partido_id")] if all(p.get("cuota") for p in patas) else [],
            "nota": "combinada copiada de un tipster (Marcos 11/11: sí o sí, sin su nombre)"}


def main(ahora=None):
    ahora = ahora or datetime.now(MADRID)
    hoy, manana = ahora.strftime("%Y-%m-%d"), (ahora + timedelta(days=1)).strftime("%Y-%m-%d")
    hechos = set(leer(REGISTRO, []) or [])
    lista = [x for x in leer(DATOS / "tipsters.json", []) or []
             if x.get("tipster") in COPIAR and x.get("dia") in (hoy, manana) and (x.get("partido_id") or x.get("hora"))]
    clave = lambda x: f"{x.get('fuente') or x['tipster'] + '|' + x['dia'] + '|' + x['local']}|{x.get('mercado')}|{x.get('opcion')}"
    sueltos, combis = [], {}
    for x in lista:
        if clave(x) in hechos:
            continue
        try:   # 11/11: los mercados que Marcos no quiere (más de 2,5 goles del partido, 1ª parte, descanso…) no se copian
            from picks import excluido
            if x.get("mercado") and excluido(x["mercado"], x.get("opcion")):
                print(f"Copiar tipsters: {x['texto']} no (mercado prohibido)")
                hechos.add(clave(x))
                continue
        except ImportError:
            pass
        ini = inicio(x)
        if not ini or ini - ahora < MARGEN + ESPERA:
            hechos.add(clave(x))   # ya empezado o muy justo: no se copia (y no se vuelve a mirar)
            continue
        cu, comprobada = cuota_bet365(x)
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
    for x in sueltos:
        p = post_suelto(x, x["_ini"], ahora, siguiente(f"{x['dia']}-pick-tip"))
        nuevos.append(p)
        hechos.add(clave(x))
    for patas in combis.values():
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
