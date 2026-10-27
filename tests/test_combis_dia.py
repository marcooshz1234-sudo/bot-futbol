import unittest

import combis_dia


def pk(i, m, o, c, pr, pid=1, lado=None):
    return {"partido_id": pid, "mercado": m, "opcion": o, "cuota": c, "prob_aprendida": pr, "texto": f"{m} {o}",
            "fecha": "2026-10-28T20:45", "tipo": "goles", "partido_id": i}


class CombisDia(unittest.TestCase):
    def test_cuota_y_patas_en_el_intervalo(self):
        pool = [pk(1, "Goals Over/Under", "Over 1.5", 1.3, .8), pk(2, "Total - Home", "Over 0.5", 1.3, .78),
                pk(3, "Corners Over Under", "Over 8.5", 1.5, .7), pk(4, "Total - Away", "Over 0.5", 1.6, .65),
                pk(5, "Cards Over/Under", "Over 3.5", 1.7, .6), pk(6, "Both Teams Score", "Yes", 1.8, .55)]
        r = combis_dia.mejor_combi(pool, (4, 7), (3.0, 10.0), 0.45)
        self.assertIsNotNone(r)
        self.assertTrue(3.0 <= r[2] <= 10.0 and 4 <= len(r[1]) <= 7)

    def test_no_mezcla_resultados_contrarios(self):
        a = pk(1, "Match Winner", "Home", 1.5, .7)
        b = pk(2, "Double Chance", "Draw/Away", 1.5, .6)
        self.assertFalse(combis_dia.coherente([a, b]))




class FactorCrear(unittest.TestCase):
    def test_medidas_bet365(self):
        """27/10: combi mezclada de Monza–Napoli multiplica 5,36 y bet365 paga 4,60 (0,86)."""
        mk = lambda m, o, **k: dict(mercado=m, opcion=o, cuota=1.3, **k)
        comb = [mk("Away Player Shots", "Scott McTominay - 2", tipo="jugador", jugador="McTominay", campo="tiros"),
                mk("Goals Over/Under First Half", "Over 0.5"),
                mk("To Win Either Half", "Away"),
                mk("Home Player Shots On Target Total", "Gustavo Varela - 1", tipo="jugador", jugador="Varela", campo="a_puerta"),
                mk("ShotOnTarget 1x2", "Away")]
        self.assertAlmostEqual(combis_dia.factor_crear(comb), 0.86, delta=0.02)
        comb2 = [comb[0], comb[3], mk("Total - Home", "Over 0.5"), mk("Home Corners Over/Under", "Over 3.5"),
                 mk("Total Shots", "Over 28.5")]
        self.assertAlmostEqual(combis_dia.factor_crear(comb2), 0.63, delta=0.02)
        # gana o empata + ese equipo marca: recorte fuerte
        self.assertLess(combis_dia.pareja(mk("Double Chance", "Home/Draw"), mk("Total - Home", "Over 0.5")), 0.85)


if __name__ == "__main__":
    unittest.main()
