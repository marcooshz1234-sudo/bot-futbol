"""
27/10: arregla JSON rotos por un choque de git (marcas <<<<<<< ======= >>>>>>>).

Pasó con publicaciones/estado_redes.json el 26/10: el bucle guardó el archivo con las marcas del choque y
desde entonces comprobar_redes.py fallaba al leerlo (no avisaba si una clave de Meta dejaba de funcionar).
Se ejecuta en el bucle justo después de cada git pull. Para cada .json con marcas:
  1) se queda con la parte local (la más nueva: lo que acaba de escribir el bucle),
  2) si así no es JSON válido, con la de GitHub,
  3) si tampoco, con la versión del último commit.
"""
import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
MARCAS = re.compile(r"^<<<<<<< .*?\n(.*?)^=======\n(.*?)^>>>>>>> .*?\n", re.S | re.M)


def lado(texto, cual):
    return MARCAS.sub(lambda m: m.group(cual), texto)


def valido(t):
    try:
        json.loads(t)
        return True
    except ValueError:
        return False


def main():
    arreglados = []
    for carpeta in ("publicaciones", "datos", "docs"):
        for f in (RAIZ / carpeta).glob("*.json"):
            try:
                t = f.read_text(encoding="utf-8")
            except OSError:
                continue
            if "<<<<<<< " not in t or valido(t):
                continue
            # en «git stash pop» la parte de arriba es la de GitHub y la de abajo la local
            for opcion in (lado(t, 2), lado(t, 1)):
                if valido(opcion):
                    f.write_text(opcion, encoding="utf-8")
                    break
            else:
                r = subprocess.run(["git", "-C", str(RAIZ), "show", f"HEAD:{f.relative_to(RAIZ)}"],
                                   capture_output=True, text=True)
                if r.returncode == 0 and valido(r.stdout):
                    f.write_text(r.stdout, encoding="utf-8")
                else:
                    print(f"⚠️ No he podido arreglar {f.relative_to(RAIZ)}")
                    continue
            arreglados.append(str(f.relative_to(RAIZ)))
    if arreglados:
        print("JSON arreglados tras un choque de git:", ", ".join(arreglados))


if __name__ == "__main__":
    main()
