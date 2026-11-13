"""13/11: el 12/11 los logos de la marca se pasaron de .png a .jpg y marca.py los seguía buscando en .png: todas las
fotos salieron sin el logo CL (ponía «COMBILOCAS» en letras) y sin que nadie avisara. Cada archivo de la marca que
nombra el código tiene que existir."""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = RAIZ / "publicaciones" / "media" / "marca"


class ArchivosMarca(unittest.TestCase):
    def test_existen(self):
        faltan = []
        for f in list(RAIZ.glob("*.py")) + list((RAIZ / "widget").glob("*.js")):
            src = f.read_text(encoding="utf-8")
            nombres = re.findall(r"marca/([\w\-]+\.(?:png|jpg|mp4))", src)
            nombres += re.findall(r'(?:CARPETA|MARCA)\s*/\s*\(?\s*f?"([\w\-]+\.(?:png|jpg|mp4))"', src)
            nombres += [n for par in re.findall(r'\("([\w\-]+\.png)" if TEMA == "cl" else "([\w\-]+\.png)"\)', src) for n in par]
            faltan += [f"{f.name}: {n}" for n in nombres if not (MARCA / n).exists()]
        self.assertEqual(faltan, [])

    def test_logo_en_las_fotos(self):
        import marca
        self.assertTrue(marca.LOGO_GRANDE.exists() and marca.CIRCULO.exists())
        self.assertNotIn("COMBILOCAS</span>", marca.logo_img(100))


if __name__ == "__main__":
    unittest.main()
