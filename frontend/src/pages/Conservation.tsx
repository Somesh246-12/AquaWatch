import React from "react";
import {
  Calendar,
  Droplet,
  Info,
  Layers,
  Leaf,
  Sliders,
  Sparkles,
} from "lucide-react";
import type {
  ConservationBudgetsResponse,
  ConservationSavingsResponse,
  ConservationTipsResponse,
} from "../types/api";

interface ConservationProps {
  budgets: ConservationBudgetsResponse | null;
  tips: ConservationTipsResponse | null;
  savings: ConservationSavingsResponse | null;
  selectedDate: string;
  onSelectDate: (date: string) => void;
  tariff: number;
  hoursPerDay: number;
  onUpdateTariff: (tariff: number) => void;
  onUpdateHoursPerDay: (hours: number) => void;
}

export const Conservation: React.FC<ConservationProps> = ({
  budgets,
  tips,
  savings,
  selectedDate,
  onSelectDate,
  tariff,
  hoursPerDay,
  onUpdateTariff,
  onUpdateHoursPerDay,
}) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
      {/* 1. TOP SAVINGS ESTIMATOR HERO SECTION */}
      <div
        className="card"
        style={{
          background: "linear-gradient(135deg, rgba(16, 33, 68, 0.9) 0%, rgba(12, 24, 51, 0.95) 100%)",
          border: "1px solid rgba(6, 182, 212, 0.3)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "20px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--accent-cyan)", marginBottom: "6px" }}>
              <Leaf size={20} />
              <span style={{ fontSize: "0.8125rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Financial & Resource Conservation Estimator
              </span>
            </div>
            <h2 style={{ fontSize: "1.75rem", fontWeight: 800, color: "#ffffff", letterSpacing: "-0.02em" }}>
              Estimated Monthly Savings: ${savings?.total_monthly_savings ? savings.total_monthly_savings.toFixed(2) : "0.00"}
            </h2>
            <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", maxWidth: "560px", marginTop: "4px" }}>
              Projected recovery across {savings?.actionable_leaks_count || 0} active continuous leaks at current utility tariff.
            </p>
          </div>

          {/* Interactive Tariff & Duration Parameter Controls */}
          <div
            style={{
              padding: "16px",
              background: "rgba(6, 12, 26, 0.8)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
              minWidth: "260px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "var(--accent-cyan)", fontWeight: 700, textTransform: "uppercase" }}>
              <Sliders size={14} /> Model Assumptions
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
              <label style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>Tariff ($/1,000L):</label>
              <input
                type="number"
                step="0.25"
                min="0.5"
                max="20"
                value={tariff}
                onChange={(e) => onUpdateTariff(Math.max(0.1, Number(e.target.value)))}
                className="input"
                style={{ width: "90px", padding: "4px 8px", fontSize: "0.8125rem" }}
              />
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
              <label style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>Leak Duration (h/d):</label>
              <input
                type="number"
                step="1"
                min="1"
                max="24"
                value={hoursPerDay}
                onChange={(e) => onUpdateHoursPerDay(Math.min(24, Math.max(1, Number(e.target.value))))}
                className="input"
                style={{ width: "90px", padding: "4px 8px", fontSize: "0.8125rem" }}
              />
            </div>
          </div>
        </div>

        {/* 3 Metric Pills */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "16px",
            marginTop: "24px",
            paddingTop: "20px",
            borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          }}
        >
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Daily Waste Rate</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--color-warning)" }}>
              {savings ? savings.total_daily_wasted_litres.toLocaleString() : "0"} L / day
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>30-Day Monthly Waste</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--color-danger)" }}>
              {savings ? savings.total_monthly_wasted_litres.toLocaleString() : "0"} L / month
            </div>
          </div>
          <div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>Active Monitored Leaks</div>
            <div style={{ fontSize: "1.25rem", fontWeight: 700, color: "var(--accent-cyan)" }}>
              {savings ? `${savings.actionable_leaks_count} / ${savings.total_leaks_evaluated}` : "0"} Actionable
            </div>
          </div>
        </div>

        {/* Disclaimer */}
        <div
          style={{
            marginTop: "16px",
            fontSize: "0.6875rem",
            color: "var(--text-dim)",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <Info size={14} color="var(--accent-cyan)" />
          {savings?.disclaimer || "Estimated savings are projections based on assumed daily leak duration and configured tariffs. They are not guaranteed or measured savings."}
        </div>
      </div>

      {/* 2. LEAK SAVINGS BREAKDOWN TABLE */}
      {savings && savings.leak_estimates.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="section-title">
                <Droplet size={18} color="var(--accent-cyan)" />
                Individual Leak Savings Telemetry
              </h3>
              <p className="page-subtitle">Granular estimates per detected flow anomaly</p>
            </div>
            <span className="badge badge-info">{savings.leak_estimates.length} Detected Leaks</span>
          </div>

          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Alert #</th>
                  <th>Zone</th>
                  <th>Detected Flow Rate</th>
                  <th>Daily Wasted</th>
                  <th>30-Day Wasted</th>
                  <th>Est. Monthly Savings</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {savings.leak_estimates.map((le, idx) => (
                  <tr key={le.alert_id || idx}>
                    <td style={{ fontWeight: 600 }}>#{le.alert_id || "—"}</td>
                    <td>{le.zone_name || `Zone ${le.zone_id}`}</td>
                    <td>{le.leak_flow_lph != null ? `${le.leak_flow_lph} L/h` : "—"}</td>
                    <td>{le.daily_wasted_litres != null ? `${le.daily_wasted_litres.toLocaleString()} L` : "—"}</td>
                    <td>{le.monthly_wasted_litres != null ? `${le.monthly_wasted_litres.toLocaleString()} L` : "—"}</td>
                    <td style={{ fontWeight: 700, color: le.monthly_savings ? "var(--color-warning)" : "inherit" }}>
                      {le.monthly_savings != null ? `$${le.monthly_savings.toFixed(2)}` : "—"}
                    </td>
                    <td>
                      <span className={`badge ${le.status === "estimated" ? "badge-normal" : "badge-neutral"}`}>
                        {le.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 3. TARGETED CONSERVATION RECOMMENDATIONS */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="section-title">
              <Sparkles size={18} color="var(--accent-cyan)" />
              Actionable Water-Saving Recommendations
            </h3>
            <p className="page-subtitle">Algorithmic guidance prioritized by severity and budget impact</p>
          </div>
          <span className="badge badge-info">{tips?.total_recommendations || 0} Recommendations</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {tips?.recommendations.map((rec) => (
            <div
              key={rec.id}
              style={{
                padding: "16px 20px",
                background: "rgba(10, 20, 44, 0.6)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "16px",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <span className={`badge ${rec.priority === "critical" || rec.priority === "high" ? "badge-danger" : rec.priority === "medium" ? "badge-warning" : "badge-info"}`}>
                    {rec.priority} Priority
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>
                    Category: {rec.category.replace("_", " ")}
                  </span>
                  {rec.zone_name && (
                    <span style={{ fontSize: "0.75rem", color: "var(--accent-cyan)", fontWeight: 600 }}>
                      • {rec.zone_name}
                    </span>
                  )}
                </div>

                <h4 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-main)" }}>{rec.title}</h4>
                <p style={{ fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>{rec.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 4. WATER BUDGET UTILIZATION SUMMARY TABLE */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="section-title">
              <Layers size={18} color="var(--accent-cyan)" />
              Daily Water Budget Compliance ({budgets?.date})
            </h3>
            <p className="page-subtitle">Allocations, actual volume, remaining quotas, and status</p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <Calendar size={16} color="var(--accent-cyan)" />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => onSelectDate(e.target.value)}
              className="input"
              style={{ padding: "4px 8px", fontSize: "0.8125rem" }}
            />
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Zone Name</th>
                <th>Type</th>
                <th>Daily Budget</th>
                <th>Actual Usage</th>
                <th>Remaining</th>
                <th>Utilization %</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {budgets?.zones.map((zb) => (
                <tr key={zb.zone_id}>
                  <td style={{ fontWeight: 600 }}>{zb.zone_name}</td>
                  <td style={{ color: "var(--text-dim)", textTransform: "capitalize" }}>{zb.zone_type.replace("_", " ")}</td>
                  <td>{zb.daily_budget_litres.toLocaleString()} L</td>
                  <td>{zb.actual_consumption_litres.toLocaleString()} L</td>
                  <td style={{ color: zb.remaining_budget_litres < 0 ? "var(--color-danger)" : "inherit" }}>
                    {zb.remaining_budget_litres.toLocaleString()} L
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span>{zb.consumed_percent}%</span>
                      <div className="progress-bar-bg" style={{ width: "60px", height: "6px" }}>
                        <div
                          className="progress-bar-fill"
                          style={{
                            width: `${Math.min(zb.consumed_percent, 100)}%`,
                            backgroundColor:
                              zb.status === "exceeded"
                                ? "var(--color-danger)"
                                : zb.status === "warning"
                                ? "var(--color-warning)"
                                : "var(--accent-cyan)",
                          }}
                        />
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={`badge badge-${zb.status}`}>{zb.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
