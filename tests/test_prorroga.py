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


class ProrrogaEstadisticas(unittest.TestCase):
    def base(self, **extra):
        p = partido("AET", [1, 1], [0, 0], [gol(30, 1), gol(80, 2),
                                            {"min": 50, "equipo": 1, "tipo": "Card", "detalle": "Yellow Card", "jugador": "A"},
                                            {"min": 105, "equipo": 1, "tipo": "Card", "detalle": "Yellow Card", "jugador": "B"}])
        p["stats"] = {"1": {"corners": 9, "a_puerta": 6, "amarillas": 2, "rojas": 0},
                      "2": {"corners": 3, "a_puerta": 2, "amarillas": 0, "rojas": 0}}
        p.update(extra)
        return p

    def test_corners_de_las_dos_partes(self):
        p = self.base(stats_partes={"1": {"corners": {"1h": 3, "2h": 4}}, "2": {"corners": {"1h": 1, "2h": 1}}})
        # 12 con la prórroga, 9 en los 90
        self.assertFalse(picks.evaluar_pick({"mercado": "Corners Over Under", "opcion": "Over 9.5"}, p))

    def test_tarjetas_solo_hasta_el_90(self):
        p = self.base()
        self.assertFalse(picks.evaluar_pick({"mercado": "Home Team Yellow Cards", "opcion": "Over 1.5"}, p))

    def test_sin_partes_y_cumplido_no_se_sabe(self):
        p = self.base()
        self.assertIsNone(picks.evaluar_pick({"mercado": "Total ShotOnGoal", "opcion": "Over 6.5"}, p))
        # ni contando la prórroga llega: roja segura
        self.assertFalse(picks.evaluar_pick({"mercado": "Total ShotOnGoal", "opcion": "Over 9.5"}, p))

    def test_jugador(self):
        p = self.base()
        p["eventos"].append(dict(gol(100, 1), jugador="Pepe Gol"))
        p["goles"] = [2, 1]
        p["jugadores"] = {"1": [{"id": 7, "nombre": "Pepe Gol", "min": 120, "goles": 1, "a_puerta": 3},
                                {"id": 8, "nombre": "Juan Tiro", "min": 75, "a_puerta": 2}]}
        self.assertFalse(picks.evaluar_pick({"mercado": "Anytime Goal Scorer", "opcion": "Pepe Gol", "jugador_id": 7, "n": 1}, p))
        self.assertIsNone(picks.evaluar_pick({"mercado": "Player Shots On Target", "opcion": "Pepe Gol - 1", "jugador_id": 7, "n": 1}, p))
        self.assertTrue(picks.evaluar_pick({"mercado": "Player Shots On Target", "opcion": "Juan Tiro - 1", "jugador_id": 8, "n": 1}, p))

    def test_extraer_partes(self):
        import bot
        r = bot.extraer_stats_por_parte([{"team": {"id": 1}, "statistics": [{"type": "Corner Kicks", "value": 5}],
                                           "statistics_1h": [{"type": "Corner Kicks", "value": 2}, {"type": "Shots on Goal", "value": 1}],
                                           "statistics_2h": [{"type": "Corner Kicks", "value": 2}]}])
        self.assertEqual(r["1"]["corners"], {"1h": 2, "2h": 2})
        self.assertEqual(r["1"]["a_puerta"], {"1h": 1})
