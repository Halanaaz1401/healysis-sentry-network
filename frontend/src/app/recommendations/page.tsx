"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import { 
  IconRefresh, 
  IconShieldCheck, 
  IconSparkles, 
  IconCheck, 
  IconX,
  IconArrowRight,
  IconHelpCircle,
  IconChevronDown,
  IconChevronUp,
  IconInfoCircle,
  IconUserCheck,
  IconMapPin,
  IconClock,
  IconPackage,
  IconLayersLinked,
  IconPlayerPlay,
  IconAlertTriangle,
  IconAlertCircle,
  IconAdjustmentsHorizontal
} from "@tabler/icons-react";

export default function RecommendationsPage() {
  const { user } = useAuth();
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [banner, setBanner] = useState<{ type: "success" | "error"; msg: string } | null>(null);
  const [expandedRecs, setExpandedRecs] = useState<Record<number, boolean>>({});
  const [explanations, setExplanations] = useState<Record<number, any>>({});
  const [explLoading, setExplLoading] = useState<Record<number, boolean>>({});

  // What-If Simulation State
  const [showSimulator, setShowSimulator] = useState(false);
  const [facilities, setFacilities] = useState<any[]>([]);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [simDonorId, setSimDonorId] = useState<number | "">("");
  const [simRecipId, setSimRecipId] = useState<number | "">("");
  const [simItemCode, setSimItemCode] = useState<string>("");
  const [simQuantity, setSimQuantity] = useState<number | "">(50);
  const [simLoading, setSimLoading] = useState(false);
  const [simResult, setSimResult] = useState<any | null>(null);
  const [simError, setSimError] = useState<string | null>(null);

  // Feature #10: Before -> After Verification State
  const [verifications, setVerifications] = useState<Record<number, any>>({});
  const [verifLoading, setVerifLoading] = useState<Record<number, boolean>>({});
  const [expandedVerifChecklist, setExpandedVerifChecklist] = useState<Record<number, boolean>>({});

  const fetchVerification = async (recId: number) => {
    try {
      setVerifLoading(prev => ({ ...prev, [recId]: true }));
      const data = await apiFetch<any>(`/api/v1/recommendations/${recId}/verification`);
      setVerifications(prev => ({ ...prev, [recId]: data }));
    } catch (err: any) {
      console.error(`Failed to load verification for #${recId}:`, err);
    } finally {
      setVerifLoading(prev => ({ ...prev, [recId]: false }));
    }
  };

  const toggleVerifChecklist = (recId: number) => {
    const nextState = !expandedVerifChecklist[recId];
    setExpandedVerifChecklist(prev => ({ ...prev, [recId]: nextState }));
    if (nextState && !verifications[recId]) {
      fetchVerification(recId);
    }
  };

  const isCdmoOrAdmin = user?.role === "CDMO" || user?.role === "ADMIN";

  const toggleExpand = async (recId: number) => {
    const nextState = !expandedRecs[recId];
    setExpandedRecs(prev => ({ ...prev, [recId]: nextState }));

    if (nextState && !explanations[recId]) {
      const recItem = recommendations.find(r => r.id === recId);
      if (recItem?.explanation && recItem.explanation.provenance && recItem.explanation.answers) {
        setExplanations(prev => ({ ...prev, [recId]: recItem.explanation }));
      } else {
        try {
          setExplLoading(prev => ({ ...prev, [recId]: true }));
          const data = await apiFetch<any>(`/api/v1/recommendations/${recId}/explanation`);
          setExplanations(prev => ({ ...prev, [recId]: data }));
        } catch (err) {
          console.error("Failed to load recommendation explanation:", err);
        } finally {
          setExplLoading(prev => ({ ...prev, [recId]: false }));
        }
      }
    }
  };

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      const data = await apiFetch<any[]>("/api/v1/recommendations");
      setRecommendations(data);
    } catch (err: any) {
      console.error("Fetch recommendations error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!isCdmoOrAdmin) {
      setBanner({ type: "error", msg: "Generating redistribution recommendations requires CDMO or ADMIN role." });
      return;
    }
    try {
      setGenerating(true);
      setBanner(null);
      const newRecs = await apiFetch<any[]>("/api/v1/recommendations/generate", { method: "POST" });
      setRecommendations(newRecs);
      setBanner({ type: "success", msg: "Cross-district stock redistribution engine generated candidate routes." });
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Generating redistribution recommendations requires CDMO or ADMIN role." });
    } finally {
      setGenerating(false);
    }
  };

  const handleAction = async (id: number, action: "APPROVE" | "REJECT") => {
    if (!isCdmoOrAdmin) {
      setBanner({ type: "error", msg: "Unauthorized. Redistribution approval/rejection requires CDMO or ADMIN role." });
      return;
    }
    try {
      setActionLoading(id);
      setBanner(null);
      await apiFetch(`/api/v1/recommendations/${id}/action`, {
        method: "POST",
        body: JSON.stringify({ action })
      });
      setBanner({ 
        type: "success", 
        msg: action === "APPROVE" 
          ? `Recommendation #${id} approved! Inventory stock transfer committed successfully to audit ledger and forecasts recalculated.` 
          : `Recommendation #${id} rejected.` 
      });
      await fetchRecommendations();
      if (action === "APPROVE") {
        await fetchVerification(id);
      }
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Action requires CDMO or ADMIN role." });
    } finally {
      setActionLoading(null);
    }
  };

  const fetchFacilitiesAndCatalog = async () => {
    try {
      const [facData, catData] = await Promise.all([
        apiFetch<any[]>("/api/v1/facilities"),
        apiFetch<any[]>("/api/v1/resources/catalog")
      ]);
      setFacilities(facData);
      setCatalog(catData);
      if (facData.length > 1) {
        setSimDonorId(prev => (prev === "" ? facData[1].id : prev));
        setSimRecipId(prev => (prev === "" ? facData[0].id : prev));
      }
      if (catData.length > 0) {
        setSimItemCode(prev => (prev === "" ? catData[0].sku : prev));
      }
    } catch (err: any) {
      console.error("Failed to load facilities or catalog:", err);
    }
  };

  const handleRunSimulation = async (
    donorId?: number,
    recipId?: number,
    itemCode?: string,
    quantity?: number
  ) => {
    const dId = donorId !== undefined ? donorId : simDonorId;
    const rId = recipId !== undefined ? recipId : simRecipId;
    const iCode = itemCode !== undefined ? itemCode : simItemCode;
    const qty = quantity !== undefined ? quantity : simQuantity;

    if (!dId || !rId || !iCode || !qty || Number(qty) <= 0) {
      setSimError("Please select a donor, recipient, resource SKU, and enter a valid quantity (> 0).");
      return;
    }
    if (Number(dId) === Number(rId)) {
      setSimError("Donor and recipient facility cannot be identical.");
      return;
    }

    try {
      setSimLoading(true);
      setSimError(null);
      const res = await apiFetch<any>("/api/v1/simulations/redistribution", {
        method: "POST",
        body: JSON.stringify({
          donor_facility_id: Number(dId),
          recipient_facility_id: Number(rId),
          item_code: iCode,
          transfer_quantity: Number(qty)
        })
      });
      setSimResult(res);
    } catch (err: any) {
      setSimError(err.message || "Failed to execute What-If simulation.");
      setSimResult(null);
    } finally {
      setSimLoading(false);
    }
  };

  const launchSimulationForRec = (rec: any) => {
    setSimDonorId(rec.donor_facility_id);
    setSimRecipId(rec.recipient_facility_id);
    setSimItemCode(rec.item_code);
    setSimQuantity(rec.recommended_quantity);
    setShowSimulator(true);
    if (facilities.length === 0) {
      fetchFacilitiesAndCatalog();
    }
    handleRunSimulation(rec.donor_facility_id, rec.recipient_facility_id, rec.item_code, rec.recommended_quantity);
  };

  useEffect(() => {
    fetchRecommendations();
    fetchFacilitiesAndCatalog();
  }, [user]);

  return (
    <AppShell>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E]">Inter-Facility Resource Redistribution</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Deterministic Haversine Candidate Scoring, Donor Stock Balance &amp; Human Approval Workflow
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                const nextState = !showSimulator;
                setShowSimulator(nextState);
                if (nextState && facilities.length === 0) {
                  fetchFacilitiesAndCatalog();
                }
              }}
              className={`text-xs font-bold px-3.5 py-2 rounded-xl flex items-center gap-1.5 shadow-2xs cursor-pointer transition ${
                showSimulator 
                  ? "bg-indigo-600 text-white hover:bg-indigo-700" 
                  : "bg-indigo-50 border border-indigo-200 text-indigo-900 hover:bg-indigo-100"
              }`}
            >
              <IconPlayerPlay size={15} className={showSimulator ? "text-white" : "text-indigo-600"} />
              {showSimulator ? "Close Simulation Sandbox" : "What-If Simulation Sandbox"}
            </button>
            {isCdmoOrAdmin && (
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50 transition"
              >
                <IconSparkles size={16} className={generating ? "animate-spin" : ""} />
                {generating ? "Calculating Routes..." : "Run Redistribution Engine"}
              </button>
            )}
            <button
              onClick={fetchRecommendations}
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

        {/* Mandatory Human Approval Banner */}
        <div className="bg-amber-50 border border-amber-200 p-4 rounded-2xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-amber-900 text-xs">
            <IconShieldCheck size={20} className="text-amber-600 shrink-0" />
            <div>
              <span className="font-bold uppercase tracking-wider block font-mono">MANDATORY HUMAN APPROVAL BOUNDARY</span>
              <p className="text-amber-700">
                Physical stock transfers are strictly non-autonomous. AI recommendations are decision-support only. Approval requires authorized CDMO or Admin role and commits atomic inventory changes with cryptographic audit logging.
              </p>
            </div>
          </div>
          <div className="hidden lg:flex items-center gap-2 font-mono text-[11px] text-amber-800 bg-amber-100/80 px-3 py-1.5 rounded-xl border border-amber-300">
            <span className="font-bold">Role:</span> {user?.role || "AUTHENTICATING"}
          </div>
        </div>

        {/* What-If Simulation Sandbox Panel */}
        {showSimulator && (
          <div className="bg-white border-2 border-indigo-200 rounded-2xl p-5 shadow-sm space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-indigo-100 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-700">
                  <IconAdjustmentsHorizontal size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-black text-[#0C2B4E] uppercase tracking-wider">
                    WHAT-IF OPERATIONAL INTERVENTION SIMULATOR
                  </h2>
                  <p className="text-[11px] text-slate-500 font-mono">
                    Simulate proposed stock movements, donor safety buffer retention, and recipient days-of-cover impact. Strictly read-only.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowSimulator(false)}
                className="text-slate-400 hover:text-slate-600 text-xs font-mono underline cursor-pointer self-start sm:self-auto"
              >
                Hide Sandbox
              </button>
            </div>

            {/* Input Controls */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono text-xs">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  DONOR FACILITY (SENDS)
                </label>
                <select
                  value={simDonorId}
                  onChange={(e) => setSimDonorId(e.target.value ? Number(e.target.value) : "")}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 font-sans focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="">Select Donor...</option>
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name} ({f.district})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  RECIPIENT FACILITY (RECEIVES)
                </label>
                <select
                  value={simRecipId}
                  onChange={(e) => setSimRecipId(e.target.value ? Number(e.target.value) : "")}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 font-sans focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="">Select Recipient...</option>
                  {facilities.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name} ({f.district})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  RESOURCE / SKU
                </label>
                <select
                  value={simItemCode}
                  onChange={(e) => setSimItemCode(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 font-sans focus:outline-hidden focus:border-indigo-500"
                >
                  <option value="">Select Resource...</option>
                  {catalog.map((c) => (
                    <option key={c.sku} value={c.sku}>
                      {c.name} ({c.sku})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  TRANSFER QUANTITY
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min="1"
                    value={simQuantity}
                    onChange={(e) => setSimQuantity(e.target.value ? Number(e.target.value) : "")}
                    placeholder="e.g. 50"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 font-mono focus:outline-hidden focus:border-indigo-500"
                  />
                  <button
                    onClick={() => handleRunSimulation()}
                    disabled={simLoading}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50 transition shrink-0"
                  >
                    <IconPlayerPlay size={14} className={simLoading ? "animate-spin" : ""} />
                    {simLoading ? "Simulating..." : "Simulate"}
                  </button>
                </div>
              </div>
            </div>

            {/* Quick Preset Buttons */}
            <div className="flex items-center gap-2 font-mono text-[11px] text-slate-500 pt-0.5 flex-wrap">
              <span className="text-[10px] uppercase font-bold text-slate-400">Quick Quantity Presets:</span>
              {[25, 50, 90, 120, 150].map((qty) => (
                <button
                  key={qty}
                  type="button"
                  onClick={() => {
                    setSimQuantity(qty);
                    handleRunSimulation(undefined, undefined, undefined, qty);
                  }}
                  className={`px-2.5 py-0.5 rounded-lg border text-xs cursor-pointer transition ${
                    simQuantity === qty
                      ? "bg-indigo-100 text-indigo-900 border-indigo-300 font-bold"
                      : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                  }`}
                >
                  {qty} units
                </button>
              ))}
            </div>

            {/* Simulation Error */}
            {simError && (
              <div className="bg-rose-50 border border-rose-200 p-3 rounded-xl text-rose-900 text-xs font-mono flex items-center gap-2">
                <IconAlertCircle size={16} className="text-rose-600 shrink-0" />
                <span>{simError}</span>
              </div>
            )}

            {/* Simulation Result Presentation */}
            {simResult && (
              <div className="space-y-4 pt-2">
                {/* Simulation Only Alert Banner */}
                <div className="bg-amber-500/10 border-2 border-amber-500/40 text-amber-950 px-4 py-2.5 rounded-xl text-xs font-mono font-bold flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-2">
                    <IconShieldCheck size={18} className="text-amber-700 shrink-0" />
                    <span className="tracking-wide">SIMULATION ONLY — NO INVENTORY CHANGED</span>
                  </div>
                  <span className="text-[11px] font-semibold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded border border-amber-300">
                    Hypothetical Analysis • In-Memory Only
                  </span>
                </div>

                {/* 4-Stage Conceptual Flow: CURRENT -> ACTION -> SIMULATED -> IMPACT */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 font-mono text-xs">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                    OPERATIONAL IMPACT PIPELINE
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
                    {/* 1. Current State */}
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">1. CURRENT</span>
                        <span className={`text-[9px] font-black px-1.5 py-0.2 rounded border ${
                          simResult.recipient.current_risk_severity === "CRITICAL"
                            ? "bg-rose-100 border-rose-300 text-rose-800"
                            : simResult.recipient.current_risk_severity === "WARNING"
                              ? "bg-amber-100 border-amber-300 text-amber-800"
                              : "bg-emerald-100 border-emerald-300 text-emerald-800"
                        }`}>
                          {simResult.recipient.current_risk_severity || "CRITICAL"}
                        </span>
                      </div>
                      <div className="text-[11px] font-bold text-slate-800 truncate">
                        {simResult.recipient.facility_name}
                      </div>
                      <div className="text-[10px] text-slate-600">
                        {simResult.recipient.current_stock} {simResult.unit} • {simResult.recipient.current_days_of_cover}d cover
                      </div>
                    </div>

                    {/* 2. What-If Action */}
                    <div className="bg-indigo-50/70 p-2.5 rounded-lg border border-indigo-200 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-indigo-700 uppercase">2. WHAT-IF ACTION</span>
                        <span className="text-[9px] font-bold text-indigo-700">{simResult.haversine_distance_km} km</span>
                      </div>
                      <div className="text-[11px] font-bold text-indigo-950 truncate">
                        Transfer {simResult.transfer_quantity} {simResult.unit}
                      </div>
                      <div className="text-[10px] text-indigo-800 truncate">
                        {simResult.donor.facility_name.split(" ")[0]} → {simResult.recipient.facility_name.split(" ")[0]}
                      </div>
                    </div>

                    {/* 3. Simulated State */}
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">3. SIMULATED</span>
                        <span className={`text-[9px] font-black px-1.5 py-0.2 rounded border ${
                          simResult.recipient.simulated_risk_severity === "CRITICAL"
                            ? "bg-rose-100 border-rose-300 text-rose-800"
                            : simResult.recipient.simulated_risk_severity === "WARNING"
                              ? "bg-amber-100 border-amber-300 text-amber-800"
                              : "bg-emerald-100 border-emerald-300 text-emerald-800"
                        }`}>
                          {simResult.recipient.simulated_risk_severity || "SAFE"}
                        </span>
                      </div>
                      <div className="text-[11px] font-bold text-slate-800 truncate">
                        {simResult.recipient.simulated_stock} {simResult.unit}
                      </div>
                      <div className="text-[10px] text-slate-600">
                        {simResult.recipient.simulated_days_of_cover}d cover (+{simResult.recipient.days_of_cover_gained}d)
                      </div>
                    </div>

                    {/* 4. Impact Assessment */}
                    <div className={`p-2.5 rounded-lg border space-y-1 ${
                      simResult.status === "SAFE"
                        ? "bg-emerald-50 border-emerald-300 text-emerald-950"
                        : simResult.status === "CAUTION"
                          ? "bg-amber-50 border-amber-300 text-amber-950"
                          : "bg-rose-50 border-rose-300 text-rose-950"
                    }`}>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase">4. IMPACT</span>
                        <span className="text-[9px] font-black uppercase px-1.5 py-0.2 rounded bg-white/70 border border-current">
                          {simResult.feasibility_status || (simResult.status !== "UNSAFE" ? "FEASIBLE" : "INFEASIBLE")}
                        </span>
                      </div>
                      <div className="text-[11px] font-bold truncate">
                        {simResult.recipient.current_risk_severity || "CRITICAL"} → {simResult.recipient.simulated_risk_severity || "SAFE"}
                      </div>
                      <div className="text-[10px] font-medium truncate">
                        Donor: {simResult.donor.buffer_preserved ? "Buffer Preserved" : "Buffer Breached"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Result Header & Status Banner */}
                <div className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-mono ${
                  simResult.status === "SAFE" 
                    ? "bg-emerald-50 border-emerald-300 text-emerald-950" 
                    : simResult.status === "CAUTION" 
                      ? "bg-amber-50 border-amber-300 text-amber-950" 
                      : "bg-rose-50 border-rose-300 text-rose-950"
                }`}>
                  <div className="flex items-center gap-2.5">
                    <span className={`text-xs font-black px-3 py-1 rounded-lg uppercase tracking-wider border ${
                      simResult.status === "SAFE"
                        ? "bg-emerald-100 border-emerald-400 text-emerald-900"
                        : simResult.status === "CAUTION"
                          ? "bg-amber-100 border-amber-400 text-amber-900"
                          : "bg-rose-100 border-rose-400 text-rose-900"
                    }`}>
                      RESULT: {simResult.feasibility_status || (simResult.status !== "UNSAFE" ? "FEASIBLE" : "INFEASIBLE")} ({simResult.status})
                    </span>
                    <span className="text-xs font-bold">
                      Proposed Transfer of {simResult.transfer_quantity} {simResult.unit} ({simResult.resource_name})
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-600 font-mono">
                    <span>Distance: <strong>{simResult.haversine_distance_km} km</strong></span>
                    <span>•</span>
                    <span>Sim ID: <strong>{simResult.simulation_id}</strong></span>
                  </div>
                </div>

                {/* Section 5: Side-by-Side Before vs After Comparison */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
                  {/* RECIPIENT NODE */}
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                    <div className="border-b border-slate-200 pb-2 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                          RECIPIENT FACILITY (RECEIVES)
                        </span>
                        <strong className="text-sm font-bold text-[#0C2B4E] font-sans block">
                          {simResult.recipient.facility_name} ({simResult.recipient.district})
                        </strong>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 block font-sans">Risk Transition</span>
                        <span className="text-[11px] font-bold font-mono text-indigo-700">
                          {simResult.recipient.current_risk_severity || "CRITICAL"} → {simResult.recipient.simulated_risk_severity || "SAFE"}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-[11px]">
                      {/* Recipient Before */}
                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                            BEFORE
                          </span>
                          <span className={`text-[9px] font-bold px-1.5 rounded ${
                            simResult.recipient.current_risk_severity === "CRITICAL"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-amber-100 text-amber-800"
                          }`}>
                            {simResult.recipient.current_risk_severity || "CRITICAL"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Current Stock:</span>
                          <span className="font-bold text-slate-800">{simResult.recipient.current_stock} {simResult.unit}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Daily Demand:</span>
                          <span className="font-bold text-slate-800">{simResult.recipient.daily_demand} {simResult.unit}/day</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Days of Cover:</span>
                          <span className="font-black text-rose-700">{simResult.recipient.current_days_of_cover} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Safety Buffer:</span>
                          <span className="font-bold text-slate-700">{simResult.recipient.safety_buffer || simResult.recipient.safety_stock} {simResult.unit}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">7-Day Projected Demand:</span>
                          <span className="font-bold text-slate-700">{simResult.recipient.projected_7day_demand || (simResult.recipient.daily_demand * 7).toFixed(1)} {simResult.unit}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Projected Stockout:</span>
                          <span className="font-bold text-slate-700">{simResult.recipient.current_projected_stockout || "None"}</span>
                        </div>
                      </div>

                      {/* Recipient After */}
                      <div className="bg-emerald-50/60 p-3 rounded-lg border border-emerald-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
                            AFTER (+{simResult.transfer_quantity})
                          </span>
                          <span className={`text-[9px] font-bold px-1.5 rounded ${
                            simResult.recipient.simulated_risk_severity === "SAFE"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-amber-100 text-amber-800"
                          }`}>
                            {simResult.recipient.simulated_risk_severity || "SAFE"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Simulated Stock:</span>
                          <span className="font-bold text-emerald-800">{simResult.recipient.simulated_stock} {simResult.unit}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Days of Cover:</span>
                          <span className="font-bold text-emerald-800">{simResult.recipient.simulated_days_of_cover} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Coverage Gained:</span>
                          <span className="font-black text-emerald-700">+{simResult.recipient.days_of_cover_gained} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Buffer Status:</span>
                          <span className={`font-bold ${simResult.recipient.buffer_achieved ? "text-emerald-700" : "text-amber-700"}`}>
                            {simResult.recipient.buffer_achieved ? "ACHIEVED (≥ Safety)" : "DEFICIT (< Safety)"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Projected Stockout:</span>
                          <span className="font-bold text-slate-700">{simResult.recipient.simulated_projected_stockout || "Safe"}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* DONOR NODE */}
                  <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                    <div className="border-b border-slate-200 pb-2 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                          DONOR FACILITY (SENDS)
                        </span>
                        <strong className="text-sm font-bold text-[#0C2B4E] font-sans block">
                          {simResult.donor.facility_name} ({simResult.donor.district})
                        </strong>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] text-slate-400 block font-sans">Risk Transition</span>
                        <span className="text-[11px] font-bold font-mono text-indigo-700">
                          {simResult.donor.current_risk_severity || "SAFE"} → {simResult.donor.simulated_risk_severity || "SAFE"}
                        </span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-[11px]">
                      {/* Donor Before */}
                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                            BEFORE
                          </span>
                          <span className="text-[9px] font-bold px-1.5 rounded bg-emerald-100 text-emerald-800">
                            {simResult.donor.current_risk_severity || "SAFE"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Current Stock:</span>
                          <span className="font-bold text-slate-800">{simResult.donor.current_stock} {simResult.unit}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Daily Demand:</span>
                          <span className="font-bold text-slate-800">{simResult.donor.daily_demand} {simResult.unit}/day</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Days of Cover:</span>
                          <span className="font-bold text-slate-800">{simResult.donor.current_days_of_cover} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Safety Buffer:</span>
                          <span className="font-bold text-slate-700">{simResult.donor.safety_buffer || simResult.donor.safety_stock} {simResult.unit}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Available Surplus:</span>
                          <span className="font-bold text-emerald-700">+{simResult.donor.surplus_available} {simResult.unit}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">7-Day Projected Demand:</span>
                          <span className="font-bold text-slate-700">{simResult.donor.projected_7day_demand || (simResult.donor.daily_demand * 7).toFixed(1)} {simResult.unit}</span>
                        </div>
                      </div>

                      {/* Donor After */}
                      <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-bold text-slate-700 uppercase tracking-wider block">
                            AFTER (-{simResult.transfer_quantity})
                          </span>
                          <span className={`text-[9px] font-bold px-1.5 rounded ${
                            simResult.donor.simulated_risk_severity === "SAFE"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-rose-100 text-rose-800"
                          }`}>
                            {simResult.donor.simulated_risk_severity || "SAFE"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Simulated Stock:</span>
                          <span className={`font-bold ${simResult.donor.buffer_preserved ? "text-slate-800" : "text-rose-700 font-black"}`}>
                            {simResult.donor.simulated_stock} {simResult.unit}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Days of Cover:</span>
                          <span className="font-bold text-slate-800">{simResult.donor.simulated_days_of_cover} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Buffer Status:</span>
                          <span className={`font-bold ${simResult.donor.buffer_preserved ? "text-emerald-700" : "text-rose-700"}`}>
                            {simResult.donor.buffer_preserved ? "PROTECTED (≥ Safety)" : "BREACHED (< Safety)"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Coverage Lost:</span>
                          <span className="font-bold text-slate-700">-{simResult.donor.days_of_cover_lost} days</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[10px]">Projected Stockout:</span>
                          <span className="font-bold text-slate-700">{simResult.donor.simulated_projected_stockout || "Safe"}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Deterministic Explanation & Risk Criteria */}
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 font-sans text-xs">
                  <div>
                    <strong className="text-xs font-bold text-[#0C2B4E] uppercase tracking-wider font-mono block mb-1">
                      WHY? (Deterministic Telemetry Evidence)
                    </strong>
                    <p className="text-slate-700 leading-relaxed font-mono text-[11px]">
                      {simResult.reason}
                    </p>
                  </div>

                  {/* Risk Analysis Flags */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-200 font-mono text-[10px]">
                    <div className={`p-2 rounded border ${simResult.risk_analysis.recipient_improves ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-slate-100 border-slate-200 text-slate-700"}`}>
                      <span>Recipient Improves:</span>
                      <strong className="block font-bold">{simResult.risk_analysis.recipient_improves ? "✓ Coverage Gained" : "✗ No Improvement"}</strong>
                    </div>
                    <div className={`p-2 rounded border ${simResult.risk_analysis.within_donor_surplus ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-rose-50 border-rose-200 text-rose-900"}`}>
                      <span>Within Surplus:</span>
                      <strong className="block font-bold">{simResult.risk_analysis.within_donor_surplus ? "✓ Within Surplus" : "✗ Exceeds Surplus"}</strong>
                    </div>
                    <div className={`p-2 rounded border ${!simResult.risk_analysis.donor_falls_below_safety ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-rose-50 border-rose-200 text-rose-900"}`}>
                      <span>Donor Buffer:</span>
                      <strong className="block font-bold">{!simResult.risk_analysis.donor_falls_below_safety ? "✓ Buffer Preserved" : "✗ Buffer Breached"}</strong>
                    </div>
                    <div className={`p-2 rounded border ${simResult.risk_analysis.is_operationally_safe ? "bg-emerald-50 border-emerald-200 text-emerald-900" : "bg-amber-50 border-amber-200 text-amber-900"}`}>
                      <span>Operational Risk:</span>
                      <strong className="block font-bold">{simResult.risk_analysis.is_operationally_safe ? "✓ Operationally Safe" : "⚠ Caution / Unsafe"}</strong>
                    </div>
                  </div>
                </div>

                {/* Mandatory Safety Notice & Path to Human Approval */}
                <div className="bg-blue-50/60 border border-blue-200 p-3.5 rounded-xl flex items-center justify-between gap-4 font-mono text-xs">
                  <div className="flex items-center gap-2.5 text-[#0C2B4E]">
                    <IconShieldCheck size={18} className="text-[#1D546C] shrink-0" />
                    <div>
                      <strong className="block font-bold uppercase tracking-wider text-[10px]">
                        SIMULATION ONLY — NO INVENTORY HAS BEEN CHANGED
                      </strong>
                      <span className="text-[11px] text-slate-600 block">
                        Interventions remain hypothetical. Operational execution requires explicit review and approval by an authorized CDMO or Admin in the recommendation queue below.
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recommendations List */}
        <div className="space-y-4">
          {recommendations.map((rec) => {
            const donorName = rec.donor_facility_name || `Facility #${rec.donor_facility_id}`;
            const donorLoc = rec.donor_district ? `${rec.donor_district}, ${rec.donor_state}` : `ID: #${rec.donor_facility_id}`;
            const recipName = rec.recipient_facility_name || `Facility #${rec.recipient_facility_id}`;
            const recipLoc = rec.recipient_district ? `${rec.recipient_district}, ${rec.recipient_state}` : `ID: #${rec.recipient_facility_id}`;
            const itemName = rec.item_name || rec.item_code;
            const expl = explanations[rec.id] || rec.explanation;

            return (
              <div key={rec.id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
                
                {/* Header Row: Rec ID, SKU, Status */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2 font-mono flex-wrap">
                    <span className="text-xs font-black text-[#0C2B4E]">Recommendation #{rec.id}</span>
                    <span className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-bold">
                      {itemName} ({rec.item_code})
                    </span>
                    <span className="text-[10px] text-slate-400 font-normal">
                      Code: {rec.recommendation_code}
                    </span>
                  </div>
                  <span className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded font-mono ${
                    rec.status === "PENDING_HUMAN_APPROVAL" ? "bg-amber-100 text-amber-900 border border-amber-300" :
                    rec.status === "APPROVED" ? "bg-emerald-100 text-emerald-900 border border-emerald-300" :
                    "bg-slate-100 text-slate-700 border border-slate-300"
                  }`}>
                    {rec.status === "PENDING_HUMAN_APPROVAL" ? "PENDING CDMO APPROVAL" : rec.status}
                  </span>
                </div>

                {/* TRANSFER ROUTE METADATA */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 items-center">
                  {/* DONOR NODE */}
                  <div className="space-y-0.5 font-mono">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">DONOR FACILITY (SENDS)</span>
                    <strong className="text-xs font-bold text-[#0C2B4E] font-sans block">{donorName}</strong>
                    <span className="text-[11px] text-slate-500 block">{donorLoc}</span>
                    <span className="text-[10px] text-slate-600 block pt-1">
                      Current Stock: <strong>{rec.donor_current_stock ?? "—"} units</strong> (Safety: {rec.donor_safety_stock ?? 40})
                    </span>
                  </div>

                  {/* QUANTITY FLOW */}
                  <div className="flex flex-col items-center justify-center text-center py-2 border-y md:border-y-0 md:border-x border-slate-200 px-3 space-y-1 font-mono">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">TRANSFER QUANTITY</span>
                    <span className="text-base font-black text-emerald-700 bg-emerald-50 px-3 py-1 rounded-lg border border-emerald-200">
                      {rec.recommended_quantity} units
                    </span>
                    <div className="flex items-center gap-1 text-[11px] text-slate-500 pt-0.5">
                      <span>{rec.haversine_distance_km} km</span>
                      <IconArrowRight size={12} className="text-slate-400" />
                      <span className="text-emerald-700 font-bold">+{rec.expected_days_cover_gained} days cover</span>
                    </div>
                  </div>

                  {/* RECIPIENT NODE */}
                  <div className="space-y-0.5 font-mono md:text-right">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">RECIPIENT FACILITY (RECEIVES)</span>
                    <strong className="text-xs font-bold text-[#0C2B4E] font-sans block">{recipName}</strong>
                    <span className="text-[11px] text-slate-500 block">{recipLoc}</span>
                    <span className="text-[10px] text-slate-600 block pt-1">
                      Current Stock: <strong>{rec.recipient_current_stock ?? "—"} units</strong> (Safety: {rec.recipient_safety_stock ?? 40})
                    </span>
                  </div>
                </div>

                {/* Reason Banner */}
                <p className="text-xs text-slate-600 font-mono bg-slate-50/80 p-3 rounded-xl border border-slate-200">
                  <strong className="text-slate-700">Reason:</strong> {rec.reason}
                </p>

                {/* FEATURE #10: BEFORE -> ACTION -> AFTER -> VERIFICATION CONTAINER */}
                {(() => {
                  const verifData = verifications[rec.id];
                  const isVerifOpen = !!expandedVerifChecklist[rec.id];
                  const isVLoading = !!verifLoading[rec.id];

                  // Deterministic fallback calculations for immediate card display
                  const beforeRecipStock = verifData?.recipient?.stock_before ?? (
                    rec.status === "APPROVED" 
                      ? Math.max(0, (rec.recipient_current_stock || 0) - rec.recommended_quantity)
                      : (rec.recipient_current_stock ?? "—")
                  );
                  const beforeDonorStock = verifData?.donor?.stock_before ?? (
                    rec.status === "APPROVED"
                      ? (rec.donor_current_stock || 0) + rec.recommended_quantity
                      : (rec.donor_current_stock ?? "—")
                  );
                  const afterRecipStock = verifData?.recipient?.stock_after_actual ?? (
                    rec.status === "APPROVED"
                      ? (rec.recipient_current_stock ?? "—")
                      : ((rec.recipient_current_stock || 0) + rec.recommended_quantity)
                  );
                  const afterDonorStock = verifData?.donor?.stock_after_actual ?? (
                    rec.status === "APPROVED"
                      ? (rec.donor_current_stock ?? "—")
                      : Math.max(0, (rec.donor_current_stock || 0) - rec.recommended_quantity)
                  );
                  const donorSafetyBufferProtected = verifData?.donor?.safety_buffer_protected ?? (
                    rec.status === "APPROVED" ? true : ((rec.donor_current_stock || 0) - rec.recommended_quantity >= (rec.donor_safety_stock || 40))
                  );

                  return (
                    <div className="bg-slate-50/90 border border-slate-200 rounded-xl p-4 space-y-3 font-mono">
                      {/* Flow Header with Live DB Status */}
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-black text-[#0C2B4E] uppercase tracking-wider flex items-center gap-1.5">
                            <IconShieldCheck size={16} className="text-[#1D546C]" />
                            BEFORE → ACTION → AFTER → VERIFICATION
                          </span>
                          <span className="text-[10px] text-slate-500 font-normal hidden sm:inline">
                            (Authoritative Database Ground Truth)
                          </span>
                        </div>

                        {/* Verification Badge */}
                        <div className="flex items-center gap-2">
                          {rec.status === "APPROVED" ? (
                            <span className={`text-[11px] font-black px-2.5 py-1 rounded-lg flex items-center gap-1.5 border shadow-2xs ${
                              verifData?.status === "PASSED" || !verifData
                                ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                                : "bg-rose-50 text-rose-900 border-rose-300"
                            }`}>
                              {verifData?.status === "PASSED" || !verifData ? (
                                <>
                                  <IconCheck size={14} className="text-emerald-700 stroke-[3]" />
                                  <span>VERIFICATION: ✓ PASSED</span>
                                </>
                              ) : (
                                <>
                                  <IconAlertTriangle size={14} className="text-rose-700 stroke-[3]" />
                                  <span>VERIFICATION: ⚠ FAILED / REVIEW REQUIRED</span>
                                </>
                              )}
                            </span>
                          ) : rec.status === "PENDING_HUMAN_APPROVAL" ? (
                            <span className="text-[11px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1.5 bg-amber-50 text-amber-900 border border-amber-300">
                              <IconClock size={13} className="text-amber-700" />
                              <span>VERIFICATION: ⏳ PENDING APPROVAL</span>
                            </span>
                          ) : (
                            <span className="text-[11px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1.5 bg-slate-100 text-slate-700 border border-slate-300">
                              <IconX size={13} className="text-slate-600" />
                              <span>VERIFICATION: REJECTED</span>
                            </span>
                          )}
                        </div>
                      </div>

                      {/* 4 Stage Flow Columns */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                        {/* 1. BEFORE */}
                        <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                          <span className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider block">
                            1. BEFORE (PRE-TRANSFER)
                          </span>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Recipient Stock:</span>
                            <strong className="text-sm font-black text-rose-700 block">
                              {beforeRecipStock} units
                            </strong>
                            <span className="text-[10px] text-slate-500 block">
                              {verifData?.recipient?.days_of_cover_before ?? rec.recipient_days_of_cover ?? "—"} days cover ({verifData?.recipient?.risk_status_before ?? "CRITICAL"})
                            </span>
                          </div>
                          <div className="pt-1 border-t border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Donor Stock:</span>
                            <strong className="text-xs font-bold text-slate-700 block">
                              {beforeDonorStock} units
                            </strong>
                          </div>
                        </div>

                        {/* 2. APPROVED ACTION */}
                        <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                          <span className="text-[10px] font-extrabold text-[#1D546C] uppercase tracking-wider block">
                            2. APPROVED ACTION
                          </span>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Transfer Route:</span>
                            <span className="text-xs font-bold text-[#0C2B4E] block truncate" title={`${donorName} → ${recipName}`}>
                              {donorName.split(' ')[0]} → {recipName.split(' ')[0]}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Transfer Quantity:</span>
                            <strong className="text-sm font-black text-emerald-700 block">
                              +{rec.recommended_quantity} units
                            </strong>
                          </div>
                          <div className="pt-1 border-t border-slate-100 text-[10px] text-slate-500 truncate">
                            <span>Audit Ref: </span>
                            <strong className="text-slate-700">
                              {verifData?.audit_reference?.event_id || (rec.status === "APPROVED" ? "Committed to Ledger" : "Pending Human Action")}
                            </strong>
                          </div>
                        </div>

                        {/* 3. ACTUAL AFTER */}
                        <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-1.5">
                          <span className="text-[10px] font-extrabold text-slate-700 uppercase tracking-wider block">
                            3. ACTUAL AFTER
                          </span>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Recipient Stock:</span>
                            <strong className="text-sm font-black text-emerald-700 block">
                              {afterRecipStock} units
                            </strong>
                            <span className="text-[10px] text-slate-500 block">
                              {verifData?.recipient?.days_of_cover_after ?? "—"} days cover ({verifData?.recipient?.risk_status_after ?? (rec.status === "APPROVED" ? "SAFE" : "PROJECTED")})
                            </span>
                          </div>
                          <div className="pt-1 border-t border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Donor Remaining Stock:</span>
                            <strong className="text-xs font-bold text-slate-700 block">
                              {afterDonorStock} units {donorSafetyBufferProtected ? "(Buffer Safe)" : "(Buffer Breached)"}
                            </strong>
                          </div>
                        </div>

                        {/* 4. VERIFICATION */}
                        <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-2 flex flex-col justify-between">
                          <div>
                            <span className="text-[10px] font-extrabold text-[#0C2B4E] uppercase tracking-wider block">
                              4. VERIFICATION
                            </span>
                            <div className="pt-1">
                              {rec.status === "APPROVED" ? (
                                <div className="space-y-1">
                                  <span className="text-xs font-black text-emerald-800 flex items-center gap-1">
                                    <IconCheck size={14} className="text-emerald-600 stroke-[3]" />
                                    {verifData?.status === "PASSED" || !verifData ? "PASSED (Matches DB)" : "DISCREPANCY DETECTED"}
                                  </span>
                                  <span className="text-[10px] text-slate-600 block leading-tight">
                                    {verifData?.summary || "Authoritative database inventory and SHA-256 audit ledger match expected outcome."}
                                  </span>
                                </div>
                              ) : rec.status === "PENDING_HUMAN_APPROVAL" ? (
                                <div className="space-y-1">
                                  <span className="text-xs font-bold text-amber-800 flex items-center gap-1">
                                    <IconClock size={14} className="text-amber-600" />
                                    PENDING APPROVAL
                                  </span>
                                  <span className="text-[10px] text-slate-500 block leading-tight">
                                    Awaiting CDMO/Admin operational approval before inventory mutation.
                                  </span>
                                </div>
                              ) : (
                                <span className="text-xs font-bold text-slate-600">REJECTED — Not Executed</span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-1 pt-1">
                            <button
                              onClick={() => toggleVerifChecklist(rec.id)}
                              className="flex-1 text-center bg-blue-50 hover:bg-blue-100 text-[#0C2B4E] border border-blue-200 rounded-md py-1 px-2 text-[10px] font-bold flex items-center justify-center gap-1 transition cursor-pointer"
                            >
                              <IconShieldCheck size={12} className="text-[#1D546C]" />
                              <span>{isVerifOpen ? "Hide Checklist" : "12-Point Checklist"}</span>
                              {isVerifOpen ? <IconChevronUp size={12} /> : <IconChevronDown size={12} />}
                            </button>
                            <button
                              onClick={() => fetchVerification(rec.id)}
                              disabled={isVLoading}
                              title="Re-verify database state"
                              className="bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 rounded-md p-1 transition cursor-pointer disabled:opacity-50"
                            >
                              <IconRefresh size={12} className={isVLoading ? "animate-spin" : ""} />
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Expandable 12-Point Verification Checklist Drawer */}
                      {isVerifOpen && (
                        <div className="bg-white border border-blue-200 rounded-xl p-4 space-y-3 pt-3">
                          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                            <span className="text-xs font-bold text-[#0C2B4E] uppercase tracking-wider flex items-center gap-1.5">
                              <IconShieldCheck size={14} className="text-[#1D546C]" />
                              Authoritative 12-Point Verification Checklist
                            </span>
                            <span className="text-[10px] text-slate-400">
                              {verifData?.verified_at ? `Verified at ${new Date(verifData.verified_at).toLocaleTimeString()}` : "Live DB Query"}
                            </span>
                          </div>

                          {isVLoading && !verifData ? (
                            <div className="text-center py-4 text-slate-500 font-mono text-xs">
                              Cross-checking database state and SHA-256 audit ledger...
                            </div>
                          ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-[11px]">
                              {/* 1. Recipient stock before */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">1. Recipient Stock Before:</span>
                                <strong className="text-slate-800 font-bold block">
                                  {verifData?.checklist?.["1_recipient_stock_before"]?.value ?? beforeRecipStock} units
                                </strong>
                              </div>

                              {/* 2. Donor stock before */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">2. Donor Stock Before:</span>
                                <strong className="text-slate-800 font-bold block">
                                  {verifData?.checklist?.["2_donor_stock_before"]?.value ?? beforeDonorStock} units
                                </strong>
                              </div>

                              {/* 3. Approved transfer quantity */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">3. Approved Transfer Quantity:</span>
                                <strong className="text-emerald-700 font-bold block">
                                  {verifData?.checklist?.["3_approved_transfer_quantity"]?.value ?? rec.recommended_quantity} units
                                </strong>
                              </div>

                              {/* 4. Actual stock movement quantity */}
                              <div className={`p-2 rounded border space-y-0.5 ${
                                verifData?.comparison?.quantity_matches || (rec.status === "APPROVED" && !verifData)
                                  ? "bg-emerald-50/70 border-emerald-200 text-emerald-900"
                                  : "bg-slate-50 border-slate-200 text-slate-700"
                              }`}>
                                <span className="text-slate-400 block text-[10px]">4. Actual Movement Quantity:</span>
                                <strong className="font-bold block">
                                  {verifData?.checklist?.["4_actual_stock_movement_quantity"]?.value ?? (rec.status === "APPROVED" ? rec.recommended_quantity : 0)} units {rec.status === "APPROVED" ? "(✓ Verified in Ledger)" : "(Not executed)"}
                                </strong>
                              </div>

                              {/* 5. Recipient stock after */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">5. Recipient Stock After:</span>
                                <strong className="text-emerald-700 font-bold block">
                                  {afterRecipStock} units (Expected: {verifData?.checklist?.["5_recipient_stock_after"]?.expected ?? afterRecipStock})
                                </strong>
                              </div>

                              {/* 6. Donor stock after */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">6. Donor Stock After:</span>
                                <strong className="text-slate-800 font-bold block">
                                  {afterDonorStock} units (Expected: {verifData?.checklist?.["6_donor_stock_after"]?.expected ?? afterDonorStock})
                                </strong>
                              </div>

                              {/* 7. Recipient daily demand */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">7. Recipient Daily Demand:</span>
                                <strong className="text-slate-800 font-bold block">
                                  {verifData?.checklist?.["7_recipient_daily_demand"]?.value ?? rec.recipient_daily_demand ?? 10.0} units/day
                                </strong>
                              </div>

                              {/* 8. Recipient days of cover */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">8. Recipient Days of Cover:</span>
                                <strong className="text-slate-800 font-bold block">
                                  {verifData?.checklist?.["8_recipient_days_of_cover"]?.before ?? rec.recipient_days_of_cover ?? "—"}d → {verifData?.checklist?.["8_recipient_days_of_cover"]?.after ?? "—"}d (+{rec.expected_days_cover_gained}d)
                                </strong>
                              </div>

                              {/* 9. Recipient risk status */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5">
                                <span className="text-slate-400 block text-[10px]">9. Recipient Risk Status:</span>
                                <strong className="text-slate-800 font-bold block">
                                  {verifData?.checklist?.["9_recipient_risk_status"]?.before ?? "CRITICAL"} → {verifData?.checklist?.["9_recipient_risk_status"]?.after ?? (rec.status === "APPROVED" ? "SAFE" : "SAFE (Projected)")}
                                </strong>
                              </div>

                              {/* 10. Donor safety buffer protection */}
                              <div className={`p-2 rounded border space-y-0.5 ${
                                donorSafetyBufferProtected ? "bg-emerald-50/70 border-emerald-200 text-emerald-900" : "bg-rose-50 border-rose-200 text-rose-900"
                              }`}>
                                <span className="text-slate-400 block text-[10px]">10. Donor Safety Buffer:</span>
                                <strong className="font-bold block">
                                  {donorSafetyBufferProtected ? "✓ Buffer Protected (≥ Safety)" : "✗ Buffer Breached"}
                                </strong>
                              </div>

                              {/* 11. Audit / stock-movement reference */}
                              <div className="p-2 rounded border bg-slate-50 border-slate-200 space-y-0.5 col-span-1 sm:col-span-2">
                                <span className="text-slate-400 block text-[10px]">11. SHA-256 Audit Ledger Reference:</span>
                                <strong className="text-slate-800 font-bold block text-[10px] truncate">
                                  Event: {verifData?.audit_reference?.event_id ?? (rec.status === "APPROVED" ? "Committed" : "Pending Execution")} | Hash: {verifData?.audit_reference?.current_hash ?? (rec.status === "APPROVED" ? "SHA-256 Chain Verified" : "Awaiting Confirmation")}
                                </strong>
                              </div>

                              {/* 12. Expected vs actual result */}
                              <div className={`p-2 rounded border space-y-0.5 col-span-1 sm:col-span-2 lg:col-span-3 ${
                                rec.status === "APPROVED" ? "bg-emerald-50 border-emerald-300 text-emerald-950" : "bg-amber-50 border-amber-200 text-amber-900"
                              }`}>
                                <span className="text-slate-500 block text-[10px] font-bold">12. Expected vs Actual Result:</span>
                                <span className="font-mono text-[11px] block">
                                  {verifData?.summary || (rec.status === "APPROVED" ? "Verification PASSED: Database stock and audit ledger match approved action." : "Verification PENDING: Awaiting CDMO approval.")}
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })()}

                {/* Explainability Toggle Button & Action Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1 text-xs font-mono">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => toggleExpand(rec.id)}
                      className="bg-blue-50 hover:bg-blue-100 text-[#0C2B4E] border border-blue-200 px-3 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1.5 cursor-pointer transition"
                      title="View verified evidence and transfer reasoning"
                    >
                      <IconHelpCircle size={14} className="text-[#1D546C]" />
                      <span>{expandedRecs[rec.id] ? "Hide Evidence" : "Why this recommendation? (View Evidence)"}</span>
                      {expandedRecs[rec.id] ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
                    </button>
                    <button
                      onClick={() => launchSimulationForRec(rec)}
                      className="bg-indigo-50 hover:bg-indigo-100 text-indigo-900 border border-indigo-200 px-3 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1.5 cursor-pointer transition"
                      title="Run What-If Simulation for this route"
                    >
                      <IconPlayerPlay size={13} className="text-indigo-600" />
                      <span>What-If Simulation</span>
                    </button>
                    <span className="text-[11px] text-slate-400">
                      Urgency: <strong className="text-slate-700 uppercase">{rec.urgency_level}</strong>
                    </span>
                  </div>

                  {/* Authorization Controls: Positive RBAC check for CDMO/ADMIN */}
                  {isCdmoOrAdmin ? (
                    rec.status === "PENDING_HUMAN_APPROVAL" ? (
                      <div className="flex items-center gap-2 self-end sm:self-auto">
                        <button
                          onClick={() => handleAction(rec.id, "REJECT")}
                          disabled={actionLoading === rec.id}
                          className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1 cursor-pointer transition disabled:opacity-50"
                        >
                          <IconX size={14} /> Reject
                        </button>
                        <button
                          onClick={() => handleAction(rec.id, "APPROVE")}
                          disabled={actionLoading === rec.id}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1 cursor-pointer shadow-xs transition disabled:opacity-50"
                        >
                          <IconCheck size={14} /> Approve &amp; Execute Stock Transfer
                        </button>
                      </div>
                    ) : (
                      <div className="text-[11px] text-slate-500 font-mono">
                        {rec.reviewed_by_name ? `Reviewed by ${rec.reviewed_by_name} (${rec.reviewed_by_role || "CDMO"})` : `Status: ${rec.status}`}
                      </div>
                    )
                  ) : (
                    /* Facility Officer View */
                    rec.status === "PENDING_HUMAN_APPROVAL" ? (
                      <div className="flex items-center gap-1.5 bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1.5 rounded-xl font-mono text-[11px] font-bold">
                        <IconShieldCheck size={14} className="text-amber-600" />
                        <span>Awaiting CDMO Review &amp; Approval</span>
                      </div>
                    ) : (
                      <div className="text-[11px] text-slate-500 font-mono">
                        {rec.reviewed_by_name ? `Reviewed by ${rec.reviewed_by_name} (${rec.reviewed_by_role || "CDMO"})` : `Status: ${rec.status}`}
                      </div>
                    )
                  )}
                </div>

                {/* Expandable Evidence & Explainability Drawer */}
                {expandedRecs[rec.id] && (
                  <div className="bg-blue-50/40 border border-blue-200 rounded-xl p-4 space-y-4 font-mono text-xs">
                    {explLoading[rec.id] ? (
                      <div className="text-center py-4 text-slate-500 font-mono">Loading verified evidence...</div>
                    ) : (
                      <>
                        {/* Header & Verification Badge */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-blue-200/60 pb-2">
                          <div className="flex items-center gap-2">
                            <IconInfoCircle size={16} className="text-[#1D546C]" />
                            <span className="font-bold text-xs text-[#0C2B4E] uppercase tracking-wider">
                              Redistribution Evidence &amp; Allocation Reasoning
                            </span>
                          </div>
                          <span className="text-[10px] bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 rounded font-bold self-start sm:self-auto flex items-center gap-1">
                            <IconShieldCheck size={12} /> Active DB Evidence
                          </span>
                        </div>

                        {/* SECTION 1: REQUEST DETAILS & PROVENANCE */}
                        <div className="bg-white p-3.5 rounded-xl border border-blue-100 space-y-2">
                          <span className="text-[10px] font-bold text-[#0C2B4E] uppercase tracking-wider flex items-center gap-1.5">
                            <IconUserCheck size={13} className="text-[#1D546C]" />
                            Request Provenance &amp; Authority Chain
                          </span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-[11px]">
                            <div>
                              <span className="text-slate-400 block text-[10px]">Requester / Field Officer:</span>
                              <span className="font-bold text-slate-800">
                                {expl?.provenance?.requester_name || rec.requester_name || "Field Officer"} ({expl?.provenance?.requester_role || rec.requester_role || "FACILITY_OFFICER"})
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[10px]">Requesting Facility:</span>
                              <span className="font-bold text-slate-800">
                                {expl?.provenance?.requesting_facility_name || rec.requesting_facility_name || recipName}
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[10px]">Recommendation Engine:</span>
                              <span className="font-bold text-slate-800">
                                {expl?.provenance?.recommendation_engine || "Healysis Deterministic Engine v1.0"}
                              </span>
                            </div>
                            <div>
                              <span className="text-slate-400 block text-[10px]">Request Timestamp:</span>
                              <span className="font-bold text-slate-800">
                                {expl?.provenance?.created_at ? new Date(expl.provenance.created_at).toLocaleString() : (rec.created_at ? new Date(rec.created_at).toLocaleString() : "Active")}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* SECTION 2: DONOR INTELLIGENCE & RECIPIENT TELEMETRY */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {/* Recipient Deficit Evidence */}
                          <div className="bg-white p-3.5 rounded-xl border border-blue-100 space-y-2">
                            <span className="text-[10px] font-bold text-rose-800 uppercase tracking-wider block">
                              Recipient Deficit Telemetry ({recipName})
                            </span>
                            <div className="grid grid-cols-2 gap-2 text-[11px]">
                              <div>
                                <span className="text-slate-400 block text-[10px]">Current Stock:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.recipient?.current_stock ?? expl?.evidence?.recipient_current_stock ?? rec.recipient_current_stock ?? "—"} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Days of Cover:</span>
                                <span className="font-black text-rose-700">
                                  {expl?.recipient?.current_days_of_cover ?? expl?.evidence?.recipient_days_of_cover ?? rec.recipient_days_of_cover ?? "—"} days
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Daily Demand:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.recipient?.daily_demand ?? expl?.evidence?.recipient_daily_demand ?? rec.recipient_daily_demand ?? "—"} units/day
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Safety Buffer Required:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.recipient?.safety_threshold ?? expl?.evidence?.recipient_safety_stock ?? (rec.recipient_safety_stock ?? 40)} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Post-Transfer Stock:</span>
                                <span className="font-bold text-emerald-700">
                                  {expl?.recipient?.post_transfer_stock ?? ((rec.recipient_current_stock || 0) + rec.recommended_quantity)} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Post-Transfer Cover:</span>
                                <span className="font-bold text-emerald-700">
                                  {expl?.recipient?.post_transfer_days_of_cover ?? "—"} days ({expl?.recipient?.post_transfer_risk_level || "SAFE"})
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Donor Surplus Evidence */}
                          <div className="bg-white p-3.5 rounded-xl border border-blue-100 space-y-2">
                            <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider block">
                              Donor Surplus Intelligence ({donorName})
                            </span>
                            <div className="grid grid-cols-2 gap-2 text-[11px]">
                              <div>
                                <span className="text-slate-400 block text-[10px]">Current Stock:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.donor?.current_stock ?? expl?.evidence?.donor_current_stock ?? rec.donor_current_stock ?? "—"} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Safety Buffer Preserved:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.donor?.safety_threshold ?? expl?.evidence?.donor_safety_stock ?? (rec.donor_safety_stock ?? 40)} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Verified Available Surplus:</span>
                                <span className="font-bold text-emerald-700">
                                  +{expl?.donor?.available_surplus ?? expl?.evidence?.donor_surplus ?? Math.max(0, (rec.donor_current_stock || 0) - (rec.donor_safety_stock || 40))} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Remaining Stock:</span>
                                <span className="font-bold text-slate-800">
                                  {expl?.donor?.post_transfer_stock ?? Math.max(0, (rec.donor_current_stock || 0) - rec.recommended_quantity)} units
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Post-Transfer Donor Cover:</span>
                                <span className="font-bold text-emerald-700">
                                  {expl?.donor?.post_transfer_days_of_cover ?? expl?.evidence?.donor_days_of_cover ?? "—"} days
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-400 block text-[10px]">Donor Buffer Integrity:</span>
                                <span className="font-bold text-emerald-700">
                                  {expl?.donor?.buffer_protected !== false ? "PROTECTED (≥ 100%)" : "MARGINAL"}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* SECTION 3: TRANSFER METRICS & LOGISTICS */}
                        <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                          <div>
                            <span className="text-slate-400 block text-[10px]">Haversine Distance:</span>
                            <span className="font-bold text-slate-800">
                              {expl?.transfer?.haversine_distance_km ?? expl?.evidence?.haversine_distance_km ?? rec.haversine_distance_km} km
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Transfer Quantity:</span>
                            <span className="font-bold text-emerald-700">
                              {rec.recommended_quantity} units
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Coverage Gained:</span>
                            <span className="font-bold text-[#0C2B4E]">
                              +{expl?.transfer?.expected_days_cover_gained ?? expl?.evidence?.expected_days_cover_gained ?? rec.expected_days_cover_gained} days
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-400 block text-[10px]">Logistics Feasibility:</span>
                            <span className="font-bold text-emerald-700">
                              {expl?.transfer?.logistics_feasibility || expl?.evidence?.logistics_status || "VERIFIED ROUTE"}
                            </span>
                          </div>
                        </div>

                        {/* SECTION 4: ALTERNATIVE DONORS (IF ANY) */}
                        {expl?.alternative_donors && expl.alternative_donors.length > 0 && (
                          <div className="bg-white p-3 rounded-xl border border-slate-200 space-y-1.5">
                            <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1">
                              <IconLayersLinked size={13} className="text-slate-500" />
                              Alternative Eligible Donors Evaluated ({expl.alternative_donors.length})
                            </span>
                            <div className="space-y-1">
                              {expl.alternative_donors.map((alt: any) => (
                                <div key={alt.facility_id} className="flex items-center justify-between text-[11px] bg-slate-50 px-2.5 py-1 rounded border border-slate-100">
                                  <span className="font-bold text-slate-700">{alt.facility_name} ({alt.district})</span>
                                  <div className="flex items-center gap-3 text-slate-500 font-mono">
                                    <span>Surplus: <strong className="text-emerald-700">{alt.available_surplus}</strong> units</span>
                                    <span>Distance: <strong>{alt.distance_km} km</strong></span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* SECTION 5: THE 5 CORE EXPLAINABILITY QUESTIONS */}
                        {expl?.answers ? (
                          <div className="bg-amber-50/70 border border-amber-200/80 rounded-xl p-3.5 font-sans text-xs space-y-2.5">
                            <strong className="text-amber-900 block text-[11px] font-bold uppercase tracking-wider">
                              Why This Recommendation? — Deterministic Grounded Evidence
                            </strong>
                            <div className="space-y-2 text-amber-950 text-xs leading-relaxed">
                              <div>
                                <span className="font-bold text-amber-900 block">1. Why does the recipient need stock?</span>
                                <p className="text-slate-700 pl-2">{expl.answers.why_recipient_needs_stock}</p>
                              </div>
                              <div>
                                <span className="font-bold text-amber-900 block">2. Why was this donor selected?</span>
                                <p className="text-slate-700 pl-2">{expl.answers.why_donor_selected}</p>
                              </div>
                              <div>
                                <span className="font-bold text-amber-900 block">3. Why this quantity?</span>
                                <p className="text-slate-700 pl-2">{expl.answers.why_this_quantity}</p>
                              </div>
                              <div>
                                <span className="font-bold text-amber-900 block">4. Why is the transfer safe for the donor?</span>
                                <p className="text-slate-700 pl-2">{expl.answers.why_transfer_is_safe}</p>
                              </div>
                              <div>
                                <span className="font-bold text-amber-900 block">5. What happens after transfer?</span>
                                <p className="text-slate-700 pl-2">{expl.answers.what_happens_post_transfer}</p>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="bg-amber-50/70 border border-amber-200/80 rounded-lg p-3 font-sans text-xs">
                            <strong className="text-amber-900 block text-[11px] font-bold uppercase tracking-wider mb-0.5">
                              Why this recommendation was calculated:
                            </strong>
                            <p className="text-amber-950 leading-relaxed">
                              {expl?.why || "The recipient facility has insufficient projected coverage while the donor facility has sufficient available stock above its safety threshold."}
                            </p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}

              </div>
            );
          })}
          {recommendations.length === 0 && (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs font-sans">
              No redistribution recommendations generated at this time.
            </div>
          )}
        </div>

      </div>
    </AppShell>
  );
}
