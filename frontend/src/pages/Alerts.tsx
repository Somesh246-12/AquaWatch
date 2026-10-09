import React, { useState } from "react";
import {
  BrainCircuit,
  CheckCircle,
  RotateCcw,
  Search,
  ShieldAlert,
  X,
} from "lucide-react";
import type {
  Alert,
  DetectionRunResponse,
  Zone,
} from "../types/api";

interface AlertsProps {
  alerts: Alert[];
  zones: Zone[];
  onResolveAlert: (alertId: number) => Promise<void>;
  onRunDetection: (contamination: number) => Promise<DetectionRunResponse>;
  isResolving: boolean;
  onRefresh: () => void;
}

export const Alerts: React.FC<AlertsProps> = ({
  alerts,
  zones,
  onResolveAlert,
  onRunDetection,
  isResolving,
  onRefresh,
}) => {
  const [selectedZoneId, setSelectedZoneId] = useState<string>("all");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("unresolved");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [activeModalAlert, setActiveModalAlert] = useState<Alert | null>(null);
  const [detectionResult, setDetectionResult] = useState<DetectionRunResponse | null>(null);
  const [isRunningDetection, setIsRunningDetection] = useState<boolean>(false);

  // Filtered alerts list
  const filteredAlerts = React.useMemo(() => {
    return alerts.filter((a) => {
      if (selectedZoneId !== "all" && a.zone_id !== Number(selectedZoneId)) return false;
      if (selectedSeverity !== "all" && a.severity !== selectedSeverity) return false;
      if (selectedStatus === "unresolved" && a.resolved) return false;
      if (selectedStatus === "resolved" && !a.resolved) return false;
      if (selectedType !== "all" && a.alert_type !== selectedType) return false;
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        const zone = zones.find((z) => z.id === a.zone_id);
        const zoneMatch = zone?.name.toLowerCase().includes(query) || false;
        const msgMatch = a.message.toLowerCase().includes(query);
        const typeMatch = a.alert_type.toLowerCase().includes(query);
        if (!zoneMatch && !msgMatch && !typeMatch) return false;
      }
      return true;
    });
  }, [alerts, selectedZoneId, selectedSeverity, selectedStatus, selectedType, searchQuery, zones]);

  // Statistics counters
  const totalCount = alerts.length;
  const unresolvedCount = alerts.filter((a) => !a.resolved).length;
  const highSeverityCount = alerts.filter((a) => a.severity === "high" && !a.resolved).length;
  const leaksCount = alerts.filter((a) => a.alert_type === "leak" && !a.resolved).length;

  const handleRunDetection = async () => {
    setIsRunningDetection(true);
    try {
      const res = await onRunDetection(0.02);
      setDetectionResult(res);
      onRefresh();
    } catch (err: any) {
      alert(`Detection failed: ${err.message}`);
    } finally {
      setIsRunningDetection(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* 1. TOP SUMMARY METRICS & PIPELINE TRIGGER */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))",
          gap: "16px",
        }}
      >
        <div className="card" style={{ padding: "18px" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 600 }}>
            Unresolved Events
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: unresolvedCount > 0 ? "var(--color-danger)" : "var(--text-main)", marginTop: "4px" }}>
            {unresolvedCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Out of {totalCount} historical alerts</div>
        </div>

        <div className="card" style={{ padding: "18px" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 600 }}>
            High Severity
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "#fb7185", marginTop: "4px" }}>
            {highSeverityCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Urgent attention required</div>
        </div>

        <div className="card" style={{ padding: "18px" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase", fontWeight: 600 }}>
            Active Night Leaks
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--accent-cyan)", marginTop: "4px" }}>
            {leaksCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Rule-based flow anomalies</div>
        </div>

        {/* Action Card: Trigger Pipeline */}
        <div
          className="card"
          style={{
            padding: "18px",
            background: "linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(15, 31, 64, 0.8) 100%)",
            border: "1px solid rgba(6, 182, 212, 0.3)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
          }}
        >
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--accent-cyan-light)", textTransform: "uppercase", fontWeight: 700 }}>
              Autonomous Pipeline
            </div>
            <div style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginTop: "2px" }}>
              Run all 3 detectors & benchmark evaluation
            </div>
          </div>
          <button
            onClick={handleRunDetection}
            disabled={isRunningDetection}
            className="btn btn-primary btn-sm"
            style={{ width: "100%", marginTop: "10px" }}
          >
            <BrainCircuit size={16} />
            <span>{isRunningDetection ? "Executing Models..." : "Run Detection Pipeline"}</span>
          </button>
        </div>
      </div>

      {/* 2. SEARCH & FILTER CONTROLS */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {/* Search bar */}
          <div style={{ display: "flex", alignItems: "center", width: "100%", position: "relative" }}>
            <Search size={16} color="var(--text-dim)" style={{ position: "absolute", left: "12px", pointerEvents: "none" }} />
            <input
              type="text"
              placeholder="Search diagnostic messages, zones, anomaly types..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input"
              style={{ width: "100%", paddingLeft: "36px" }}
            />
          </div>

          {/* Filter Dropdowns Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 150px), 1fr))", gap: "10px" }}>
            {/* Zone filter */}
            <select
              value={selectedZoneId}
              onChange={(e) => setSelectedZoneId(e.target.value)}
              className="select"
              style={{ width: "100%" }}
            >
              <option value="all">All Zones</option>
              {zones.map((z) => (
                <option key={z.id} value={String(z.id)}>
                  {z.name}
                </option>
              ))}
            </select>

            {/* Severity filter */}
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="select"
              style={{ width: "100%" }}
            >
              <option value="all">All Severities</option>
              <option value="high">High Severity</option>
              <option value="medium">Medium Severity</option>
              <option value="low">Low Severity</option>
            </select>

            {/* Alert Type filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="select"
              style={{ width: "100%" }}
            >
              <option value="all">All Alert Types</option>
              <option value="leak">Leak (Rule-Based)</option>
              <option value="spike">Spike (Z-Score)</option>
              <option value="abnormal_usage">Abnormal (Isolation Forest)</option>
            </select>

            {/* Status filter */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="select"
              style={{ width: "100%" }}
            >
              <option value="unresolved">Unresolved Only</option>
              <option value="resolved">Resolved Only</option>
              <option value="all">All Statuses</option>
            </select>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--text-dim)" }}>
          <span>Showing {filteredAlerts.length} matching events</span>
          {(selectedZoneId !== "all" || selectedSeverity !== "all" || selectedType !== "all" || searchQuery) && (
            <button
              onClick={() => {
                setSelectedZoneId("all");
                setSelectedSeverity("all");
                setSelectedType("all");
                setSearchQuery("");
                setSelectedStatus("unresolved");
              }}
              className="btn btn-outline btn-sm"
              style={{ fontSize: "0.6875rem", padding: "2px 8px" }}
            >
              <RotateCcw size={12} /> Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* 3. ALERTS TABLE & MOBILE CARDS */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {/* Desktop Table View (>= 769px) */}
        <div className="alerts-desktop-table table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Zone</th>
                <th>Alert Type</th>
                <th>Detected At</th>
                <th>Diagnostic Description</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "48px", color: "var(--text-muted)" }}>
                    <CheckCircle size={32} color="var(--color-success)" style={{ margin: "0 auto 8px" }} />
                    <p style={{ fontWeight: 600 }}>No alerts matching the selected criteria</p>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Adjust filters or execute the detection engine.</p>
                  </td>
                </tr>
              ) : (
                filteredAlerts.map((alert) => {
                  const zone = zones.find((z) => z.id === alert.zone_id);
                  return (
                    <tr
                      key={alert.id}
                      style={{ cursor: "pointer" }}
                      onClick={() => setActiveModalAlert(alert)}
                    >
                      <td>
                        <span className={`badge badge-${alert.severity === "high" ? "danger" : alert.severity === "medium" ? "warning" : "info"}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td style={{ fontWeight: 600 }}>{zone?.name || `Zone ${alert.zone_id}`}</td>
                      <td>
                        <span className={`badge ${alert.alert_type === "leak" ? "badge-info" : alert.alert_type === "spike" ? "badge-warning" : "badge-purple"}`}>
                          {alert.alert_type.replace("_", " ")}
                        </span>
                      </td>
                      <td style={{ fontSize: "0.8125rem", color: "var(--text-dim)", whiteSpace: "nowrap" }}>
                        {new Date(alert.timestamp).toLocaleString()}
                      </td>
                      <td style={{ maxWidth: "380px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {alert.message}
                      </td>
                      <td>
                        <span className={`badge ${alert.resolved ? "badge-normal" : "badge-danger"}`}>
                          {alert.resolved ? "Resolved" : "Active"}
                        </span>
                      </td>
                      <td style={{ textAlign: "right" }} onClick={(e) => e.stopPropagation()}>
                        {!alert.resolved ? (
                          <button
                            onClick={() => onResolveAlert(alert.id)}
                            disabled={isResolving}
                            className="btn btn-secondary btn-sm"
                            style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                          >
                            Resolve
                          </button>
                        ) : (
                          <span style={{ fontSize: "0.75rem", color: "var(--color-success)", fontWeight: 600 }}>
                            Fixed
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile Alert Cards View (<= 768px) */}
        <div className="alerts-mobile-cards">
          {filteredAlerts.length === 0 ? (
            <div style={{ textAlign: "center", padding: "32px 16px", color: "var(--text-muted)" }}>
              <CheckCircle size={32} color="var(--color-success)" style={{ margin: "0 auto 8px" }} />
              <p style={{ fontWeight: 600 }}>No alerts matching the selected criteria</p>
              <p style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>Adjust filters or execute the detection engine.</p>
            </div>
          ) : (
            filteredAlerts.map((alert) => {
              const zone = zones.find((z) => z.id === alert.zone_id);
              return (
                <div
                  key={alert.id}
                  onClick={() => setActiveModalAlert(alert)}
                  style={{
                    padding: "14px",
                    background: "rgba(10, 20, 44, 0.6)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "var(--radius-md)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span className={`badge badge-${alert.severity === "high" ? "danger" : alert.severity === "medium" ? "warning" : "info"}`}>
                        {alert.severity}
                      </span>
                      <span style={{ fontWeight: 700, fontSize: "0.875rem" }}>
                        {zone?.name || `Zone ${alert.zone_id}`}
                      </span>
                    </div>
                    <span className={`badge ${alert.resolved ? "badge-normal" : "badge-danger"}`}>
                      {alert.resolved ? "Resolved" : "Active"}
                    </span>
                  </div>

                  <p style={{ fontSize: "0.8125rem", color: "var(--text-main)", margin: 0, lineHeight: 1.4 }}>
                    {alert.message}
                  </p>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px", paddingTop: "6px", borderTop: "1px solid rgba(255, 255, 255, 0.06)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span className={`badge ${alert.alert_type === "leak" ? "badge-info" : alert.alert_type === "spike" ? "badge-warning" : "badge-purple"}`} style={{ fontSize: "0.6875rem" }}>
                        {alert.alert_type.replace("_", " ")}
                      </span>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                        {new Date(alert.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", month: "short", day: "numeric" })}
                      </span>
                    </div>

                    {!alert.resolved ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onResolveAlert(alert.id);
                        }}
                        disabled={isResolving}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: "0.75rem", padding: "5px 12px" }}
                      >
                        Resolve Alert
                      </button>
                    ) : (
                      <span style={{ fontSize: "0.75rem", color: "var(--color-success)", fontWeight: 600 }}>
                        Fixed
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 4. ALERT DETAIL MODAL DIALOG */}
      {activeModalAlert && (
        <div
          onClick={() => setActiveModalAlert(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="card"
            style={{
              maxWidth: "540px",
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              background: "#0c1833",
              border: "1px solid var(--accent-cyan)",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.8)",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <ShieldAlert size={22} color="var(--color-danger)" />
                <h3 style={{ fontSize: "1.125rem", fontWeight: 700 }}>Alert Event #{activeModalAlert.id}</h3>
              </div>
              <button
                onClick={() => setActiveModalAlert(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "0.875rem" }}>
              <div>
                <span style={{ color: "var(--text-dim)", fontSize: "0.75rem", textTransform: "uppercase" }}>Zone</span>
                <div style={{ fontWeight: 600 }}>{zones.find((z) => z.id === activeModalAlert.zone_id)?.name || `Zone ${activeModalAlert.zone_id}`}</div>
              </div>
              <div>
                <span style={{ color: "var(--text-dim)", fontSize: "0.75rem", textTransform: "uppercase" }}>Severity</span>
                <div>
                  <span className={`badge badge-${activeModalAlert.severity === "high" ? "danger" : activeModalAlert.severity === "medium" ? "warning" : "info"}`}>
                    {activeModalAlert.severity}
                  </span>
                </div>
              </div>
              <div>
                <span style={{ color: "var(--text-dim)", fontSize: "0.75rem", textTransform: "uppercase" }}>Detection Category</span>
                <div style={{ fontWeight: 600, textTransform: "capitalize" }}>{activeModalAlert.alert_type.replace("_", " ")}</div>
              </div>
              <div>
                <span style={{ color: "var(--text-dim)", fontSize: "0.75rem", textTransform: "uppercase" }}>Timestamp</span>
                <div style={{ fontWeight: 500 }}>{new Date(activeModalAlert.timestamp).toLocaleString()}</div>
              </div>
            </div>

            <div>
              <span style={{ color: "var(--text-dim)", fontSize: "0.75rem", textTransform: "uppercase" }}>Diagnostic Message</span>
              <div
                style={{
                  marginTop: "6px",
                  padding: "12px",
                  background: "rgba(6, 12, 26, 0.8)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  fontSize: "0.875rem",
                  lineHeight: 1.5,
                }}
              >
                {activeModalAlert.message}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
              <button onClick={() => setActiveModalAlert(null)} className="btn btn-outline btn-sm">
                Close
              </button>
              {!activeModalAlert.resolved && (
                <button
                  onClick={async () => {
                    await onResolveAlert(activeModalAlert.id);
                    setActiveModalAlert(null);
                  }}
                  className="btn btn-primary btn-sm"
                >
                  Mark as Resolved
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 5. DETECTION RUN RESULT MODAL */}
      {detectionResult && (
        <div
          onClick={() => setDetectionResult(null)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="card"
            style={{
              maxWidth: "680px",
              width: "100%",
              background: "#0c1833",
              border: "1px solid var(--accent-cyan)",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <BrainCircuit size={22} color="var(--accent-cyan)" />
                <h3 style={{ fontSize: "1.125rem", fontWeight: 700 }}>Detection Pipeline Results</h3>
              </div>
              <button
                onClick={() => setDetectionResult(null)}
                style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Run summary stats */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "12px",
                padding: "14px",
                background: "rgba(6, 12, 26, 0.7)",
                borderRadius: "var(--radius-md)",
                textAlign: "center",
              }}
            >
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Candidate Events</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 800 }}>{detectionResult.candidate_detections}</div>
              </div>
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>New Alerts Created</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--color-success)" }}>{detectionResult.alerts_created}</div>
              </div>
              <div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Duplicates Skipped</div>
                <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-muted)" }}>{detectionResult.alerts_existing}</div>
              </div>
            </div>

            {/* Benchmark Table */}
            <div>
              <div style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "8px" }}>Ground Truth Benchmark Scoring</div>
              <div className="table-container">
                <table className="table" style={{ fontSize: "0.8125rem" }}>
                  <thead>
                    <tr>
                      <th>Detector Model</th>
                      <th>Precision</th>
                      <th>Recall</th>
                      <th>F1-Score</th>
                      <th>TP / FP / FN</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(detectionResult.evaluation).map(([method, em]) => (
                      <tr key={method}>
                        <td style={{ fontWeight: 600, textTransform: "capitalize" }}>{method.replace("_", " ")}</td>
                        <td>{(em.precision * 100).toFixed(1)}%</td>
                        <td>{(em.recall * 100).toFixed(1)}%</td>
                        <td>{em.f1_score.toFixed(3)}</td>
                        <td>
                          {em.true_positives} TP / {em.false_positives} FP / {em.false_negatives} FN
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button onClick={() => setDetectionResult(null)} className="btn btn-primary btn-sm">
                Acknowledged
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
