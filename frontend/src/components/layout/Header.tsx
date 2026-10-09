import React from "react";
import { Menu, RefreshCw } from "lucide-react";
import type { NavTab } from "./Sidebar";

interface HeaderProps {
  currentTab: NavTab;
  onOpenMobile: () => void;
  onRefresh: () => void;
  isLoading: boolean;
  selectedDate: string;
  onSelectDate: (date: string) => void;
  isBackendConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onOpenMobile,
  onRefresh,
  isLoading,
  selectedDate,
  onSelectDate,
  isBackendConnected,
}) => {
  const titles: Record<NavTab, { title: string; subtitle: string }> = {
    overview: {
      title: "Environmental Intelligence Overview",
      subtitle: "Multi-zone consumption telemetry, active anomalies, and live conservation tracking",
    },
    zones: {
      title: "Monitored Water Zones",
      subtitle: "Daily allocation budgets, utilization rates, and spatial distribution",
    },
    alerts: {
      title: "Anomaly & Leak Operations",
      subtitle: "Rule-based night flows, statistical surges, and ML-flagged multivariate outliers",
    },
    conservation: {
      title: "Conservation Intelligence & Savings",
      subtitle: "Actionable water-saving recommendations and volumetric loss monetary projections",
    },
    detection: {
      title: "Detection Engine & ML Benchmarks",
      subtitle: "Comparative evaluation of Rule-Based, Z-Score, and Isolation Forest algorithms vs Ground Truth",
    },
    demo: {
      title: "Live Demonstration Sandbox",
      subtitle: "Simulated leak injection, automated detector triggering, and live operational resolution",
    },
  };

  const { title, subtitle } = titles[currentTab];

  return (
    <header className="top-header">
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <button
          onClick={onOpenMobile}
          className="btn btn-secondary btn-sm"
          style={{ display: "none" }}
          id="mobile-nav-toggle"
          aria-label="Toggle navigation"
        >
          <Menu size={18} />
        </button>

        <div>
          <h1 className="page-title">{title}</h1>
          <p className="page-subtitle">{subtitle}</p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        {/* Date Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <label style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, textTransform: "uppercase" }}>
            Date:
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => onSelectDate(e.target.value)}
            className="input"
            style={{ padding: "5px 10px", fontSize: "0.8125rem", cursor: "pointer" }}
          />
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="btn btn-secondary btn-sm"
          title="Refresh telemetry and models"
        >
          <RefreshCw
            size={14}
            style={{
              animation: isLoading ? "spin 1s linear infinite" : "none",
            }}
          />
          <span>{isLoading ? "Syncing..." : "Refresh"}</span>
        </button>

        {/* Connection status badge */}
        <div
          className={`badge ${isBackendConnected ? "badge-normal" : "badge-danger"}`}
          style={{ padding: "4px 10px", fontSize: "0.75rem" }}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: "currentColor",
            }}
          />
          {isBackendConnected ? "Telemetry Live" : "Offline"}
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @media (max-width: 1024px) {
          #mobile-nav-toggle {
            display: inline-flex !important;
          }
        }
      `}</style>
    </header>
  );
};
