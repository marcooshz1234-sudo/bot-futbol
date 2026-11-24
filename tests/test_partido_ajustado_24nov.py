import unittest
import publicar_telegram as PT
import combis_dia


class MismoPartidoAjustado(unittest.TestCase):
    """24/11 (Marcos: «ajústalo»): en el mismo partido no van dos de goles/resultado, ni más de 2 picks; sí dos de tipos
    distintos (se perdieron Dortmund remates y ambos marcan Madrid–PSV, que habrían acertado)."""
    def q(self, i, sel):
        return {"id": i, "sel": [sel]}

    def test_tipos_distintos_si(self):
        guirassy = self.q("a", "1635611|Away Player Shots|Serhou Guirassy - 2")
        self.assertIsNone(PT.choque_partido(self.q("b", "1635611|Away Player Shots Total|Over 8.5"), [guirassy]))
        obispo = self.q("c", "1635715|Player Fouls Committed|Armando Obispo - 1")
        self.assertIsNone(PT.choque_partido(self.q("d", "1635715|Both Teams Score|Yes"), [obispo]))

    def test_dos_de_goles_no(self):
        marca2 = self.q("a", "9|Total - Home|Over 1.5")
        self.assertEqual(PT.choque_partido(self.q("b", "9|Match Winner|Home"), [marca2]), "a")

    def test_tercero_no(self):
        otros = [self.q("a", "9|Player Fouls Committed|X - 1"), self.q("b", "9|Home Corners Over/Under|Over 4.5")]
        self.assertEqual(PT.choque_partido(self.q("c", "9|Away Player Shots|Y - 1"), otros), "a")


class DosPartesSoloEquipazo(unittest.TestCase):
    """24/11 (Marcos: «lo de marcan ambas partes no me gusta nada en Telegram; como mucho un equipazo»)."""
    def test(self):
        bodo = {"mercado": "To Score In Both Halves By Teams", "opcion": "Home", "local": "Bodo/Glimt", "visitante": "LASK"}
        self.assertTrue(combis_dia.suelto_no(bodo))
        madrid = dict(bodo, local="Real Madrid")
        self.assertFalse(combis_dia.suelto_no(madrid))


if __name__ == "__main__":
    unittest.main()
