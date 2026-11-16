"""16/11 (Marcos): contenido constante en Threads (cada 30 min de día, cada hora de madrugada), combis locas por 50,
100, 500 y 1000, listas y tiros de jugadores habituales. Solo Threads, sin porqué, con las normas de siempre."""
import unittest
from datetime import datetime

import threads_locas as T


class ThreadsLocas(unittest.TestCase):
    def test_huecos(self):
        from bot import MADRID
        h = T.huecos("2026-11-16", datetime(2026, 11, 16, 0, 0, tzinfo=MADRID))
        horas = [x.strftime("%H:%M") for x in h]
        self.assertIn("03:00", horas)
        self.assertNotIn("03:30", horas)        # de madrugada, cada hora
        self.assertIn("12:30", horas)           # de día, cada media hora
        self.assertEqual(horas[-1], "00:30")    # hasta la 01:00

    def test_combi_cuota_respeta_patas(self):
        from bot import MADRID
        ini = datetime(2026, 11, 16, 20, 45, tzinfo=MADRID)
        partidos = [{"fid": i, "ini": ini, "local": f"L{i}", "visitante": f"V{i}", "local_en": "x", "patas": [
            {"mercado": "Match Winner", "opcion": "Home", "cuota": 1.5, "prob": 0.62, "familia": "gana", "texto": "Gana L"},
            {"mercado": "Both Teams Score", "opcion": "Yes", "cuota": 1.6, "prob": 0.58, "familia": "ambos", "texto": "Ambos marcan"},
            {"mercado": "Total - Home", "opcion": "Over 0.5", "cuota": 1.3, "prob": 0.7, "familia": "marca", "texto": "L marca"},
            {"mercado": "Corners 1x2", "opcion": "Home", "cuota": 1.45, "prob": 0.6, "familia": "corners", "texto": "L más córners"}]}
            for i in range(8)]
        sel, cuota, misma = T.combi_cuota(partidos, 100, "s", set())
        self.assertGreaterEqual(cuota, 60)
        for fid in {pt["fid"] for pt, _ in sel}:
            fams = {p["familia"] for pt, p in sel if pt["fid"] == fid}
            self.assertFalse({"ambos", "marca"} <= fams)   # no van juntas en el mismo partido

    def test_texto_sin_partido_repetido(self):
        pt = {"local": "Alemania", "visitante": "Países Bajos"}
        self.assertEqual(T._corto(pt, {"texto": "Ambos marcan en Alemania–Países Bajos"}), "Ambos marcan")


if __name__ == "__main__":
    unittest.main()
