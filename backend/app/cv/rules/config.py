"""
Centralized Configuration for Computer Vision Geometric & Architectural Rules.
All angles, percentages, ratios, and thresholds are defined as tunable variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CVRuleConfig:
    """
    Centralized parameters and thresholds for CV rule evaluation, pruning, and scoring.
    """

    # --- Statement 1: Back Wall Parallelism & Slant Alignment ---
    max_back_wall_angle_diff_deg: float = 4.0
    hard_prune_back_wall_angle_diff_deg: float = 7.0

    # --- Statement 2: Relative Vertical Crease & Keystone Convergence ---
    max_crease_mutual_tilt_diff_deg: float = 5.0
    max_keystone_convergence_deg: float = 12.0
    max_crease_shear_ratio: float = 0.08

    # --- Statement 3: Showerpan / Tub Base & Floor Clutter ---
    tub_to_floor_min_offset_ratio: float = 0.06
    floor_drain_y_min_ratio: float = 0.92
    floor_drain_x_min_ratio: float = 0.35
    floor_drain_x_max_ratio: float = 0.65

    # --- Statement 4: Elevation Bands ---
    band_ceiling_y_min_ratio: float = 0.00
    band_ceiling_y_max_ratio: float = 0.16
    band_header_y_min_ratio: float = 0.12
    band_header_y_max_ratio: float = 0.35
    band_tub_rim_y_min_ratio: float = 0.58
    band_tub_rim_y_max_ratio: float = 0.76
    band_floor_y_min_ratio: float = 0.78
    band_floor_y_max_ratio: float = 0.98

    # --- Statement 5: Hardware Deadband (Fixtures) ---
    deadband_y_min_ratio: float = 0.35
    deadband_y_max_ratio: float = 0.56

    # --- Statement 6: Sidewall Vanishing Ray Convergence ---
    sidewall_min_receding_angle_deg: float = 8.0
    sidewall_max_receding_angle_deg: float = 75.0
    vp_proximity_tolerance_ratio: float = 0.25

    # --- Statement 7: Back Wall Aspect Ratio & Proportions ---
    min_back_wall_aspect_ratio: float = 0.60
    max_back_wall_aspect_ratio: float = 1.40
    min_back_wall_span_ratio: float = 0.20

    # --- Statement 8: 4-Column Monotonic Ordering ---
    min_column_spacing_ratio: float = 0.04

    # --- Rule Scoring Weights ---
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "back_wall_parallelism": 0.25,
            "crease_relative_tilt": 0.20,
            "elevation_monotonicity": 0.20,
            "vanishing_convergence": 0.15,
            "back_wall_aspect_ratio": 0.10,
            "column_ordering": 0.10,
        }
    )


# Default global instance
DEFAULT_RULE_CONFIG = CVRuleConfig()
