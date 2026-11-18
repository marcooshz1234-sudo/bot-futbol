"""18/11 (Marcos: «algún pick de hoy también ha salido sin escudo»): la combi del miércoles y la de las favoritas salieron
en Telegram sin foto (patas sin @cuota, «combi-favoritas» fuera de CON_TARJETA). Toda combi de Telegram, con escudos."""
import unittest

import tarjeta_tg as T

TEXTO = ("Combi de las favoritas 🔥\n\n🏆 Gana el Real Madrid (fem.) · vs Inter · 18:45\n"
         "⚽ Más de 1,5 goles en la 2ª parte del Real Madrid (fem.)–Inter Milano (fem.)\n\n📈 Cuota @2,62\n\n"
         "🧠 Por qué:\n👨‍💻 Muy favoritas")


class CombisConEscudos(unittest.TestCase):
    def test_cualquier_combi_toca(self):
        for pid in ("2026-11-18-combi-favoritas", "2026-11-18-combi-tres", "2026-11-18-combi-m", "2026-11-18-combi-tip-1"):
            self.assertTrue(T.toca({"id": pid}), pid)
        self.assertFalse(T.toca({"id": "2026-11-18-verde-auto-2026-11-18-combi-tres", "verde_de": "x"}))

    def test_patas_sin_cuota(self):
        ps = T.patas_sin_cuota(TEXTO.split("🧠 Por qué")[0])
        self.assertEqual(ps[0], "Gana el Real Madrid (fem.)")
        self.assertEqual(len(ps), 2)

    def test_segunda_parte(self):
        f = T.fila("Más de 1,5 goles en la 2ª parte del Real Madrid (fem.)–Inter Milano (fem.)")
        self.assertEqual(f["pick"], "+1,5 GOLES 2ªP")

    def test_sin_foto_no_sale(self):
        src = open(T.RAIZ / "publicar_telegram.py", encoding="utf-8").read()
        self.assertIn('re.search(r"-(pick|combi)-|-combi$"', src)


if __name__ == "__main__":
    unittest.main()
