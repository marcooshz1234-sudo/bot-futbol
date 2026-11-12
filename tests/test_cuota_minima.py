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

    def test_pata_de_combi_minimo_120(self):   # 12/11: «en una combi sí, pero mínimo 1,20»
        p = {"id": "2026-11-12-combi-tip-1", "sel": ["1|a|b", "2|c|d"], "cuotas": [1.14, 1.28], "texto": "📈 Cuota @1,46"}
        self.assertIn("pata", cuota_baja(p))
        self.assertIsNone(cuota_baja(dict(p, cuotas=[1.20, 1.28])))
        self.assertIsNone(cuota_baja(dict(p, id="2026-11-12-ganadores-nations")))   # la lista de ganadores no es combi

    def test_pata_de_elite_en_combi(self):   # 12/11: «España gana es muy, muy buena… no es lo mismo que Bielorrusia»
        import bot
        p = {"id": "2026-11-12-combi-tip-9", "sel": ["1|Match Winner|Away", "2|Match Winner|Home"],
             "cuotas": [1.19, 1.29], "texto": "📈 Cuota @1,54"}
        with mock.patch.object(bot, "pata_de_elite", lambda s: s.startswith("1|")):
            self.assertIsNone(cuota_baja(p))                                   # España @1,19 en combi de 1,54: vale
            self.assertTrue(cuota_baja(dict(p, cuotas=[1.12, 1.29], texto="📈 Cuota @1,44")))   # por debajo de 1,15, no
            self.assertTrue(cuota_baja(dict(p, cuotas=[1.19, 1.22], texto="📈 Cuota @1,45")))   # combi corta, no
        with mock.patch.object(bot, "pata_de_elite", lambda s: False):          # Bielorrusia gana @1,19: no
            self.assertTrue(cuota_baja(p))

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

    def test_tres_bajos_una_combi(self):   # «si son pocas cosas o picks bajos, que los combines»
        r = self.correr([self.pk(1, 1.22), self.pk(2, 1.25), self.pk(3, 1.30)])
        self.assertEqual(len(r), 1)
        self.assertEqual(len(r[0]["sel"]), 3)

    def test_dos_bajos_esperan_si_queda_tiempo(self):   # partido a 6 h: espera por si llega un tercero
        self.assertEqual(self.correr([self.pk(1, 1.22), self.pk(2, 1.25)]), [])

    def test_dos_bajos_se_juntan(self):
        import copiar_tipsters as CT
        with mock.patch.object(CT, "ESPERA_PAREJA", timedelta(hours=8)):   # ya queda poco para el partido
            r = self.correr([self.pk(1, 1.22), self.pk(2, 1.20)])
        self.assertEqual(len(r), 1)
        self.assertIn("combi-tip", r[0]["id"])

    def test_pareja_que_no_llega_no(self):
        self.assertEqual(self.correr([self.pk(1, 1.08), self.pk(2, 1.10)]), [])

    def test_pata_bajo_120_ni_en_pareja(self):
        self.assertEqual(self.correr([self.pk(1, 1.14), self.pk(2, 1.30)]), [])

    def test_combinada_con_pata_bajo_120_fuera(self):
        self.assertEqual(self.correr([self.pk(1, 1.14, combinada="z"), self.pk(2, 1.40, combinada="z")]), [])

    def test_suelto_bueno_sale(self):
        self.assertEqual(len(self.correr([self.pk(1, 1.55)])), 1)

    def test_sin_cuota_no(self):
        self.assertEqual(self.correr([self.pk(1, None)]), [])

    def test_mercados_de_ellos_si(self):   # 12/11 (Marcos: «esos mercados sí los puedes usar, y más si lo dicen ellos»)
        r = self.correr_real([self.pk(1, 1.50, mercado="Goals Over/Under", opcion="Over 2.5", texto="Más de 2,5 goles")])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["sel"], ["1|Goals Over/Under|Over 2.5"])

    def test_crear_apuesta_con_su_cuota(self):
        import copiar_tipsters as CT
        x = self.pk(1, 1.54, texto="Gana Inglaterra y goles en la 1ª parte (Crear apuesta)")
        self.assertEqual(CT.cuota_bet365(x), (1.54, False))

    def test_crear_apuesta_sin_sel(self):   # varias condiciones: que el verde no salga con una sola
        r = self.correr_real([self.pk(1, 1.54, mercado="Match Winner", opcion="Home",
                                      texto="Gana Inglaterra y más de 0,5 goles en la 1ª parte (Crear apuesta)")])
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["sel"], [])

    def test_combinada_sin_una_pata_fuera_entera(self):
        import copiar_tipsters as CT
        a = self.pk(1, 1.4, combinada="z")
        b = self.pk(2, 1.15, combinada="z")
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
