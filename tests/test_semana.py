import unittest
from unittest.mock import patch

import semana


class Semana(unittest.TestCase):
    def test_solo_lunes_y_viernes(self):
        self.assertIsNone(semana.post("2026-11-03"))
        self.assertIsNone(semana.resultado("2026-11-05"))

    def test_acierto(self):
        with patch.object(semana, "leer", lambda ruta, *a: {"estado": "FT", "goles": [2, 1]}):
            self.assertTrue(semana.acierto("1|Match Winner|Home"))
            self.assertFalse(semana.acierto("1|Match Winner|Away"))
            self.assertTrue(semana.acierto("1|Double Chance|Home/Draw"))
            self.assertFalse(semana.acierto("1|Double Chance|Draw/Away"))
        with patch.object(semana, "leer", lambda ruta, *a: {"estado": "NS"}):
            self.assertIsNone(semana.acierto("1|Match Winner|Home"))


if __name__ == "__main__":
    unittest.main()
