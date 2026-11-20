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
