import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import redes


class Historias(unittest.TestCase):
    def test_verde_sale_tambien_como_historia(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); pub = root / "publicaciones"; (pub / "media").mkdir(parents=True)
            ahora = datetime.now(redes.MADRID)
            post = {"id": "2026-10-26-verde-auto-x", "fecha": (ahora - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M"),
                    "texto": "✅💚 ¡VERDE x3,00! A 🆚 B 💚✅", "directo": True}
            (pub / "cola.json").write_text(json.dumps([post]))
            for ext in ("jpg", "mp4", "story.jpg"):
                (pub / "media" / f"{post['id']}.{ext}").write_text("x")
            with patch.multiple(redes, RAIZ=root, COLA=pub / "cola.json", AUTO=pub / "auto.json",
                                CONTROL=pub / "control.json", ESTADO_AUTO=pub / "enviados_redes.json"), \
                    patch.dict(os.environ, {"INSTAGRAM_TOKEN": "t"}, clear=True), \
                    patch.object(redes, "ya_esta", return_value=False), \
                    patch.object(redes, "instagram", return_value="ig1"), \
                    patch.object(redes, "instagram_story", return_value="st1") as story:
                redes.main()
                story.assert_called_once()
            hecho = json.loads((pub / "cola.json").read_text())[0]["redes"]
            self.assertEqual(hecho.get("instagram_story"), "st1")


if __name__ == "__main__":
    unittest.main()
