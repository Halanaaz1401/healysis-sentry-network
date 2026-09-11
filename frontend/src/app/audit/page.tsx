"use client";

import React, { useState, useEffect, useCallback } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import {
  IconClipboardList,
  IconRefresh,
  IconShieldCheck,
  IconLock,
  IconAlertTriangle,
  IconCheck,
  IconHash,
  IconUser,
  IconBuildingHospital,
  IconFilter,
  IconDatabase,
} from "@tabler/icons-react";

// Types
interface AuditEvent {
  id: number;
  event_id: string;
  timestamp: string;
  actor_user_id: number | null;
  actor_name: string | null;
  actor_email: string | null;
  action: string;
  event_type: string;
  facility_id: number | null;
  facility_name: string | null;
  facility_code: string | null;
  payload_json: Record<string, unknown> | null;
  previous_hash: string;
  current_hash: string;
  is_tampered: boolean;
  created_at: string;
}

const EVENT_TYPE_FILTERS = [
  { value: "", label: "All Events" },
  { value: "TRANSACTION", label: "Transaction" },
  { value: "RULE_ALERT", label: "Rule Alert" },
  { value: "REQUISITION", label: "Requisition" },
  { value: "SYSTEM", label: "System" },
];

const EVENT_TYPE_BADGE: Record<string, string> = {
  TRANSACTION: "bg-blue-50 text-blue-800 border-blue-200",
  RULE_ALERT: "bg-amber-50 text-amber-800 border-amber-200",
  REQUISITION: "bg-purple-50 text-purple-800 border-purple-200",
  SYSTEM: "bg-slate-100 text-slate-700 border-slate-200",
};

function formatTimestamp(ts: string): string {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
      hour12: true,
    }).format(new Date(ts));
  } catch {
    return ts;
  }
}

function truncateHash(hash: string, chars = 12): string {
  if (!hash) return "---";
  if (hash.length <= chars * 2 + 3) return hash;
  return hash.slice(0, chars) + "..." + hash.slice(-chars);
}

function HashBadge({ hash, label }: { hash: string; label: string }) {
  return (
    <div className="space-y-0.5">
      <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider font-mono block">
        {label}
      </span>
      <span
        title={hash}
        className="font-mono text-[10px] text-[#1D546C] bg-slate-50 border border-slate-200 px-2 py-0.5 rounded block truncate max-w-[200px] cursor-default"
      >
        {hash === "GENESIS_ROOT_HEALYSIS_000" ? "GENESIS ROOT" : truncateHash(hash)}
      </span>
    </div>
  );
}

function TamperBadge({ tampered }: { tampered: boolean }) {
  if (tampered) {
    return (
      <span className="inline-flex items-center gap-1 bg-rose-50 border border-rose-300 text-rose-800 text-[9px] font-extrabold uppercase px-2 py-0.5 rounded">
        <IconAlertTriangle size={10} /> TAMPERED
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 bg-emerald-50 border border-emerald-200 text-emerald-800 text-[9px] font-extrabold uppercase px-2 py-0.5 rounded">
      <IconCheck size={10} /> VERIFIED
    </span>
  );
}

export default function AuditPage() {
  const { user } = useAuth();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);

  const isCDMOOrAdmin = user?.role === "CDMO" || user?.role === "ADMIN";

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (eventTypeFilter) params.set("event_type", eventTypeFilter);
      const data = await apiFetch<AuditEvent[]>(
        "/api/v1/audit/events?" + params.toString()
      );
      setEvents(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load audit ledger.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [eventTypeFilter]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  if (!isCDMOOrAdmin) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E] flex items-center gap-2">
              <IconClipboardList className="text-[#1D546C]" size={24} />
              Audit Ledger
            </h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              SHA-256 Tamper-Evident Cryptographic Ledger
            </p>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-8 flex flex-col items-center gap-4 text-center">
            <div className="h-14 w-14 bg-amber-100 rounded-2xl flex items-center justify-center">
              <IconLock size={28} className="text-amber-700" />
            </div>
            <div>
              <p className="text-sm font-bold text-amber-900">Access Restricted</p>
              <p className="text-xs text-amber-700 mt-1 leading-relaxed max-w-xs">
                The Audit Ledger is accessible to CDMO Directors and System Admins only.
                Your current role ({user?.role}) does not have permission to view this page.
              </p>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  const tamperedCount = events.filter((e) => e.is_tampered).length;

  return (
    <AppShell>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E] flex items-center gap-2">
              <IconClipboardList className="text-[#1D546C]" size={24} />
              Audit Ledger
            </h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              SHA-256 Tamper-Evident Cryptographic Ledger — Read-Only
            </p>
          </div>
          <button
            onClick={fetchEvents}
            disabled={loading}
            className="self-start sm:self-auto inline-flex items-center gap-2 bg-white hover:bg-slate-50 active:scale-95 border border-slate-200 text-[#0C2B4E] px-4 py-2 rounded-xl text-xs font-bold transition shadow-xs cursor-pointer disabled:opacity-50"
          >
            <IconRefresh size={15} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        {/* Security callout */}
        <div className="bg-[#0C2B4E] bg-opacity-5 border border-slate-200 p-4 rounded-xl flex items-start gap-3">
          <IconShieldCheck size={20} className="text-[#1D546C] shrink-0 mt-0.5" />
          <div className="text-xs space-y-0.5">
            <span className="font-bold text-[#0C2B4E]">Tamper-Evident Chain Ledger</span>
            <p className="text-slate-600 leading-relaxed">
              Each audit block is cryptographically linked to the previous block via SHA-256 hashing.
              Any modification to a historical record will cause hash verification to fail and mark the block as TAMPERED.
              This ledger is read-only.
            </p>
          </div>
        </div>

        {/* Stats strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Total Events", value: events.length, Icon: IconDatabase, color: "text-[#1D546C]", bg: "bg-slate-50" },
            { label: "Transactions", value: events.filter((e) => e.event_type === "TRANSACTION").length, Icon: IconHash, color: "text-blue-700", bg: "bg-blue-50" },
            { label: "Verified Blocks", value: events.filter((e) => !e.is_tampered).length, Icon: IconCheck, color: "text-emerald-700", bg: "bg-emerald-50" },
            { label: "Tampered", value: tamperedCount, Icon: IconAlertTriangle, color: tamperedCount > 0 ? "text-rose-700" : "text-slate-400", bg: tamperedCount > 0 ? "bg-rose-50" : "bg-slate-50" },
          ].map(({ label, value, Icon, color, bg }) => (
            <div key={label} className="bg-white border border-slate-200 rounded-xl p-4 flex items-center gap-3 shadow-xs">
              <div className={"h-9 w-9 rounded-lg " + bg + " flex items-center justify-center shrink-0"}>
                <Icon size={18} className={color} />
              </div>
              <div>
                <p className="text-lg font-black text-[#0C2B4E] leading-none">{value}</p>
                <p className="text-[10px] text-slate-500 font-mono uppercase tracking-wide mt-0.5">{label}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] text-slate-500 font-mono uppercase tracking-wider flex items-center gap-1">
            <IconFilter size={12} /> Filter:
          </span>
          {EVENT_TYPE_FILTERS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setEventTypeFilter(value)}
              className={
                "text-[10px] font-bold uppercase px-3 py-1.5 rounded-full border transition cursor-pointer " +
                (eventTypeFilter === value
                  ? "bg-[#0C2B4E] text-white border-[#0C2B4E]"
                  : "bg-white text-slate-600 border-slate-200 hover:border-[#1D546C] hover:text-[#1D546C]")
              }
            >
              {label}
            </button>
          ))}
        </div>

        {/* Loading */}
        {loading && (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 flex flex-col items-center gap-4 text-center shadow-xs">
            <div className="h-10 w-10 rounded-full border-2 border-[#1D546C] border-t-transparent animate-spin" />
            <p className="text-xs text-slate-500 font-mono">Loading audit ledger blocks...</p>
          </div>
        )}

        {/* Error */}
        {!loading && error && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-8 flex flex-col items-center gap-3 text-center">
            <IconAlertTriangle size={28} className="text-rose-500" />
            <div>
              <p className="text-sm font-bold text-rose-900">Failed to Load Audit Ledger</p>
              <p className="text-xs text-rose-700 mt-1 max-w-md leading-relaxed">{error}</p>
            </div>
            <button
              onClick={fetchEvents}
              className="mt-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty */}
        {!loading && !error && events.length === 0 && (
          <div className="bg-white border border-slate-200 rounded-2xl p-12 flex flex-col items-center gap-4 text-center shadow-xs">
            <div className="h-14 w-14 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center">
              <IconClipboardList size={28} className="text-slate-300" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-600">No Audit Events Found</p>
              <p className="text-xs text-slate-400 mt-1">
                {eventTypeFilter
                  ? "No " + eventTypeFilter + " events recorded yet."
                  : "No audit events have been recorded yet. Approve a redistribution recommendation to generate the first ledger block."}
              </p>
            </div>
          </div>
        )}

        {/* Ledger table */}
        {!loading && !error && events.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
            {/* Table header */}
            <div className="grid grid-cols-12 gap-2 px-4 py-3 bg-slate-50 border-b border-slate-200 text-[9.5px] font-extrabold uppercase text-slate-400 tracking-wider font-mono">
              <div className="col-span-1">#</div>
              <div className="col-span-2">Timestamp</div>
              <div className="col-span-2">Actor</div>
              <div className="col-span-3">Action</div>
              <div className="col-span-2">Facility</div>
              <div className="col-span-1">Type</div>
              <div className="col-span-1">Status</div>
            </div>

            <div className="divide-y divide-slate-100">
              {events.map((evt) => {
                const isExpanded = expanded === evt.id;
                return (
                  <div key={evt.id}>
                    <button
                      onClick={() => setExpanded(isExpanded ? null : evt.id)}
                      className="w-full grid grid-cols-12 gap-2 px-4 py-3 hover:bg-slate-50 transition-colors text-left items-center cursor-pointer"
                      aria-expanded={isExpanded}
                      aria-label={"Audit event " + evt.event_id}
                    >
                      <div className="col-span-1">
                        <span className="font-mono text-[10px] text-slate-400">#{evt.id}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-[10px] font-mono text-slate-600 block leading-snug">
                          {formatTimestamp(evt.timestamp)}
                        </span>
                      </div>
                      <div className="col-span-2 flex items-center gap-1.5 min-w-0">
                        <div className="h-5 w-5 rounded-md bg-slate-100 flex items-center justify-center shrink-0">
                          <IconUser size={11} className="text-[#1D546C]" />
                        </div>
                        <div className="min-w-0">
                          <span className="text-[10px] font-semibold text-slate-700 block truncate">
                            {evt.actor_name ?? "System"}
                          </span>
                          {evt.actor_email && (
                            <span className="text-[9px] text-slate-400 font-mono block truncate">{evt.actor_email}</span>
                          )}
                        </div>
                      </div>
                      <div className="col-span-3 min-w-0">
                        <span className="text-[10px] font-bold text-[#0C2B4E] font-mono block truncate">{evt.action}</span>
                        <span className="text-[9px] text-slate-400 font-mono block truncate">{evt.event_id}</span>
                      </div>
                      <div className="col-span-2 flex items-center gap-1.5 min-w-0">
                        {evt.facility_name ? (
                          <>
                            <IconBuildingHospital size={11} className="text-slate-400 shrink-0" />
                            <div className="min-w-0">
                              <span className="text-[10px] text-slate-600 block truncate">{evt.facility_name}</span>
                              {evt.facility_code && (
                                <span className="text-[9px] text-slate-400 font-mono block truncate">{evt.facility_code}</span>
                              )}
                            </div>
                          </>
                        ) : (
                          <span className="text-[10px] text-slate-400 font-mono">---</span>
                        )}
                      </div>
                      <div className="col-span-1">
                        <span className={"text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded border block text-center " + (EVENT_TYPE_BADGE[evt.event_type] ?? "bg-slate-100 text-slate-600 border-slate-200")}>
                          {evt.event_type.replace("_", " ")}
                        </span>
                      </div>
                      <div className="col-span-1 flex justify-end">
                        <TamperBadge tampered={evt.is_tampered} />
                      </div>
                    </button>

                    {/* Expanded hash detail panel */}
                    {isExpanded && (
                      <div className="px-4 pb-4 bg-slate-50 border-t border-slate-100">
                        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                          <HashBadge label="Current Hash (SHA-256)" hash={evt.current_hash} />
                          <HashBadge label="Previous Hash (SHA-256)" hash={evt.previous_hash} />
                          <div className="space-y-0.5">
                            <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider font-mono block">Event ID</span>
                            <span className="font-mono text-[10px] text-slate-700 bg-white border border-slate-200 px-2 py-0.5 rounded block">{evt.event_id}</span>
                          </div>
                          <div className="space-y-0.5">
                            <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider font-mono block">Recorded At</span>
                            <span className="font-mono text-[10px] text-slate-700 bg-white border border-slate-200 px-2 py-0.5 rounded block">{formatTimestamp(evt.created_at)}</span>
                          </div>
                        </div>

                        {evt.payload_json && Object.keys(evt.payload_json).length > 0 && (
                          <div className="mt-3 space-y-1">
                            <span className="text-[9px] uppercase font-bold text-slate-400 tracking-wider font-mono block">Payload</span>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(evt.payload_json).map(([k, v]) => (
                                <div key={k} className="bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 text-[10px] font-mono">
                                  <span className="text-slate-400 mr-1">{k}:</span>
                                  <span className="text-[#0C2B4E] font-semibold">{String(v)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
              <span className="text-[10px] text-slate-400 font-mono">
                Showing {events.length} ledger block{events.length !== 1 ? "s" : ""}
                {eventTypeFilter ? " filtered by " + eventTypeFilter : ""}
              </span>
              <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                <IconLock size={11} className="text-emerald-600" />
                Read-Only · CDMO / ADMIN Access
              </span>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
