"""
Publicador de Telegram para el canal Combilocas.

Lee publicaciones/cola.json y publica en el canal las que ya han llegado a su
hora. Cada publicación enviada se marca con el id del mensaje para que nunca
salga dos veces. Lo lanza GitHub Actions cada 15 minutos.

Formato de cada publicación en la cola:
{
  "id": "2026-10-27-picks-manana",      # único
  "fecha": "2026-10-27T23:00",          # hora de España
  "texto": "🔥 9 PICKS PARA MAÑANA ...",
  "foto": "publicaciones/fotos/x.jpg"   # opcional (o null)
}
"""

import json
import re
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from incidencias import ambiguo

RAIZ = Path(__file__).resolve().parent
COLA = RAIZ / "publicaciones" / "cola.json"        # posts manuales (estado dentro)
# Regla (23/10): lo que sale en un sitio sale en todos (Threads, Instagram, Facebook y Telegram).
# Los posts automáticos de El Analista solo podrían ir a Telegram, así que no se publican solos:
# se usan como borrador y se programan a la vez en todas las redes.
AUTOS = [RAIZ / "publicaciones" / "auto.json"]   # posts del bot (plantillas.py); alineaciones.json ya no
ENVIADOS = RAIZ / "publicaciones" / "enviados.json"  # estado de los de auto.json
CONTROL = RAIZ / "publicaciones" / "control.json"    # decisiones desde el móvil (asistente)
MADRID = ZoneInfo("Europe/Madrid")
PIE = "🔞 +18 | Juega con responsabilidad"
MAX_RETRASO = timedelta(minutes=45)   # más tarde ya no se publica: podría haber empezado el partido
LIMITE_TEXTO = 4096
LIMITE_PIE_FOTO = 1024


def api(token, metodo, datos=None, archivo=None, campo="photo", tipo="image/jpeg"):
    url = f"https://api.telegram.org/bot{token}/{metodo}"
    if archivo:
        frontera = uuid.uuid4().hex
        cuerpo = b""
        for k, v in datos.items():
            cuerpo += (f"--{frontera}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
        nombre = Path(archivo).name
        cuerpo += (f"--{frontera}\r\nContent-Disposition: form-data; name=\"{campo}\"; filename=\"{nombre}\"\r\n"
                   f"Content-Type: {tipo}\r\n\r\n").encode()
        cuerpo += Path(archivo).read_bytes() + f"\r\n--{frontera}--\r\n".encode()
        req = Request(url, data=cuerpo, headers={"Content-Type": f"multipart/form-data; boundary={frontera}"})
    else:
        req = Request(url, data=json.dumps(datos).encode(), headers={"Content-Type": "application/json"})
    for intento in range(3):
        try:
            with urlopen(req, timeout=60) as r:
                return json.load(r)
        except HTTPError as e:
            resp = json.loads(e.read() or b"{}")
            espera = resp.get("parameters", {}).get("retry_after")
            if e.code == 429 and espera:
                time.sleep(espera + 1)
                continue
            raise RuntimeError(f"Telegram {e.code}: {resp.get('description')}")
        except (URLError, TimeoutError):
            if metodo in ("sendMessage", "sendPhoto"):
                raise RuntimeError("Envío sin confirmación: comprueba el canal antes de repetir") from None
            time.sleep(5)
    raise RuntimeError("Telegram no responde")


CUOTA_ANIMACION = 3.0   # 12/11 (Marcos: «la del verde solo para buenas cuotas acertadas»)
ANIMACION_VERDE = RAIZ / "publicaciones" / "media" / "marca" / "verde.mp4"


def cuota_de_verde(p, texto):
    """Cuota de un verde («¡VERDE x3,42!»); None si no es un verde."""
    if not (p.get("resultado") == "verde" or p.get("verde_de") or "verde" in p.get("id", "")):
        return None
    m = re.search(r"VERDE\s*x\s*(\d+[.,]\d+)", texto, re.I) or re.search(r"Cuota\s*@?\s*(\d+[.,]\d+)", texto)
    return float(m.group(1).replace(",", ".")) if m else None


def foto_de_marca(p, texto):
    """12/11 (Marcos: «activa todo menos el balance de la noche»): la escalera, el pick del día y los rojos, que
    salían sin foto en Telegram, llevan la imagen de la marca (publicaciones/media/marca)."""
    pid = p.get("id", "")
    if len(texto) > LIMITE_PIE_FOTO:
        return None
    nombre = ("hoy-no.jpg" if "rojo" in pid else "escalera.jpg" if pid.endswith("-escalera")
              else "pick-del-dia.jpg" if pid.endswith("-pick-seguro") else None)
    if not nombre or (p.get("verde_de") and "rojo" not in pid):
        return None
    f = RAIZ / "publicaciones" / "media" / "marca" / nombre
    return str(f.relative_to(RAIZ)) if f.exists() else None


def animacion_verde(token, canal, p, texto):
    """Tras un verde de buena cuota (3,00 o más), el «¡VERDE! PARA DENTRO» animado (imagen de la marca)."""
    c = cuota_de_verde(p, texto)
    if not c or c < CUOTA_ANIMACION or not ANIMACION_VERDE.exists():
        return False
    try:
        api(token, "sendAnimation", {"chat_id": canal}, archivo=ANIMACION_VERDE, campo="animation", tipo="video/mp4")
        p["animacion"] = True
        return True
    except Exception as e:
        print(f"Animación del verde {p['id']}: {e}")
        return False


def preparar_texto(texto):
    # 27/10: sin el aviso de +18 (lo pidió Marcos)
    texto = texto.replace("jugarbien.es", "")
    texto = re.sub(r"\n*🔞 \+18 \| Jueg[ao] (?:con )?responsab\w*", "", texto).rstrip()
    from nombres import espanol   # 15/11: países en español y sin «el» delante
    return espanol(texto)


def comprobar(token, canal, ahora):
    """Guarda en publicaciones/estado.json si el bot funciona y es admin del canal."""
    estado = {"comprobado": ahora.strftime("%Y-%m-%d %H:%M")}
    try:
        yo = api(token, "getMe", {})["result"]
        estado["bot"] = "@" + yo["username"]
        miembro = api(token, "getChatMember", {"chat_id": canal, "user_id": yo["id"]})["result"]
        estado["rol"] = miembro.get("status")
        estado["puede_publicar"] = bool(miembro.get("can_post_messages"))
    except Exception as e:
        estado["error"] = str(e)
    ruta = RAIZ / "publicaciones" / "estado.json"
    anterior = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    if {k: v for k, v in anterior.items() if k != "comprobado"} != {k: v for k, v in estado.items() if k != "comprobado"}:
        ruta.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Estado:", estado)


ES_RESULTADO = re.compile(r"verde|rojo|balance|resumen|resultado|directo|noche|pleno")
DESDE_BUENOS, HASTA_BUENOS = (1, 0), (10, 20)   # de 01:00 a 10:20: lo nuevo espera al «buenos días»


def espera_buenos_dias(p, ahora):
    """16/11 (Marcos: «antes de nada tienes que subir el buenos días y luego el contenido»; a las 03:11 salió una copia
    de tipster): de madrugada y por la mañana no sale nada nuevo hasta que se haya publicado el buenos días de hoy.
    Los resultados (verdes de la noche) sí. Lo que espera sale después del buenos días (no caduca)."""
    if ES_RESULTADO.search(p["id"]) or p.get("verde_de") or p.get("resultado"):
        return False
    ini = ahora.replace(hour=DESDE_BUENOS[0], minute=DESDE_BUENOS[1], second=0, microsecond=0)
    fin = ahora.replace(hour=HASTA_BUENOS[0], minute=HASTA_BUENOS[1], second=0, microsecond=0)
    if not ini <= ahora <= fin:
        return False
    try:
        est = json.loads((RAIZ / "datos" / "marca_tg.json").read_text(encoding="utf-8"))
    except Exception:
        est = {}
    return est.get("buenos_dias") != ahora.strftime("%Y-%m-%d")


def sin_porque(texto):
    return not re.search(r"👨‍💻|Por qué|^\s*•", texto or "", re.M)   # «🧠 Pensada con calma» es una etiqueta, no un porqué


def con_porque(p, texto):
    """16/11 (Marcos: «en Telegram tiene que haber explicación… por qué coges cada pick o cosas de ese partido»): si un
    pick va sin porqué, se le añaden 1-3 razones (razones.py: forma, tabla, rachas) y qué se juega cada uno."""
    if ES_RESULTADO.search(p["id"]) or not p.get("sel") or not sin_porque(texto):
        return texto
    frases = []
    try:
        import picks as P
        import que_se_juegan
        import razones
        from bot import EXTRA
        from nombres import espanol
        hist = P.historial()
        for s_ in p["sel"][:3]:
            fid, mercado, opcion = (str(s_).split("|") + ["", ""])[:3]
            ex = json.loads((EXTRA / f"{fid}.json").read_text(encoding="utf-8")) if (EXTRA / f"{fid}.json").exists() else {}
            pa = ex.get("partido") or {}
            if not pa:
                continue
            loc, vis = pa["teams"]["home"]["name"], pa["teams"]["away"]["name"]
            pk = {"partido_id": int(fid), "liga_id": pa["league"]["id"], "local": loc, "visitante": vis,
                  "mercado": mercado, "opcion": opcion, "texto": P.texto_pick(mercado, opcion, loc, vis)}
            for f in razones.razones(pk, hist, ex, maximo=2):
                frases.append(espanol(f))
            c = que_se_juegan.contexto(pa["league"]["id"], int(fid))
            if c:
                for lado in ("local", "visitante"):
                    if c[lado]["estado"] == "nada":
                        frases.append(espanol(f"{c[lado]['equipo']}: {c[lado]['texto']}, no se juega nada."))
                    elif c[lado]["estado"] == "se_juega":
                        g = next((x for x in c[lado]["texto"].split(" · ") if x.startswith("gana:")), "")
                        g = g.replace("gana:", "si gana, acaba").strip() if g else c[lado]["texto"]
                        frases.append(espanol(f"{c[lado]['equipo']} se lo juega: {g}."))
    except Exception as e:
        print("porqué:", str(e)[:150])
    frases = list(dict.fromkeys(f for f in frases if f))[:3]
    if not frases:
        return texto
    return texto.rstrip() + "\n\n🧠 Por qué:\n" + "\n".join(f"👨‍💻 {f}" for f in frases)


def main(objetivo=None):
    token = os.environ.get("TELEGRAM_TOKEN")
    canal = os.environ.get("TELEGRAM_CANAL")
    if not token or not canal:
        sys.exit("Faltan TELEGRAM_TOKEN o TELEGRAM_CANAL")
    ahora = datetime.now(MADRID)
    comprobar(token, canal, ahora)
    cola = json.loads(COLA.read_text(encoding="utf-8")) if COLA.exists() else []
    auto = [p for ruta in AUTOS if ruta.exists() for p in json.loads(ruta.read_text(encoding="utf-8"))]
    enviados = json.loads(ENVIADOS.read_text(encoding="utf-8")) if ENVIADOS.exists() else {}
    for p in auto:  # el estado de los automáticos vive en enviados.json
        p.update(enviados.get(p["id"], {}))
        p["_auto"] = True
    control = json.loads(CONTROL.read_text(encoding="utf-8")) if CONTROL.exists() else {}
    if control.get("pausa"):
        print("En pausa (desde el asistente): no se publica nada")
        return
    def guardar_estado():
        COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for p in auto:
            estado = {k: p[k] for k in ("enviado", "mensaje_id", "caducada", "error", "foto_tg") if k in p}
            if estado:
                enviados[p["id"]] = estado
        ENVIADOS.write_text(json.dumps(enviados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cambios = 0
    # correcciones de posts ya publicados: "editar_texto" en cola.json → se edita el mensaje del canal
    for p in cola:   # posts ya publicados que hay que quitar del canal: "borrar": true
        if not objetivo and p.get("borrar") and p.get("mensaje_id") and not p.get("borrado"):
            try:
                api(token, "deleteMessage", {"chat_id": canal, "message_id": p["mensaje_id"]})
                p["borrado"] = ahora.strftime("%Y-%m-%dT%H:%M")
                print(f"Borrado del canal: {p['id']}")
            except Exception as e:
                p["error_borrado"] = str(e)
            cambios += 1
    for p in cola:
        nuevo = p.get("editar_texto")
        if objetivo or not nuevo or not p.get("mensaje_id"):
            continue
        metodo, campo = ("editMessageCaption", "caption") if p.get("foto") or p.get("foto_tg") else ("editMessageText", "text")
        try:
            api(token, metodo, {"chat_id": canal, "message_id": p["mensaje_id"], campo: preparar_texto(nuevo)})
            p["texto"], p["editado"] = nuevo, ahora.strftime("%Y-%m-%dT%H:%M")
            p.pop("editar_texto")
            print(f"Editado en el canal: {p['id']}")
        except Exception as e:
            p["error_edicion"] = str(e)
            print(f"ERROR al editar {p['id']}: {e}")
        cambios += 1
    ids_cola = {p['id'] for p in cola}
    for p in sorted(cola + [p for p in auto if p['id'] not in ids_cola], key=lambda x: x["fecha"]):
        if objetivo and (p['id'], 'telegram') != objetivo:
            continue
        if p.get("enviado") or p.get("mensaje_id") or p.get("caducada") or p.get("solo_redes") or p.get("borrar"):
            continue
        if p.get("solo_en") and "telegram" not in p["solo_en"]:   # 12/11: la combi de solo Threads salió en Telegram
            continue
        if ambiguo(p.get("error")):
            continue
        if p["id"] in control.get("cancelados", []):
            p["caducada"] = "cancelado"
            cambios += 1
            continue
        cuando = datetime.fromisoformat(p["fecha"]).replace(tzinfo=MADRID)
        if p.get("requiere_ok"):   # 09/11 (Marcos): los verdes solo salen cuando él le da a «✅ Publicar»
            ok = (control.get("aprobados") or {}).get(p["id"])
            if not ok:
                continue
            cuando = datetime.fromisoformat(ok).replace(tzinfo=MADRID)
        if cuando > ahora:
            continue
        if espera_buenos_dias(p, ahora):
            continue
        if cuando.hour < HASTA_BUENOS[0] and cuando.date() == ahora.date() and cuando.hour >= DESDE_BUENOS[0]:
            try:   # esperó al buenos días: cuenta desde que salió
                bd = json.loads((RAIZ / "datos" / "marca_tg.json").read_text(encoding="utf-8")).get("buenos_dias_hora")
                cuando = max(cuando, datetime.fromisoformat(bd).replace(tzinfo=MADRID)) if bd else cuando
            except Exception:
                pass
        if ahora - cuando > MAX_RETRASO:
            p["caducada"] = True
            cambios += 1
            print(f"Caducada (no se publica): {p['id']}")
            continue
        from bot import partido_caido
        from bot import cuota_baja
        from bot import mercado_prohibido
        from comprobar_post import bloquea   # 12/11: TODAS las reglas en un sitio (comprobar_post.py)
        motivo = partido_caido(p) or cuota_baja(p, control.get("textos", {}).get(p["id"])) or mercado_prohibido(p) \
            or bloquea(p, control.get("textos", {}).get(p["id"]))
        if motivo:   # 07/11: combi con un partido aplazado o ya jugado: no se publica (12/11: ni con cuota < 1,35)
            p["caducada"] = motivo
            cambios += 1
            print(f"No se publica {p['id']}: {motivo}")
            continue
        if p.get("tarjeta") and not (RAIZ / "publicaciones" / "media" / f"{p['id']}.tarjeta.jpg").exists():
            print(f"Esperando la foto del partido: {p['id']}")   # 28/10 (Marcos): combi de partido SIEMPRE con foto
            continue
        texto = preparar_texto(con_porque(p, control.get("textos", {}).get(p["id"], p["texto"])))
        foto = p.get("foto") or foto_de_marca(p, texto)
        # 27/10 (Marcos): las combis de un partido también van con su foto (escudos y hora) en Telegram
        tarjeta = RAIZ / "publicaciones" / "media" / f"{p['id']}.tarjeta.jpg"
        if not foto and p.get("tarjeta") and tarjeta.exists() and len(texto) <= LIMITE_PIE_FOTO:
            foto = str(tarjeta.relative_to(RAIZ))
            p["foto_tg"] = foto
        if not foto and not p.get("sin_tarjeta"):   # 15/11 sin_tarjeta = solo texto con el porqué entero. 13/11 (Marcos: «más fotos, no tanto texto»): tarjeta con banderas/escudos y texto corto
            import tarjeta_tg
            t = tarjeta_tg.hacer(p, texto, cola + auto)
            corto = texto if p.get("origen") == "tipster" else tarjeta_tg.texto_corto(texto)   # 15/11 (Marcos): las copias llevan el porqué
            if t and len(corto) <= LIMITE_PIE_FOTO:
                foto, texto = t, corto
                p["foto_tg"] = foto
        # 16/11 (Marcos: «arregla»): una copia sin «sel» no se sigue sola (verde/rojo ni resumen): aviso para ponérsela
        if p.get("origen") == "tipster" and not p.get("sel") and not p.get("aviso_sin_sel"):
            p["aviso_sin_sel"] = True
            try:
                import alineaciones_posts
                alineaciones_posts.dm(f"🔎 {p['id']} sale sin mercado reconocido: no contará en verdes ni en el resumen hasta que Claude le ponga la «sel».")
            except Exception as e:
                print(f"Aviso sin sel: {e}")
        # 16/11 (Marcos: «programalo todo bien»): un pick o una copia NUNCA sale sin su foto de banderas/escudos
        if not foto and not p.get("sin_tarjeta") and ("-pick-" in p.get("id", "") or p.get("origen") == "tipster"):
            print(f"Sin foto, no sale: {p['id']}")
            if not p.get("aviso_sin_foto"):
                p["aviso_sin_foto"] = True
                try:
                    import alineaciones_posts
                    alineaciones_posts.dm(f"⏸️ {p['id']} no sale: no se pudo hacer su foto con banderas/escudos. Lo mira Claude.")
                except Exception as e:
                    print(f"Aviso sin foto: {e}")
            continue
        try:
            if foto:
                if len(texto) > LIMITE_PIE_FOTO:
                    raise RuntimeError(f"pie de foto de {len(texto)} caracteres (máx {LIMITE_PIE_FOTO})")
                r = api(token, "sendPhoto", {"chat_id": canal, "caption": texto}, archivo=RAIZ / foto)
            else:
                if len(texto) > LIMITE_TEXTO:
                    raise RuntimeError(f"texto de {len(texto)} caracteres (máx {LIMITE_TEXTO})")
                r = api(token, "sendMessage", {"chat_id": canal, "text": texto,
                                                "link_preview_options": {"is_disabled": True}})
        except Exception as e:
            p["error"] = str(e)
            cambios += 1
            print(f"ERROR en {p['id']}: {e}")
            guardar_estado()
            continue
        p["enviado"] = ahora.strftime("%Y-%m-%dT%H:%M")
        p["mensaje_id"] = r["result"]["message_id"]
        p.pop("error", None)
        animacion_verde(token, canal, p, texto)
        cambios += 1
        print(f"Publicada: {p['id']}")
        guardar_estado()
        time.sleep(2)
    if cambios:
        guardar_estado()
    print(f"Hecho. Cambios: {cambios}")


if __name__ == "__main__":
    main()
