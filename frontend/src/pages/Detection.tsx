import React, { useState } from "react";
import {
  BrainCircuit,
  Info,
  ShieldCheck,
  Zap,
} from "lucide-react";
import type { DetectionRunResponse } from "../types/api";

interface DetectionProps {
  lastRunResult: DetectionRunResponse | null;
  onRunDetection: (contamination: number) => Promise<DetectionRunResponse>;
  isRunning: boolean;
}

export const Detection: React.FC<DetectionProps> = ({
  lastRunResult,
  onRunDetection,
  isRunning,
}) => {
  const [contamination, setContamination] = useState<number>(0.02);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const handleExecute = async () => {
    setStatusMessage(null);
    try {
      await onRunDetection(contamination);
      setStatusMessage("Pipeline executed successfully. Alerts and benchmarks updated.");
    } catch (err: any) {
      setStatusMessage(`Pipeline execution failed: ${err.message}`);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
      {/* 1. PIPELINE EXECUTION CONTROL HERO */}
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg, rgba(16, 33, 68, 0.95) 0%, rgba(10, 20, 44, 0.9) 100%)",
          border: "1px solid rgba(6, 182, 212, 0.3)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "20px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--accent-cyan)", marginBottom: "6px" }}>
              <BrainCircuit size={20} />
              <span style={{ fontSize: "0.8125rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Multi-Model Anomaly Detection Engine
              </span>
            </div>
            <h2 style={{ fontSize: "1.75rem", fontWeight: 800, color: "#ffffff", letterSpacing: "-0.02em" }}>
              Ensemble Pipeline & Benchmark Verification
            </h2>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", maxWidth: "600px", marginTop: "6px" }}>
              Executes Rule-Based Night Flow, Statistical Z-Score, and ML Isolation Forest in parallel across all monitored water zones, scoring predictions against synthetic ground-truth events.
            </p>
          </div>

          <div
            style={{
              padding: "16px",
              background: "rgba(6, 12, 26, 0.8)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              width: "100%",
              maxWidth: "300px",
              boxSizing: "border-box",
            }}
          >
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 700 }}>
              Contamination Prior
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
              <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>Isolation Forest:</span>
              <input
                type="number"
                step="0.005"
                min="0.005"
                max="0.1"
                value={contamination}
                onChange={(e) => setContamination(Number(e.target.value))}
                className="input"
                style={{ width: "80px", padding: "4px 8px", fontSize: "0.8125rem" }}
              />
            </div>
            <button
              onClick={handleExecute}
              disabled={isRunning}
              className="btn btn-primary btn-sm"
              style={{ marginTop: "6px", width: "100%" }}
            >
              <Zap size={14} />
              <span>{isRunning ? "Executing Models..." : "Run Detection Pipeline"}</span>
            </button>
          </div>
        </div>

        {statusMessage && (
          <div
            style={{
              marginTop: "16px",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              background: "rgba(16, 185, 129, 0.15)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              fontSize: "0.8125rem",
              color: "#34d399",
            }}
          >
            {statusMessage}
          </div>
        )}
      </div>

      {/* 2. THREE DETECTOR SPECIFICATIONS */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: "20px" }}>
        {/* Model 1: Rule-Based */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span className="badge badge-info">Deterministic</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Alert: 'leak'</span>
          </div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "6px" }}>Rule-Based Night Flow</h3>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.5, marginBottom: "16px" }}>
            Monitors quiet hours (01:00–04:00) for persistent flow &gt; 3.0 L/h lasting at least 3 consecutive hours. Highly reliable for continuous physical leaks.
          </p>
          <div style={{ fontSize: "0.75rem", color: "var(--accent-cyan)", fontWeight: 600 }}>
            Target: Continuous Slow Leaks
          </div>
        </div>

        {/* Model 2: Z-Score */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span className="badge badge-warning">Statistical</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Alert: 'spike'</span>
          </div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "6px" }}>Statistical Z-Score</h3>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.5, marginBottom: "16px" }}>
            Calculates diurnal standardized z-scores per zone and hour-of-day. Flags extreme consumption surges with z &gt; 3.0 against baseline distributions.
          </p>
          <div style={{ fontSize: "0.75rem", color: "var(--color-warning)", fontWeight: 600 }}>
            Target: Pipe Bursts & Sudden Spikes
          </div>
        </div>

        {/* Model 3: Isolation Forest */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <span className="badge badge-purple">Machine Learning</span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Alert: 'abnormal_usage'</span>
          </div>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 700, marginBottom: "6px" }}>Isolation Forest (ML)</h3>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.5, marginBottom: "16px" }}>
            Unsupervised tree ensemble modeling 5 temporal features: hour of day, day of week, flow volume, 3h rolling mean, and 24h rolling baseline.
          </p>
          <div style={{ fontSize: "0.75rem", color: "var(--color-purple)", fontWeight: 600 }}>
            Target: Multivariate Wastage Outliers
          </div>
        </div>
      </div>

      {/* 3. BENCHMARK EVALUATION TABLE */}
      {lastRunResult && (
        <div className="card">
          <div className="card-header" style={{ flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h3 className="section-title">
                <ShieldCheck size={18} color="var(--color-success)" />
                Ground Truth Benchmark Verification
              </h3>
              <p className="page-subtitle">Event-level bipartite matching against 10 synthetic ground-truth anomaly events</p>
            </div>
            <div style={{ display: "flex", gap: "8px", fontSize: "0.8125rem", flexWrap: "wrap" }}>
              <span className="badge badge-neutral">Candidates: {lastRunResult.candidate_detections}</span>
              <span className="badge badge-normal">Created: {lastRunResult.alerts_created}</span>
              <span className="badge badge-warning">Skipped Duplicates: {lastRunResult.alerts_existing}</span>
            </div>
          </div>

          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Method</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1-Score</th>
                  <th>True Positives (TP)</th>
                  <th>False Positives (FP)</th>
                  <th>False Negatives (FN)</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(lastRunResult.evaluation).map(([method, em]) => (
                  <tr key={method}>
                    <td style={{ fontWeight: 700, textTransform: "capitalize" }}>{method.replace("_", " ")}</td>
                    <td style={{ fontWeight: 600, color: em.precision >= 0.8 ? "var(--color-success)" : "inherit" }}>
                      {(em.precision * 100).toFixed(1)}%
                    </td>
                    <td style={{ fontWeight: 600, color: em.recall >= 0.8 ? "var(--color-success)" : "inherit" }}>
                      {(em.recall * 100).toFixed(1)}%
                    </td>
                    <td style={{ fontWeight: 700, color: "var(--accent-cyan)" }}>{em.f1_score.toFixed(3)}</td>
                    <td>{em.true_positives}</td>
                    <td>{em.false_positives}</td>
                    <td>{em.false_negatives}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Deduplication explanation note */}
          <div
            style={{
              marginTop: "16px",
              padding: "12px 16px",
              background: "rgba(6, 12, 26, 0.6)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
              fontSize: "0.75rem",
              color: "var(--text-muted)",
              lineHeight: 1.5,
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
            }}
          >
            <Info size={16} color="var(--accent-cyan)" style={{ flexShrink: 0, marginTop: "2px" }} />
            <div>
              <strong style={{ color: "var(--text-main)" }}>Duplicate Alert Suppression Strategy: </strong>
              Candidate events matching the same zone, alert type, and occurring within a $\pm 4$-hour temporal window of an existing alert are suppressed. This prevents duplicate alert creation on multiple pipeline runs while allowing distinct anomalies to be recorded.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
