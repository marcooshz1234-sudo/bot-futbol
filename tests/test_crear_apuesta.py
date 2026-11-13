"""13/11 (Marcos: «no me des estimaciones, quiero que aprendas a calcularlo»): calculadora del «Crear apuesta»."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import crear_apuesta as CA

# cuotas de bet365 del Serbia–Alemania (13/11), las que hacen falta
C = {"Match Winner": [["Home", "8.50"], ["Draw", "6.25"], ["Away", "1.28"]],
     "Total - Home": [["Over 0.5", "1.62"], ["Under 0.5", "2.20"], ["Over 1.5", "4.00"], ["Under 1.5", "1.22"]],
     "Total - Away": [["Over 0.5", "1.05"], ["Under 0.5", "11.00"], ["Over 1.5", "1.28"], ["Under 1.5", "3.50"],
                      ["Over 2.5", "1.83"], ["Under 2.5", "1.83"]],
     "Away Player Shots": [["Florian Wirtz - 3", "1.33"]],
     "Player to Score or Assist": [["Florian Wirtz", "1.44"]],
     "Away Corners Over/Under": [["Over 6.5", "1.83"], ["Under 6.5", "1.83"]]}
SEL = ["1|Match Winner|Away", "1|Total - Away|Over 1.5", "1|Away Player Shots|Florian Wirtz - 3",
       "1|Player to Score or Assist|Florian Wirtz"]


class CrearApuesta(unittest.TestCase):
    def test_alemania_como_bet365(self):   # multiplicando 3,14; bet365 1,95
        r = CA.calcular(SEL, [1.28, 1.28, 1.33, 1.44], C)
        self.assertAlmostEqual(r["mult"], 3.138, places=2)
        self.assertTrue(1.75 <= r["cuota_modelo"] <= 2.10, r)

    def test_suelta_no_cambia(self):   # goles de Alemania + córners de Alemania: casi multiplicar
        r = CA.calcular(["1|Total - Away|Over 1.5", "1|Away Corners Over/Under|Over 6.5"], [1.28, 1.83], C)
        self.assertEqual(r["sueltas"], 1)
        self.assertAlmostEqual(r["cuota_modelo"], 2.34, places=1)

    def test_en_contra_paga_mas(self):   # gana Alemania + Serbia marca: van en contra → más que multiplicar
        r = CA.calcular(["1|Match Winner|Away", "1|Total - Home|Over 0.5"], [1.28, 1.62], C)
        self.assertGreater(r["cuota_modelo"], r["mult"])

    def test_se_guarda_y_aprende(self):
        with tempfile.TemporaryDirectory() as d:
            prox = Path(d, "proximos")
            prox.mkdir()
            (prox / "1.json").write_text(json.dumps({"cuotas": C}))
            with mock.patch.object(CA, "DATOS", Path(d)), mock.patch.object(CA, "MEDIDAS", Path(d, "m.json")):
                m = CA.guardar_medida("x", SEL, [1.28, 1.28, 1.33, 1.44], 1.95)
                self.assertEqual(m["real"], 1.95)
                self.assertIn("Match Winner", m["mercados"])   # con las cuotas del partido de ese momento
                self.assertIsNone(CA.guardar_medida("x", SEL, [1.28, 1.28, 1.33, 1.44], 1.95))   # no repite
                self.assertNotEqual(CA.sesgo(), 0.0)


class Aprende(unittest.TestCase):
    def test_margen_por_pata(self):   # 13/11 Escocia–Macedonia: 7 patas, multiplicando 9,03, bet365 6,25
        ms = [{"sel": ["x"] * 2, "R": 1.0, "mult": 2.342, "real": 2.65},
              {"sel": ["x"] * 4, "R": 1.677, "mult": 3.138, "real": 1.95},
              {"sel": ["x"] * 7, "R": 1.76, "mult": 9.029, "real": 6.25}]
        a, k = CA.parametros(ms)
        self.assertGreater(a, 1.0)          # cada pata suma un poco: bet365 quita margen pata a pata
        self.assertTrue(0.7 < k < 1.4, k)
        self.assertAlmostEqual(CA.parametros([])[0], 1.0)   # sin medidas: no inventa


class SinScipy(unittest.TestCase):
    def test_sin_scipy(self):   # 13/11: en GitHub no está scipy (fallaron los tests y calibrar_crear en el bucle)
        raiz = Path(__file__).resolve().parent.parent
        for f in raiz.glob("*.py"):
            if f.name != "preparar_logo.py":   # herramienta a mano, en el ordenador de Marcos
                self.assertNotRegex(f.read_text(encoding="utf-8"), r"(?m)^\s*(from scipy|import scipy)", f.name)


if __name__ == "__main__":
    unittest.main()
