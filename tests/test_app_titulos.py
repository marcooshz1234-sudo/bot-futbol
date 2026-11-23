"""23/11 (Marcos: «quiero que la app sea profesional»): en la app, el título de un post es lo que se apuesta y
lleva su cuota (antes salían «Vamos con otro pick, familia» y «@—»)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app_datos as A  # noqa: E402


class Titulos(unittest.TestCase):
    def test_titulo_es_el_pick(self):
        t = "Vamos con otro pick, familia 👇\n🧠 Pensada con calma\n\n🍀 Gana el Real Madrid @1,53\n\n⚽ Real Madrid – PSV"
        self.assertEqual(A.titulo_de(t), "Gana el Real Madrid")
        self.assertEqual(A.titulo_de("Empezamos el día con este pick\n🍀 Poland ve más de 1,5 tarjetas @1,67"),
                         "Polonia ve más de 1,5 tarjetas")
        self.assertEqual(A.titulo_de("🧨 COMBI POR 104 🧨\n🍀 a @1,5\n🍀 b @2"), "🧨 COMBI POR 104 🧨")   # los títulos de verdad, igual
        self.assertEqual(A.titulo_de("Os dejo el pick\n🍀 a @1,5\n🍀 b @2"), "Combi de 2 picks")


if __name__ == "__main__":
    unittest.main()
