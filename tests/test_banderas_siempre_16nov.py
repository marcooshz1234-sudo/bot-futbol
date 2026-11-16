"""16/11: Islandia –1,5 salió en Telegram sin foto (3 fotos seguidas → texto, y el hándicap no tenía fila).
Marcos: «banderas o escudos siempre» / «prográmalo todo bien»."""
import unittest
from unittest import mock

import tarjeta_tg as T


class BanderasSiempre16Nov(unittest.TestCase):
    def test_handicap_con_bandera(self):
        for t in ("Gana Islandia por 2 o más goles (hándicap asiático –1,5)",
                  "Islandia gana por 2 o más goles (hándicap asiático –1,5)"):
            f = T.fila(t, "Islandia – Luxemburgo")
            self.assertEqual(f["pais"], "Iceland")
            self.assertEqual(f["pick"], "GANA DE 2+")

    def test_pick_raro_lleva_banderas_del_partido(self):
        f = T.fila("Algo que no se entiende", "Islandia – Luxemburgo")
        self.assertEqual(f["pais"], "Iceland")
        self.assertEqual(f.get("pais2"), "Luxembourg")

    def test_picks_y_copias_con_foto_aunque_haya_racha(self):
        p = {"id": "2026-11-16-pick-tip-99", "origen": "tipster", "texto": "🍀 Gana Islandia @1,85\n\n⚽ Islandia – Luxemburgo · hoy 18:00"}
        with mock.patch.object(T, "racha_fotos", return_value=9), mock.patch.object(T, "toca", return_value=True), \
                mock.patch("ganadores_img.generar") as gen, mock.patch.object(T, "MEDIA") as media:
            media.__truediv__.return_value.exists.return_value = False
            media.__truediv__.return_value.relative_to.return_value = "x.jpg"
            self.assertIsNotNone(T.hacer(p, p["texto"], []))
            self.assertTrue(gen.called)

    def test_publicar_no_manda_pick_sin_foto(self):
        src = open(T.RAIZ / "publicar_telegram.py", encoding="utf-8").read()
        self.assertIn("Sin foto, no sale", src)


if __name__ == "__main__":
    unittest.main()
