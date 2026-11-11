"""11/11: Pinnacle como referencia, etiquetas diversión/cabeza y aprendizaje de tipsters."""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import plantillas  # noqa: E402
import sharp  # noqa: E402
import tipsters  # noqa: E402

DATOS = {"1": {"cuotas": {"bookmakerOdds": {"pinnacle": {"markets": {
    "101": {"outcomes": {"101": {"players": {"0": {"price": 2.0}}}, "102": {"players": {"0": {"price": 3.5}}},
                         "103": {"players": {"0": {"price": 4.0}}}}},
    "1010": {"outcomes": {"1010": {"players": {"0": {"price": 1.9}}}, "1011": {"players": {"0": {"price": 1.9}}}}}}}}}}}


class TestSharp(unittest.TestCase):
    def setUp(self):
        sharp._datos.c = DATOS

    def tearDown(self):
        del sharp._datos.c

    def test_prob_justa(self):
        p = sharp.prob_justa(1, "Match Winner", "Home")
        self.assertAlmostEqual(p, (1 / 2) / (1 / 2 + 1 / 3.5 + 1 / 4), places=3)
        self.assertAlmostEqual(sharp.prob_justa(1, "Goals Over/Under", "Over 2.5"), 0.5, places=3)
        self.assertIsNone(sharp.prob_justa(1, "Total - Home", "Over 0.5"))
        self.assertIsNone(sharp.prob_justa(2, "Match Winner", "Home"))

    def test_filtrar(self):
        pool = [{"partido_id": 1, "mercado": "Goals Over/Under", "opcion": "Over 2.5", "cuota": 1.80, "texto": "cara"},
                {"partido_id": 1, "mercado": "Goals Over/Under", "opcion": "Over 2.5", "cuota": 2.05, "texto": "buena"},
                {"partido_id": 1, "mercado": "Corners", "opcion": "Over 9.5", "cuota": 1.5, "texto": "sin dato"}]
        r = sharp.filtrar(pool)
        self.assertEqual([p["texto"] for p in r], ["buena", "sin dato"])
        self.assertEqual(r[0]["prob_aprendida"], 0.5)


class TestEtiquetas(unittest.TestCase):
    def test_etiquetas(self):
        self.assertIn(plantillas.ETIQUETA_DIVERSION, plantillas.etiquetar("combi-loca", "Hola\n\n🍀 a"))
        self.assertIn(plantillas.ETIQUETA_CABEZA, plantillas.etiquetar("pick-seguro", "Hola\n\n🍀 a"))
        self.assertEqual(plantillas.etiquetar("ganadores-win", "Hola"), "Hola")
        t = plantillas.etiquetar("combi-tres", "Hola\n\n🍀 a")
        self.assertEqual(plantillas.etiquetar("combi-tres", t), t)


class TestTipsters(unittest.TestCase):
    def test_total_equipo(self):
        self.assertEqual(tipsters.resultado({"mercado": "Total - Away", "opcion": "Over 0.5"}, (2, 1)), "verde")
        self.assertEqual(tipsters.resultado({"mercado": "Total - Home", "opcion": "Over 1.5"}, (1, 0)), "rojo")

    def test_bonus(self):
        for k in ("hoy", "ap"):
            if hasattr(tipsters.bonus, k):
                delattr(tipsters.bonus, k)
        lista = [{"tipster": "A", "partido_id": 9, "mercado": "Match Winner", "opcion": "Home"}]
        with mock.patch.object(tipsters, "leer", side_effect=lambda f, d=None: lista if f == tipsters.FICHERO else
                               {"tipster": {"A": {"verdes": 15, "rojos": 10, "unidades": 3.0}}}):
            self.assertEqual(tipsters.bonus({"partido_id": 9, "mercado": "Match Winner", "opcion": "Home"}), (0.05, ["A"]))
            self.assertEqual(tipsters.bonus({"partido_id": 9, "mercado": "Match Winner", "opcion": "Away"}), (0.0, []))
        for k in ("hoy", "ap"):
            delattr(tipsters.bonus, k)


if __name__ == "__main__":
    unittest.main()
