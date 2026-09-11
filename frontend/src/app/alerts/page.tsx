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
} from "@tabler/icons-react";

interface AlertItem {
  id: number;
  alert_code: string;
  facility_id: number;
  resource_id: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  alert_type: string;
  title: string;
  projected_impact_date: string | null;
  status: "ACTIVE" | "RESOLVED" | "ACKNOWLEDGED";
  created_at: string;
  facility_name?: string;
}

export default function AlertsPage() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [facilities, setFacilities] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("ACTIVE");

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

  const criticalCount = alerts.filter((a) => a.severity === "CRITICAL" && a.status === "ACTIVE").length;
  const warningCount = alerts.filter((a) => a.severity === "WARNING" && a.status === "ACTIVE").length;
  const resolvedCount = alerts.filter((a) => a.status === "RESOLVED").length;

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
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-bold uppercase tracking-wider">Critical Stockouts</span>
              <IconAlertOctagon size={20} className="text-rose-600" />
            </div>
            <h2 className="text-3xl font-black text-rose-600 mt-2">{criticalCount}</h2>
            <span className="text-[11px] text-rose-500 font-semibold block mt-1">Days of Cover &lt; 3.0 Days</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-bold uppercase tracking-wider">Warning Alerts</span>
              <IconClockHour4 size={20} className="text-amber-600" />
            </div>
            <h2 className="text-3xl font-black text-amber-600 mt-2">{warningCount}</h2>
            <span className="text-[11px] text-amber-600 font-semibold block mt-1">Buffer Depletion Threshold</span>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-xs font-bold uppercase tracking-wider">Resolved Alerts</span>
              <IconCheck size={20} className="text-emerald-600" />
            </div>
            <h2 className="text-3xl font-black text-emerald-700 mt-2">{resolvedCount}</h2>
            <span className="text-[11px] text-emerald-600 font-semibold block mt-1">Stock Replenished Post-Transfer</span>
          </div>
        </div>

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
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-mono uppercase text-[10px]">
                  <tr>
                    <th className="py-3 px-4 font-bold">Severity</th>
                    <th className="py-3 px-4 font-bold">Facility</th>
                    <th className="py-3 px-4 font-bold">Resource SKU</th>
                    <th className="py-3 px-4 font-bold">Alert Title &amp; Reason</th>
                    <th className="py-3 px-4 font-bold">Projected Stockout</th>
                    <th className="py-3 px-4 font-bold">Status</th>
                    <th className="py-3 px-4 font-bold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredAlerts.map((alt) => (
                    <tr key={alt.id || alt.alert_code} className="hover:bg-slate-50/50 transition">
                      <td className="py-3.5 px-4 whitespace-nowrap">
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

                      <td className="py-3.5 px-4 whitespace-nowrap font-medium text-[#0C2B4E]">
                        <div className="flex items-center gap-1.5">
                          <IconBuildingHospital size={14} className="text-[#1D546C]" />
                          <span>{facilities[alt.facility_id] || `Facility #${alt.facility_id}`}</span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap font-mono text-[11px] text-slate-700">
                        {alt.resource_id}
                      </td>

                      <td className="py-3.5 px-4 text-slate-800 max-w-xs">
                        <p className="font-semibold text-xs">{alt.title}</p>
                        <span className="text-[10px] text-slate-400 font-mono">Code: {alt.alert_code}</span>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap font-mono text-[11px] text-slate-600">
                        {alt.projected_impact_date || "Immediate"}
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                            alt.status === "ACTIVE"
                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                              : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          }`}
                        >
                          {alt.status}
                        </span>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href="/forecasts"
                            className="text-[#1D546C] hover:underline font-bold text-[11px] flex items-center gap-0.5"
                          >
                            <IconTrendingUp size={12} /> Forecast
                          </Link>
                          <span className="text-slate-300">|</span>
                          <Link
                            href="/recommendations"
                            className="text-[#0C2B4E] hover:underline font-bold text-[11px] flex items-center gap-0.5"
                          >
                            Redistribute <IconArrowRight size={12} />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
