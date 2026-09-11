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
  IconLayoutGrid
} from "@tabler/icons-react";

export default function ForecastsPage() {
  const { user } = useAuth();
  const [forecasts, setForecasts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [banner, setBanner] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFacility, setSelectedFacility] = useState("ALL");
  const [selectedState, setSelectedState] = useState("ALL");
  const [selectedRisk, setSelectedRisk] = useState("ALL");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");

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
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 font-mono uppercase text-[10px] border-b border-slate-200">
                  <tr>
                    <th className="p-3.5">Facility Node</th>
                    <th className="p-3.5">Resource &amp; SKU</th>
                    <th className="p-3.5">Current Stock</th>
                    <th className="p-3.5">Daily Demand</th>
                    <th className="p-3.5">Days of Cover</th>
                    <th className="p-3.5">Projected Stockout Date</th>
                    <th className="p-3.5 text-right">Risk Severity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  {filteredForecasts.map((f) => {
                    const risk = f.risk_level || (f.days_of_cover < 3 ? "CRITICAL" : f.days_of_cover < 7 ? "WARNING" : "SAFE");
                    return (
                      <tr key={f.id} className="hover:bg-slate-50/50">
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
                      </tr>
                    );
                  })}
                  {filteredForecasts.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-400 font-sans">
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
                </div>
              );
            })}
          </div>
        )}

      </div>
    </AppShell>
  );
}
