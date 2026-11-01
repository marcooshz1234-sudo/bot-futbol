import json
import math
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import app_datos
import mis_datos
from bot import MADRID

FINAL = {"id": 7, "estado": "FT", "local": {"id": 1, "nombre": "Local"}, "visitante": {"id": 2, "nombre": "Visitante"},
         "goles": [2, 1], "stats": {}}


class MisDatosTest(unittest.TestCase):
    def generar(self, combis, conf=None, dias=None):
        with tempfile.TemporaryDirectory() as td:
            entrada, salida = Path(td) / "mis_combis.json", Path(td) / "mis" / "datos.json"
            entrada.write_text(json.dumps(combis))
            with patch.object(mis_datos, "ENTRADA", entrada), patch.object(mis_datos, "SALIDA", salida), \
                    patch.object(app_datos, "datos_partido", return_value=FINAL):
                mis_datos.main(datetime(2026, 11, 1, 18, 0, tzinfo=MADRID), conf, {}, [],
                               [dict(FINAL, fecha="2026-11-01T16:00", liga="LaLiga", ficha={"pesada": 1})],
                               dias or {}, "2026-10-31", "2026-11-01", "2026-11-02")
            return json.loads(salida.read_text())

    def test_combi_con_sus_patas_y_sin_dinero(self):
        d = self.generar([{"id": "c1", "fecha": "2026-11-01T16:00", "titulo": "Local – Visitante", "cuota": 3.0,
                           "sel": ["7|Match Winner|Home", "7|Goals Over/Under|Over 3.5"], "cuotas": [1.5, 2.0]}])
        c = d["combis"][0]
        self.assertEqual([p["estado"] for p in c["picks"]], ["verde", "rojo"])
        self.assertEqual(c["estado"], "rojo")
        self.assertEqual(c["picks"][0]["marcador"], [2, 1])
        self.assertNotIn("ficha", d["partidos"][0])   # la ficha pesada no se copia
        self.assertNotIn("importe", json.dumps(d))

    def test_combis_viejas_no_pasan_por_confirmar(self):
        conf = MagicMock()
        conf.pata.side_effect = lambda f: f
        self.generar([{"id": "vieja", "fecha": "2026-10-20T16:00", "sel": ["7|Match Winner|Home"], "cuotas": [1.5]},
                      {"id": "hoy", "fecha": "2026-11-01T16:00", "sel": ["7|Match Winner|Home"], "cuotas": [1.5]}], conf)
        self.assertEqual(conf.pata.call_count, 1)

    def test_combi_sin_sel_se_salta_y_picks_del_bot(self):
        dias = {"2026-11-01": {"picks": [{"partido_id": 7, "fecha": "2026-11-01T16:00", "partido": "Local – Visitante",
                                          "texto": "Gana el Local", "cuota": 1.5, "frecuencia": 80, "pct_real": None,
                                          "estado": "verde"}]}}
        d = self.generar([{"id": "mal", "fecha": "2026-11-01T16:00", "sel": ["7|Match Winner|Home"], "cuotas": []}], dias=dias)
        self.assertEqual(d["combis"], [])
        self.assertEqual(d["picks"][0]["pct"], 80)


class ProbabilidadTest(unittest.TestCase):
    PARTIDO = {"estado": "2H", "goles": [1, 2], "descanso": [0, 1], "local": {"id": 1, "nombre": "Local"},
               "visitante": {"id": 2, "nombre": "Visitante"}, "stats": {"1": {"a_puerta": 3}, "2": {"a_puerta": 7}}}

    def test_verde_roja_y_anulada(self):
        self.assertEqual(mis_datos.prob_pata({"estado": "verde"}, "7|X|Y", 0.5, None), 1.0)
        self.assertEqual(mis_datos.prob_pata({"estado": "rojo"}, "7|X|Y", 0.5, None), 0.0)
        self.assertIsNone(mis_datos.prob_pata({"estado": "anulada"}, "7|X|Y", 0.5, None))
        # «comprobando» cuenta como lo que se está comprobando
        self.assertEqual(mis_datos.prob_pata({"estado": "comprobando", "confirmando": "verde"}, "7|X|Y", 0.5, None), 1.0)

    def test_sin_empezar_usa_la_previa(self):
        self.assertEqual(mis_datos.prob_pata({"estado": "pendiente", "estado_partido": "NS"}, "7|X|Y", 0.62, None), 0.62)

    def test_goles_en_juego_con_poisson(self):
        gana = mis_datos.prob_goles_vivo("Match Winner", "Away", self.PARTIDO, 71, (1.0, 3.0))
        self.assertTrue(0.8 < gana < 0.95)
        # ya se cumplió en la 1ª parte: seguro
        self.assertEqual(mis_datos.prob_goles_vivo("Goals Over/Under First Half", "Over 0.5", self.PARTIDO, 71, None), 1.0)
        # en el 90 no queda nada por marcar
        self.assertAlmostEqual(mis_datos.prob_goles_vivo("Goals Over/Under", "Over 3.5", self.PARTIDO, 90, None), 0.0)
        # lo que no es de goles no se calcula aquí
        self.assertIsNone(mis_datos.prob_goles_vivo("Corners Over Under", "Over 8.5", self.PARTIDO, 71, None))

    def test_ritmo_de_estadisticas(self):
        self.assertEqual(mis_datos.prob_ritmo(5, 4, 30), 1.0)
        self.assertLess(mis_datos.prob_ritmo(19, 31, 71), 0.05)   # 19 tiros al 71: no llega a 31
        self.assertGreater(mis_datos.prob_ritmo(8, 10, 60), 0.5)

    def test_ajuste_con_la_cuota_de_bet365(self):
        c = {"cuota": 8.73, "sel": ["a", "b", "c"]}
        prev = {"a": 0.25, "b": 0.3, "c": 0.3}   # 2,25 % multiplicando; bet365 dice ~10,9 %
        a = mis_datos.ajuste(c, prev)
        self.assertAlmostEqual(math.prod(prev.values()) ** a, 0.95 / 8.73, places=3)
        self.assertEqual(1.0 ** a, 1.0)   # con todo en verde sigue siendo 100 %
        # si el bot la ve mejor que bet365 no se toca, y sin previas tampoco
        self.assertEqual(mis_datos.ajuste({"cuota": 2.0, "sel": ["a"]}, {"a": 0.8}), 1.0)
        self.assertEqual(mis_datos.ajuste({"cuota": 8.0, "sel": ["a", "x"]}, {"a": 0.5}), 1.0)
        # tope: nunca menos del 40 %
        self.assertEqual(mis_datos.ajuste({"cuota": 1.1, "sel": ["a"]}, {"a": 0.01}), mis_datos.AJUSTE_MIN)

    def test_comparacion(self):
        self.assertGreater(mis_datos.prob_comparacion("ShotOnTarget 1x2", "Away", self.PARTIDO, 71), 0.9)


class SustitutoYPluralTest(unittest.TestCase):
    PARTIDO = {"estado": "FT", "goles": [1, 1], "local": {"id": 1, "nombre": "L"}, "visitante": {"id": 2, "nombre": "V"},
               "stats": {"1": {"corners": 1}, "2": {"corners": 0}},
               "jugadores": {"1": [{"nombre": "Ana Uno", "min": 62, "faltas_c": 0, "goles": 0, "asist": 0, "tiros": 1, "paradas": 1},
                                   {"nombre": "Bea Dos", "min": 28, "faltas_c": 1, "goles": 0, "asist": 1, "tiros": 0}]},
               "eventos": [{"tipo": "subst", "min": 62, "jugador": "Ana Uno", "otro": "Bea Dos"}]}

    def test_gol_o_asistencia_cuenta_el_que_entra(self):
        import picks
        pick = {"mercado": "Player to Score or Assist", "opcion": "Ana Uno"}
        self.assertTrue(picks.evaluar_pick(pick, self.PARTIDO))
        self.assertFalse(picks.evaluar_pick(pick, dict(self.PARTIDO, eventos=[])))   # sin cambio, solo cuenta ella

    def test_plural_y_aviso_del_sustituto(self):
        texto = lambda m, o: app_datos.progreso_sel(m, o, dict(self.PARTIDO, estado="2H"))["texto"]
        self.assertEqual(texto("Player Fouls Committed", "Ana Uno - 1"), "1 falta · cumplido ✅ (con Bea Dos, que entró por él)")
        self.assertEqual(texto("Player Shots Total", "Ana Uno - 1"), "1 tiro · cumplido ✅")   # el que entra no aporta
        self.assertEqual(texto("Goalkeeper Saves", "Ana Uno - 2"), "1 de 2 paradas")
        self.assertEqual(texto("Home Corners Over/Under", "Over 0.5"), "1 córner · cumplido ✅")


class TiposTest(unittest.TestCase):
    def test_familias_y_top(self):
        combis = [{"picks": [{"estado": "verde", "sel": "7|Corners Over Under|Over 8.5", "texto": "Más de 8,5 córners en A–B"},
                             {"estado": "rojo", "sel": "7|Goalkeeper Saves|X - 3", "texto": "X: 3+ paradas"},
                             {"estado": "pendiente", "sel": "7|Match Winner|Home", "texto": "Gana el A"}]}]
        apuestas = {"patas": [{"familia": "jugador", "campo": "paradas", "pata": "Y 3+ paradas", "acierto": True}] * 3}
        with tempfile.TemporaryDirectory() as td:
            ruta = Path(td) / "apuestas.json"
            ruta.write_text(json.dumps(apuestas))
            with patch.object(mis_datos, "APUESTAS", ruta):
                t = mis_datos.tipos(combis)
        self.assertEqual(t["total"], 5)   # la pendiente no cuenta
        fam = {x["nombre"]: x for x in t["familias"]}
        self.assertEqual((fam["Jugadores"]["n"], fam["Jugadores"]["aciertos"]), (4, 3))
        self.assertEqual(t["mejor"][0]["nombre"], "Paradas del portero")


if __name__ == "__main__":
    unittest.main()
