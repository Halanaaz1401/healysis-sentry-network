"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import { 
  IconTruckDelivery, 
  IconRefresh, 
  IconShieldCheck, 
  IconSparkles, 
  IconCheck, 
  IconX,
  IconArrowRight
} from "@tabler/icons-react";

export default function RecommendationsPage() {
  const { user } = useAuth();
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [banner, setBanner] = useState<{ type: "success" | "error"; msg: string } | null>(null);

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
    try {
      setGenerating(true);
      setBanner(null);
      const newRecs = await apiFetch<any[]>("/api/v1/recommendations/generate", { method: "POST" });
      setRecommendations(newRecs);
      setBanner({ type: "success", msg: "Cross-district stock redistribution engine generated new candidate routes." });
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Generating redistribution recommendations requires CDMO or ADMIN role." });
    } finally {
      setGenerating(false);
    }
  };

  const handleAction = async (id: number, action: "APPROVE" | "REJECT") => {
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
          ? `Recommendation #${id} approved! Inventory stock transfer committed successfully and forecast recalculated.` 
          : `Recommendation #${id} rejected.` 
      });
      await fetchRecommendations();
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Action requires CDMO or ADMIN role." });
    } finally {
      setActionLoading(null);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [user]);

  return (
    <AppShell>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E]">Inter-Facility Resource Redistribution</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Deterministic Haversine Candidate Scoring &amp; Donor Stock Balance Optimization
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleGenerate}
              disabled={generating || user?.role === "FACILITY_OFFICER"}
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-xs cursor-pointer disabled:opacity-50 transition"
            >
              <IconSparkles size={16} className={generating ? "animate-spin" : ""} />
              {generating ? "Calculating Routes..." : "Run Redistribution Engine"}
            </button>
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

        {/* Non-Autonomous Banner */}
        <div className="bg-amber-50 border border-amber-200 p-4 rounded-2xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-amber-900 text-xs">
            <IconShieldCheck size={20} className="text-amber-600 shrink-0" />
            <div>
              <span className="font-bold uppercase tracking-wider block font-mono">MANDATORY HUMAN APPROVAL BOUNDARY</span>
              <p className="text-amber-700">Physical stock transfers are strictly non-autonomous. Approval commits atomic inventory updates across donor and recipient nodes.</p>
            </div>
          </div>
        </div>

        {/* Recommendations List */}
        <div className="space-y-4">
          {recommendations.map((rec) => {
            const donorName = rec.donor_facility_name || `Facility #${rec.donor_facility_id}`;
            const donorLoc = rec.donor_district ? `${rec.donor_district}, ${rec.donor_state}` : `ID: #${rec.donor_facility_id}`;
            const recipName = rec.recipient_facility_name || `Facility #${rec.recipient_facility_id}`;
            const recipLoc = rec.recipient_district ? `${rec.recipient_district}, ${rec.recipient_state}` : `ID: #${rec.recipient_facility_id}`;
            const itemName = rec.item_name || rec.item_code;

            return (
              <div key={rec.id} className="bg-white p-5 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
                
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-xs font-black text-[#0C2B4E]">Recommendation #{rec.id}</span>
                    <span className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-bold">
                      {itemName} ({rec.item_code})
                    </span>
                  </div>
                  <span className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded font-mono ${
                    rec.status === "PENDING_HUMAN_APPROVAL" ? "bg-amber-100 text-amber-900 border border-amber-300" :
                    rec.status === "APPROVED" ? "bg-emerald-100 text-emerald-900 border border-emerald-300" :
                    "bg-slate-100 text-slate-700 border border-slate-300"
                  }`}>
                    {rec.status}
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

                <p className="text-xs text-slate-600 font-mono bg-slate-50/80 p-3 rounded-xl border border-slate-200">
                  <strong className="text-slate-700">Reason:</strong> {rec.reason}
                </p>

                <div className="flex items-center justify-between pt-1 text-xs font-mono">
                  <div className="text-[11px] text-slate-400">
                    Urgency: <strong className="text-slate-700 uppercase">{rec.urgency_level}</strong>
                  </div>

                  {user?.role !== "FACILITY_OFFICER" && rec.status === "PENDING_HUMAN_APPROVAL" && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleAction(rec.id, "REJECT")}
                        disabled={actionLoading === rec.id}
                        className="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1 cursor-pointer"
                      >
                        <IconX size={14} /> Reject
                      </button>
                      <button
                        onClick={() => handleAction(rec.id, "APPROVE")}
                        disabled={actionLoading === rec.id}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1 cursor-pointer shadow-xs"
                      >
                        <IconCheck size={14} /> Approve &amp; Execute Stock Transfer
                      </button>
                    </div>
                  )}
                </div>

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
