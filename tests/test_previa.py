import unittest
from datetime import datetime
from unittest import mock

import datos_futbol as d
from bot import MADRID


def pa(i, loc, vis):
    return {"id": i, "inicio": datetime(2026, 10, 27, 20, 45, tzinfo=MADRID), "liga": "Serie A",
            "local": {"id": i * 10, "name": loc}, "visitante": {"id": i * 10 + 1, "name": vis}, "h2h": []}


class Previa(unittest.TestCase):
    def test_sale_a_las_23_de_la_vispera(self):
        with mock.patch.object(d, "partidos_del_dia", return_value=[pa(1, "AS Roma", "Cagliari"), pa(2, "Torino", "Como")]), \
                mock.patch.object(d, "dato_partido", return_value="Dato."):
            tipo, hora, texto = d.previa("2026-10-27", hist={})
        self.assertEqual((tipo, hora.strftime("%Y-%m-%dT%H:%M")), ("datos-manana", "2026-10-26T23:00"))
        self.assertIn("Roma – Cagliari", texto)
        self.assertNotIn("apuesta", texto.lower())

    def test_con_un_partido_no_sale(self):
        with mock.patch.object(d, "partidos_del_dia", return_value=[pa(1, "Torino", "Como")]), \
                mock.patch.object(d, "dato_partido", return_value="Dato."):
            self.assertIsNone(d.previa("2026-10-27", hist={}))

    def test_articulo(self):
        self.assertEqual(d.el("AS Roma"), "La Roma")
        self.assertEqual(d.el("Inter", False), "el Inter")


if __name__ == "__main__":
    unittest.main()
