"""13/11 (Marcos: «estas, cuando estén en directo, si se aciertan que se pongan en verde automáticamente»)."""
import re
import unittest
from pathlib import Path


class PicksEnDirecto(unittest.TestCase):
    def test_va_bien_se_ve_en_la_pestana_picks(self):
        html = (Path(__file__).resolve().parent.parent / "docs" / "index.html").read_text(encoding="utf-8")
        cuerpo = html[html.index("function vPicksDia"):]
        cuerpo = cuerpo[:cuerpo.index("\n}\n")]
        self.assertRegex(cuerpo, r'e==="va_bien"\?.*Va bien')
        self.assertNotRegex(cuerpo, r'e==="va_mal"\?')   # lo que va mal no se marca


if __name__ == "__main__":
    unittest.main()
