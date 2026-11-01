import unittest

from sk_llm_eval.checks import normalize, run_check


class TestChecks(unittest.TestCase):
    def test_contains_ci(self):
        ok, _ = run_check({"type": "contains", "value": "bratislava"}, "Je to Bratislava.")
        self.assertTrue(ok)

    def test_not_contains(self):
        ok, _ = run_check({"type": "not_contains", "value": "Bratislavi"}, "do Bratislavy")
        self.assertTrue(ok)

    def test_exact_strips_period(self):
        ok, _ = run_check({"type": "exact", "value": "koní"}, "Koní.")
        self.assertTrue(ok)

    def test_regex_case_sensitive_by_default(self):
        ok, _ = run_check({"type": "regex", "value": r"\bVám\b"}, "ďakujem vám")
        self.assertFalse(ok)
        ok, _ = run_check({"type": "regex", "value": r"\bVám\b", "flags": "i"}, "ďakujem vám")
        self.assertTrue(ok)

    def test_not_regex(self):
        ok, _ = run_check({"type": "not_regex", "value": r"\bby ste\b"}, "Mohol by si mi pomôcť?")
        self.assertTrue(ok)

    def test_normalize_nbsp(self):
        self.assertEqual(normalize("1 000  €"), "1 000 €")


if __name__ == "__main__":
    unittest.main()
