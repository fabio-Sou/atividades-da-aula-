import unittest

from metricas import (
    CPU_COUNTER_PATH,
    PDH_CSTATUS_NEW_DATA,
    PDH_CSTATUS_VALID_DATA,
    normalize_cpu_percent,
)


class CpuCalculationTests(unittest.TestCase):
    def test_uses_processor_utility_counter_path(self):
        self.assertEqual(
            CPU_COUNTER_PATH,
            r"\Processor Information(_Total)\% Processor Utility",
        )

    def test_accepts_valid_performance_counter_values(self):
        self.assertEqual(normalize_cpu_percent(17.2, PDH_CSTATUS_VALID_DATA), 17.2)
        self.assertEqual(normalize_cpu_percent(27.0, PDH_CSTATUS_NEW_DATA), 27.0)

    def test_clamps_counter_value_to_the_percent_range(self):
        self.assertEqual(normalize_cpu_percent(120.0, PDH_CSTATUS_VALID_DATA), 100.0)
        self.assertEqual(normalize_cpu_percent(-1.0, PDH_CSTATUS_VALID_DATA), 0.0)

    def test_rejects_invalid_counter_status(self):
        with self.assertRaises(OSError):
            normalize_cpu_percent(17.2, 0xC0000BB8)

    def test_rejects_non_finite_counter_value(self):
        with self.assertRaises(OSError):
            normalize_cpu_percent(float("nan"), PDH_CSTATUS_VALID_DATA)


if __name__ == "__main__":
    unittest.main()
