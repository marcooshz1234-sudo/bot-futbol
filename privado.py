"""18/11 (Marcos: «quítame todos los avisos del vigilante, al final nunca los leo… los de Threads, si falla algo, no
pasa nada; en Telegram sí quiero que esté todo perfecto: que solo me avise de lo que se elige en Telegram»).

Un solo sitio para decidir qué avisos privados le llegan a Marcos:
  - es_tg(p): el post va (o fue) al canal de Telegram.
  - solo_telegram(): ajuste «avisos_solo_telegram» (por defecto sí). Con él, los avisos de Threads/Instagram, spam,
    noticias, lecciones, crecer en Threads y sus combis personales NO se mandan (se siguen apuntando en sus ficheros).
"""
import re

SOLO_REDES = re.compile(r"-loca-th-|-lista-|ganadores|combi-larga|-boleto-|threads|-ig-")
PASOS_TG = {"publicar_telegram", "verdes_auto", "app_datos", "directo", "resumen_dia", "marca_tg", "copiar_tipsters",
            "combis_dia", "escalera"}


def es_tg(p):
    if not p:
        return False
    if p.get("mensaje_id"):
        return True
    solo = p.get("solo_en")
    if solo:
        return "telegram" in solo
    return not SOLO_REDES.search(p.get("id", ""))


def solo_telegram(control=None):
    try:
        from ajustes import valor
        v = valor("avisos_solo_telegram", control=control)
        return True if v is None else bool(v)
    except Exception:
        return True


ID = re.compile(r"\d{4}-\d\d-\d\d-[\w-]+")


def aviso_vigilante_tg(clave, posts_por_id):
    """¿Este problema del vigilante es de Telegram? Por el id del post que va en la clave; o un paso del bucle de
    Telegram; o la escalera."""
    if clave.startswith(("escalera-", "escalon-")):
        return True
    if clave.startswith("bucle-"):
        return clave.split("-")[1] in PASOS_TG
    if clave.startswith(("redes-", "directo-", "claves-", "repe-", "prensa-", "api-")):
        return False   # Threads/Instagram o ruido
    ids = [m.group(0) for m in ID.finditer(clave)]
    for i in ids:
        for j in sorted(posts_por_id, key=len, reverse=True):
            if i.startswith(j) and es_tg(posts_por_id[j]):
                return True
    return False
