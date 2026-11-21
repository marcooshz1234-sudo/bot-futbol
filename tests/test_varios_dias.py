"""21/11: el boleto de Marcos (sáb–lun) se dio por «partido movido al 23/11» y no salió. Con varios_dias no."""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bot  # noqa: E402


class VariosDias(unittest.TestCase):
    def test_boleto_de_varios_dias_no_caduca(self):
        post = {"fecha": "2026-11-21T13:47", "sel": ["1557469|Player Fouls Committed|Jannik Schuster - 1"]}
        with mock.patch.object(bot, "leer", return_value={}), \
             mock.patch.object(bot, "partidos_fuera", return_value=set()), \
             mock.patch.object(bot, "fechas_calendario", return_value={"1557469": "2026-11-23T20:00:00+00:00"}):
            self.assertIn("movido", bot.partido_caido(post))
            self.assertIsNone(bot.partido_caido(dict(post, varios_dias=True)))


if __name__ == "__main__":
    unittest.main()
