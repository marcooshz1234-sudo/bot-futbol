import unittest

import combis_dia


def pk(i, m, o, c, pr, pid=1, lado=None):
    return {"partido_id": pid, "mercado": m, "opcion": o, "cuota": c, "prob_aprendida": pr, "texto": f"{m} {o}",
            "fecha": "2026-10-28T20:45", "tipo": "goles", "partido_id": i}



import combis_dia as _cd
_cd._APRENDIDO = {}   # 28/10: estos tests miden las reglas base, sin lo aprendido de las cuotas reales

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


class RecorteCaso28(unittest.TestCase):
    def test_city_brighton_como_bet365(self):
        import combis_dia
        sel = ["1|To Win Either Half|Home", "1|Total - Away|Over 0.5", "1|Away Team Total Cards|Over 1.5", "1|Total ShotOnGoal|Over 9.5"]
        real = combis_dia.cuota_real_sel(sel, [1.33, 1.36, 1.50, 1.91])
        self.assertAlmostEqual(real, 4.25, delta=0.15)   # bet365 pagaba 4,25 (Marcos, 28/10)


class RecorteMilan28(unittest.TestCase):
    def test_milan_bologna_como_bet365(self):
        import combis_dia
        from bot import EXTRA
        if not (EXTRA / "1550167.json").exists():   # 29/10: el bot borra las cuotas de los partidos ya jugados
            self.skipTest("ya no están las cuotas del Milan–Bologna")
        sel = ["1550167|ShotOnTarget 1x2|Home", "1550167|Total - Away|Over 0.5", "1550167|Match Winner|Home", "1550167|Cards Over/Under|Over 3.5"]
        real = combis_dia.cuota_real_sel(sel, [1.44, 1.62, 1.70, 1.80])
        self.assertAlmostEqual(real, 8.0, delta=0.4)   # bet365 pagaba 8,00 (Marcos, 28/10)
