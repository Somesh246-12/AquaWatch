/**
 * AquaWatch API TypeScript Definitions
 * Strictly maps to FastAPI backend Pydantic schemas.
 */

export interface HealthResponse {
  status: "ok" | "degraded" | string;
  service: string;
  version: string;
  database: "connected" | "disconnected" | string;
}

export interface Zone {
  id: number;
  name: string;
  type: string;
  daily_budget_litres: number;
}

export interface Reading {
  id: number;
  zone_id: number;
  timestamp: string;
  litres: number;
}

export interface DailyReading {
  date: string;
  zone_id: number;
  zone_name?: string;
  litres: number;
}

export type AlertSeverity = "low" | "medium" | "high";
export type AlertType = "leak" | "spike" | "abnormal_usage";

export interface Alert {
  id: number;
  zone_id: number;
  timestamp: string;
  alert_type: AlertType;
  severity: AlertSeverity;
  message: string;
  resolved: boolean;
}

export interface TopZoneSummary {
  id: number;
  name: string;
  litres: number;
}

export interface ZoneBudgetSummary {
  id: number;
  name: string;
  type: string;
  daily_budget_litres: number;
  today_usage_litres: number;
  budget_used_percent: number;
}

export interface DashboardSummary {
  today_usage_litres: number;
  yesterday_usage_litres: number;
  change_percent: number;
  weekly_usage_litres: number;
  top_zone?: TopZoneSummary | null;
  active_alerts: number;
  zones: ZoneBudgetSummary[];
}

export type BudgetStatus = "normal" | "warning" | "exceeded";

export interface ZoneBudgetStatus {
  zone_id: number;
  zone_name: string;
  zone_type: string;
  daily_budget_litres: number;
  actual_consumption_litres: number;
  remaining_budget_litres: number;
  consumed_percent: number;
  is_exceeded: boolean;
  status: BudgetStatus;
}

export interface ConservationBudgetsResponse {
  date: string;
  total_budget_litres: number;
  total_actual_litres: number;
  total_remaining_litres: number;
  overall_consumed_percent: number;
  overall_status: BudgetStatus;
  zones: ZoneBudgetStatus[];
}

export type RecommendationPriority = "low" | "medium" | "high" | "critical";

export interface ConservationRecommendation {
  id: string;
  category: "leak_repair" | "budget_exceeded" | "budget_warning" | "high_consumption" | "general_tip" | string;
  title: string;
  description: string;
  priority: RecommendationPriority;
  zone_id?: number | null;
  zone_name?: string | null;
  supporting_data?: Record<string, any> | null;
}

export interface ConservationTipsResponse {
  date: string;
  total_recommendations: number;
  recommendations: ConservationRecommendation[];
}

export interface LeakSavingsEstimate {
  alert_id?: number | null;
  zone_id: number;
  zone_name?: string | null;
  timestamp?: string | null;
  leak_flow_lph?: number | null;
  assumed_hours_per_day: number;
  daily_wasted_litres?: number | null;
  monthly_wasted_litres?: number | null;
  monthly_savings?: number | null;
  status: "estimated" | "unavailable" | string;
  message: string;
  is_estimate: boolean;
}

export interface ConservationSavingsResponse {
  tariff_per_kl: number;
  currency: string;
  assumed_hours_per_day: number;
  total_leaks_evaluated: number;
  actionable_leaks_count: number;
  total_daily_wasted_litres: number;
  total_monthly_wasted_litres: number;
  total_monthly_savings: number;
  leak_estimates: LeakSavingsEstimate[];
  disclaimer: string;
}

export interface DetectorBenchmarkMetrics {
  method: string;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
  f1_score: number;
  per_type_metrics?: Record<string, any>;
}

export interface DetectionRunResponse {
  status: string;
  candidate_detections: number;
  alerts_created: number;
  alerts_existing: number;
  detectors: Record<string, {
    events_detected: number;
    zones_affected: number[];
    mapped_alert_type: string;
  }>;
  evaluation: Record<string, DetectorBenchmarkMetrics>;
}

export interface DemoTimelineStep {
  step: string;
  title: string;
  description: string;
  status: "completed" | "active" | "pending";
  timestamp: string;
}

export interface DemoTelemetryPoint {
  timestamp: string;
  litres: number;
  is_anomaly: boolean;
  baseline_litres: number;
}

export interface DemoSessionStatus {
  session_id: string;
  status: "idle" | "ready" | "injecting" | "detected" | "resolved";
  zone_id?: number | null;
  zone_name?: string | null;
  leak_type?: string | null;
  severity?: string | null;
  leak_flow_lph?: number | null;
  total_leak_volume_litres?: number | null;
  alert_id?: number | null;
  alert_resolved: boolean;
  injected_readings_count: number;
  detector_name?: string | null;
  detector_score?: number | null;
  detector_message?: string | null;
  timeline: DemoTimelineStep[];
  telemetry_points: DemoTelemetryPoint[];
}

export interface DemoInjectRequest {
  zone_id: number;
  leak_type: "slow_leak" | "burst";
  severity: "low" | "medium" | "high";
  session_id?: string;
}

export interface DemoInjectResponse {
  success: boolean;
  session_id: string;
  event_id: number;
  zone_id: number;
  zone_name: string;
  leak_type: string;
  severity: string;
  leak_flow_lph: number;
  total_leak_volume: number;
  alert: Alert;
  detector: {
    name: string;
    score: number;
    message: string;
    rule: string;
  };
  readings_injected: number;
  timeline: DemoTimelineStep[];
  summary: string;
}

export interface DemoResetResponse {
  status: string;
  session_id?: string | null;
  readings_cleaned: number;
  alerts_cleaned: number;
  original_data_preserved: boolean;
  message: string;
}
