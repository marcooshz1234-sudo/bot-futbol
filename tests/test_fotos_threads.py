import unittest
from unittest import mock

import redes


class FotosThreads(unittest.TestCase):
    """12/11 (Marcos: «no pongas tanta foto en Threads» → solo el pick del día y los ganadores)."""
    def foto(self, pid, **kw):
        with mock.patch.object(redes, "url_media", lambda p, e: f"{p['id']}.{e}"):
            return redes.foto_threads({"id": pid, **kw})

    def test_con_foto(self):
        self.assertEqual(self.foto("2026-11-12-pick-seguro"), "2026-11-12-pick-seguro.jpg")
        self.assertEqual(self.foto("2026-11-12-ganadores-nations"), "2026-11-12-ganadores-nations.tarjeta.jpg")

    def test_con_foto_salvo_muchas_cosas(self):   # 15/11 (Marcos: «solo a texto cuando son muchas cosas»)
        self.assertEqual(self.foto("2026-11-12-combi-partido-1", tarjeta={"local": "A"}, texto="🍀 a\n🍀 b"),
                         "2026-11-12-combi-partido-1.tarjeta.jpg")
        self.assertEqual(self.foto("2026-11-12-pick-tip-3", texto="🍀 Gana A @1,5"), "2026-11-12-pick-tip-3.jpg")
        largo = "\n".join(f"🍀 pata {i}" for i in range(5))
        self.assertIsNone(self.foto("2026-11-12-combi-loca", texto=largo))


if __name__ == "__main__":
    unittest.main()


class BoletoConFoto(unittest.TestCase):
    def test_boleto_lleva_su_captura_en_threads(self):   # 14/11: la combinada personal salió sin foto y no se entendía
        # 19/11: con una carpeta de prueba (la limpieza de media borró la captura real del 14/11 y el test fallaba)
        import tempfile
        from pathlib import Path
        from unittest import mock
        import redes
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "publicaciones" / "media").mkdir(parents=True)
            (Path(d) / "publicaciones" / "media" / "2026-11-14-boleto-personal.tarjeta.jpg").write_bytes(b"jpg")
            with mock.patch.object(redes, "RAIZ", Path(d)):
                u = redes.foto_threads({"id": "2026-11-14-boleto-personal", "foto": "publicaciones/media/2026-11-14-boleto-personal.tarjeta.jpg"})
        self.assertIn("2026-11-14-boleto-personal.tarjeta.jpg", u or "")
        self.assertIsNone(redes.foto_threads({"id": "2026-11-14-pick-tip-1", "texto": "\n".join(["🍀 x"] * 5)}))
