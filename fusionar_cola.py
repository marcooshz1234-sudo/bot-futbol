"""
Fusión de publicaciones/cola.json cuando dos cambios llegan a la vez (driver de merge de git).
Une las dos versiones por id: no se pierde ningún post añadido a mano y, si un post está en las dos,
se queda con el estado más avanzado (enviado, ids de redes, errores...). Uso: python fusionar_cola.py %O %A %B
"""
import json
import sys


def leer(r):
    try:
        return json.load(open(r, encoding="utf-8"))
    except Exception:
        return []


def main(base, a, b):
    va, vb, vo = leer(a), leer(b), leer(base)
    quitados = {p["id"] for p in vo} - {p["id"] for p in va} | ({p["id"] for p in vo} - {p["id"] for p in vb})
    final = {}
    for lista in (va, vb):
        for p in lista:
            if p["id"] in quitados:
                continue   # quitado a propósito en una de las dos versiones
            if p["id"] not in final:
                final[p["id"]] = dict(p)
                continue
            x = final[p["id"]]
            for k, v in p.items():
                if k in ("redes", "errores_redes") and isinstance(v, dict):
                    x[k] = {**(x.get(k) or {}), **v}
                elif v not in (None, "", {}, []) and x.get(k) in (None, "", {}, []):
                    x[k] = v
                elif k in ("texto", "editar_texto", "fecha", "borrar", "caducada") and v != x.get(k):
                    x[k] = v   # la versión que llega (cambio más reciente) manda en el contenido
    salida = sorted(final.values(), key=lambda p: p.get("fecha", ""))
    json.dump(salida, open(a, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(a, "a", encoding="utf-8").write("\n")


if __name__ == "__main__":
    main(*sys.argv[1:4])
