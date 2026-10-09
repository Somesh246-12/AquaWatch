import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  CheckCircle2,
  Clock,
  Droplet,
  Info,
  Play,
  Radio,
  RotateCcw,
  ShieldAlert,
  Sparkles,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type {
  Alert,
  ConservationBudgetsResponse,
  ConservationSavingsResponse,
  DashboardSummary,
  DemoInjectRequest,
  DemoResetResponse,
  DemoSessionStatus,
  Zone,
} from "../types/api";

interface DemoProps {
  zones: Zone[];
  summary: DashboardSummary | null;
  budgets: ConservationBudgetsResponse | null;
  savings: ConservationSavingsResponse | null;
  alerts: Alert[];
  onRefreshAll: () => Promise<void>;
  onResolveAlert: (alertId: number) => Promise<void>;
}

export const Demo: React.FC<DemoProps> = ({
  zones,
  summary,
  budgets,
  savings,
  alerts,
  onRefreshAll,
  onResolveAlert,
}) => {
  // Session and control state
  const [demoStatus, setDemoStatus] = useState<DemoSessionStatus | null>(null);
  const [selectedZoneId, setSelectedZoneId] = useState<number>(zones[0]?.id || 1);
  const [leakType, setLeakType] = useState<"slow_leak" | "burst">("slow_leak");
  const [severity, setSeverity] = useState<"low" | "medium" | "high">("high");

  // Interaction loading states
  const [isInjecting, setIsInjecting] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [isResolvingDemoAlert, setIsResolvingDemoAlert] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);
  const [lastPollTime, setLastPollTime] = useState<Date>(new Date());
  const [isPolling, setIsPolling] = useState<boolean>(true);

  // Guide accordion toggle
  const [showPresenterGuide, setShowPresenterGuide] = useState<boolean>(true);

  const isFetchingRef = useRef<boolean>(false);

  // Poll demo status and global data every 3 seconds
  const fetchDemoData = useCallback(async () => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;
    try {
      const statusRes = await api.getDemoStatus();
      setDemoStatus(statusRes);
      setLastPollTime(new Date());
      // Refresh summary, alerts, and budgets
      await onRefreshAll();
    } catch (err: any) {
      console.warn("Demo polling issue:", err.message);
    } finally {
      isFetchingRef.current = false;
    }
  }, [onRefreshAll]);

  useEffect(() => {
    // Initial fetch on mount
    fetchDemoData();

    if (!isPolling) return;

    const interval = setInterval(() => {
      fetchDemoData();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchDemoData, isPolling]);

  // Inject leak handler
  const handleInject = async () => {
    setIsInjecting(true);
    setFeedbackMessage(null);
    try {
      const payload: DemoInjectRequest = {
        zone_id: selectedZoneId,
        leak_type: leakType,
        severity: severity,
        session_id: demoStatus?.session_id,
      };
      const res = await api.injectDemoLeak(payload);
      setFeedbackMessage({
        type: "success",
        text: `Successfully injected ${severity} ${leakType.replace("_", " ")} into ${res.zone_name}. Alert #${res.event_id} dispatched!`,
      });
      // Immediately refresh live telemetry
      await fetchDemoData();
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err.data?.detail || err.message || "Failed to inject simulated leak.",
      });
    } finally {
      setIsInjecting(false);
    }
  };

  // Reset demo handler
  const handleReset = async () => {
    setIsResetting(true);
    setFeedbackMessage(null);
    try {
      const res: DemoResetResponse = await api.resetDemo(demoStatus?.session_id);
      setFeedbackMessage({
        type: "info",
        text: res.message,
      });
      await fetchDemoData();
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: err.data?.detail || err.message || "Failed to reset demo session.",
      });
    } finally {
      setIsResetting(false);
    }
  };

  // Resolve active demo alert
  const handleResolveAlertClick = async (alertId: number) => {
    setIsResolvingDemoAlert(true);
    try {
      await onResolveAlert(alertId);
      setFeedbackMessage({
        type: "success",
        text: `Alert #${alertId} has been acknowledged and marked as resolved.`,
      });
      await fetchDemoData();
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: `Failed to resolve alert #${alertId}: ${err.message}`,
      });
    } finally {
      setIsResolvingDemoAlert(false);
    }
  };

  const selectedZone = zones.find((z) => z.id === selectedZoneId) || zones[0];
  const activeAlert = demoStatus?.alert_id
    ? alerts.find((a) => a.id === demoStatus.alert_id)
    : null;

  // Find zone budget status
  const currentZoneBudget = budgets?.zones.find((zb) => zb.zone_id === selectedZoneId);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* 1. DEMO MODE LIVE BANNER & REALITY NOTICE */}
      <div
        className="card"
        style={{
          padding: "18px 24px",
          background: "linear-gradient(135deg, rgba(6, 182, 212, 0.12) 0%, rgba(14, 165, 233, 0.05) 100%)",
          borderColor: "rgba(6, 182, 212, 0.4)",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "10px",
              background: "rgba(6, 182, 212, 0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--accent-cyan)",
            }}
          >
            <Radio size={22} className="pulse" />
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h2 style={{ fontSize: "1.1rem", fontWeight: 700, margin: 0 }}>
                Interactive Live Demonstration Sandbox
              </h2>
              <span
                style={{
                  fontSize: "0.68rem",
                  padding: "2px 8px",
                  borderRadius: "12px",
                  background: "rgba(34, 197, 94, 0.2)",
                  color: "#4ade80",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: "#4ade80",
                  }}
                />
                Live 3s Polling
              </span>
            </div>
            <p style={{ fontSize: "0.82rem", color: "var(--text-muted)", margin: "4px 0 0 0" }}>
              Simulates realistic water anomaly injection, tests multi-detector algorithmic triggers, and verifies safe alert dispatch without modifying ground-truth evaluation datasets.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div style={{ fontSize: "0.78rem", color: "var(--text-dim)", textAlign: "right" }}>
            <div>Session ID: <code style={{ color: "var(--accent-cyan)" }}>{demoStatus?.session_id || "initializing..."}</code></div>
            <div>Updated: {lastPollTime.toLocaleTimeString()}</div>
          </div>
          <button
            className="btn btn-secondary"
            onClick={() => setIsPolling(!isPolling)}
            style={{ fontSize: "0.78rem", padding: "6px 12px" }}
            title={isPolling ? "Pause 3s polling" : "Resume 3s polling"}
          >
            {isPolling ? "Pause Polling" : "Resume Polling"}
          </button>
        </div>
      </div>

      {/* FEEDBACK ALERT */}
      {feedbackMessage && (
        <div
          style={{
            padding: "12px 18px",
            borderRadius: "var(--radius-sm)",
            fontSize: "0.85rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background:
              feedbackMessage.type === "success"
                ? "rgba(34, 197, 94, 0.15)"
                : feedbackMessage.type === "error"
                ? "rgba(239, 68, 68, 0.15)"
                : "rgba(59, 130, 246, 0.15)",
            border: `1px solid ${
              feedbackMessage.type === "success"
                ? "rgba(34, 197, 94, 0.4)"
                : feedbackMessage.type === "error"
                ? "rgba(239, 68, 68, 0.4)"
                : "rgba(59, 130, 246, 0.4)"
            }`,
            color:
              feedbackMessage.type === "success"
                ? "#4ade80"
                : feedbackMessage.type === "error"
                ? "#f87171"
                : "#60a5fa",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {feedbackMessage.type === "success" ? <CheckCircle2 size={16} /> : <Info size={16} />}
            <span>{feedbackMessage.text}</span>
          </div>
          <button
            onClick={() => setFeedbackMessage(null)}
            style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: "0.8rem" }}
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. DEMO CONTROLS & INJECTION DECK */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "20px",
        }}
      >
        {/* Left: Injection Controls */}
        <div className="card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "18px" }}>
            <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <Zap size={18} color="var(--accent-cyan)" />
              Simulated Leak Injector
            </h3>
            <span className="badge badge-normal" style={{ fontSize: "0.72rem" }}>
              Status: {demoStatus?.status.toUpperCase() || "READY"}
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Zone Selector */}
            <div>
              <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                Target Water Zone
              </label>
              <select
                className="select"
                value={selectedZoneId}
                onChange={(e) => setSelectedZoneId(Number(e.target.value))}
                disabled={isInjecting}
                style={{ width: "100%" }}
              >
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.name} ({z.type}) — Budget: {z.daily_budget_litres.toLocaleString()} L/d
                  </option>
                ))}
              </select>
            </div>

            {/* Leak Profile Selector */}
            <div>
              <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                Anomaly Flow Profile & Detection Method
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setLeakType("slow_leak")}
                  style={{
                    padding: "12px",
                    borderRadius: "var(--radius-sm)",
                    border: `1px solid ${leakType === "slow_leak" ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
                    background: leakType === "slow_leak" ? "rgba(6, 182, 212, 0.15)" : "var(--bg-elevated)",
                    color: leakType === "slow_leak" ? "var(--accent-cyan)" : "var(--text-muted)",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "var(--transition-fast)",
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "0.84rem", marginBottom: "4px" }}>
                    Continuous Night Leak
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                    Rule-Based Detector: 01:00-04:00 flow exceeding 3.0 L/h
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setLeakType("burst")}
                  style={{
                    padding: "12px",
                    borderRadius: "var(--radius-sm)",
                    border: `1px solid ${leakType === "burst" ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
                    background: leakType === "burst" ? "rgba(6, 182, 212, 0.15)" : "var(--bg-elevated)",
                    color: leakType === "burst" ? "var(--accent-cyan)" : "var(--text-muted)",
                    cursor: "pointer",
                    textAlign: "left",
                    transition: "var(--transition-fast)",
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "0.84rem", marginBottom: "4px" }}>
                    Sudden Surge Burst
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                    Z-Score Detector: Sudden surge exceeding z &gt; 3.0
                  </div>
                </button>
              </div>
            </div>

            {/* Severity Selector */}
            <div>
              <label style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 600, display: "block", marginBottom: "6px" }}>
                Leak Flow Magnitude / Severity
              </label>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
                {(["low", "medium", "high"] as const).map((sev) => {
                  const flowText =
                    leakType === "slow_leak"
                      ? sev === "high"
                        ? "+22.0 L/h"
                        : sev === "medium"
                        ? "+12.0 L/h"
                        : "+5.5 L/h"
                      : sev === "high"
                      ? "+550 L/h"
                      : sev === "medium"
                      ? "+320 L/h"
                      : "+180 L/h";

                  return (
                    <button
                      key={sev}
                      type="button"
                      onClick={() => setSeverity(sev)}
                      style={{
                        padding: "8px 10px",
                        borderRadius: "var(--radius-sm)",
                        border: `1px solid ${severity === sev ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
                        background: severity === sev ? "rgba(6, 182, 212, 0.15)" : "var(--bg-card)",
                        color: severity === sev ? "var(--accent-cyan)" : "var(--text-dim)",
                        cursor: "pointer",
                        fontWeight: 600,
                        fontSize: "0.78rem",
                        textTransform: "capitalize",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "2px",
                      }}
                    >
                      <span>{sev}</span>
                      <span style={{ fontSize: "0.68rem", opacity: 0.8 }}>{flowText}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
              <button
                className="btn btn-primary"
                onClick={handleInject}
                disabled={isInjecting || (demoStatus?.status === "detected" && !demoStatus?.alert_resolved)}
                style={{ flex: 2, padding: "12px", justifyContent: "center" }}
              >
                {isInjecting ? (
                  <>
                    <span className="pulse">Injecting Telemetry...</span>
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Inject Simulated Leak
                  </>
                )}
              </button>

              <button
                className="btn btn-secondary"
                onClick={handleReset}
                disabled={isResetting || demoStatus?.status === "idle"}
                style={{ flex: 1, padding: "12px", justifyContent: "center" }}
                title="Rollback injected demo readings and alerts"
              >
                {isResetting ? "Cleaning..." : (
                  <>
                    <RotateCcw size={15} />
                    Reset Demo
                  </>
                )}
              </button>
            </div>

            {demoStatus?.status === "detected" && !demoStatus?.alert_resolved && (
              <div style={{ fontSize: "0.75rem", color: "var(--color-warning)", display: "flex", alignItems: "center", gap: "6px" }}>
                <AlertTriangle size={14} />
                <span>An active leak event is currently running. Resolve Alert #{demoStatus.alert_id} or click Reset before injecting another.</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Active Event & Impact Summary */}
        <div className="card" style={{ padding: "24px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "14px" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldAlert size={18} color={activeAlert ? "var(--color-danger)" : "var(--accent-cyan)"} />
                Active Incident Telemetry
              </h3>
              {activeAlert && (
                <span className={`badge ${activeAlert.resolved ? "badge-normal" : "badge-danger"}`}>
                  {activeAlert.resolved ? "RESOLVED" : "ACTIVE UNRESOLVED"}
                </span>
              )}
            </div>

            {demoStatus?.alert_id ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div
                  style={{
                    padding: "14px",
                    borderRadius: "var(--radius-sm)",
                    background: demoStatus.alert_resolved ? "rgba(34, 197, 94, 0.08)" : "rgba(239, 68, 68, 0.08)",
                    border: `1px solid ${demoStatus.alert_resolved ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)"}`,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>
                      Alert #{demoStatus.alert_id} ({demoStatus.zone_name})
                    </span>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                      Flow: {demoStatus.leak_flow_lph} L/h
                    </span>
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", lineHeight: 1.4, marginBottom: "8px" }}>
                    {demoStatus.detector_message || "Anomaly detected and verified by automated detection engine."}
                  </div>
                  <div style={{ display: "flex", gap: "14px", fontSize: "0.74rem", color: "var(--text-dim)" }}>
                    <span>Detector: <b style={{ color: "var(--text-main)" }}>{demoStatus.detector_name}</b></span>
                    <span>Total Vol: <b style={{ color: "var(--text-main)" }}>{demoStatus.total_leak_volume_litres} L</b></span>
                  </div>
                </div>

                {/* Resolve Action Button if not yet resolved */}
                {!demoStatus.alert_resolved && (
                  <button
                    className="btn btn-primary"
                    onClick={() => handleResolveAlertClick(demoStatus.alert_id!)}
                    disabled={isResolvingDemoAlert}
                    style={{
                      background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                      borderColor: "#10b981",
                      justifyContent: "center",
                      padding: "10px",
                    }}
                  >
                    <CheckCircle size={16} />
                    {isResolvingDemoAlert ? "Resolving Alert..." : `Acknowledge & Resolve Alert #${demoStatus.alert_id}`}
                  </button>
                )}

                {demoStatus.alert_resolved && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      color: "#4ade80",
                      fontSize: "0.82rem",
                      fontWeight: 600,
                    }}
                  >
                    <CheckCircle2 size={16} />
                    <span>Incident successfully acknowledged and resolved. Telemetry returned to normal baseline.</span>
                  </div>
                )}
              </div>
            ) : (
              <div
                style={{
                  padding: "36px 20px",
                  textAlign: "center",
                  color: "var(--text-dim)",
                  fontSize: "0.85rem",
                  background: "var(--bg-card)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px dashed var(--border-subtle)",
                }}
              >
                <Droplet size={32} style={{ margin: "0 auto 10px auto", opacity: 0.4 }} />
                <div>No simulated leak active currently.</div>
                <div style={{ fontSize: "0.75rem", marginTop: "4px" }}>
                  Select a zone on the left and click <b>Inject Simulated Leak</b> to start.
                </div>
              </div>
            )}
          </div>

          {/* Quick Stats Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "10px",
              marginTop: "16px",
              paddingTop: "14px",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>Today's Total Flow</div>
              <div style={{ fontSize: "1rem", fontWeight: 700, color: "var(--accent-cyan)" }}>
                {summary?.today_usage_litres.toLocaleString() || "—"} L
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>Active Leaks Count</div>
              <div style={{ fontSize: "1rem", fontWeight: 700, color: (summary?.active_alerts || 0) > 0 ? "var(--color-danger)" : "var(--color-success)" }}>
                {summary?.active_alerts || 0} alerts
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>{selectedZone.name} Budget Status</div>
              <div style={{ fontSize: "0.85rem", fontWeight: 600 }}>
                {currentZoneBudget ? `${currentZoneBudget.consumed_percent.toFixed(1)}% (${currentZoneBudget.status})` : "—"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>Est. Monthly Waste</div>
              <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--color-warning)" }}>
                {savings?.total_monthly_savings ? `$${savings.total_monthly_savings.toFixed(2)}` : "$0.00"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. EVENT SEQUENCE TIMELINE */}
      <div className="card" style={{ padding: "24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
            <Clock size={18} color="var(--accent-cyan)" />
            Demonstration Milestone Timeline
          </h3>
          <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
            {demoStatus?.timeline.length || 0} milestone events recorded
          </span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {demoStatus?.timeline.map((item, idx) => (
            <div
              key={`${item.step}-${idx}`}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "14px",
                padding: "12px 16px",
                borderRadius: "var(--radius-sm)",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background:
                    item.status === "completed"
                      ? "rgba(34, 197, 94, 0.2)"
                      : "rgba(6, 182, 212, 0.2)",
                  color: item.status === "completed" ? "#4ade80" : "var(--accent-cyan)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: "0.75rem",
                  flexShrink: 0,
                  marginTop: "2px",
                }}
              >
                {item.status === "completed" ? <CheckCircle size={15} /> : idx + 1}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontWeight: 700, fontSize: "0.88rem" }}>{item.title}</div>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-dim)" }}>
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </div>
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "3px" }}>
                  {item.description}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. TELEMETRY GRAPH FOR SELECTED ZONE */}
      {demoStatus?.telemetry_points && demoStatus.telemetry_points.length > 0 && (
        <div className="card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700, margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <Activity size={18} color="var(--accent-cyan)" />
                Streamed Telemetry Trace: {demoStatus.zone_name}
              </h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-dim)", margin: "4px 0 0 0" }}>
                Visualizing baseline vs. simulated leak consumption points in real time
              </p>
            </div>
            <div style={{ display: "flex", gap: "12px", fontSize: "0.75rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "var(--accent-cyan)" }} />
                Actual Reading (L)
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ width: "10px", height: "10px", borderRadius: "2px", background: "rgba(255, 255, 255, 0.3)" }} />
                Baseline (L)
              </span>
            </div>
          </div>

          <div style={{ width: "100%", height: "240px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={demoStatus.telemetry_points.map((p) => ({
                  time: new Date(p.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                  litres: p.litres,
                  baseline: p.baseline_litres,
                  isAnomaly: p.is_anomaly,
                }))}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="demoTelemetryGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-cyan)" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="var(--accent-cyan)" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" />
                <XAxis dataKey="time" stroke="var(--text-dim)" fontSize={11} />
                <YAxis stroke="var(--text-dim)" fontSize={11} unit="L" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(10, 17, 34, 0.95)",
                    borderColor: "var(--border-subtle)",
                    borderRadius: "8px",
                    fontSize: "0.8rem",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="baseline"
                  stroke="rgba(255, 255, 255, 0.3)"
                  strokeDasharray="4 4"
                  fill="none"
                  name="Baseline (L)"
                />
                <Area
                  type="monotone"
                  dataKey="litres"
                  stroke="var(--accent-cyan)"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#demoTelemetryGrad)"
                  name="Recorded Litres"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 5. GUIDED 2-3 MINUTE PRESENTATION WALKTHROUGH */}
      <div className="card" style={{ padding: "20px 24px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            cursor: "pointer",
          }}
          onClick={() => setShowPresenterGuide(!showPresenterGuide)}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Sparkles size={18} color="var(--accent-cyan)" />
            <h3 style={{ fontSize: "0.95rem", fontWeight: 700, margin: 0 }}>
              2-Minute Classroom Demo Script & Talking Points
            </h3>
          </div>
          <span style={{ fontSize: "0.8rem", color: "var(--accent-cyan)", fontWeight: 600 }}>
            {showPresenterGuide ? "Collapse Guide ▲" : "Expand Guide ▼"}
          </span>
        </div>

        {showPresenterGuide && (
          <div
            style={{
              marginTop: "16px",
              paddingTop: "16px",
              borderTop: "1px solid var(--border-subtle)",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "16px",
            }}
          >
            <div style={{ background: "var(--bg-elevated)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
              <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--accent-cyan)", marginBottom: "4px" }}>
                Phase 1: Baseline Context
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                Show the normal 5 zones and daily budgets on the Overview tab. Explain diurnal patterns (morning &amp; evening peaks, near-zero night flow).
              </div>
            </div>

            <div style={{ background: "var(--bg-elevated)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
              <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--accent-cyan)", marginBottom: "4px" }}>
                Phase 2: Injection &amp; Detection
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                Select a zone and click <b>Inject Simulated Leak</b>. Show the live telemetry arrival and how the Rule-Based detector or Z-Score algorithm immediately catches it.
              </div>
            </div>

            <div style={{ background: "var(--bg-elevated)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
              <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--accent-cyan)", marginBottom: "4px" }}>
                Phase 3: Impact &amp; Resolution
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                Point out how the active alert appears, budget gauge shifts, and monthly savings update. Click <b>Acknowledge &amp; Resolve</b> to restore normal operational state.
              </div>
            </div>

            <div style={{ background: "var(--bg-elevated)", padding: "14px", borderRadius: "var(--radius-sm)" }}>
              <div style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--accent-cyan)", marginBottom: "4px" }}>
                Phase 4: Safe Reset
              </div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                Click <b>Reset Demo</b> to demonstrate clean session rollback: injected readings are cleaned up while all 7,200 evaluation readings remain preserved.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
