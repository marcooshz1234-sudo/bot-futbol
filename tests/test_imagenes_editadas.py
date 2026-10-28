import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import imagenes

M = ZoneInfo("Europe/Madrid")


class ImagenesEditadas(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp()) / "publicaciones" / "media"
        self.d.mkdir(parents=True)
        self.p = patch.object(imagenes, "MEDIA", self.d)
        self.p.start()
        self.post = {"id": "x", "fecha": "2026-10-28T02:00", "texto": "viejo", "foto": None}
        for e in ("mp4", "story.jpg"):
            (self.d / f"x.{e}").write_text("-")
        (self.d / "x.huella").write_text(imagenes.huella(self.post))

    def tearDown(self):
        self.p.stop()

    def test_editado_justo_antes_se_rehace(self):
        ahora = datetime(2026, 10, 28, 2, 5, tzinfo=M)   # ya tocaba y aún no ha salido en Instagram
        r = imagenes.pendientes_de([self.post], ahora, {"textos": {"x": "nuevo"}}, {})
        self.assertEqual([p["texto"] for p in r], ["nuevo"])

    def test_sin_cambios_no_se_rehace(self):
        ahora = datetime(2026, 10, 28, 1, 0, tzinfo=M)
        self.assertEqual(imagenes.pendientes_de([self.post], ahora, {}, {}), [])

    def test_ya_publicado_en_instagram_no_se_toca(self):
        ahora = datetime(2026, 10, 28, 2, 5, tzinfo=M)
        post = dict(self.post, redes={"instagram": "123"})
        self.assertEqual(imagenes.pendientes_de([post], ahora, {"textos": {"x": "nuevo"}}, {}), [])


if __name__ == "__main__":
    unittest.main()
