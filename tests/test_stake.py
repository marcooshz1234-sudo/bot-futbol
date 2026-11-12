import unittest
from datetime import datetime

from bot import MADRID


class Stake(unittest.TestCase):
    """12/11 (Marcos: «siempre pones stake 2 en las publicaciones, no queda bien poner tantas veces eso»)."""
    def test_copias(self):
        import copiar_tipsters as C
        ini = datetime(2026, 11, 12, 20, 45, tzinfo=MADRID)
        ahora = datetime(2026, 11, 12, 12, 0, tzinfo=MADRID)
        pk = {"tipster": "X", "dia": "2026-11-12", "local": "A", "visitante": "B", "texto": "Gana A", "cuota": 1.5,
              "partido_id": 1, "mercado": "Match Winner", "opcion": "Home", "_ini": ini}
        self.assertNotIn("Stake", C.post_suelto(dict(pk, stake=2), ini, ahora, 1)["texto"])
        self.assertNotIn("Stake", C.post_suelto(pk, ini, ahora, 1)["texto"])          # sin stake suyo = 2
        self.assertIn("Stake 3/10", C.post_suelto(dict(pk, stake=3), ini, ahora, 1)["texto"])
        self.assertNotIn("Stake", C.post_combi([pk, dict(pk, partido_id=2)], ahora, 1)["texto"])

    def test_plantilla_solo_si_no_es_2(self):
        src = open(__import__("plantillas").__file__, encoding="utf-8").read()
        self.assertIn("if con_stake and stake(p) != 2", src)


if __name__ == "__main__":
    unittest.main()
