import unittest
from unittest import mock

import picks


def reg(t):
    return {"tiros": t, "a_puerta": 0, "min": 90}


class TirosContexto(unittest.TestCase):
    def _picks(self, ganar_local, tiros):
        prox = {"partido": {"teams": {"home": {"id": 1, "name": "Pequeño"}, "away": {"id": 2, "name": "Grande"}}},
                "cuotas": {"Match Winner": [["Home", str(ganar_local)], ["Draw", "4"], ["Away", "1.4"]],
                           "Home Player Shots": [["Juan Perez - 1", "1.30"]]}}
        fijos = {"home": {9: {"nombre": "Juan Perez", "pos": "M", "partidos": [reg(t) for t in tiros]}}, "away": {}}
        with mock.patch.object(picks, "plantilla_fija", side_effect=lambda eq, h: fijos["home"] if eq == 1 else {}):
            return picks.picks_jugadores(prox, {}, {"partido_id": 5})

    def test_equipo_victima_sin_tiros(self):
        self.assertEqual(self._picks(9.5, [2, 2, 3, 2, 2, 3, 2, 2]), [])

    def test_favorito_y_tirador_si(self):
        self.assertEqual(len(self._picks(1.8, [2, 2, 3, 2, 2, 3, 2, 2])), 1)

    def test_media_baja_no(self):
        self.assertEqual(self._picks(1.8, [1, 1, 1, 1, 1, 1, 1, 0]), [])


if __name__ == "__main__":
    unittest.main()
