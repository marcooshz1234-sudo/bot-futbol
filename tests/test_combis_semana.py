import unittest
from datetime import datetime
from unittest import mock
import combis_semana as CS
from bot import MADRID


def partido(i, hora, liga="LaLiga"):
    return {"id": i, "fecha": f"2026-11-21T{hora}:00+01:00", "competicion": liga, "local": f"L{i}", "visitante": f"V{i}",
            "stats_local": {"forma": "VVVDE", "gf": 2.0, "btts": "70%", "o25": "70%"},
            "stats_visitante": {"forma": "DDEVD", "gc": 1.8, "btts": "65%", "o25": "62%"},
            "cuotas_bet365": {"Match Winner": [["Home", "1.50"], ["Away", "5"]],
                              "Player Fouls Committed": [["Pepe Uno - 1", "1.50"]]}}


class CombisSemana(unittest.TestCase):
    """20/11 (Marcos): un partido por pata, ~@1,50, con el dato del jugador (cumple X/Y siendo titular)."""
    def test_una_pata_por_partido_y_dato_de_titular(self):
        h = {"pepe uno": [{"nombre": "Pepe Uno", "min": 90, "faltas_c": v, "eq": "10"} for v in (1, 2, 1, 1, 0, 1)]}
        ps = [partido(i, f"{12 + i}:00") for i in range(5)]
        with mock.patch.object(CS, "equipos_partido", lambda pid: {"10", "20"}):
            cs = CS.generar("2026-11-21", "2026-11-23", partidos=ps, h=h)
        self.assertEqual(len(cs), 1)
        c = cs[0]
        self.assertEqual(len({x["sel"].split("|")[0] for x in c["patas"]}), len(c["patas"]))   # una por partido
        self.assertTrue(all(1.38 <= x["cuota"] <= 1.70 for x in c["patas"]))
        jug = [x for x in c["patas"] if "Pepe" in x["texto"]]
        self.assertTrue(jug and "cumple 5/6 siendo titular" in jug[0]["dato"] and "(1-2-1-1-0-1)" in jug[0]["dato"])
        self.assertIn("📊", CS.texto_post(c))

    def test_jugador_de_otro_equipo_no_vale(self):
        h = {"pepe uno": [{"nombre": "Pepe Uno", "min": 90, "faltas_c": 2, "eq": "99"}] * 6}
        with mock.patch.object(CS, "equipos_partido", lambda pid: {"10", "20"}):
            self.assertEqual(CS.patas_jugador(partido(1, "15:00"), h), [])

    def test_suplente_no_cuenta(self):
        hj = [{"min": 20, "faltas_c": 0}] * 6 + [{"min": 90, "faltas_c": 1}] * 3
        self.assertIsNone(CS.serie_jugador(hj, "faltas_c", 1))   # solo 3 de titular

    def test_dias(self):
        self.assertEqual(CS.de_hoy(datetime(2026, 11, 20, 10, tzinfo=MADRID)), ("2026-11-21", "2026-11-23"))
        self.assertEqual(CS.de_hoy(datetime(2026, 11, 24, 10, tzinfo=MADRID)), ("2026-11-24", "2026-11-26"))
        self.assertIsNone(CS.de_hoy(datetime(2026, 11, 22, 10, tzinfo=MADRID)))

    def test_boleto_casa_con_la_propuesta(self):
        c = {"liga": "LaLiga", "patas": [{"sel": f"{i}|M|O"} for i in range(5)], "cuota": 7}
        self.assertIs(CS.casa_con(["0|M|O", "1|M|O", "2|M|O", None], [c]), c)
        self.assertIsNone(CS.casa_con(["0|M|O", "9|M|O"], [c]))

    def test_boleto_casa_por_nombres_leidos(self):
        c = {"liga": "LaLiga", "patas": [{"sel": "1|a|b", "texto": "Ville Koski: comete 1+ falta"},
                                          {"sel": "2|a|b", "texto": "Sergio Camello: comete 1+ falta"},
                                          {"sel": "3|a|b", "texto": "Gana Barcelona"}], "cuota": 3}
        self.assertIs(CS.casa_con([], [c], textos=["Koski - Más de 0.5 faltas", "Camello más de 0.5", "Barcelona"]), c)


class SinRepetir(unittest.TestCase):
    """20/11 (Marcos): lo ya subido sale de las combis y se cambia por otra pata del mismo partido."""
    def test_fuera_lo_subido(self):
        h = {"pepe uno": [{"nombre": "Pepe Uno", "min": 90, "faltas_c": v, "eq": "10"} for v in (1, 2, 1, 1, 1, 1)]}
        ps = [partido(i, f"{12 + i}:00") for i in range(5)]
        with mock.patch.object(CS, "equipos_partido", lambda pid: {"10", "20"}):
            antes = CS.generar("2026-11-21", "2026-11-23", partidos=ps, h=h)[0]
            quitada = antes["patas"][0]["sel"]
            despues = CS.generar("2026-11-21", "2026-11-23", partidos=ps, h=h, fuera={quitada})
        sels = {x["sel"] for c in despues for x in c["patas"]}
        self.assertNotIn(quitada, sels)

    def test_poisson(self):
        self.assertAlmostEqual(CS.poisson_al_menos(2.0, 1), 0.8647, places=3)
        self.assertEqual(CS.poisson_al_menos(0, 1), 0.0)
