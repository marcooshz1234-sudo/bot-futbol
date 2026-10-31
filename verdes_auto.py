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
from datetime import datetime

from bot import DATOS, MADRID, RAIZ, leer

COLA = RAIZ / "publicaciones" / "cola.json"
ESTADO = DATOS / "verdes_auto.json"
ESPERA = DATOS / "verdes_espera.json"   # 30/10: cuándo se vio cada combi toda en verde por primera vez
ESPERA_MIN = 10                         # minutos en verde antes de celebrarla (gol anulado por el VAR: Espanyol 30/10)
TERMINADO = {"FT", "AET", "PEN"}
ES_COMBI = re.compile(r"COMBI|COMBINADA|ESCALERA|GANA O EMPATA|🆚", re.I)
NO_ES = re.compile(r"¡VERDE|^\s*(📋|🔄|📲)|PICKS PARA|OPCIONES|BALANCE|ASÍ FUE|QUIÉN GANA|RESULTADOS EXACTOS", re.U | re.I)   # 27/10: «✅ COMBI LOCAS» sí


def limpio(t):
    t = re.sub(r"\s*x\d+(,\d+)?", "", t)   # la cuota ya va en "¡VERDE xN!"
    t = re.sub(r"[🔒💥🤪🍀🛡️🎯📊]", "", t).strip()
    return re.sub(r"\s*·\s*$", "", t)          # «LUNES DE GOLES ·» sin el punto suelto


def num(c):
    return f"{c:.2f}".replace(".", ",")


def main():
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
    for p in d.get("publicados_hoy", []):
        # 26/10: también por id (los estilos, p. ej. «⚽ LUNES DE GOLES», no llevan «COMBI» en el título)
        es_combi = ES_COMBI.search(p["titulo"]) or (re.search(r"-combi-|escalera", p["id"]) and "verde-auto" not in p["id"])
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
        x = f" x{num(p['cuota'])}" if p.get("cuota") else ""   # 26/10: la cuota en la primera línea
        titulo = limpio(p["titulo"])
        if "COMBI LOCAS" in p["titulo"]:   # combi de partido: «COMBI LOCAS · SASSUOLO vs LAZIO»
            orig = originales.get(p["id"], {}).get("texto", "").splitlines()
            partido = re.sub(r"[^\w\s.'·-]", "", orig[1]).strip() if len(orig) > 1 else ""
            titulo = f"COMBI LOCAS · {partido}" if partido else "COMBI LOCAS"
        boleto = "-boleto-" in p["id"]   # 27/10: boleto de bet365 (Marcos): solo la foto y poco texto, sin las patas
        if boleto:
            titulo = "CREAR APUESTA"
        texto = f"✅💚 ¡VERDE{x}! {titulo} 💚✅" + ("\n\n📲 Montada en bet365, partido a partido 👇" if boleto else
                                                   "\n\n" + "\n".join(f"✅ {x['texto']}" for x in legs))
        if p.get("cuota"):
            texto += f"\n\n🎯 Cuota {num(p['cuota'])}\n💶 10€ → {num(p['cuota'] * 10)}€"
        texto += "\n\n¿Quién la llevaba? 👇💚"
        pid = f"{ahora:%Y-%m-%d}-verde-auto-{p['id'][-40:]}"
        if pid in ids_cola:
            hechos.add(p["id"])
            continue
        post = {"id": pid, "fecha": ahora.strftime("%Y-%m-%dT%H:%M"), "texto": texto, "foto": None,
                "origen": "bot", "directo": True, "facebook": "foto", "resultado": "verde", "verde_de": p["id"]}
        foto = (originales.get(p["id"]) or {}).get("imagen") or (originales.get(p["id"]) or {}).get("foto")
        if boleto and isinstance(foto, str) and (RAIZ / foto).exists():   # con la captura recortada
            import shutil
            post["foto"] = foto
            shutil.copy(RAIZ / foto, RAIZ / "publicaciones" / "media" / f"{pid}.tarjeta.jpg")
        nuevos.append(post)
        hechos.add(p["id"])
    ESPERA.write_text(json.dumps(espera, ensure_ascii=False) + "\n", encoding="utf-8")
    if not nuevos:
        ESTADO.write_text(json.dumps(sorted(hechos)), encoding="utf-8")
        return
    try:   # imagen y reel sin las líneas de dinero
        from playwright.sync_api import sync_playwright
        from imagenes import generar
        with sync_playwright() as pw:
            nav = pw.chromium.launch()
            pagina = nav.new_page()
            for post in nuevos:
                # sin dinero y sin la foto del boleto (norma de Instagram); la foto solo va a Telegram y Threads
                # (la escalera sí lleva dinero: en eso consiste el reto)
                generar(dict(post, foto=None, texto="\n".join(l for l in post["texto"].splitlines()
                                                              if ("€" not in l or "escalera" in post["id"])
                                                              and "Montada en bet365" not in l)), pagina)
            nav.close()
    except Exception as e:
        print(f"Verdes: sin imagen ({e}); se publica sin Instagram")
        for post in nuevos:
            post["sin_instagram"] = True
    cola.extend(nuevos)
    COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ESTADO.write_text(json.dumps(sorted(hechos)), encoding="utf-8")
    for post in nuevos:
        print("Verde automático:", post["id"])


if __name__ == "__main__":
    main()
