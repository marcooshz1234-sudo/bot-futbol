"""13/11 (Marcos: «vamos a mejorar los picks y hacerlos más seguros: patas de máximo 1,8»; y las cuotazas: hasta
2,20 y solo de 9:00 a 23:00 — la de ambos marcan Andorra–Gibraltar @3,25 salió a las 3 de la mañana)."""
import unittest
from datetime import datetime
from unittest import mock

import cazador
import comprobar_post as CP
import escalera
from bot import MADRID


class PatasMax(unittest.TestCase):
    def test_comprobar_post_pata_alta(self):
        p = {"id": "2026-11-13-combi-tres", "texto": "x", "sel": [], "cuotas": [1.44, 1.83]}
        with mock.patch.object(CP, "partido_caido", lambda p: None), mock.patch.object(CP, "cuota_baja", lambda *a: None):
            self.assertIn("cuota_alta", [r for r, _ in CP.comprobar(p, otros={})])
            self.assertNotIn("cuota_alta", [r for r, _ in CP.comprobar(dict(p, cuotas=[1.44, 1.80]), otros={})])
            # las copias de canales y los ganadores, no
            self.assertNotIn("cuota_alta", [r for r, _ in CP.comprobar(dict(p, id="2026-11-13-pick-tip-1"), otros={})])
            self.assertNotIn("cuota_alta", [r for r, _ in CP.comprobar(dict(p, id="2026-11-13-ganadores-x"), otros={})])

    def test_escalera_se_rehace(self):
        self.assertTrue(escalera.pata_alta({"picks": [{"cuota": 1.83}]}))
        self.assertFalse(escalera.pata_alta({"picks": [{"cuota": 1.36}, {"cuota": 1.36}]}))

    def test_cazador(self):
        self.assertEqual(cazador.CUOTA_MAX, 2.20)
        self.assertEqual(cazador.HORAS, (9, 23))
        self.assertFalse(cazador.HORAS[0] <= datetime(2026, 11, 13, 3, 0, tzinfo=MADRID).hour < cazador.HORAS[1])


if __name__ == "__main__":
    unittest.main()
