import unittest
import razones as R


class TablaAFavor(unittest.TestCase):
    """20/11 (Marcos): «Newcastle marca» con «el Arsenal va 1º y el Newcastle 12º» va en contra del pick."""
    def eq(self, texto, opcion=""):
        p = {"texto": texto, "opcion": opcion}
        fl = opcion in ("Home", "Home/Draw")
        fv = opcion in ("Away", "Draw/Away")
        return R.equipo_del_pick(p, "Newcastle", "Arsenal", fl, fv)

    def test_marca(self):
        self.assertEqual(self.eq("Newcastle marca"), "Newcastle")
        self.assertEqual(self.eq("Arsenal marca 2 o más"), "Arsenal")

    def test_gana(self):
        self.assertEqual(self.eq("Gana el Newcastle", "Home"), "Newcastle")

    def test_neutros(self):
        for t in ("Newcastle ve más de 1,5 tarjetas", "Ambos marcan en Newcastle–Arsenal", "Bruno Guimaraes: 2+ tiros",
                  "Más de 1,5 goles en la 2ª parte del Newcastle–Arsenal", "Newcastle hace más córners"):
            self.assertIsNone(self.eq(t), t)
