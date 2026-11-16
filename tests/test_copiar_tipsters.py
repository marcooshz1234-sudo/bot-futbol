import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import copiar_tipsters as C
from bot import MADRID


class TestCopiarTipsters(unittest.TestCase):
    def setUp(self):   # 16/11: el filtro de calidad de las copias se prueba en test_copiar_calidad
        _p = mock.patch("copiar_tipsters.calidad_no", return_value=None)
        _p.start()
        self.addCleanup(_p.stop)

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
                # 12/11: ya se copian todos los canales de fútbol (también INSIDER)
                # 15/11 (Marcos): los 2 sueltos que llegan a la vez salen juntos en una combi (no sueltos)
                self.assertEqual([p["id"] for p in n], ["2026-11-12-combi-tip-1", "2026-11-12-combi-tip-2"])
                self.assertIn("Gana España", n[0]["texto"])
                self.assertIn("Cuota @2,40", n[0]["texto"])
                self.assertIn("Cuota @1,82", n[1]["texto"])
                self.assertNotIn("Pérez", n[0]["texto"] + n[1]["texto"])
                # 11/11: con sel y cuotas de la misma longitud, para que la app y los verdes los corrijan
                for p in n:
                    self.assertEqual(len(p["sel"]), len(p["cuotas"]))
                self.assertEqual(C.main(datetime(2026, 11, 11, 8, 5, tzinfo=MADRID)), [])   # no se repite

    def test_suelto_ya_subido_no_entra_en_combi(self):
        """15/11 (Marcos): si un pick ya salió suelto, el que llega después sale suelto, no en combi con él."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            t1 = {"tipster": "A", "fuente": "a/1", "dia": "2026-11-12", "local": "A", "visitante": "B", "texto": "Gana A",
                  "mercado": "Match Winner", "opcion": "Home", "cuota": 1.5, "partido_id": 1}
            t2 = {"tipster": "B", "fuente": "b/1", "dia": "2026-11-12", "local": "C", "visitante": "D", "texto": "Gana C",
                  "mercado": "Match Winner", "opcion": "Home", "cuota": 1.6, "partido_id": 2}
            ini = datetime(2026, 11, 12, 20, 45, tzinfo=MADRID)
            with mock.patch.object(C, "DATOS", d), mock.patch.object(C, "REGISTRO", d / "r.json"), \
                    mock.patch.object(C, "COLA", d / "cola.json"), mock.patch.object(C, "inicio", lambda pk: ini):
                (d / "tipsters.json").write_text(json.dumps([t1]))
                self.assertEqual([p["id"] for p in C.main(datetime(2026, 11, 11, 8, 0, tzinfo=MADRID))], ["2026-11-12-pick-tip-1"])
                (d / "tipsters.json").write_text(json.dumps([t1, t2]))
                self.assertEqual([p["id"] for p in C.main(datetime(2026, 11, 11, 8, 5, tzinfo=MADRID))], ["2026-11-12-pick-tip-2"])

    def test_combi_con_pata_sin_seguir_no_se_corrige_sola(self):
        import copiar_tipsters as C
        from datetime import datetime
        from bot import MADRID
        ini = datetime(2026, 11, 11, 20, 0, tzinfo=MADRID)
        patas = [{"dia": "2026-11-11", "texto": "Gana el Betis", "cuota": 1.5, "partido_id": 1, "mercado": "Match Winner",
                  "opcion": "Home", "_ini": ini},
                 {"dia": "2026-11-11", "texto": "Accrington +1,5", "cuota": 1.5, "hora": "20:00", "_ini": ini}]
        p = C.post_combi(patas, ini.replace(hour=12), 1)
        self.assertEqual(p["sel"], [])   # si no, el verde saldría sin mirar la pata de Accrington
        self.assertEqual(p["cuotas"], [])
        p = C.post_combi([patas[0], dict(patas[0], partido_id=2)], ini.replace(hour=12), 1)
        self.assertEqual(len(p["sel"]), 2)
        self.assertEqual(p["cuotas"], [1.5, 1.5])

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
