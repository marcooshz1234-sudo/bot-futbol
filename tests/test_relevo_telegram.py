"""22/11: GitHub dejó de lanzar el cron 3 horas y no salieron posts. Cada tanda lanza la siguiente (relevo)."""
import unittest
from pathlib import Path

WF = (Path(__file__).resolve().parent.parent / ".github/workflows/telegram.yml").read_text(encoding="utf-8")


class Relevo(unittest.TestCase):
    def test_relevo(self):
        self.assertIn("actions: write", WF)
        self.assertIn("actions/workflows/telegram.yml/dispatches", WF)
        self.assertIn("if: always()", WF)
        self.assertIn("cancel-in-progress: false", WF)   # nunca dos tandas a la vez
        self.assertIn('cron: "*/30 * * * *"', WF)          # el cron, de respaldo


if __name__ == "__main__":
    unittest.main()
