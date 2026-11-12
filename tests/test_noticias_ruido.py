"""12/11: noticias de otros deportes (rugby) salían en el partido de fútbol Italia–Francia."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import noticias


def ruido(titulo, fuente=""):
    return bool(re.search(noticias.RUIDO, noticias.norm(titulo + " · " + fuente)))


class TestRuido(unittest.TestCase):
    def test_otros_deportes(self):
        self.assertTrue(ruido("Con cinco cambios, y más bajas, Los Pumas tienen a su equipo confirmado para enfrentar a Italia",
                              "Rugby Champagne"))
        self.assertTrue(ruido("Italia gana en el Seis Naciones", "Rugby Champagne"))
        self.assertTrue(ruido("Francia arrolla en el Eurobasket de baloncesto"))

    def test_futbol_vale(self):
        self.assertFalse(ruido("Mbappé no jugará contra Italia en la Nations League", "Yahoo Sports"))
        self.assertFalse(ruido("Tchouaméni, lesionado, causa baja con Francia", "www.abc.com.py"))


if __name__ == "__main__":
    unittest.main()
