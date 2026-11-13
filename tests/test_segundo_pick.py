"""13/11: el 2º pick (18:00) repetía el de las 10:30 ya publicado (Andorra gana alguna de las dos partes),
porque al recalcular, el «primero» era otro (un tipster de la tarde). Ahora se aparta del que ya salió
y no repite un pick ya publicado ese día."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import combis_dia


def pk(pid, m, o, c, pr):
    return {"partido_id": pid, "mercado": m, "opcion": o, "cuota": c, "prob_aprendida": pr, "texto": f"{m} {o}",
            "fecha": "2026-11-20T20:45", "tipo": "resultado", "local": "A", "visitante": "B"}


class SegundoPick(unittest.TestCase):
    def test_seguro_publicado(self):
        with tempfile.TemporaryDirectory() as d:
            pub = Path(d) / "publicaciones"
            pub.mkdir()
            (pub / "auto.json").write_text(json.dumps([{"id": "2026-11-20-pick-seguro", "sel": ["77|To Win Either Half|Home"]}]))
            (pub / "enviados.json").write_text(json.dumps({"2026-11-20-pick-seguro": {"enviado": "2026-11-20T10:30"}}))
            with mock.patch("bot.RAIZ", Path(d)):
                self.assertEqual(combis_dia.seguro_publicado("2026-11-20"), {"partido_id": 77})
                self.assertIsNone(combis_dia.seguro_publicado("2026-11-21"))

    def test_no_repite_lo_publicado(self):
        pools = [[pk(77, "To Win Either Half", "Home", 1.55, .8)], [pk(88, "Goals Over/Under", "Over 1.5", 1.55, .75)]]
        with mock.patch.object(combis_dia, "pick_de_tipster", return_value=None), \
                mock.patch.object(combis_dia, "pick_de_copa", return_value=None), \
                mock.patch.object(combis_dia, "fijisimo", return_value=True), \
                mock.patch.object(combis_dia, "suelto_no", return_value=False), \
                mock.patch.object(combis_dia, "familia", return_value="resultado"), \
                mock.patch.dict(combis_dia.SEGURO, {"familias": ["resultado"], "prob_min": 0.5}):
            r = combis_dia.pick_seguro(pools, "2026-11-20", segundo={"partido_id": 77},
                                       ya=[("77", "To Win Either Half", "Home")])
        self.assertIsNotNone(r)
        self.assertEqual(r[0]["partido_id"], 88)


if __name__ == "__main__":
    unittest.main()
