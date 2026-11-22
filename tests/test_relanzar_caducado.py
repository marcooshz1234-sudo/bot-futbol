"""22/11: el cron se saltó 3 h y el pick de las 10:30 y la escalera caducaron por retraso. Con
control.aprobados[id] = hora, un post normal (sin requiere_ok) se relanza desde esa hora."""
import unittest
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent / "publicar_telegram.py").read_text(encoding="utf-8")


class Relanzar(unittest.TestCase):
    def test_relanzar(self):
        i = SRC.index('rel = (control.get("aprobados") or {}).get(p["id"])')
        self.assertLess(i, SRC.index("if ahora - cuando > MAX_RETRASO"))   # antes del control de retraso
        self.assertIn('if rel and not p.get("requiere_ok"):', SRC)
        self.assertIn("cuando = max(cuando, datetime.fromisoformat(rel)", SRC)


if __name__ == "__main__":
    unittest.main()
