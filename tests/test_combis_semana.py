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


class CombisDeEquipo(unittest.TestCase):
    """20/11 (Marcos: «un apartado de combis de cada equipo»): solo cosas de ese equipo, sin repetir tipo."""
    def test_solo_cosas_del_equipo(self):
        p = partido(1, "15:00")
        p["cuotas_bet365"].update({"Total - Home": [["Over 0.5", "1.45"]], "Both Teams Score": [["Yes", "1.50"]],
                                   "Double Chance": [["Home/Draw", "1.40"]]})
        h = {"pepe uno": [{"nombre": "Pepe Uno", "min": 90, "faltas_c": 1, "eq": "10"}] * 6}
        teams = {"home": {"id": 10, "name": "L1", "logo": "l.png"}, "away": {"id": 20, "name": "V1"}}
        with mock.patch.object(CS, "equipos_partido", lambda pid: {"10", "20"}), mock.patch.object(CS, "_teams", lambda pid: teams):
            es = CS.generar_equipos("2026-11-21", "2026-11-23", partidos=[p], h=h)
        self.assertEqual([c["equipo"] for c in es], ["L1"])
        c = es[0]
        textos = [x["texto"] for x in c["patas"]]
        self.assertNotIn("Ambos marcan", textos)                           # del partido, no del equipo
        self.assertIn("Pepe Uno: comete 1+ falta", textos)
        self.assertLessEqual(sum(t in ("Gana L1", "L1 o empate") for t in textos), 1)   # un solo resultado
        self.assertEqual(c["logo"], "l.png")
        self.assertIn("COMBI DEL L1", CS.texto_post(c))


class MasMercados(unittest.TestCase):
    """20/11 (Marcos: «quiero más cosas»): más de 1,5, gol en la 2ª parte, quién saca más córners/remates, tarjetas totales."""
    def test_mercados_nuevos(self):
        p = partido(1, "15:00")
        p["stats_local_casa"] = {"gf": 2.2, "gc": 1.0, "gf_2p": 1.3, "gc_2p": 0.6, "o15": "90%", "corners": 7, "corners_c": 3,
                                 "tiros": 17, "tiros_c": 9, "amarillas": 3, "amarillas_c": 3}
        p["stats_visitante_fuera"] = {"gf": 1.2, "gc": 1.8, "gf_2p": 0.7, "gc_2p": 1.1, "o15": "85%", "corners": 3, "corners_c": 6,
                                      "tiros": 9, "tiros_c": 15, "amarillas": 3, "amarillas_c": 3}
        p["cuotas_bet365"] = {"Goals Over/Under": [["Over 1.5", "1.40"]], "Goals Over/Under - Second Half": [["Over 0.5", "1.40"]],
                              "Corners 1x2": [["Home", "1.45"]], "Shots.1x2": [["Home", "1.40"]], "Cards Over/Under": [["Over 3.5", "1.60"]]}
        textos = {x["texto"] for x in CS.patas_equipo(p)}
        for t in ("Más de 1,5 goles", "Gol en la 2ª parte", "L1 saca más córners", "L1 remata más que el rival",
                  "Más de 3,5 tarjetas en el partido"):
            self.assertIn(t, textos)


class LigasYDestacadas(unittest.TestCase):
    """20/11 (Marcos): solo 5 grandes, europeas, copas y selecciones; si no hay nada de eso, otras ligas (nunca femenino).
    Destacadas que mezclan ligas sin repetir partido entre ellas."""
    def test_solo_grandes_si_hay(self):
        ps = [partido(1, "15:00", "LaLiga"), partido(2, "16:00", "Segunda División"), partido(3, "17:00", "Liga F")]
        self.assertEqual(CS.ligas_elegidas(ps, "2026-11-21", "2026-11-21"), ["LaLiga"])
        self.assertEqual(CS.ligas_elegidas(ps[1:], "2026-11-21", "2026-11-21"), ["Segunda División"])   # sin grandes: otras, sin Liga F

    def test_destacadas_sin_repetir_partido(self):
        h = {"pepe uno": [{"nombre": "Pepe Uno", "min": 90, "faltas_c": 1, "eq": "10"}] * 6}
        ps = [partido(i, f"{12 + i}:00", liga) for i, liga in enumerate(["LaLiga", "Serie A", "Premier League", "Bundesliga",
                                                                        "Ligue 1", "LaLiga", "Serie A", "Premier League"])]
        for p in ps:
            p["cuotas_bet365"]["Total - Home"] = [["Over 0.5", "1.45"]]
        with mock.patch.object(CS, "equipos_partido", lambda pid: {"10", "20"}), mock.patch.object(CS, "_teams", lambda pid: {}):
            ds = CS.generar_destacadas("2026-11-21", "2026-11-23", partidos=ps, h=h)
        self.assertTrue(ds and ds[0]["clave"] == "todas")
        self.assertGreater(len({x["liga"] for x in ds[0]["patas"]}), 1)          # mezcla ligas
        sels = [x["sel"] for c in ds for x in c["patas"]]
        self.assertEqual(len(sels), len(set(sels)))                                # ningún pick en dos destacadas
        for c in ds:
            ids = [x["sel"].split("|")[0] for x in c["patas"]]
            self.assertEqual(len(ids), len(set(ids)))                              # un partido una vez por combi
            self.assertTrue(0 < c["prob"] <= 1)


class QuienGana(unittest.TestCase):
    """20/11 (Marcos: «otra de quién gana»): favoritos de @1,20 a @1,80, solo en su combi."""
    def test_favorito(self):
        p = partido(1, "15:00")
        p["stats_local_casa"] = {"gf": 2.4, "gc": 0.8, "forma": "VVVVE"}
        p["stats_visitante_fuera"] = {"gf": 0.8, "gc": 2.0, "forma": "DDEDV"}
        p["cuotas_bet365"] = {"Match Winner": [["Home", "1.30"], ["Away", "9.00"]]}
        ps = CS.patas_ganador(p)
        self.assertEqual([x["texto"] for x in ps], ["Gana L1"])
        p["cuotas_bet365"] = {"Match Winner": [["Home", "1.10"]]}
        self.assertEqual(CS.patas_ganador(p), [])           # demasiado baja
