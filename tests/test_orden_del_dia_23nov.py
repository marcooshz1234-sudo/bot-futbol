"""23/11 (Marcos): (1) a primera hora salió «Vamos con otro pick» sin haber salido ninguno; (2) salió un pick de
mañana antes que los de hoy; (3) el porqué del Madrid era el homenaje a Jesús de Miguel."""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import publicar_telegram as PT  # noqa: E402
import noticias  # noqa: E402

M = ZoneInfo("Europe/Madrid")


class OrdenDelDia(unittest.TestCase):
    def test_primera_frase(self):
        p = {"id": "2026-11-23-pick-tip-1", "sel": ["1|Match Winner|Home"]}
        t = PT.primera_frase(p, "Vamos con otro pick, familia 👇\n🍀 Gana el Madrid", primero=True)
        self.assertTrue(PT.EMPEZAR.search(t.split("\n")[0]))
        self.assertTrue(t.endswith("🍀 Gana el Madrid"))
        t = PT.primera_frase(p, "Empezamos el día con este pick\n🍀 x", primero=False)
        self.assertTrue(PT.OTRO.search(t.split("\n")[0]))
        t = PT.primera_frase(p, "Os dejo el pick, familia 👇\nx", primero=True)                 # 12:37: «¿qué pick?»
        self.assertTrue(PT.EMPEZAR.search(t.split("\n")[0]))
        t = PT.primera_frase(p, "Os dejo el pick, familia 👇\nx", primero=False)
        self.assertTrue(PT.OTRO.search(t.split("\n")[0]))
        self.assertEqual(PT.primera_frase(p, "🚨 CUOTAZA EN BET365 🚨\nx", primero=True), "🚨 CUOTAZA EN BET365 🚨\nx")

    def test_pick_de_manana_espera_a_la_noche(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "9.json").write_text(json.dumps({"partido": {"fixture": {"date": "2026-11-24T20:00:00+00:00"}}}))
        p = {"id": "2026-11-24-pick-tip-1", "sel": ["9|Match Winner|Home"]}
        with mock.patch("bot.EXTRA", tmp):
            self.assertEqual(PT.dia_del_pick(p), "2026-11-24")
            self.assertTrue(PT.espera_a_la_noche(p, datetime(2026, 11, 23, 9, 30, tzinfo=M)))
            self.assertFalse(PT.espera_a_la_noche(p, datetime(2026, 11, 23, 21, 5, tzinfo=M)))
            self.assertFalse(PT.espera_a_la_noche(p, datetime(2026, 11, 24, 10, 0, tzinfo=M)))
        src = Path(PT.__file__).read_text(encoding="utf-8")
        self.assertLess(src.index("cuenta desde las 21:00 de la víspera"), src.index("if ahora - cuando > MAX_RETRASO"))

    def test_homenaje_no_es_porque(self):
        n = {"titulo": "El homenaje más sentido a Jesús de Miguel, con la familia sobre el césped del Santiago Bernabéu",
             "fuente": "AS", "tipos": ["campo"]}
        with mock.patch.object(noticias, "leer", return_value={"5": [n]}):
            self.assertEqual(noticias.razones(5), [])
        import re
        self.assertFalse(re.search(noticias.TIPOS["campo"], noticias.norm("homenaje sobre el cesped del bernabeu")))
        self.assertTrue(re.search(noticias.TIPOS["campo"], noticias.norm("el cesped esta en mal estado por la lluvia")))


if __name__ == "__main__":
    unittest.main()
