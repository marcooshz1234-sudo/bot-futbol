"""18/11 (Marcos: «este resumen habría que mejorarlo» → «foto»): foto con la lista y las banderas, «8/8», lo que se
gana con 10 € a cada pick y el texto corto. Y banderas que faltaban (Bosnia, Corea del Sur, Irlanda)."""
import unittest

import fotos
import resumen_dia as R


def post(pid, textos, cuota, est="verde", partido_id=1, partido="Polonia – Suecia"):
    return (pid, [{"texto": t, "partido_id": partido_id, "partido": partido, "estado": est} for t in textos], est, cuota)


class ResumenFoto18Nov(unittest.TestCase):
    def test_filas_cortas_sin_partido_y_tarjetas_2mas(self):
        rp = [post("a", ["Polonia ve más de 1,5 tarjetas"], 1.67),
              post("b", ["Más de 6,5 córners en Polonia–Suecia", "Más de 1,5 goles en Polonia–Suecia"], 1.50)]
        f = R.filas_resumen(rp)
        self.assertEqual(f[0]["texto"], "Polonia ve 2+ tarjetas · @1,67")
        self.assertEqual(f[1]["texto"], "7+ córners + más de 1,5 goles · @1,50")

    def test_ganancia_10_euros(self):
        rp = [post("a", ["x"], 1.73), post("b", ["y"], 1.40), post("c", ["z"], 1.50, est="rojo")]
        self.assertEqual(R.ganancia(rp), round(7.3 + 4.0 - 10, 2))
        self.assertIsNone(R.ganancia([post("a", ["x"], None)]))

    def test_texto_corto_pleno(self):
        rp = [post(str(i), ["x"], 1.5) for i in range(3)]
        t = R.texto_corto(rp, "2026-11-17")
        self.assertIn("🔥 PLENO: 3 de 3 en verde", t)
        self.assertIn("+15,00 €", t)
        self.assertNotIn("sueltos", t)

    def test_fallos_pasan_al_texto(self):
        rp = [post("a", ["x"], 1.5), post("b", ["y"], 1.5, est="rojo")]
        t = R.texto_corto(rp, "2026-11-17", "📊 …\n\n😤 Se nos escaparon:\n🔸 Gana X · 0-1\n\n🔔 Mañana")
        self.assertIn("😤 Se nos escaparon:", t)
        self.assertIn("✅ 1 de 2 picks en verde", t)

    def test_banderas_que_faltaban(self):
        for p in ("Bosnia & Herzegovina", "South Korea", "Rep. Of Ireland"):
            self.assertTrue(fotos.bandera_real(p), p)

    def test_main_usa_foto(self):
        self.assertIn("foto_resumen(rp, hoy", open(R.__file__, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main()
