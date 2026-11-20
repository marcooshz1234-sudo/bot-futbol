import unittest
import combis_dia
import publicar_telegram as PT


class TelegramSinCombis(unittest.TestCase):
    """20/11 (Marcos: «no quiero combis en Telegram a no ser que te la pida o la suba yo; entre 7 y 11 picks al día»)."""
    def test_combi_bloqueada(self):
        p = {"id": "2026-11-21-estrella-1", "fecha": "2026-11-21T19:55", "sel": ["1|a|b", "1|c|d"], "cuotas": [1.5, 1.4]}
        self.assertIn("solo picks sueltos", PT.combi_no_pedida(p))

    def test_pasan_sueltos_pedidas_y_lo_suyo(self):
        base = {"fecha": "2026-11-21T12:00", "sel": ["1|a|b", "2|a|b"], "cuotas": [1.5, 1.4]}
        self.assertIsNone(PT.combi_no_pedida(dict(base, id="2026-11-21-pick-seguro-3", sel=["1|a|b"], cuotas=[1.5])))
        self.assertIsNone(PT.combi_no_pedida(dict(base, id="2026-11-21-combi-x", pedida=True)))
        self.assertIsNone(PT.combi_no_pedida(dict(base, id="2026-11-21-boleto-personal")))
        self.assertIsNone(PT.combi_no_pedida(dict(base, id="2026-11-21-verde-auto-x")))
        self.assertIsNone(PT.combi_no_pedida(dict(base, id="2026-11-20-combi-tres", fecha="2026-11-20T12:00")))   # lo de antes no se toca

    def test_hasta_11_picks(self):
        # pick del día + el de las 18:00 + escalera + extras = 11 como mucho, mínimo 7
        self.assertEqual(3 + len(combis_dia.EXTRA_PICKS["horas"]), 11)
        self.assertEqual(combis_dia.EXTRA_PICKS["minimo_tg"], 7)


if __name__ == "__main__":
    unittest.main()
