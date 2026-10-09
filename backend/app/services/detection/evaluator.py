"""AquaWatch Detection Evaluator and Benchmark Pipeline.

Implements event-level evaluation comparing detector predictions against
ground-truth anomalies injected by the simulator. Computes:
- True Positives (TP)
- False Positives (FP)
- False Negatives (FN)
- Precision, Recall, and F1-score
- Breakdown by anomaly type ('slow_leak', 'burst', 'wastage_day')
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import pandas as pd
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import (
    engine as default_engine,
    SessionLocal as default_session_factory,
)
from app.models import InjectedAnomaly, Reading, Zone
from app.services.detection.common import DetectionResult, load_readings_dataframe
from app.services.detection.rule_based import RuleBasedDetector
from app.services.detection.z_score import ZScoreDetector
from app.services.detection.isolation_forest import IsolationForestDetector

logger = logging.getLogger("aquawatch.evaluator")


@dataclass
class GroundTruthEvent:
    """Represents a ground-truth anomaly event from injected_anomalies."""

    id: int
    zone_id: int
    timestamp: datetime
    anomaly_type: str


@dataclass
class EvaluationMetrics:
    """Calculated performance metrics for a detector."""

    method: str
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    per_type_metrics: Dict[str, Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Converts metrics into a serializable dictionary."""
        return {
            "method": self.method,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "per_type_metrics": self.per_type_metrics,
        }


def safe_divide(numerator: float, denominator: float) -> float:
    """Performs division with safe zero-denominator fallback."""
    if denominator <= 0.0:
        return 0.0
    return round(numerator / denominator, 4)


def calculate_metrics(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    """Calculates precision, recall, and F1-score from TP, FP, FN."""
    precision = safe_divide(float(tp), float(tp + fp))
    recall = safe_divide(float(tp), float(tp + fn))
    f1 = (
        safe_divide(2.0 * precision * recall, precision + recall)
        if (precision + recall) > 0.0
        else 0.0
    )
    return precision, recall, f1


def is_temporally_compatible(
    pred_start: datetime,
    pred_end: Optional[datetime],
    gt_start: datetime,
    anomaly_type: str,
) -> bool:
    """Checks if a prediction event overlaps or aligns with a ground-truth event.

    Tolerance definitions:
    - slow_leak: 4-hour active night window + 2h margin.
    - burst: 2-hour burst duration + 2h margin.
    - wastage_day: 16-hour daytime active window or same calendar date.
    """
    effective_end = pred_end or pred_start

    if anomaly_type == "slow_leak":
        window_start = gt_start - timedelta(hours=2)
        window_end = gt_start + timedelta(hours=6)
    elif anomaly_type == "burst":
        window_start = gt_start - timedelta(hours=2)
        window_end = gt_start + timedelta(hours=4)
    elif anomaly_type == "wastage_day":
        # Check either same calendar date or 20-hour window around event
        if pred_start.date() == gt_start.date():
            return True
        window_start = gt_start - timedelta(hours=2)
        window_end = gt_start + timedelta(hours=20)
    else:
        window_start = gt_start - timedelta(hours=3)
        window_end = gt_start + timedelta(hours=6)

    # Check for window intersection
    return not (effective_end < window_start or pred_start > window_end)


def evaluate_detector_predictions(
    predictions: List[DetectionResult],
    ground_truth: List[GroundTruthEvent],
    method_name: str,
) -> EvaluationMetrics:
    """Performs 1-to-1 event-level matching and computes Precision, Recall, and F1.

    Algorithm:
    1. Identify candidate matches where pred.zone_id == gt.zone_id and timing is compatible.
    2. Sort candidate matches by smallest time delta.
    3. Greedily match 1-to-1 (each GT matched at most once, each prediction matched at most once).
    4. Compute TP, FP, FN, Precision, Recall, F1.
    5. Compute per-anomaly-type breakdown.
    """
    matched_predictions: Set[int] = set()
    matched_ground_truth: Set[int] = set()

    # Build candidate pairs: (time_delta_seconds, pred_idx, gt_idx)
    candidates: List[Tuple[float, int, int]] = []
    for p_idx, pred in enumerate(predictions):
        for g_idx, gt in enumerate(ground_truth):
            if pred.zone_id == gt.zone_id:
                if is_temporally_compatible(
                    pred.timestamp, pred.end_timestamp, gt.timestamp, gt.anomaly_type
                ):
                    delta = abs((pred.timestamp - gt.timestamp).total_seconds())
                    candidates.append((delta, p_idx, g_idx))

    # Sort candidates greedily by closest temporal alignment
    candidates.sort(key=lambda x: x[0])

    for _, p_idx, g_idx in candidates:
        if p_idx not in matched_predictions and g_idx not in matched_ground_truth:
            matched_predictions.add(p_idx)
            matched_ground_truth.add(g_idx)

    tp = len(matched_predictions)
    fp = len(predictions) - tp
    fn = len(ground_truth) - len(matched_ground_truth)

    precision, recall, f1 = calculate_metrics(tp, fp, fn)

    # Per-anomaly-type evaluation
    type_categories = ["slow_leak", "burst", "wastage_day"]
    per_type: Dict[str, Dict[str, Any]] = {}

    for cat in type_categories:
        cat_gt_indices = {
            i for i, g in enumerate(ground_truth) if g.anomaly_type == cat
        }
        cat_total_gt = len(cat_gt_indices)
        cat_tp = len(cat_gt_indices.intersection(matched_ground_truth))
        cat_fn = cat_total_gt - cat_tp

        cat_pred_count = sum(
            1 for p in predictions if p.anomaly_type == cat or method_name == "isolation_forest"
        )
        cat_recall = safe_divide(float(cat_tp), float(cat_total_gt))

        per_type[cat] = {
            "ground_truth_total": cat_total_gt,
            "true_positives": cat_tp,
            "false_negatives": cat_fn,
            "recall": cat_recall,
        }

    return EvaluationMetrics(
        method=method_name,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        per_type_metrics=per_type,
    )


def load_ground_truth_from_db(session: Session) -> List[GroundTruthEvent]:
    """Loads all ground-truth records from injected_anomalies."""
    records = session.query(InjectedAnomaly).order_by(InjectedAnomaly.timestamp).all()
    return [
        GroundTruthEvent(
            id=r.id,
            zone_id=r.zone_id,
            timestamp=r.timestamp,
            anomaly_type=r.anomaly_type,
        )
        for r in records
    ]


def run_all_detectors(
    session: Optional[Session] = None,
    engine_to_use: Optional[Engine] = None,
    session_factory: Optional[sessionmaker] = None,
    contamination: float = 0.02,
) -> Dict[str, Any]:
    """Executes the full AquaWatch anomaly detection pipeline.

    1. Loads time-series readings from database.
    2. Loads ground-truth anomalies from injected_anomalies.
    3. Runs Rule-Based night-flow detector.
    4. Runs Statistical Z-Score detector.
    5. Runs Machine-Learning Isolation Forest detector.
    6. Performs event-level benchmark evaluation for each detector.
    7. Returns unified results and comparative metrics.
    """
    should_close = False
    if session is None:
        target_factory = session_factory or (
            sessionmaker(autocommit=False, autoflush=False, bind=engine_to_use)
            if engine_to_use
            else default_session_factory
        )
        session = target_factory()
        should_close = True

    try:
        readings_df = load_readings_dataframe(session)
        ground_truth = load_ground_truth_from_db(session)

        if readings_df.empty:
            logger.warning("No readings available in database for detection.")
            return {
                "readings_count": 0,
                "ground_truth_count": len(ground_truth),
                "evaluations": {},
                "predictions": {},
            }

        # 1. Rule-Based Detector
        rule_detector = RuleBasedDetector(
            night_hours=[1, 2, 3, 4],
            flow_threshold_litres=3.0,
            min_consecutive_hours=3,
        )
        rule_preds = rule_detector.detect(readings_df)
        rule_eval = evaluate_detector_predictions(rule_preds, ground_truth, "rule_based")

        # 2. Z-Score Detector
        z_detector = ZScoreDetector(threshold=3.0)
        z_preds = z_detector.detect(readings_df)
        z_eval = evaluate_detector_predictions(z_preds, ground_truth, "z_score")

        # 3. Isolation Forest Detector
        iforest_detector = IsolationForestDetector(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        iforest_preds = iforest_detector.detect(readings_df)
        iforest_eval = evaluate_detector_predictions(
            iforest_preds, ground_truth, "isolation_forest"
        )

        return {
            "readings_count": len(readings_df),
            "ground_truth_count": len(ground_truth),
            "evaluations": {
                "rule_based": rule_eval,
                "z_score": z_eval,
                "isolation_forest": iforest_eval,
            },
            "predictions": {
                "rule_based": rule_preds,
                "z_score": z_preds,
                "isolation_forest": iforest_preds,
            },
        }
    finally:
        if should_close:
            session.close()


def run_detection_and_persist_alerts(
    session: Session,
    contamination: float = 0.02,
) -> Dict[str, Any]:
    """Runs all detectors, stores unique alerts into the alerts table, and returns evaluation.

    Duplicate Prevention Strategy:
    - Checks existing alerts for the same zone_id and alert_type within +/- 4 hours of the event timestamp.
    - If a matching alert already exists (resolved or unresolved), skips creation to avoid alert duplication.
    """
    from app.models.alert import Alert

    raw_results = run_all_detectors(session=session, contamination=contamination)
    predictions = raw_results.get("predictions", {})
    evaluations = raw_results.get("evaluations", {})

    existing_alerts = session.query(Alert).all()
    method_to_alert_type = {
        "rule_based": "leak",
        "z_score": "spike",
        "isolation_forest": "abnormal_usage",
    }

    new_alerts: List[Alert] = []
    already_existing_count = 0

    for method, preds in predictions.items():
        mapped_type = method_to_alert_type.get(method, "abnormal_usage")
        for pred in preds:
            is_duplicate = False
            for ea in existing_alerts:
                if ea.zone_id == pred.zone_id and ea.alert_type == mapped_type:
                    delta_seconds = abs((ea.timestamp - pred.timestamp).total_seconds())
                    if delta_seconds <= 4 * 3600:
                        is_duplicate = True
                        break

            if is_duplicate:
                already_existing_count += 1
            else:
                new_alert = Alert(
                    zone_id=pred.zone_id,
                    timestamp=pred.timestamp,
                    alert_type=mapped_type,
                    severity=pred.severity,
                    message=pred.message,
                    resolved=False,
                )
                new_alerts.append(new_alert)
                existing_alerts.append(new_alert)

    if new_alerts:
        session.add_all(new_alerts)
        session.commit()

    detectors_summary = {}
    for method, preds in predictions.items():
        detectors_summary[method] = {
            "events_detected": len(preds),
            "zones_affected": list(set(p.zone_id for p in preds)),
            "mapped_alert_type": method_to_alert_type.get(method, "abnormal_usage"),
        }

    serialized_evals = {}
    for method, em in evaluations.items():
        serialized_evals[method] = em.to_dict() if hasattr(em, "to_dict") else vars(em)

    total_candidates = sum(len(preds) for preds in predictions.values())

    return {
        "status": "completed",
        "candidate_detections": total_candidates,
        "alerts_created": len(new_alerts),
        "alerts_existing": already_existing_count,
        "detectors": detectors_summary,
        "evaluation": serialized_evals,
    }
