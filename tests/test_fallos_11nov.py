"""11/11: fallos que vio Marcos (o la revisión de las 18:51). Estos tests fallan si vuelven a aparecer."""
import re
import unittest
from unittest import mock
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

    def test_multi_respeta_max_dos_posts(self):
        import combis_dia
        from datetime import datetime as dt
        base = {"partido_id": 1, "mercado": "Match Winner", "opcion": "Home", "cuota": 1.6, "prob_aprendida": 0.9,
                "fecha": "2026-11-15T21:00", "liga_id": 140}
        pools = [[dict(base, partido_id=i)] for i in range(1, 9)]
        with mock.patch.object(combis_dia, "fijisimo", lambda p: True), mock.patch.object(combis_dia, "suelto_no", lambda p: False):
            libre = combis_dia.combi_multi(pools, "2026-11-15")
            usos = {f"{i}|Match Winner|Home": 2 for i in range(1, 9)}
            lleno = combis_dia.combi_multi(pools, "2026-11-15", usos=usos)
        self.assertIsNotNone(libre)
        self.assertIsNone(lleno)   # todas usadas ya 2 veces: no hay multi

    def test_cuentan_pick_y_estrella_en_max_dos(self):
        src = (RAIZ / "combis_dia.py").read_text(encoding="utf-8")
        i = src.index('for x in (res.get("seguro"), res.get("seguro2"))')
        self.assertLess(i, src.index('res["multi"] = combi_multi(pools, dia, dia_europeo, usos=usos)'))
        self.assertLess(src.index('res["multi"] = combi_multi('), src.index('for clave, cfg in (("tres", TRES)'))

    def test_escalera_todo_anulado_repite_escalon(self):
        import json as js
        import tempfile
        import escalera
        with tempfile.TemporaryDirectory() as d:
            est = Path(d) / "e.json"
            est.write_text(js.dumps({"escalon": 3, "stake": 64.8, "historial": [], "actual": {
                "dia": "2026-11-11", "escalon": 3, "stake": 64.8, "cuota": 1.9,
                "picks": [{"partido_id": 1, "fecha": "2026-11-11T20:00", "mercado": "Match Winner", "opcion": "Home"}]}}))
            leer_real = escalera.leer
            with mock.patch.object(escalera, "ESTADO", est), mock.patch.object(escalera, "resultado", lambda p: "anulada"), \
                    mock.patch.object(escalera, "leer", lambda r, *a: None if "picks" in str(r) else leer_real(r, *a)):
                escalera.main()
            e = js.loads(est.read_text())
            self.assertEqual((e["escalon"], e["stake"]), (3, 64.8))   # bet365 devuelve: no vuelve a 20 €
            self.assertEqual(e["historial"][-1]["resultado"], "anulada")

    def test_huella_siempre_la_misma(self):
        # 11/11: cuotas_frescas y alineaciones_posts escribían la huella vieja (sin DISENO): fotos rehechas dos veces
        for f in RAIZ.glob("*.py"):
            src = f.read_text(encoding="utf-8")
            for m in re.finditer(r'\.huella"\)\.write_text\((.*)', src):
                self.assertIn("huella(p)", m.group(1), f.name)

    def test_no_titular_sin_rehacer_no_sale(self):
        src = (RAIZ / "alineaciones_espera.py").read_text(encoding="utf-8")
        self.assertIn('nuevo["caducada"] = f"no titular:', src)   # antes salía con el jugador suplente

    def test_pick_del_dia_tipster_y_copa_en_rango(self):
        import combis_dia as C
        from datetime import datetime as dt
        from bot import MADRID
        pools = [[{"partido_id": 1, "mercado": "Match Winner", "opcion": "Home", "cuota": 1.95, "fecha": "2026-11-12T20:00",
                   "prob_aprendida": 0.7}]]
        llamadas = []
        with mock.patch.object(C, "pick_de_tipster", lambda *a, **k: llamadas.append(k.get("rango")) or None), \
                mock.patch.object(C, "pick_de_copa", lambda *a, **k: llamadas.append(("copa", k.get("rango"))) or None), \
                mock.patch.object(C, "minimo_diario", lambda: False):
            C.pick_seguro(pools, "2026-11-12")
        self.assertEqual(llamadas[0], (1.5, 1.7))   # primero, siempre el rango de Marcos
        self.assertEqual(llamadas[1], ("copa", (1.5, 1.7)))
        self.assertTrue(C.pick_de_copa(pools, dt(2026, 11, 12, 10, 30, tzinfo=MADRID), rango=(1.5, 1.7)) is None)

    def test_sin_quien_gana_antiguo(self):
        self.assertFalse(plantillas.GANADORES_ACTIVO)   # Marcos 11/11: solo los «Partidos de hoy» con escudos

    def test_comunidad_no_publica_en_el_canal(self):
        import comunidad
        self.assertFalse(comunidad.CANAL_ACTIVO)   # Marcos 11/11: en Telegram solo pick, escalera y una combi
        llamadas = []
        with mock.patch.object(comunidad, "canal", lambda *a, **k: llamadas.append(a)), \
                mock.patch.object(comunidad, "publicar_cola", lambda *a: llamadas.append(a)), \
                mock.patch.object(comunidad, "guardar", lambda e: None):
            comunidad.main()
        self.assertEqual(llamadas, [])

    def test_sin_gifs_ni_editar_publicados(self):
        import gifs
        self.assertFalse(gifs.ACTIVO)   # Marcos 11/11
        src = (RAIZ / "alineaciones_posts.py").read_text(encoding="utf-8")
        self.assertIn("r = cambiar_patas(p, cambios) if cambios and not enviado else None", src)

    def test_app_sin_borrados(self):
        src = (RAIZ / "app_datos.py").read_text(encoding="utf-8")
        self.assertIn('todos = [p for p in todos if p["id"] not in borrados]', src)
        src = (RAIZ / "vigilante.py").read_text(encoding="utf-8")
        self.assertIn('if p["id"] not in borrados', src)

    def test_fondo_de_las_apps(self):
        # 11/11: la app pública buscaba publica/fondo.jpg (no existe) y se veía negra
        self.assertTrue((RAIZ / "docs" / "fondo.jpg").exists())
        for app in ("publica", "panel", "mis"):
            src = (RAIZ / "docs" / app / "index.html").read_text(encoding="utf-8")
            self.assertIn('url("../fondo.jpg")', src, app)
        self.assertIn('url("fondo.jpg")', (RAIZ / "docs" / "index.html").read_text(encoding="utf-8"))
        # 12/11: la pública la rehace app_datos.copia_publica en cada pasada: el arreglo tiene que estar ahí
        import tempfile, shutil, app_datos
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "docs").mkdir()
            for f in ("index.html", "manifest.json"):
                shutil.copy(RAIZ / "docs" / f, Path(d) / "docs" / f)
            with mock.patch.object(app_datos, "RAIZ", Path(d)):
                app_datos.copia_publica()
            self.assertIn('url("../fondo.jpg")', (Path(d) / "docs" / "publica" / "index.html").read_text(encoding="utf-8"))

    def test_verde_de_escalera_lo_dice(self):
        import ticket_verde as T
        p = {"id": "2026-11-11-escalera-2", "titulo": "🪜 Reto escalera · Día 2/7", "cuota": 2.02,
             "picks": [{"texto": "OH Leuven (fem.) marca", "estado": "verde"}, {"texto": "Lyon (fem.) marca 3 o más", "estado": "verde"}]}
        with mock.patch.object(T, "_escalon", lambda p: {"escalon": 2, "stake": 36.0, "cuota": 2.02}):
            html = T.documento(p, "15:15")
        self.assertIn("ESCALERA · DÍA 2 SUPERADO", html)
        self.assertIn("36,00€ → 72,72€", html)
        self.assertIn("DÍA 3", html)
        html = T.documento(dict(p, id="2026-11-11-combi-tres"), "15:15")
        self.assertIn("COMBI ACERTADA", html)


if __name__ == "__main__":
    unittest.main()
