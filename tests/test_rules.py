"""
Unit tests for the Geometric & Architectural Rule Engine.
Tests all rules, hard-pruning logic, tunable parameters, and composite mesh evaluation.
"""

from backend.app.cv.rules.aspect_ratio import AspectRatioRule
from backend.app.cv.rules.config import CVRuleConfig
from backend.app.cv.rules.elevation import ElevationMonotonicityRule
from backend.app.cv.rules.evaluator import MeshRuleEvaluator
from backend.app.cv.rules.parallelism import BackWallParallelismRule
from backend.app.cv.rules.relative_crease import RelativeCreaseTiltAndKeystoneRule


def test_cv_rule_config_defaults_and_customization():
    """Verify that CVRuleConfig defaults are properly set and can be fine-tuned."""
    cfg = CVRuleConfig()
    assert cfg.max_back_wall_angle_diff_deg == 4.0
    assert cfg.max_crease_mutual_tilt_diff_deg == 5.0
    assert cfg.deadband_y_min_ratio == 0.35
    assert cfg.deadband_y_max_ratio == 0.56

    # Test customization
    custom_cfg = CVRuleConfig(
        max_back_wall_angle_diff_deg=2.5,
        max_crease_mutual_tilt_diff_deg=3.0,
    )
    assert custom_cfg.max_back_wall_angle_diff_deg == 2.5
    assert custom_cfg.max_crease_mutual_tilt_diff_deg == 3.0


def test_back_wall_parallelism_rule():
    """Test BackWallParallelismRule on parallel vs crooked non-parallel walls."""
    rule = BackWallParallelismRule()
    cfg = CVRuleConfig(max_back_wall_angle_diff_deg=4.0, hard_prune_back_wall_angle_diff_deg=7.0)

    # 1. Perfectly parallel horizontal header and tub rim
    pts_parallel = [
        [50, 100],  # 0
        [200, 200],  # 1: Back-Left Top
        [800, 200],  # 2: Back-Right Top (0.0 deg)
        [950, 100],  # 3
        [100, 950],  # 4
        [200, 700],  # 5: Back-Left Tub
        [800, 700],  # 6: Back-Right Tub (0.0 deg)
        [900, 950],  # 7
    ]
    res_parallel = rule.evaluate(pts_parallel, 1000, 1000, cfg)
    assert res_parallel.passed is True
    assert res_parallel.score >= 0.95
    assert res_parallel.is_hard_pruned is False

    # 2. Both tilted by 10 deg (crooked photo, but parallel to each other)
    pts_crooked_parallel = [
        [50, 100],
        [200, 200],
        [800, 305],  # ~10 deg top
        [950, 100],
        [100, 950],
        [200, 700],
        [800, 805],  # ~10 deg bottom
        [900, 950],
    ]
    res_crooked = rule.evaluate(pts_crooked_parallel, 1000, 1000, cfg)
    assert res_crooked.passed is True
    assert res_crooked.score >= 0.90
    assert res_crooked.is_hard_pruned is False

    # 3. Severely non-parallel (top tilted down, bottom tilted up -> divergent)
    pts_divergent = [
        [50, 100],
        [200, 200],
        [800, 350],  # ~14 deg top
        [950, 100],
        [100, 950],
        [200, 750],
        [800, 650],  # -9.5 deg bottom
        [900, 950],
    ]
    res_divergent = rule.evaluate(pts_divergent, 1000, 1000, cfg)
    assert res_divergent.passed is False
    assert res_divergent.is_hard_pruned is True
    assert "not parallel" in res_divergent.reason or "diverge" in res_divergent.reason


def test_relative_crease_tilt_and_keystone_rule():
    """Test RelativeCreaseTiltAndKeystoneRule on mutual tilt and keystone convergence."""
    rule = RelativeCreaseTiltAndKeystoneRule()
    cfg = CVRuleConfig()

    # 1. Straight vertical creases
    pts_vertical = [
        [50, 100],
        [250, 200],
        [750, 200],
        [950, 100],
        [100, 950],
        [250, 700],
        [750, 700],
        [900, 950],
    ]
    res = rule.evaluate(pts_vertical, 1000, 1000, cfg)
    assert res.passed is True
    assert res.score >= 0.95

    # 2. Both tilted by 8 deg (camera rotated, matching tilt)
    pts_tilted = [
        [50, 100],
        [250, 200],
        [750, 200],
        [950, 100],
        [100, 950],
        [320, 700],
        [820, 700],
        [900, 950],  # Both shifted right by 70px
    ]
    res_tilted = rule.evaluate(pts_tilted, 1000, 1000, cfg)
    assert res_tilted.passed is True
    assert res_tilted.score >= 0.90

    # 3. Asymmetric wild shear (left shifted right +150px, right shifted left -150px)
    pts_sheared = [
        [50, 100],
        [250, 200],
        [750, 200],
        [950, 100],
        [100, 950],
        [420, 700],
        [580, 700],
        [900, 950],
    ]
    res_sheared = rule.evaluate(pts_sheared, 1000, 1000, cfg)
    assert res_sheared.passed is False
    assert res_sheared.is_hard_pruned is True


def test_elevation_monotonicity_rule():
    """Test ElevationMonotonicityRule on correct vs inverted vertical layers."""
    rule = ElevationMonotonicityRule()
    cfg = CVRuleConfig(tub_to_floor_min_offset_ratio=0.06)

    # 1. Correct vertical ordering
    pts_good = [
        [50, 80],  # Y0=80 (Ceiling)
        [200, 250],  # Y1=250 (Header)
        [800, 250],  # Y2=250
        [950, 80],  # Y3=80
        [100, 920],  # Y4=920 (Floor)
        [200, 700],  # Y5=700 (Tub)
        [800, 700],  # Y6=700
        [900, 920],  # Y7=920
    ]
    res_good = rule.evaluate(pts_good, 1000, 1000, cfg)
    assert res_good.passed is True
    assert res_good.score == 1.0

    # 2. Inverted header and tub rim (Y1 > Y5)
    pts_inverted = [
        [50, 80],
        [200, 750],  # Inverted! Header below tub
        [800, 750],
        [950, 80],
        [100, 920],
        [200, 500],  # Tub above header
        [800, 500],
        [900, 920],
    ]
    res_inverted = rule.evaluate(pts_inverted, 1000, 1000, cfg)
    assert res_inverted.passed is False
    assert res_inverted.is_hard_pruned is True
    assert "below or equal" in res_inverted.reason


def test_aspect_ratio_rule():
    """Test AspectRatioRule on realistic vs extreme aspect ratios."""
    rule = AspectRatioRule()
    cfg = CVRuleConfig(min_back_wall_aspect_ratio=0.60, max_back_wall_aspect_ratio=1.40)

    # 1. Standard realistic alcove back wall (Width=600px, Height=500px -> Aspect=1.20)
    pts_normal = [
        [50, 80],
        [200, 200],
        [800, 200],
        [950, 80],
        [100, 920],
        [200, 700],
        [800, 700],
        [900, 920],
    ]
    res_normal = rule.evaluate(pts_normal, 1000, 1000, cfg)
    assert res_normal.passed is True
    assert res_normal.score >= 0.70

    # 2. Impossibly narrow sliver (Width=50px, Height=500px -> Aspect=0.10)
    pts_narrow = [
        [50, 80],
        [475, 200],
        [525, 200],
        [950, 80],
        [100, 920],
        [475, 700],
        [525, 700],
        [900, 920],
    ]
    res_narrow = rule.evaluate(pts_narrow, 1000, 1000, cfg)
    assert res_narrow.passed is False
    assert res_narrow.is_hard_pruned is True
    assert "too narrow" in res_narrow.reason


def test_mesh_rule_evaluator_composite():
    """Test MeshRuleEvaluator aggregating all rules and outputting report dictionary."""
    evaluator = MeshRuleEvaluator()

    pts_valid = [
        [50, 80],
        [250, 220],
        [750, 220],
        [950, 80],
        [100, 920],
        [250, 700],
        [750, 700],
        [900, 920],
    ]
    report = evaluator.evaluate_mesh(pts_valid, 1000, 1000)

    assert report.is_valid is True
    assert report.composite_score >= 0.80
    assert len(report.passed_rules) >= 4
    assert len(report.hard_pruned_reasons) == 0

    d = report.to_dict()
    assert d["is_valid"] is True
    assert "rule_breakdown" in d
    assert "back_wall_parallelism" in d["rule_breakdown"]
    assert "crease_relative_tilt" in d["rule_breakdown"]
    assert "elevation_monotonicity" in d["rule_breakdown"]
