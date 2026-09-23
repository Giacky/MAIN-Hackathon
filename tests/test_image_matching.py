"""Photo-score blend and geometry helpers. No real LightGlue weights required."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("LOST_FOUND_MOCK_ML", "1")

from services.image_matching import (
    _DINO_WEIGHT,
    _GLUE_WEIGHT,
    _SAME_OBJECT_DINO_MIN,
    blend_photo_score,
    count_geometric_inliers,
    same_object_decision,
)


class PhotoBlendTests(unittest.TestCase):
    def test_glue_miss_with_high_dino_is_dino(self) -> None:
        self.assertAlmostEqual(blend_photo_score(0.91, 0.0), 0.91)
        self.assertNotAlmostEqual(blend_photo_score(0.91, 0.0), 0.35 * 0.91)

    def test_glue_hit_uses_weighted_blend(self) -> None:
        expected = _DINO_WEIGHT * 0.8 + _GLUE_WEIGHT * 0.4
        self.assertAlmostEqual(blend_photo_score(0.8, 0.4), expected)
        self.assertAlmostEqual(expected, 0.35 * 0.8 + 0.65 * 0.4)

    def test_clamps_dino_on_glue_miss(self) -> None:
        self.assertEqual(blend_photo_score(1.4, 0.0), 1.0)
        self.assertEqual(blend_photo_score(-0.2, 0.0), 0.0)


class SameObjectDecisionTests(unittest.TestCase):
    def test_inliers_lock_counts(self) -> None:
        self.assertTrue(same_object_decision(0.1, 4))
        self.assertTrue(same_object_decision(0.0, 10))

    def test_dino_band_without_geometry(self) -> None:
        self.assertTrue(same_object_decision(_SAME_OBJECT_DINO_MIN, 0))
        self.assertTrue(same_object_decision(0.47, None))
        self.assertFalse(same_object_decision(_SAME_OBJECT_DINO_MIN - 0.01, 0))
        self.assertFalse(same_object_decision(0.07, 3))


class GeometricInlierTests(unittest.TestCase):
    def test_too_few_points_are_zero(self) -> None:
        self.assertEqual(
            count_geometric_inliers(
                [[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]],
                [[0.0, 1.0], [1.0, 2.0], [2.0, 3.0]],
            ),
            0,
        )

    def test_planar_correspondences_use_homography(self) -> None:
        import numpy as np

        rng = np.random.default_rng(0)
        pts0 = rng.uniform(10.0, 200.0, size=(30, 2)).astype(np.float32)
        pts1 = pts0 * np.float32(1.2) + np.array([15.0, -8.0], dtype=np.float32)
        self.assertGreaterEqual(count_geometric_inliers(pts0, pts1), 4)


if __name__ == "__main__":
    unittest.main()
