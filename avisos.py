"""
Avisos al móvil por Telegram (privado, solo al dueño del canal):
  - combi en verde (todo lo publicado) y escalera en verde
  - fallos del bot al publicar en Telegram o Threads
Lo ya avisado se guarda en datos/avisos.json. Se ejecuta en el bucle cada ~10 min.
"""
import json
import os
import re
from datetime import datetime, timedelta

from bot import DATOS, MADRID, RAIZ, leer
from publicar_telegram import api

ESTADO = DATOS / "avisos.json"
NOMBRE = {"segura": "COMBI SEGURA", "cuota_3": "COMBI CUOTA 3", "loca": "COMBI LOCA"}


def main():
    token, canal = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CANAL")
    if not (token and canal):
        return
    ahora = datetime.now(MADRID)
    hecho = set(leer(ESTADO, []) or [])
    avisos = []
    reg = leer(DATOS / "registro_aciertos.json", {}) or {}
    clave = lambda p: f"{p['partido_id']}|{p['mercado']}|{p['opcion']}"
    desde = (ahora - timedelta(days=2)).strftime("%Y-%m-%d")
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}

    # 27/10: aciertos de todo lo publicado (combis de partido, x3, loca, escalera…), en cuanto la app los da por verdes
    app = leer(RAIZ / "docs" / "datos.json", {}) or {}
    import re
    for p in app.get("publicados_hoy", []):
        if p.get("estado") != "verde" or "verde-auto" in p["id"] or not re.search(r"-combi-|escalera|-boleto-", p["id"]):
            continue
        k = f"verde-{p['id']}"
        if k in hecho:
            continue
        cuota = f" x{p['cuota']:.2f}".replace(".", ",") if p.get("cuota") else ""
        avisos.append((k, f"✅💚 ¡VERDE{cuota}! {p['titulo']}\n\n" + "\n".join(f"✅ {x['texto']}" for x in p.get("picks", []))
                       + "\n\nEl post de verde sale ahora en el canal y en redes."))
    esc = leer(DATOS / "escalera.json", {}) or {}
    for h in (esc.get("historial") or [])[-3:]:
        k = f"escalera-{h['dia']}"
        if h.get("resultado") == "verde" and k not in hecho and h["dia"] >= desde:
            avisos.append((k, f"🪜 Escalera día {h['escalon']}: ✅ VERDE, mañana se sube de escalón 🚀"))
    enviados = leer(RAIZ / "publicaciones" / "enviados.json", {}) or {}

    est_redes = leer(RAIZ / "publicaciones" / "enviados_redes.json", {}) or {}
    for p in (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + [
            dict(x, **enviados.get(x["id"], {}), **est_redes.get(x["id"], {})) for x in leer(RAIZ / "publicaciones" / "auto.json", []) or []]:
        if p["fecha"][:10] < desde:
            continue
        # 27/10: nada de falsas alarmas: un post quitado o cancelado a propósito, o que aún no le toca, no es un fallo
        # (esa mañana saltó «no salió a su hora» con dos combis que se habían quitado a mano)
        if (p["id"] in (control.get("cancelados") or []) or p.get("caducada") in ("quitada", "cancelado")
                or "quitada" in str(p.get("nota", "")) or p["fecha"] > ahora.strftime("%Y-%m-%dT%H:%M")):
            continue
        fallos = dict(p.get("errores_redes") or {})
        if p.get("error"):
            fallos["telegram"] = p["error"]
        if p.get("caducada") is True:
            fallos["telegram"] = "no salió a su hora"
        for red, e in fallos.items():
            if red not in ("telegram", "threads"):   # 27/10: solo Telegram y Threads
                continue
            k = f"fallo-{p['id']}-{red}"
            if k not in hecho:
                lineas = p["texto"].splitlines()
                avisos.append((k, f"⚠️ Fallo publicando en {red} (post de las {p['fecha'][11:16]}):\n{lineas[0][:60]}\n"
                                  + (f"{lineas[1][:60]}\n" if len(lineas) > 1 and lineas[1].strip() else "")
                                  + f"{str(e)[:200]}"))

    # 27/10 (Marcos): a las 10:00, las 2 combis «Crear apuesta» del día para que las monte en bet365
    k = f"boletos-{ahora:%Y-%m-%d}"
    if ahora.hour >= 10 and k not in hecho:
        try:
            import combis_dia
            bs = combis_dia.boletos(f"{ahora:%Y-%m-%d}", desde=f"{ahora:%Y-%m-%d}T12:00")
            (DATOS / "boletos.json").write_text(json.dumps({"dia": f"{ahora:%Y-%m-%d}", "boletos": bs},
                                                           ensure_ascii=False, default=str), encoding="utf-8")
            for i, b in enumerate(bs, 1):
                avisos.append((f"{k}-{i}", combis_dia.texto_boleto(b, i)
                               + "\n\n📲 Móntala en bet365 y mándame la captura aquí: recorto el dinero y te pregunto antes de subirla."))
            if not bs:
                avisos.append((k, "🎟️ Hoy no hay partidos suficientes para la combi «Crear apuesta»."))
            hecho.add(k)
        except Exception as e:
            print("boletos:", e)
    # 27/10: revisión de cuotas antes de publicar. Si la cuota que pone el texto no cuadra con la real de bet365
    # (patas del mismo partido en «Crear apuesta»), aviso con tiempo para corregirla.
    try:
        import combis_dia
        limite = (ahora + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")
        for p in (leer(RAIZ / "publicaciones" / "cola.json", []) or []) + (leer(RAIZ / "publicaciones" / "auto.json", []) or []):
            if p.get("enviado") or p.get("caducada") or not (ahora.strftime("%Y-%m-%dT%H:%M") < p["fecha"] <= limite):
                continue
            real = p.get("cuota_bet365") or combis_dia.cuota_real_sel(p.get("sel"), p.get("cuotas") or [])
            m = re.search(r"(?:Cuota total aprox\.:|CUOTA|x)\s*(\d+,\d+)", p["texto"])
            if not real or not m:
                continue
            pone = float(m.group(1).replace(",", "."))
            k = f"cuota-{p['id']}-{pone}"
            if abs(pone - real) / real > 0.10 and k not in hecho:
                avisos.append((k, f"⚠️ Cuota que no cuadra ({p['fecha'][11:16]}):\n{p['texto'].splitlines()[0][:60]}\n"
                                  f"{p['texto'].splitlines()[1][:60] if len(p['texto'].splitlines()) > 1 else ''}\n"
                                  f"Pone {pone:.2f} y en bet365 saldría ~{real:.2f}. Díselo a Claude o cancélala."))
    except Exception as e:
        print("revisión de cuotas:", e)
    # avisos sueltos que dejo yo a mano (p. ej. una prueba): datos/avisos_manuales.json = [{"k", "texto"}]
    for x in leer(DATOS / "avisos_manuales.json", []) or []:
        if x["k"] not in hecho:
            avisos.append((x["k"], x["texto"]))
    try:   # 28/10: lo que sale en Threads, listo para publicarlo en X con un toque
        import para_x
        para_x.main(token, canal, api, ahora)
    except Exception as e:
        print("para X:", str(e)[:150])
    if not ESTADO.exists():   # primera vez: no se avisa de lo viejo
        hecho |= {k for k, _ in avisos}
        avisos = []
    if not avisos:
        ESTADO.write_text(json.dumps(sorted(hecho)[-1000:]), encoding="utf-8")
        return
    admins = api(token, "getChatAdministrators", {"chat_id": canal})["result"]
    duenio = next(a["user"]["id"] for a in admins if a["status"] == "creator")
    for k, texto in avisos[:8]:
        try:
            api(token, "sendMessage", {"chat_id": duenio, "text": texto})
            hecho.add(k)
        except Exception as e:
            print("aviso no enviado:", e)
    ESTADO.write_text(json.dumps(sorted(hecho)[-1000:]), encoding="utf-8")
    print(f"Avisos enviados: {len(avisos[:8])}")


if __name__ == "__main__":
    main()
