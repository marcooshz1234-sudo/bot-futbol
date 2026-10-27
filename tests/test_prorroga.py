import unittest
import picks


def partido(estado, goles, descanso, eventos, goles_90=None):
    p = {"estado": estado, "local": {"id": 1}, "visitante": {"id": 2}, "goles": goles, "descanso": descanso,
         "eventos": eventos, "stats": {}}
    if goles_90 is not None:
        p["goles_90"] = goles_90
    return p


def gol(minuto, equipo, detalle="Normal Goal"):
    return {"min": minuto, "extra": None, "equipo": equipo, "tipo": "Goal", "detalle": detalle}


class Prorroga(unittest.TestCase):
    # Recreativo–Rayo (Copa, 27/10): 1-1 a los 90 y 2-3 tras la prórroga
    def setUp(self):
        self.p = partido("AET", [2, 3], [1, 1], [gol(23, 1), gol(43, 2), gol(97, 2), gol(99, 2), gol(109, 1)])

    def test_gana_una_parte_no_cuenta_la_prorroga(self):
        self.assertFalse(picks.evaluar_pick({"mercado": "To Win Either Half", "opcion": "Away"}, self.p))

    def test_ganador_y_goles_a_los_90(self):
        self.assertFalse(picks.evaluar_pick({"mercado": "Match Winner", "opcion": "Away"}, self.p))
        self.assertTrue(picks.evaluar_pick({"mercado": "Match Winner", "opcion": "Draw"}, self.p))
        self.assertFalse(picks.evaluar_pick({"mercado": "Goals Over/Under", "opcion": "Over 2.5"}, self.p))

    def test_dos_goles_arriba_solo_en_90(self):
        p = partido("AET", [1, 3], [0, 0], [gol(80, 1), gol(88, 2), gol(100, 2), gol(115, 2)])
        self.assertFalse(picks.lidero_por_2(p, 2))

    def test_usa_marcador_90_guardado(self):
        p = partido("PEN", [1, 1], [0, 0], [], goles_90=[1, 1])
        self.assertTrue(picks.evaluar_pick({"mercado": "Both Teams Score", "opcion": "Yes"}, p))

    def test_partido_normal_igual(self):
        p = partido("FT", [0, 2], [0, 1], [gol(30, 2), gol(92, 2)])
        self.assertTrue(picks.evaluar_pick({"mercado": "To Win Either Half", "opcion": "Away"}, p))


if __name__ == "__main__":
    unittest.main()
