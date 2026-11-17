"""17/11 (Marcos): verdes de Telegram uno a uno cada 10 min (no juntos); en Threads solo combis de x5 o más
(también las locas); y nunca más un pick de tarjetas en Telegram."""
import unittest
from datetime import datetime
from unittest import mock

import comprobar_post as C
import combis_dia as CD
import redes as R
import verdes_auto as V
from bot import MADRID


def verde(i, fecha, **k):
    return {"id": f"2026-11-17-verde-auto-{i}", "fecha": fecha, "resultado": "verde", "verde_de": i, **k}


class Escalonar17Nov(unittest.TestCase):
    def setUp(self):
        self.ahora = datetime(2026, 11, 17, 22, 40, tzinfo=MADRID)

    def test_uno_cada_10_min(self):
        cola = [verde("a", "2026-11-17T22:40"), verde("b", "2026-11-17T22:40"), verde("c", "2026-11-17T22:41")]
        with mock.patch.object(V, "leer", return_value={}):
            V.escalonar(cola, self.ahora)
        self.assertEqual([p["fecha"] for p in cola], ["2026-11-17T22:40", "2026-11-17T22:50", "2026-11-17T23:00"])

    def test_cuenta_el_que_ya_salio(self):
        cola = [verde("a", "2026-11-17T22:35", enviado="2026-11-17T22:36", mensaje_id=1),
                verde("b", "2026-11-17T22:40")]
        with mock.patch.object(V, "leer", return_value={}):
            V.escalonar(cola, self.ahora)
        self.assertEqual(cola[1]["fecha"], "2026-11-17T22:46")

    def test_solo_threads_no_cuenta(self):
        cola = [verde("a", "2026-11-17T22:40"), verde("b", "2026-11-17T22:40", solo_en=["threads"])]
        with mock.patch.object(V, "leer", return_value={}):
            V.escalonar(cola, self.ahora)
        self.assertEqual(cola[1]["fecha"], "2026-11-17T22:40")

    def test_ya_no_se_agrupan(self):
        src = open(V.__file__, encoding="utf-8").read()
        self.assertIn("escalonar(cola, ahora)", src)
        self.assertNotIn("        agrupar(cola, ahora)", src)


class ThreadsX5(unittest.TestCase):
    def test_x5_si_y_menos_no(self):
        self.assertFalse(R.resultado_sin_cuoton({"id": "2026-11-17-verde-auto-a", "resultado": "verde",
                                                 "texto": "PARA DENTRO ✅\n📈 Cuota @5,20"}))
        self.assertTrue(R.resultado_sin_cuoton({"id": "2026-11-17-verde-auto-a", "resultado": "verde",
                                                "texto": "PARA DENTRO ✅\n📈 Cuota @4,80"}))

    def test_locas_de_threads_cuentan_como_combi(self):
        src = open(V.__file__, encoding="utf-8").read()
        self.assertIn('-loca-th-', src)


class SinTarjetas17Nov(unittest.TestCase):
    def test_pick_de_tarjetas_bloqueado(self):
        p = {"id": "2026-11-18-pick-seguro", "texto": "🍀 Polonia ve más de 1,5 tarjetas @1,60\n\n⚽ Polonia – Suecia · hoy"}
        self.assertTrue(C.pick_tarjetas_tg(p))

    def test_copia_de_tipster_bloqueada(self):
        p = {"id": "2026-11-18-pick-tip-1", "origen": "tipster", "texto": "🍀 Más de 4,5 tarjetas @1,70"}
        self.assertTrue(C.pick_tarjetas_tg(p))

    def test_otros_picks_y_combis_si(self):
        self.assertIsNone(C.pick_tarjetas_tg({"id": "2026-11-18-pick-seguro", "texto": "🍀 Gana Polonia @1,60"}))
        self.assertIsNone(C.pick_tarjetas_tg({"id": "2026-11-18-combi-tres", "texto": "🍀 Más de 3,5 tarjetas"}))
        self.assertIsNone(C.pick_tarjetas_tg({"id": "2026-11-18-pick-seguro", "solo_en": ["threads"],
                                              "texto": "🍀 Más de 3,5 tarjetas"}))

    def test_el_modelo_no_las_elige(self):
        self.assertIn("tarjetas", CD.SEGURO["no_tipos"])


if __name__ == "__main__":
    unittest.main()
