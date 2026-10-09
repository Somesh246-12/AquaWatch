"""AquaWatch Rule-Based Night-Flow Detector.

Algorithm Specification:
- Monitors night hours 1:00 AM through 4:00 AM (01:00, 02:00, 03:00, 04:00).
- Identifies flow exceeding the 3.0 Litres/hour threshold.
- Triggers only when high flow persists for at least 3 consecutive hours.
- Combines consecutive hourly readings into a single logical leak event.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Union
import pandas as pd
from sqlalchemy.orm import Session
from app.services.detection.common import DetectionResult, load_readings_dataframe


class RuleBasedDetector:
    """Detects continuous night-time water leaks based on persistent flow thresholds."""

    def __init__(
        self,
        night_hours: Optional[List[int]] = None,
        flow_threshold_litres: float = 3.0,
        min_consecutive_hours: int = 3,
    ):
        """Configure detector parameters.

        Args:
            night_hours: Target night hours to inspect (default: [1, 2, 3, 4]).
            flow_threshold_litres: Lower bound flow threshold in L/h (default: 3.0).
            min_consecutive_hours: Minimum consecutive hours required to trigger (default: 3).
        """
        self.night_hours = night_hours or [1, 2, 3, 4]
        self.flow_threshold = flow_threshold_litres
        self.min_consecutive_hours = min_consecutive_hours

    def detect(
        self, data: Union[pd.DataFrame, Session]
    ) -> List[DetectionResult]:
        """Runs rule-based detection on time-series readings.

        Args:
            data: Either a pandas DataFrame or an active SQLAlchemy Session.

        Returns:
            List of discrete DetectionResult events representing continuous leaks.
        """
        if isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            df = load_readings_dataframe(data)

        if df.empty:
            return []

        # Ensure timestamp is datetime and sort by zone and timestamp
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(by=["zone_id", "timestamp"]).reset_index(drop=True)

        results: List[DetectionResult] = []

        for zone_id, zone_df in df.groupby("zone_id"):
            zone_name = zone_df["zone_name"].iloc[0]
            zone_df = zone_df.set_index("timestamp")

            # Extract calendar date for each reading
            # Group by night window: for hours 1, 2, 3, 4 of each date
            zone_night_df = zone_df[zone_df.index.hour.isin(self.night_hours)]

            if zone_night_df.empty:
                continue

            # Group night readings by date
            for date_val, night_readings in zone_night_df.groupby(zone_night_df.index.date):
                # Check for consecutive hours exceeding flow threshold
                sorted_night = night_readings.sort_index()

                current_streak: List[pd.Series] = []
                detected_events: List[List[pd.Series]] = []

                prev_time: Optional[datetime] = None
                for ts, row in sorted_night.iterrows():
                    litres = float(row["litres"])

                    if litres > self.flow_threshold:
                        if prev_time is None or (ts - prev_time) == timedelta(hours=1):
                            current_streak.append(row)
                        else:
                            if len(current_streak) >= self.min_consecutive_hours:
                                detected_events.append(current_streak)
                            current_streak = [row]
                        prev_time = ts
                    else:
                        if len(current_streak) >= self.min_consecutive_hours:
                            detected_events.append(current_streak)
                        current_streak = []
                        prev_time = None

                if len(current_streak) >= self.min_consecutive_hours:
                    detected_events.append(current_streak)

                # Convert confirmed streaks into single logical DetectionResult
                for streak in detected_events:
                    streak_df = pd.DataFrame(streak)
                    start_time = streak_df.index[0]
                    end_time = streak_df.index[-1]
                    duration = len(streak_df)
                    peak_flow = round(float(streak_df["litres"].max()), 2)
                    avg_flow = round(float(streak_df["litres"].mean()), 2)

                    # Severity classification based on average leak flow
                    if avg_flow >= 15.0:
                        severity = "high"
                    elif avg_flow >= 8.0:
                        severity = "medium"
                    else:
                        severity = "low"

                    message = (
                        f"Continuous night leak detected in {zone_name}: average flow of "
                        f"{avg_flow} L/h across {duration} consecutive hours between "
                        f"01:00 and 04:00 (threshold: {self.flow_threshold} L/h, peak: {peak_flow} L/h)."
                    )

                    results.append(
                        DetectionResult(
                            zone_id=int(zone_id),
                            zone_name=str(zone_name),
                            timestamp=start_time.to_pydatetime() if hasattr(start_time, "to_pydatetime") else start_time,
                            end_timestamp=end_time.to_pydatetime() if hasattr(end_time, "to_pydatetime") else end_time,
                            method="rule_based",
                            anomaly_type="slow_leak",
                            severity=severity,
                            score=avg_flow,
                            litres=peak_flow,
                            message=message,
                            metadata={
                                "duration_hours": duration,
                                "average_flow": avg_flow,
                                "peak_flow": peak_flow,
                                "threshold_litres": self.flow_threshold,
                            },
                        )
                    )

        return results
