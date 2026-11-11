"""11/11: fallos que vio Marcos (o la revisión de las 18:51). Estos tests fallan si vuelven a aparecer."""
import re
import unittest
from pathlib import Path

import plantillas
import tipsters_auto

RAIZ = Path(__file__).resolve().parents[1]


class TestFallos11Nov(unittest.TestCase):
    def test_sin_check_falso_en_patas_sin_bandera(self):
        self.assertNotEqual(plantillas.bandera_pick({"equipo": "Equipo Inventado FC", "mercado": "Match Winner"}), "✅")

    def test_nombres_en_espanol(self):
        self.assertEqual(plantillas.es("Czechia"), "Chequia")
        self.assertEqual(plantillas.es("Finland"), "Finlandia")

    def test_handicap_no_es_goles(self):
        self.assertIsNone(tipsters_auto.mercado("accrington +1,5 cuota 1,51", True, False))

    def test_pick_del_dia_de_tipster_con_rango(self):
        src = (RAIZ / "combis_dia.py").read_text(encoding="utf-8")
        llamadas = re.findall(r"(?<!def )pick_de_tipster\(pools, dia, hora[^)]*\)", src)
        self.assertTrue(llamadas)
        self.assertTrue(all("rango=" in x for x in llamadas), llamadas)

    def test_texto_de_tipster_sin_su_nombre(self):
        t = tipsters_auto.texto_limpio(("Goals Over/Under", "Over 1.5"), "Czechia", "Spain", "INSIDER 🍀 +1.5 goles", "INSIDER")
        self.assertNotIn("INSIDER", t)
        self.assertIn("Chequia", t)

    def test_no_se_copian_mercados_prohibidos(self):
        import json, tempfile
        from datetime import datetime
        from unittest import mock
        import copiar_tipsters as C
        from bot import MADRID
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "tipsters.json").write_text(json.dumps([{"tipster": "TipsAnalistas", "fuente": "x", "dia": "2026-11-12",
                "local": "A", "visitante": "B", "texto": "Más de 2,5 goles", "mercado": "Goals Over/Under",
                "opcion": "Over 2.5", "cuota": 1.6, "partido_id": 5}]))
            with mock.patch.object(C, "DATOS", d), mock.patch.object(C, "REGISTRO", d / "r.json"), \
                    mock.patch.object(C, "COLA", d / "c.json"), \
                    mock.patch.object(C, "inicio", lambda pk: datetime(2026, 11, 12, 20, 0, tzinfo=MADRID)):
                self.assertEqual(C.main(datetime(2026, 11, 11, 20, 0, tzinfo=MADRID)), [])

    def test_cuotaza_sin_aprobar_caduca(self):
        import json, tempfile
        from datetime import datetime
        from unittest import mock
        import cazador
        from bot import MADRID
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            cola = d / "cola.json"
            cola.write_text(json.dumps([{"id": "2026-11-11-cuotaza-1-abc", "fecha": "2026-11-11T09:05", "requiere_ok": True,
                                         "texto": "x"}]))
            with mock.patch.object(cazador, "COLA", cola), mock.patch.object(cazador, "ESTADO", d / "e.json"), \
                    mock.patch.object(cazador, "refrescar", lambda a: 0), mock.patch.object(cazador, "buscar", lambda *a, **k: []):
                cazador.main(datetime(2026, 11, 11, 17, 0, tzinfo=MADRID))
            self.assertTrue(json.loads(cola.read_text())[0].get("caducada"))

    def test_chromium_del_bucle_por_su_lado(self):
        wf = (RAIZ / ".github/workflows/telegram.yml").read_text(encoding="utf-8")
        self.assertNotIn("playwright install --with-deps chromium >/dev/null 2>&1' || echo", wf)
        self.assertIn("python -m playwright install chromium", wf)

    def test_reels_centrados(self):
        src = (RAIZ / "imagenes.py").read_text(encoding="utf-8")
        self.assertNotIn("\n.marca{margin-top:auto}", src)

    def test_historia_pie_no_pisa_la_cuota(self):
        src = (RAIZ / "imagenes.py").read_text(encoding="utf-8")
        self.assertIn(".v .pie{position:static", src)   # el pie va detrás de la cuota, nunca encima

    def test_titulo_con_euros_no_se_pierde(self):
        import imagenes
        t = imagenes.sin_dinero("🧮 COMBILOCAS — ¡DE 1€ A 500€! x453,38 🧮\n\n🇳🇱 Fortuna Sittard o empate\n💶 1€ → 453€")
        self.assertEqual(imagenes.partes(t)[0], "🧮 COMBILOCAS · x453,38 🧮")
        self.assertNotIn("€", t)
        self.assertIn("Fortuna", t)


if __name__ == "__main__":
    unittest.main()
