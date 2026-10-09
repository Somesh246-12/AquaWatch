/**
 * AquaWatch Centralized API Client
 * Interfaces with the FastAPI backend.
 */

import type {
  Alert,
  AlertSeverity,
  AlertType,
  ConservationBudgetsResponse,
  ConservationSavingsResponse,
  ConservationTipsResponse,
  DailyReading,
  DashboardSummary,
  DemoInjectRequest,
  DemoInjectResponse,
  DemoResetResponse,
  DemoSessionStatus,
  DetectionRunResponse,
  HealthResponse,
  Reading,
  Zone,
} from "../types/api";

const resolveBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) {
    return envUrl.replace(/\/+$/, "");
  }
  if (import.meta.env.PROD) {
    console.error(
      "[AquaWatch] Configuration Warning: VITE_API_BASE_URL is not set in production. " +
      "Please set VITE_API_BASE_URL in your Vercel project environment variables to your deployed backend URL."
    );
    return "";
  }
  return "http://127.0.0.1:8000";
};

const API_BASE_URL = resolveBaseUrl();

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorData: any = null;
      try {
        errorData = await response.json();
      } catch {
        // Response was not JSON
      }

      const detail = errorData?.detail || `HTTP ${response.status}: ${response.statusText}`;
      throw new ApiError(response.status, typeof detail === "string" ? detail : JSON.stringify(detail), errorData);
    }

    return (await response.json()) as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(0, `Cannot connect to AquaWatch backend at ${API_BASE_URL}. Ensure the FastAPI server is running. (${err.message})`);
  }
}

export const api = {
  // System Health
  getHealth: () => request<HealthResponse>("/health"),

  // Zones
  getZones: () => request<Zone[]>("/zones"),
  getZone: (zoneId: number) => request<Zone>(`/zones/${zoneId}`),

  // Readings
  getReadingsHourly: (params?: {
    zone_id?: number;
    start?: string;
    end?: string;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    search.set("aggregation", "hourly");
    if (params?.zone_id) search.set("zone_id", String(params.zone_id));
    if (params?.start) search.set("start", params.start);
    if (params?.end) search.set("end", params.end);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.offset) search.set("offset", String(params.offset));
    return request<Reading[]>(`/readings?${search.toString()}`);
  },

  getReadingsDaily: (params?: {
    zone_id?: number;
    start?: string;
    end?: string;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    search.set("aggregation", "daily");
    if (params?.zone_id) search.set("zone_id", String(params.zone_id));
    if (params?.start) search.set("start", params.start);
    if (params?.end) search.set("end", params.end);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.offset) search.set("offset", String(params.offset));
    return request<DailyReading[]>(`/readings?${search.toString()}`);
  },

  // Ingest reading
  createReading: (reading: { zone_id: number; timestamp: string; litres: number }) =>
    request<Reading>("/readings", {
      method: "POST",
      body: JSON.stringify(reading),
    }),

  // Summary
  getSummary: () => request<DashboardSummary>("/summary"),

  // Alerts
  getAlerts: (params?: {
    zone_id?: number;
    severity?: AlertSeverity;
    resolved?: boolean;
    alert_type?: AlertType;
    limit?: number;
    offset?: number;
  }) => {
    const search = new URLSearchParams();
    if (params?.zone_id) search.set("zone_id", String(params.zone_id));
    if (params?.severity) search.set("severity", params.severity);
    if (params?.resolved !== undefined) search.set("resolved", String(params.resolved));
    if (params?.alert_type) search.set("alert_type", params.alert_type);
    if (params?.limit) search.set("limit", String(params.limit));
    if (params?.offset) search.set("offset", String(params.offset));
    const query = search.toString();
    return request<Alert[]>(`/alerts${query ? `?${query}` : ""}`);
  },

  getAlert: (alertId: number) => request<Alert>(`/alerts/${alertId}`),

  resolveAlert: (alertId: number) =>
    request<Alert>(`/alerts/${alertId}/resolve`, {
      method: "PATCH",
    }),

  // Detection Pipeline
  runDetection: (contamination = 0.02) =>
    request<DetectionRunResponse>(`/detection/run?contamination=${contamination}`, {
      method: "POST",
    }),

  // Conservation Intelligence
  getConservationBudgets: (date?: string) => {
    const query = date ? `?date=${encodeURIComponent(date)}` : "";
    return request<ConservationBudgetsResponse>(`/conservation/budgets${query}`);
  },

  getConservationTips: (date?: string) => {
    const query = date ? `?date=${encodeURIComponent(date)}` : "";
    return request<ConservationTipsResponse>(`/conservation/tips${query}`);
  },

  getConservationSavings: (params?: {
    tariff_per_kl?: number;
    hours_per_day?: number;
    zone_id?: number;
  }) => {
    const search = new URLSearchParams();
    if (params?.tariff_per_kl !== undefined) search.set("tariff_per_kl", String(params.tariff_per_kl));
    if (params?.hours_per_day !== undefined) search.set("hours_per_day", String(params.hours_per_day));
    if (params?.zone_id !== undefined) search.set("zone_id", String(params.zone_id));
    const query = search.toString();
    return request<ConservationSavingsResponse>(`/conservation/savings${query ? `?${query}` : ""}`);
  },

  // Interactive Live Demo & Leak Injection
  getDemoStatus: (sessionId?: string) => {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    return request<DemoSessionStatus>(`/demo/status${query}`);
  },

  startDemo: (sessionId?: string) => {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    return request<DemoSessionStatus>(`/demo/start${query}`, { method: "POST" });
  },

  injectDemoLeak: (payload: DemoInjectRequest) =>
    request<DemoInjectResponse>("/demo/inject", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  resetDemo: (sessionId?: string) => {
    const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    return request<DemoResetResponse>(`/demo/reset${query}`, { method: "POST" });
  },
};
