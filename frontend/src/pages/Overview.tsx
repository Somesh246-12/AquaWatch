import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  DollarSign,
  Droplet,
  ExternalLink,
  Layers,
  Sparkles,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type {
  Alert,
  ConservationBudgetsResponse,
  ConservationSavingsResponse,
  ConservationTipsResponse,
  DailyReading,
  DashboardSummary,
  Reading,
  Zone,
} from "../types/api";
import type { NavTab } from "../components/layout/Sidebar";

interface OverviewProps {
  summary: DashboardSummary | null;
  budgets: ConservationBudgetsResponse | null;
  savings: ConservationSavingsResponse | null;
  tips: ConservationTipsResponse | null;
  recentAlerts: Alert[];
  dailyReadings: DailyReading[];
  hourlyReadings: Reading[];
  zones: Zone[];
  onNavigate: (tab: NavTab) => void;
  onResolveAlert: (alertId: number) => void;
}

export const Overview: React.FC<OverviewProps> = ({
  summary,
  budgets,
  savings,
  tips,
  recentAlerts,
  dailyReadings,
  hourlyReadings,
  zones,
  onNavigate,
  onResolveAlert,
}) => {
  const [trendView, setTrendView] = useState<"daily" | "hourly">("daily");

  // Chart data formatting
  const dailyChartData = React.useMemo(() => {
    // Group daily readings by date
    const dateMap = new Map<string, number>();
    dailyReadings.forEach((r) => {
      const current = dateMap.get(r.date) || 0;
      dateMap.set(r.date, Math.round((current + r.litres) * 100) / 100);
    });
    return Array.from(dateMap.entries())
      .map(([date, litres]) => ({
        date: date.slice(5), // MM-DD
        fullDate: date,
        litres,
      }))
      .slice(-14); // Recent 14 days
  }, [dailyReadings]);

  const hourlyChartData = React.useMemo(() => {
    // Group hourly readings by timestamp
    const timeMap = new Map<string, number>();
    hourlyReadings.slice(-48).forEach((r) => {
      const timeStr = r.timestamp.slice(11, 16); // HH:MM
      const current = timeMap.get(timeStr) || 0;
      timeMap.set(timeStr, Math.round((current + r.litres) * 100) / 100);
    });
    return hourlyReadings.slice(-24).map((r) => ({
      time: r.timestamp.slice(11, 16),
      litres: Math.round(r.litres * 10) / 10,
    }));
  }, [hourlyReadings]);

  // Zone budget comparison chart data
  const zoneBarData = React.useMemo(() => {
    if (!budgets?.zones) return [];
    return budgets.zones.map((zb) => ({
      name: zb.zone_name,
      actual: zb.actual_consumption_litres,
      budget: zb.daily_budget_litres,
      percent: zb.consumed_percent,
    }));
  }, [budgets]);

  const changeIsPositive = (summary?.change_percent || 0) > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* 1. TOP KPI CARDS */}
      <div className="kpi-grid">
        {/* KPI 1: Today Usage */}
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Today's Consumption</span>
            <div className="kpi-icon-wrap">
              <Droplet size={20} />
            </div>
          </div>
          <div className="kpi-value">
            {summary ? summary.today_usage_litres.toLocaleString() : "—"}
            <span style={{ fontSize: "1rem", fontWeight: 500, color: "var(--text-muted)", marginLeft: "4px" }}>L</span>
          </div>
          <div className="kpi-footer">
            {summary?.yesterday_usage_litres !== undefined && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "2px",
                  fontWeight: 600,
                  color: changeIsPositive ? "var(--color-danger)" : "var(--color-success)",
                }}
              >
                {changeIsPositive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                {Math.abs(summary.change_percent)}%
              </span>
            )}
            <span>vs yesterday ({summary?.yesterday_usage_litres.toLocaleString()} L)</span>
          </div>
        </div>

        {/* KPI 2: Water Budget Utilization */}
        <div className="kpi-card" style={{ "--accent-cyan": "var(--accent-cyan)" } as any}>
          <div className="kpi-header">
            <span className="kpi-label">Daily Budget Utilization</span>
            <div className="kpi-icon-wrap" style={{ background: "rgba(16, 185, 129, 0.1)", color: "#34d399" }}>
              <Layers size={20} />
            </div>
          </div>
          <div className="kpi-value">
            {budgets ? `${budgets.overall_consumed_percent}%` : "—"}
          </div>
          <div className="kpi-footer">
            <span className={`badge ${budgets?.overall_status ? `badge-${budgets.overall_status}` : "badge-neutral"}`}>
              {budgets?.overall_status || "Evaluating"}
            </span>
            <span>
              {budgets ? `${budgets.total_actual_litres.toLocaleString()} / ${budgets.total_budget_litres.toLocaleString()} L` : "Loading..."}
            </span>
          </div>
        </div>

        {/* KPI 3: Active Alerts */}
        <div className="kpi-card" style={{ "--accent-cyan": "var(--color-danger)" } as any}>
          <div className="kpi-header">
            <span className="kpi-label">Active Anomaly Alerts</span>
            <div className="kpi-icon-wrap" style={{ background: "rgba(244, 63, 94, 0.1)", color: "#fb7185" }}>
              <AlertTriangle size={20} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: (summary?.active_alerts || 0) > 0 ? "#fb7185" : "var(--text-main)" }}>
            {summary?.active_alerts ?? "0"}
          </div>
          <div className="kpi-footer">
            <button
              onClick={() => onNavigate("alerts")}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--accent-cyan)",
                cursor: "pointer",
                padding: 0,
                fontSize: "0.8125rem",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                fontWeight: 600,
              }}
            >
              Inspect active events <ExternalLink size={12} />
            </button>
          </div>
        </div>

        {/* KPI 4: Monthly Potential Savings */}
        <div className="kpi-card" style={{ "--accent-cyan": "var(--color-warning)" } as any}>
          <div className="kpi-header">
            <span className="kpi-label">Est. Monthly Leak Savings</span>
            <div className="kpi-icon-wrap" style={{ background: "rgba(245, 158, 11, 0.1)", color: "#fbbf24" }}>
              <DollarSign size={20} />
            </div>
          </div>
          <div className="kpi-value" style={{ color: "#fbbf24" }}>
            ${savings?.total_monthly_savings ? savings.total_monthly_savings.toFixed(2) : "0.00"}
          </div>
          <div className="kpi-footer">
            <span>
              {savings?.actionable_leaks_count || 0} active leaks ({savings?.total_daily_wasted_litres.toFixed(0) || 0} L/day)
            </span>
          </div>
        </div>
      </div>

      {/* 2. CHARTS SECTION (2 COLUMNS) */}
      <div className="grid-2">
        {/* Trend Area Chart */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="section-title">
                <Droplet size={18} color="var(--accent-cyan)" />
                Water Consumption Telemetry
              </h2>
              <p className="page-subtitle">Real-time aggregate consumption curve</p>
            </div>
            <div style={{ display: "flex", gap: "6px" }}>
              <button
                onClick={() => setTrendView("daily")}
                className={`btn btn-sm ${trendView === "daily" ? "btn-primary" : "btn-secondary"}`}
              >
                14 Days
              </button>
              <button
                onClick={() => setTrendView("hourly")}
                className={`btn btn-sm ${trendView === "hourly" ? "btn-primary" : "btn-secondary"}`}
              >
                Hourly
              </button>
            </div>
          </div>

          <div className="chart-container" style={{ height: "280px", width: "100%", minWidth: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              {trendView === "daily" ? (
                <AreaChart data={dailyChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `${v / 1000}kL`} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0a1329",
                      borderColor: "rgba(6, 182, 212, 0.3)",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                    formatter={(val: any) => [`${Number(val).toLocaleString()} Litres`, "Total Usage"]}
                    labelFormatter={(lbl) => `Date: ${lbl}`}
                  />
                  <Area type="monotone" dataKey="litres" stroke="#00f2fe" strokeWidth={2.5} fillOpacity={1} fill="url(#cyanGrad)" />
                </AreaChart>
              ) : (
                <AreaChart data={hourlyChartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="hourlyGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickLine={false} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `${v}L`} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0a1329",
                      borderColor: "rgba(56, 189, 248, 0.3)",
                      borderRadius: "8px",
                      color: "#f8fafc",
                    }}
                    formatter={(val: any) => [`${Number(val).toFixed(1)} Litres`, "Hourly Flow"]}
                  />
                  <Area type="monotone" dataKey="litres" stroke="#38bdf8" strokeWidth={2} fillOpacity={1} fill="url(#hourlyGrad)" />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>

        {/* Zone Budget Comparison Bar Chart */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="section-title">
                <Layers size={18} color="var(--accent-cyan)" />
                Zone Consumption vs Budget
              </h2>
              <p className="page-subtitle">Actual consumption compared to configured daily limit</p>
            </div>
            <button onClick={() => onNavigate("zones")} className="btn btn-outline btn-sm">
              All Zones
            </button>
          </div>

          <div className="chart-container" style={{ height: "280px", width: "100%", minWidth: 0 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={zoneBarData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `${v / 1000}k`} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0a1329",
                    borderColor: "rgba(6, 182, 212, 0.3)",
                    borderRadius: "8px",
                    color: "#f8fafc",
                  }}
                  formatter={(val: any, name: any) => [
                    `${Number(val).toLocaleString()} Litres`,
                    name === "actual" ? "Actual Usage" : "Daily Budget",
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: "0.75rem", paddingTop: "8px" }} />
                <Bar dataKey="actual" name="Actual Usage" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                <Bar dataKey="budget" name="Daily Budget" fill="#1e293b" stroke="#334155" strokeWidth={1} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 3. ZONE BUDGET STATUS & RECENT ALERTS (2 COLUMNS) */}
      <div className="grid-2">
        {/* Zone Budget List */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="section-title">
                <Layers size={18} color="var(--accent-cyan)" />
                Zone Budget Status
              </h2>
              <p className="page-subtitle">Real-time tracking of water allowances</p>
            </div>
            <span className="badge badge-info">{budgets?.zones?.length || 0} Zones</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {budgets?.zones?.map((zb) => (
              <div key={zb.zone_id} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "6px", fontSize: "0.875rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
                    <span style={{ fontWeight: 600 }}>{zb.zone_name}</span>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>({zb.zone_type})</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600 }}>{zb.actual_consumption_litres.toLocaleString()} L</span>
                    <span style={{ color: "var(--text-dim)", fontSize: "0.8125rem" }}>/ {zb.daily_budget_litres.toLocaleString()} L</span>
                    <span className={`badge badge-${zb.status}`}>{zb.status}</span>
                  </div>
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
            ))}
          </div>
        </div>

        {/* Recent Alerts List */}
        <div className="card">
          <div className="card-header">
            <div>
              <h2 className="section-title">
                <AlertTriangle size={18} color="var(--color-danger)" />
                Recent Detected Alerts
              </h2>
              <p className="page-subtitle">Immediate anomalies flagged by detector algorithms</p>
            </div>
            <button onClick={() => onNavigate("alerts")} className="btn btn-outline btn-sm">
              View All ({recentAlerts.length})
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {recentAlerts.length === 0 ? (
              <div style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)" }}>
                <CheckCircle2 size={32} color="var(--color-success)" style={{ margin: "0 auto 8px" }} />
                <p style={{ fontWeight: 600 }}>No unresolved alerts present</p>
                <p style={{ fontSize: "0.8125rem", color: "var(--text-dim)" }}>All zones operating within normal parameters.</p>
              </div>
            ) : (
              recentAlerts.slice(0, 4).map((alert) => {
                const zone = zones.find((z) => z.id === alert.zone_id);
                return (
                  <div
                    key={alert.id}
                    style={{
                      padding: "12px 14px",
                      background: "rgba(10, 20, 44, 0.6)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-md)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                      gap: "10px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0, flex: 1 }}>
                      <span className={`badge badge-${alert.severity === "high" ? "danger" : alert.severity === "medium" ? "warning" : "info"}`} style={{ flexShrink: 0 }}>
                        {alert.severity}
                      </span>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: "0.8125rem", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {zone?.name || `Zone ${alert.zone_id}`} •{" "}
                          <span style={{ textTransform: "capitalize", color: "var(--accent-cyan)" }}>
                            {alert.alert_type.replace("_", " ")}
                          </span>
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-dim)" }}>
                          {new Date(alert.timestamp).toLocaleString()}
                        </div>
                      </div>
                    </div>

                    {!alert.resolved && (
                      <button
                        onClick={() => onResolveAlert(alert.id)}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: "0.75rem", padding: "4px 10px", flexShrink: 0 }}
                      >
                        Resolve
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 4. CONSERVATION RECOMMENDATIONS PREVIEW */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="section-title">
              <Sparkles size={18} color="var(--accent-cyan)" />
              Conservation Intelligence Preview
            </h2>
            <p className="page-subtitle">Data-driven recommendations to curtail waste and reduce utility expenditures</p>
          </div>
          <button onClick={() => onNavigate("conservation")} className="btn btn-outline btn-sm">
            View All Tips
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
          {tips?.recommendations.slice(0, 3).map((rec) => (
            <div
              key={rec.id}
              style={{
                padding: "16px",
                background: "rgba(10, 20, 44, 0.6)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span className={`badge ${rec.priority === "critical" || rec.priority === "high" ? "badge-danger" : rec.priority === "medium" ? "badge-warning" : "badge-info"}`}>
                  {rec.priority} Priority
                </span>
                {rec.zone_name && <span style={{ fontSize: "0.75rem", color: "var(--accent-cyan)" }}>{rec.zone_name}</span>}
              </div>
              <h3 style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-main)" }}>{rec.title}</h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", lineHeight: 1.4 }}>{rec.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
