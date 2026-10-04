import unittest

from axiom_cegis import choose_candidate


class CegisTests(unittest.TestCase):
    def test_counterexamples_refine_candidate(self):
        self.assertEqual(choose_candidate([0]).name, "x")
        self.assertEqual(choose_candidate([0, -1]).name, "neg-x")
        self.assertEqual(choose_candidate([0, -1, 1]).name, "abs-branch")


if __name__ == "__main__":
    unittest.main()
