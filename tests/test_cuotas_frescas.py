import json, unittest, tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest import mock
import cuotas_frescas as cf


class CuotasFrescas(unittest.TestCase):
    def test_corrige_cuota_total_y_ganancia(self):
        ahora = datetime.now(cf.MADRID)
        post = {"id": "x-combi-segura", "fecha": (ahora + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M"),
                "sel": ["1|Goals Over/Under|Over 1.5", "2|Match Winner|Home"],
                "texto": "T\n\n✅1. Más de 1,5 goles · 1,30\n✅2. Gana el A · 1,50\n\n🎯 Cuota total: 1,95\n💶 10€ → 19,50€"}
        with tempfile.TemporaryDirectory() as d:
            auto = Path(d) / "auto.json"; auto.write_text(json.dumps([post]))
            api = mock.MagicMock()
            api.get.side_effect = lambda ruta, fixture, bookmaker: [{"bookmakers": [{"bets": [
                {"name": "Goals Over/Under", "values": [{"value": "Over 1.5", "odd": "1.20"}]},
                {"name": "Match Winner", "values": [{"value": "Home", "odd": "1.50"}]}]}]}]
            with mock.patch.object(cf, "AUTO", auto), mock.patch.object(cf, "CACHE", Path(d) / "c.json"), \
                 mock.patch.object(cf, "API", return_value=api), mock.patch.dict("os.environ", {"API_FOOTBALL_KEY": "k"}), \
                 mock.patch.object(cf, "leer", side_effect=lambda r, dflt=None: dflt), \
                 mock.patch("playwright.sync_api.sync_playwright", side_effect=RuntimeError("sin navegador")):
                cf.main()
            t = json.loads(auto.read_text())[0]["texto"]
        self.assertIn("✅1. Más de 1,5 goles · 1,20", t)
        self.assertIn("🎯 Cuota total: 1,80", t)
        self.assertIn("💶 10€ → 18,00€", t)


if __name__ == "__main__":
    unittest.main()
