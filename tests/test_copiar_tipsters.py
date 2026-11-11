import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import copiar_tipsters as C
from bot import MADRID


class TestCopiarTipsters(unittest.TestCase):
    def test_suelto_y_combi(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            tips = [{"tipster": "Tipster Pérez", "fuente": "a/1", "dia": "2026-11-12", "local": "Czechia", "visitante": "Spain",
                     "texto": "Gana España", "mercado": "Match Winner", "opcion": "Away", "cuota": 1.5, "partido_id": 1},
                    {"tipster": "TipsAnalistas", "fuente": "b/1", "dia": "2026-11-12", "local": "A", "visitante": "B",
                     "texto": "Gana A", "mercado": "Match Winner", "opcion": "Home", "cuota": 1.4, "partido_id": 2, "combinada": "x"},
                    {"tipster": "TipsAnalistas", "fuente": "b/1", "dia": "2026-11-12", "local": "C", "visitante": "D",
                     "texto": "C o empate", "mercado": "Double Chance", "opcion": "Home/Draw", "cuota": 1.3, "partido_id": 3, "combinada": "x"},
                    {"tipster": "INSIDER", "fuente": "c/1", "dia": "2026-11-12", "local": "E", "visitante": "F",
                     "texto": "Gana E", "partido_id": 4, "cuota": 1.6}]
            (d / "tipsters.json").write_text(json.dumps(tips))
            ini = datetime(2026, 11, 12, 20, 45, tzinfo=MADRID)
            with mock.patch.object(C, "DATOS", d), mock.patch.object(C, "REGISTRO", d / "r.json"), \
                    mock.patch.object(C, "COLA", d / "cola.json"), mock.patch.object(C, "inicio", lambda pk: ini):
                n = C.main(datetime(2026, 11, 11, 8, 0, tzinfo=MADRID))
                self.assertEqual([p["id"] for p in n], ["2026-11-12-pick-tip-1", "2026-11-12-combi-tip-1"])
                self.assertIn("🍀 Gana España @1,50", n[0]["texto"])
                self.assertIn("Cuota @1,82", n[1]["texto"])
                self.assertNotIn("Pérez", n[0]["texto"] + n[1]["texto"])
                self.assertEqual(C.main(datetime(2026, 11, 11, 8, 5, tzinfo=MADRID)), [])   # no se repite

    def test_empezado_no(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "tipsters.json").write_text(json.dumps([{"tipster": "TipsAnalistas", "fuente": "z", "dia": "2026-11-11",
                                                            "local": "A", "visitante": "B", "texto": "Gana A", "partido_id": 9}]))
            with mock.patch.object(C, "DATOS", d), mock.patch.object(C, "REGISTRO", d / "r.json"), \
                    mock.patch.object(C, "COLA", d / "cola.json"), \
                    mock.patch.object(C, "inicio", lambda pk: datetime(2026, 11, 11, 8, 10, tzinfo=MADRID)):
                self.assertEqual(C.main(datetime(2026, 11, 11, 8, 0, tzinfo=MADRID)), [])


if __name__ == "__main__":
    unittest.main()
