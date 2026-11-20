"""
20/11 (Marcos: «mira en X a ver qué contenido le funciona a la gente para copiarlo» → «monta todo»).
Formatos que mejor van en las cuentas de apuestas en español de X (Bilbets, BambaBets, La Banda del Cash…),
aplicados a lo que x_buffer.py sube a @combilocass. Todo apagado hasta que Marcos dé el OK: control.json
"x_extra": true.

  1. «Para mañana»: las combis de la noche (las «-loca-th-noche-», que son de partidos del día siguiente) salen con
     la cabecera «🗓️ PARA MAÑANA · VIERNES 20/11» y un 2.º post: «La más clara de todas, en el Telegram ⤵️» + enlace.
  2. La escalera presumida: su verde sale como la escalera entera («✅ Día 1 · 1,73 / ✅ Día 2 · 1,80 / …»).
  3. El enlace de Telegram nunca en el post principal (X lo esconde): va en el 2.º post del hilo.
  5. Directo: un post por día con la escalera en juego (min. 60–80): marcador y cómo va.
  (4. «Likes a cambio de pick»: aún no, con 1 seguidor no tiene sentido.)
"""
import re
from datetime import datetime, timedelta

TELEGRAM = "https://t.me/+NMCCvWtZu842Mjhk"
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]


def activo(control):
    return bool(control.get("x_extra"))


def coma(x):
    return f"{x:.2f}".replace(".", ",")


# ---------- 2. escalera
def tramo(esc, dia):
    """Los escalones seguidos que acaban en el del `dia` (de la cadena «anterior» de datos/escalera.json)."""
    pasos, x = [], esc.get("actual")
    while x:
        pasos.append(x)
        if x.get("escalon") == 1:
            break
        x = x.get("anterior")
    pasos = [p for p in pasos if p.get("dia", "") <= dia][::-1]
    while pasos and pasos[0].get("escalon") != 1:
        pasos.pop(0)
    return pasos


def escalera_x(esc, dia):
    pasos = tramo(esc, dia)
    if not pasos:
        return None
    lineas = [f"✅ Día {p['escalon']} · {coma(p['cuota'])}" for p in pasos]
    ini, fin = pasos[0]["stake"], pasos[-1]["stake"] * pasos[-1]["cuota"]
    n = len(pasos)
    return (f"🪜 RETO ESCALERA · DÍA {n}/7 SUPERADO ✅\n\n" + "\n".join(lineas) +
            f"\n\n💶 {coma(ini)}€ → {coma(fin)}€\n\n🔥 Mañana, a por el día {n + 1}" if n < 7 else
            f"🪜 RETO ESCALERA COMPLETADO 🏆\n\n" + "\n".join(lineas) + f"\n\n💶 {coma(ini)}€ → {coma(fin)}€")


# ---------- 1 y 3. para mañana + enlace en el 2.º post
def para_manana(pid, textos, ahora):
    if "-loca-th-noche-" not in pid:
        return textos
    m = re.match(r"(\d{4}-\d{2}-\d{2})", pid)
    dia = datetime.fromisoformat(m.group(1)) if m else ahora + timedelta(days=1)
    cab = f"🗓️ PARA MAÑANA · {DIAS[dia.weekday()]} {dia:%d/%m}"
    return [cab + "\n" + textos[0]] + textos[1:]


def con_enlace(pid, textos):
    """El enlace del canal, en el 2.º post (o al final del 2.º si ya es hilo). Los verdes van sin él."""
    if "-verde-" in pid:
        return textos
    gancho = ("La más clara de todas, en el Telegram (gratis) ⤵️" if "-loca-th-noche-" in pid
              else "📲 Todos los picks y verdes, gratis en Telegram ⤵️")
    if len(textos) == 1:
        return textos + [f"{gancho}\n{TELEGRAM}"]
    return textos[:-1] + [textos[-1] + f"\n\n{gancho}\n{TELEGRAM}"]


def transformar(p, textos, ahora, esc=None):
    """Lo que x_buffer sube, con los formatos nuevos."""
    if re.search(r"-verde-auto-(\d{4}-\d{2}-\d{2})-escalera$", p["id"]) and esc:
        dia = re.search(r"-verde-auto-(\d{4}-\d{2}-\d{2})-escalera$", p["id"]).group(1)
        t = escalera_x(esc, dia)
        if t:
            return [t]
    return con_enlace(p["id"], para_manana(p["id"], textos, ahora))


# ---------- 5. directo de la escalera
def directo(vivo, hoy, hechos):
    """Un post al día con la escalera en juego entre el 60' y el 80' (de docs/datos.json → publicados_hoy)."""
    if hoy in hechos:
        return None
    x = next((v for v in vivo or [] if v.get("id") == f"{hoy}-escalera"), None)
    if not x or x.get("estado") in ("verde", "rojo"):
        return None
    for pk in x.get("picks") or []:
        mi, mc = pk.get("minuto"), pk.get("marcador")
        if not (isinstance(mi, int) and 60 <= mi <= 80 and isinstance(mc, list)) or pk.get("estado") not in ("va_bien", "va_mal"):
            continue
        partido = pk.get("partido") or ""
        cab = f"⏱️ Minuto {mi}' · {partido} {mc[0]}-{mc[1]}"
        if pk["estado"] == "va_bien":
            return f"{cab}\n\n🪜 La escalera va camino del verde 😎🍀\n🍀 {pk.get('texto')}\n\n¡Aguanta! 🔥"
        return f"{cab}\n\n😰 A la escalera le falta un empujón…\n🍀 {pk.get('texto')}\n\n¡Vamos! 🙏🔥"
    return None
