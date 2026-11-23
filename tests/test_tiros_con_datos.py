"""23/11 (Marcos: «Varela tira un montón y está a 1,50; Beto apenas tira y está a 1,40, ¿por qué pone a Beto?»):
los tiros de jugador en Threads se elegían solo por la cuota más baja. Ahora mandan sus tiros de verdad."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import threads_locas as T  # noqa: E402

EX = {"partido": {"fixture": {"id": 1}, "teams": {"home": {"id": 10}, "away": {"id": 20}}},
      "cuotas": {"Home Player Shots": [["Varela - 2", "1.45"], ["Varela - 3", "1.50"]],
                 "Away Player Shots": [["Beto - 3", "1.40"], ["Pellegrino - 2", "1.42"]]}}
R = lambda ts: {"partidos": [{"min": 90, "tiros": t} for t in ts]}


def fijos(tid, h):
    if tid == 10:
        return {1: dict(nombre="Varela", **R([5, 1, 6, 2, 2, 0, 2, 2, 2, 3]))}
    return {2: dict(nombre="Pellegrino", **R([4, 2, 2, 1, 1, 0, 4, 1, 3, 2]))}   # Beto: sin datos


class TirosConDatos(unittest.TestCase):
    def setUp(self):
        T._HIST.clear()
        self.p = [mock.patch.object(T, "_ex", return_value=EX), mock.patch("picks.historial", return_value={}),
                  mock.patch("picks.plantilla_fija", side_effect=fijos),
                  mock.patch("picks.mismo_jugador", side_effect=lambda a, b: a == b)]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def test_frecuencias(self):
        self.assertIsNone(T.frec_tiros(1, "Away Player Shots", "Beto", 3))               # sin datos: fuera
        self.assertAlmostEqual(T.frec_tiros(1, "Home Player Shots", "Varela", 3), 0.3)
        self.assertAlmostEqual(T.frec_tiros(1, "Home Player Shots", "Varela", 2), 0.8)

    def test_duelo_elige_por_lo_que_tira(self):
        pt = {"fid": 1, "local": "Monza", "visitante": "Fiorentina", "ini": __import__("datetime").datetime(2026, 11, 23, 20, 45)}
        with mock.patch.object(T, "libre", return_value=True), mock.patch.object(T, "cuota_bet", return_value=2.0), \
             mock.patch.object(T, "_pata", side_effect=lambda pt, m, o, c, t, f: {"texto": t, "cuota": c}):
            sel, _, txt = T.duelo_tiros([pt], 0, set())
        textos = [p["texto"] for _, p in sel]
        self.assertIn("Varela: 2+ tiros", textos)       # 8 de 10, y no el 3+ (3 de 10)
        self.assertIn("Pellegrino: 2+ tiros", textos)   # y no Beto, que no tiene datos
        self.assertNotIn("Beto", txt)


if __name__ == "__main__":
    unittest.main()
