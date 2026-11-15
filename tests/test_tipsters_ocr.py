import unittest
from unittest import mock
from datetime import datetime
import tipsters_auto as T
from bot import MADRID

CANDS = [(1, datetime(2026, 11, 15, 20, 45, tzinfo=MADRID), "Spain", "England"),
         (2, datetime(2026, 11, 15, 20, 45, tzinfo=MADRID), "France", "Türkiye")]


class BoletoOCR(unittest.TestCase):
    """15/11 (Marcos): los picks que vienen solo en la foto (boleto) también se leen."""
    def analiza(self, ocr):
        with mock.patch.object(T, "texto_foto", lambda r: ocr):
            return T.analizar_post("X", {"id": "a", "texto": "", "foto_ruta": "f.jpg"}, CANDS)

    def test_boleto_claro(self):
        r = self.analiza("© Francia 1.22\nResultado final\nEspaña Dom 15 nov\nImp: 10,00€ Ganancias 12,20€")
        self.assertEqual([(x["partido_id"], x["mercado"], x["opcion"], x["cuota"]) for x in r], [(2, "Match Winner", "Home", 1.22)])

    def test_remates_no_son_goles(self):
        r = self.analiza("© Inglaterra - Mas de 3.5 1.80\n\nEquipo visitante - Remates a puerta\nEspana Dom 15 nov\nImp: 300,00€")
        self.assertEqual(r, [])

    def test_importes_no_son_cuotas(self):
        self.assertEqual(T.lineas_boleto("Imp: 1.000,00 €\nGanancias potenciales 2.300,00 €"), [])
