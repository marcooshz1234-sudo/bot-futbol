"""13/11 (Marcos: «¿por qué pone lo de MyMatch en la publicación? Eso no lo vuelvas a poner»).

El «Crear apuesta» de TipsPro (Países Bajos–Grecia @1,54) salió bien como pick; después otra IA lo partió en patas
«(pata de su MyMatch @1,54)» y salió OTRA VEZ como combi, con @1,54 en cada pata (cuota falsa 2,37)."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import comprobar_post as CP
import copiar_tipsters as C
from bot import MADRID


class CopiarMyMatch(unittest.TestCase):
    def test_texto_limpio(self):
        self.assertEqual(C.limpiar("Grecia no marca 3 (pata de su MyMatch @1,54)"), "Grecia no marca 3")
        self.assertEqual(C.limpiar("Gana PB y +1,5 (MyMatch)"), "Gana PB y +1,5")
        self.assertNotIn("MyMatch", C.limpiar("MyMatch: Francia marca"))

    def test_comprobar_bloquea(self):
        p = {"id": "2026-11-13-combi-tip-1", "texto": "🍀 Grecia no marca 3 (pata de su MyMatch @1,54) @1,54"}
        with mock.patch.object(CP, "partido_caido", lambda p: None):
            self.assertIn("texto", [r for r, _ in CP.comprobar(p, otros={})])

    def test_no_se_copia_dos_veces_ni_se_multiplica(self):
        base = {"tipster": "TipsPro", "dia": "2026-11-13", "local": "Netherlands", "visitante": "Greece", "partido_id": 9}
        tips = [dict(base, fuente="t/1", texto="PB gana una parte, +1,5 y Grecia no marca 3 (Crear apuesta)",
                     mercado="To Win Either Half", opcion="Home", cuota=1.54),
                dict(base, fuente="t/1", combinada="t/1", texto="Más de 1,5 goles (pata de su MyMatch @1,54)",
                     mercado="Goals Over/Under", opcion="Over 1.5", cuota=1.54),
                dict(base, fuente="t/1", combinada="t/1", texto="Grecia no marca 3", mercado="Total - Away",
                     opcion="Under 2.5", cuota=1.54)]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            ini = datetime(2026, 11, 13, 20, 45, tzinfo=MADRID)
            with mock.patch.object(C, "DATOS", d), mock.patch.object(C, "REGISTRO", d / "r.json"), \
                    mock.patch.object(C, "COLA", d / "cola.json"), mock.patch.object(C, "inicio", lambda pk: ini), \
                    mock.patch.object(C, "motivo_no", lambda x, u: None), \
                    mock.patch.object(C, "cuota_bet365", lambda x: (x.get("cuota"), False)):
                (d / "tipsters.json").write_text(json.dumps(tips[:1]))
                primero = C.main(datetime(2026, 11, 13, 14, 0, tzinfo=MADRID))
                self.assertEqual(len(primero), 1)
                (d / "tipsters.json").write_text(json.dumps(tips))   # luego llegan sus patas por separado
                self.assertEqual(C.main(datetime(2026, 11, 13, 16, 0, tzinfo=MADRID)), [])
            with mock.patch.object(C, "DATOS", d), mock.patch.object(C, "REGISTRO", d / "r2.json"), \
                    mock.patch.object(C, "COLA", d / "cola2.json"), mock.patch.object(C, "inicio", lambda pk: ini), \
                    mock.patch.object(C, "motivo_no", lambda x, u: None), \
                    mock.patch.object(C, "cuota_bet365", lambda x: (x.get("cuota"), False)):
                (d / "tipsters.json").write_text(json.dumps(tips[1:]))   # solo las patas: mismo partido → no
                self.assertEqual(C.main(datetime(2026, 11, 13, 16, 0, tzinfo=MADRID)), [])


if __name__ == "__main__":
    unittest.main()


class MismoPickDosCanales(unittest.TestCase):
    """14/11: «Gana el Almería» salió dos veces (STAKE REAL 11:12 y TipsAnalistas 12:36)."""

    def test_mismo_pick(self):
        import copiar_tipsters as C
        a = {"dia": "2026-11-14", "local": "Almería", "visitante": "FC Andorra", "mercado": "Match Winner", "opcion": "Home"}
        b = {"dia": "2026-11-14", "local": "Almeria", "visitante": "Andorra", "mercado": "Match Winner", "opcion": "Home"}
        c = dict(b, opcion="Away")
        self.assertEqual(C.mismo_pick(a), C.mismo_pick(b))
        self.assertNotEqual(C.mismo_pick(a), C.mismo_pick(c))
        src = open(C.__file__, encoding="utf-8").read()
        self.assertIn("ese pick ya se ha copiado de otro canal", src)
