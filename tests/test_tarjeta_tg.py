"""13/11 (Marcos: «en Telegram sube un poco más de fotos, no tanto texto»): tarjeta con banderas y texto corto."""
import unittest

import tarjeta_tg as T

NOCHE = ("Combinada de selecciones para esta noche 🔥\n\n🇨🇭 Gana Suiza (Eslovenia – Suiza) @1,70\n"
         "🇦🇿 Azerbaiyán marca 2 o más (Liechtenstein – Azerbaiyán) @1,57\n\n⏰ Las dos a las 20:45\n\n"
         "👨‍💻 Suiza le ganó 2–1 y 3–0\n\n📈 Cuota @2,67")


class TarjetaTG(unittest.TestCase):
    def test_combi_noche(self):
        p = {"id": "2026-11-13-combi-noche-1"}
        self.assertTrue(T.toca(p))
        self.assertEqual(T.titulo(p, NOCHE), "COMBI DE LA NOCHE · @2,67")
        filas = [T.fila(x) for x in T.patas(NOCHE)]
        self.assertEqual([(f["nombre"], f["pick"], f["pais"]) for f in filas],
                         [("Suiza", "GANA", "Switzerland"), ("Azerbaiyán", "2+ GOLES", "Azerbaijan")])
        corto = T.texto_corto(NOCHE)
        self.assertNotIn("👨‍💻", corto)
        self.assertNotIn("⏰", corto)
        self.assertIn("📈 Cuota @2,67", corto)

    def test_no_toca(self):
        for pid in ("2026-11-13-verde-grupo-1", "2026-11-13-escalera", "2026-11-12-balance-auto",
                    "2026-11-13-pick-seguro", "2026-11-13-ganadores-a"):
            self.assertFalse(T.toca({"id": pid}), pid)
        self.assertFalse(T.toca({"id": "2026-11-13-combi-partido-1-th", "tarjeta": {"x": 1}}))

    def test_cuotaza_sin_linea_de_lo_normal(self):
        t = "🚨 CUOTAZA 🚨\n\n🍀 Ambos marcan en Andorra–Gibraltar @3,25\n\n👀 Lo normal sería @3,00: corred"
        self.assertEqual(T.patas(t), ["Ambos marcan en Andorra–Gibraltar"])
        self.assertEqual(T.fila(T.patas(t)[0])["pick"], "AMBOS MARCAN")
        self.assertEqual(T.titulo({"id": "x-cuotaza-1"}, t), "CUOTAZA · @3,25")

    def test_sin_argumento_fuera(self):   # el «Sin argumento: solo el pick» de las copias
        import copiar_tipsters as C
        src = open(C.__file__, encoding="utf-8").read()
        self.assertIn("sin argumento", src.lower())


if __name__ == "__main__":
    unittest.main()
