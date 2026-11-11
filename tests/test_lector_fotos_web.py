"""11/11: los boletos (fotos) de los canales leídos por la web (TipsAnalistas) también se bajan."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import lector_canales as L

PAGINA = ('<div class="tgme_widget_message_wrap"><div data-post="Tipsanalistas/99">'
          '<a class="tgme_widget_message_photo_wrap 1" style="width:800px;background-image:url(\'https://cdn.example/f.jpg?a=1&amp;b=2\')"></a>'
          '<div class="tgme_widget_message_photo"></div><time datetime="2026-11-11T19:43:00+00:00"></time></div></div>')


class Resp:
    def __init__(self, b): self.b = b
    def read(self): return self.b
    def __enter__(self): return self
    def __exit__(self, *a): return False


class FotosWeb(unittest.TestCase):
    def test_saca_url_y_baja_foto(self):
        with mock.patch("urllib.request.urlopen", return_value=Resp(PAGINA.encode())):
            p = L.leer_canal("Tipsanalistas")[0]
        self.assertTrue(p["foto"])
        self.assertEqual(p["foto_url"], "https://cdn.example/f.jpg?a=1&b=2")
        with tempfile.TemporaryDirectory() as d:
            datos = Path(d) / "datos"
            datos.mkdir()
            with mock.patch.object(L, "FOTOS", datos / "tipsters_fotos"), mock.patch.object(L, "DATOS", datos), \
                    mock.patch("urllib.request.urlopen", return_value=Resp(b"JPG")):
                L.bajar_foto_web(p, "TipsAnalistas")
            self.assertEqual(p["foto_ruta"], "datos/tipsters_fotos/TipsAnalistas_99.jpg")
            self.assertNotIn("foto_url", p)
            self.assertEqual((datos / "tipsters_fotos" / "TipsAnalistas_99.jpg").read_bytes(), b"JPG")

    def test_sin_foto_no_hace_nada(self):
        p = {"id": "x/1"}
        L.bajar_foto_web(p, "X")
        self.assertNotIn("foto_ruta", p)


if __name__ == "__main__":
    unittest.main()
