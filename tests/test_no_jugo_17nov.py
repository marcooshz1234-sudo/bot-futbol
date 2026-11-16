"""17/11: «Gregor Kobel 3+ paradas» salió anulada (y la combi de x14,13 en verde) porque no llegaban sus minutos."""
import unittest

import picks as P


def partido(minutos):
    return {"estado": "FT", "jugadores": {"home": [{"id": 1, "nombre": "Gregor Kobel", "min": minutos}]}}


class NoJugo17Nov(unittest.TestCase):
    pick = {"mercado": "Goalkeeper Saves", "opcion": "Gregor Kobel - 3"}

    def test_sin_minutos_no_es_anulada(self):
        self.assertFalse(P.no_jugo(self.pick, partido(None)))

    def test_jugo_no_es_anulada(self):
        self.assertFalse(P.no_jugo(self.pick, partido(90)))

    def test_cero_minutos_si(self):
        self.assertTrue(P.no_jugo(self.pick, partido(0)))


if __name__ == "__main__":
    unittest.main()
