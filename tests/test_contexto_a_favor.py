import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import contexto_extra as C


class SoloLoQueApoya(unittest.TestCase):
    """15/11 (Marcos): «Bielorrusia marca» con «los dos llegan cansados» debajo no tiene sentido."""
    def razones(self, c, pick):
        with mock.patch.object(C, "leer", lambda *a, **k: {"7": c}):
            return [f for _, f in C.razones(7, pick)]

    def test_los_dos_cansados_no_sale(self):
        c = {"local": {"nombre": "Bielorrusia", "dias_desde": 2}, "visitante": {"nombre": "Albania", "dias_desde": 2}}
        r = self.razones(c, {"texto": "Bielorrusia marca", "mercado": "Total - Home", "opcion": "Over 0.5"})
        self.assertFalse([x for x in r if "cansado" in x])

    def test_solo_el_rival_cansado(self):
        c = {"local": {"nombre": "Bielorrusia", "dias_desde": 5}, "visitante": {"nombre": "Albania", "dias_desde": 2}}
        r = self.razones(c, {"texto": "Gana Bielorrusia", "mercado": "Match Winner", "opcion": "Home"})
        self.assertTrue(any("Albania jugó hace 2 días" in x for x in r))
        r = self.razones(c, {"texto": "Gana Albania", "mercado": "Match Winner", "opcion": "Away"})
        self.assertFalse([x for x in r if "cansado" in x])   # el cansado es el nuestro: en contra

    def test_pick_neutro_sin_cansancio(self):
        c = {"local": {"nombre": "A", "dias_desde": 1}, "visitante": {"nombre": "B", "dias_desde": 5}}
        self.assertEqual(self.razones(c, {"texto": "Ambos marcan", "mercado": "Both Teams Score", "opcion": "Yes"}), [])


if __name__ == "__main__":
    unittest.main()
