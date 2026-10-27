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
        r = combis_dia.mejor_combi(pool, (4, 7), (7 * combis_dia.FACTOR_CREAR, 10 * combis_dia.FACTOR_CREAR), 0.45)
        self.assertIsNotNone(r)
        self.assertTrue(7 * combis_dia.FACTOR_CREAR <= r[2] <= 10 * combis_dia.FACTOR_CREAR and 4 <= len(r[1]) <= 7)

    def test_no_mezcla_resultados_contrarios(self):
        a = pk(1, "Match Winner", "Home", 1.5, .7)
        b = pk(2, "Double Chance", "Draw/Away", 1.5, .6)
        self.assertFalse(combis_dia.coherente([a, b]))


if __name__ == "__main__":
    unittest.main()
