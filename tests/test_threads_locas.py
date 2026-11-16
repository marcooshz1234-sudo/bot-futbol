"""16/11 (Marcos): contenido constante en Threads (cada 30 min de día, cada hora de madrugada), combis locas por 50,
100, 500 y 1000, listas y tiros de jugadores habituales. Solo Threads, sin porqué, con las normas de siempre."""
import unittest
from datetime import datetime

import threads_locas as T


class ThreadsLocas(unittest.TestCase):
    def test_huecos(self):
        from bot import MADRID
        h = T.huecos("2026-11-16", datetime(2026, 11, 16, 0, 0, tzinfo=MADRID))
        horas = [x.strftime("%H:%M") for x in h]
        self.assertIn("03:00", horas)
        self.assertNotIn("03:30", horas)        # de madrugada, cada hora
        self.assertIn("12:30", horas)           # de día, cada media hora
        self.assertEqual(horas[-1], "00:30")    # hasta la 01:00

    def test_combi_cuota_respeta_patas(self):
        from bot import MADRID
        ini = datetime(2026, 11, 16, 20, 45, tzinfo=MADRID)
        partidos = [{"fid": i, "ini": ini, "local": f"L{i}", "visitante": f"V{i}", "local_en": "x", "patas": [
            {"mercado": "Match Winner", "opcion": "Home", "cuota": 1.5, "prob": 0.62, "familia": "gana", "texto": "Gana L"},
            {"mercado": "Both Teams Score", "opcion": "Yes", "cuota": 1.6, "prob": 0.58, "familia": "ambos", "texto": "Ambos marcan"},
            {"mercado": "Total - Home", "opcion": "Over 0.5", "cuota": 1.3, "prob": 0.7, "familia": "marca", "texto": "L marca"},
            {"mercado": "Corners 1x2", "opcion": "Home", "cuota": 1.45, "prob": 0.6, "familia": "corners", "texto": "L más córners"}]}
            for i in range(8)]
        sel, cuota, misma = T.combi_cuota(partidos, 100, "s", set())
        self.assertGreaterEqual(cuota, 60)
        for fid in {pt["fid"] for pt, _ in sel}:
            fams = {p["familia"] for pt, p in sel if pt["fid"] == fid}
            self.assertFalse({"ambos", "marca"} <= fams)   # no van juntas en el mismo partido

    def test_enlace_y_estilo(self):
        import redes
        import estilo_threads
        self.assertTrue(redes.lleva_enlace({"id": "2026-11-16-loca-th-1000-x50", "enlace_telegram": True}))
        self.assertFalse(redes.lleva_enlace({"id": "2026-11-16-loca-th-1030-x50", "enlace_telegram": False}))
        t = "💎 COMBI x442 💎\n\n🏆 Gana Malta"
        self.assertEqual(estilo_threads.estilo(t, "2026-11-16-loca-th-0700-x500"), t)

    def test_tope_de_pata_por_red(self):
        import comprobar_post as C
        base = {"id": "2026-11-16-combi-x", "texto": "x", "cuotas": [1.5, 2.6]}
        self.assertIn("1,80", C.bloquea(dict(base), "x") or "")                       # Telegram: máx. 1,80
        self.assertNotIn("pata de más", C.bloquea(dict(base, solo_en=["threads"]), "x") or "")   # Threads: hasta 9

    def test_variedad(self):
        # nunca el mismo tipo dos veces seguidas y cada «xN» como mucho 2 al día
        self.assertTrue(all(T.MAX_DIA[k] <= 2 for k in ("x50", "x100", "x500", "x1000")))
        r = T.ROTACION
        self.assertTrue(all(a != b for a, b in zip(r, r[1:])))
        for k in ("ganaambos", "duelo", "empates", "hora", "tapados", "reto"):
            self.assertIn(k, r)

    def test_cuota_como_bet365_y_500_caracteres(self):
        # 16/11: «LA CENTENARIA» de 572 caracteres no salió (Threads: máx. 500) y «x59,32» no cuadraba con bet365
        from bot import MADRID
        import combis_dia as C
        ini = datetime(2026, 11, 16, 20, 45, tzinfo=MADRID)
        partidos = [{"fid": 900 + i, "ini": ini, "local": f"Equipo local {i}", "visitante": f"Equipo visitante {i}",
                     "local_en": "x", "patas": [
                         {"mercado": "Match Winner", "opcion": "Home", "cuota": 1.9, "prob": 0.5, "familia": "gana", "texto": "Gana Equipo local"},
                         {"mercado": "Corners 1x2", "opcion": "Home", "cuota": 1.75, "prob": 0.55, "familia": "corners", "texto": "Equipo local hace más córners"}]}
                    for i in range(12)]
        sel, cuota, texto = T.combi_que_quepa(1000, T.combi_cuota(partidos, 1000, "s", {})[0], "s")
        self.assertLessEqual(len(texto), 500)
        real = C.cuota_real_sel([f"{pt['fid']}|{p['mercado']}|{p['opcion']}" for pt, p in sel], [p["cuota"] for _, p in sel])
        self.assertAlmostEqual(cuota, real, places=1)

    def test_texto_sin_partido_repetido(self):
        pt = {"local": "Alemania", "visitante": "Países Bajos"}
        self.assertEqual(T._corto(pt, {"texto": "Ambos marcan en Alemania–Países Bajos"}), "Ambos marcan")


if __name__ == "__main__":
    unittest.main()
