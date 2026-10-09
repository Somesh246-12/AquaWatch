import React from "react";
import {
  AlertTriangle,
  BrainCircuit,
  Droplets,
  Layers,
  LayoutDashboard,
  Leaf,
  Radio,
  X,
} from "lucide-react";

export type NavTab = "overview" | "zones" | "alerts" | "conservation" | "detection" | "demo";

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  unresolvedAlertCount: number;
  isBackendConnected: boolean;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  unresolvedAlertCount,
  isBackendConnected,
  isOpenMobile,
  onCloseMobile,
}) => {
  const navItems = [
    {
      id: "overview" as NavTab,
      label: "Overview",
      icon: LayoutDashboard,
      badge: null,
    },
    {
      id: "zones" as NavTab,
      label: "Water Zones",
      icon: Layers,
      badge: "5 Zones",
    },
    {
      id: "alerts" as NavTab,
      label: "Alerts & Leaks",
      icon: AlertTriangle,
      badge: unresolvedAlertCount > 0 ? String(unresolvedAlertCount) : null,
      badgeColor: unresolvedAlertCount > 0 ? "badge-danger" : undefined,
    },
    {
      id: "conservation" as NavTab,
      label: "Conservation",
      icon: Leaf,
      badge: "Smart Tips",
    },
    {
      id: "detection" as NavTab,
      label: "Detection Engine",
      icon: BrainCircuit,
      badge: "3 Models",
    },
    {
      id: "demo" as NavTab,
      label: "Live Demo",
      icon: Radio,
      badge: "LIVE",
      badgeColor: "badge-normal",
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 35,
          }}
        />
      )}

      <aside className={`sidebar ${isOpenMobile ? "open" : ""}`}>
        {/* Brand Header */}
        <div
          style={{
            padding: "24px 20px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, #00f2fe 0%, #06b6d4 50%, #0284c7 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 20px rgba(6, 182, 212, 0.4)",
              }}
            >
              <Droplets size={22} color="#050c1e" strokeWidth={2.5} />
            </div>
            <div>
              <div
                style={{
                  fontWeight: 800,
                  fontSize: "1.125rem",
                  letterSpacing: "-0.02em",
                  color: "#ffffff",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                AquaWatch
              </div>
              <div
                style={{
                  fontSize: "0.6875rem",
                  color: "var(--accent-cyan)",
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                }}
              >
                Water Intelligence
              </div>
            </div>
          </div>

          {isOpenMobile && (
            <button
              onClick={onCloseMobile}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
              }}
            >
              <X size={20} />
            </button>
          )}
        </div>

        {/* Navigation list */}
        <div style={{ padding: "20px 12px", flex: 1, display: "flex", flexDirection: "column", gap: "6px" }}>
          <div
            style={{
              padding: "0 12px 8px 12px",
              fontSize: "0.6875rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-dim)",
            }}
          >
            Monitoring Platform
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onCloseMobile();
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "var(--radius-md)",
                  border: isActive ? "1px solid rgba(6, 182, 212, 0.3)" : "1px solid transparent",
                  background: isActive ? "rgba(6, 182, 212, 0.12)" : "transparent",
                  color: isActive ? "var(--accent-cyan-light)" : "var(--text-muted)",
                  fontWeight: isActive ? 600 : 500,
                  fontSize: "0.875rem",
                  cursor: "pointer",
                  transition: "var(--transition)",
                  textAlign: "left",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <Icon size={18} color={isActive ? "var(--accent-cyan)" : "currentColor"} />
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span
                    className={`badge ${item.badgeColor || (isActive ? "badge-info" : "badge-neutral")}`}
                    style={{ fontSize: "0.6875rem", padding: "1px 7px" }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Sidebar Footer Status */}
        <div
          style={{
            padding: "16px 20px",
            borderTop: "1px solid var(--border-subtle)",
            background: "rgba(6, 11, 23, 0.5)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.8125rem" }}>
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor: isBackendConnected ? "var(--color-success)" : "var(--color-danger)",
                  boxShadow: isBackendConnected
                    ? "0 0 8px rgba(16, 185, 129, 0.8)"
                    : "0 0 8px rgba(244, 63, 94, 0.8)",
                }}
              />
              <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>
                {isBackendConnected ? "API Connected" : "Connecting..."}
              </span>
            </div>
            <span style={{ fontSize: "0.6875rem", color: "var(--text-dim)", fontWeight: 600 }}>v0.1.0</span>
          </div>

          <div style={{ fontSize: "0.6875rem", color: "var(--text-dim)" }}>
            Autonomous Anomaly & Conservation System
          </div>
        </div>
      </aside>
    </>
  );
};
