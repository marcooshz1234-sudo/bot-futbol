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
        i = src.index('usos[sel(res["seguro"][0])] += 1')
        self.assertLess(src.index('usos.update(sel(p) for cp, *_ in res.get("estrella")'), i)
        self.assertLess(i, src.index('res["multi"] = combi_multi(sin_choques(pools), dia, dia_europeo, usos=usos)'))
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

    def test_verdes_distintos_no_son_duplicados(self):
        import redes
        a = "PARA DENTRO SEÑORES ✅🤑\n\n✅ Accrington +1,5 (hándicap)\n\n📈 Cuota @1,51"
        b = "PARA DENTRO SEÑORES ✅🤑\n\n✅ OH Leuven (fem.) marca\n✅ Lyon (fem.) marca 3 o más"
        self.assertNotEqual(redes._titulo(a), redes._titulo(b))
        self.assertEqual(redes._titulo(a), redes._titulo(a + "\n\nOtra cosa"))

    def test_logo_liga_sin_circulo_y_partidos_fijas(self):
        import fotos, ganadores_win as G
        html = fotos._logo_liga(RAIZ / "publicaciones" / "media" / "escudos" / "liga-5.png", 190)
        self.assertNotIn("border-radius:50%", html)   # Marcos 12/11: sin el círculo blanco
        self.assertIn("width:190px", html)   # (la llamada de quien_gana usa 230)
        base = {"ini": 0, "equipo": {"name": "x"}, "grande": False, "lado": "Home", "cuota": 1.5, "liga": 5}
        altos = [dict(base, fid=i, prob=0.7) for i in range(4)]
        bajos = altos + [dict(base, fid=10 + i, prob=0.45) for i in range(4)]
        with mock.patch.object(G, "candidatos", lambda dia, minimo=None, excluir=(): bajos if minimo else altos):
            g = dict(G.grupos("2026-11-12"))
        self.assertEqual(len(g["nations"]), 8)   # «tiene que haber 8-9»

    def test_lema_partidos_de_hoy_varia(self):
        import fotos, ganadores_win as G, plantillas
        self.assertGreater(len({plantillas.lema(f"2026-11-{d:02d}") for d in range(1, 31)}), 3)
        html = fotos.quien_gana([], "NATIONS LEAGUE", lema="¿PLENO HOY?")
        self.assertIn("¿PLENO HOY?", html)
        self.assertNotIn("PINTAMOS", html)
        base = {"ini": 0, "equipo": {"name": "x"}, "grande": False, "lado": "Home", "cuota": 1.5, "prob": 0.7}
        gr = [("laliga", [dict(base, fid=1, liga=140)]), ("premier", [dict(base, fid=2, liga=39)])]
        frases = []
        with mock.patch.object(G, "grupos", lambda d, e=(): gr), \
                mock.patch.object(G, "post", lambda *a, **k: frases.append(k["frase"]) or {"x": 1}):
            G.posts("2026-11-14")
        self.assertEqual(len(set(frases)), 2)   # mismo día, frases distintas

    def test_lema_verdes_varia(self):
        import ticket_verde as T
        lemas = set()
        for i in range(12):
            p = {"id": f"2026-11-1{i % 9}-combi-{i}", "cuota": 2, "picks": [{"texto": "Gana el Betis", "estado": "verde"},
                                                                         {"texto": "Marca el Sevilla", "estado": "verde"}]}
            html = T.documento(p, "12:00")
            lemas |= {l for l in __import__("plantillas").LEMAS_VERDE if l in html}
        self.assertGreater(len(lemas), 2)

    def test_cierre_solo_a_veces(self):
        tx = "Combi\n\n✅ Gana el Betis\n\n📈 Cuota @1,80\n\n" + plantillas.CIERRE_TELEGRAM
        salen = [plantillas.cierre_a_veces(tx, f"2026-11-12-combi-{i}") for i in range(40)]
        con = sum(s.endswith(plantillas.CIERRE_TELEGRAM) for s in salen)
        self.assertTrue(10 < con < 30)   # más o menos la mitad
        self.assertTrue(all(s.rstrip().endswith(("@1,80", plantillas.CIERRE_TELEGRAM)) for s in salen))
        self.assertEqual(plantillas.cierre_a_veces("Hola\n\nadiós", "x"), "Hola\n\nadiós")   # sin cierre: igual

    def test_verde_en_threads_como_comentario(self):
        import redes
        enviados = []
        with mock.patch.object(redes, "hilo_original", lambda p: "999"), \
                mock.patch.object(redes, "llamar", lambda m, u, d: enviados.append(d) or {"id": "1"}), \
                mock.patch.object(redes.time, "sleep", lambda s: None):
            redes.threads({"id": "2026-11-12-verde-auto-x", "texto": "PARA DENTRO SEÑORES ✅🤑\n\n✅ Gana el Betis",
                           "verde_de": "x"}, "t")
        self.assertEqual(enviados[0]["reply_to_id"], "999")
        self.assertNotIn("topic_tag", enviados[0])

    def test_noticias_utiles(self):
        import app_datos as A
        self.assertTrue(A.noticia_util({"titulo": "La posible alineación titular de Inglaterra para enfrentar a Croacia"}, "England", "Croatia"))
        self.assertFalse(A.noticia_util({"titulo": "Cómo conseguir entradas para el Italia-Francia"}, "Italy", "France"))
        self.assertFalse(A.noticia_util({"titulo": "Watch New Zealand vs. India Live Stream Online"}, "Türkiye", "Belgium"))
        self.assertFalse(A.noticia_util({"titulo": "Inglaterra vs Croacia Pronóstico y Apuestas"}, "England", "Croatia"))

    def test_tarjeta_nombres_en_espanol(self):
        src = (RAIZ / "imagenes.py").read_text(encoding="utf-8")
        self.assertIn('"local": _es(t["local"])', src)

    def test_cuota_real_combi_partido(self):
        import asistente
        b = asistente.Asistente.__new__(asistente.Asistente)
        c = {"textos": {}, "cancelados": [], "aprobados": {}}
        post = {"id": "2026-11-12-combi-partido-1-th", "fecha": "2026-11-12T19:45", "pide_cuota": True,
                "texto": "Os dejo la combi del Italia – Francia ⚽🔥\n\n🍀 A\n🍀 B\n\n📈 Cuota @2,35"}
        dichos = []
        b.control = lambda: c
        b.programados = lambda: [post]
        b.enviar = lambda t, *a: dichos.append(t)
        with mock.patch.object(asistente, "escribir", lambda *a: None), mock.patch.object(asistente, "guardar", lambda *a: None):
            self.assertIsNone(b.cuota_combi_partido("hola"))
            b.cuota_combi_partido("1,85")
        self.assertIn("📈 Cuota @1,85", c["textos"][post["id"]])
        self.assertIn(post["id"], c["aprobados"])
        self.assertIn("1,85", dichos[0])
        # las combis de UN partido piden la cuota (plantillas)
        self.assertIn("pide_cuota=True", (RAIZ / "plantillas.py").read_text(encoding="utf-8"))

    def test_nunca_seguro_en_lo_publicado(self):
        # 12/11 (Marcos: «nunca pongas nada seguro o asegurado»): ninguna frase entre comillas del código que se publica
        import ast
        for f in ("plantillas.py", "copiar_tipsters.py", "verdes_auto.py", "combis_dia.py", "fotos.py", "ganadores_win.py",
                  "cazador.py", "puente/puente.py", "razones.py", "ticket_verde.py", "panel_datos.py", "avisos.py"):
            for n in ast.walk(ast.parse((RAIZ / f).read_text(encoding="utf-8"))):
                if isinstance(n, ast.Constant) and isinstance(n.value, str) and not n.value.startswith(("pick-seguro", "-pick-seguro")) \
                        and n.value not in ("SEGURA", "segura", "seguro", "seguros", "combi-segura") and "|" not in n.value:   # claves y patrones internos
                    if re.search(r"(?<![a-z_-])(seguro|segura|asegurad[oa])(?![a-z_-])", n.value, re.I) and \
                            not re.search(r"\bid\b|pick-seguro|seguro2|SEGURO_|^\s*\d|«|\n\s{4}", n.value):
                        self.fail(f"{f}: «{n.value[:70]}»")
        for f in ("docs/index.html", "docs/panel/index.html"):
            self.assertNotIn("Combi segura", (RAIZ / f).read_text(encoding="utf-8"))

    def test_logo_competicion_en_el_pick(self):
        import fotos
        t = {"liga_id": 5, "local": "Albania", "visitante": "Finland"}
        html = fotos._logo_hueco(t, 120, 200)
        self.assertIn("data:image/png;base64", html)
        self.assertNotIn("border-radius:50%", html)
        self.assertEqual(fotos._logo_hueco({}, 120, 200), "")
        import ganadores_img as G
        self.assertTrue(G.logo_liga(5).endswith((".png",)))

    def test_datos_clave_del_partido(self):
        import app_datos as A
        p = {"id": 1, "fecha": "2026-11-12T20:45", "local": "England", "visitante": "Croatia",
             "ficha": {"local": {"nombre": "England", "partidos": 4, "forma": "GGGP", "medias": {"gf": 3.5, "gc": 0.8},
                                 "pct": {"marca": 100, "ambos": 25}},
                       "visitante": {"nombre": "Croatia", "partidos": 4, "forma": "PPPG", "medias": {"gf": 1, "gc": 3.5},
                                     "pct": {"marca": 75, "ambos": 75}},
                       "bajas_importantes": {"local": ["Kane"]}}}
        with mock.patch.object(A, "leer", lambda r, d=None: {"2026-11-12": [{"partido_id": 1, "datos": [
                "Dato del bot", "El deporte 'esquiva' la huelga (La Tribuna de Ciudad Real)"]}]}):
            d = A.datos_clave(p, {})
        self.assertIn("Dato del bot", d)
        self.assertIn("Inglaterra gana sus últimos 3 partidos", d)
        self.assertIn("Croacia no gana en sus últimos 3", d)
        self.assertIn("Baja importante en Inglaterra: Kane", d)
        self.assertFalse(any("Tribuna" in x for x in d))   # titulares de prensa fuera

    def test_app_pestana_picks(self):
        src = (RAIZ / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn('["picksdia","🍀","Picks"]', src)
        self.assertIn("function vPicksDia()", src)

    def test_arbitros_ext_con_la_api(self):
        import tempfile, json as js
        import arbitros_ext as AE
        class FakeAPI:
            def __init__(self, k): pass
            def get(self, ruta, **p):
                if ruta == "fixtures":   # 12/11: la API no deja buscar por árbitro; se filtra el calendario
                    assert "referee" not in p and "league" in p, p
                    if p["league"] != 5:
                        return []
                    return [{"fixture": {"id": i, "date": f"2026-10-0{i}", "status": {"short": "FT"},
                                         "referee": "Sandro Schärer, Switzerland" if i < 4 else "Otro, Italy"}}
                            for i in range(1, 6)]
                return [{"statistics": [{"type": "Yellow Cards", "value": 2}, {"type": "Red Cards", "value": None}]},
                        {"statistics": [{"type": "Yellow Cards", "value": 3}]}]
        with tempfile.TemporaryDirectory() as d:
            sal = Path(d) / "a.json"
            with mock.patch.object(AE, "API", FakeAPI), mock.patch.object(AE, "SALIDA", sal), \
                    mock.patch.object(AE, "arbitros_pendientes", lambda a: iter([("Sandro Schärer", "Sandro Schärer, Switzerland")])), \
                    mock.patch.dict("os.environ", {"API_FOOTBALL_KEY": "x"}):
                AE.main()
            self.assertEqual(js.loads(sal.read_text())["Sandro Schärer"]["tarjetas"], [5, 5, 5])


if __name__ == "__main__":
    unittest.main()
