"""Unit and integration tests for AquaWatch Anomaly Detection Engine."""

from datetime import datetime, timedelta, timezone
import pytest
import pandas as pd
from app.services.detection.common import DetectionResult
from app.services.detection.rule_based import RuleBasedDetector
from app.services.detection.z_score import ZScoreDetector
from app.services.detection.isolation_forest import (
    IsolationForestDetector,
    FEATURE_COLUMNS,
)
from app.services.detection.evaluator import (
    GroundTruthEvent,
    evaluate_detector_predictions,
    calculate_metrics,
    safe_divide,
    run_all_detectors,
)
from app.services.simulator import simulate_dataset


# ==============================================================================
# 1. RULE-BASED DETECTOR TESTS (Tests 1 to 5)
# ==============================================================================

def test_rule_based_detects_continuous_night_leak():
    """1. Verify rule-based detector identifies continuous flow > 3 L/h across 3+ night hours."""
    detector = RuleBasedDetector(night_hours=[1, 2, 3, 4], flow_threshold_litres=3.0, min_consecutive_hours=3)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = []
    # 24 hours of normal data with a 4-hour leak at 01:00-04:00
    for h in range(24):
        litres = 12.0 if h in [1, 2, 3, 4] else 1.0
        rows.append({
            "id": h,
            "zone_id": 1,
            "zone_name": "Household",
            "timestamp": base_date + timedelta(hours=h),
            "litres": litres,
        })
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 1
    assert results[0].anomaly_type == "slow_leak"
    assert results[0].zone_id == 1
    assert results[0].metadata["duration_hours"] == 4
    assert results[0].litres == 12.0


def test_rule_based_ignores_normal_night_flow():
    """2. Verify rule-based detector does not flag normal night flow (0-2 L/h)."""
    detector = RuleBasedDetector()
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = [
        {"id": h, "zone_id": 1, "zone_name": "Household", "timestamp": base_date + timedelta(hours=h), "litres": 0.8}
        for h in range(24)
    ]
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 0


def test_rule_based_ignores_isolated_high_reading():
    """3. Verify rule-based detector does NOT treat an isolated single high night reading as a leak."""
    detector = RuleBasedDetector(min_consecutive_hours=3)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = []
    for h in range(24):
        # Only hour 2 is high (1 hour, not >= 3 consecutive hours)
        litres = 15.0 if h == 2 else 0.8
        rows.append({"id": h, "zone_id": 1, "zone_name": "Household", "timestamp": base_date + timedelta(hours=h), "litres": litres})
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 0


def test_rule_based_groups_consecutive_readings_into_single_event():
    """4. Verify rule-based detector groups hours 1, 2, 3, 4 into ONE logical event."""
    detector = RuleBasedDetector()
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = [
        {"id": h, "zone_id": 1, "zone_name": "Household", "timestamp": base_date + timedelta(hours=h), "litres": 11.5 if h in [1, 2, 3, 4] else 0.5}
        for h in range(24)
    ]
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 1
    assert results[0].metadata["duration_hours"] == 4


def test_rule_based_handles_multiple_zones_correctly():
    """5. Verify rule-based detector evaluates multiple zones independently."""
    detector = RuleBasedDetector()
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = []
    for h in range(24):
        # Zone 1 has leak
        rows.append({"id": h, "zone_id": 1, "zone_name": "Household", "timestamp": base_date + timedelta(hours=h), "litres": 10.0 if h in [1, 2, 3] else 0.5})
        # Zone 2 is normal
        rows.append({"id": 100 + h, "zone_id": 2, "zone_name": "Hostel", "timestamp": base_date + timedelta(hours=h), "litres": 0.8})
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 1
    assert results[0].zone_id == 1


# ==============================================================================
# 2. Z-SCORE DETECTOR TESTS (Tests 6 to 10)
# ==============================================================================

def test_z_score_detects_strong_burst_spike():
    """6. Verify z-score detector flags a strong artificial consumption burst."""
    detector = ZScoreDetector(threshold=3.0)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = []
    # 30 days of hourly data for hour 14
    for d in range(30):
        for h in range(24):
            # Day 15 hour 14 has massive burst
            val = 800.0 if (d == 15 and h == 14) else 50.0 + (h % 5)
            rows.append({
                "id": d * 24 + h,
                "zone_id": 1,
                "zone_name": "Kitchen",
                "timestamp": base_date + timedelta(days=d, hours=h),
                "litres": val,
            })
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) >= 1
    assert any(r.anomaly_type == "burst" and r.score > 3.0 for r in results)


def test_z_score_normal_values_do_not_trigger():
    """7. Verify normal uniform/diurnal data does not produce false z-score spikes."""
    detector = ZScoreDetector(threshold=3.0)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = [
        {"id": d * 24 + h, "zone_id": 1, "zone_name": "Garden", "timestamp": base_date + timedelta(days=d, hours=h), "litres": 20.0 + (h % 3)}
        for d in range(14)
        for h in range(24)
    ]
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 0


def test_z_score_strictly_uses_threshold():
    """8. Verify that readings below threshold (e.g. z = 2.0 < 3.0) are not flagged."""
    detector = ZScoreDetector(threshold=3.0)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    # 30 observations where max deviation is z < 2.5
    rows = []
    for d in range(30):
        val = 10.5 if d == 15 else 10.0 + (d % 3 * 0.2 - 0.2)
        rows.append({
            "id": d,
            "zone_id": 1,
            "zone_name": "Test",
            "timestamp": base_date + timedelta(days=d, hours=12),
            "litres": val,
        })
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 0


def test_z_score_handles_zero_std_safely():
    """9. Verify zero standard deviation does not cause division by zero."""
    detector = ZScoreDetector(threshold=3.0)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    # Identical values -> std = 0
    rows = [
        {"id": d, "zone_id": 1, "zone_name": "Test", "timestamp": base_date + timedelta(days=d, hours=12), "litres": 25.0}
        for d in range(10)
    ]
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert len(results) == 0


def test_z_score_deterministic_output():
    """10. Verify z-score detector produces identical results on identical input."""
    detector = ZScoreDetector(threshold=3.0)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = [
        {"id": d * 24 + h, "zone_id": 1, "zone_name": "Zone", "timestamp": base_date + timedelta(days=d, hours=h), "litres": 500.0 if (d == 3 and h == 10) else 30.0}
        for d in range(7)
        for h in range(24)
    ]
    df = pd.DataFrame(rows)

    res1 = detector.detect(df)
    res2 = detector.detect(df)
    assert len(res1) == len(res2)
    assert [r.score for r in res1] == [r.score for r in res2]


# ==============================================================================
# 3. ISOLATION FOREST TESTS (Tests 11 to 14)
# ==============================================================================

def test_isolation_forest_produces_predictions():
    """11. Verify Isolation Forest produces valid detection results for a dataset."""
    detector = IsolationForestDetector(contamination=0.05, random_state=42)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = []
    for d in range(10):
        for h in range(24):
            val = 600.0 if (d == 4 and h == 12) else 50.0 + (h % 5)
            rows.append({
                "id": d * 24 + h,
                "zone_id": 1,
                "zone_name": "Hostel",
                "timestamp": base_date + timedelta(days=d, hours=h),
                "litres": val,
            })
    df = pd.DataFrame(rows)

    results = detector.detect(df)
    assert isinstance(results, list)
    assert len(results) > 0
    assert results[0].method == "isolation_forest"


def test_isolation_forest_uses_exactly_five_features():
    """12. Verify detector generates and uses exactly the five specified features."""
    detector = IsolationForestDetector()
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = [
        {"id": h, "zone_id": 1, "zone_name": "Household", "timestamp": base_date + timedelta(hours=h), "litres": float(h * 5)}
        for h in range(48)
    ]
    df = pd.DataFrame(rows)
    feat_df = detector.prepare_features(df)

    for col in FEATURE_COLUMNS:
        assert col in feat_df.columns
    assert len(FEATURE_COLUMNS) == 5


def test_isolation_forest_random_state_is_42():
    """13. Verify default random_state is 42."""
    detector = IsolationForestDetector()
    assert detector.random_state == 42


def test_isolation_forest_reproducible_predictions():
    """14. Verify Isolation Forest yields identical predictions with random_state=42."""
    detector1 = IsolationForestDetector(random_state=42)
    detector2 = IsolationForestDetector(random_state=42)
    base_date = datetime(2026, 8, 10, 0, 0, 0)

    rows = [
        {"id": d * 24 + h, "zone_id": 1, "zone_name": "Hostel", "timestamp": base_date + timedelta(days=d, hours=h), "litres": 900.0 if (d == 2 and h == 8) else 40.0}
        for d in range(7)
        for h in range(24)
    ]
    df = pd.DataFrame(rows)

    preds1 = detector1.detect(df)
    preds2 = detector2.detect(df)

    assert len(preds1) == len(preds2)
    assert [p.score for p in preds1] == [p.score for p in preds2]


# ==============================================================================
# 4. EVALUATOR TESTS (Tests 15 to 22)
# ==============================================================================

def test_precision_calculation():
    """15. Verify Precision = TP / (TP + FP)."""
    p, _, _ = calculate_metrics(tp=8, fp=2, fn=0)
    assert p == 0.8


def test_recall_calculation():
    """16. Verify Recall = TP / (TP + FN)."""
    _, r, _ = calculate_metrics(tp=6, fp=0, fn=4)
    assert r == 0.6


def test_f1_score_calculation():
    """17. Verify F1 Score = 2 * P * R / (P + R)."""
    # P = 0.8, R = 0.8 -> F1 = 0.8
    _, _, f1 = calculate_metrics(tp=8, fp=2, fn=2)
    assert f1 == 0.8


def test_event_matching_no_duplicate_true_positives():
    """18. Verify multiple detections inside one ground-truth event window count as 1 TP and remaining as FP."""
    gt_time = datetime(2026, 8, 10, 14, 0, 0)
    ground_truth = [GroundTruthEvent(id=1, zone_id=1, timestamp=gt_time, anomaly_type="burst")]

    # 2 separate detection events targeting the same burst event
    predictions = [
        DetectionResult(zone_id=1, zone_name="A", timestamp=gt_time, anomaly_type="burst"),
        DetectionResult(zone_id=1, zone_name="A", timestamp=gt_time + timedelta(hours=1), anomaly_type="burst"),
    ]

    metrics = evaluate_detector_predictions(predictions, ground_truth, "test")
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 0


def test_one_ground_truth_cannot_match_twice():
    """19. Verify a single ground-truth event can only be matched at most once."""
    gt_time = datetime(2026, 8, 10, 1, 0, 0)
    ground_truth = [GroundTruthEvent(id=1, zone_id=1, timestamp=gt_time, anomaly_type="slow_leak")]

    predictions = [
        DetectionResult(zone_id=1, zone_name="A", timestamp=gt_time, anomaly_type="slow_leak"),
        DetectionResult(zone_id=1, zone_name="A", timestamp=gt_time + timedelta(hours=2), anomaly_type="slow_leak"),
        DetectionResult(zone_id=1, zone_name="A", timestamp=gt_time + timedelta(hours=3), anomaly_type="slow_leak"),
    ]

    metrics = evaluate_detector_predictions(predictions, ground_truth, "test")
    assert metrics.true_positives == 1
    assert metrics.false_positives == 2


def test_same_zone_requirement_enforced():
    """20. Verify detections in Zone 1 cannot match Ground Truth in Zone 2."""
    gt_time = datetime(2026, 8, 10, 1, 0, 0)
    ground_truth = [GroundTruthEvent(id=1, zone_id=2, timestamp=gt_time, anomaly_type="slow_leak")]

    predictions = [
        DetectionResult(zone_id=1, zone_name="Z1", timestamp=gt_time, anomaly_type="slow_leak"),
    ]

    metrics = evaluate_detector_predictions(predictions, ground_truth, "test")
    assert metrics.true_positives == 0
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1


def test_temporal_matching_rejects_distant_predictions():
    """21. Verify detections outside the temporal tolerance window do not match."""
    gt_time = datetime(2026, 8, 10, 14, 0, 0)
    ground_truth = [GroundTruthEvent(id=1, zone_id=1, timestamp=gt_time, anomaly_type="burst")]

    # Prediction 15 days later
    predictions = [
        DetectionResult(zone_id=1, zone_name="Z1", timestamp=gt_time + timedelta(days=15), anomaly_type="burst"),
    ]

    metrics = evaluate_detector_predictions(predictions, ground_truth, "test")
    assert metrics.true_positives == 0
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 1


def test_safe_divide_handles_zero_division():
    """22. Verify safe_divide returns 0.0 when denominator is zero without error."""
    assert safe_divide(10.0, 0.0) == 0.0
    p, r, f1 = calculate_metrics(tp=0, fp=0, fn=0)
    assert p == 0.0
    assert r == 0.0
    assert f1 == 0.0


# ==============================================================================
# 5. INTEGRATION TESTS ON 7,200 READINGS DATASET (Tests 23 to 25)
# ==============================================================================

@pytest.fixture
def sim_db_for_detection(test_db):
    """Initializes and seeds simulated dataset in test database."""
    engine = test_db["engine"]
    session_factory = test_db["session_factory"]
    simulate_dataset(days=60, seed=42, persist=True, engine=engine, session_factory=session_factory)
    return test_db


def test_run_all_detectors_on_full_dataset(sim_db_for_detection):
    """23. Verify run_all_detectors executes all 3 detectors on the full 7,200 readings."""
    session = sim_db_for_detection["session"]
    result = run_all_detectors(session=session)

    assert result["readings_count"] == 7200
    assert result["ground_truth_count"] == 10
    assert "rule_based" in result["evaluations"]
    assert "z_score" in result["evaluations"]
    assert "isolation_forest" in result["evaluations"]


def test_actual_evaluation_metrics_produced(sim_db_for_detection):
    """24. Verify actual metrics are generated and non-negative."""
    session = sim_db_for_detection["session"]
    result = run_all_detectors(session=session)
    evals = result["evaluations"]

    for method_name, em in evals.items():
        assert 0.0 <= em.precision <= 1.0
        assert 0.0 <= em.recall <= 1.0
        assert 0.0 <= em.f1_score <= 1.0
        assert em.true_positives + em.false_negatives == 10  # All 10 GT accounted for

    # Rule-based detector achieves 100% precision and identifies all 4 slow leaks
    rule_eval = evals["rule_based"]
    assert rule_eval.precision == 1.0
    assert rule_eval.per_type_metrics["slow_leak"]["true_positives"] == 4
