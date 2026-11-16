"""16/11: las copias salían con «más de 2.5 goles» / «2.5 tiros» (punto inglés) en Telegram."""
import unittest

import nombres as N


class DecimalComa16Nov(unittest.TestCase):
    def test_lineas_y_cuotas(self):
        self.assertEqual(N.espanol("ambos marcan + más de 2.5 goles @1.60"), "ambos marcan + más de 2,5 goles @1,60")
        self.assertEqual(N.espanol("Escocia más de 2.5 tiros a puerta"), "Escocia más de 2,5 tiros a puerta")
        self.assertEqual(N.espanol("Islandia -1.5"), "Islandia -1,5")

    def test_no_toca_horas_miles_ni_enlaces(self):
        for t in ("a las 21.00", "20.45h", "3.000 €", "https://t.me/a1.5", "v2.5.1", "1.ª parte"):
            self.assertEqual(N.espanol(t), t)


if __name__ == "__main__":
    unittest.main()
