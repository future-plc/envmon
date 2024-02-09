import unittest
from envmon import equations


class TestSeaLevelPressure(unittest.TestCase):
    def test_inputs(self):
        actual = 9.2042
        pressure = 9.2
        alt = 21.0
        slp = equations.sea_level_pressure(alt, pressure)
        self.assertAlmostEqual(slp, actual, 2)
