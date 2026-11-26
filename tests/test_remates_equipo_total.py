"""26/11 (Marcos: «otra vez que no se sube el resumen»): «Bayern: más de 16,5 remates» (bet365: «Away Player
Shots Total | Over 16.5») se leía como pick de jugador, se quedaba sin verde/rojo y el resumen esperaba."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import picks as P  # noqa: E402

PARTIDO = {"estado": "FT", "goles": [2, 1], "local": {"id": 79}, "visitante": {"id": 157},
           "stats": {"79": {"tiros": 15, "a_puerta": 3}, "157": {"tiros": 12, "a_puerta": 7}}}


class RematesEquipo(unittest.TestCase):
    def test_total_de_equipo(self):
        self.assertFalse(P.evaluar_pick({"mercado": "Away Player Shots Total", "opcion": "Over 16.5"}, PARTIDO))
        self.assertTrue(P.evaluar_pick({"mercado": "Home Player Shots Total", "opcion": "Over 14.5"}, PARTIDO))
        self.assertTrue(P.evaluar_pick({"mercado": "Away Player Shots On Target Total", "opcion": "Over 5.5"}, PARTIDO))

    def test_el_de_jugador_sigue_igual(self):
        p = dict(PARTIDO, jugadores={"157": [{"nombre": "Harry Kane", "min": 90, "tiros": 4}]})
        self.assertTrue(P.evaluar_pick({"mercado": "Away Player Shots Total", "opcion": "Harry Kane - 3"}, p))


if __name__ == "__main__":
    unittest.main()
