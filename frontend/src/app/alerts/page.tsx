"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import {
  IconAlertOctagon,
  IconRefresh,
  IconSearch,
  IconFilter,
  IconArrowRight,
  IconCheck,
  IconBuildingHospital,
  IconClockHour4,
  IconTrendingUp,
  IconHelpCircle,
  IconChevronDown,
  IconChevronUp,
  IconInfoCircle,
} from "@tabler/icons-react";

interface RiskEvidence {
  current_stock: number;
  unit: string;
  safety_stock: number;
  incoming_quantity: number;
  estimated_daily_demand: number;
  days_of_cover: number;
  projected_stockout_date: string | null;
  risk_threshold: string;
  risk_level: string;
  forecast_method: string;
}

interface RiskExplanation {
  entity_type: string;
  entity_id: number;
  code: string;
  facility_id: number;
  facility_name: string;
  resource_id: string;
  resource_name: string;
  severity: string;
  evidence: RiskEvidence;
  why: string;
  recommended_action: string;
}

interface AlertItem {
  id: number;
  alert_code: string;
  facility_id: number;
  resource_id: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  alert_type: string;
  title: string;
  projected_impact_date: string | null;
  status: "ACTIVE" | "RESOLVED" | "ACKNOWLEDGED" | "ESCALATED" | "MONITORED";
  created_at: string;
  facility_name?: string;
  item_name?: string;
  explanation?: RiskExplanation;
  notification_lifecycle?: {
    notification_created_at: string;
    is_escalated: boolean;
    escalated_at: string | null;
    escalation_reason: string | null;
    is_acknowledged: boolean;
    acknowledged_at: string | null;
    acknowledged_by_name: string | null;
  };
}

export default function AlertsPage() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [facilities, setFacilities] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ackLoadingId, setAckLoadingId] = useState<number | null>(null);
  const [ackMessage, setAckMessage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ACTIVE");
  const [expandedAlerts, setExpandedAlerts] = useState<Record<number, boolean>>({});

  const toggleExpand = (id: number) => {
    setExpandedAlerts((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleAcknowledgeAlert = async (alertId: number) => {
    try {
      setAckLoadingId(alertId);
      setAckMessage(null);
      await apiFetch(`/api/v1/alerts/${alertId}/acknowledge`, {
        method: "POST",
        body: JSON.stringify({ reason: "Officer on-duty acknowledgement" }),
      });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: "ACKNOWLEDGED" } : a))
      );
      setAckMessage(`Alert #${alertId} successfully acknowledged.`);
      setTimeout(() => setAckMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to acknowledge alert");
    } finally {
      setAckLoadingId(null);
    }
  };

  const handleMonitorAlert = async (alertId: number) => {
    try {
      setAckLoadingId(alertId);
      setAckMessage(null);
      await apiFetch(`/api/v1/alerts/${alertId}/monitor`, {
        method: "POST",
        body: JSON.stringify({ reason: "Alert placed under active clinical monitoring" }),
      });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: "MONITORED" } : a))
      );
      setAckMessage(`Alert #${alertId} placed under active monitoring.`);
      setTimeout(() => setAckMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to place alert under monitoring");
    } finally {
      setAckLoadingId(null);
    }
  };

  const handleResolveAlert = async (alertId: number) => {
    try {
      setAckLoadingId(alertId);
      setAckMessage(null);
      await apiFetch(`/api/v1/alerts/${alertId}/resolve`, {
        method: "POST",
        body: JSON.stringify({ reason: "Inventory restored to safe operational buffer" }),
      });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: "RESOLVED" } : a))
      );
      setAckMessage(`Alert #${alertId} successfully marked as RESOLVED.`);
      setTimeout(() => setAckMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to resolve alert");
    } finally {
      setAckLoadingId(null);
    }
  };

  const handleEscalateAlert = async (alertId: number) => {
    try {
      setAckLoadingId(alertId);
      setAckMessage(null);
      await apiFetch(`/api/v1/alerts/${alertId}/escalate`, {
        method: "POST",
        body: JSON.stringify({ reason: "Operator escalated risk to CDMO for supervisory review and redistribution" }),
      });
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, status: "ESCALATED" } : a))
      );
      setAckMessage(`Alert #${alertId} successfully escalated to CDMO supervisory tier.`);
      setTimeout(() => setAckMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to escalate alert");
    } finally {
      setAckLoadingId(null);
    }
  };

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [alertsData, facilitiesData] = await Promise.all([
        apiFetch<AlertItem[]>("/api/v1/alerts"),
        apiFetch<any[]>("/api/v1/facilities").catch(() => []),
      ]);

      const facMap: Record<number, string> = {};
      if (Array.isArray(facilitiesData)) {
        facilitiesData.forEach((f) => {
          facMap[f.id] = f.name;
        });
      }
      setFacilities(facMap);
      setAlerts(alertsData);
    } catch (err: any) {
      console.error("Alerts fetch error:", err);
      setError(err.message || "Failed to load early warning alerts from server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);

  // Read URL query params for ?expand={id} and ?status={status}
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const expandId = params.get("expand");
      if (expandId) {
        const idNum = parseInt(expandId, 10);
        if (!isNaN(idNum)) {
          setExpandedAlerts((prev) => ({ ...prev, [idNum]: true }));
        }
      }
      const statusParam = params.get("status");
      if (statusParam) {
        setStatusFilter(statusParam);
      }
    }
  }, []);


  const criticalCount = alerts.filter((a) => a.severity === "CRITICAL" && (a.status === "ACTIVE" || a.status === "ESCALATED")).length;
  const escalatedCount = alerts.filter((a) => a.status === "ESCALATED").length;
  const warningCount = alerts.filter((a) => a.severity === "WARNING" && (a.status === "ACTIVE" || a.status === "ESCALATED")).length;
  const resolvedCount = alerts.filter((a) => a.status === "RESOLVED" || a.status === "ACKNOWLEDGED").length;

  const filteredAlerts = alerts.filter((a) => {
    const titleMatch = (a.title || "").toLowerCase().includes(searchQuery.toLowerCase());
    const skuMatch = (a.resource_id || "").toLowerCase().includes(searchQuery.toLowerCase());
    const facName = facilities[a.facility_id] || "";
    const facMatch = facName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSearch = !searchQuery || titleMatch || skuMatch || facMatch;

    const matchesSeverity = severityFilter === "ALL" || a.severity === severityFilter;
    const matchesStatus = statusFilter === "ALL" || a.status === statusFilter;

    return matchesSearch && matchesSeverity && matchesStatus;
  });

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E]">Early Warning Risk Alerts</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Deterministic Demand-Outlier &amp; Stockout Forecast Sentinel
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/recommendations"
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-xs transition"
            >
              <IconArrowRight size={16} />
              Open Redistribution Queue
            </Link>
            <button
              onClick={fetchData}
              className="bg-white border border-slate-200 hover:bg-slate-50 active:scale-95 text-slate-700 text-xs font-bold px-3 py-2 rounded-xl flex items-center gap-1.5 shadow-2xs transition"
            >
              <IconRefresh size={16} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
          <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-bold uppercase tracking-wider">Critical Stockouts</span>
              <IconAlertOctagon size={20} className="text-rose-600" />
            </div>
            <h2 className="text-3xl font-black text-rose-600 mt-2">{criticalCount}</h2>
            <span className="text-[11px] text-rose-500 font-semibold block mt-1">Days of Cover &lt; 3.0 Days</span>
          </div>

          <div className="bg-white p-4 sm:p-5 rounded-2xl border border-rose-200/80 shadow-2xs bg-rose-50/20">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-bold uppercase tracking-wider text-rose-800">Escalated to CDMO</span>
              <IconAlertOctagon size={20} className="text-rose-700" />
            </div>
            <h2 className="text-3xl font-black text-rose-700 mt-2">{escalatedCount}</h2>
            <span className="text-[11px] text-rose-600 font-semibold block mt-1">SLA Timeout Exceeded</span>
          </div>

          <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-bold uppercase tracking-wider">Warning Alerts</span>
              <IconClockHour4 size={20} className="text-amber-600" />
            </div>
            <h2 className="text-3xl font-black text-amber-600 mt-2">{warningCount}</h2>
            <span className="text-[11px] text-amber-600 font-semibold block mt-1">Buffer Depletion Threshold</span>
          </div>

          <div className="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-bold uppercase tracking-wider">Acknowledged</span>
              <IconCheck size={20} className="text-teal-600" />
            </div>
            <h2 className="text-3xl font-black text-teal-700 mt-2">{resolvedCount}</h2>
            <span className="text-[11px] text-teal-600 font-semibold block mt-1">Under Active Oversight</span>
          </div>
        </div>

        {/* Action Confirmation Banner */}
        {ackMessage && (
          <div className="bg-teal-50 border border-teal-200 text-teal-800 text-xs p-3 rounded-xl flex items-center justify-between shadow-2xs animate-in fade-in duration-200">
            <span className="flex items-center gap-1.5 font-bold">
              <IconCheck size={16} className="text-teal-600" />
              {ackMessage}
            </span>
            <button onClick={() => setAckMessage(null)} className="text-teal-700 hover:text-teal-900 text-xs font-bold underline cursor-pointer">
              Dismiss
            </button>
          </div>
        )}

        {/* Error Banner */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs p-3 rounded-xl flex items-center justify-between">
            <span>{error}</span>
            <button onClick={fetchData} className="underline font-bold">Retry</button>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex flex-col md:flex-row gap-3 items-center justify-between">
          <div className="relative w-full md:w-80">
            <IconSearch size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by SKU, facility, or alert title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-800 focus:outline-hidden focus:border-[#1D546C] focus:bg-white transition"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <IconFilter size={14} />
              <span>Severity:</span>
            </div>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-xs rounded-xl px-3 py-2 text-slate-700 focus:outline-hidden focus:border-[#1D546C]"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-xs rounded-xl px-3 py-2 text-slate-700 focus:outline-hidden focus:border-[#1D546C]"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active Only</option>
              <option value="ESCALATED">Escalated to CDMO</option>
              <option value="ACKNOWLEDGED">Acknowledged Only</option>
              <option value="MONITORED">Monitored Only</option>
              <option value="RESOLVED">Resolved Only</option>
            </select>
          </div>
        </div>

        {/* Alerts Table */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-slate-400 text-xs">
              <IconRefresh size={24} className="animate-spin mx-auto mb-2 text-slate-300" />
              Loading real-time early warning alerts...
            </div>
          ) : filteredAlerts.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-xs">
              <IconCheck size={32} className="mx-auto mb-2 text-emerald-600" />
              <p className="font-bold text-slate-700">No alerts match the active filter criteria.</p>
              <p className="text-slate-400 mt-1">All monitored resources maintain adequate stock coverage above threshold.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[980px]">
                <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-mono uppercase text-[10px]">
                  <tr>
                    <th className="py-3 px-3.5 font-bold w-[95px]">Severity</th>
                    <th className="py-3 px-3.5 font-bold w-[160px]">Facility</th>
                    <th className="py-3 px-3.5 font-bold w-[120px]">Resource SKU</th>
                    <th className="py-3 px-3.5 font-bold min-w-[220px]">Alert Title &amp; Reason</th>
                    <th className="py-3 px-3.5 font-bold w-[125px]">Projected Impact</th>
                    <th className="py-3 px-3.5 font-bold w-[110px]">Status</th>
                    <th className="py-3 px-3.5 font-bold text-right min-w-[340px]">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredAlerts.map((alt) => {
                    const canAcknowledge =
                      (user?.role === "ADMIN" ||
                       user?.role === "CDMO" ||
                       (user?.role === "FACILITY_OFFICER" && user?.facility_id === alt.facility_id));

                    const canTransition = canAcknowledge && alt.status !== "RESOLVED";

                    return (
                    <React.Fragment key={alt.id || alt.alert_code}>
                      <tr className="hover:bg-slate-50/50 transition">
                      <td className="py-3.5 px-3.5 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-md border ${
                            alt.severity === "CRITICAL"
                              ? "bg-rose-50 text-rose-800 border-rose-200"
                              : "bg-amber-50 text-amber-800 border-amber-200"
                          }`}
                        >
                          <IconAlertOctagon size={12} />
                          {alt.severity}
                        </span>
                      </td>

                      <td className="py-3.5 px-3.5 whitespace-nowrap font-medium text-[#0C2B4E]">
                        <div className="flex items-center gap-1.5">
                          <IconBuildingHospital size={14} className="text-[#1D546C] shrink-0" />
                          <span className="truncate max-w-[140px]" title={facilities[alt.facility_id] || `Facility #${alt.facility_id}`}>
                            {facilities[alt.facility_id] || `Facility #${alt.facility_id}`}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-3.5 whitespace-nowrap font-mono text-[11px] text-slate-700">
                        {alt.resource_id}
                      </td>

                      <td className="py-3.5 px-3.5 text-slate-800 max-w-[260px]">
                        <p className="font-semibold text-xs leading-snug break-words">{alt.title}</p>
                        <span className="text-[10px] text-slate-400 font-mono block mt-0.5 break-all">Code: {alt.alert_code}</span>
                      </td>

                      <td className="py-3.5 px-3.5 whitespace-nowrap font-mono text-[11px] text-slate-600">
                        {alt.projected_impact_date || "Immediate"}
                      </td>

                      <td className="py-3.5 px-3.5 whitespace-nowrap">
                        {alt.status === "ACTIVE" && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                            ACTIVE
                          </span>
                        )}
                        {alt.status === "ESCALATED" && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-black uppercase px-2 py-0.5 rounded bg-rose-100 text-rose-900 border border-rose-300 shadow-2xs">
                            ESCALATED TO CDMO
                          </span>
                        )}
                        {alt.status === "ACKNOWLEDGED" && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-teal-50 text-teal-800 border border-teal-200">
                            <IconCheck size={11} /> ACKNOWLEDGED
                          </span>
                        )}
                        {alt.status === "MONITORED" && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                            <IconCheck size={11} /> MONITORED
                          </span>
                        )}
                        {alt.status === "RESOLVED" && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <IconCheck size={11} /> RESOLVED
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-3.5 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-1.5 font-mono">
                          {/* 1. Why this risk? evidence button */}
                          <button
                            onClick={() => toggleExpand(alt.id)}
                            className="bg-blue-50 hover:bg-blue-100 text-[#0C2B4E] border border-blue-200 px-2.5 py-1 rounded-lg font-bold text-[11px] inline-flex items-center gap-1 cursor-pointer transition shadow-2xs"
                            title="View grounded evidence and reasoning"
                          >
                            <IconHelpCircle size={13} className="text-[#1D546C]" />
                            <span>{expandedAlerts[alt.id] ? "Hide Reason" : "Why this risk?"}</span>
                            {expandedAlerts[alt.id] ? <IconChevronUp size={12} /> : <IconChevronDown size={12} />}
                          </button>

                          {/* 2. ACTIVE Alert Workflow Action: [Acknowledge] */}
                          {alt.status === "ACTIVE" && canTransition && (
                            <button
                              onClick={() => handleAcknowledgeAlert(alt.id)}
                              disabled={ackLoadingId === alt.id}
                              className="bg-teal-700 hover:bg-teal-800 active:scale-95 text-white px-2.5 py-1 rounded-lg font-bold text-[11px] inline-flex items-center gap-1 transition shadow-2xs cursor-pointer disabled:opacity-50"
                              title="Acknowledge receipt and active monitoring of this risk"
                            >
                              <IconCheck size={12} />
                              {ackLoadingId === alt.id ? "Saving..." : "Acknowledge"}
                            </button>
                          )}

                          {/* 3. ACKNOWLEDGED Alert Workflow Actions: [Acknowledged] [Escalate] [Monitor] [Resolve] */}
                          {alt.status === "ACKNOWLEDGED" && (
                            <>
                              <span className="bg-slate-100 text-slate-700 border border-slate-200 px-2 py-0.5 rounded text-[10px] font-bold">
                                Acknowledged
                              </span>
                              {canTransition && (
                                <button
                                  onClick={() => handleEscalateAlert(alt.id)}
                                  disabled={ackLoadingId === alt.id}
                                  className="bg-rose-600 hover:bg-rose-700 active:scale-95 text-white px-2 py-1 rounded-lg font-bold text-[10px] inline-flex items-center gap-1 transition shadow-2xs cursor-pointer disabled:opacity-50"
                                  title="Escalate unresolved risk to CDMO"
                                >
                                  {ackLoadingId === alt.id ? "Escalating..." : "Escalate"}
                                </button>
                              )}
                              {canTransition && (
                                <>
                                  <button
                                    onClick={() => handleMonitorAlert(alt.id)}
                                    disabled={ackLoadingId === alt.id}
                                    className="bg-blue-600 hover:bg-blue-700 active:scale-95 text-white px-2 py-1 rounded-lg font-bold text-[10px] inline-flex items-center gap-1 transition shadow-2xs cursor-pointer disabled:opacity-50"
                                    title="Put alert under active clinical/inventory monitoring"
                                  >
                                    Monitor
                                  </button>
                                  <button
                                    onClick={() => handleResolveAlert(alt.id)}
                                    disabled={ackLoadingId === alt.id}
                                    className="bg-emerald-700 hover:bg-emerald-800 active:scale-95 text-white px-2 py-1 rounded-lg font-bold text-[10px] inline-flex items-center gap-1 transition shadow-2xs cursor-pointer disabled:opacity-50"
                                    title="Resolve alert following replenishment"
                                  >
                                    Resolve
                                  </button>
                                </>
                              )}
                            </>
                          )}

                          {/* 4. ESCALATED Alert Workflow Actions: [Escalated] + CDMO Action */}
                          {alt.status === "ESCALATED" && (
                            <>
                              <span className="bg-rose-100 text-rose-800 border border-rose-200 px-2 py-0.5 rounded text-[10px] font-bold">
                                Escalated
                              </span>
                              {(user?.role === "CDMO" || user?.role === "ADMIN") && (
                                <button
                                  onClick={() => handleAcknowledgeAlert(alt.id)}
                                  disabled={ackLoadingId === alt.id}
                                  className="bg-teal-700 hover:bg-teal-800 active:scale-95 text-white px-2 py-1 rounded-lg font-bold text-[10px] inline-flex items-center gap-1 transition shadow-2xs cursor-pointer disabled:opacity-50"
                                  title="Acknowledge escalated risk as CDMO"
                                >
                                  <IconCheck size={11} /> {ackLoadingId === alt.id ? "Saving..." : "CDMO Acknowledge"}
                                </button>
                              )}
                            </>
                          )}

                          {/* 5. MONITORED Alert Actions */}
                          {alt.status === "MONITORED" && canTransition && (
                            <>
                              <span className="bg-blue-50 text-blue-800 border border-blue-200 px-2 py-0.5 rounded text-[10px] font-bold">
                                Monitored
                              </span>
                              <button
                                onClick={() => handleResolveAlert(alt.id)}
                                disabled={ackLoadingId === alt.id}
                                className="bg-emerald-700 hover:bg-emerald-800 active:scale-95 text-white px-2 py-1 rounded-lg font-bold text-[10px] inline-flex items-center gap-1 transition shadow-2xs cursor-pointer disabled:opacity-50"
                                title="Resolve alert following replenishment"
                              >
                                Resolve
                              </button>
                            </>
                          )}

                          {/* 6. RESOLVED Alert Indicator */}
                          {alt.status === "RESOLVED" && (
                            <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded text-[10px] font-bold">
                              Resolved
                            </span>
                          )}
                          <span className="text-slate-200">|</span>
                          <Link
                            href="/forecasts"
                            className="text-[#1D546C] hover:text-[#0C2B4E] hover:underline font-bold text-[11px] inline-flex items-center gap-0.5 px-1 py-0.5"
                          >
                            <IconTrendingUp size={12} /> Forecast
                          </Link>
                          <span className="text-slate-200">|</span>
                          <Link
                            href="/recommendations"
                            className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-2.5 py-1 rounded-lg font-bold text-[11px] inline-flex items-center gap-0.5 transition shadow-2xs"
                          >
                            Redistribute <IconArrowRight size={11} />
                          </Link>
                        </div>
                      </td>
                    </tr>

                    {/* Expandable Evidence & Explainability Drawer */}
                    {expandedAlerts[alt.id] && (
                      <tr key={`exp-${alt.id}`} className="bg-blue-50/40 border-b border-slate-200">
                        <td colSpan={7} className="p-3 sm:p-4">
                          <div className="bg-white rounded-xl border border-blue-200/80 p-4 shadow-2xs space-y-3 font-mono">
                            {/* Escalation Supervisory Banner if Escalated */}
                            {alt.status === "ESCALATED" && (
                              <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl flex items-start gap-2.5">
                                <IconAlertOctagon size={18} className="text-rose-600 shrink-0 mt-0.5" />
                                <div className="space-y-1 text-xs">
                                  <div className="flex items-center gap-2">
                                    <span className="font-extrabold text-rose-900 uppercase tracking-wide">
                                      Supervisory Escalation: CDMO Action Required
                                    </span>
                                    <span className="text-[10px] bg-rose-200 text-rose-900 px-1.5 py-0.5 rounded font-mono font-bold">
                                      Level 1 Escalation
                                    </span>
                                  </div>
                                  <p className="text-rose-800 text-[11px] font-sans">
                                    Frontline facility officer did not acknowledge within the configured SLA window. Alert has escalated to the district supervisory queue for CDMO intervention and redistribution authorization.
                                  </p>
                                </div>
                              </div>
                            )}

                            {/* Section 9: Lifecycle Audit Trail (WHAT HAPPENED) */}
                            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">
                                  Lifecycle Audit Trail (What Happened)
                                </span>
                                <span className="text-[10px] font-mono text-slate-500">
                                  Current Status: <strong className="text-[#0C2B4E] uppercase">{alt.status}</strong>
                                </span>
                              </div>

                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-[11px] font-mono bg-white p-2.5 rounded-md border border-slate-200/80">
                                <div>
                                  <span className="text-[9.5px] uppercase font-bold text-slate-400 block">Notification Created</span>
                                  <span className="text-slate-700">
                                    {alt.notification_lifecycle?.notification_created_at
                                      ? new Date(alt.notification_lifecycle.notification_created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
                                      : "At alert trigger"}
                                  </span>
                                </div>

                                <div>
                                  <span className="text-[9.5px] uppercase font-bold text-slate-400 block">Frontline Officer Status</span>
                                  {alt.notification_lifecycle?.is_acknowledged ? (
                                    <span className="text-teal-700 font-bold">
                                      Acknowledged {alt.notification_lifecycle.acknowledged_by_name ? `(${alt.notification_lifecycle.acknowledged_by_name})` : ""}
                                    </span>
                                  ) : alt.status === "ESCALATED" ? (
                                    <span className="text-rose-700 font-bold">Unacknowledged (SLA Exceeded)</span>
                                  ) : (
                                    <span className="text-amber-700 font-bold">Awaiting Acknowledgment</span>
                                  )}
                                </div>

                                <div>
                                  <span className="text-[9.5px] uppercase font-bold text-slate-400 block">Supervisory Escalation</span>
                                  {alt.status === "ESCALATED" || alt.notification_lifecycle?.is_escalated ? (
                                    <span className="text-rose-800 font-bold">
                                      Escalated to CDMO {alt.notification_lifecycle?.escalated_at ? `(${new Date(alt.notification_lifecycle.escalated_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })})` : ""}
                                    </span>
                                  ) : (
                                    <span className="text-slate-500">Within Standard SLA</span>
                                  )}
                                </div>
                              </div>
                            </div>

                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2">
                              <div className="flex items-center gap-2">
                                <IconInfoCircle size={16} className="text-[#1D546C]" />
                                <span className="font-bold text-xs text-[#0C2B4E] uppercase tracking-wider">
                                  Risk Explainability &amp; Grounded Evidence (Why)
                                </span>
                              </div>
                              <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold self-start sm:self-auto">
                                {facilities[alt.facility_id] || `Facility #${alt.facility_id}`} • {alt.resource_id}
                              </span>
                            </div>


                            {/* Evidence Metrics Grid */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
                              <div>
                                <span className="text-[10px] text-slate-400 block uppercase font-bold">Current Stock</span>
                                <span className="font-bold text-[#0C2B4E]">
                                  {alt.explanation?.evidence?.current_stock ?? "—"} {alt.explanation?.evidence?.unit || "units"}
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block uppercase font-bold">Daily Demand</span>
                                <span className="font-bold text-slate-700">
                                  {alt.explanation?.evidence?.estimated_daily_demand ?? "—"} /day
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block uppercase font-bold">Days of Cover</span>
                                <span className={`font-black ${alt.severity === "CRITICAL" ? "text-rose-600" : "text-amber-600"}`}>
                                  {alt.explanation?.evidence?.days_of_cover ?? "—"} Days
                                </span>
                              </div>
                              <div>
                                <span className="text-[10px] text-slate-400 block uppercase font-bold">Safety Threshold</span>
                                <span className="font-bold text-slate-700">
                                  {alt.explanation?.evidence?.safety_stock ?? 40} {alt.explanation?.evidence?.unit || "units"}
                                </span>
                              </div>
                            </div>

                            {/* Why explanation */}
                            <div className="space-y-1">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                                Causal Explanation (Why):
                              </span>
                              <p className="text-slate-700 bg-amber-50/60 border border-amber-200/60 p-2.5 rounded-lg font-sans text-xs leading-relaxed">
                                {alt.explanation?.why || alt.title}
                              </p>
                            </div>

                            {/* Recommended Action */}
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1 border-t border-slate-100">
                              <div className="text-[11px] text-slate-600 font-sans">
                                <strong className="text-slate-800 font-mono text-[10px] uppercase block sm:inline mr-1">
                                  Recommended Action:
                                </strong>
                                <span>{alt.explanation?.recommended_action || "Review stock and consider redistribution."}</span>
                              </div>
                              <Link
                                href="/recommendations"
                                className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white text-[11px] font-bold px-3 py-1.5 rounded-lg inline-flex items-center gap-1 shrink-0 self-start sm:self-auto transition shadow-2xs"
                              >
                                Open Redistribution Queue <IconArrowRight size={12} />
                              </Link>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  </AppShell>
);
}
