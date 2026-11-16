"""16/11 (Marcos: «no siempre solo quién gana, quiero más cosas… si es muy probable y está a 1,50-1,70, para
adelante»): el pick del día también puede ser de córners o tarjetas de un equipo, nunca un mercado prohibido, y los
dos picks del día son de tipos distintos."""
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import combis_dia as C  # noqa: E402

DIA = "2099-06-01"


def pk(pid, mercado, opcion, cuota, prob, texto):
    return {"partido_id": pid, "fecha": f"{DIA}T20:45", "mercado": mercado, "opcion": opcion, "cuota": cuota,
            "prob_aprendida": prob, "texto": texto, "tipo": "resultado"}


GANA = pk(1, "Match Winner", "Home", 1.57, 0.70, "Gana Eslovenia")
GANA2 = pk(2, "Match Winner", "Away", 1.60, 0.69, "Gana Grecia")
CORNERS = pk(3, "Home Corners Over/Under", "Over 4.5", 1.62, 0.66, "Alemania más de 4,5 córners")
TARJETAS_TOTAL = pk(4, "Cards Over/Under", "Over 3.5", 1.55, 0.80, "Más de 3,5 tarjetas")


class PickVariado(unittest.TestCase):
    def _pick(self, pools, segundo=False):
        with mock.patch.object(C, "pick_de_tipster", lambda *a, **k: None), \
                mock.patch.object(C, "pick_de_copa", lambda *a, **k: None), \
                mock.patch.object(C, "minimo_diario", lambda: False):
            r = C.pick_seguro(pools, DIA, segundo=segundo)
        return r[0]["texto"] if r else None

    def test_corners_puede_ser_pick_del_dia(self):
        self.assertEqual(self._pick([[CORNERS]]), "Alemania más de 4,5 córners")

    def test_nunca_tarjetas_totales(self):
        self.assertIsNone(self._pick([[TARJETAS_TOTAL]]))

    def test_el_segundo_no_es_otro_gana(self):
        # el primero fue «gana»: el segundo no puede ser otro «gana» aunque sea más probable
        self.assertEqual(self._pick([[GANA2, CORNERS]], segundo=GANA), "Alemania más de 4,5 córners")

    def test_el_segundo_sin_otro_tipo_no_repite_gana(self):
        self.assertIsNone(self._pick([[GANA2]], segundo=GANA))

    def test_tipo_pick(self):
        self.assertEqual(C.tipo_pick(GANA), "resultado")
        self.assertEqual(C.tipo_pick(CORNERS), "corners")
        self.assertEqual(C.tipo_pick({"mercado": "Both Teams Cards", "opcion": "Yes"}), "tarjetas")


if __name__ == "__main__":
    unittest.main()
