"""13/11 (Marcos: «el proyecto limpio»): fotos de boletos y partidos en directo de hace más de una semana."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import limpiar_media as L
from bot import MADRID


class LimpiarDatos(unittest.TestCase):
    def test_borra_solo_lo_viejo(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "datos" / "tipsters_fotos").mkdir(parents=True)
            (d / "datos" / "en_directo").mkdir()
            for n in ("nueva.jpg", "vieja.jpg", "huerfana.jpg"):
                (d / "datos" / "tipsters_fotos" / n).write_bytes(b"x")
            (d / "datos" / "tipsters_raw.json").write_text(json.dumps({"c": [
                {"fecha": "2026-11-12T10:00", "foto_ruta": "datos/tipsters_fotos/nueva.jpg"},
                {"fecha": "2026-11-01T10:00", "foto_ruta": "datos/tipsters_fotos/vieja.jpg"}]}))
            (d / "datos" / "en_directo" / "1.json").write_text(json.dumps({"fecha": "2026-11-12T20:45"}))
            (d / "datos" / "en_directo" / "2.json").write_text(json.dumps({"fecha": "2026-11-02T20:45"}))
            with mock.patch.object(L, "RAIZ", d):
                fuera = sorted(f.name for f in L.datos_viejos(datetime(2026, 11, 13, 7, 0, tzinfo=MADRID)))
        self.assertEqual(fuera, ["2.json", "huerfana.jpg", "vieja.jpg"])


if __name__ == "__main__":
    unittest.main()
