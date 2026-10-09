import React, { useState } from "react";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  Droplet,
  Filter,
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
import type {
  Alert,
  ConservationBudgetsResponse,
  Reading,
  Zone,
} from "../types/api";

interface ZonesProps {
  zones: Zone[];
  budgets: ConservationBudgetsResponse | null;
  selectedDate: string;
  onSelectDate: (date: string) => void;
  hourlyReadings: Reading[];
  alerts: Alert[];
}

export const Zones: React.FC<ZonesProps> = ({
  zones,
  budgets,
  selectedDate,
  onSelectDate,
  hourlyReadings,
  alerts,
}) => {
  const [selectedZoneId, setSelectedZoneId] = useState<number | null>(1);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredZoneBudgets = React.useMemo(() => {
    if (!budgets?.zones) return [];
    if (statusFilter === "all") return budgets.zones;
    return budgets.zones.filter((zb) => zb.status === statusFilter);
  }, [budgets, statusFilter]);

  const selectedZone = zones.find((z) => z.id === selectedZoneId) || zones[0];
  const selectedZoneBudget = budgets?.zones.find((z) => z.zone_id === selectedZoneId);

  // Hourly readings for selected zone
  const zoneHourlyData = React.useMemo(() => {
    if (!selectedZoneId) return [];
    return hourlyReadings
      .filter((r) => r.zone_id === selectedZoneId)
      .slice(-24)
      .map((r) => ({
        time: r.timestamp.slice(11, 16),
        litres: Math.round(r.litres * 10) / 10,
      }));
  }, [hourlyReadings, selectedZoneId]);

  // Alerts for selected zone
  const zoneAlerts = React.useMemo(() => {
    if (!selectedZoneId) return [];
    return alerts.filter((a) => a.zone_id === selectedZoneId);
  }, [alerts, selectedZoneId]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Top Filter and Controls Bar */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Filter size={18} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.875rem", fontWeight: 600 }}>Filter Status:</span>
          <div style={{ display: "flex", gap: "6px" }}>
            {["all", "normal", "warning", "exceeded"].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`btn btn-sm ${statusFilter === status ? "btn-primary" : "btn-secondary"}`}
                style={{ textTransform: "capitalize" }}
              >
                {status}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Calendar size={16} color="var(--accent-cyan)" />
          <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Inspection Date:</span>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => onSelectDate(e.target.value)}
            className="input"
            style={{ padding: "4px 10px", fontSize: "0.8125rem" }}
          />
        </div>
      </div>

      {/* Zone Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "18px",
        }}
      >
        {filteredZoneBudgets.map((zb) => {
          const isSelected = zb.zone_id === selectedZoneId;
          return (
            <div
              key={zb.zone_id}
              onClick={() => setSelectedZoneId(zb.zone_id)}
              className="card card-hover"
              style={{
                cursor: "pointer",
                border: isSelected ? "2px solid var(--accent-cyan)" : "1px solid var(--border-subtle)",
                background: isSelected ? "rgba(14, 30, 64, 0.9)" : "var(--bg-card)",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "14px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <h3 style={{ fontSize: "1.125rem", fontWeight: 700 }}>{zb.zone_name}</h3>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "capitalize" }}>
                    {zb.zone_type.replace("_", " ")}
                  </span>
                </div>
                <span className={`badge badge-${zb.status}`}>{zb.status}</span>
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", marginBottom: "6px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Usage / Budget</span>
                  <span style={{ fontWeight: 600 }}>{zb.consumed_percent}%</span>
                </div>
                <div className="progress-bar-bg">
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

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "10px",
                  fontSize: "0.8125rem",
                  paddingTop: "8px",
                  borderTop: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <div>
                  <div style={{ color: "var(--text-dim)", fontSize: "0.6875rem", textTransform: "uppercase" }}>Actual</div>
                  <div style={{ fontWeight: 700 }}>{zb.actual_consumption_litres.toLocaleString()} L</div>
                </div>
                <div>
                  <div style={{ color: "var(--text-dim)", fontSize: "0.6875rem", textTransform: "uppercase" }}>Allowance</div>
                  <div style={{ fontWeight: 700 }}>{zb.daily_budget_litres.toLocaleString()} L</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Zone Deep Dive Panel */}
      {selectedZone && (
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="section-title">
                <Droplet size={20} color="var(--accent-cyan)" />
                Zone Telemetry Deep Dive: {selectedZone.name}
              </h2>
              <p className="page-subtitle">
                Category: {selectedZone.type} • Daily Allowance: {selectedZone.daily_budget_litres.toLocaleString()} Litres
              </p>
            </div>

            {selectedZoneBudget && (
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span className={`badge badge-${selectedZoneBudget.status}`} style={{ fontSize: "0.8125rem" }}>
                  {selectedZoneBudget.status} status ({selectedZoneBudget.consumed_percent}% budget used)
                </span>
              </div>
            )}
          </div>

          <div className="grid-2">
            {/* Hourly Flow Chart for Selected Zone */}
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px", fontSize: "0.875rem", fontWeight: 600 }}>
                <Clock size={16} color="var(--accent-cyan)" />
                Recent Hourly Consumption (24 Hours)
              </div>
              <div style={{ height: "240px", width: "100%" }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={zoneHourlyData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="zoneGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `${v}L`} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0a1329",
                        borderColor: "rgba(6, 182, 212, 0.3)",
                        borderRadius: "8px",
                        color: "#f8fafc",
                      }}
                      formatter={(val: any) => [`${val} Litres`, "Hourly Flow"]}
                    />
                    <Area type="monotone" dataKey="litres" stroke="#06b6d4" strokeWidth={2} fillOpacity={1} fill="url(#zoneGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Zone Telemetry Metrics & Active Anomalies */}
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.875rem", fontWeight: 600 }}>
                <AlertTriangle size={16} color="var(--color-danger)" />
                Zone Anomalies & Leaks ({zoneAlerts.length})
              </div>

              {zoneAlerts.length === 0 ? (
                <div
                  style={{
                    padding: "24px",
                    background: "rgba(10, 20, 44, 0.5)",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                    textAlign: "center",
                    color: "var(--text-muted)",
                  }}
                >
                  <CheckCircle2 size={24} color="var(--color-success)" style={{ margin: "0 auto 6px" }} />
                  <p style={{ fontWeight: 600 }}>No anomalies recorded in {selectedZone.name}</p>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "240px", overflowY: "auto" }}>
                  {zoneAlerts.map((a) => (
                    <div
                      key={a.id}
                      style={{
                        padding: "10px 14px",
                        background: "rgba(10, 20, 44, 0.6)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: "var(--radius-md)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        fontSize: "0.8125rem",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <span className={`badge badge-${a.severity === "high" ? "danger" : a.severity === "medium" ? "warning" : "info"}`}>
                          {a.severity}
                        </span>
                        <div>
                          <div style={{ fontWeight: 600, textTransform: "capitalize" }}>{a.alert_type.replace("_", " ")}</div>
                          <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                            {new Date(a.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      <span className={`badge ${a.resolved ? "badge-normal" : "badge-danger"}`}>
                        {a.resolved ? "Resolved" : "Active"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
