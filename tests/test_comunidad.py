import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import comunidad as C
from bot import MADRID


class Comunidad(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.p = [mock.patch.object(C, "PICKS", self.d / "p.json"), mock.patch.object(C, "ESTADO", self.d / "e.json"),
                  mock.patch.object(C, "partidos_abiertos", return_value=[
                      {"id": 7, "local": "Inter", "visitante": "Fiorentina", "inicio": datetime(2026, 10, 27, 20, 45, tzinfo=MADRID)}])]
        for x in self.p:
            x.start()
        self.ahora = datetime(2026, 10, 26, 12, 0, tzinfo=MADRID)

    def tearDown(self):
        for x in self.p:
            x.stop()

    def test_un_pick_al_dia_y_ranking(self):
        r = C.responder("/pick Más de 2,5 goles en Inter–Fiorentina", {"id": 1, "first_name": "Ana"}, self.ahora)
        self.assertIn("Apuntado", r)
        self.assertIn("ya tienes", C.responder("/pick Gana el Inter", {"id": 1, "first_name": "Ana"}, self.ahora))
        picks = json.loads((self.d / "p.json").read_text())
        (self.d / "e.json").write_text(json.dumps({"resultados": {C.clave(picks[0]): "verde"}}))
        self.assertIn("Ana · 1/1", C.responder("/ranking", {"id": 2}, self.ahora))

    def test_no_entiende(self):
        self.assertIn("No lo he entendido", C.responder("/pick hola que tal", {"id": 3}, self.ahora))

    def test_otro_mensaje_explica_el_concurso(self):
        self.assertIn("CONCURSO", C.responder("hola", {"id": 3}, self.ahora))


if __name__ == "__main__":
    unittest.main()
