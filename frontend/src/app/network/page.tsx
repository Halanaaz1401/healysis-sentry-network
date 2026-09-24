"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import { 
  IconNetwork,
  IconShieldCheck,
  IconAlertOctagon,
  IconAlertTriangle,
  IconCircleCheck,
  IconRefresh,
  IconBuildingHospital,
  IconReportMedical,
  IconTrendingUp,
  IconArrowRight,
  IconLock,
  IconActivity,
  IconTruckDelivery,
  IconSearch,
  IconCheck
} from "@tabler/icons-react";

interface DistrictItem {
  district: string;
  state: string;
  facility_count: number;
  critical_facilities_count: number;
  warning_facilities_count: number;
  safe_facilities_count: number;
  total_inventory: number;
  total_daily_velocity: number;
  resources_at_risk_count: number;
  resources_surplus_count: number;
  active_alerts_count: number;
  pending_interventions_count: number;
}

interface ResourceItem {
  item_code: string;
  item_name: string;
  category: string;
  unit: string;
  total_network_stock: number;
  total_daily_demand: number;
  network_days_of_cover: number;
  facilities_below_safety_count: number;
  critical_facilities_count: number;
  warning_facilities_count: number;
  surplus_facilities_count: number;
  potential_donors: string[];
  potential_recipients: string[];
}

interface InterventionItem {
  priority_rank: number;
  facility_id: number;
  facility_name: string;
  district: string;
  state: string;
  item_code: string;
  item_name: string;
  current_stock: number;
  daily_demand: number;
  days_of_cover: number;
  safety_stock: number;
  risk_severity: string;
  projected_stockout_date?: string;
  has_pending_recommendation: boolean;
  existing_recommendation_code?: string;
  suggested_action: string;
}

interface NetworkOverview {
  total_facilities: number;
  total_resources_monitored: number;
  critical_facilities_count: number;
  warning_facilities_count: number;
  safe_facilities_count: number;
  total_stock_units: number;
  facilities_requiring_intervention: number;
  pending_redistribution_recommendations: number;
  active_critical_alerts: number;
  active_warning_alerts: number;
  network_shortage_count: number;
  network_surplus_count: number;
}

interface NetworkRiskSummary {
  classification: "CRITICAL" | "WARNING" | "STABLE";
  headline: string;
  explanation: string;
  criteria_met: string[];
}

interface NetworkData {
  generated_at: string;
  overview: NetworkOverview;
  risk_summary: NetworkRiskSummary;
  districts: DistrictItem[];
  resources: ResourceItem[];
  intervention_priority: InterventionItem[];
  disclaimer: string;
}

export default function NetworkIntelligencePage() {
  const { user } = useAuth();
  const [data, setData] = useState<NetworkData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [districtFilter, setDistrictFilter] = useState("");
  const [resourceFilter, setResourceFilter] = useState("");

  const fetchIntelligence = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch<NetworkData>("/api/v1/network/intelligence");
      setData(res);
    } catch (err: any) {
      console.error("Network Intelligence fetch error:", err);
      if (err.status === 403 || err.message?.includes("Forbidden")) {
        setError("ACCESS_FORBIDDEN");
      } else {
        setError(err.message || "Failed to load network intelligence.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntelligence();
  }, [user]);

  // If Facility Officer, show strict RBAC boundary message
  if (user?.role === "FACILITY_OFFICER" || error === "ACCESS_FORBIDDEN") {
    return (
      <AppShell>
        <div className="max-w-4xl mx-auto py-12 px-4">
          <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-sm space-y-6 text-center">
            <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200 text-amber-700 flex items-center justify-center mx-auto">
              <IconLock size={32} />
            </div>
            <div className="space-y-2">
              <span className="text-[11px] font-mono font-bold tracking-widest text-amber-700 uppercase bg-amber-100/70 px-3 py-1 rounded-full border border-amber-300 inline-block">
                RBAC ACCESS CONTROL ENFORCED
              </span>
              <h1 className="text-2xl font-black text-[#0C2B4E]">
                Network Intelligence Restricted
              </h1>
              <p className="text-sm text-slate-600 max-w-lg mx-auto font-sans leading-relaxed">
                Network-wide and cross-district operational aggregation is restricted to authorized CDMO and Admin directors.
                As a <strong>Facility Officer</strong>, your operational scope is strictly isolated to your assigned facility.
              </p>
            </div>
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2 font-mono text-xs">
              <Link
                href="/dashboard"
                className="bg-[#0C2B4E] hover:bg-[#1D546C] text-white px-5 py-2.5 rounded-xl font-bold transition shadow-xs flex items-center gap-2"
              >
                <IconBuildingHospital size={16} />
                Return to Facility Dashboard
              </Link>
              <Link
                href="/advisor"
                className="bg-slate-100 hover:bg-slate-200 text-slate-800 px-5 py-2.5 rounded-xl font-bold transition border border-slate-300 flex items-center gap-2"
              >
                Open AI Advisor
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  const filteredDistricts = data?.districts.filter(d => 
    d.district.toLowerCase().includes(districtFilter.toLowerCase()) ||
    d.state.toLowerCase().includes(districtFilter.toLowerCase())
  ) || [];

  const filteredResources = data?.resources.filter(r => 
    r.item_name.toLowerCase().includes(resourceFilter.toLowerCase()) ||
    r.item_code.toLowerCase().includes(resourceFilter.toLowerCase())
  ) || [];

  return (
    <AppShell>
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-1 duration-200 pb-16">
        
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-2 bg-white text-[#1D546C] border border-slate-200 px-3 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider shadow-2xs">
              <IconNetwork size={14} className="text-[#1D546C]" />
              Feature #11 • Multi-District Operational Telemetry
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#0C2B4E] tracking-tight">
              District / Network Intelligence
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 font-mono">
              Network-level operational visibility, shortage/surplus signals, and intervention priorities. Grounded in authoritative DB records.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchIntelligence}
              disabled={loading}
              className="bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 px-4 py-2 rounded-xl text-xs font-mono font-bold flex items-center gap-2 shadow-2xs transition cursor-pointer disabled:opacity-50"
            >
              <IconRefresh size={14} className={loading ? "animate-spin" : ""} />
              {loading ? "Refreshing..." : "Refresh Network"}
            </button>
            <div className="hidden lg:flex items-center gap-2 font-mono text-[11px] text-emerald-800 bg-emerald-50 px-3 py-2 rounded-xl border border-emerald-200">
              <IconShieldCheck size={16} className="text-emerald-600" />
              <span>CDMO Network Scope Verified</span>
            </div>
          </div>
        </div>

        {/* Deterministic Network Risk Summary Banner */}
        {data && (
          <div className={`p-5 rounded-2xl border-2 shadow-xs transition-all ${
            data.risk_summary.classification === "CRITICAL"
              ? "bg-rose-50/70 border-rose-300 text-rose-950"
              : data.risk_summary.classification === "WARNING"
                ? "bg-amber-50/70 border-amber-300 text-amber-950"
                : "bg-emerald-50/70 border-emerald-300 text-emerald-950"
          }`}>
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2.5">
                  <span className={`text-[10px] font-black uppercase px-2.5 py-0.5 rounded-md border font-mono tracking-wider ${
                    data.risk_summary.classification === "CRITICAL"
                      ? "bg-rose-600 text-white border-rose-700"
                      : data.risk_summary.classification === "WARNING"
                        ? "bg-amber-500 text-white border-amber-600"
                        : "bg-emerald-600 text-white border-emerald-700"
                  }`}>
                    NETWORK STATUS: {data.risk_summary.classification}
                  </span>
                  <span className="text-xs font-mono text-slate-500">
                    Generated: {new Date(data.generated_at).toLocaleTimeString()} UTC
                  </span>
                </div>
                <h2 className="text-base sm:text-lg font-black text-[#0C2B4E]">
                  {data.risk_summary.headline}
                </h2>
                <p className="text-xs sm:text-sm text-slate-700 font-sans leading-relaxed max-w-3xl">
                  {data.risk_summary.explanation}
                </p>
              </div>

              {/* Criteria Met */}
              <div className="bg-white/90 p-3.5 rounded-xl border border-slate-200 space-y-1.5 shrink-0 font-mono text-[11px] min-w-[240px]">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Deterministic Trigger Rules
                </span>
                {data.risk_summary.criteria_met.map((crit, idx) => (
                  <div key={idx} className="flex items-center gap-1.5 text-slate-800">
                    <IconCheck size={13} className="text-emerald-600 shrink-0" />
                    <span>{crit}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Section 1: Network Overview Stat Tiles */}
        {data && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono">
            {/* Total Facilities */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Total Facilities
              </span>
              <div className="text-2xl font-black text-[#0C2B4E]">
                {data.overview.total_facilities}
              </div>
              <span className="text-[10px] text-slate-500 font-sans block">
                across {data.districts.length} districts
              </span>
            </div>

            {/* Critical Facilities */}
            <div className="bg-white p-4 rounded-2xl border border-rose-200 shadow-2xs space-y-1 bg-rose-50/20">
              <span className="text-[10px] font-bold text-rose-500 uppercase tracking-wider block">
                Critical Facilities
              </span>
              <div className="text-2xl font-black text-rose-700">
                {data.overview.critical_facilities_count}
              </div>
              <span className="text-[10px] text-rose-600 font-sans block">
                &lt; 3.0 days cover
              </span>
            </div>

            {/* Warning Facilities */}
            <div className="bg-white p-4 rounded-2xl border border-amber-200 shadow-2xs space-y-1 bg-amber-50/20">
              <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider block">
                Warning Facilities
              </span>
              <div className="text-2xl font-black text-amber-700">
                {data.overview.warning_facilities_count}
              </div>
              <span className="text-[10px] text-amber-600 font-sans block">
                3.0 - 7.0 days cover
              </span>
            </div>

            {/* Safe Facilities */}
            <div className="bg-white p-4 rounded-2xl border border-emerald-200 shadow-2xs space-y-1 bg-emerald-50/20">
              <span className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider block">
                Safe Facilities
              </span>
              <div className="text-2xl font-black text-emerald-700">
                {data.overview.safe_facilities_count}
              </div>
              <span className="text-[10px] text-emerald-600 font-sans block">
                ≥ 7.0 days buffer
              </span>
            </div>

            {/* Total Stock Units */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                Network Stock
              </span>
              <div className="text-2xl font-black text-[#0C2B4E]">
                {data.overview.total_stock_units}
              </div>
              <span className="text-[10px] text-slate-500 font-sans block">
                {data.overview.total_resources_monitored} monitored SKUs
              </span>
            </div>

            {/* Pending Interventions */}
            <div className="bg-white p-4 rounded-2xl border border-indigo-200 shadow-2xs space-y-1 bg-indigo-50/20">
              <span className="text-[10px] font-bold text-indigo-600 uppercase tracking-wider block">
                Pending Interventions
              </span>
              <div className="text-2xl font-black text-indigo-900">
                {data.overview.pending_redistribution_recommendations}
              </div>
              <span className="text-[10px] text-indigo-700 font-sans block">
                {data.overview.facilities_requiring_intervention} nodes at risk
              </span>
            </div>
          </div>
        )}

        {/* Section 2: District Risk Overview Table */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-base font-black text-[#0C2B4E]">
                District Risk Breakdown
              </h3>
              <p className="text-xs text-slate-500 font-mono">
                Regional healthcare supply-chain resilience grouped by administrative district.
              </p>
            </div>
            <div className="relative w-full sm:w-64 font-mono text-xs">
              <IconSearch size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={districtFilter}
                onChange={(e) => setDistrictFilter(e.target.value)}
                placeholder="Filter districts..."
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 text-[10px] uppercase tracking-wider bg-slate-50/50">
                  <th className="py-2.5 px-3">District</th>
                  <th className="py-2.5 px-3 text-center">Facilities</th>
                  <th className="py-2.5 px-3 text-center">Critical</th>
                  <th className="py-2.5 px-3 text-center">Warning</th>
                  <th className="py-2.5 px-3 text-center">Safe</th>
                  <th className="py-2.5 px-3 text-right">Total Inventory</th>
                  <th className="py-2.5 px-3 text-right">Daily Demand</th>
                  <th className="py-2.5 px-3 text-center">At Risk SKUs</th>
                  <th className="py-2.5 px-3 text-center">Active Alerts</th>
                  <th className="py-2.5 px-3 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDistricts.map((d) => {
                  const status = d.critical_facilities_count > 0 ? "CRITICAL" : (d.warning_facilities_count > 0 ? "WARNING" : "SAFE");
                  return (
                    <tr key={`${d.district}-${d.state}`} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-3 font-bold text-slate-900 font-sans">
                        {d.district} <span className="text-slate-400 font-mono text-[10px]">({d.state})</span>
                      </td>
                      <td className="py-3 px-3 text-center font-bold">{d.facility_count}</td>
                      <td className="py-3 px-3 text-center font-bold text-rose-700">
                        {d.critical_facilities_count > 0 ? d.critical_facilities_count : "—"}
                      </td>
                      <td className="py-3 px-3 text-center font-bold text-amber-700">
                        {d.warning_facilities_count > 0 ? d.warning_facilities_count : "—"}
                      </td>
                      <td className="py-3 px-3 text-center font-bold text-emerald-700">
                        {d.safe_facilities_count}
                      </td>
                      <td className="py-3 px-3 text-right font-bold text-slate-800">
                        {d.total_inventory} units
                      </td>
                      <td className="py-3 px-3 text-right text-slate-600">
                        {d.total_daily_velocity} /day
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          d.resources_at_risk_count > 0 ? "bg-rose-100 text-rose-800" : "text-slate-400"
                        }`}>
                          {d.resources_at_risk_count}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          d.active_alerts_count > 0 ? "bg-amber-100 text-amber-900" : "text-slate-400"
                        }`}>
                          {d.active_alerts_count}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase border ${
                          status === "CRITICAL"
                            ? "bg-rose-100 border-rose-300 text-rose-800"
                            : status === "WARNING"
                              ? "bg-amber-100 border-amber-300 text-amber-800"
                              : "bg-emerald-100 border-emerald-300 text-emerald-800"
                        }`}>
                          {status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 3: Network Resource Intelligence */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-base font-black text-[#0C2B4E]">
                Network Resource Intelligence
              </h3>
              <p className="text-xs text-slate-500 font-mono">
                SKU-level stock availability, coverage velocity, and preliminary donor/recipient indicators.
              </p>
            </div>
            <div className="relative w-full sm:w-64 font-mono text-xs">
              <IconSearch size={14} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={resourceFilter}
                onChange={(e) => setResourceFilter(e.target.value)}
                placeholder="Filter resources/SKUs..."
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-slate-800 focus:outline-hidden focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 text-[10px] uppercase tracking-wider bg-slate-50/50">
                  <th className="py-2.5 px-3">Resource / SKU</th>
                  <th className="py-2.5 px-3 text-right">Network Stock</th>
                  <th className="py-2.5 px-3 text-right">Daily Demand</th>
                  <th className="py-2.5 px-3 text-right">Days Cover</th>
                  <th className="py-2.5 px-3 text-center">Below Safety</th>
                  <th className="py-2.5 px-3 text-center">Critical Nodes</th>
                  <th className="py-2.5 px-3">Potential Donors (Surplus)</th>
                  <th className="py-2.5 px-3">Potential Recipients (Deficit)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredResources.map((r) => (
                  <tr key={r.item_code} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-3">
                      <div className="font-bold text-slate-900 font-sans">{r.item_name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{r.item_code} • {r.category}</div>
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-slate-800">
                      {r.total_network_stock} {r.unit}
                    </td>
                    <td className="py-3 px-3 text-right text-slate-600">
                      {r.total_daily_demand} {r.unit}/day
                    </td>
                    <td className="py-3 px-3 text-right">
                      <span className={`font-black ${
                        r.network_days_of_cover < 7.0 ? "text-rose-700" : "text-emerald-700"
                      }`}>
                        {r.network_days_of_cover} days
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center font-bold">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        r.facilities_below_safety_count > 0 ? "bg-amber-100 text-amber-900" : "text-slate-400"
                      }`}>
                        {r.facilities_below_safety_count}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center font-bold">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        r.critical_facilities_count > 0 ? "bg-rose-100 text-rose-800 font-black" : "text-slate-400"
                      }`}>
                        {r.critical_facilities_count}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-[11px] text-emerald-800 font-sans">
                      {r.potential_donors.length > 0 ? (
                        <div className="space-y-0.5">
                          {r.potential_donors.map((d, i) => (
                            <div key={i} className="truncate max-w-[220px]">✓ {d}</div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-400 font-mono text-[10px]">None available</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-[11px] text-rose-800 font-sans">
                      {r.potential_recipients.length > 0 ? (
                        <div className="space-y-0.5">
                          {r.potential_recipients.map((rec, i) => (
                            <div key={i} className="truncate max-w-[220px]">⚠ {rec}</div>
                          ))}
                        </div>
                      ) : (
                        <span className="text-slate-400 font-mono text-[10px]">Buffer intact</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Section 4: Intervention Priority Queue */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              <h3 className="text-base font-black text-[#0C2B4E]">
                Operational Intervention Priority Queue
              </h3>
              <p className="text-xs text-slate-500 font-mono">
                Deterministic prioritization of facility-resource deficits requiring immediate CDMO action.
              </p>
            </div>
            <Link
              href="/recommendations"
              className="text-xs text-indigo-700 hover:text-indigo-900 font-mono font-bold flex items-center gap-1 self-start sm:self-auto"
            >
              Open Redistribution Queue <IconArrowRight size={14} />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-400 text-[10px] uppercase tracking-wider bg-slate-50/50">
                  <th className="py-2.5 px-3 text-center">Rank</th>
                  <th className="py-2.5 px-3">Facility</th>
                  <th className="py-2.5 px-3">District</th>
                  <th className="py-2.5 px-3">Resource</th>
                  <th className="py-2.5 px-3 text-right">Current Stock</th>
                  <th className="py-2.5 px-3 text-right">Days Cover</th>
                  <th className="py-2.5 px-3 text-center">Risk</th>
                  <th className="py-2.5 px-3 text-center">Stockout Date</th>
                  <th className="py-2.5 px-3">Operational Next Step</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data?.intervention_priority.map((item) => (
                  <tr key={`${item.facility_id}-${item.item_code}`} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-3 text-center font-black text-slate-900">
                      #{item.priority_rank}
                    </td>
                    <td className="py-3 px-3 font-bold text-slate-900 font-sans">
                      {item.facility_name}
                    </td>
                    <td className="py-3 px-3 text-slate-600">
                      {item.district}
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-bold text-slate-900 font-sans">{item.item_name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{item.item_code}</div>
                    </td>
                    <td className="py-3 px-3 text-right font-bold text-slate-800">
                      {item.current_stock} / {item.safety_stock}
                    </td>
                    <td className="py-3 px-3 text-right font-black text-rose-700">
                      {item.days_of_cover} days
                    </td>
                    <td className="py-3 px-3 text-center">
                      <span className={`text-[9px] font-black px-2 py-0.5 rounded uppercase border ${
                        item.risk_severity === "CRITICAL"
                          ? "bg-rose-100 border-rose-300 text-rose-800"
                          : "bg-amber-100 border-amber-300 text-amber-800"
                      }`}>
                        {item.risk_severity}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-center text-slate-600">
                      {item.projected_stockout_date || "Immediate"}
                    </td>
                    <td className="py-3 px-3 font-sans text-[11px]">
                      {item.has_pending_recommendation ? (
                        <span className="text-emerald-800 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          {item.suggested_action}
                        </span>
                      ) : (
                        <span className="text-slate-700">
                          {item.suggested_action}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer Disclaimer & Architecture Note */}
        <div className="bg-slate-100/70 border border-slate-200 p-4 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 font-mono">
          <div className="flex items-center gap-2">
            <IconShieldCheck size={18} className="text-[#1D546C] shrink-0" />
            <span>{data?.disclaimer || "Authoritative network intelligence aggregated from verified facility records. Strictly read-only."}</span>
          </div>
          <span className="text-[10px] text-slate-400">
            Cloud Run • BigQuery-Ready Aggregation Schema
          </span>
        </div>

      </div>
    </AppShell>
  );
}
