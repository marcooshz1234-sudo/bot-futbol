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
MARGEN = timedelta(minutes=35)
ESPERA = timedelta(minutes=20)


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


def texto_pata(pk):
    t = re.sub(r"\s+", " ", pk["texto"]).strip()
    return f"🍀 {t} @{coma(pk['cuota'])}" if pk.get("cuota") else f"🍀 {t}"


def stake(pk):
    s = pk.get("stake")
    return s if isinstance(s, int) and 1 <= s <= 5 else 2


def post_suelto(pk, ini, ahora, n):
    from plantillas import ETIQUETA_CABEZA
    arg = next((a for a in pk.get("argumento") or [] if len(a) > 25), None)
    try:
        from combis_dia import nombre_es
    except Exception:
        nombre_es = str
    dia = "hoy" if ini.date() == ahora.date() else "mañana" if (ini.date() - ahora.date()).days == 1 else f"{ini:%d/%m}"
    lineas = ["Otro pick que nos gusta mucho familia 🔥", ETIQUETA_CABEZA, "", texto_pata(pk), "",
              f"⚽ {nombre_es(pk['local'])} – {nombre_es(pk['visitante'])} · {dia} {ini:%H:%M}"]
    if arg:
        lineas += ["", f"👨‍💻 {arg}"]
    lineas += ["", f"Stake {stake(pk)}/10"]
    return {"id": f"{pk['dia']}-pick-tip-{n}", "fecha": (ahora + ESPERA).strftime("%Y-%m-%dT%H:%M"),
            "texto": re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", "\n".join(lineas), flags=re.M),
            "foto": None, "origen": "tipster", "directo": True, "forzar": True,
            "sel": [f"{pk['partido_id']}|{pk.get('mercado')}|{pk.get('opcion')}"] if pk.get("partido_id") else [],
            "nota": "copiado de un tipster (Marcos 11/11: sí o sí, sin su nombre)"}


def post_combi(patas, ahora, n):
    from plantillas import ETIQUETA_CABEZA
    patas = sorted(patas, key=lambda x: x["_ini"])   # Marcos: siempre por hora
    total = 1.0
    for p in patas:
        total *= float(p["cuota"]) if p.get("cuota") else 1
    lineas = ["Combinada que nos gusta mucho familia 🔥", ETIQUETA_CABEZA, ""] + [texto_pata(p) for p in patas]
    if all(p.get("cuota") for p in patas):
        lineas += ["", f"📈 Cuota @{coma(total)}"]
    lineas += ["", f"Stake {min(stake(patas[0]), 2)}/10"]
    return {"id": f"{patas[0]['dia']}-combi-tip-{n}", "fecha": (ahora + ESPERA).strftime("%Y-%m-%dT%H:%M"),
            "texto": re.sub(r"(?<=[A-Za-zÀ-ÿ]) W(?=[\s–\-,.)!]|$)", " (fem.)", "\n".join(lineas), flags=re.M),
            "foto": None, "origen": "tipster", "directo": True, "forzar": True,
            "sel": [f"{p['partido_id']}|{p.get('mercado')}|{p.get('opcion')}" for p in patas if p.get("partido_id")],
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
        ini = inicio(x)
        if not ini or ini - ahora < MARGEN + ESPERA:
            hechos.add(clave(x))   # ya empezado o muy justo: no se copia (y no se vuelve a mirar)
            continue
        x = dict(x, _ini=ini)
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
        for p in nuevos:
            print(f"Copiado de tipster: {p['id']} a las {p['fecha'][11:]} · {p['texto'].splitlines()[3]}")
    REGISTRO.write_text(json.dumps(sorted(hechos)[-2000:], ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Copiar tipsters: {len(nuevos)} posts nuevos")
    return nuevos


if __name__ == "__main__":
    main()
