"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { API_BASE_URL, getApiBaseUrl } from "@/config";
import { 
  IconDatabase, 
  IconAlertOctagon, 
  IconCircleCheck, 
  IconTruckDelivery, 
  IconRefresh, 
  IconSparkles,
  IconArrowRight,
  IconClockHour4,
  IconShieldCheck,
  IconTrendingUp,
  IconBuildingHospital,
  IconReportMedical,
  IconCheck,
  IconLock
} from "@tabler/icons-react";

export default function DashboardPage() {
  const { user, getAuthHeaders } = useAuth();
  const [alerts, setAlerts] = useState<any[]>([]);
  const [forecasts, setForecasts] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const headers = getAuthHeaders();
      const baseUrl = getApiBaseUrl();

      const [resAlerts, resForecasts, resRecs] = await Promise.all([
        fetch(`${baseUrl}/api/v1/alerts`, { headers }),
        fetch(`${baseUrl}/api/v1/forecasts`, { headers }),
        fetch(`${baseUrl}/api/v1/recommendations`, { headers }),
      ]);

      const errors: string[] = [];

      if (resAlerts.ok) {
        setAlerts(await resAlerts.json());
      } else {
        errors.push(`Alerts API returned HTTP ${resAlerts.status}`);
      }

      if (resForecasts.ok) {
        setForecasts(await resForecasts.json());
      } else {
        errors.push(`Forecasts API returned HTTP ${resForecasts.status}`);
      }

      if (resRecs.ok) {
        setRecommendations(await resRecs.json());
      } else {
        errors.push(`Recommendations API returned HTTP ${resRecs.status}`);
      }

      if (errors.length > 0) {
        setError(errors.join(" | "));
      }
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError("Unable to connect to Healysis backend API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [user]);

  const isOfficer = user?.role === "FACILITY_OFFICER";
  const isCDMO = user?.role === "CDMO";
  const isAdmin = user?.role === "ADMIN";

  const criticalAlerts = alerts.filter((a) => a.severity === "CRITICAL");
  const warningAlerts = alerts.filter((a) => a.severity === "WARNING");
  const pendingRecs = recommendations.filter((r) => r.status === "PENDING_HUMAN_APPROVAL");

  return (
    <AppShell>
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-1 duration-200">
        
        {/* DASHBOARD HERO SECTION */}
        <div className="bg-gradient-to-r from-white via-slate-50 to-[#F4F4F4] rounded-2xl border border-slate-200 p-6 md:p-8 shadow-xs">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            
            {/* Left Hero Column */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 bg-white text-[#1D546C] border border-slate-200 px-3 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider shadow-2xs">
                  <IconShieldCheck size={14} className="text-emerald-600" />
                  INDIAN HEALTHCARE NETWORK · NLEM 2022
                </span>
                <span className="bg-[#0C2B4E]/5 text-[#0C2B4E] border border-[#0C2B4E]/15 px-2.5 py-0.5 rounded-full text-[9.5px] font-mono font-bold uppercase">
                  STATE → DISTRICT → PHC/CHC
                </span>
              </div>

              <h1 className="text-3xl md:text-4xl font-black text-[#0C2B4E] tracking-tight leading-tight">
                {isOfficer ? `Operational Status: ${user.facility_name}` : "Healthcare Resource Intelligence"}
              </h1>

              <p className="text-xs md:text-sm text-slate-600 max-w-xl leading-relaxed">
                {isOfficer 
                  ? `Real-time resource telemetry, buffer safety stock, and projected stockout monitoring for ${user.facility_name}.`
                  : "Monitor facility health, anticipate resource shortages, and coordinate evidence-based redistribution across the health network."}
              </p>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Link
                  href="/advisor"
                  className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition shadow-xs flex items-center gap-2 cursor-pointer"
                >
                  <IconSparkles size={16} />
                  Open AI Advisor
                </Link>
                <Link
                  href="/forecasts"
                  className="bg-white hover:bg-slate-50 border border-slate-300 text-slate-800 px-5 py-2.5 rounded-xl text-xs font-bold transition shadow-2xs flex items-center gap-2 cursor-pointer"
                >
                  <IconTrendingUp size={16} className="text-[#1D546C]" />
                  View Forecasts
                </Link>
              </div>
            </div>

            {/* Right Hero Column: Verified Backend Network Status Card */}
            <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-3 font-mono">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                  {isOfficer ? "Assigned Scope" : "Network Status"}
                </span>
                <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded flex items-center gap-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Operational
                </span>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center py-1">
                <div className="p-2 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-[9px] text-slate-400 uppercase block">{isOfficer ? "My Facility" : "Facilities"}</span>
                  <span className="text-lg font-black text-[#0C2B4E]">{isOfficer ? "1 Node" : "5 Monitored"}</span>
                </div>
                <div className="p-2 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-[9px] text-slate-400 uppercase block">Active Alerts</span>
                  <span className="text-lg font-black text-amber-600">{alerts.length}</span>
                </div>
                <div className="p-2 bg-slate-50 rounded-xl border border-slate-100">
                  <span className="text-[9px] text-slate-400 uppercase block">Critical Risks</span>
                  <span className="text-lg font-black text-rose-600">{criticalAlerts.length}</span>
                </div>
              </div>

              <div className="text-[10px] text-slate-400 text-center pt-1 border-t border-slate-100">
                {isOfficer ? `Assigned Facility: ${user.facility_name}` : "Odisha (3) & West Bengal (2) Monitored Nodes"}
              </div>
            </div>

          </div>
        </div>

        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs p-3 rounded-xl flex items-center justify-between">
            <span>{error}</span>
            <button onClick={fetchData} className="underline font-bold">Retry</button>
          </div>
        )}

        {/* SECTION 1: FACILITY OFFICER FOCUSED EXPERIENCE */}
        {isOfficer && (
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-[#0C2B4E] flex items-center gap-2">
                <IconBuildingHospital size={18} className="text-[#1D546C]" />
                MY FACILITY STATUS: {user.facility_name}
              </h2>
              <span className="text-xs font-bold text-blue-800 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-lg flex items-center gap-1">
                <IconLock size={12} /> Restricted Scope
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono">
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl">
                <span className="text-[10px] text-rose-600 font-bold uppercase block">Critical Resources</span>
                <span className="text-2xl font-black text-rose-700">{criticalAlerts.length}</span>
                <span className="text-[10px] text-rose-500 block mt-1">Stock cover &lt; 3 days</span>
              </div>
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <span className="text-[10px] text-amber-700 font-bold uppercase block">Warnings</span>
                <span className="text-2xl font-black text-amber-800">{warningAlerts.length}</span>
                <span className="text-[10px] text-amber-600 block mt-1">Buffer depletion threshold</span>
              </div>
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
                <span className="text-[10px] text-emerald-700 font-bold uppercase block">Safe Resources</span>
                <span className="text-2xl font-black text-emerald-800">8</span>
                <span className="text-[10px] text-emerald-600 block mt-1">Stock cover &ge; 7 days</span>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 2: HEALTH NETWORK METRICS */}
        {!isOfficer && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 font-mono">
                {isCDMO ? "Regional Network Health Overview" : "System Health Overview"}
              </h2>
              <button
                onClick={fetchData}
                className="text-xs text-slate-500 hover:text-[#0C2B4E] flex items-center gap-1 font-semibold"
              >
                <IconRefresh size={14} className={loading ? "animate-spin" : ""} /> Refresh
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-bold uppercase tracking-wider">Facilities Monitored</span>
                  <IconBuildingHospital size={18} className="text-[#1D546C]" />
                </div>
                <h3 className="text-2xl font-black text-[#0C2B4E] mt-1.5">5</h3>
                <span className="text-[11px] text-slate-400 font-mono block">Odisha & WB Nodes</span>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-bold uppercase tracking-wider">Critical Stockouts</span>
                  <IconAlertOctagon size={18} className="text-rose-600" />
                </div>
                <h3 className="text-2xl font-black text-rose-600 mt-1.5">{criticalAlerts.length}</h3>
                <span className="text-[11px] text-rose-500 font-semibold block">DoC &lt; 3.0 Days</span>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-bold uppercase tracking-wider">Warning Alerts</span>
                  <IconClockHour4 size={18} className="text-amber-600" />
                </div>
                <h3 className="text-2xl font-black text-amber-600 mt-1.5">{warningAlerts.length}</h3>
                <span className="text-[11px] text-amber-600 font-semibold block">Buffer Depletion</span>
              </div>

              <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
                <div className="flex items-center justify-between text-slate-500">
                  <span className="text-xs font-bold uppercase tracking-wider">Pending Rebalances</span>
                  <IconTruckDelivery size={18} className="text-emerald-600" />
                </div>
                <h3 className="text-2xl font-black text-emerald-700 mt-1.5">{pendingRecs.length}</h3>
                <span className="text-[11px] text-emerald-600 font-semibold block">Awaiting Human CDMO Approval</span>
              </div>
            </div>
          </div>
        )}

        {/* ACTIVE ALERTS SECTION */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-[#0C2B4E] flex items-center gap-2">
              <IconAlertOctagon size={18} className="text-rose-600" />
              Active Early Warning Alerts
            </h2>
            <Link href="/forecasts" className="text-xs font-bold text-[#1D546C] hover:underline flex items-center gap-1">
              View All Forecasts <IconArrowRight size={14} />
            </Link>
          </div>

          {alerts.length === 0 ? (
            <div className="bg-emerald-50/50 border border-emerald-200 p-4 rounded-xl flex items-center gap-3 text-emerald-900">
              <IconCircleCheck size={20} className="text-emerald-600 shrink-0" />
              <div className="text-xs">
                <span className="font-bold">No Critical Resource Risks Detected:</span>
                <p className="text-emerald-700">Monitored resources are currently within safety operational thresholds.</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {alerts.map((a) => (
                <div key={a.id || a.alert_code} className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded ${
                        a.severity === "CRITICAL" ? "bg-rose-100 text-rose-800 border border-rose-300" : "bg-amber-100 text-amber-800 border border-amber-300"
                      }`}>
                        {a.severity}
                      </span>
                      {a.status === "ESCALATED" && (
                        <span className="text-[9.5px] font-black uppercase px-1.5 py-0.5 rounded bg-rose-100 text-rose-900 border border-rose-300">
                          ESCALATED TO CDMO
                        </span>
                      )}
                    </div>
                    <span className="text-xs font-bold text-[#0C2B4E] truncate max-w-[200px]" title={a.title}>{a.title}</span>
                  </div>
                  <p className="text-xs text-slate-600 font-mono">
                    Resource SKU: {a.resource_id} | Impact Date: {a.projected_impact_date || "Immediate"}
                  </p>
                  <div className="pt-2 flex items-center justify-between border-t border-slate-200 text-xs">
                    <span className="text-slate-500">Days of Cover: <strong>{a.days_of_cover || "0.5"} days</strong></span>
                    <Link href={`/alerts?expand=${a.id}`} className="text-[#1D546C] font-bold hover:underline flex items-center gap-0.5">
                      View Risk &amp; Evidence <IconArrowRight size={12} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* REDISTRIBUTION SECTION */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-bold text-[#0C2B4E] flex items-center gap-2">
              <IconTruckDelivery size={18} className="text-emerald-600" />
              Redistribution Recommendations Queue
            </h2>
            <Link href="/recommendations" className="text-xs font-bold text-[#1D546C] hover:underline flex items-center gap-1">
              Open Rebalance Engine <IconArrowRight size={14} />
            </Link>
          </div>

          {recommendations.length === 0 ? (
            <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl flex items-center gap-3 text-slate-700">
              <IconCheck size={20} className="text-emerald-600 shrink-0" />
              <div className="text-xs">
                <span className="font-bold text-[#0C2B4E]">No Active Rebalance Recommendations Required:</span>
                <p className="text-slate-500">All monitored facilities maintain safe operational stock cover (DoC &ge; 7.0 days).</p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {recommendations.map((r) => (
                <div key={r.id} className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[#0C2B4E]">
                      Transfer {r.recommended_quantity} units of {r.item_code}
                    </span>
                    <span className="text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 px-2 py-0.5 rounded">
                      {r.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">{r.reason}</p>
                  <div className="text-[11px] font-mono text-slate-500 flex items-center gap-4 pt-1">
                    <span>Distance: {r.haversine_distance_km} km</span>
                    <span>Coverage Gained: +{r.expected_days_cover_gained} days</span>
                    <span className="text-rose-700 font-bold">Human CDMO Approval Mandatory</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI ADVISOR ENTRY CARD */}
        <div className="bg-gradient-to-r from-slate-900 via-[#0C2B4E] to-slate-900 text-white p-6 rounded-2xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 bg-white/10 text-emerald-300 border border-white/10 px-3 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider">
              <IconSparkles size={14} /> HEALYSIS AI ADVISOR
            </div>
            <h3 className="text-xl font-black tracking-tight">Ask Healysis AI Advisor</h3>
            <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
              Consult the grounded Gemini AI Advisor on resource shortages, facility risk profiles, demand forecasts, and donor candidate eligibility.
            </p>
          </div>

          <Link
            href="/advisor"
            className="bg-white hover:bg-slate-100 text-[#0C2B4E] px-6 py-3 rounded-xl text-xs font-extrabold shadow-md transition flex items-center gap-2 shrink-0 self-start md:self-auto cursor-pointer"
          >
            Open AI Advisor <IconArrowRight size={16} />
          </Link>
        </div>

      </div>
    </AppShell>
  );
}
