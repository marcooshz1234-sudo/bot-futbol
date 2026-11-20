import unittest
import tipsters_auto as T


class BoletosMalLeidos(unittest.TestCase):
    """20/11 (Marcos: «mira bien las fotos dentro de cada canal»): dos boletos leídos mal."""
    def test_doble_oportunidad_no_es_empate(self):
        # INSIDER: «Doble oportunidad Ath Bilbao o empate 1,14» se apuntó como «empate en Porto–Paredes»
        self.assertIsNone(T.mercado(T.norm("Doble oportunidad Ath Bilbao o empate"), False, False))
        self.assertIn("ath bilbao", T.fichas("Athletic Club"))

    def test_goles_del_equipo(self):
        # Cobrich: «Bayern de Múnich - más de 2.5 / Equipo local - Goles» = goles del Bayern, no del partido
        self.assertEqual(T.mercado(T.norm("Bayern de Múnich - más de 2.5 Equipo local - Goles"), True, False),
                         ("Total - Home", "Over 2.5"))
        self.assertEqual(T.mercado(T.norm("Colonia anota más de 0.5"), False, True), ("Total - Away", "Over 0.5"))

    def test_empate_sigue_valiendo(self):
        self.assertEqual(T.mercado(T.norm("Empate"), False, False), ("Match Winner", "Draw"))


if __name__ == "__main__":
    unittest.main()
