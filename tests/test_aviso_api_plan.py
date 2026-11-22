"""22/11: la API pasó al plan gratis a las 08:43 y nadie se enteró hasta las 19:40. Ahora avisa al móvil."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bot  # noqa: E402


class R:
    headers = {}
    def __init__(self, d): self.d = d
    def read(self): return json.dumps(self.d).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


class AvisoPlan(unittest.TestCase):
    def test_error_de_plan_se_apunta(self):
        tmp = Path(tempfile.mkdtemp())
        err = {"errors": {"plan": "Free plans do not have access to the Ids parameter."}, "response": []}
        with mock.patch.object(bot, "DATOS", tmp), mock.patch.object(bot, "urlopen", return_value=R(err)):
            self.assertEqual(bot.API("x").get("fixtures", ids="1-2"), [])
        self.assertIn("Free plans", json.loads((tmp / "api_plan.json").read_text())["error"])

    def test_avisos_lo_manda(self):
        src = (Path(__file__).resolve().parent.parent / "avisos.py").read_text(encoding="utf-8")
        self.assertIn('api_plan.json', src)
        self.assertIn('PLAN GRATIS', src)
        wf = (Path(__file__).resolve().parent.parent / ".github/workflows/telegram.yml").read_text(encoding="utf-8")
        self.assertIn("datos/api_plan.json", wf)


if __name__ == "__main__":
    unittest.main()
