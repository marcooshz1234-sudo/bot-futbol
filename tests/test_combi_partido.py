import unittest

import plantillas


def pk(m, o, t, c):
    return {"partido_id": 1, "mercado": m, "opcion": o, "texto": t, "cuota": c}


class CombiPartido(unittest.TestCase):
    def test_formato_como_el_clasico(self):
        cp = {"local": "Barcelona", "visitante": "Real Madrid", "competicion": "LaLiga", "fecha": "2026-10-25T21:00",
              "picks": [pk("Goals Over/Under", "Over 3.5", "Más de 3,5 goles en Barcelona–Real Madrid", 1.5),
                        pk("Both Teams Score", "Yes", "Ambos marcan", 1.24)]}
        t = plantillas.texto_combi_partido(cp, None, 1.86)
        self.assertTrue(t.startswith("✅ COMBI LOCAS | LALIGA\n🇪🇸 BARCELONA vs REAL MADRID 🇪🇸"))
        self.assertIn("🎯 MÁS DE 3,5 GOLES [x1.50]", t)
        self.assertIn("✅ AMBOS MARCAN [x1.24]", t)
        self.assertIn("🟢 VERDE A VERDE 🟢", t)

    def test_marcadores_que_cumplen(self):
        p = pk("Goals Over/Under", "Over 3.5", "", 1.5)
        self.assertTrue(plantillas.cumple(p, 3, 1))
        self.assertFalse(plantillas.cumple(p, 2, 1))
        self.assertIsNone(plantillas.cumple(pk("Corners", "Over 9.5", "", 1.5), 1, 1))


if __name__ == "__main__":
    unittest.main()
