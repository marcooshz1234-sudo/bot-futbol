import json
import sys
import tempfile
import unittest
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import MADRID, cuota_baja, cuota_post


class TestCuotaMinima(unittest.TestCase):
    """12/11 (Marcos: «no puedes subir una publicación con un solo pick a cuota 1,10, 1,11… mínimo 1,30 o 1,35»)."""

    def test_pick_suelto_bajo_no_sale(self):
        p = {"id": "2026-11-12-pick-tip-1", "sel": ["1|Total - Away|Over 0.5"], "cuotas": [1.11],
             "texto": "🍀 Bélgica marca @1,11"}
        self.assertTrue(cuota_baja(p))

    def test_cuota_del_texto_manda(self):
        p = {"id": "x", "sel": ["1|a|b", "1|c|d"], "cuotas": [1.2, 1.3], "texto": "📈 Cuota @1,60"}
        self.assertAlmostEqual(cuota_post(p), 1.60)
        self.assertIsNone(cuota_baja(p))

    def test_combi_baja_tampoco(self):
        self.assertTrue(cuota_baja({"id": "x", "sel": ["1|a|b", "2|c|d"], "cuotas": [1.1, 1.15], "texto": ""}))

    def test_sin_cuota_y_verdes_no_se_tocan(self):
        self.assertIsNone(cuota_baja({"id": "2026-11-12-ganadores", "texto": "1. Bélgica - Win"}))
        self.assertIsNone(cuota_baja({"id": "v", "verde_de": "x", "texto": "✅ @1,11"}))

    def test_puertas_de_publicar(self):
        raiz = Path(__file__).resolve().parent.parent
        self.assertIn("cuota_baja(p", (raiz / "publicar_telegram.py").read_text(encoding="utf-8"))
        self.assertIn("cuota_baja(p", (raiz / "redes.py").read_text(encoding="utf-8"))


class TestCopiarTipsters(unittest.TestCase):
    def correr(self, picks):
        import copiar_tipsters as CT
        ahora = datetime(2026, 11, 12, 12, 0, tzinfo=MADRID)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "tipsters.json").write_text(json.dumps(picks))
            (d / "cola.json").write_text("[]")
            with mock.patch.object(CT, "DATOS", d), mock.patch.object(CT, "COLA", d / "cola.json"), \
                    mock.patch.object(CT, "REGISTRO", d / "reg.json"), \
                    mock.patch.object(CT, "inicio", lambda x: ahora + timedelta(hours=6)), \
                    mock.patch.object(CT, "cuota_bet365", lambda x: (x.get("cuota"), True)), \
                    mock.patch.object(CT, "motivo_no", lambda x, u: None), \
                    mock.patch("combis_dia.ya_publicadas", lambda dia: Counter()), \
                    mock.patch.dict("os.environ", {"GITHUB_ACTIONS": ""}):
                return CT.main(ahora)

    def pk(self, fid, cuota, tipster="INSIDER", **kw):
        return {"tipster": tipster, "fuente": f"c/{fid}", "dia": "2026-11-12", "local": "A", "visitante": "B",
                "partido_id": fid, "mercado": "Total - Away", "opcion": "Over 0.5", "cuota": cuota,
                "texto": f"Pata {fid}", **kw}

    def test_suelto_bajo_no_se_sube(self):
        self.assertEqual(self.correr([self.pk(1, 1.11)]), [])

    def test_dos_bajos_se_juntan(self):
        r = self.correr([self.pk(1, 1.15), self.pk(2, 1.20)])
        self.assertEqual(len(r), 1)
        self.assertIn("combi-tip", r[0]["id"])

    def test_pareja_que_no_llega_no(self):
        self.assertEqual(self.correr([self.pk(1, 1.08), self.pk(2, 1.10)]), [])

    def test_suelto_bueno_sale(self):
        self.assertEqual(len(self.correr([self.pk(1, 1.55)])), 1)

    def test_sin_cuota_no(self):
        self.assertEqual(self.correr([self.pk(1, None)]), [])

    def test_primera_parte_no(self):
        import copiar_tipsters as CT
        self.assertTrue(CT.PROHIBIDO_TEXTO.search("Gana Inglaterra y más de 0,5 goles en la 1ª parte"))

    def test_combinada_sin_una_pata_fuera_entera(self):
        import copiar_tipsters as CT
        a = self.pk(1, 1.4, combinada="z")
        b = self.pk(2, 1.5, combinada="z", texto="Más de 0,5 goles en la 1ª parte")
        r = self.correr_real([a, b])
        self.assertEqual(r, [])

    def correr_real(self, picks):   # con motivo_no de verdad (sin choques: usos vacíos)
        import copiar_tipsters as CT
        ahora = datetime(2026, 11, 12, 12, 0, tzinfo=MADRID)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "tipsters.json").write_text(json.dumps(picks))
            (d / "cola.json").write_text("[]")
            with mock.patch.object(CT, "DATOS", d), mock.patch.object(CT, "COLA", d / "cola.json"), \
                    mock.patch.object(CT, "REGISTRO", d / "reg.json"), \
                    mock.patch.object(CT, "inicio", lambda x: ahora + timedelta(hours=6)), \
                    mock.patch.object(CT, "cuota_bet365", lambda x: (x.get("cuota"), True)), \
                    mock.patch("combis_dia.ya_publicadas", lambda dia: Counter()), \
                    mock.patch("revision.lados_sin_estrella", lambda fid: set()), \
                    mock.patch.dict("os.environ", {"GITHUB_ACTIONS": ""}):
                return CT.main(ahora)

    def test_baloncesto_no(self):
        self.assertEqual(self.correr([self.pk(1, 1.55, tipster="TipsAnalistasNBA🏀")]), [])

    def test_canal_nuevo_de_futbol_si(self):
        self.assertEqual(len(self.correr([self.pk(1, 1.55, tipster="TRADER FOOTBALL || FREE👨🏼‍💻")])), 1)


if __name__ == "__main__":
    unittest.main()
