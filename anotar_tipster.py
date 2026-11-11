"""11/11 (Marcos: «guarda todo lo de los tipsters y que el bot aprenda de lo que cogen; cada vez que sale una
apuesta, que la analice y vea por qué»).

Lo usa Claude (rol OJEADOR) al leer datos/tipsters_raw.json y las fotos de boletos:

  python anotar_tipster.py '{"tipster": "CRIMINALPICKS", "fuente": "canal/123", "dia": "2026-11-11",
      "local": "Betis", "visitante": "Sevilla", "texto": "Betis o empate", "mercado": "Double Chance",
      "opcion": "Home/Draw", "cuota": 1.45, "stake": 3, "combinada": false,
      "argumento": ["hechos que da el tipster"], "por_que": ["lo que ve Claude: datos que lo apoyan o no"]}'

- Una línea por pata (si es una combinada, cada pata con "combinada": "<id de la combi>").
- No se repite: si ya está esa fuente con ese mercado/opción, no se apunta otra vez.
- Después, python tipsters.py: casa con nuestro partido, lo corrige al acabar y aprende (tipsters_aprendizaje.json).
"""
import json
import sys

from bot import DATOS, leer

FICHERO = DATOS / "tipsters.json"
OBLIGATORIOS = ("tipster", "dia", "local", "visitante", "texto")


def anotar(pk):
    falta = [k for k in OBLIGATORIOS if not pk.get(k)]
    if falta:
        raise ValueError(f"faltan: {', '.join(falta)}")
    lista = leer(FICHERO, []) or []
    clave = lambda x: (x.get("fuente") or f"{x['tipster']}|{x['dia']}|{x['local']}", x.get("mercado"), str(x.get("opcion")))
    if any(clave(x) == clave(pk) for x in lista):
        return False
    for k in ("argumento", "por_que"):
        if isinstance(pk.get(k), str):
            pk[k] = [pk[k]]
    lista.append(pk)
    FICHERO.write_text(json.dumps(lista, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        datos = json.loads(arg)
        for pk in datos if isinstance(datos, list) else [datos]:
            print("apuntado" if anotar(pk) else "ya estaba", "·", pk.get("tipster"), "·", pk.get("texto"))
