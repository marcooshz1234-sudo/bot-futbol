"""16/11 (Marcos): contenido constante en Threads (cada 30 min de día, cada hora de madrugada), combis locas por 50,
100, 500 y 1000, listas y tiros de jugadores habituales. Solo Threads, sin porqué, con las normas de siempre."""
import unittest
from pathlib import Path
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
            {"mercado": "Match Winner", "opcion": "Home", "cuota": 1.8, "prob": 0.52, "familia": "gana", "texto": "Gana L"},
            {"mercado": "Both Teams Score", "opcion": "Yes", "cuota": 1.85, "prob": 0.5, "familia": "ambos", "texto": "Ambos marcan"},
            {"mercado": "Total - Home", "opcion": "Over 1.5", "cuota": 1.75, "prob": 0.54, "familia": "marca", "texto": "L marca 2 o más"},
            {"mercado": "Corners 1x2", "opcion": "Home", "cuota": 1.72, "prob": 0.55, "familia": "corners", "texto": "L más córners"}]}
            for i in range(8)]
        sel, cuota, misma = T.combi_cuota(partidos, 100, "s", {})
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
                         {"mercado": "Match Winner", "opcion": "Home", "cuota": 2.6, "prob": 0.38, "familia": "gana", "texto": "Gana Equipo local"},
                         {"mercado": "Corners 1x2", "opcion": "Home", "cuota": 2.45, "prob": 0.4, "familia": "corners", "texto": "Equipo local hace más córners"}]}
                    for i in range(12)]
        sel, cuota, texto = T.combi_que_quepa(1000, T.combi_cuota(partidos, 1000, "s", {})[0], "s")
        self.assertLessEqual(len(texto), 500)
        real = C.cuota_real_sel([f"{pt['fid']}|{p['mercado']}|{p['opcion']}" for pt, p in sel], [p["cuota"] for _, p in sel])
        self.assertAlmostEqual(cuota, real, places=1)

    def test_escudos(self):
        # partidazo (dos selecciones top) → 6-8 cosas; flojo → 3-4; nunca «gana X» con «X o empate»
        self.assertTrue(T.partidazo({"local_en": "Germany", "visitante_en": "Netherlands"}))
        self.assertFalse(T.partidazo({"local_en": "Gibraltar", "visitante_en": "Malta"}))
        self.assertIn("doble", T.CHOCAN["gana"])
        self.assertEqual(T.ESCUDOS_DIA, (4, 6))

    def test_dia_lleno_mas_posts(self):
        from bot import MADRID
        d = datetime(2026, 11, 16, 0, 0, tzinfo=MADRID)
        self.assertGreater(len(T.huecos("2026-11-16", d, lleno=True)), len(T.huecos("2026-11-16", d)))
        self.assertTrue(T.dia_lleno([{"liga": "UEFA Europa League"}]))
        self.assertFalse(T.dia_lleno([{"liga": "Nations League"}] * 5))

    def test_variadas(self):
        # 18/11: «solo tiros y córners»: primero lo mejor de cada familia
        ps = [{"familia": "jugador"}, {"familia": "jugador"}, {"familia": "goleador"}, {"familia": "ambos"}]
        self.assertEqual([p["familia"] for p in T.variadas(ps)][:3], ["jugador", "goleador", "ambos"])

    def test_texto_sin_partido_repetido(self):
        pt = {"local": "Alemania", "visitante": "Países Bajos"}
        self.assertEqual(T._corto(pt, {"texto": "Ambos marcan en Alemania–Países Bajos"}), "Ambos marcan")


if __name__ == "__main__":
    unittest.main()


class Fallos16Nov(unittest.TestCase):
    """16/11 (vigilante): «La combi de los empates» chocaba con «Gana Islas Feroe» (combi-m), las patas iban sin orden
    de hora, «✅» antes de jugarse (parecía ganada) y Albacete–Celta II (Segunda) en un día de Nations."""

    def _pt(self, fid, h):
        from bot import MADRID
        return {"fid": fid, "ini": datetime(2026, 11, 16, h, 0, tzinfo=MADRID)}

    def test_choca_con_lo_de_hoy(self):
        pt = self._pt(1528987, 16)
        empate = {"mercado": "Match Winner", "opcion": "Draw"}
        self.assertTrue(T.choca_con([(pt, empate)], {(1528987, "Match Winner", "Home"): 1}))
        self.assertFalse(T.choca_con([(pt, empate)], {(1528986, "Match Winner", "Home"): 1}))   # otro partido
        dc = {"mercado": "Double Chance", "opcion": "Home/Draw"}
        self.assertFalse(T.choca_con([(pt, dc)], {(1528987, "Match Winner", "Home"): 1}))       # «o empate» de la loca

    def test_sin_check_antes_de_jugarse(self):
        import re
        self.assertFalse(any(c.startswith("✅") for c in T.CIERRES))
        import inspect
        self.assertNotIn('f"✅ {p', inspect.getsource(T.gana_y_ambos))

    def test_dia_bueno_fuera_partidos_menores(self):
        import inspect
        self.assertIn("fuera_por_dia_bueno", inspect.getsource(T.partidos_del_dia))

    def test_plan_en_orden_y_sin_choques(self):
        import inspect
        src = inspect.getsource(T.plan)
        self.assertIn('sorted(sel, key=lambda x: (x[0]["ini"]', src)
        self.assertIn("choca_con(hecho[2], usados)", src)


class Noche16Nov(unittest.TestCase):
    """16/11 (Marcos: «sí»): de 21:00 a 23:30 salían 0 posts (ya habían empezado los partidos de hoy):
    ahora salen con los partidos de MAÑANA, con id de mañana («-loca-th-noche-») y sin pisar el plan del día."""

    def test_noche_con_lo_de_manana(self):
        from datetime import datetime
        from unittest import mock
        import threads_locas as T
        from bot import MADRID
        visto = {}

        def plan(dia, desde, ya, previos, con_esc, horas=None, max_escudos=None):
            visto.update(dia=dia, horas=[h.strftime("%H:%M") for h in horas], max_escudos=max_escudos)
            return [(horas[0], "lista-ambos", "⚽ AMBOS MARCAN HOY ⚽\n\n1. A–B ➜ Ambos marcan @1,60", ["1|Both Teams Score|Yes"], [1.6])]
        with mock.patch.object(T, "plan", plan), mock.patch.object(T, "leer", lambda *a: []):
            ps = T.posts_noche("2099-06-01", datetime(2099, 6, 1, 21, 10, tzinfo=MADRID))
        self.assertEqual(visto["dia"], "2099-06-02")
        self.assertEqual(visto["horas"], ["21:30", "22:00", "22:30", "23:00", "23:30"])
        self.assertEqual(visto["max_escudos"], 1)
        self.assertEqual(ps[0]["id"], "2099-06-02-loca-th-noche-2130-lista-ambos")
        self.assertEqual(ps[0]["fecha"], "2099-06-01T21:30")
        self.assertIn("MAÑANA", ps[0]["texto"])
        self.assertNotIn("HOY", ps[0]["texto"])

    def test_la_noche_no_tapa_el_plan_del_dia(self):
        src = (Path(__file__).resolve().parent.parent / "threads_locas.py").read_text(encoding="utf-8")
        self.assertIn('"-loca-th-noche-" not in p["id"] for p in auto', src)
