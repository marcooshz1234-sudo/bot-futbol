"""18/11 (Marcos: «no salen los escudos de los equipos, siempre revisa eso»): un verde nunca sale sin su foto."""
import unittest

import comprobar_post as C


class VerdeConEscudos(unittest.TestCase):
    def test_verde_sin_foto_no_sale(self):
        p = {"id": "2026-11-18-verde-auto-2026-11-17-loca-th-0300-duelo", "verde_de": "2026-11-17-loca-th-0300-duelo",
             "resultado": "verde", "foto": None, "texto": "PARA DENTRO SEÑORES ✅"}
        self.assertTrue(C.verde_sin_escudos(p))
        self.assertTrue(C.bloquea(p, p["texto"]))

    def test_foto_que_no_existe_tampoco(self):
        p = {"id": "x-verde-auto-y", "verde_de": "y", "foto": "publicaciones/media/no-existe.jpg"}
        self.assertTrue(C.verde_sin_escudos(p))

    def test_con_foto_si(self):
        p = {"id": "x-verde-auto-y", "verde_de": "y", "foto": "REGLAS.md"}
        self.assertIsNone(C.verde_sin_escudos(p))

    def test_rojo_y_picks_no_cuentan(self):
        self.assertIsNone(C.verde_sin_escudos({"id": "a-rojo-auto-b", "rojo_de": "b"}))
        self.assertIsNone(C.verde_sin_escudos({"id": "2026-11-18-pick-claude-1", "sel": ["1|x|y"]}))


if __name__ == "__main__":
    unittest.main()
