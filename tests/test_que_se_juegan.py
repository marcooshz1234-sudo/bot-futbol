"""16/11 (Marcos: «mira a ver si se juegan algo»): Suiza (ya 1.ª) – Escocia (se juega el play-off) no puede llevar
«gana Suiza»; las patas del que se lo juega suben y las del que no, bajan. Desempate UEFA: el cara a cara primero."""
import unittest

import que_se_juegan as Q


def f(fid, h, a, gh=None, ga=None, fecha="2099-11-16T19:45:00+00:00", fase="League B - 6"):
    return {"fixture": {"id": fid, "date": fecha, "status": {"short": "FT" if gh is not None else "NS"}},
            "league": {"id": 5, "round": fase}, "teams": {"home": {"name": h}, "away": {"name": a}},
            "goals": {"home": gh, "away": ga}}


# Grupo como el de Suiza el 16/11: Suiza 13, Eslovenia 8, Escocia 7, Macedonia 0; quedan SUI-SCO y MKD-SVN
CAL = [f(1, "MKD", "SUI", 0, 3), f(2, "SVN", "SCO", 0, 0), f(3, "SVN", "MKD", 2, 0), f(4, "SCO", "SUI", 0, 3),
       f(5, "SUI", "SVN", 2, 1), f(6, "MKD", "SCO", 0, 2), f(7, "SUI", "MKD", 3, 0), f(8, "SCO", "SVN", 1, 2),
       f(9, "SVN", "SUI", 0, 0), f(10, "SCO", "MKD", 2, 1), f(11, "SUI", "SCO"), f(12, "MKD", "SVN")]


class QueSeJuegan(unittest.TestCase):
    def setUp(self):
        Q._cache[5] = CAL

    def tearDown(self):
        Q._cache.pop(5, None)

    def test_suiza_nada_escocia_se_juega(self):
        c = Q.contexto(5, 11)
        self.assertEqual(c["local"]["estado"], "nada")
        self.assertIn("ya es 1.º", c["local"]["texto"])
        self.assertEqual(c["visitante"]["estado"], "se_juega")
        self.assertIn("gana: 2.º-3.º", c["visitante"]["texto"])
        self.assertIn("(se queda)", Q.contexto(5, 11)["visitante"]["texto"])   # empata/pierde: 3.º
        self.assertTrue(Q.sin_motivo(5, 11, "local"))
        self.assertFalse(Q.sin_motivo(5, 11, "visitante"))

    def test_eslovenia_se_juega_macedonia_descendida(self):
        c = Q.contexto(5, 12)
        self.assertEqual(c["local"]["estado"], "nada")
        self.assertIn("play-off para no bajar", c["local"]["texto"])   # 2026-27: el 4.º de la B no baja directo
        self.assertFalse(Q.sin_motivo(5, 12, "visitante"))

    def test_liga_d_nadie_se_juega_nada(self):
        # 2026-27: en la Liga D suben todos a la C → Gibraltar – Malta no es «se_juega» para nadie
        Q._cache[5] = [dict(x, league={"id": 5, "round": "League D - 6"}) for x in CAL]
        c = Q.contexto(5, 12)
        self.assertEqual(c["visitante"]["estado"], "nada")
        self.assertIn("sube a la C", c["visitante"]["texto"])

    def test_cara_a_cara_primero(self):
        # A y B empatan a 3 puntos; B tiene mejor diferencia general (+4 frente a 0), pero A le ganó: A va delante
        ms = [("A", "B", 1, 0), ("B", "C", 5, 0), ("C", "D", 0, 1), ("A", "D", 0, 1)]
        o = Q.orden(ms, ["A", "B", "C", "D"])
        self.assertLess(o.index("A"), o.index("B"))

    def test_calendario_viejo_no_adivina(self):
        Q._cache[5] = [x if x["fixture"]["id"] != 11 else f(11, "SUI", "SCO", fecha="2020-01-01T19:45:00+00:00")
                       for x in CAL]
        self.assertIsNone(Q.contexto(5, 11))

    def test_motivacion_en_las_patas(self):
        import combis_dia
        ex = {"partido": {"league": {"id": 5}, "fixture": {"id": 11}}}
        gana = {"mercado": "Match Winner", "opcion": "Home", "prob_aprendida": 0.6}
        self.assertTrue(combis_dia.gana_sin_motivo(ex, gana))
        self.assertFalse(combis_dia.gana_sin_motivo(ex, dict(gana, opcion="Away")))
        pool = [{"mercado": "Corners 1x2", "opcion": "Away", "prob_aprendida": 0.5},
                {"mercado": "Corners 1x2", "opcion": "Home", "prob_aprendida": 0.5},
                {"mercado": "Goals Over/Under", "opcion": "Over 1.5", "prob_aprendida": 0.7}]
        r = combis_dia.con_motivacion(ex, pool)
        self.assertGreater(r[0]["prob_aprendida"], 0.5)   # Escocia (se lo juega)
        self.assertLess(r[1]["prob_aprendida"], 0.5)      # Suiza (nada)
        self.assertEqual(r[2]["prob_aprendida"], 0.7)     # goles del partido: igual


if __name__ == "__main__":
    unittest.main()
