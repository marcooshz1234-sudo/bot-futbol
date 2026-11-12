import unittest
from pathlib import Path


class SoloEnTelegram(unittest.TestCase):
    """12/11: «combi-partido-…-th» (solo_en: threads) salió en Telegram. Telegram respeta «solo_en»."""
    def test_publicar_respeta_solo_en(self):
        src = (Path(__file__).resolve().parent.parent / "publicar_telegram.py").read_text(encoding="utf-8")
        i = src.index('if p.get("solo_en") and "telegram" not in p["solo_en"]')
        self.assertLess(i, src.index("motivo = partido_caido(p)"))


if __name__ == "__main__":
    unittest.main()
