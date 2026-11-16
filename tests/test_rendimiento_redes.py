"""16/11 (Marcos: «que me siga la gente»): tipo y formato de cada post, y reparto de los seguidores nuevos de
Threads entre los posts del rato según sus vistas."""
import unittest

import rendimiento_redes as R


class Rendimiento(unittest.TestCase):
    def test_tipos(self):
        self.assertEqual(R.tipo("2026-11-16-escalera"), "escalera")
        self.assertEqual(R.tipo("2026-11-16-ganadores-nations-texto"), "GANADORES")
        self.assertEqual(R.tipo("2026-11-15-combi-partido-123"), "combi de 1 partido")
        self.assertEqual(R.formato({"id": "2026-11-16-ganadores-nations-texto", "sin_foto": True}), "texto")
        self.assertEqual(R.formato({"id": "x-pick-seguro"}), "foto")

    def test_reparto_seguidores(self):
        medidos = {"a": {"ts": "2026-11-16T10:00:00+0000", "m": {"views": 300}},
                   "b": {"ts": "2026-11-16T11:00:00+0000", "m": {"views": 100}},
                   "c": {"ts": "2026-11-10T11:00:00+0000", "m": {"views": 9999}}}   # viejo: no entra
        fotos = {"2026-11-16T12:00:00+00:00": 1000, "2026-11-16T15:00:00+00:00": 1008}
        est = R.repartir_seguidores(medidos, fotos)
        self.assertEqual(est, {"a": 6.0, "b": 2.0})


if __name__ == "__main__":
    unittest.main()
