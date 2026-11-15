"""16/11 (Marcos): la tarjeta de 10 selecciones de la Nations salía cortada (la 10.ª a medias) y la borró;
pidió subirla sin foto. Una tarjeta GANADORES de 9-12 filas tiene que caber entera, y «sin_foto» = Threads sin foto."""
import unittest


class GanadoresDiez(unittest.TestCase):
    def test_sin_foto_en_threads(self):
        import redes
        p = {"id": "2026-11-16-ganadores-nations-texto", "texto": "x", "sin_foto": True}
        self.assertIsNone(redes.foto_threads(p))

    def test_diez_filas_caben(self):
        import fotos
        from playwright.sync_api import sync_playwright
        for n in (9, 10, 12):
            filas = [{"nombre": f"Equipo {i}", "pais": "Spain", "bandera": "🇪🇸", "pick": "WIN"} for i in range(n)]
            html = fotos.quien_gana(filas, "NATIONS LEAGUE", lema="¿PLENO HOY?")
            with sync_playwright() as p:
                b = p.chromium.launch()
                pg = b.new_page(viewport={"width": 1080, "height": 1350})
                pg.set_content(html)
                alto = pg.evaluate("document.body.scrollHeight")
                b.close()
            self.assertLessEqual(alto, 1350, f"{n} filas: {alto}px")


if __name__ == "__main__":
    unittest.main()
