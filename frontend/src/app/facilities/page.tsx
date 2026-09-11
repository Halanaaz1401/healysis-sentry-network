"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch, ApiError } from "@/lib/apiClient";
import { 
  IconBuildingHospital, 
  IconMapPin, 
  IconSearch, 
  IconFilter, 
  IconLock, 
  IconArrowRight,
  IconRefresh,
  IconAlertCircle
} from "@tabler/icons-react";

export default function FacilitiesPage() {
  const { user } = useAuth();
  const [facilities, setFacilities] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<string>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFacilities = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<any[]>("/api/v1/facilities");
      setFacilities(data);
    } catch (err: any) {
      console.error("Fetch facilities error:", err);
      setError(err.message || "Failed to load healthcare facilities from server.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFacilities();
  }, [user]);

  const filteredFacilities = facilities.filter((f) => {
    const nameStr = f.name || "";
    const distStr = f.district || "";
    const matchesSearch = nameStr.toLowerCase().includes(searchQuery.toLowerCase()) || distStr.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesState = stateFilter === "ALL" || f.state === stateFilter;
    return matchesSearch && matchesState;
  });

  return (
    <AppShell>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E]">Regional Healthcare Facilities</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Odisha & West Bengal Healthcare Care Nodes & Operational Risk Profiles
            </p>
          </div>

          <div className="flex items-center gap-3">
            {user && user.role === "FACILITY_OFFICER" && (
              <div className="bg-blue-50 border border-blue-200 text-blue-900 text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-bold">
                <IconLock size={14} className="text-blue-700" />
                <span>Scope: {user.facility_name}</span>
              </div>
            )}
            <button
              onClick={fetchFacilities}
              className="text-xs text-slate-600 hover:text-[#0C2B4E] bg-white border border-slate-200 px-3 py-1.5 rounded-lg flex items-center gap-1 font-bold shadow-2xs cursor-pointer"
            >
              <IconRefresh size={14} className={loading ? "animate-spin" : ""} /> Refresh
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl text-rose-900 text-xs flex items-center justify-between font-mono">
            <div className="flex items-center gap-2">
              <IconAlertCircle size={16} className="text-rose-600 shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={fetchFacilities} className="font-bold underline text-slate-600">Retry</button>
          </div>
        )}

        {/* Search & Filters */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="relative w-full sm:w-80">
            <IconSearch size={16} className="absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search facility name or district..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-xs font-semibold outline-none focus:border-[#0C2B4E]"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <IconFilter size={16} className="text-slate-400" />
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2 text-xs font-bold text-[#0C2B4E] bg-white outline-none cursor-pointer"
            >
              <option value="ALL">All States (OD & WB)</option>
              <option value="OD">Odisha (OD)</option>
              <option value="WB">West Bengal (WB)</option>
            </select>
          </div>
        </div>

        {/* Facilities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredFacilities.map((fac) => {
            const riskSev = fac.risk_status || (fac.id === 1 ? "CRITICAL" : fac.id === 4 ? "WARNING" : "SAFE");
            const isAccessible = !user || user.role !== "FACILITY_OFFICER" || user.facility_id === fac.id;

            const CardContent = (
              <div className={`bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4 transition block ${
                isAccessible ? "hover:border-[#1D546C] hover:shadow-xs cursor-pointer group" : "opacity-80 bg-slate-50/50"
              }`}>
                {/* PRIMARY HIERARCHY */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-base font-bold text-[#0C2B4E] group-hover:text-[#1D546C] transition flex items-center gap-1.5">
                      <IconBuildingHospital size={18} className="text-[#1D546C] shrink-0" />
                      {fac.name}
                    </h3>
                    <div className="flex items-center gap-1 text-xs text-slate-600 font-medium mt-1">
                      <IconMapPin size={14} className="text-slate-400 shrink-0" />
                      <span>{fac.district}, {fac.state} ({fac.facility_type} Node)</span>
                    </div>
                  </div>
                  <span className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded border shrink-0 ${
                    riskSev === "CRITICAL" ? "bg-rose-100 text-rose-800 border-rose-300" :
                    riskSev === "WARNING" ? "bg-amber-100 text-amber-800 border-amber-300" :
                    "bg-emerald-100 text-emerald-800 border-emerald-300"
                  }`}>
                    {riskSev}
                  </span>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-700">Operational Profile:</span>
                  {isAccessible ? (
                    <span className="text-[#1D546C] font-bold group-hover:underline flex items-center gap-1">
                      View Profile <IconArrowRight size={14} />
                    </span>
                  ) : (
                    <span className="text-slate-400 font-bold flex items-center gap-1">
                      <IconLock size={12} /> Restricted Scope
                    </span>
                  )}
                </div>

                {/* SECONDARY HIERARCHY */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Code: {fac.facility_code}</span>
                  <span>{fac.latitude}° N, {fac.longitude}° E</span>
                </div>
              </div>
            );

            return isAccessible ? (
              <Link key={fac.id} href={`/facilities/${fac.id}`}>
                {CardContent}
              </Link>
            ) : (
              <div key={fac.id} title={`Access restricted. Your scope is assigned to ${user?.facility_name}.`}>
                {CardContent}
              </div>
            );
          })}
        </div>

      </div>
    </AppShell>
  );
}
