"""16/11: el Ojeador copió a las 13:43 los mismos picks que Claude había metido a mano (TRADER y Pérez, escritos con
otras palabras y sin sel) → salieron 2 veces en Telegram, y además en Threads/Instagram (copia de un pick sin sel)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import comprobar_post as C  # noqa: E402
import redes  # noqa: E402

A = ("Para esta noche 👀\n\n🍀 Más de 2,5 goles y gol en la 1ª parte en Alemania–Países Bajos (Crear apuesta) @1,52\n\n"
     "⚽ Alemania – Países Bajos · hoy 20:45")
B = ("Otro pick 🔥\n\n🍀 Gol en la 1ª parte y más de 2,5 goles en el partido (Crear apuesta) @1,52\n\n"
     "⚽ Alemania – Países Bajos · hoy 20:45")
OTRO = ("Otro 🔥\n\n🍀 Gol en la 1ª parte y más de 2,5 goles en el partido (Crear apuesta) @1,52\n\n"
        "⚽ Grecia – Serbia · hoy 20:45")


class Duplicados16Nov(unittest.TestCase):
    def test_mismo_pick_con_otras_palabras(self):
        orig = {"id": "2099-06-01-pick-tip-3", "texto": A, "enviado": "2099-06-01T12:17", "sel": []}
        nuevo = {"id": "2099-06-01-pick-tip-6", "texto": B, "sel": [], "solo_en": ["telegram"]}
        self.assertIsNotNone(C.duplicado(nuevo, cola=[orig]))

    def test_otro_partido_no_es_repetido(self):
        orig = {"id": "2099-06-01-pick-tip-3", "texto": A, "enviado": "2099-06-01T12:17", "sel": []}
        nuevo = {"id": "2099-06-01-pick-tip-6", "texto": OTRO, "sel": [], "solo_en": ["telegram"]}
        self.assertIsNone(C.duplicado(nuevo, cola=[orig]))

    def test_copia_sin_sel_solo_telegram(self):
        self.assertTrue(redes.pick_suelto({"id": "2099-06-01-pick-tip-6", "origen": "tipster", "texto": B, "sel": []}))


if __name__ == "__main__":
    unittest.main()
