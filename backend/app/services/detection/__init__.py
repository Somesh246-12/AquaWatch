"""AquaWatch Anomaly Detection Engine Package."""

from app.services.detection.common import DetectionResult, load_readings_dataframe
from app.services.detection.rule_based import RuleBasedDetector
from app.services.detection.z_score import ZScoreDetector
from app.services.detection.isolation_forest import IsolationForestDetector, FEATURE_COLUMNS
from app.services.detection.evaluator import (
    GroundTruthEvent,
    EvaluationMetrics,
    evaluate_detector_predictions,
    run_all_detectors,
    run_detection_and_persist_alerts,
)

__all__ = [
    "DetectionResult",
    "load_readings_dataframe",
    "RuleBasedDetector",
    "ZScoreDetector",
    "IsolationForestDetector",
    "FEATURE_COLUMNS",
    "GroundTruthEvent",
    "EvaluationMetrics",
    "evaluate_detector_predictions",
    "run_all_detectors",
    "run_detection_and_persist_alerts",
]
