#!/usr/bin/env python3
"""
Puente · une El Analista, El Bot Asesor y El Publicador.

Se ejecuta en el Mac (cada hora, con launchd) y hace:
1. Baja lo último del Analista (git pull de este repositorio).
2. Con datos/picks.json prepara los posts del día con tus plantillas.
3. El Bot Asesor (Ollama, qwen3.5:9b) añade a cada post una frase "📊" con el dato
   que lo respalda. Si se inventa algún número, la frase se descarta y se usa la
   del código.
4. Escribe los borradores en ~/Combilocas/Borradores/AAAA-MM-DD.md
5. Los que marques con [x] se meten en la cola del Publicador y se suben a GitHub.
   El Publicador los publica en Telegram a su hora.

Solo usa la librería estándar de Python. No necesita claves.
"""

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
CASA = Path.home() / "Combilocas"
BORRADORES = CASA / "Borradores"
ESTADO = CASA / "puente_estado.json"
REGISTRO = CASA / "puente.log"
COLA = REPO / "publicaciones" / "cola.json"
PICKS = REPO / "datos" / "picks.json"
MADRID = ZoneInfo("Europe/Madrid")
OLLAMA = "http://127.0.0.1:11434/api/chat"
MODELO = "qwen3.5:9b"
MARGEN_ANTES_PARTIDO = timedelta(minutes=60)   # un post sale como tarde 1 h antes de su primer partido
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def log(msg):
    linea = f"{datetime.now(MADRID):%Y-%m-%d %H:%M} {msg}"
    print(linea)
    CASA.mkdir(exist_ok=True)
    with REGISTRO.open("a", encoding="utf-8") as f:
        f.write(linea + "\n")


def git(*args):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout


# ------------------------------------------------------------------ plantillas

def num(c):
    return f"{c:.2f}".replace(".", ",")


def lista(picks):
    return "\n".join(f"✅{i}. {p['texto']}" for i, p in enumerate(picks, 1))


def dato_codigo(picks):
    """Frase de respaldo hecha por el código (siempre correcta)."""
    p = max(picks, key=lambda x: x["frecuencia"])
    return f"📊 {p['texto']} → {p['detalle']} en sus últimos partidos"


def posts_del_dia(dia, d):
    """Devuelve la lista de posts (sin la frase del Asesor) para un día de picks."""
    f = datetime.fromisoformat(dia).replace(tzinfo=MADRID)
    nombre_dia = DIAS[f.weekday()].upper()
    posts = []

    mejores = d.get("mejores_por_partido") or []
    if len(mejores) >= 4:
        sel = mejores[:9]
        posts.append({
            "tipo": "picks-manana", "hora": (f - timedelta(days=1)).replace(hour=23, minute=0),
            "picks": sel,
            "texto": f"🔥 {len(sel)} PICKS PARA MAÑANA ({nombre_dia}) 🔥\n\n{lista(sel)}\n\n¡Combina máximo 2 o 3! 🍀",
        })
    tarde = [p for p in mejores if p["fecha"][11:] >= "18:30"]
    if len(tarde) >= 4:
        sel = tarde[:9]
        posts.append({
            "tipo": "picks-hoy", "hora": f.replace(hour=17, minute=30), "picks": sel,
            "texto": f"🔥 {len(sel)} PICKS PARA HOY 🔥\n\n{lista(sel)}\n\n¡Combina máximo 2 o 3! 🍀",
        })
    combis = d.get("combis") or {}
    plantillas = {
        "segura": (12, 0, f"🔒 COMBI SEGURA DEL {nombre_dia} 🔒"),
        "cuota_3": (11, 0, None),
        "loca": (19, 0, f"🤪 COMBI LOCA DEL {nombre_dia} 🤪"),
    }
    for nombre, (h, m, titulo) in plantillas.items():
        c = combis.get(nombre)
        if not c:
            continue
        titulo = titulo or f"💥 COMBINADA CUOTA {int(c['cuota'])} DEL {nombre_dia} 💥"
        posts.append({
            "tipo": f"combi-{nombre}", "hora": f.replace(hour=h, minute=m), "picks": c["picks"],
            "texto": (f"{titulo}\n\n{lista(c['picks'])}\n\n🎯 Cuota total: {num(c['cuota'])}\n"
                      f"💶 10€ → {num(c['cuota'] * 10)}€\n\n🍀 ¿LA PINTAMOS DE VERDE? 👀💚"),
        })
    # nunca después del primer partido del post
    for p in posts:
        primero = min(datetime.fromisoformat(x["fecha"]).replace(tzinfo=MADRID) for x in p["picks"])
        p["hora"] = min(p["hora"], primero - MARGEN_ANTES_PARTIDO)
        p["id"] = f"{dia}-{p['tipo']}"
    return posts


# ------------------------------------------------------------------ Bot Asesor

INSTRUCCIONES = (
    "Eres el redactor de Combilocas, un canal de picks de fútbol en español de España. "
    "Te paso los picks de un post con su dato real. Escribe UNA sola frase corta (máximo 140 "
    "caracteres) que empiece por 📊 y explique por qué el pick principal tiene sentido. "
    "Usa SOLO los números y equipos que te doy; no inventes cuotas, porcentajes ni datos. "
    "No pongas nombres de personas reales que no aparezcan. Responde solo con la frase."
)


def frase_asesor(picks):
    datos = "\n".join(f"- {p['texto']} · cuota {p['cuota']} · se cumplió: {p['detalle']}" for p in picks[:5])
    cuerpo = json.dumps({
        "model": MODELO, "stream": False, "think": False,
        "options": {"temperature": 0.4, "num_predict": 120},
        "messages": [{"role": "system", "content": INSTRUCCIONES},
                     {"role": "user", "content": datos}],
    }).encode()
    try:
        with urlopen(Request(OLLAMA, data=cuerpo, headers={"Content-Type": "application/json"}), timeout=180) as r:
            texto = json.load(r)["message"]["content"].strip().splitlines()[0].strip()
    except Exception as e:
        log(f"Asesor no disponible ({e}); uso la frase del código")
        return None
    # control: todo número de la frase tiene que estar en los datos
    permitidos = set(re.findall(r"\d+(?:[.,]\d+)?", datos.replace(",", ".")))
    usados = set(n.replace(",", ".") for n in re.findall(r"\d+(?:[.,]\d+)?", texto))
    if not texto.startswith("📊") or len(texto) > 160 or not usados <= permitidos:
        log(f"Frase del Asesor descartada: {texto[:100]}")
        return None
    return texto


# ------------------------------------------------------------------ borradores

def leer_json(ruta, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return defecto


def huella(t):
    return hashlib.sha1(t.strip().encode()).hexdigest()[:12]


BLOQUE = re.compile(r"^### \[( |x|X)\] ([^\n]*?) · id:(\S+)[^\n]*\n(.*?)(?=^### \[|\Z)", re.M | re.S)


def leer_borrador(ruta):
    if not ruta.exists():
        return {}
    res = {}
    for marca, cab, pid, cuerpo in BLOQUE.findall(ruta.read_text(encoding="utf-8")):
        texto = cuerpo.strip().strip("`").strip()
        res[pid] = {"marcado": marca.lower() == "x", "texto": texto}
    return res


def escribir_borrador(ruta, dia, posts, enviados):
    f = datetime.fromisoformat(dia)
    lineas = [f"# Borradores · {DIAS[f.weekday()]} {f:%d/%m}", "",
              "Marca con **[x]** los que quieras publicar (puedes editar el texto). "
              "El puente los manda al Publicador en la próxima pasada (cada hora).", ""]
    for p in sorted(posts, key=lambda x: x["hora"]):
        estado = "x" if p["id"] in enviados else " "
        nota = "  ✅ ENVIADO A LA COLA" if p["id"] in enviados else ""
        lineas += [f"### [{estado}] {p['hora']:%d/%m %H:%M} · {p['tipo']} · id:{p['id']}{nota}",
                   "```", p["texto"], "```", ""]
    ruta.write_text("\n".join(lineas), encoding="utf-8")


def main():
    BORRADORES.mkdir(parents=True, exist_ok=True)
    estado = leer_json(ESTADO, {"generados": {}, "enviados": []})
    try:
        git("pull", "--rebase", "-q")
    except RuntimeError as e:
        log(f"No pude bajar lo último del Analista: {e}")
    picks = leer_json(PICKS, None)
    if not picks:
        log("Todavía no hay datos/picks.json")
        return
    ahora = datetime.now(MADRID)
    cola = leer_json(COLA, [])
    en_cola = {c["id"] for c in cola}
    nuevos_en_cola = 0

    for dia, d in picks["dias"].items():
        posts = [p for p in posts_del_dia(dia, d) if p["hora"] > ahora + timedelta(minutes=20)]
        ruta = BORRADORES / f"{dia}.md"
        actuales = leer_borrador(ruta)
        for p in posts:
            previo = actuales.get(p["id"])
            generado = estado["generados"].get(p["id"])
            # 1) si ya lo marcaste o editaste, se respeta tu texto
            base = huella(p["texto"])
            mismo_contenido = estado.setdefault("base", {}).get(p["id"]) == base
            if previo and (previo["marcado"] or huella(previo["texto"]) != generado or mismo_contenido):
                p["texto"] = previo["texto"]
            else:
                estado["base"][p["id"]] = base
                frase = frase_asesor(p["picks"]) or dato_codigo(p["picks"])
                base, _, cierre = p["texto"].rpartition("\n\n")
                p["texto"] = f"{base}\n\n{frase}\n\n{cierre}"
                estado["generados"][p["id"]] = huella(p["texto"])
            # 2) marcado → a la cola del Publicador
            if previo and previo["marcado"] and p["id"] not in en_cola:
                cola.append({"id": p["id"], "fecha": p["hora"].strftime("%Y-%m-%dT%H:%M"),
                             "texto": p["texto"], "foto": None})
                en_cola.add(p["id"])
                estado["enviados"].append(p["id"])
                nuevos_en_cola += 1
        if posts:
            escribir_borrador(ruta, dia, posts, set(estado["enviados"]))

    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    if nuevos_en_cola:
        COLA.write_text(json.dumps(sorted(cola, key=lambda c: c["fecha"]), ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        try:
            git("add", "publicaciones/cola.json")
            git("commit", "-q", "-m", f"Puente: {nuevos_en_cola} post(s) aprobados a la cola")
            git("pull", "--rebase", "-q")
            git("push", "-q")
            log(f"{nuevos_en_cola} post(s) enviados a la cola del Publicador")
        except RuntimeError as e:
            log(f"No pude subir la cola: {e}")
    else:
        log("Borradores al día, nada nuevo que enviar")


if __name__ == "__main__":
    main()
