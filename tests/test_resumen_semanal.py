"""16/11 (Marcos): resumen semanal por privado, el domingo a las 22:00, del acierto de los picks de Telegram por tipo."""
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import resumen_semanal as R  # noqa: E402
from bot import MADRID  # noqa: E402

RES = {"2099-06-01": {"combis": [
    {"id": "2099-06-01-pick-seguro", "estado": "verde"},
    {"id": "2099-06-01-pick-seguro-2", "estado": "rojo"},
    {"id": "2099-06-01-pick-seguro-3", "estado": "rojo"},
    {"id": "2099-06-01-pick-m1", "estado": "rojo"},
    {"id": "2099-06-01-pick-tip-1", "estado": "verde"},
    {"id": "2099-06-01-pick-tip-2", "estado": "pendiente"},
    {"id": "2099-06-01-combi-tres", "estado": "verde"}]}}
POSTS = {"2099-06-01-pick-seguro": {"sel": ["1|Match Winner|Home"]},
         "2099-06-01-pick-seguro-2": {"sel": ["2|Home Corners Over/Under|Over 4.5"]},
         "2099-06-01-pick-seguro-3": {"sel": ["3|Away Corners Over/Under|Over 3.5"]},
         "2099-06-01-pick-m1": {"sel": ["4|Corners Over Under|Over 8.5"]}}


class ResumenSemanal(unittest.TestCase):
    def test_cuenta_por_tipo_y_copias(self):
        nuestros, copias = R.contar(["2099-06-01"], RES, POSTS)
        self.assertEqual(nuestros, {"resultado": [1, 1], "corners": [0, 3]})
        self.assertEqual(copias, [1, 1])   # la pendiente y la combi no cuentan
        t = R.texto(datetime(2099, 5, 26).date(), datetime(2099, 6, 1).date(), nuestros, copias)
        self.assertIn("🚩 Córners: 0 de 3 (0%) ⚠️", t)
        self.assertIn("🏆 Gana / doble: 1 de 1 (100%)", t)

    def test_solo_domingo_22_y_una_vez(self):
        enviados = []
        with tempfile.TemporaryDirectory() as d, mock.patch.object(R, "ESTADO", Path(d) / "e.json"):
            self.assertIsNone(R.main(datetime(2099, 6, 7, 21, 59, tzinfo=MADRID), enviar=enviados.append))
            self.assertIsNone(R.main(datetime(2099, 6, 6, 22, 30, tzinfo=MADRID), enviar=enviados.append))   # sábado
            self.assertIsNotNone(R.main(datetime(2099, 6, 7, 22, 0, tzinfo=MADRID), enviar=enviados.append))
            self.assertIsNone(R.main(datetime(2099, 6, 7, 22, 10, tzinfo=MADRID), enviar=enviados.append))
        self.assertEqual(len(enviados), 1)

    def test_va_por_privado_no_al_canal(self):
        src = Path(R.__file__).read_text(encoding="utf-8")
        self.assertIn("from alineaciones_posts import dm", src)
        self.assertNotIn("TELEGRAM_CANAL", src)


if __name__ == "__main__":
    unittest.main()
