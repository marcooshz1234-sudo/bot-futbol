import unittest
import plantillas


class CierreSinCombis(unittest.TestCase):
    """24/11: en Telegram ya no hay combis (Marcos 20/11): el cierre no puede decir «que vienen más combis»."""
    def test_cierre(self):
        self.assertNotIn("combis", plantillas.CIERRE_TELEGRAM)


if __name__ == "__main__":
    unittest.main()
