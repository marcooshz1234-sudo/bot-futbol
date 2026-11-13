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

    def test_segundo_pick_seguro(self):   # 13/11: el pick seguro de las 18:00 salía sin foto (la de marca es solo el 1º)
        self.assertTrue(T.toca({"id": "2026-11-13-pick-seguro-2"}))
        self.assertFalse(T.toca({"id": "2026-11-13-pick-seguro"}))
        f = T.fila("Andorra gana alguna de las dos partes")
        self.assertEqual((f["nombre"], f["pick"], f["pais"]), ("Andorra", "GANA UNA PARTE", "Andorra"))

    def test_crear_apuesta_con_partido(self):
        # 13/11 (Marcos: «pon en la foto lo que es el pick, no solo en el texto»): una fila por condición
        fs = T.filas(["Serbia más de 6,5 remates y más de 1,5 goles en el partido (Crear apuesta)"], "Serbia – Alemania")
        self.assertEqual([(f["nombre"], f["pick"]) for f in fs], [("Serbia", "+6,5 REMATES"), ("Partido", "+1,5 GOLES")])
        fs = T.filas(["Países Bajos gana alguna de las dos partes, más de 1,5 goles y Grecia no marca 3 (Crear apuesta)"])
        self.assertEqual([f["pick"] for f in fs], ["GANA UNA PARTE", "+1,5 GOLES", "NO MARCA 3"])
        self.assertEqual(T.titulo({"id": "x-pick-tip-6"}, "🍀 Serbia más de 6,5 remates (Crear apuesta) @1,53"),
                         "CREAR APUESTA · @1,53")

    def test_no_siempre_foto(self):   # «me gusta más con foto, pero que el canal no esté solo con fotos»
        con = lambda i: {"enviado": f"2026-11-13T1{i}:00", "mensaje_id": i + 1, "foto_tg": "x.jpg"}
        sin = lambda i: {"enviado": f"2026-11-13T1{i}:00", "mensaje_id": i + 1}
        self.assertEqual(T.racha_fotos([sin(0), con(1), con(2)]), 2)
        self.assertEqual(T.racha_fotos([con(0), con(1), con(2)]), 3)
        self.assertIsNone(T.hacer({"id": "x-pick-tip-1"}, NOCHE, [con(0), con(1), con(2)]))

    def test_escudo_de_club(self):   # 13/11: los clubes con su escudo; las selecciones con su bandera
        from unittest import mock
        with mock.patch.object(T, "escudo_club", return_value="/x/541.png"):
            self.assertEqual(T.fila("Gana el Real Madrid")["escudo"], "/x/541.png")
            self.assertEqual(T.fila("Gana Suiza")["escudo"], "")

    def test_logos_buenos(self):   # 13/11 (Marcos: «ese logo no tiene calidad»): logos de competición grandes
        from PIL import Image
        for lid in (2, 3, 5, 39, 61, 78, 135, 140, 143, 525, 848):
            im = Image.open(T.MEDIA / "escudos" / f"liga-{lid}-hd.png")
            self.assertGreaterEqual(max(im.size), 650, lid)

    def test_sin_argumento_fuera(self):   # el «Sin argumento: solo el pick» de las copias
        import copiar_tipsters as C
        src = open(C.__file__, encoding="utf-8").read()
        self.assertIn("sin argumento", src.lower())


if __name__ == "__main__":
    unittest.main()
