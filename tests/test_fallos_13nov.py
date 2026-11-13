"""13/11 (Marcos: «hemos fallado bastante»): Suiza en 4 posts (0-0), «más goles» en Liechtenstein y Luxemburgo
(0-1 los dos) y combis largas que caen por una pata. «Una combi al día tiene que haber; el resto lo puedes cambiar»."""
import unittest
from unittest import mock

import combis_dia as C


class Fallos13Nov(unittest.TestCase):
    def test_mas_goles(self):
        self.assertTrue(C.es_mas_goles({"mercado": "Goals Over/Under", "opcion": "Over 1.5"}))
        self.assertTrue(C.es_mas_goles({"mercado": "Total - Away", "opcion": "Over 1.5"}))
        self.assertTrue(C.es_mas_goles({"mercado": "Both Teams Score", "opcion": "Yes"}))
        self.assertFalse(C.es_mas_goles({"mercado": "Total - Away", "opcion": "Over 0.5"}))   # «X marca» sí vale
        self.assertFalse(C.es_mas_goles({"mercado": "Goals Over/Under", "opcion": "Under 3.5"}))

    def test_partido_flojo_de_selecciones(self):
        ex = {"partido": {"league": {"id": 5}}, "cuotas": {"Goals Over/Under": [["Over 2.5", "2.05"]]}}
        self.assertTrue(C.partido_flojo_de_goles(ex))   # Liechtenstein–Azerbaiyán
        ex["cuotas"]["Goals Over/Under"] = [["Over 2.5", "1.53"]]
        self.assertFalse(C.partido_flojo_de_goles(ex))   # Países Bajos–Grecia
        self.assertFalse(C.partido_flojo_de_goles({"partido": {"league": {"id": 140}},
                                                   "cuotas": {"Goals Over/Under": [["Over 2.5", "2.30"]]}}))

    def test_mismo_equipo_mismo_contador(self):
        with mock.patch.object(C, "lado", return_value="visitante"):
            a = C.equipo_de({"partido_id": 1545654, "mercado": "Match Winner", "opcion": "Away"})
            b = C.equipo_de({"partido_id": 1545654, "mercado": "To Win Either Half", "opcion": "Away"})
        self.assertEqual(a, b)   # «Gana Suiza» y «Suiza gana una parte» cuentan como el mismo equipo
        self.assertEqual(C.MAX_POSTS_EQUIPO, 2)
        # Marcos: «¿dos posts al día sea el partido que sea?» → córners, tarjetas, jugadores y goles no cuentan
        for m, o in (("Corners Over Under", "Over 8.5"), ("Goals Over/Under", "Over 1.5"), ("Total - Home", "Over 1.5"),
                     ("Cards Over/Under", "Over 4.5")):
            self.assertIsNone(C.equipo_de({"partido_id": 1, "mercado": m, "opcion": o}), m)
        self.assertEqual(C.equipo_de({"partido_id": 1, "mercado": "Double Chance", "opcion": "Draw/Away"}), "1|visitante")
        self.assertIn("combi-partido", C.NO_CUENTAN_EQUIPO)
        self.assertIn("estrella", C.NO_CUENTAN_EQUIPO)

    def test_dia_bueno_una_sola_combi(self):
        src = open(C.__file__, encoding="utf-8").read()
        self.assertIn('res["multi"] = None if bueno else', src)
        self.assertIn('if bueno and clave == "loca"', src)


if __name__ == "__main__":
    unittest.main()
