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
      <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0, flex: 1 }}>
        <button
          onClick={onOpenMobile}
          className="btn btn-secondary btn-sm"
          style={{ display: "none", flexShrink: 0 }}
          id="mobile-nav-toggle"
          aria-label="Toggle navigation"
        >
          <Menu size={18} />
        </button>

        <div style={{ minWidth: 0 }}>
          <h1 className="page-title" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {title}
          </h1>
          <p className="page-subtitle">{subtitle}</p>
        </div>
      </div>

      <div className="header-actions" style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
        {/* Date Selector (hidden on small mobile screens to prevent header overflow) */}
        <div className="header-date-wrap" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label style={{ fontSize: "0.75rem", color: "var(--text-dim)", fontWeight: 600, textTransform: "uppercase" }}>
            Date:
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => onSelectDate(e.target.value)}
            className="input"
            style={{ padding: "4px 8px", fontSize: "0.8125rem", cursor: "pointer", maxWidth: "135px" }}
          />
        </div>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="btn btn-secondary btn-sm"
          title="Refresh telemetry and models"
          style={{ padding: "5px 10px", gap: "6px" }}
        >
          <RefreshCw
            size={14}
            style={{
              animation: isLoading ? "spin 1s linear infinite" : "none",
            }}
          />
          <span className="btn-text-responsive">{isLoading ? "Syncing..." : "Refresh"}</span>
        </button>

        {/* Connection status badge */}
        <div
          className={`badge ${isBackendConnected ? "badge-normal" : "badge-danger"}`}
          style={{ padding: "4px 8px", fontSize: "0.75rem" }}
          title={isBackendConnected ? "Connected to live FastAPI backend" : "Disconnected from backend"}
        >
          <span
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: "currentColor",
              flexShrink: 0,
            }}
          />
          <span className="badge-text-full">{isBackendConnected ? "Telemetry Live" : "Offline"}</span>
          <span className="badge-text-short">{isBackendConnected ? "Live" : "Off"}</span>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .badge-text-short {
          display: none;
        }
        @media (max-width: 1024px) {
          #mobile-nav-toggle {
            display: inline-flex !important;
          }
        }
        @media (max-width: 640px) {
          .header-date-wrap {
            display: none !important;
          }
          .btn-text-responsive {
            display: none;
          }
          .badge-text-full {
            display: none;
          }
          .badge-text-short {
            display: inline;
          }
        }
      `}</style>
    </header>
  );
};
