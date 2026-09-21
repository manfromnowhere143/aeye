from __future__ import annotations

import unittest
from fractions import Fraction

from scripts import coded_mvm_demo as demo


class CodedMvmDemonstratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.matrix = [[3, 1, 4], [1, 5, 9], [2, 6, 5]]
        self.x = [7, 8, 9]
        self.generator = demo.reed_solomon_generator(3, 7)
        self.preprocessed = demo.preprocess(self.matrix, self.generator)
        self.subject = bytes.fromhex("ab" * 32)

    def test_correct_relation_accepts_and_altered_output_rejects(self) -> None:
        y = demo.matrix_vector(self.matrix, self.x)
        self.assertTrue(
            demo.verify(self.preprocessed, self.generator, self.x, y, self.subject, 3, 8)
        )
        altered = y.copy()
        altered[1] = (altered[1] + 1) % demo.FIELD
        self.assertFalse(
            demo.verify(
                self.preprocessed, self.generator, self.x, altered, self.subject, 3, 8
            )
        )

    def test_challenge_is_subject_bound_and_reproducible(self) -> None:
        first = demo.sparse_challenge(self.subject, 0, 7, 3)
        self.assertEqual(first, demo.sparse_challenge(self.subject, 0, 7, 3))
        self.assertNotEqual(first, demo.sparse_challenge(bytes.fromhex("ac" * 32), 0, 7, 3))

    def test_reed_solomon_parameters_and_bound(self) -> None:
        bound = demo.soundness_bound(3, 7, 3, 8)
        self.assertGreater(bound, 0)
        self.assertLess(bound, Fraction(1, 2**40))
        self.assertEqual(5, 7 - 3 + 1)

    def test_dimension_mismatch_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            demo.preprocess(self.matrix, demo.reed_solomon_generator(2, 7))


if __name__ == "__main__":
    unittest.main()
