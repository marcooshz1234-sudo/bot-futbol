import unittest
from datetime import datetime
import combis_personales as C
from bot import MADRID


def partido(i, hora, gana="1.50", btts="1.70"):
    return {"id": i, "fecha": f"2026-11-15T{hora}:00+01:00", "local": f"Equipo{i}", "visitante": f"Rival{i}",
            "stats_local": {"forma": "VVVDE", "btts": "60%"}, "stats_visitante": {"forma": "DDDVE", "btts": "60%"},
            "cuotas_bet365": {"Match Winner": [["Home", gana], ["Away", "5"]], "Both Teams Score": [["Yes", btts]]}}


class Personales(unittest.TestCase):
    def test_dos_combis_sin_compartir_partido(self):
        ps = [partido(i, f"{14 + i // 2:02d}:{(i % 2) * 30:02d}") for i in range(14)]
        desde = datetime(2026, 11, 15, 13, 0, tzinfo=MADRID)
        a, b = C.montar(ps, desde, set(), 0), C.montar(ps, desde, set(), 1)
        self.assertTrue(a and b)
        ids = lambda pt: {x["sel"].split("|")[0] for x in pt}
        self.assertFalse(ids(a) & ids(b))
        self.assertIn("SEGUNDA", C.texto_post(b, segunda=True)); self.assertNotIn("MI ", C.texto_post(a))

    def test_pocos_partidos_no_sale(self):
        ps = [partido(i, "18:00") for i in range(5)]
        self.assertIsNone(C.montar(ps, datetime(2026, 11, 15, 13, 0, tzinfo=MADRID), set(), 0))
