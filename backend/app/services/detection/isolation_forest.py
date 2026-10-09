"""AquaWatch Machine-Learning Isolation Forest Detector.

Algorithm Specification:
- Trains an unsupervised scikit-learn IsolationForest model per zone.
- Feature set (5 features per the project specification):
    1. hour_of_day (0 to 23)
    2. day_of_week (0 to 6)
    3. litres (instantaneous hourly consumption)
    4. rolling_3_hour_mean (short-term moving average)
    5. rolling_24_hour_mean (daily baseline moving average)
- Configured with random_state=42 for deterministic evaluation.
- Contamination parameter defaults to 0.02 (~2% of readings, corresponding to
  the injected fault density of ~20 anomalous hours out of 1,440 hours per zone).
- Groups adjacent anomalous timestamps into unified detection events.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session
from app.services.detection.common import DetectionResult, load_readings_dataframe

FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "litres",
    "rolling_3_hour_mean",
    "rolling_24_hour_mean",
]


class IsolationForestDetector:
    """Unsupervised Machine-Learning anomaly detector using scikit-learn Isolation Forest."""

    def __init__(
        self,
        contamination: float = 0.02,
        random_state: int = 42,
        n_estimators: int = 100,
    ):
        """Configure Isolation Forest parameters.

        Args:
            contamination: Expected proportion of outliers in the dataset (default: 0.02).
            random_state: Fixed seed for reproducible splits and trees (default: 42).
            n_estimators: Number of isolation trees (default: 100).
        """
        self.contamination = contamination
        self.random_state = random_state
        self.n_estimators = n_estimators
        self.models: Dict[int, IsolationForest] = {}

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes the five required features per zone."""
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour_of_day"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df = df.sort_values(by=["zone_id", "timestamp"]).reset_index(drop=True)

        # Compute rolling window means per zone
        df["rolling_3_hour_mean"] = (
            df.groupby("zone_id")["litres"]
            .transform(lambda s: s.rolling(window=3, min_periods=1).mean())
        )
        df["rolling_24_hour_mean"] = (
            df.groupby("zone_id")["litres"]
            .transform(lambda s: s.rolling(window=24, min_periods=1).mean())
        )

        return df

    def detect(
        self, data: Union[pd.DataFrame, Session]
    ) -> List[DetectionResult]:
        """Runs Isolation Forest anomaly detection per zone.

        Args:
            data: Either a pandas DataFrame or an active SQLAlchemy Session.

        Returns:
            List of discrete DetectionResult events representing detected anomalies.
        """
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            df = load_readings_dataframe(data)

        if df.empty:
            return []

        df = self.prepare_features(df)
        results: List[DetectionResult] = []

        # Train and detect per zone
        for zone_id, zone_df in df.groupby("zone_id"):
            zone_df = zone_df.sort_values(by="timestamp").reset_index(drop=True)
            zone_name = zone_df["zone_name"].iloc[0]

            X = zone_df[FEATURE_COLUMNS].values

            # Initialize and fit model per zone
            model = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=self.n_estimators,
            )
            model.fit(X)
            self.models[int(zone_id)] = model

            # -1 for anomaly, 1 for inlier
            predictions = model.predict(X)

            # decision_function: lower means more anomalous; invert so higher = more anomalous
            raw_scores = model.decision_function(X)
            anomaly_scores = -raw_scores

            zone_df["is_anomaly"] = predictions == -1
            zone_df["anomaly_score"] = anomaly_scores

            # Filter flagged anomaly records
            anomalies_df = zone_df[zone_df["is_anomaly"]].copy()
            if anomalies_df.empty:
                continue

            # Group adjacent anomaly hours (within 2 hours) into consolidated detection events
            current_event: List[pd.Series] = []
            prev_time: Optional[datetime] = None

            for _, row in anomalies_df.iterrows():
                ts = row["timestamp"]
                if prev_time is None or (ts - prev_time) <= timedelta(hours=2):
                    current_event.append(row)
                else:
                    self._append_iforest_result(results, zone_id, zone_name, current_event)
                    current_event = [row]
                prev_time = ts

            if current_event:
                self._append_iforest_result(results, zone_id, zone_name, current_event)

        return results

    def _append_iforest_result(
        self,
        results_list: List[DetectionResult],
        zone_id: int,
        zone_name: str,
        event_rows: List[pd.Series],
    ):
        """Constructs a DetectionResult for an aggregated Isolation Forest event."""
        event_df = pd.DataFrame(event_rows)
        start_time = event_df["timestamp"].iloc[0]
        end_time = event_df["timestamp"].iloc[-1]
        duration = len(event_df)

        peak_score = round(float(event_df["anomaly_score"].max()), 4)
        peak_litres = round(float(event_df["litres"].max()), 2)
        avg_litres = round(float(event_df["litres"].mean()), 2)

        # Severity determined by Isolation Forest outlier score magnitude
        if peak_score >= 0.15:
            severity = "high"
        elif peak_score >= 0.08:
            severity = "medium"
        else:
            severity = "low"

        message = (
            f"Machine-learning anomaly detected in {zone_name} via Isolation Forest: "
            f"peak outlier score = {peak_score:.3f} (flow = {peak_litres} L/h, "
            f"avg = {avg_litres} L/h across {duration} hour(s))."
        )

        results_list.append(
            DetectionResult(
                zone_id=int(zone_id),
                zone_name=str(zone_name),
                timestamp=start_time.to_pydatetime() if hasattr(start_time, "to_pydatetime") else start_time,
                end_timestamp=end_time.to_pydatetime() if hasattr(end_time, "to_pydatetime") else end_time,
                method="isolation_forest",
                anomaly_type="abnormal_usage",
                severity=severity,
                score=peak_score,
                litres=peak_litres,
                message=message,
                metadata={
                    "peak_anomaly_score": peak_score,
                    "duration_hours": duration,
                    "peak_flow": peak_litres,
                    "average_flow": avg_litres,
                    "features_used": FEATURE_COLUMNS,
                    "contamination": self.contamination,
                },
            )
        )
