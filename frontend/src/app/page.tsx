"use client";

import React, { useState, useEffect } from "react";
import { Analytics } from "@vercel/analytics/next";
import { 
  IconShieldCheck, 
  IconAlertOctagon, 
  IconDatabase, 
  IconActivity, 
  IconSparkles, 
  IconRefresh, 
  IconCircleCheck, 
  IconFileText, 
  IconLock, 
  IconSearch, 
  IconBuildingHospital,
  IconReportMedical,
  IconLanguage,
  IconArrowDown,
  IconAlertCircle,
  IconSend,
  IconInfoCircle,
  IconChevronRight,
  IconCheck,
  IconTruckDelivery,
  IconUserCheck,
  IconX,
  IconClockHour4,
  IconPrinter
} from "@tabler/icons-react";

interface EventRecord {
  event_id: string;
  facility_id: string;
  facility_name: string;
  state_id: string;
  timestamp: string;
  action_type: string;
  item_id: string;
  quantity: number;
  patient_footfall: number;
  bed_occupancy: number;
  patient_token: string;
  current_hash: string;
  is_flagged: boolean;
  severity: string;
  violations: string;
}

interface RequisitionItem {
  req_id: string;
  timestamp: string;
  requester_node: string;
  source_facility: string;
  target_facility: string;
  item_id: string;
  quantity: number;
  urgency_reason: string;
  status: "PENDING_APPROVAL" | "APPROVED_AND_DISPATCHED" | "REJECTED";
  reviewed_by: string | null;
}

const BACKEND_URL = "https://healysis-sentry-network.onrender.com";

const RBAC_USERS = [
  {
    userId: "USR-OD-KHU-101",
    name: "Dr. A. Nayak (MO)",
    role: "Facility Staff",
    facilityId: "CHC-OD-KHU-001",
    facilityName: "Jatni CHC (Khordha)",
    shortLabel: "Jatni CHC",
    state: "OD"
  },
  {
    userId: "USR-OD-CTC-204",
    name: "S. Patra (Pharmacist)",
    role: "Facility Staff",
    facilityId: "UPHC-OD-CTC-002",
    facilityName: "UPHC MS Das (Kafla Bazar)",
    shortLabel: "Cuttack (Kafla Bazar)",
    state: "OD"
  },
  {
    userId: "USR-OD-PURI-309",
    name: "R. Mohanty (Inventory)",
    role: "Facility Staff",
    facilityId: "PHC-OD-PURI-004",
    facilityName: "Pipili PHC (Puri)",
    shortLabel: "Pipili PHC (Puri)",
    state: "OD"
  },
  {
    userId: "USR-WB-KOL-501",
    name: "T. Banerjee (Nurse Admin)",
    role: "Facility Staff",
    facilityId: "UPHC-WB-KOL-012",
    facilityName: "Behala Urban PHC (Kolkata)",
    shortLabel: "Behala PHC (Kolkata)",
    state: "WB"
  },
  {
    userId: "USR-CDMO-HQ-001",
    name: "CDMO District Director",
    role: "District Chief Auditor",
    facilityId: "ALL_NODES",
    facilityName: "State Health Director Hub",
    shortLabel: "CDMO Central Hub",
    state: "OD"
  }
];

const FACILITIES = [
  { id: "CHC-OD-KHU-001", name: "Jatni CHC (Khordha)", state: "OD", type: "CHC Hub" },
  { id: "UPHC-OD-CTC-002", name: "UPHC MS Das (Kafla Bazar)", state: "OD", type: "Urban PHC" },
  { id: "PHC-OD-PURI-004", name: "Pipili PHC (Puri)", state: "OD", type: "Rural PHC" },
  { id: "UPHC-WB-KOL-012", name: "Behala Urban PHC (Kolkata)", state: "WB", type: "Metro UPHC" },
  { id: "PHC-WB-S24P-008", name: "Diamond Harbour PHC", state: "WB", type: "Coastal PHC" }
];

const AVAILABLE_MEDICINES = [
  { id: "MED-ORS-SACHET", name: "ORS Sachet (Oral Rehydration Salts)" },
  { id: "MED-PARACET-500MG", name: "Paracetamol 500mg (Fever & Body Pain)" },
  { id: "MED-VAPORUB-BALM", name: "Pain Balm / Vaporub (Cold & Headache)" },
  { id: "MED-CETIRIZINE-10", name: "Cetirizine 10mg (Cold & Allergy)" },
  { id: "MED-ANTACID-GEL", name: "Antacid / Digene (Acidity & Gas)" },
  { id: "MED-P-IODINE-OINT", name: "Betadine / Povidone Iodine (Wound Antiseptic)" },
  { id: "MED-BANDAGE-COTTON", name: "Absorbent Cotton & Bandage Roll (First Aid)" },
  { id: "MED-ZINC-20MG", name: "Zinc Sulphate Tablets 20mg (Pediatric Care)" },
  { id: "MED-AMOXICILLIN-250", name: "Amoxicillin 250mg (Antibiotic Capsule)" },
  { id: "MED-INSULIN-100IU", name: "Insulin 100IU Injection (Cold Chain)" }
];

export default function HealysisDashboard() {
  const [currentUser, setCurrentUser] = useState(RBAC_USERS[0]);
  const [scopeFilter, setScopeFilter] = useState<"MY_FACILITY" | "ALL_FACILITIES">("ALL_FACILITIES");

  const [events, setEvents] = useState<EventRecord[]>([]);
  const [requisitions, setRequisitions] = useState<RequisitionItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [backendOffline, setBackendOffline] = useState<boolean>(false);
  const [selectedEvent, setSelectedEvent] = useState<EventRecord | null>(null);
  const [incidentReport, setIncidentReport] = useState<string | null>(null);
  const [generatingReport, setGeneratingReport] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"ALL" | "FLAGGED">("ALL");
  const [lang, setLang] = useState<"EN" | "HI">("EN");
  const [lastSubmittedId, setLastSubmittedId] = useState<string | null>(null);

  // Verification states
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyStatus, setVerifyStatus] = useState<string | null>(null);

  // Two-Tier Requisition & Approval States
  const [reqSource, setReqSource] = useState<string>("UPHC MS Das (Kafla Bazar)");
  const [reqTarget, setReqTarget] = useState<string>("Jatni CHC (Khordha)");
  const [reqItem, setReqItem] = useState<string>("MED-ORS-SACHET");
  const [reqQuantity, setReqQuantity] = useState<number>(50);
  const [reqReason, setReqReason] = useState<string>("Critical Buffer Depletion");
  const [reqSubmitting, setReqSubmitting] = useState<boolean>(false);
  const [reqActionLoading, setReqActionLoading] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    facility_id: RBAC_USERS[0].facilityId,
    facility_name: RBAC_USERS[0].facilityName,
    state_id: RBAC_USERS[0].state,
    action_type: "DISPENSE",
    item_id: "MED-ORS-SACHET",
    quantity: 10,
    patient_footfall: 22,
    bed_occupancy: 8,
    patient_token: "PAT-IN-8921",
    reporter_id: RBAC_USERS[0].userId
  });
  const [submitting, setSubmitting] = useState(false);
  const [simulating, setSimulating] = useState(false);

  // Advisor state
  const [queryInput, setQueryInput] = useState<string>("");
  const [queryResponse, setQueryResponse] = useState<string | null>(null);
  const [querying, setQuerying] = useState<boolean>(false);

  const isCDMO = currentUser.userId === "USR-CDMO-HQ-001";

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${BACKEND_URL}/api/v1/reports`);
      if (res.ok) {
        const data = await res.json();
        setEvents(data);
        setBackendOffline(false);
      } else {
        setBackendOffline(true);
      }
    } catch (err) {
      setBackendOffline(true);
    } finally {
      setLoading(false);
    }
  };

  const fetchRequisitions = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/requisitions`);
      if (res.ok) {
        const data = await res.json();
        setRequisitions(data);
      }
    } catch (err) {
      console.error("Failed to load requisitions", err);
    }
  };

  useEffect(() => {
    fetchEvents();
    fetchRequisitions();
    const interval = setInterval(() => {
      fetchEvents();
      fetchRequisitions();
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleUserSwitch = (userId: string) => {
    const user = RBAC_USERS.find(u => u.userId === userId) || RBAC_USERS[0];
    setCurrentUser(user);
    if (user.facilityId !== "ALL_NODES") {
      setFormData(prev => ({
        ...prev,
        facility_id: user.facilityId,
        facility_name: user.facilityName,
        state_id: user.state,
        reporter_id: user.userId
      }));
      setReqTarget(user.facilityName);
      const otherFac = FACILITIES.find(f => f.name !== user.facilityName)?.name || "UPHC MS Das (Kafla Bazar)";
      setReqSource(otherFac);
    }
  };

  const handleFacilityChange = (facId: string) => {
    const found = FACILITIES.find((f) => f.id === facId);
    if (found) {
      setFormData({
        ...formData,
        facility_id: found.id,
        facility_name: found.name,
        state_id: found.state
      });
    }
  };

  const handleIngest = async (e?: React.FormEvent, overrideData?: typeof formData) => {
    if (e) e.preventDefault();
    const payload = overrideData || formData;
    try {
      setSubmitting(true);
      const res = await fetch(`${BACKEND_URL}/api/v1/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const data = await res.json();
        setLastSubmittedId(data.event_id);
        await fetchEvents();
        setTimeout(() => setLastSubmittedId(null), 4000);
      }
    } catch (err) {
      console.error("Ingestion failed", err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleSimulateGhostDrawdown = async () => {
    try {
      setSimulating(true);
      const anomalyPayload = {
        facility_id: formData.facility_id,
        facility_name: formData.facility_name,
        state_id: formData.state_id,
        action_type: "DISPENSE",
        item_id: "MED-ORS-SACHET",
        quantity: 85,
        patient_footfall: 1,
        bed_occupancy: 2,
        patient_token: "",
        reporter_id: currentUser.userId
      };

      setFormData(anomalyPayload);
      await handleIngest(undefined, anomalyPayload);
    } catch (err) {
      console.error("Simulation failed", err);
    } finally {
      setSimulating(false);
    }
  };

  const handleExplain = async (evt: EventRecord) => {
    try {
      setSelectedEvent(evt);
      setGeneratingReport(true);
      setIncidentReport(null);

      const res = await fetch(`${BACKEND_URL}/api/v1/anomalies/${evt.event_id}/explain`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setIncidentReport(data.incident_report);
      }
    } catch (err) {
      setIncidentReport("Failed to generate incident case report via Gemini API.");
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleLedgerVerification = async () => {
    try {
      setVerifying(true);
      setVerifyStatus(null);
      const res = await fetch(`${BACKEND_URL}/api/v1/ledger/verify`);
      if (res.ok) {
        const data = await res.json();
        if (data.is_valid) {
          setVerifyStatus(`✅ SHA-256 Ledger Integrity Passed: All ${data.verified_hashes} block hashes cryptographically verified from genesis root.`);
        } else {
          setVerifyStatus(`❌ Tamper Detected at ${data.broken_at}! Hash mismatch in chain sequence.`);
        }
      }
    } catch (err) {
      setVerifyStatus("Ledger audit failed. Backend unavailable.");
    } finally {
      setVerifying(false);
    }
  };

  const handleCreateRequisition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reqSource === reqTarget) {
      alert("Source and Target health facilities cannot be the same!");
      return;
    }

    try {
      setReqSubmitting(true);
      const res = await fetch(`${BACKEND_URL}/api/v1/requisitions/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester_node: currentUser.shortLabel,
          source_facility: reqSource,
          target_facility: reqTarget,
          item_id: reqItem,
          quantity: reqQuantity,
          urgency_reason: reqReason
        })
      });
      if (res.ok) {
        alert(`✅ Requisition Request Logged! Sent to CDMO District Director for verification & authorization.`);
        fetchRequisitions();
      }
    } catch (err) {
      alert("Failed to submit requisition request.");
    } finally {
      setReqSubmitting(false);
    }
  };

  const handleAuthorizeAction = async (reqId: string, action: "APPROVE" | "REJECT") => {
    try {
      setReqActionLoading(reqId);
      const res = await fetch(`${BACKEND_URL}/api/v1/requisitions/${reqId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: action,
          reviewed_by: "CDMO-DISTRICT-DIRECTOR"
        })
      });
      if (res.ok) {
        const data = await res.json();
        alert(data.message);
        await Promise.all([fetchRequisitions(), fetchEvents()]);
      }
    } catch (err) {
      alert("Authorization execution failed.");
    } finally {
      setReqActionLoading(null);
    }
  };

  const handleDownloadPDF = () => {
    if (!selectedEvent || !incidentReport) return;
    const printWin = window.open("", "_blank");
    if (printWin) {
      printWin.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>Forensic Report - ${selectedEvent.event_id}</title>
            <style>
              body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; 
                padding: 40px; 
                color: #0f172a; 
                line-height: 1.6;
              }
              .header {
                border-bottom: 2px solid #0c2b4e;
                padding-bottom: 12px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
              }
              h1 { 
                font-size: 20px; 
                color: #0c2b4e; 
                margin: 0;
                font-weight: 800;
              }
              .meta-grid { 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 10px; 
                background: #f8fafc; 
                padding: 16px; 
                border: 1px solid #e2e8f0; 
                border-radius: 8px; 
                margin-bottom: 24px;
                font-size: 12px;
                font-family: monospace;
              }
              pre { 
                white-space: pre-wrap; 
                font-family: inherit; 
                font-size: 13px; 
                background: #ffffff; 
                padding: 20px; 
                border: 1px solid #cbd5e1; 
                border-radius: 8px; 
                line-height: 1.7;
              }
              .footer { 
                margin-top: 40px; 
                font-size: 11px; 
                color: #64748b; 
                border-top: 1px solid #e2e8f0; 
                padding-top: 12px; 
                text-align: center;
              }
            </style>
          </head>
          <body>
            <div class="header">
              <h1>HEALYSIS SENTRY NETWORK — FORENSIC AUDIT REPORT</h1>
            </div>
            <div class="meta-grid">
              <div><strong>Case Event ID:</strong> ${selectedEvent.event_id}</div>
              <div><strong>Facility Node:</strong> ${selectedEvent.facility_name}</div>
              <div><strong>State Jurisdiction:</strong> ${selectedEvent.state_id}</div>
              <div><strong>Audit Severity:</strong> ${selectedEvent.severity}</div>
              <div style="grid-column: span 2;"><strong>SHA-256 Hash:</strong> ${selectedEvent.current_hash}</div>
              <div style="grid-column: span 2;"><strong>Audit Timestamp:</strong> ${new Date().toUTCString()}</div>
            </div>
            <pre>${incidentReport}</pre>
            <div class="footer">
              Official Cryptographic Public Health Intelligence Report · Government of Odisha & West Bengal CDMO Directorate
            </div>
            <script>
              window.onload = function() { window.print(); }
            </script>
          </body>
        </html>
      `);
      printWin.document.close();
    }
  };

  const executeQuery = async (queryText: string) => {
    if (!queryText.trim()) return;
    try {
      setQuerying(true);
      setQueryResponse(null);
      const res = await fetch(`${BACKEND_URL}/api/v1/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: queryText }),
      });
      if (res.ok) {
        const data = await res.json();
        setQueryResponse(data.answer);
      }
    } catch (err) {
      setQueryResponse("Unable to query telemetry stream.");
    } finally {
      setQuerying(false);
    }
  };

  const handleNLQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    await executeQuery(queryInput);
  };

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  const userScopedEvents = (scopeFilter === "MY_FACILITY" && currentUser.facilityId !== "ALL_NODES")
    ? events.filter(e => e.facility_name.toLowerCase().includes(currentUser.facilityName.toLowerCase().split(" ")[0]))
    : events;

  const filteredEvents = activeTab === "FLAGGED" 
    ? userScopedEvents.filter(e => e.is_flagged) 
    : userScopedEvents;

  const flaggedCount = events.filter((e) => e.is_flagged).length;
  const verifiedCount = events.length - flaggedCount;
  const pendingReqCount = requisitions.filter(r => r.status === "PENDING_APPROVAL").length;

  return (
    <div className="min-h-screen bg-[#F4F4F4] text-slate-900 flex flex-col font-sans antialiased selection:bg-[#1D546C] selection:text-white">
      <Analytics />
      
      {/* Sticky Header */}
      <header className="bg-white/95 backdrop-blur-md border-b border-slate-200 px-6 py-3 shadow-xs flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5 cursor-pointer select-none">
            <div className="h-10 w-10 bg-[#0C2B4E] rounded-lg flex items-center justify-center p-2 shadow-2xs">
              <svg viewBox="0 0 100 100" fill="none" className="w-full h-full">
                <path d="M50 10L90 85H65L50 55L35 85H10L50 10Z" fill="white" />
                <path d="M50 55L65 85H35L50 55Z" fill="#1D546C" />
                <path d="M22 85L35 60L48 85H22Z" fill="#94A3B8" />
              </svg>
            </div>
            
            <div className="flex flex-col justify-center">
              <span className="text-2xl font-black tracking-tight text-[#0C2B4E] leading-none">
                Healysis
              </span>
              <span className="text-[9px] font-bold tracking-widest text-[#1D546C] uppercase mt-0.5 font-mono">
                TELEMETRY NETWORK
              </span>
            </div>
          </div>
          
          <div className="hidden sm:flex items-center gap-2 border-l border-slate-200 pl-4 h-8">
            <span className="relative flex h-2.5 w-2.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${backendOffline ? "bg-rose-400" : "bg-emerald-400"} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${backendOffline ? "bg-rose-500" : "bg-emerald-500"}`}></span>
            </span>
            <span className="text-[11px] bg-[#0C2B4E] text-white px-2.5 py-1 rounded-md font-mono font-bold tracking-wider shadow-2xs">
              {backendOffline ? "BACKEND OFFLINE" : "LIVE SENTRY NETWORK"}
            </span>
          </div>
        </div>

        {/* RBAC Session Switcher */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-100 rounded-lg border border-slate-200 px-2.5 py-1 text-xs gap-2">
            <IconUserCheck size={16} className="text-[#1D546C]" />
            <div className="flex flex-col text-left">
              <span className="text-[9px] font-bold uppercase text-slate-500 tracking-wider">Logged In Session (RBAC)</span>
              <select
                value={currentUser.userId}
                onChange={(e) => handleUserSwitch(e.target.value)}
                className="bg-transparent font-bold text-[#0C2B4E] text-xs outline-none cursor-pointer"
              >
                {RBAC_USERS.map((u) => (
                  <option key={u.userId} value={u.userId}>
                    {u.name} ({u.shortLabel})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={handleLedgerVerification}
            disabled={verifying}
            className="hidden md:flex items-center gap-1.5 text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-300 px-3 py-1.5 rounded-lg font-bold transition-all shadow-2xs active:scale-95 cursor-pointer"
          >
            <IconShieldCheck size={16} className={verifying ? "animate-spin" : "text-emerald-600"} />
            {verifying ? "Auditing Hashes..." : "Verify Hash Chain"}
          </button>

          <div className="flex items-center bg-slate-100 rounded-lg border border-slate-200 p-0.5 text-xs font-semibold">
            <IconLanguage size={15} className="text-slate-500 mx-2" />
            <button 
              onClick={() => setLang("EN")} 
              className={`px-3 py-1 rounded-md transition-all duration-150 cursor-pointer ${lang === "EN" ? "bg-[#0C2B4E] text-white shadow-xs" : "text-slate-600 hover:text-black"}`}
            >
              English
            </button>
            <button 
              onClick={() => setLang("HI")} 
              className={`px-3 py-1 rounded-md transition-all duration-150 cursor-pointer ${lang === "HI" ? "bg-[#0C2B4E] text-white shadow-xs" : "text-slate-600 hover:text-black"}`}
            >
              हिंदी
            </button>
          </div>

          <button
            onClick={() => { fetchEvents(); fetchRequisitions(); }}
            className="flex items-center gap-2 text-xs bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-4 py-2 rounded-lg transition-all font-bold shadow-xs hover:shadow-md cursor-pointer"
          >
            <IconRefresh size={15} className={loading ? "animate-spin" : ""} />
            {lang === "EN" ? "Refresh Ledger" : "रिफ्रेश करें"}
          </button>
        </div>
      </header>

      {verifyStatus && (
        <div className="bg-emerald-900 text-white px-6 py-2 text-xs font-mono font-medium flex items-center justify-between animate-in fade-in">
          <span>{verifyStatus}</span>
          <button onClick={() => setVerifyStatus(null)} className="font-bold hover:text-emerald-300 cursor-pointer">✕</button>
        </div>
      )}

      {backendOffline && (
        <div className="bg-rose-50 border-b border-rose-200 px-6 py-2.5 text-xs text-rose-800 flex items-center justify-between animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-2">
            <IconAlertCircle size={16} className="text-rose-600 shrink-0" />
            <span><strong>Backend Server Offline:</strong> Render server is waking up or starting.</span>
          </div>
          <button onClick={() => { fetchEvents(); fetchRequisitions(); }} className="underline font-bold hover:text-rose-950 cursor-pointer">Retry Connection</button>
        </div>
      )}

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-white via-slate-50/50 to-[#F4F4F4] border-b border-slate-200 py-10 px-6">
        <div className="max-w-5xl mx-auto text-center space-y-3">
          <div className="inline-flex items-center gap-2 bg-white text-[#0C2B4E] border border-slate-200 px-3.5 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-wider shadow-xs hover:border-[#1D546C] transition-colors">
            <IconLock size={13} className="text-emerald-600" />
            Role-Scoped Telemetry · {currentUser.role} ({currentUser.shortLabel}) Active
          </div>

          <h1 className="text-3xl md:text-5xl font-black text-[#0C2B4E] tracking-tight leading-tight">
            {lang === "EN" 
              ? "Securing Every Vial & Bed Across Primary Health Centres" 
              : "प्राथमिक स्वास्थ्य केंद्रों में दवाओं एवं बिस्तरों की सुरक्षित निगरानी"}
          </h1>

          <p className="text-sm md:text-base text-slate-600 max-w-3xl mx-auto leading-relaxed font-normal">
            {lang === "EN"
              ? "Cryptographic telemetry network connecting CHCs & PHCs across Odisha & West Bengal. Authenticated node operators ingest verified logs, while CDMO directors coordinate inter-district buffer rebalancing."
              : "ओडिशा और पश्चिम बंगाल के स्वास्थ्य केंद्रों को जोड़ने वाला सुरक्षित नेटवर्क। दवाइयों की हेराफेरी रोकने और आपातकालीन पुनर्वितरण के लिए SHA-256 ब्लॉकचेन एवं Google Gemini AI द्वारा संचालित।"}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button 
              onClick={() => scrollToSection(isCDMO ? "cdmo-authorization-desk" : "reporting-console")}
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-6 py-3 rounded-lg text-xs md:text-sm font-bold shadow-sm hover:shadow-md transition-all flex items-center gap-2 group cursor-pointer"
            >
              <IconReportMedical size={18} />
              {isCDMO ? "Open CDMO Authorization Desk" : (lang === "EN" ? `Open ${currentUser.shortLabel} Entry Console` : `${currentUser.shortLabel} एंट्री फॉर्म खोलें`)}
              <IconChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
            </button>
            <button 
              onClick={() => scrollToSection("telemetry-ledger")}
              className="bg-white hover:bg-slate-50 active:scale-95 border border-slate-300 text-slate-800 px-6 py-3 rounded-lg text-xs md:text-sm font-bold shadow-2xs hover:shadow-xs transition-all flex items-center gap-2 cursor-pointer"
            >
              <IconActivity size={18} className="text-[#1D546C]" />
              {lang === "EN" ? "Inspect Audit Ledger" : "लेजर रिकॉर्ड देखें"}
              <IconArrowDown size={14} />
            </button>
          </div>
        </div>
      </section>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-8">
        
        {/* Metric Overview Tiles */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="group relative bg-white p-5 rounded-xl border border-slate-200 shadow-2xs hover:shadow-md hover:border-[#1D546C] transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                {lang === "EN" ? "Total Logged Nodes" : "कुल दर्ज इवेंट"}
                <IconInfoCircle size={13} className="text-slate-400 group-hover:text-[#1D546C] transition-colors" />
              </span>
              <div className="p-2.5 bg-slate-50 group-hover:bg-slate-100 border border-slate-200 rounded-lg text-[#1A3D64] transition-colors">
                <IconDatabase size={20} />
              </div>
            </div>
            <h3 className="text-3xl font-black text-[#0C2B4E] mt-2 group-hover:text-[#1D546C] transition-colors">{events.length}</h3>
            <span className="text-xs text-slate-400 font-mono mt-1 block">Chained: OD & WB Nodes</span>
          </div>

          <div className="group relative bg-white p-5 rounded-xl border border-slate-200 shadow-2xs hover:shadow-md hover:border-emerald-500 transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                {lang === "EN" ? "Verified Transactions" : "सत्यापित ट्रांजैक्शन"}
                <IconInfoCircle size={13} className="text-slate-400 group-hover:text-emerald-600 transition-colors" />
              </span>
              <div className="p-2.5 bg-emerald-50 group-hover:bg-emerald-100 border border-emerald-200 rounded-lg text-emerald-600 transition-colors">
                <IconCircleCheck size={20} />
              </div>
            </div>
            <h3 className="text-3xl font-black text-emerald-700 mt-2">{verifiedCount}</h3>
            <span className="text-xs text-emerald-600 font-semibold mt-1 block">100% SHA-256 Passed</span>
          </div>

          <div className="group relative bg-white p-5 rounded-xl border border-slate-200 shadow-2xs hover:shadow-md hover:border-amber-500 transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                Pending Authorizations
                <IconClockHour4 size={13} className="text-slate-400 group-hover:text-amber-600 transition-colors" />
              </span>
              <div className="p-2.5 bg-amber-50 group-hover:bg-amber-100 border border-amber-200 rounded-lg text-amber-600 transition-colors">
                <IconTruckDelivery size={20} />
              </div>
            </div>
            <h3 className="text-3xl font-black text-amber-600 mt-2">{pendingReqCount}</h3>
            <span className="text-xs text-amber-600 font-semibold mt-1 block">Awaiting CDMO Review</span>
          </div>

          <div className="group relative bg-white p-5 rounded-xl border border-slate-200 shadow-2xs hover:shadow-md hover:border-rose-500 transition-all duration-200 hover:-translate-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                {lang === "EN" ? "Critical Anomaly Queue" : "पहचाने गए खतरे"}
                <IconInfoCircle size={13} className="text-slate-400 group-hover:text-rose-600 transition-colors" />
              </span>
              <div className="p-2.5 bg-rose-50 group-hover:bg-rose-100 border border-rose-200 rounded-lg text-rose-600 transition-colors">
                <IconAlertOctagon size={20} />
              </div>
            </div>
            <h3 className="text-3xl font-black text-rose-600 mt-2">{flaggedCount}</h3>
            <span className="text-xs text-rose-500 font-semibold mt-1 block">Triage Required</span>
          </div>
        </div>

        {/* SECTION 1: TWO-TIER CDMO REQUISITION & AUTHORIZATION DESK */}
        {isCDMO ? (
          <div id="cdmo-authorization-desk" className="bg-white p-6 rounded-xl border-2 border-amber-500/40 shadow-xs hover:border-amber-500 transition-colors">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 pb-3 mb-4 gap-2">
              <div className="flex items-center gap-2">
                <IconTruckDelivery size={22} className="text-amber-600" />
                <div>
                  <h3 className="text-base font-bold text-[#0C2B4E]">
                    Central CDMO Stock Requisition & Authorization Desk
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    Jurisdiction: Multi-State Emergency Rebalancing Network (Odisha & West Bengal)
                  </p>
                </div>
              </div>
              <span className="text-xs font-bold px-3 py-1 bg-amber-100 text-amber-900 border border-amber-300 rounded-full self-start sm:self-auto">
                {pendingReqCount} Pending Approvals
              </span>
            </div>

            {requisitions.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">No incoming stock requisitions in queue.</p>
            ) : (
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-[#0C2B4E] text-white text-[11px] font-bold uppercase tracking-wider">
                    <tr>
                      <th className="p-3">Req ID</th>
                      <th className="p-3">Requesting Target</th>
                      <th className="p-3">Source Dispatch</th>
                      <th className="p-3">Item & Quantity</th>
                      <th className="p-3">Reason</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Director Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {requisitions.map((req) => (
                      <tr key={req.req_id} className="hover:bg-slate-50 transition">
                        <td className="p-3 font-mono font-bold text-[#1D546C]">{req.req_id}</td>
                        <td className="p-3 font-bold text-slate-800">{req.target_facility}</td>
                        <td className="p-3 text-slate-600">{req.source_facility}</td>
                        <td className="p-3 font-bold text-[#0C2B4E]">{req.quantity} units of {req.item_id}</td>
                        <td className="p-3 text-slate-500 italic">{req.urgency_reason}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            req.status === "PENDING_APPROVAL" ? "bg-amber-100 text-amber-800 border border-amber-300" :
                            req.status === "APPROVED_AND_DISPATCHED" ? "bg-emerald-100 text-emerald-800 border border-emerald-300" :
                            "bg-rose-100 text-rose-800 border border-rose-300"
                          }`}>
                            {req.status}
                          </span>
                        </td>
                        <td className="p-3 text-right space-x-2">
                          {req.status === "PENDING_APPROVAL" ? (
                            <>
                              <button
                                onClick={() => handleAuthorizeAction(req.req_id, "APPROVE")}
                                disabled={reqActionLoading === req.req_id}
                                className="bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md font-bold text-xs shadow-2xs transition cursor-pointer"
                              >
                                {reqActionLoading === req.req_id ? "Dispatching..." : "Authorize & Dispatch"}
                              </button>
                              <button
                                onClick={() => handleAuthorizeAction(req.req_id, "REJECT")}
                                disabled={reqActionLoading === req.req_id}
                                className="bg-rose-600 hover:bg-rose-700 text-white px-2.5 py-1.5 rounded-md font-bold text-xs shadow-2xs transition cursor-pointer"
                              >
                                Reject
                              </button>
                            </>
                          ) : (
                            <span className="text-slate-400 font-mono text-[11px]">Reviewed: {req.reviewed_by}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs hover:border-[#1D546C] transition-colors">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
              <div className="flex items-center gap-2">
                <IconTruckDelivery size={20} className="text-[#1D546C]" />
                <h3 className="text-sm font-bold text-[#0C2B4E]">
                  Request Emergency Stock Replenishment from Network
                </h3>
              </div>
              <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono font-bold">
                Requester Node: {currentUser.shortLabel}
              </span>
            </div>

            <form onSubmit={handleCreateRequisition} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Source Health Facility</label>
                <select
                  value={reqSource}
                  onChange={(e) => setReqSource(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 font-medium bg-white outline-none focus:border-[#1D546C]"
                >
                  {FACILITIES.filter(f => f.name !== currentUser.facilityName).map(f => (
                    <option key={f.id} value={f.name}>{f.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Medicine Item</label>
                <select
                  value={reqItem}
                  onChange={(e) => setReqItem(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 font-mono font-medium bg-white outline-none focus:border-[#1D546C]"
                >
                  {AVAILABLE_MEDICINES.map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Quantity (Units)</label>
                <input
                  type="number"
                  min="10"
                  max="500"
                  value={reqQuantity}
                  onChange={(e) => setReqQuantity(Number(e.target.value))}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 font-mono font-bold outline-none focus:border-[#1D546C]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Reason / Urgency</label>
                <input
                  type="text"
                  value={reqReason}
                  onChange={(e) => setReqReason(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg p-2 font-medium outline-none focus:border-[#1D546C]"
                />
              </div>

              <div className="flex items-end">
                <button
                  type="submit"
                  disabled={reqSubmitting}
                  className="w-full bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white font-bold py-2 rounded-lg text-xs transition shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <IconSend size={14} />
                  {reqSubmitting ? "Submitting..." : "Submit to CDMO"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Natural Language Advisor Terminal */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs hover:border-slate-300 transition-colors">
          <form onSubmit={handleNLQuery} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <IconSearch size={18} className="text-slate-400 absolute left-3.5 top-3.5" />
              <input
                type="text"
                placeholder={lang === "EN" ? "Ask Healysis Telemetry Advisor: e.g. 'How many stock of ORS in Jatni CHC?'" : "सलाहकार से पूछें: उदाहरण: 'जटनी में ओआरएस का कितना स्टॉक है?'"}
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                className="w-full text-xs md:text-sm pl-10 pr-4 py-3 bg-slate-50 border border-slate-300 rounded-lg focus:bg-white focus:border-[#1D546C] focus:ring-1 focus:ring-[#1D546C] outline-none font-medium transition"
              />
            </div>
            <button
              type="submit"
              disabled={querying}
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-5 py-3 rounded-lg text-xs md:text-sm font-bold tracking-wide flex items-center justify-center gap-2 transition shadow-xs hover:shadow-md shrink-0 cursor-pointer"
            >
              <IconSparkles size={16} className={`text-cyan-300 ${querying ? "animate-spin" : ""}`} />
              {querying ? "Analyzing..." : (lang === "EN" ? "Query AI Advisor" : "पूछें")}
            </button>
          </form>

          {/* 4 Active Pre-Set Query Pills */}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              {lang === "EN" ? "Suggested Queries:" : "त्वरित सुझाव:"}
            </span>
            
            <button
              type="button"
              onClick={() => {
                const q = "Which facilities in Odisha risk ORS or Insulin stockouts?";
                setQueryInput(q);
                executeQuery(q);
              }}
              className="text-xs bg-slate-100 hover:bg-[#0C2B4E] hover:text-white text-slate-700 font-medium px-3 py-1.5 rounded-full border border-slate-200 transition-all cursor-pointer shadow-2xs active:scale-95"
            >
              ⚡ Stockout Risks in Odisha
            </button>

            <button
              type="button"
              onClick={() => {
                const q = "Audit unverified ghost drawdowns and suspicious anomalies in Jatni CHC";
                setQueryInput(q);
                executeQuery(q);
              }}
              className="text-xs bg-slate-100 hover:bg-[#0C2B4E] hover:text-white text-slate-700 font-medium px-3 py-1.5 rounded-full border border-slate-200 transition-all cursor-pointer shadow-2xs active:scale-95"
            >
              🔍 Audit Jatni Ghost Drawdowns
            </button>

            <button
              type="button"
              onClick={() => {
                const q = "Total Paracetamol and ORS consumption breakdown across Cuttack and Puri";
                setQueryInput(q);
                executeQuery(q);
              }}
              className="text-xs bg-slate-100 hover:bg-[#0C2B4E] hover:text-white text-slate-700 font-medium px-3 py-1.5 rounded-full border border-slate-200 transition-all cursor-pointer shadow-2xs active:scale-95"
            >
              📊 Consumption in Cuttack & Puri
            </button>

            <button
              type="button"
              onClick={() => {
                const q = "Flagged spoilage anomalies and temperature breach events in Bengal PHCs";
                setQueryInput(q);
                executeQuery(q);
              }}
              className="text-xs bg-slate-100 hover:bg-[#0C2B4E] hover:text-white text-slate-700 font-medium px-3 py-1.5 rounded-full border border-slate-200 transition-all cursor-pointer shadow-2xs active:scale-95"
            >
              🚨 Spoilage & Cold-Chain Alerts
            </button>
          </div>

          {/* AI Advisor Response */}
          {queryResponse && (
            <div className="mt-4 p-4 bg-slate-50 border-l-4 border-[#1D546C] border-y border-r border-slate-200 rounded-lg text-xs md:text-sm text-slate-800 leading-relaxed animate-in fade-in slide-in-from-top-2 duration-200">
              <p className="font-bold text-[#0C2B4E] mb-1.5 flex items-center gap-2">
                <IconShieldCheck size={18} className="text-[#1D546C]" /> Gemini 2.5 Flash Advisory Assessment:
              </p>
              <div className="whitespace-pre-wrap font-sans">{queryResponse}</div>
            </div>
          )}
        </div>

        {/* Form and Table Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Panel: Frontline Form */}
          <div id="reporting-console" className="lg:col-span-5 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs hover:border-slate-300 transition-colors flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <IconReportMedical size={20} className="text-[#1D546C]" />
                  <h2 className="text-base font-bold text-[#0C2B4E]">
                    {lang === "EN" ? "Frontline Stock Reporting Form" : "दवा एवं संसाधन एंट्री फॉर्म"}
                  </h2>
                </div>
                <span className="text-[10px] bg-slate-100 text-slate-600 px-2.5 py-1 rounded font-mono font-medium border border-slate-200">
                  {currentUser.shortLabel}
                </span>
              </div>

              <form onSubmit={(e) => handleIngest(e)} className="space-y-4 text-xs md:text-sm">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    {lang === "EN" ? "Reporting Health Centre (Facility)" : "स्वास्थ्य केंद्र चुनें"}
                  </label>
                  <select
                    value={formData.facility_id}
                    onChange={(e) => handleFacilityChange(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1D546C] focus:ring-1 focus:ring-[#1D546C] outline-none font-medium bg-white text-xs md:text-sm transition"
                  >
                    {FACILITIES.map((fac) => (
                      <option key={fac.id} value={fac.id}>
                        [{fac.state}] {fac.name} ({fac.type})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">
                      {lang === "EN" ? "Action Type" : "गतिविधि प्रकार"}
                    </label>
                    <select
                      value={formData.action_type}
                      onChange={(e) => setFormData({ ...formData, action_type: e.target.value })}
                      className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1D546C] focus:ring-1 focus:ring-[#1D546C] outline-none font-medium bg-white text-xs md:text-sm transition"
                    >
                      <option value="DISPENSE">DISPENSE (निकासी/वितरण)</option>
                      <option value="RECEIVE">RECEIVE (आवक/प्राप्त)</option>
                      <option value="SPOILAGE">SPOILAGE (खराब/नुकसान)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">
                      {lang === "EN" ? "Quantity (Units)" : "मात्रा (Units)"}
                    </label>
                    <input
                      type="number"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 0 })}
                      className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1D546C] outline-none font-mono font-bold text-xs md:text-sm transition"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">
                      {lang === "EN" ? "Patient Footfall" : "मरीजों की संख्या (OPD)"}
                    </label>
                    <input
                      type="number"
                      value={formData.patient_footfall}
                      onChange={(e) => setFormData({ ...formData, patient_footfall: parseInt(e.target.value) || 0 })}
                      className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1D546C] outline-none font-mono text-xs md:text-sm transition"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">
                      {lang === "EN" ? "Beds Occupied" : "भर्ती बेड"}
                    </label>
                    <input
                      type="number"
                      value={formData.bed_occupancy}
                      onChange={(e) => setFormData({ ...formData, bed_occupancy: parseInt(e.target.value) || 0 })}
                      className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1D546C] outline-none font-mono text-xs md:text-sm transition"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    {lang === "EN" ? "Essential Medicine / Supply Item" : "दवा या आवश्यक संसाधन"}
                  </label>
                  <select
                    value={formData.item_id}
                    onChange={(e) => setFormData({ ...formData, item_id: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1D546C] outline-none font-mono font-medium text-xs md:text-sm transition bg-white"
                  >
                    {AVAILABLE_MEDICINES.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    {lang === "EN" ? "Anonymous Patient Token" : "मरीज पर्ची टोकन"}
                    <span className="text-slate-400 font-normal text-xs block">
                      {lang === "EN" ? "(Leave blank to trigger anomaly alert)" : "(खाली छोड़ने पर फ्रॉड अलर्ट ट्रिगर होगा)"}
                    </span>
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. PAT-IN-8921"
                    value={formData.patient_token}
                    onChange={(e) => setFormData({ ...formData, patient_token: e.target.value })}
                    className="w-full border border-slate-300 rounded-lg p-2.5 focus:border-[#1D546C] outline-none font-mono text-xs md:text-sm transition"
                  />
                </div>

                <div className="pt-2 flex flex-col gap-2.5">
                  <button
                    type="submit"
                    disabled={submitting || backendOffline}
                    className="w-full bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-[0.99] disabled:opacity-60 text-white py-3 rounded-lg font-bold text-xs md:text-sm transition-all shadow-xs hover:shadow-md flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {submitting ? (
                      <>
                        <IconRefresh size={16} className="animate-spin" />
                        Hashing & Submitting...
                      </>
                    ) : (
                      <>
                        <IconSend size={16} />
                        {lang === "EN" ? "Submit to Cryptographic Ledger" : "लेजर में सुरक्षित दर्ज करें"}
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    disabled={simulating || backendOffline}
                    onClick={handleSimulateGhostDrawdown}
                    className="w-full bg-rose-50 text-rose-800 hover:bg-rose-100 active:scale-[0.99] border border-rose-200 py-2 rounded-lg font-bold text-xs transition cursor-pointer flex items-center justify-center gap-2 disabled:opacity-60"
                  >
                    {simulating ? (
                      <>
                        <IconRefresh size={14} className="animate-spin text-rose-600" />
                        Injecting Simulated Anomaly...
                      </>
                    ) : (
                      <>
                        ⚡ Simulate Ghost Drawdown for {currentUser.shortLabel}
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>

          {/* Right Panel: Telemetry Ledger Table */}
          <div id="telemetry-ledger" className="lg:col-span-7 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs hover:border-slate-300 transition-colors flex flex-col justify-between">
            <div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-3 mb-4 gap-2">
                <div className="flex items-center gap-2">
                  <IconActivity size={20} className="text-[#1D546C]" />
                  <div>
                    <h2 className="text-base font-bold text-[#0C2B4E]">
                      {lang === "EN" ? "Cryptographic Telemetry Ledger" : "टेलीमेट्री लेजर"}
                    </h2>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  {currentUser.facilityId !== "ALL_NODES" && (
                    <button
                      onClick={() => setScopeFilter(scopeFilter === "ALL_FACILITIES" ? "MY_FACILITY" : "ALL_FACILITIES")}
                      className="text-[11px] font-bold px-2.5 py-1 rounded bg-slate-100 border border-slate-300 text-slate-700 hover:bg-slate-200 cursor-pointer"
                    >
                      {scopeFilter === "ALL_FACILITIES" ? "Scope: Show All" : `Scope: ${currentUser.shortLabel}`}
                    </button>
                  )}

                  <div className="flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs font-semibold self-start sm:self-auto">
                    <button
                      onClick={() => setActiveTab("ALL")}
                      className={`px-3 py-1 rounded-md transition-all cursor-pointer ${activeTab === "ALL" ? "bg-white shadow-xs text-[#0C2B4E]" : "text-slate-500 hover:text-slate-800"}`}
                    >
                      All Events ({filteredEvents.length})
                    </button>
                    <button
                      onClick={() => setActiveTab("FLAGGED")}
                      className={`px-3 py-1 rounded-md transition-all cursor-pointer ${activeTab === "FLAGGED" ? "bg-rose-600 text-white" : "text-slate-500 hover:text-rose-600"}`}
                    >
                      Anomalies ({flaggedCount})
                    </button>
                  </div>
                </div>
              </div>

              {/* Data Table */}
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-[#0C2B4E] text-white text-[11px] font-bold uppercase tracking-wider sticky top-0 z-20">
                    <tr>
                      <th className="p-3">Event ID & Hash</th>
                      <th className="p-3">Facility Node</th>
                      <th className="p-3">Action & Item</th>
                      <th className="p-3 text-center">Qty</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 text-right">Audit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredEvents.map((evt) => {
                      const isNew = evt.event_id === lastSubmittedId;
                      return (
                        <tr 
                          key={evt.event_id} 
                          className={`transition-colors duration-200 ${
                            isNew 
                              ? "bg-cyan-50/80 animate-pulse" 
                              : evt.is_flagged 
                              ? "bg-rose-50/50 hover:bg-rose-50" 
                              : "hover:bg-slate-50/80"
                          }`}
                        >
                          <td className="p-3 font-mono">
                            <span className="font-bold text-[#1A3D64] block">{evt.event_id}</span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {evt.current_hash ? evt.current_hash.substring(0, 10) + "..." : ""}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className="font-bold text-slate-800 block">{evt.facility_name}</span>
                            <span className="text-[11px] text-slate-500">
                              Footfall: {evt.patient_footfall} | Beds: {evt.bed_occupancy}
                            </span>
                          </td>
                          <td className="p-3">
                            <span className="font-bold text-slate-700">{evt.action_type}</span>
                            <span className="block text-[10px] text-slate-500 font-mono">{evt.item_id}</span>
                          </td>
                          <td className="p-3 text-center font-mono font-bold text-slate-900 text-sm">
                            {evt.quantity}
                          </td>
                          <td className="p-3">
                            {evt.is_flagged ? (
                              <span className="inline-flex items-center gap-1 bg-rose-100 text-rose-800 px-2.5 py-1 rounded text-[10px] font-bold tracking-tight border border-rose-200">
                                <IconAlertOctagon size={13} stroke={2} /> {evt.severity}
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 px-2.5 py-1 rounded text-[10px] font-bold tracking-tight border border-emerald-200">
                                <IconCircleCheck size={13} stroke={2} /> VERIFIED
                              </span>
                            )}
                          </td>
                          <td className="p-3 text-right">
                            {evt.is_flagged ? (
                              <button
                                onClick={() => handleExplain(evt)}
                                className="inline-flex items-center gap-1 bg-[#1D546C] hover:bg-[#1A3D64] active:scale-95 text-white px-3 py-1.5 rounded-md text-[11px] font-bold tracking-wide transition shadow-xs hover:shadow-sm cursor-pointer"
                              >
                                <IconSparkles size={13} className="text-cyan-200" /> Triage AI
                              </button>
                            ) : (
                              <span className="text-slate-400 text-xs font-mono">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* GEMINI FORENSIC AUDIT BRIEF MODAL */}
        {selectedEvent && (
          <div className="bg-white p-6 rounded-xl border-2 border-[#1D546C] shadow-lg animate-in fade-in slide-in-from-bottom-3 duration-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-200 pb-3 mb-4 gap-2">
              <div className="flex items-center gap-2">
                <IconFileText size={22} className="text-[#1D546C]" />
                <div>
                  <h3 className="text-base font-bold text-[#0C2B4E]">
                    Forensic Incident Case Brief — <span className="font-mono text-[#1D546C]">{selectedEvent.event_id}</span>
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    Facility: {selectedEvent.facility_name} | Triggered Violations: {selectedEvent.violations}
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {incidentReport && (
                  <button
                    onClick={handleDownloadPDF}
                    className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-3 py-1.5 rounded-md text-xs font-bold transition shadow-xs flex items-center gap-1.5 cursor-pointer"
                  >
                    <IconPrinter size={14} />
                    Download as PDF
                  </button>
                )}
                
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="text-xs text-slate-500 hover:text-slate-900 font-bold px-3 py-1.5 rounded-md border border-slate-200 hover:bg-slate-100 transition cursor-pointer"
                >
                  ✕ Close
                </button>
              </div>
            </div>

            {generatingReport ? (
              <div className="py-12 flex flex-col items-center justify-center space-y-3">
                <IconSparkles size={28} className="text-[#1D546C] animate-spin" />
                <p className="text-xs md:text-sm font-semibold text-slate-600">
                  Google Gemini 2.5 Flash is analyzing logs, baselines & forensic vectors...
                </p>
                <div className="w-full max-w-xl space-y-2.5 pt-2 animate-pulse">
                  <div className="h-3 bg-slate-200 rounded w-3/4"></div>
                  <div className="h-3 bg-slate-200 rounded w-full"></div>
                  <div className="h-3 bg-slate-200 rounded w-5/6"></div>
                </div>
              </div>
            ) : (
              <div className="bg-slate-50 p-6 rounded-lg border border-slate-200 text-xs md:text-sm text-slate-800 whitespace-pre-wrap leading-relaxed shadow-inner font-sans">
                {incidentReport}
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
}