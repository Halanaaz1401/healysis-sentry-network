"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch, ApiError } from "@/lib/apiClient";
import { 
  IconBuildingHospital, 
  IconMapPin, 
  IconUserCheck, 
  IconBed, 
  IconStethoscope, 
  IconPackage, 
  IconAlertOctagon, 
  IconTrendingUp,
  IconArrowLeft,
  IconLock,
  IconAlertCircle,
  IconCircleCheck
} from "@tabler/icons-react";

export default function FacilityDetailPage() {
  const params = useParams();
  const facilityId = params?.id as string;
  const { user } = useAuth();
  
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorObj, setErrorObj] = useState<{ status: number; msg: string } | null>(null);

  const fetchFacilityDetails = async () => {
    try {
      setLoading(true);
      setErrorObj(null);
      
      const json = await apiFetch<any>(`/api/v1/facilities/${facilityId}`);
      setData(json);
    } catch (err: any) {
      console.error("Facility detail fetch error:", err);
      if (err instanceof ApiError) {
        setErrorObj({ status: err.status, msg: err.detail });
      } else {
        setErrorObj({ status: 500, msg: err.message || "Failed to connect to backend server." });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (facilityId) {
      fetchFacilityDetails();
    }
  }, [facilityId, user]);

  if (loading) {
    return (
      <AppShell>
        <div className="p-12 text-center space-y-3">
          <div className="inline-block animate-spin text-[#0C2B4E]">
            <IconBuildingHospital size={32} />
          </div>
          <p className="text-xs font-mono font-bold text-slate-500">Loading Facility Operational Profile...</p>
        </div>
      </AppShell>
    );
  }

  if (errorObj) {
    const is403 = errorObj.status === 403;
    const is404 = errorObj.status === 404;

    return (
      <AppShell>
        <div className="space-y-4 max-w-4xl mx-auto">
          <Link href="/facilities" className="inline-flex items-center gap-1 text-xs font-bold text-[#1D546C] hover:underline">
            <IconArrowLeft size={14} /> Back to Facilities Catalog
          </Link>

          <div className={`p-6 rounded-2xl space-y-3 border ${
            is403 ? "bg-amber-50 border-amber-200 text-amber-900" :
            is404 ? "bg-slate-50 border-slate-200 text-slate-900" :
            "bg-rose-50 border-rose-200 text-rose-900"
          }`}>
            <div className="flex items-center gap-2 font-extrabold text-sm">
              {is403 && <IconLock size={20} className="text-amber-700" />}
              {is404 && <IconAlertCircle size={20} className="text-slate-600" />}
              {!is403 && !is404 && <IconAlertOctagon size={20} className="text-rose-700" />}
              <span>
                {is403 ? "Access Restricted (HTTP 403 Forbidden)" :
                 is404 ? "Facility Not Found (HTTP 404 Not Found)" :
                 `Server Error (HTTP ${errorObj.status})`}
              </span>
            </div>
            <p className="text-xs font-mono leading-relaxed">{errorObj.msg}</p>

            {is403 && user?.facility_id && (
              <div className="pt-2">
                <Link
                  href={`/facilities/${user.facility_id}`}
                  className="bg-[#0C2B4E] text-white text-xs font-bold px-4 py-2 rounded-xl inline-flex items-center gap-1.5 shadow-xs"
                >
                  <IconBuildingHospital size={14} /> Open My Assigned Facility Profile (#{user.facility_id})
                </Link>
              </div>
            )}
          </div>
        </div>
      </AppShell>
    );
  }

  const fac = data?.facility || {};
  const officers = data?.assigned_officers || [];
  const capacity = data?.capacity || {};
  const personnel = data?.personnel || {};
  const inventory = data?.inventory || [];
  const alerts = data?.active_alerts || [];
  const forecasts = data?.forecasts || [];

  return (
    <AppShell>
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-1 duration-200">
        
        {/* Navigation Breadcrumb */}
        <div className="flex items-center justify-between">
          <Link href="/facilities" className="inline-flex items-center gap-1.5 text-xs font-bold text-[#1D546C] hover:underline">
            <IconArrowLeft size={16} /> Back to Facilities Catalog
          </Link>
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider">
            FACILITY NODE ID: #{fac.id}
          </span>
        </div>

        {/* HERO SECTION: FACILITY INFORMATION */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <div className="inline-flex items-center gap-1.5 text-[10px] font-mono font-bold text-[#1D546C] uppercase bg-slate-100 px-2.5 py-0.5 rounded-full mb-1">
                <IconBuildingHospital size={12} /> {fac.facility_type} NODE | CODE: {fac.facility_code}
              </div>
              <h1 className="text-2xl md:text-3xl font-black text-[#0C2B4E]">{fac.name}</h1>
              <div className="flex items-center gap-2 text-xs text-slate-600 font-medium mt-1">
                <IconMapPin size={14} className="text-slate-400 shrink-0" />
                <span>{fac.district}, {fac.state} ({fac.latitude}° N, {fac.longitude}° E)</span>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-xl flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                {fac.status || "OPERATIONAL"}
              </span>
            </div>
          </div>

          {/* FACILITY OFFICER ROSTER */}
          <div className="flex flex-wrap items-center gap-3 font-mono text-xs">
            <span className="text-slate-400 font-bold">Assigned Facility Officers:</span>
            {officers.length === 0 ? (
              <span className="text-slate-500 italic">None assigned</span>
            ) : (
              officers.map((o: any) => (
                <span key={o.id} className="bg-slate-50 border border-slate-200 px-3 py-1 rounded-lg text-slate-700 font-semibold flex items-center gap-1.5">
                  <IconUserCheck size={14} className="text-[#1D546C]" />
                  <span>{o.full_name} ({o.role})</span>
                  <span className="text-[10px] text-slate-400">· {o.email}</span>
                </span>
              ))
            )}
          </div>
        </div>

        {/* HEALTHCARE CAPACITY & PERSONNEL */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Healthcare Bed Capacity Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-sm font-bold text-[#0C2B4E] flex items-center gap-2">
                <IconBed size={18} className="text-[#1D546C]" />
                Healthcare Bed Capacity
              </h2>
              <span className="text-xs font-mono font-bold text-[#0C2B4E] bg-slate-100 px-2.5 py-0.5 rounded">
                Occupancy: {capacity.occupancy_rate_pct || 50}%
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center font-mono">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">General</span>
                <span className="text-base font-black text-[#0C2B4E]">{capacity.general_occupied}/{capacity.general_capacity}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">ICU</span>
                <span className="text-base font-black text-[#0C2B4E]">{capacity.icu_occupied}/{capacity.icu_capacity}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">Oxygen</span>
                <span className="text-base font-black text-[#0C2B4E]">{capacity.oxygen_occupied}/{capacity.oxygen_capacity}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">Isolation</span>
                <span className="text-base font-black text-[#0C2B4E]">{capacity.isolation_occupied}/{capacity.isolation_capacity}</span>
              </div>
            </div>
          </div>

          {/* Personnel Roster Card */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-sm font-bold text-[#0C2B4E] flex items-center gap-2">
                <IconStethoscope size={18} className="text-[#1D546C]" />
                Medical Staff & Personnel
              </h2>
              <span className="text-xs font-mono font-bold text-[#0C2B4E] bg-slate-100 px-2.5 py-0.5 rounded">
                Total Staff: {personnel.total_staff || 25}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center font-mono">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">Doctors</span>
                <span className="text-base font-black text-[#0C2B4E]">{personnel.doctors_count || 3}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">Nurses</span>
                <span className="text-base font-black text-[#0C2B4E]">{personnel.nurses_count || 8}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">Pharmacists</span>
                <span className="text-base font-black text-[#0C2B4E]">{personnel.pharmacists_count || 2}</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-[9px] text-slate-400 uppercase block">ASHA Workers</span>
                <span className="text-base font-black text-[#0C2B4E]">{personnel.asha_count || 12}</span>
              </div>
            </div>
          </div>

        </div>

        {/* RESOURCE INVENTORY TABLE */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-[#0C2B4E] flex items-center gap-2">
              <IconPackage size={18} className="text-[#1D546C]" />
              Resource Inventory Status ({inventory.length} SKUs)
            </h2>
            <Link href="/resources" className="text-xs font-bold text-[#1D546C] hover:underline">
              Open Inventory Catalog &rarr;
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-mono uppercase text-[10px] border-b border-slate-200">
                <tr>
                  <th className="p-3">SKU Code</th>
                  <th className="p-3">Resource Name</th>
                  <th className="p-3">Current Stock</th>
                  <th className="p-3">Safety Stock</th>
                  <th className="p-3">Incoming</th>
                  <th className="p-3">Unit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {inventory.map((inv: any) => (
                  <tr key={inv.id} className="hover:bg-slate-50/50">
                    <td className="p-3 font-bold text-[#0C2B4E]">{inv.item_code}</td>
                    <td className="p-3 font-sans font-semibold text-slate-800">{inv.item_name}</td>
                    <td className="p-3 font-black text-[#0C2B4E]">{inv.quantity}</td>
                    <td className="p-3 text-slate-600">{inv.safety_stock}</td>
                    <td className="p-3 text-emerald-700">+{inv.incoming_quantity}</td>
                    <td className="p-3 text-slate-500">{inv.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ACTIVE ALERTS & FORECASTS */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Active Alerts */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
            <h2 className="text-sm font-bold text-[#0C2B4E] flex items-center gap-2 border-b border-slate-100 pb-3">
              <IconAlertOctagon size={18} className="text-rose-600" />
              Active Early Warning Alerts ({alerts.length})
            </h2>

            {alerts.length === 0 ? (
              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center gap-2">
                <IconCircleCheck size={18} className="text-emerald-600 shrink-0" />
                <span>No active critical alerts for {fac.name}.</span>
              </div>
            ) : (
              <div className="space-y-3">
                {alerts.map((a: any) => (
                  <div key={a.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[#0C2B4E]">{a.title}</span>
                      <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded ${
                        a.severity === "CRITICAL" ? "bg-rose-100 text-rose-800" : "bg-amber-100 text-amber-800"
                      }`}>
                        {a.severity}
                      </span>
                    </div>
                    <p className="text-[11px] font-mono text-slate-500">Resource: {a.resource_id}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Demand Forecasts */}
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
            <h2 className="text-sm font-bold text-[#0C2B4E] flex items-center gap-2 border-b border-slate-100 pb-3">
              <IconTrendingUp size={18} className="text-[#1D546C]" />
              Verified Demand Forecasts ({forecasts.length})
            </h2>

            <div className="space-y-3">
              {forecasts.map((f: any) => (
                <div key={f.id} className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between text-xs font-mono">
                  <div>
                    <span className="font-bold text-[#0C2B4E] block">{f.item_code}</span>
                    <span className="text-[11px] text-slate-500">Demand: {f.expected_daily_demand}/day</span>
                  </div>
                  <div className="text-right">
                    <span className={`font-bold block ${f.days_of_cover < 3 ? "text-rose-600" : f.days_of_cover < 7 ? "text-amber-600" : "text-emerald-700"}`}>
                      {f.days_of_cover} Days of Cover
                    </span>
                    <span className="text-[10px] text-slate-400">Stockout: {f.projected_stockout_date || "Safe"}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </AppShell>
  );
}
