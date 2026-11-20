"""20/11 (Marcos borró el pick del día: era el mismo que la escalera, y el porqué decía «puede acabar entre 1.º y 22.º»)."""
import unittest

import comprobar_post as C
import plantillas


class Telegram20Nov(unittest.TestCase):
    def test_bloquea_repetido_telegram_aunque_sea_del_bot(self):
        src = open(C.RAIZ / "comprobar_post.py", encoding="utf-8").read()
        self.assertIn('x[0] == "repetido" and "en Telegram" in x[1]', src)

    def test_pick_del_dia_evita_la_escalera(self):
        src = open(C.RAIZ / "combis_dia.py", encoding="utf-8").read()
        self.assertIn('pick_seguro(sin_choques(pools_pick), dia, ya=ya1)', src)

    def test_razon_vacia_fuera(self):
        src = open(C.RAIZ / "publicar_telegram.py", encoding="utf-8").read()
        self.assertIn('int(m_.group(2)) - int(m_.group(1)) >= 8', src)

    def test_etiqueta_no_repite_la_entrada(self):
        for i in range(40):
            t = plantillas.etiquetar("pick-seguro", "Pick de hoy, con datos detrás 📊\n\nx", semilla=f"2026-11-{i:02d}-pick-seguro")
            self.assertLessEqual(t.lower().count("con datos detrás"), 1)


if __name__ == "__main__":
    unittest.main()


class EscudosPorSel(unittest.TestCase):
    def test_rellena_escudo_del_partido(self):
        import tarjeta_tg as T
        fs = T.filas(["Athletic Club marca 2 o más vs Espanyol"], None)
        self.assertFalse(fs[0].get("escudo"))
        con = T.escudos_por_sel(fs, ["1570454|Total - Home|Over 1.5"])
        if (T.RAIZ / "datos" / "proximos" / "1570454.json").exists():
            self.assertTrue(con[0]["escudo"].endswith(".png"))

    def test_sin_escudo_no_hay_foto(self):
        import tarjeta_tg as T
        src = open(T.RAIZ / "tarjeta_tg.py", encoding="utf-8").read()
        self.assertIn("fila sin escudo/bandera", src)


class PartidosRaros(unittest.TestCase):
    def test_ligas(self):
        import combis_dia as D
        self.assertTrue(D.liga_conocida(140))      # La Liga
        self.assertTrue(D.liga_conocida(141))      # Segunda
        self.assertFalse(D.liga_conocida(283))     # Liga I (Rumanía)

    def test_bloquea_pick_raro_en_telegram(self):
        from unittest import mock
        p = {"id": "2026-11-20-pick-claude-2", "solo_en": ["telegram"], "origen": "claude", "sel": ["999|Match Winner|Home"]}
        with mock.patch("combis_dia.liga_conocida", return_value=False), \
             mock.patch.object(C.json, "loads", return_value={"partido": {"league": {"id": 283, "name": "Liga I"},
                                                                          "teams": {"home": {"name": "A"}, "away": {"name": "B"}}}}), \
             mock.patch("pathlib.Path.read_text", return_value="{}"):
            self.assertIn("partido raro", C.partido_raro(p) or "")
        th = dict(p, id="2026-11-20-loca-th-1200-x50", solo_en=["threads"])
        self.assertIsNone(C.partido_raro(th))      # Threads puede llevar lo que sea
