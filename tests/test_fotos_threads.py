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

    def test_sin_foto(self):
        for pid in ("2026-11-12-pick-seguro-2", "2026-11-12-pick-tip-3", "2026-11-12-pick-th-1",
                    "2026-11-12-combi-partido-1528958-th", "2026-11-12-combi-tres", "2026-11-12-combi-loca"):
            self.assertIsNone(self.foto(pid, tarjeta={"local": "A"}), pid)


if __name__ == "__main__":
    unittest.main()


class BoletoConFoto(unittest.TestCase):
    def test_boleto_lleva_su_captura_en_threads(self):   # 14/11: la combinada personal salió sin foto y no se entendía
        import redes
        u = redes.foto_threads({"id": "2026-11-14-boleto-personal", "foto": "publicaciones/media/2026-11-14-boleto-personal.tarjeta.jpg"})
        self.assertIn("2026-11-14-boleto-personal.tarjeta.jpg", u or "")
        self.assertIsNone(redes.foto_threads({"id": "2026-11-14-pick-tip-1"}))
