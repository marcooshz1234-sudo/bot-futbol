"""23/11 (Marcos: «arréglalo en todos los tipos de apuestas; en Threads, aparte de las cuotas grandes, que las
respalden un poco los datos»): ninguna pata de Threads entra si los datos no la respaldan."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import threads_locas as T  # noqa: E402

EX = {"partido": {"fixture": {"id": 1}, "teams": {"home": {"id": 10}, "away": {"id": 20}}},
      "cuotas": {"Both Teams Score": [["Yes", "1.60"]], "Match Winner": [["Home", "2.50"]],
                 "Player Fouls Committed": [["Pepe - 1", "1.50"]], "Anytime Goal Scorer": [["Goleador", "3.00"]],
                 "Rare Market": [["X", "2.0"]]}}


def partido(gl, gv):   # el equipo «eq» es siempre el local de su partido pasado
    return {"goles": [gl, gv], "local": {"id": 0}, "visitante": {"id": 0}}


class Respaldo(unittest.TestCase):
    def setUp(self):
        T._RESP.clear(); T._HIST.clear()
        self.p = [mock.patch.object(T, "_ex", return_value=EX), mock.patch.object(T, "_hist", return_value={10: [], 20: []})]
        for x in self.p:
            x.start()

    def tearDown(self):
        for x in self.p:
            x.stop()

    def test_equipos_por_frecuencia(self):
        import picks as P
        si = lambda f, h: (8, 10)   # 80 % los dos: respalda «ambos marcan» @1,60 (59 %)
        with mock.patch.object(P, "frecuencia", side_effect=si), mock.patch.object(P, "evaluador", return_value=lambda p, e: True):
            self.assertTrue(T.respaldado(1, "Both Teams Score", "Yes"))
        T._RESP.clear()
        no = iter([(3, 10), (2, 10)])   # 25 %: no llega a lo que dice la cuota @2,50 (38 %)
        with mock.patch.object(P, "frecuencia", side_effect=lambda f, h: next(no)), mock.patch.object(P, "evaluador", return_value=lambda p, e: True):
            self.assertFalse(T.respaldado(1, "Match Winner", "Home"))

    def test_sin_datos_no(self):
        import picks as P
        with mock.patch.object(P, "evaluador", return_value=None):
            self.assertFalse(T.respaldado(1, "Rare Market", "X"))

    def test_jugadores(self):
        with mock.patch.object(T, "frec_jugador", return_value=0.7):
            self.assertTrue(T.respaldado(1, "Player Fouls Committed", "Pepe - 1"))
        T._RESP.clear()
        with mock.patch.object(T, "frec_jugador", return_value=None):
            self.assertFalse(T.respaldado(1, "Player Fouls Committed", "Pepe - 1"))
        T._RESP.clear()
        with mock.patch.object(T, "frec_jugador", return_value=0.2):   # @3,00 → necesita 31 %
            self.assertFalse(T.respaldado(1, "Anytime Goal Scorer", "Goleador"))

    def test_libre_lo_usa(self):
        with mock.patch.object(T, "respaldado", return_value=False):
            self.assertFalse(T.libre(1, "Both Teams Score", "Yes", {}))


if __name__ == "__main__":
    unittest.main()
