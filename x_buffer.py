"""
19/11 (Marcos: «busca alguna forma de poder automatizarlo gratis y que no tengas que hacerlo tú» → «prepárame lo del
Buffer»). Publica en X (@combilocass) lo mismo que sale en Threads, a través de Buffer (plan gratis: X incluido y
API con clave personal). Sin la clave (secreto BUFFER_TOKEN en GitHub) no hace nada.

Reglas (REGLAS.md, X):
  · lo mismo que Threads, cortado a 280 (emojis cuentan 2): sin la línea ⭐, sin «aprox.», sin la frase final,
    sin «(fem.)»… y si aún no cabe, hilo de 2.
  · SIN «@» delante de las cuotas (en X «@1,80» es una mención).
  · cuenta nueva: de momento solo «lo fuerte» (pick, escalera, verdes, ganadores, combis gordas) y máx. 5 al día.
    Se cambia en control.json: "x_modo": "todo" | "fuerte", "x_max_dia": N, "x_pausa": true.

API de Buffer (GraphQL, https://api.buffer.com, «Authorization: Bearer <clave>»): createPost con channelId, text,
schedulingType: automatic, mode: customScheduled + dueAt (ahora + 1 min) para que salga ya; foto por URL pública
(assets: [{image: {url}}]); hilo con metadata.twitter.thread.
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API = "https://api.buffer.com"
ESTADO_F = "x_buffer.json"
VENTANA_H = 3          # solo lo publicado en Threads en las últimas 3 h (nada viejo al arrancar)
MAX_DIA = 5
FUERTE = re.compile(r"-(escalera|pick-seguro(-\d+)?|ganadores[-\w]*|verde-[-\w]+)$|-x(50|100|500)$")


# ---------- texto para X
def peso(t):
    """Lo que cuenta X: emojis y CJK 2, enlaces 23, selectores de variante y uniones 0."""
    t = re.sub(r"https?://\S+", "x" * 23, t)
    n = 0
    for ch in t:
        o = ord(ch)
        if 0xFE00 <= o <= 0xFE0F or o == 0x200D or 0xE0020 <= o <= 0xE007F:
            continue
        n += 1 if o < 0x1100 or (0x2000 <= o < 0x2300 and o not in (0x231A, 0x231B)) else 2
    return n


def sin_arrobas(t):
    return re.sub(r"@(?=\s?\d)", "", t)   # «@1,80» → «1,80» (en X es una mención)


def a_x(texto, limite=280):
    """El texto de Threads → uno o dos posts de X (hilo) que caben en el límite."""
    L = sin_arrobas(texto).strip().split("\n")

    def cabe():
        return peso("\n".join(L).strip()) <= limite

    if not cabe() and len(L) > 2 and L[2].startswith("⭐"):   # «⭐ A vs B» repite la cabecera
        L = L[:2] + L[4:] if len(L) > 3 and not L[3].strip() else L[:2] + L[3:]
    if not cabe():
        L = [x.replace(" aprox.", "") for x in L]
    if not cabe():   # la frase final de ánimo
        while L and not L[-1].strip():
            L.pop()
        if L and not re.match(r"(✅|🎯 C(UOTA|uota)|📈|💶|💎)", L[-1]):
            L.pop()
    if not cabe():
        L = [re.sub(r" \((fem|FEM)\.\)", "", x) for x in L]
    if not cabe() and "–" in L[0]:   # combi de un partido: el partido ya va en la cabecera
        L = [re.sub(r" del [^\n]+–[^\n]+$", "", x) if i else x for i, x in enumerate(L)]
    if not cabe():
        L = [x for i, x in enumerate(L) if x.strip() or i == 1]
    t = "\n".join(L).strip()
    if peso(t) <= limite:
        return [t]
    a, b = [], []
    for x in L:
        (a if not b and peso("\n".join(a + [x])) <= limite - 10 else b).append(x)
    return ["\n".join(a).strip(), "\n".join(b).strip()]


def texto_threads(p):
    from estilo_threads import estilo
    from redes import texto_final
    return estilo(texto_final(dict(p, texto=p.get("texto_threads") or p["texto"])), p["id"])


# ---------- qué se sube
def fuerte(pid):
    return bool(FUERTE.search(pid))


def candidatos(posts, estado, control, ahora):
    """Lo que ya salió en Threads (últimas VENTANA_H horas), aún no subido a X, según el modo y el tope del día."""
    if control.get("x_pausa"):
        return []
    hoy = ahora.strftime("%Y-%m-%d")
    hechos = estado.get("enviados") or {}
    subidos_hoy = sum(1 for v in hechos.values() if str(v.get("cuando", "")).startswith(hoy))
    tope = int(control.get("x_max_dia") or MAX_DIA)
    modo = control.get("x_modo") or "fuerte"
    desde = (ahora - timedelta(hours=VENTANA_H)).strftime("%Y-%m-%dT%H:%M")
    ya = ahora.strftime("%Y-%m-%dT%H:%M")
    out = []
    for p in sorted(posts, key=lambda x: x.get("fecha") or ""):
        if not (p.get("redes") or {}).get("threads") or p["id"] in hechos:
            continue
        if not (desde <= (p.get("fecha") or "") <= ya):
            continue
        if modo != "todo" and not fuerte(p["id"]):
            continue
        out.append(p)
    return out[:max(0, tope - subidos_hoy)]


# ---------- Buffer
class Enum(str):
    """Un valor de enum de GraphQL (va sin comillas)."""


def lit(v):
    if isinstance(v, Enum):
        return str(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return json.dumps(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(lit(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {lit(x)}" for k, x in v.items()) + "}"
    raise TypeError(type(v))


def entrada(canal, textos, foto, cuando):
    """El input de createPost: sale en `cuando` (UTC); foto en el primero; hilo si son dos."""
    imagen = [{"image": {"url": foto}}] if foto else None
    d = {"text": textos[0], "channelId": canal, "schedulingType": Enum("automatic"),
         "mode": Enum("customScheduled"), "dueAt": cuando.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")}
    if len(textos) > 1:
        hilo = [dict({"text": t}, **({"assets": imagen} if imagen and i == 0 else {})) for i, t in enumerate(textos)]
        d["metadata"] = {"twitter": {"thread": hilo}}
    elif imagen:
        d["assets"] = imagen
    return d


def mutacion(inp):
    return ("mutation { createPost(input: " + lit(inp) + ") { ... on PostActionSuccess { post { id dueAt } } "
            "... on MutationError { message } } }")


def pedir(token, query):
    r = Request(API, data=json.dumps({"query": query}).encode(), method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    try:
        with urlopen(r, timeout=30) as f:
            return json.loads(f.read().decode())
    except HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.code}: {e.read().decode()[:300]}"}]}


def canal_x(token, estado):
    if estado.get("canal"):
        return estado["canal"]
    orgs = ((pedir(token, "query { account { organizations { id name } } }").get("data") or {})
            .get("account") or {}).get("organizations") or []
    for o in orgs:
        q = 'query { channels(input: { organizationId: %s }) { id name service } }' % json.dumps(o["id"])
        for c in (pedir(token, q).get("data") or {}).get("channels") or []:
            if c.get("service") in ("twitter", "x"):
                estado["canal"] = c["id"]
                return c["id"]
    return None


def main(ahora=None):
    from bot import DATOS, MADRID, RAIZ, escribir, leer
    from incidencias import publicaciones
    token = os.environ.get("BUFFER_TOKEN")
    if not token:
        print("x_buffer: sin BUFFER_TOKEN (Marcos aún no ha puesto la clave de Buffer): no se sube nada")
        return 0
    ahora = ahora or datetime.now(MADRID)
    estado = leer(DATOS / ESTADO_F, {}) or {}
    control = leer(RAIZ / "publicaciones" / "control.json", {}) or {}
    if not estado.get("canal"):   # 19/11: se comprueba la conexión en cuanto hay clave (sin publicar nada)
        canal = canal_x(token, estado)
        estado["conexion"] = {"cuando": ahora.strftime("%Y-%m-%dT%H:%M"),
                              "ok": bool(canal), "nota": None if canal else "con clave, pero sin canal de X en Buffer"}
        escribir(DATOS / ESTADO_F, estado)
        print("x_buffer: conectado a Buffer, canal de X", canal if canal else "NO encontrado")
        if not canal:
            return 1
    lista = candidatos(publicaciones(RAIZ), estado, control, ahora)
    if not lista:
        return 0
    canal = estado["canal"]
    from redes import foto_threads
    for p in lista:
        textos = a_x(texto_threads(p))
        r = pedir(token, mutacion(entrada(canal, textos, foto_threads(p), ahora + timedelta(minutes=1))))
        res = (r.get("data") or {}).get("createPost") or {}
        if res.get("post"):
            estado.setdefault("enviados", {})[p["id"]] = {"cuando": ahora.strftime("%Y-%m-%dT%H:%M"),
                                                        "buffer": res["post"].get("id"), "hilo": len(textos) > 1}
            print("x_buffer: subido", p["id"])
        else:
            msg = res.get("message") or json.dumps(r.get("errors"), ensure_ascii=False)[:300]
            estado.setdefault("fallos", {})[p["id"]] = {"cuando": ahora.strftime("%Y-%m-%dT%H:%M"), "error": msg}
            print("x_buffer: FALLO", p["id"], msg)
            break   # p. ej. la cola de Buffer llena: se reintenta en la próxima vuelta
    escribir(DATOS / ESTADO_F, estado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
