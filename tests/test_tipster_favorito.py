"""16/11: (1) el acierto de un canal salía partido en dos por los emojis de su nombre; (2) Marcos: «la de Tipster
Pérez… me gusta mucho» → sus picks se copian siempre (sin nota ni tope de 1,80), salvo suelo y motivación."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import copiar_tipsters as C  # noqa: E402


class TipsterFavorito(unittest.TestCase):
    def test_nombres_con_y_sin_emojis_suman(self):
        datos = {"tipster": {"TRADER FOOTBALL || FREE👨🏼‍💻": {"verdes": 3, "rojos": 0},
                             "TRADER FOOTBALL || FREE": {"verdes": 3, "rojos": 2},
                             "𝐌𝐀𝐗 𝐀𝐍𝐀𝐋𝐈𝐒𝐓𝐀 ⚜️": {"verdes": 2, "rojos": 0}, "MAX ANALISTA": {"verdes": 3, "rojos": 0}}}
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "tipsters_aprendizaje.json").write_text(json.dumps(datos))
            with mock.patch.object(C, "DATOS", Path(d)):
                self.assertAlmostEqual(C.acierto_tipster("TRADER FOOTBALL || FREE"), (6 + 2) / (8 + 4))
                self.assertAlmostEqual(C.acierto_tipster("MAX ANALISTA"), (5 + 2) / (5 + 4))

    def test_perez_es_favorito(self):
        self.assertTrue(C.favorito("Tipster Pérez"))
        self.assertTrue(C.favorito("Tipster Perez"))
        self.assertFalse(C.favorito("AllSportsPicks ⚽🏀🎾"))

    def test_perez_pasa_con_nota_baja_y_cuota_alta(self):
        x = {"tipster": "Tipster Pérez", "texto": "Gana el Getafe"}
        otro = dict(x, tipster="AllSportsPicks ⚽🏀🎾")
        with mock.patch.object(C, "acierto_tipster", lambda n: 0.45), mock.patch.object(C, "sel_de", lambda x: None):
            self.assertIsNone(C.calidad_no(x, 1.95, [x]))
            self.assertIsNotNone(C.calidad_no(otro, 1.95, [otro]))

    def test_perez_no_pasa_lo_muy_arriesgado(self):
        x = {"tipster": "Tipster Pérez", "texto": "Gana el Getafe"}
        with mock.patch.object(C, "sel_de", lambda x: None):
            self.assertIsNotNone(C.calidad_no(x, 4.50, [x]))


if __name__ == "__main__":
    unittest.main()
