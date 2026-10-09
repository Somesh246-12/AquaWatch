import React, { useEffect, useState, useCallback } from "react";
import { Header } from "./components/layout/Header";
import { Sidebar, type NavTab } from "./components/layout/Sidebar";
import { Overview } from "./pages/Overview";
import { Zones } from "./pages/Zones";
import { Alerts } from "./pages/Alerts";
import { Conservation } from "./pages/Conservation";
import { Detection } from "./pages/Detection";
import { Demo } from "./pages/Demo";
import { api } from "./api/client";
import type {
  Alert,
  ConservationBudgetsResponse,
  ConservationSavingsResponse,
  ConservationTipsResponse,
  DailyReading,
  DashboardSummary,
  DetectionRunResponse,
  HealthResponse,
  Reading,
  Zone,
} from "./types/api";
import { AlertCircle, RefreshCw } from "lucide-react";

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>("overview");
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);

  // Core Data States
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [budgets, setBudgets] = useState<ConservationBudgetsResponse | null>(null);
  const [savings, setSavings] = useState<ConservationSavingsResponse | null>(null);
  const [tips, setTips] = useState<ConservationTipsResponse | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [dailyReadings, setDailyReadings] = useState<DailyReading[]>([]);
  const [hourlyReadings, setHourlyReadings] = useState<Reading[]>([]);
  const [lastDetectionResult, setLastDetectionResult] = useState<DetectionRunResponse | null>(null);

  // Parameter states
  const [selectedDate, setSelectedDate] = useState<string>("2026-10-08");
  const [tariff, setTariff] = useState<number>(2.5);
  const [hoursPerDay, setHoursPerDay] = useState<number>(24);

  // Status & loading
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isResolving, setIsResolving] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch all core system data
  const loadData = useCallback(async (isInitial = false) => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // 1. Health check
      try {
        const healthRes = await api.getHealth();
        setHealth(healthRes);
      } catch {
        setHealth(null);
      }

      // 2. Parallel Core Queries
      const [
        zonesData,
        summaryData,
        alertsData,
        budgetsData,
        tipsData,
        savingsData,
        dailyData,
        hourlyData,
      ] = await Promise.all([
        api.getZones().catch(() => []),
        api.getSummary().catch(() => null),
        api.getAlerts({ limit: 100 }).catch(() => []),
        api.getConservationBudgets(selectedDate).catch(() => null),
        api.getConservationTips(selectedDate).catch(() => null),
        api.getConservationSavings({ tariff_per_kl: tariff, hours_per_day: hoursPerDay }).catch(() => null),
        api.getReadingsDaily({ limit: 300 }).catch(() => []),
        api.getReadingsHourly({ limit: 100 }).catch(() => []),
      ]);

      setZones(zonesData);
      setSummary(summaryData);
      setAlerts(alertsData);
      setBudgets(budgetsData);
      setTips(tipsData);
      setSavings(savingsData);
      setDailyReadings(dailyData);
      setHourlyReadings(hourlyData);

      // If initial load and budget returned a date, sync with it
      if (isInitial && budgetsData?.date) {
        setSelectedDate(budgetsData.date);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load system telemetry from AquaWatch backend.");
    } finally {
      setIsLoading(false);
    }
  }, [selectedDate, tariff, hoursPerDay]);

  useEffect(() => {
    loadData(true);
  }, [selectedDate, tariff, hoursPerDay]);

  // Alert resolution mutation
  const handleResolveAlert = async (alertId: number) => {
    setIsResolving(true);
    try {
      const updated = await api.resolveAlert(alertId);
      // Update alerts list with returned updated alert
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? updated : a))
      );
      // Refresh summary KPIs and savings
      const [newSummary, newSavings, newTips] = await Promise.all([
        api.getSummary().catch(() => null),
        api.getConservationSavings({ tariff_per_kl: tariff, hours_per_day: hoursPerDay }).catch(() => null),
        api.getConservationTips(selectedDate).catch(() => null),
      ]);
      if (newSummary) setSummary(newSummary);
      if (newSavings) setSavings(newSavings);
      if (newTips) setTips(newTips);
    } catch (err: any) {
      alert(`Could not resolve alert #${alertId}: ${err.message}`);
    } finally {
      setIsResolving(false);
    }
  };

  // Run detection pipeline
  const handleRunDetection = async (contaminationRate: number) => {
    const res = await api.runDetection(contaminationRate);
    setLastDetectionResult(res);
    // Refresh alerts, summary, savings
    const [alertsData, summaryData, savingsData, tipsData] = await Promise.all([
      api.getAlerts({ limit: 100 }),
      api.getSummary(),
      api.getConservationSavings({ tariff_per_kl: tariff, hours_per_day: hoursPerDay }),
      api.getConservationTips(selectedDate),
    ]);
    setAlerts(alertsData);
    setSummary(summaryData);
    setSavings(savingsData);
    setTips(tipsData);
    return res;
  };

  const unresolvedAlertCount = alerts.filter((a) => !a.resolved).length;
  const isBackendConnected = health?.status === "ok" || health?.database === "connected";

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        unresolvedAlertCount={unresolvedAlertCount}
        isBackendConnected={isBackendConnected}
        isOpenMobile={isMobileNavOpen}
        onCloseMobile={() => setIsMobileNavOpen(false)}
      />

      {/* Main Content Area */}
      <div className="main-content">
        <Header
          currentTab={currentTab}
          onOpenMobile={() => setIsMobileNavOpen(true)}
          onRefresh={() => loadData(false)}
          isLoading={isLoading}
          selectedDate={selectedDate}
          onSelectDate={setSelectedDate}
          isBackendConnected={isBackendConnected}
        />

        <main className="page-body">
          {/* Error Banner */}
          {errorMessage && (
            <div
              style={{
                marginBottom: "20px",
                padding: "16px 20px",
                background: "rgba(244, 63, 94, 0.12)",
                border: "1px solid rgba(244, 63, 94, 0.3)",
                borderRadius: "var(--radius-md)",
                color: "#fb7185",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.875rem" }}>
                <AlertCircle size={20} />
                <span>{errorMessage}</span>
              </div>
              <button onClick={() => loadData(false)} className="btn btn-secondary btn-sm">
                <RefreshCw size={14} /> Retry
              </button>
            </div>
          )}

          {/* Active Tab View */}
          {currentTab === "overview" && (
            <Overview
              summary={summary}
              budgets={budgets}
              savings={savings}
              tips={tips}
              recentAlerts={alerts.filter((a) => !a.resolved)}
              dailyReadings={dailyReadings}
              hourlyReadings={hourlyReadings}
              zones={zones}
              onNavigate={setCurrentTab}
              onResolveAlert={handleResolveAlert}
            />
          )}

          {currentTab === "zones" && (
            <Zones
              zones={zones}
              budgets={budgets}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
              hourlyReadings={hourlyReadings}
              alerts={alerts}
            />
          )}

          {currentTab === "alerts" && (
            <Alerts
              alerts={alerts}
              zones={zones}
              onResolveAlert={handleResolveAlert}
              onRunDetection={handleRunDetection}
              isResolving={isResolving}
              onRefresh={() => loadData(false)}
            />
          )}

          {currentTab === "conservation" && (
            <Conservation
              budgets={budgets}
              tips={tips}
              savings={savings}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
              tariff={tariff}
              hoursPerDay={hoursPerDay}
              onUpdateTariff={setTariff}
              onUpdateHoursPerDay={setHoursPerDay}
            />
          )}

          {currentTab === "detection" && (
            <Detection
              lastRunResult={lastDetectionResult}
              onRunDetection={handleRunDetection}
              isRunning={isLoading}
            />
          )}

          {currentTab === "demo" && (
            <Demo
              zones={zones}
              summary={summary}
              budgets={budgets}
              savings={savings}
              alerts={alerts}
              onRefreshAll={() => loadData(false)}
              onResolveAlert={handleResolveAlert}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
