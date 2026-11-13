"""13/11 (Marcos: «los de baloncesto también, pero solo cuando te los pida me los das; nada de subirlos al canal»)."""
import unittest

import copiar_tipsters as C


class BaloncestoNoSeSube(unittest.TestCase):
    def test_canales_de_basket_y_tenis_no_se_copian(self):
        for t in ("TipsAnalistasNBA🏀", "MisterBasquet 🏀", "INSIDER Tenis"):
            self.assertFalse(C.es_de_futbol(t), t)
        self.assertTrue(C.es_de_futbol("TipsAnalistas"))


if __name__ == "__main__":
    unittest.main()
