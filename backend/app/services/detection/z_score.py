"""AquaWatch Statistical Z-Score Anomaly Detector.

Algorithm Specification:
- Computes historical consumption mean and standard deviation grouped by (zone_id, hour_of_day).
- Standardizes each reading: z = (litres - mean) / std.
- Identifies sudden spikes/bursts where z > 3.0.
- Safely handles zero standard deviation edge cases.
- Aggregates consecutive spike hours into unified burst events.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Union
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from app.services.detection.common import DetectionResult, load_readings_dataframe


class ZScoreDetector:
    """Detects sudden consumption bursts and spikes using hour-specific statistical z-scores."""

    def __init__(self, threshold: float = 3.0):
        """Configure detector threshold.

        Args:
            threshold: Standard deviations above mean to flag an anomaly (default: 3.0).
        """
        self.threshold = threshold

    def detect(
        self, data: Union[pd.DataFrame, Session]
    ) -> List[DetectionResult]:
        """Runs z-score anomaly detection across all zones.

        Args:
            data: Either a pandas DataFrame or an active SQLAlchemy Session.

        Returns:
            List of discrete DetectionResult events representing detected bursts.
        """
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            df = load_readings_dataframe(data)

        if df.empty:
            return []

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour_of_day"] = df["timestamp"].dt.hour
        df = df.sort_values(by=["zone_id", "timestamp"]).reset_index(drop=True)

        # Calculate statistics per (zone_id, hour_of_day)
        grouped_stats = (
            df.groupby(["zone_id", "hour_of_day"])["litres"]
            .agg(mean="mean", std="std")
            .reset_index()
        )

        merged = pd.merge(
            df, grouped_stats, on=["zone_id", "hour_of_day"], how="left"
        )

        # Compute z-score safely
        std_series = merged["std"].fillna(0.0)
        diff_series = merged["litres"] - merged["mean"]

        z_scores = np.zeros(len(merged), dtype=float)
        valid_std_mask = std_series > 1e-6

        # Standard case: std > 0
        z_scores[valid_std_mask] = (
            diff_series[valid_std_mask] / std_series[valid_std_mask]
        )

        # Zero std case: if litres > mean and std == 0, mark as high anomaly
        zero_std_excess = (~valid_std_mask) & (diff_series > 1e-3)
        z_scores[zero_std_excess] = 999.0

        merged["z_score"] = z_scores

        # Filter flagged anomalies: z > threshold
        spikes_df = merged[merged["z_score"] > self.threshold].copy()
        if spikes_df.empty:
            return []

        results: List[DetectionResult] = []

        # Group consecutive flagged hours in the same zone into cohesive burst events
        for zone_id, zone_spikes in spikes_df.groupby("zone_id"):
            zone_spikes = zone_spikes.sort_values(by="timestamp").reset_index(drop=True)
            zone_name = zone_spikes["zone_name"].iloc[0]

            current_event: List[pd.Series] = []
            prev_time: Optional[datetime] = None

            for _, row in zone_spikes.iterrows():
                ts = row["timestamp"]
                if prev_time is None or (ts - prev_time) <= timedelta(hours=1):
                    current_event.append(row)
                else:
                    self._append_burst_result(results, zone_id, zone_name, current_event)
                    current_event = [row]
                prev_time = ts

            if current_event:
                self._append_burst_result(results, zone_id, zone_name, current_event)

        return results

    def _append_burst_result(
        self,
        results_list: List[DetectionResult],
        zone_id: int,
        zone_name: str,
        event_rows: List[pd.Series],
    ):
        """Constructs a DetectionResult for an aggregated burst event."""
        event_df = pd.DataFrame(event_rows)
        start_time = event_df["timestamp"].iloc[0]
        end_time = event_df["timestamp"].iloc[-1]
        duration = len(event_df)

        peak_z = round(float(event_df["z_score"].max()), 2)
        peak_litres = round(float(event_df["litres"].max()), 2)
        mean_baseline = round(float(event_df["mean"].mean()), 2)

        # Severity determined by statistical deviation magnitude
        if peak_z >= 6.0:
            severity = "high"
        elif peak_z >= 4.5:
            severity = "medium"
        else:
            severity = "low"

        message = (
            f"Sudden consumption burst detected in {zone_name}: peak z-score = {peak_z} "
            f"(flow = {peak_litres} L/h vs historical mean = {mean_baseline} L/h) "
            f"lasting {duration} hour(s)."
        )

        results_list.append(
            DetectionResult(
                zone_id=int(zone_id),
                zone_name=str(zone_name),
                timestamp=start_time.to_pydatetime() if hasattr(start_time, "to_pydatetime") else start_time,
                end_timestamp=end_time.to_pydatetime() if hasattr(end_time, "to_pydatetime") else end_time,
                method="z_score",
                anomaly_type="burst",
                severity=severity,
                score=peak_z,
                litres=peak_litres,
                message=message,
                metadata={
                    "peak_z_score": peak_z,
                    "duration_hours": duration,
                    "peak_flow": peak_litres,
                    "baseline_mean": mean_baseline,
                    "threshold": self.threshold,
                },
            )
        )
