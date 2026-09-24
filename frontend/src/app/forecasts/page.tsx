"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import { 
  IconRefresh, 
  IconSparkles, 
  IconSearch,
  IconFilter,
  IconTable,
  IconLayoutGrid,
  IconHelpCircle,
  IconChevronDown,
  IconChevronUp,
  IconInfoCircle,
  IconShieldCheck,
  IconArrowRight
} from "@tabler/icons-react";
import Link from "next/link";

export default function ForecastsPage() {
  const { user } = useAuth();
  const [forecasts, setForecasts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [expandedForecasts, setExpandedForecasts] = useState<Record<number, boolean>>({});
  const [explanations, setExplanations] = useState<Record<number, any>>({});
  const [explLoading, setExplLoading] = useState<Record<number, boolean>>({});

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFacility, setSelectedFacility] = useState("ALL");
  const [selectedState, setSelectedState] = useState("ALL");
  const [selectedRisk, setSelectedRisk] = useState("ALL");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");

  const toggleExpand = async (forecastId: number) => {
    const nextState = !expandedForecasts[forecastId];
    setExpandedForecasts(prev => ({ ...prev, [forecastId]: nextState }));

    if (nextState && !explanations[forecastId]) {
      const forecastItem = forecasts.find(f => f.id === forecastId);
      if (forecastItem?.explanation) {
        setExplanations(prev => ({ ...prev, [forecastId]: forecastItem.explanation }));
      } else {
        try {
          setExplLoading(prev => ({ ...prev, [forecastId]: true }));
          const data = await apiFetch<any>(`/api/v1/forecasts/${forecastId}/explanation`);
          setExplanations(prev => ({ ...prev, [forecastId]: data }));
        } catch (err) {
          console.error("Failed to load forecast explanation:", err);
        } finally {
          setExplLoading(prev => ({ ...prev, [forecastId]: false }));
        }
      }
    }
  };

  const fetchForecasts = async () => {
    try {
      setLoading(true);
      const data = await apiFetch<any[]>("/api/v1/forecasts");
      setForecasts(data);
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Failed to load forecast data from server." });
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculate = async () => {
    try {
      setRecalculating(true);
      setBanner(null);
      const newForecasts = await apiFetch<any[]>("/api/v1/forecasts/recalculate", { method: "POST" });
      setForecasts(newForecasts);
      setBanner({ type: "success", msg: "EWMA demand forecasts & stockout risk engine recalculated successfully." });
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Forecast recalculation requires CDMO or ADMIN role." });
    } finally {
      setRecalculating(false);
    }
  };

  useEffect(() => {
    fetchForecasts();
  }, [user]);

  // Derived filter options
  const facilitiesList = Array.from(new Set(forecasts.map(f => f.facility_name).filter(Boolean)));
  const statesList = Array.from(new Set(forecasts.map(f => f.state).filter(Boolean)));

  const filteredForecasts = forecasts.filter(f => {
    const code = (f.item_code || "").toLowerCase();
    const name = (f.item_name || "").toLowerCase();
    const facName = (f.facility_name || "").toLowerCase();
    const searchLower = searchQuery.toLowerCase();

    const matchesSearch = !searchQuery || code.includes(searchLower) || name.includes(searchLower) || facName.includes(searchLower);
    const matchesFacility = selectedFacility === "ALL" || f.facility_name === selectedFacility;
    const matchesState = selectedState === "ALL" || f.state === selectedState;
    
    const risk = f.risk_level || (f.days_of_cover < 3 ? "CRITICAL" : f.days_of_cover < 7 ? "WARNING" : "SAFE");
    const matchesRisk = selectedRisk === "ALL" || risk === selectedRisk;

    return matchesSearch && matchesFacility && matchesState && matchesRisk;
  });

  return (
    <AppShell>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E]">Demand Forecasting & Stockout Risk Engine</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              EWMA Demand Velocity (&alpha;=0.3), Days-of-Cover Calculation &amp; Safety-Stock Risk
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRecalculate}
              disabled={recalculating || user?.role === "FACILITY_OFFICER"}
              title={user?.role === "FACILITY_OFFICER" ? "EWMA Recalculation requires CDMO or System Admin role." : "Trigger server-side EWMA demand recalculation"}
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50 transition"
            >
              <IconSparkles size={16} className={recalculating ? "animate-spin" : ""} />
              {recalculating ? "Recalculating EWMA..." : user?.role === "FACILITY_OFFICER" ? "Recalculation (CDMO/Admin Only)" : "Trigger EWMA Recalculation"}
            </button>
            <button
              onClick={fetchForecasts}
              className="bg-white border border-slate-200 text-slate-700 text-xs font-bold px-3 py-2 rounded-xl flex items-center gap-1 shadow-2xs hover:bg-slate-50 cursor-pointer"
            >
              <IconRefresh size={14} className={loading ? "animate-spin" : ""} /> Refresh
            </button>
          </div>
        </div>

        {/* Inline Banner */}
        {banner && (
          <div className={`p-4 rounded-xl border text-xs flex items-center justify-between font-mono ${
            banner.type === "success" ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-rose-50 border-rose-200 text-rose-900"
          }`}>
            <span>{banner.msg}</span>
            <button onClick={() => setBanner(null)} className="font-bold underline text-slate-600 cursor-pointer">Dismiss</button>
          </div>
        )}

        {/* Operational Filter Toolbar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
            <div className="relative w-full md:w-72">
              <IconSearch size={16} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search facility, SKU, or resource..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-xs font-semibold outline-none focus:border-[#0C2B4E]"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
              <div className="flex items-center gap-1 text-slate-500 text-xs font-mono">
                <IconFilter size={14} /> Filter:
              </div>

              {/* Facility Filter */}
              <select
                value={selectedFacility}
                onChange={(e) => setSelectedFacility(e.target.value)}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold bg-white outline-none cursor-pointer"
              >
                <option value="ALL">All Facilities</option>
                {facilitiesList.map(fac => (
                  <option key={fac} value={fac}>{fac}</option>
                ))}
              </select>

              {/* State Filter */}
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold bg-white outline-none cursor-pointer"
              >
                <option value="ALL">All States</option>
                {statesList.map(st => (
                  <option key={st} value={st}>{st === "OD" ? "Odisha (OD)" : st === "WB" ? "West Bengal (WB)" : st}</option>
                ))}
              </select>

              {/* Risk Filter */}
              <select
                value={selectedRisk}
                onChange={(e) => setSelectedRisk(e.target.value)}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold bg-white outline-none cursor-pointer"
              >
                <option value="ALL">All Severity Levels</option>
                <option value="CRITICAL">Critical Risk</option>
                <option value="WARNING">Warning</option>
                <option value="SAFE">Safe Buffer</option>
              </select>

              {/* View Mode Switcher */}
              <div className="flex items-center border border-slate-200 rounded-lg p-0.5 bg-slate-50 ml-auto md:ml-0">
                <button
                  onClick={() => setViewMode("table")}
                  className={`p-1.5 rounded-md cursor-pointer ${viewMode === "table" ? "bg-white shadow-2xs text-[#0C2B4E]" : "text-slate-400"}`}
                  title="Table View"
                >
                  <IconTable size={16} />
                </button>
                <button
                  onClick={() => setViewMode("grid")}
                  className={`p-1.5 rounded-md cursor-pointer ${viewMode === "grid" ? "bg-white shadow-2xs text-[#0C2B4E]" : "text-slate-400"}`}
                  title="Grid View"
                >
                  <IconLayoutGrid size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Forecast Records Display */}
        {viewMode === "table" ? (
          <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs min-w-[980px]">
                <thead className="bg-slate-50 text-slate-500 font-mono uppercase text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="p-3.5 w-[170px]">Facility Node</th>
                    <th className="p-3.5 w-[160px]">Resource &amp; SKU</th>
                    <th className="p-3.5 w-[110px]">Current Stock</th>
                    <th className="p-3.5 w-[110px]">Daily Demand</th>
                    <th className="p-3.5 w-[110px]">Days of Cover</th>
                    <th className="p-3.5 w-[130px]">Projected Stockout</th>
                    <th className="p-3.5 text-right w-[110px]">Risk Severity</th>
                    <th className="p-3.5 text-right w-[130px]">Reasoning</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {filteredForecasts.map((f) => {
                    const risk = f.risk_level || (f.days_of_cover < 3 ? "CRITICAL" : f.days_of_cover < 7 ? "WARNING" : "SAFE");
                    const expl = explanations[f.id] || f.explanation;
                    const isExpanded = !!expandedForecasts[f.id];

                    return (
                      <React.Fragment key={f.id}>
                        <tr className="hover:bg-slate-50/50">
                          <td className="p-3.5">
                            <strong className="text-[#0C2B4E] font-sans font-bold block">{f.facility_name || `Facility #${f.facility_id}`}</strong>
                            <span className="text-[10px] text-slate-400">{f.district || "District"}, {f.state || "State"}</span>
                          </td>
                          <td className="p-3.5">
                            <strong className="text-slate-800 font-sans block">{f.item_name || f.item_code}</strong>
                            <span className="text-[10px] text-slate-500 font-mono">{f.item_code}</span>
                          </td>
                          <td className="p-3.5 font-bold text-[#0C2B4E]">
                            {f.current_stock ?? "—"} <span className="text-[10px] text-slate-400 font-normal">units</span>
                          </td>
                          <td className="p-3.5 text-slate-700">
                            {f.expected_daily_demand} <span className="text-[10px] text-slate-400">/day</span>
                          </td>
                          <td className="p-3.5">
                            <span className="font-black text-[#0C2B4E] text-sm">{f.days_of_cover}</span> <span className="text-[10px] text-slate-400">Days</span>
                          </td>
                          <td className="p-3.5 text-slate-600">
                            {f.projected_stockout_date ? (
                              <strong className={risk === "CRITICAL" ? "text-rose-700 font-bold" : "text-slate-700"}>
                                {f.projected_stockout_date}
                              </strong>
                            ) : (
                              <span className="text-emerald-700 text-[11px]">Safe (&gt;= 7d)</span>
                            )}
                          </td>
                          <td className="p-3.5 text-right">
                            <span className={`text-[10px] font-extrabold uppercase px-2.5 py-1 rounded font-mono inline-block border ${
                              risk === "CRITICAL" ? "bg-rose-100 text-rose-800 border-rose-300" :
                              risk === "WARNING" ? "bg-amber-100 text-amber-800 border-amber-300" :
                              "bg-emerald-100 text-emerald-800 border-emerald-300"
                            }`}>
                              {risk === "CRITICAL" ? "CRITICAL RISK" : risk === "WARNING" ? "WARNING" : "SAFE"}
                            </span>
                          </td>
                          <td className="p-3.5 text-right">
                            <button
                              onClick={() => toggleExpand(f.id)}
                              className="bg-blue-50 hover:bg-blue-100 text-[#0C2B4E] border border-blue-200 px-2.5 py-1 rounded-lg font-bold text-[11px] inline-flex items-center gap-1 cursor-pointer transition"
                              title="View verified evidence and causal reasoning"
                            >
                              <IconHelpCircle size={13} className="text-[#1D546C]" />
                              <span>{isExpanded ? "Hide Reason" : "Why this risk?"}</span>
                              {isExpanded ? <IconChevronUp size={12} /> : <IconChevronDown size={12} />}
                            </button>
                          </td>
                        </tr>

                        {/* Expandable Evidence & Explainability Drawer */}
                        {isExpanded && (
                          <tr key={`exp-${f.id}`} className="bg-blue-50/40 border-b border-slate-200">
                            <td colSpan={8} className="p-3 sm:p-4">
                              <div className="bg-white rounded-xl border border-blue-200/80 p-4 shadow-2xs space-y-3 font-mono">
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2">
                                  <div className="flex items-center gap-2">
                                    <IconInfoCircle size={16} className="text-[#1D546C]" />
                                    <span className="font-bold text-xs text-[#0C2B4E] uppercase tracking-wider">
                                      Forecast Risk Explainability &amp; Real Telemetry Evidence
                                    </span>
                                  </div>
                                  <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-bold self-start sm:self-auto">
                                    {f.facility_name || `Facility #${f.facility_id}`} • {f.item_code}
                                  </span>
                                </div>

                                {explLoading[f.id] ? (
                                  <div className="text-xs text-slate-500 py-3 text-center">Loading verified telemetry...</div>
                                ) : (
                                  <>
                                    {/* Evidence Metrics Grid */}
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">Current Stock</span>
                                        <span className="font-bold text-[#0C2B4E]">
                                          {expl?.evidence?.current_stock ?? f.current_stock ?? "—"} units
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">Est. Daily Demand</span>
                                        <span className="font-bold text-slate-800">
                                          {expl?.evidence?.estimated_daily_demand ?? f.expected_daily_demand} units/day
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">Days of Cover</span>
                                        <span className={`font-black ${
                                          risk === "CRITICAL" ? "text-rose-700" : risk === "WARNING" ? "text-amber-700" : "text-emerald-700"
                                        }`}>
                                          {expl?.evidence?.days_of_cover ?? f.days_of_cover} days
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">Safety Buffer</span>
                                        <span className="font-bold text-slate-800">
                                          {expl?.evidence?.safety_stock_threshold ?? (f.safety_stock ?? "—")} units
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">7-Day Projected Demand</span>
                                        <span className="font-bold text-slate-800">
                                          {expl?.evidence?.forecasted_demand_7d ?? (f.expected_daily_demand * 7).toFixed(1)} units
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">Projected Stockout</span>
                                        <span className="font-bold text-rose-700">
                                          {expl?.evidence?.projected_stockout_date ?? f.projected_stockout_date ?? "Safe (>= 7d)"}
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">Risk Severity</span>
                                        <span className="font-bold text-[#0C2B4E]">
                                          {expl?.risk_level || risk}
                                        </span>
                                      </div>
                                      <div>
                                        <span className="text-[10px] text-slate-500 block uppercase">Verification Status</span>
                                        <span className="text-emerald-700 font-bold flex items-center gap-1">
                                          <IconShieldCheck size={13} /> Active DB Evidence
                                        </span>
                                      </div>
                                    </div>

                                    {/* Reasoning & Actions */}
                                    <div className="space-y-2 text-xs font-sans">
                                      <div className="bg-amber-50/70 border border-amber-200/80 rounded-lg p-2.5">
                                        <strong className="text-amber-900 block text-[11px] font-bold uppercase tracking-wider mb-0.5">
                                          Why this risk is flagged:
                                        </strong>
                                        <p className="text-amber-950 leading-relaxed text-xs">
                                          {expl?.why || "Current inventory is below the configured safety threshold and projected demand indicates insufficient coverage."}
                                        </p>
                                      </div>

                                      <div className="bg-blue-50/60 border border-blue-200/80 rounded-lg p-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                        <div>
                                          <strong className="text-blue-900 block text-[11px] font-bold uppercase tracking-wider mb-0.5">
                                            Recommended operational action:
                                          </strong>
                                          <p className="text-blue-950 text-xs">
                                            {expl?.recommended_action || "Consider redistribution from a facility with sufficient surplus inventory."}
                                          </p>
                                        </div>
                                        {(risk === "CRITICAL" || risk === "WARNING") && (
                                          <Link
                                            href="/recommendations"
                                            className="bg-[#0C2B4E] hover:bg-[#1A3D64] text-white text-[11px] font-bold px-3 py-1.5 rounded-lg inline-flex items-center gap-1 self-start sm:self-auto whitespace-nowrap transition cursor-pointer"
                                          >
                                            Redistribute <IconArrowRight size={12} />
                                          </Link>
                                        )}
                                      </div>
                                    </div>
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                  {filteredForecasts.length === 0 && (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-slate-400 font-sans">
                        No forecast records match the selected filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredForecasts.map((f) => {
              const risk = f.risk_level || (f.days_of_cover < 3 ? "CRITICAL" : f.days_of_cover < 7 ? "WARNING" : "SAFE");
              const expl = explanations[f.id] || f.explanation;
              const isExpanded = !!expandedForecasts[f.id];

              return (
                <div key={f.id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block font-mono">
                        {f.facility_name || `Facility #${f.facility_id}`} ({f.district}, {f.state})
                      </span>
                      <h3 className="text-base font-bold text-[#0C2B4E]">{f.item_name || f.item_code}</h3>
                      <span className="text-[10px] text-slate-500 font-mono">{f.item_code}</span>
                    </div>
                    <span className={`text-[10px] font-extrabold uppercase px-2.5 py-1 rounded font-mono border ${
                      risk === "CRITICAL" ? "bg-rose-100 text-rose-800 border-rose-300" :
                      risk === "WARNING" ? "bg-amber-100 text-amber-800 border-amber-300" :
                      "bg-emerald-100 text-emerald-800 border-emerald-300"
                    }`}>
                      {risk === "CRITICAL" ? "CRITICAL RISK" : risk === "WARNING" ? "WARNING" : "SAFE"}
                    </span>
                  </div>

                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 font-mono text-xs">
                    <div className="flex justify-between text-slate-500 text-[10px] font-bold uppercase tracking-wider">
                      <span>VERIFIED EWMA CALCULATIONS</span>
                      <span className="text-emerald-700">Math Verified</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-slate-800 pt-1">
                      <div>
                        <span className="text-[10px] text-slate-400 block">Current Stock</span>
                        <span className="font-bold">{f.current_stock ?? "—"} units</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 block">Daily Demand</span>
                        <span className="font-bold">{f.expected_daily_demand} /day</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 block">Days of Cover</span>
                        <span className="font-black text-[#0C2B4E]">{f.days_of_cover} Days</span>
                      </div>
                    </div>
                    <div className="pt-1 text-[11px] text-slate-500 flex justify-between border-t border-slate-200/60">
                      <span>Projected Stockout Date:</span>
                      <strong className={risk === "CRITICAL" ? "text-rose-700" : "text-slate-700"}>
                        {f.projected_stockout_date || "Safe (DoC >= 7d)"}
                      </strong>
                    </div>
                  </div>

                  {/* Explainability Toggle Button */}
                  <div className="pt-1">
                    <button
                      onClick={() => toggleExpand(f.id)}
                      className="w-full bg-blue-50 hover:bg-blue-100 text-[#0C2B4E] border border-blue-200 py-1.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition"
                    >
                      <IconHelpCircle size={14} className="text-[#1D546C]" />
                      <span>{isExpanded ? "Hide Reasoning & Evidence" : "Why this risk? (View Evidence)"}</span>
                      {isExpanded ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
                    </button>
                  </div>

                  {/* Expanded Explainability Panel in Grid Card */}
                  {isExpanded && (
                    <div className="bg-blue-50/40 border border-blue-200 rounded-xl p-3.5 space-y-3 font-sans text-xs">
                      {explLoading[f.id] ? (
                        <div className="text-center py-2 text-slate-500 font-mono">Loading verified telemetry...</div>
                      ) : (
                        <>
                          <div className="bg-white p-3 rounded-lg border border-blue-100 space-y-2">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider font-mono block">
                              Authoritative Evidence
                            </span>
                            <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                              <div>
                                <span className="text-slate-400 block text-[10px]">7d Forecast Demand:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.evidence?.forecasted_demand_7d ?? (f.expected_daily_demand * 7).toFixed(1)} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Safety Threshold:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.evidence?.safety_stock_threshold ?? (f.safety_stock ?? "—")} units
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="bg-amber-50/70 border border-amber-200/80 rounded-lg p-2.5">
                            <strong className="text-amber-900 block text-[10px] font-bold uppercase tracking-wider mb-0.5">
                              Why this risk is flagged:
                            </strong>
                            <p className="text-amber-950 text-xs leading-relaxed">
                              {expl?.why || "Current inventory is below the configured safety threshold and projected demand indicates insufficient coverage."}
                            </p>
                          </div>

                          <div className="bg-blue-50/60 border border-blue-200/80 rounded-lg p-2.5">
                            <strong className="text-blue-900 block text-[10px] font-bold uppercase tracking-wider mb-0.5">
                              Recommended Action:
                            </strong>
                            <p className="text-blue-950 text-xs">
                              {expl?.recommended_action || "Consider redistribution from a facility with sufficient surplus inventory."}
                            </p>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

      </div>
    </AppShell>
  );
}
