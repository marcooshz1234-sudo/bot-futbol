import unittest

import aprender
from picks import aplicar_aprendizaje


from datetime import datetime as _dt
HOY = _dt.now().strftime("%Y-%m-%dT15:00")   # 29/10: fecha de hoy (con una fija el test caducaba al pesar menos lo antiguo)


def pick(i, ok, tipo="goles", cuota=1.3, frec=0.85, partido=None):
    return {"partido_id": partido or i, "fecha": HOY, "competicion": "Ligue 1", "tipo": tipo,
            "mercado": "Goals Over/Under", "opcion": "Over 1.5", "cuota": cuota, "frecuencia": frec, "acierto": ok,
            "local": "A", "visitante": "B", "texto": "x"}


class TestAprender(unittest.TestCase):
    def setUp(self):
        aprender._CAL["c"] = {}   # los tests no dependen del histórico real

    def test_calibracion_baja_lo_que_exagera(self):
        cal = {"global": {"real": 0.7, "frec_media": 0.76, "pendiente": 0.6, "n": 1000},
               "tipos": {"jugador:a_puerta": {"real": 0.49, "frec_media": 0.75, "pendiente": 0.7, "n": 264}},
               "mercados": {}}
        p = dict(pick(1, None), tipo="jugador", campo="a_puerta", n=1, frecuencia=0.75)
        self.assertAlmostEqual(aprender.frec_calibrada(p, cal), 0.49, places=2)

    def test_sin_datos_no_cambia(self):
        p = [pick(1, None)]
        self.assertEqual(aplicar_aprendizaje(p, {}), p)

    def test_lo_que_falla_mucho_deja_de_salir(self):
        reg = [pick(i, i % 3 == 0) for i in range(120)]          # acierta 33 % con cuota 1,30 (77 %)
        ap = aprender.calibrar(reg)
        self.assertLess(ap["tipos"]["goles"]["ajuste"], 0)
        self.assertEqual(aplicar_aprendizaje([pick(999, None)], ap), [])

    def test_lo_que_acierta_sube(self):
        reg = [pick(i, True) for i in range(60)]
        ap = aprender.calibrar(reg)
        p = aplicar_aprendizaje([pick(999, None)], ap)
        self.assertEqual(len(p), 1)
        self.assertGreater(p[0]["prob_aprendida"], 1 / 1.3)

    def test_mismo_partido_cuenta_como_uno(self):
        reg = [pick(i, False, partido=7) for i in range(10)]
        ap = aprender.calibrar(reg)
        self.assertAlmostEqual(ap["tipos"]["goles"]["partidos"], 1.0, places=1)


if __name__ == "__main__":
    unittest.main()
