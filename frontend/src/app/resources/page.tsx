"use client";

import React, { useState, useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import { 
  IconPackage, 
  IconSearch, 
  IconPlus, 
  IconRefresh, 
  IconTrash, 
  IconEdit,
  IconX,
  IconAlertCircle,
  IconFilter,
  IconBuildingHospital
} from "@tabler/icons-react";

const DEFAULT_FACILITIES = [
  { id: 1, facility_code: "CHC-OD-KHU-001", name: "Jatni CHC (Khordha)", state: "OD", district: "Khordha" },
  { id: 2, facility_code: "UPHC-OD-CTC-002", name: "UPHC MS Das (Kafla Bazar)", state: "OD", district: "Cuttack" },
  { id: 3, facility_code: "PHC-OD-PURI-004", name: "Pipili PHC (Puri)", state: "OD", district: "Puri" },
  { id: 4, facility_code: "UPHC-WB-KOL-012", name: "Behala Urban PHC (Kolkata)", state: "WB", district: "Kolkata" },
  { id: 5, facility_code: "PHC-WB-S24P-008", name: "Diamond Harbour PHC", state: "WB", district: "South 24 Parganas" }
];

export default function ResourcesPage() {
  const { user } = useAuth();
  const [resources, setResources] = useState<any[]>([]);
  const [facilities, setFacilities] = useState<any[]>(DEFAULT_FACILITIES);
  const [catalog, setCatalog] = useState<any[]>([]);
  
  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedFacilityFilter, setSelectedFacilityFilter] = useState("ALL");
  const [selectedStateFilter, setSelectedStateFilter] = useState("ALL");
  const [selectedDistrictFilter, setSelectedDistrictFilter] = useState("ALL");
  const [selectedRiskFilter, setSelectedRiskFilter] = useState("ALL");

  const [loading, setLoading] = useState(true);
  const [facilitiesLoading, setFacilitiesLoading] = useState(false);
  const [facilitiesError, setFacilitiesError] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  // Add Resource Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [formFacilityId, setFormFacilityId] = useState<number>(user?.facility_id || 1);
  const [selectedSku, setSelectedSku] = useState("");
  const [formItemName, setFormItemName] = useState("");
  const [formUnit, setFormUnit] = useState("sachets");
  const [formQuantity, setFormQuantity] = useState<number>(100);
  const [formSafetyStock, setFormSafetyStock] = useState<number>(40);
  const [formDailyDemand, setFormDailyDemand] = useState<number>(15);
  const [submitting, setSubmitting] = useState(false);

  // Edit Resource Modal State
  const [showEditModal, setShowEditModal] = useState(false);
  const [editResourceId, setEditResourceId] = useState<number | null>(null);
  const [editSku, setEditSku] = useState("");
  const [editItemName, setEditItemName] = useState("");
  const [editFacilityId, setEditFacilityId] = useState<number>(1);
  const [editFacilityName, setEditFacilityName] = useState("");
  const [editQuantity, setEditQuantity] = useState<number>(0);
  const [editSafetyStock, setEditSafetyStock] = useState<number>(0);
  const [editDailyDemand, setEditDailyDemand] = useState<number>(10);
  const [editIncomingQuantity, setEditIncomingQuantity] = useState<number>(0);
  const [editUnit, setEditUnit] = useState("units");

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      setFacilitiesError(null);

      // Fetch resources
      try {
        const resRec = await apiFetch<any[]>("/api/v1/resources");
        setResources(resRec);
      } catch (err: any) {
        console.error("Resources fetch error:", err);
      }

      // Fetch facilities
      try {
        setFacilitiesLoading(true);
        const resFac = await apiFetch<any[]>("/api/v1/facilities");
        if (Array.isArray(resFac) && resFac.length > 0) {
          setFacilities(resFac);
        } else {
          setFacilities(DEFAULT_FACILITIES);
        }
      } catch (err: any) {
        console.error("Facilities fetch error:", err);
        setFacilitiesError(err.message || "Unable to load facilities. Using seeded defaults.");
        setFacilities(DEFAULT_FACILITIES);
      } finally {
        setFacilitiesLoading(false);
      }

      // Fetch catalog
      try {
        const resCat = await apiFetch<any[]>("/api/v1/resources/catalog");
        const catList = Array.isArray(resCat) && resCat.length > 0 ? resCat : [
          { id: 1, sku: "MED-ORS-SACHET", name: "ORS Sachet (Oral Rehydration Salts)", unit_of_measure: "sachets" },
          { id: 2, sku: "MED-PARACET-500MG", name: "Paracetamol 500mg", unit_of_measure: "tablets" },
          { id: 3, sku: "MED-INSULIN-100IU", name: "Insulin 100IU Injection", unit_of_measure: "vials" },
          { id: 4, sku: "MED-AMOXICILLIN-250", name: "Amoxicillin 250mg Capsule", unit_of_measure: "capsules" },
          { id: 5, sku: "MED-CETIRIZINE-10", name: "Cetirizine 10mg", unit_of_measure: "tablets" }
        ];
        setCatalog(catList);
        if (catList.length > 0 && !selectedSku) {
          setSelectedSku(catList[0].sku);
          setFormItemName(catList[0].name);
          setFormUnit(catList[0].unit_of_measure);
        }
      } catch (e) {
        const fallbackCat = [
          { id: 1, sku: "MED-ORS-SACHET", name: "ORS Sachet (Oral Rehydration Salts)", unit_of_measure: "sachets" },
          { id: 2, sku: "MED-PARACET-500MG", name: "Paracetamol 500mg", unit_of_measure: "tablets" },
          { id: 3, sku: "MED-INSULIN-100IU", name: "Insulin 100IU Injection", unit_of_measure: "vials" },
          { id: 4, sku: "MED-AMOXICILLIN-250", name: "Amoxicillin 250mg Capsule", unit_of_measure: "capsules" },
          { id: 5, sku: "MED-CETIRIZINE-10", name: "Cetirizine 10mg", unit_of_measure: "tablets" }
        ];
        setCatalog(fallbackCat);
        if (!selectedSku) {
          setSelectedSku(fallbackCat[0].sku);
          setFormItemName(fallbackCat[0].name);
          setFormUnit(fallbackCat[0].unit_of_measure);
        }
      }

    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, [user]);

  useEffect(() => {
    if (user?.facility_id) {
      setFormFacilityId(user.facility_id);
    } else if (facilities.length > 0) {
      setFormFacilityId(facilities[0].id);
    }
  }, [user, facilities]);

  const handleSkuChange = (skuCode: string) => {
    setSelectedSku(skuCode);
    const catItem = catalog.find((c) => c.sku === skuCode);
    if (catItem) {
      setFormItemName(catItem.name);
      setFormUnit(catItem.unit_of_measure);
    }
  };

  const handleResourceNameChange = (name: string) => {
    setFormItemName(name);
    const catItem = catalog.find((c) => c.name === name);
    if (catItem) {
      setSelectedSku(catItem.sku);
      setFormUnit(catItem.unit_of_measure);
    }
  };

  const handleAddResource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSku || !formItemName) {
      setBanner({ type: "error", msg: "SKU and Resource name are required." });
      return;
    }

    try {
      setSubmitting(true);
      setBanner(null);

      const targetFacId = (user && user.role === "FACILITY_OFFICER" && user.facility_id) ? user.facility_id : formFacilityId;

      await apiFetch("/api/v1/resources", {
        method: "POST",
        body: JSON.stringify({
          facility_id: targetFacId,
          item_code: selectedSku.trim().toUpperCase(),
          item_name: formItemName.trim(),
          quantity: formQuantity,
          safety_stock: formSafetyStock,
          daily_demand: formDailyDemand,
          incoming_quantity: 0,
          unit: formUnit,
          batch: "BATCH-2026-N1"
        })
      });

      setBanner({ type: "success", msg: `Successfully added resource SKU: ${selectedSku} to Facility #${targetFacId}` });
      setShowAddModal(false);
      fetchInitialData();
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Failed to create resource." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleOpenEditModal = (resItem: any) => {
    setEditResourceId(resItem.id);
    setEditSku(resItem.item_code);
    setEditItemName(resItem.item_name);
    setEditFacilityId(resItem.facility_id);
    setEditFacilityName(resItem.facility_name || `Facility #${resItem.facility_id}`);
    setEditQuantity(resItem.quantity);
    setEditSafetyStock(resItem.safety_stock);
    setEditDailyDemand(resItem.daily_demand || 15);
    setEditIncomingQuantity(resItem.incoming_quantity || 0);
    setEditUnit(resItem.unit || "units");
    setShowEditModal(true);
  };

  const handleUpdateResource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editResourceId) return;

    try {
      setSubmitting(true);
      setBanner(null);

      await apiFetch(`/api/v1/resources/${editResourceId}`, {
        method: "PUT",
        body: JSON.stringify({
          quantity: editQuantity,
          safety_stock: editSafetyStock,
          daily_demand: editDailyDemand,
          incoming_quantity: editIncomingQuantity
        })
      });

      setBanner({ type: "success", msg: `Successfully updated inventory stock for SKU: ${editSku}` });
      setShowEditModal(false);
      fetchInitialData();
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Failed to update resource stock." });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteResource = async (resourceId: number, itemCode: string) => {
    if (user?.role === "FACILITY_OFFICER") {
      setBanner({ type: "error", msg: "Permission denied. Deletion requires CDMO or System Admin role." });
      return;
    }

    try {
      setBanner(null);
      await apiFetch(`/api/v1/resources/${resourceId}`, { method: "DELETE" });
      setBanner({ type: "success", msg: `Deleted resource SKU: ${itemCode}` });
      fetchInitialData();
    } catch (err: any) {
      setBanner({ type: "error", msg: err.message || "Failed to delete resource." });
    }
  };

  // Filter options derived from data
  const stateOptions = Array.from(new Set(resources.map(r => r.state).filter(Boolean)));
  const districtOptions = Array.from(new Set(resources.map(r => r.district).filter(Boolean)));
  const facilityOptions = Array.from(new Set(resources.map(r => r.facility_name).filter(Boolean)));

  const filteredResources = resources.filter((r) => {
    const codeStr = r.item_code || "";
    const nameStr = r.item_name || "";
    const facStr = r.facility_name || "";
    const searchLower = searchQuery.toLowerCase();

    const matchesSearch = !searchQuery || codeStr.toLowerCase().includes(searchLower) || nameStr.toLowerCase().includes(searchLower) || facStr.toLowerCase().includes(searchLower);
    const matchesFacility = selectedFacilityFilter === "ALL" || r.facility_name === selectedFacilityFilter;
    const matchesState = selectedStateFilter === "ALL" || r.state === selectedStateFilter;
    const matchesDistrict = selectedDistrictFilter === "ALL" || r.district === selectedDistrictFilter;

    const risk = r.risk_level || (r.days_of_cover < 3 ? "CRITICAL" : r.days_of_cover < 7 ? "WARNING" : "SAFE");
    const matchesRisk = selectedRiskFilter === "ALL" || risk === selectedRiskFilter;

    return matchesSearch && matchesFacility && matchesState && matchesDistrict && matchesRisk;
  });

  // Group inventory records by Facility Node
  const groupedByFacility = filteredResources.reduce((acc: { [key: string]: { facilityName: string; district?: string; state?: string; items: any[] } }, item) => {
    const facKey = item.facility_name || `Facility #${item.facility_id}`;
    if (!acc[facKey]) {
      acc[facKey] = {
        facilityName: facKey,
        district: item.district,
        state: item.state,
        items: []
      };
    }
    acc[facKey].items.push(item);
    return acc;
  }, {});

  const calculatedAddDoc = formDailyDemand > 0 ? (formQuantity / formDailyDemand).toFixed(1) : "0.0";
  const addDocNum = parseFloat(calculatedAddDoc);
  const calculatedAddRisk = addDocNum < 3.0 ? "CRITICAL" : addDocNum < 7.0 ? "WARNING" : "SAFE";

  const calculatedEditDoc = editDailyDemand > 0 ? (editQuantity / editDailyDemand).toFixed(1) : "0.0";
  const editDocNum = parseFloat(calculatedEditDoc);
  const calculatedEditRisk = editDocNum < 3.0 ? "CRITICAL" : editDocNum < 7.0 ? "WARNING" : "SAFE";

  return (
    <AppShell>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-[#0C2B4E]">Medicine &amp; Resource Inventory</h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Resource Catalog Telemetry, Deterministic DoC Calculation &amp; Stock Tracking
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 shadow-xs cursor-pointer transition"
            >
              <IconPlus size={16} /> Add Resource
            </button>
            <button
              onClick={fetchInitialData}
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

        {/* Operational Filters Toolbar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
          <div className="flex flex-col lg:flex-row gap-3 items-center justify-between">
            <div className="relative w-full lg:w-72">
              <IconSearch size={16} className="absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search resource SKU or name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-lg text-xs font-semibold outline-none focus:border-[#0C2B4E]"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2.5 w-full lg:w-auto">
              <div className="flex items-center gap-1 text-slate-500 text-xs font-mono">
                <IconFilter size={14} /> Filter:
              </div>

              {/* Facility Filter */}
              <select
                value={selectedFacilityFilter}
                onChange={(e) => setSelectedFacilityFilter(e.target.value)}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold bg-white outline-none cursor-pointer"
              >
                <option value="ALL">All Facilities</option>
                {facilityOptions.map(fac => (
                  <option key={fac} value={fac}>{fac}</option>
                ))}
              </select>

              {/* State Filter */}
              <select
                value={selectedStateFilter}
                onChange={(e) => setSelectedStateFilter(e.target.value)}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold bg-white outline-none cursor-pointer"
              >
                <option value="ALL">All States</option>
                {stateOptions.map(st => (
                  <option key={st} value={st}>{st === "OD" ? "Odisha (OD)" : st === "WB" ? "West Bengal (WB)" : st}</option>
                ))}
              </select>

              {/* District Filter */}
              <select
                value={selectedDistrictFilter}
                onChange={(e) => setSelectedDistrictFilter(e.target.value)}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold bg-white outline-none cursor-pointer"
              >
                <option value="ALL">All Districts</option>
                {districtOptions.map(dist => (
                  <option key={dist} value={dist}>{dist}</option>
                ))}
              </select>

              {/* Risk Filter */}
              <select
                value={selectedRiskFilter}
                onChange={(e) => setSelectedRiskFilter(e.target.value)}
                className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold bg-white outline-none cursor-pointer"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical Risk</option>
                <option value="WARNING">Warning</option>
                <option value="SAFE">Safe Buffer</option>
              </select>
            </div>
          </div>
        </div>

        {/* Grouped Inventory Display by Facility */}
        <div className="space-y-6">
          {Object.values(groupedByFacility).map((group) => (
            <div key={group.facilityName} className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden space-y-0">
              
              {/* FACILITY HEADER BLOCK */}
              <div className="bg-slate-50 px-5 py-3.5 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <IconBuildingHospital size={18} className="text-[#0C2B4E]" />
                  <div>
                    <h3 className="text-sm font-black text-[#0C2B4E] font-sans">{group.facilityName}</h3>
                    {group.district && (
                      <span className="text-[10px] text-slate-500 font-mono">
                        {group.district}, {group.state}
                      </span>
                    )}
                  </div>
                </div>
                <span className="text-[10px] font-bold text-slate-500 font-mono bg-white px-2.5 py-1 rounded-lg border border-slate-200">
                  {group.items.length} Resource SKUs
                </span>
              </div>

              {/* FACILITY RESOURCE TABLE */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-100/60 text-slate-500 font-mono uppercase text-[10px] border-b border-slate-200">
                    <tr>
                      <th className="p-3.5">SKU Code</th>
                      <th className="p-3.5">Resource Name</th>
                      <th className="p-3.5">Current Stock</th>
                      <th className="p-3.5">Safety Buffer</th>
                      <th className="p-3.5">Incoming</th>
                      <th className="p-3.5">Days of Cover</th>
                      <th className="p-3.5">Risk Severity</th>
                      <th className="p-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono">
                    {group.items.map((res) => {
                      const doc = res.days_of_cover ?? 99.0;
                      const risk = res.risk_level || (doc < 3 ? "CRITICAL" : doc < 7 ? "WARNING" : "SAFE");

                      return (
                        <tr key={res.id} className="hover:bg-slate-50/50">
                          <td className="p-3.5 font-bold text-[#0C2B4E]">{res.item_code}</td>
                          <td className="p-3.5 font-sans font-semibold text-slate-800">{res.item_name}</td>
                          <td className="p-3.5 font-black text-[#0C2B4E]">
                            {res.quantity} <span className="text-[10px] font-normal text-slate-400">{res.unit}</span>
                          </td>
                          <td className="p-3.5 text-slate-600">
                            {res.safety_stock} <span className="text-[10px] text-slate-400">{res.unit}</span>
                          </td>
                          <td className="p-3.5 text-emerald-700">+{res.incoming_quantity}</td>
                          <td className="p-3.5">
                            <span className="font-bold text-[#0C2B4E]">{doc.toFixed(1)}</span> <span className="text-[10px] text-slate-400">Days</span>
                          </td>
                          <td className="p-3.5">
                            <span className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded font-mono border ${
                              risk === "CRITICAL" ? "bg-rose-100 text-rose-800 border-rose-300" :
                              risk === "WARNING" ? "bg-amber-100 text-amber-800 border-amber-300" :
                              "bg-emerald-100 text-emerald-800 border-emerald-300"
                            }`}>
                              {risk === "CRITICAL" ? "CRITICAL RISK" : risk === "WARNING" ? "WARNING" : "SAFE"}
                            </span>
                          </td>
                          <td className="p-3.5 text-right flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleOpenEditModal(res)}
                              className="text-[#1D546C] hover:text-[#0C2B4E] text-xs font-bold p-1 rounded hover:bg-slate-100 cursor-pointer"
                              title="Edit Resource Telemetry"
                            >
                              <IconEdit size={16} />
                            </button>
                            {user?.role !== "FACILITY_OFFICER" ? (
                              <button
                                onClick={() => handleDeleteResource(res.id, res.item_code)}
                                className="text-rose-600 hover:text-rose-800 text-xs font-bold p-1 rounded hover:bg-rose-50 cursor-pointer"
                                title="Delete SKU"
                              >
                                <IconTrash size={16} />
                              </button>
                            ) : (
                              <span className="text-[10px] text-slate-400 ml-1">Scoped</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

            </div>
          ))}
          {filteredResources.length === 0 && (
            <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs font-sans">
              No inventory resource records match the selected filters.
            </div>
          )}
        </div>

        {/* ADD RESOURCE MODAL WITH CATALOG & TARGET FACILITY SELECTORS */}
        {showAddModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
            <div className="bg-white w-full max-w-lg rounded-2xl p-6 border border-slate-200 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-[#0C2B4E] flex items-center gap-2">
                  <IconPackage size={18} className="text-[#1D546C]" />
                  Add New Resource SKU to Inventory
                </h3>
                <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                  <IconX size={18} />
                </button>
              </div>

              <form onSubmit={handleAddResource} className="space-y-4 text-xs font-semibold">
                
                {/* TARGET FACILITY SELECTOR */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-slate-600">Target Facility</label>
                    {facilitiesError && (
                      <button
                        type="button"
                        onClick={fetchInitialData}
                        className="text-[10px] text-rose-600 hover:underline flex items-center gap-1 cursor-pointer"
                      >
                        <IconAlertCircle size={12} /> Unable to load facilities. Retry
                      </button>
                    )}
                  </div>
                  <select
                    value={formFacilityId}
                    onChange={(e) => setFormFacilityId(Number(e.target.value))}
                    disabled={user?.role === "FACILITY_OFFICER"}
                    className="w-full border border-slate-200 rounded-xl p-2.5 bg-white text-[#0C2B4E] font-bold outline-none cursor-pointer"
                  >
                    {facilities.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} ({f.facility_code || `ID: #${f.id}`})
                      </option>
                    ))}
                  </select>
                </div>

                {/* SKU & RESOURCE NAME CATALOG SELECTORS */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 mb-1">Item SKU (Catalog)</label>
                    <select
                      value={selectedSku}
                      onChange={(e) => handleSkuChange(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono bg-white outline-none cursor-pointer"
                    >
                      {catalog.map((c) => (
                        <option key={c.id} value={c.sku}>
                          {c.sku}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-600 mb-1">Resource Name</label>
                    <select
                      value={formItemName}
                      onChange={(e) => handleResourceNameChange(e.target.value)}
                      className="w-full border border-slate-200 rounded-xl p-2.5 bg-white outline-none cursor-pointer"
                    >
                      {catalog.map((c) => (
                        <option key={c.id} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-600 mb-1">Unit of Measure (Catalog Auto-populated)</label>
                  <input
                    type="text"
                    value={formUnit}
                    readOnly
                    className="w-full border border-slate-200 rounded-xl p-2.5 bg-slate-100 font-mono text-slate-600 outline-none"
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-slate-600 mb-1">Current Stock</label>
                    <input
                      type="number"
                      value={formQuantity}
                      onChange={(e) => setFormQuantity(Number(e.target.value))}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono outline-none"
                      min={0}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 mb-1">Safety Buffer</label>
                    <input
                      type="number"
                      value={formSafetyStock}
                      onChange={(e) => setFormSafetyStock(Number(e.target.value))}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono outline-none"
                      min={0}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-slate-600 mb-1">Daily Demand</label>
                    <input
                      type="number"
                      value={formDailyDemand}
                      onChange={(e) => setFormDailyDemand(Number(e.target.value))}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono outline-none"
                      min={1}
                      required
                    />
                  </div>
                </div>

                {/* READ-ONLY DETERMINISTIC CALCULATIONS */}
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-[11px] space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>Calculated Days of Cover:</span>
                    <strong className="text-[#0C2B4E]">{calculatedAddDoc} Days</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Risk Severity Threshold:</span>
                    <strong className={calculatedAddRisk === "CRITICAL" ? "text-rose-700 font-black" : calculatedAddRisk === "WARNING" ? "text-amber-700 font-black" : "text-emerald-700 font-black"}>
                      {calculatedAddRisk}
                    </strong>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-bold cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="bg-[#0C2B4E] hover:bg-[#1A3D64] text-white px-5 py-2 rounded-xl font-bold transition shadow-xs cursor-pointer"
                  >
                    {submitting ? "Creating..." : "Save Resource SKU"}
                  </button>
                </div>

              </form>
            </div>
          </div>
        )}

        {/* EDIT RESOURCE SKU MODAL */}
        {showEditModal && (
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
            <div className="bg-white w-full max-w-lg rounded-2xl p-6 border border-slate-200 shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-[#0C2B4E] flex items-center gap-2">
                  <IconEdit size={18} className="text-[#1D546C]" />
                  Edit Stock Telemetry — {editSku}
                </h3>
                <button onClick={() => setShowEditModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer">
                  <IconX size={18} />
                </button>
              </div>

              <form onSubmit={handleUpdateResource} className="space-y-4 text-xs font-semibold">
                
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-xs space-y-1">
                  <div className="flex justify-between text-slate-500">
                    <span>Resource Name:</span>
                    <strong className="text-slate-800 font-sans">{editItemName}</strong>
                  </div>
                  <div className="flex justify-between text-slate-500">
                    <span>Facility Node:</span>
                    <strong className="text-slate-800">{editFacilityName}</strong>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 mb-1">Current Stock ({editUnit})</label>
                    <input
                      type="number"
                      value={editQuantity}
                      onChange={(e) => setEditQuantity(Number(e.target.value))}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono outline-none"
                      min={0}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 mb-1">Safety Buffer ({editUnit})</label>
                    <input
                      type="number"
                      value={editSafetyStock}
                      onChange={(e) => setEditSafetyStock(Number(e.target.value))}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono outline-none"
                      min={0}
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-600 mb-1">Daily Consumption Demand</label>
                    <input
                      type="number"
                      value={editDailyDemand}
                      onChange={(e) => setEditDailyDemand(Number(e.target.value))}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono outline-none"
                      min={1}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-slate-600 mb-1">Incoming Stock in Transit</label>
                    <input
                      type="number"
                      value={editIncomingQuantity}
                      onChange={(e) => setEditIncomingQuantity(Number(e.target.value))}
                      className="w-full border border-slate-200 rounded-xl p-2.5 font-mono outline-none"
                      min={0}
                      required
                    />
                  </div>
                </div>

                {/* READ-ONLY DETERMINISTIC RECALCULATION */}
                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-[11px] space-y-1 text-slate-600">
                  <div className="flex justify-between">
                    <span>Recalculated Days of Cover:</span>
                    <strong className="text-[#0C2B4E]">{calculatedEditDoc} Days</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Risk Severity Threshold:</span>
                    <strong className={calculatedEditRisk === "CRITICAL" ? "text-rose-700 font-black" : calculatedEditRisk === "WARNING" ? "text-amber-700 font-black" : "text-emerald-700 font-black"}>
                      {calculatedEditRisk}
                    </strong>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowEditModal(false)}
                    className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-bold cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="bg-[#0C2B4E] hover:bg-[#1A3D64] text-white px-5 py-2 rounded-xl font-bold transition shadow-xs cursor-pointer"
                  >
                    {submitting ? "Updating..." : "Update Stock Telemetry"}
                  </button>
                </div>

              </form>
            </div>
          </div>
        )}

      </div>
    </AppShell>
  );
}
