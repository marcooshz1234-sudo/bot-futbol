import unittest
from unittest import mock

import revisor


class TestProximosConFecha(unittest.TestCase):
    def test_proximos_lleva_fecha(self):
        falso = {"partido": {"fixture": {"id": 1, "date": "2026-10-26T20:00:00+00:00"},
                             "teams": {"home": {"name": "Sevilla"}, "away": {"name": "Osasuna"}}}}
        with mock.patch.object(revisor, "leer", return_value=falso), \
                mock.patch.object(revisor, "EXTRA", mock.Mock(glob=lambda _: ["x.json"])):
            self.assertEqual(revisor.proximos()[0]["fecha"], "2026-10-26")


if __name__ == "__main__":
    unittest.main()
