"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { 
  IconMapPin, 
  IconRoute, 
  IconBuildingHospital, 
  IconArrowRight, 
  IconInfoCircle,
  IconPlus,
  IconMinus,
  IconFocus2,
  IconTruck,
  IconPackage,
  IconClock,
  IconAlertTriangle,
  IconCheck
} from "@tabler/icons-react";

interface GoogleMapsRouteViewerProps {
  donorFacility: string;
  recipientFacility: string;
  donorDistrict?: string;
  recipientDistrict?: string;
  donorCoords: { lat: number; lng: number };
  recipientCoords: { lat: number; lng: number };
  distanceKm: number;
  medicineName: string;
  transferQuantity: number;
  urgencyLevel?: string;
}

export const GoogleMapsRouteViewer: React.FC<GoogleMapsRouteViewerProps> = ({
  donorFacility,
  recipientFacility,
  donorDistrict = "Puri",
  recipientDistrict = "Khordha",
  donorCoords,
  recipientCoords,
  distanceKm,
  medicineName,
  transferQuantity,
  urgencyLevel = "CRITICAL"
}) => {
  // Map viewport & interaction state
  const [zoomLevel, setZoomLevel] = useState<number>(11);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [activeTooltip, setActiveTooltip] = useState<"donor" | "recipient" | null>(null);
  const [tilesLoaded, setTilesLoaded] = useState<boolean>(true);
  const [animProgress, setAnimProgress] = useState<number>(0);

  const containerRef = useRef<HTMLDivElement>(null);

  // Fallback to real Odisha coordinates if defaults are somehow missing
  const dLat = donorCoords?.lat || 20.1170;
  const dLng = donorCoords?.lng || 85.8330;
  const rLat = recipientCoords?.lat || 20.1650;
  const rLng = recipientCoords?.lng || 85.7050;

  const centerLat = (dLat + rLat) / 2;
  const centerLng = (dLng + rLng) / 2;

  // Real highway corridor waypoints between Pipili and Jatni via State Highway 1 / Daya River corridor
  const waypoints = useMemo(() => [
    { lat: dLat, lng: dLng, label: "Pipili PHC Dispatch Gate" },
    { lat: 20.1240, lng: 85.8180, label: "NH-316 / Pipili Bypass" },
    { lat: 20.1380, lng: 85.7820, label: "Daya River Logistics Bridge" },
    { lat: 20.1510, lng: 85.7430, label: "Jatni-Pipili State Highway 1" },
    { lat: rLat, lng: rLng, label: "Jatni CHC Receiving Bay" },
  ], [dLat, dLng, rLat, rLng]);

  // Smooth transit animation loop for supplies (0 to 1 over 4 seconds)
  useEffect(() => {
    let frameId: number;
    let startTime: number | null = null;
    const duration = 4500; // 4.5 seconds per transfer cycle

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = (elapsed % duration) / duration;
      setAnimProgress(progress);
      frameId = requestAnimationFrame(step);
    };

    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, []);

  // Web Mercator / Equirectangular projection to convert (lat, lng) to canvas (x, y)
  const project = useCallback((lat: number, lng: number, width: number, height: number) => {
    // Zoom factor: at zoom 11, approx 5000px per degree of longitude in this viewport
    const scale = 4200 * Math.pow(1.35, zoomLevel - 11);
    const cosLat = Math.cos((centerLat * Math.PI) / 180);

    const x = width / 2 + (lng - centerLng) * scale + panOffset.x;
    const y = height / 2 - (lat - centerLat) * (scale * cosLat) + panOffset.y;

    return { x, y };
  }, [centerLat, centerLng, zoomLevel, panOffset]);

  // Interpolate vehicle position along the route line
  const vehiclePos = useMemo(() => {
    if (waypoints.length < 2) return { lat: dLat, lng: dLng };
    const numSegments = waypoints.length - 1;
    const scaledP = animProgress * numSegments;
    const segIndex = Math.min(Math.floor(scaledP), numSegments - 1);
    const segT = scaledP - segIndex;

    const p0 = waypoints[segIndex];
    const p1 = waypoints[segIndex + 1];

    const curLat = p0.lat + (p1.lat - p0.lat) * segT;
    const curLng = p0.lng + (p1.lng - p0.lng) * segT;

    return { lat: curLat, lng: curLng };
  }, [waypoints, animProgress]);

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPanOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleResetView = () => {
    setZoomLevel(11);
    setPanOffset({ x: 0, y: 0 });
  };

  // Compute OpenStreetMap tile grid around center (lat ~20.141, lng ~85.769)
  const osmTiles = useMemo(() => {
    const z = Math.min(Math.max(zoomLevel, 10), 12);
    const n = Math.pow(2, z);
    const latRad = (centerLat * Math.PI) / 180;
    const centerTileX = ((centerLng + 180) / 360) * n;
    const centerTileY = ((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * n;

    const baseTileX = Math.floor(centerTileX);
    const baseTileY = Math.floor(centerTileY);

    const tiles = [];
    // Render 3x3 grid around center tile
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        const tx = baseTileX + dx;
        const ty = baseTileY + dy;
        tiles.push({
          key: `${z}-${tx}-${ty}`,
          url: `https://tile.openstreetmap.org/${z}/${tx}/${ty}.png`,
          dx,
          dy,
          z,
          tx,
          ty,
          offsetX: (dx - (centerTileX - baseTileX)) * 256,
          offsetY: (dy - (centerTileY - baseTileY)) * 256,
        });
      }
    }
    return tiles;
  }, [centerLat, centerLng, zoomLevel]);

  // Estimated driving transit time based on rural highway corridor
  const estimatedTransitMins = Math.max(18, Math.round((distanceKm / 32) * 60));

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs my-4 select-none">
      {/* Top Header Bar */}
      <div className="bg-slate-900 text-white px-4 py-3 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-emerald-700/80 border border-emerald-500/30 flex items-center justify-center text-white shrink-0">
            <IconTruck size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                Inter-Facility Transfer Logistics Map
              </h4>
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] px-2 py-0.5 rounded-full font-mono font-bold">
                {distanceKm.toFixed(1)} km
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Corridor: <span className="text-emerald-300 font-semibold">{donorFacility}</span> ({donorDistrict}) &rarr; <span className="text-sky-300 font-semibold">{recipientFacility}</span> ({recipientDistrict})
            </p>
          </div>
        </div>

        {/* Map Control Toolbar */}
        <div className="flex items-center gap-1.5 text-xs">
          <button
            onClick={() => setZoomLevel(prev => Math.min(prev + 1, 13))}
            className="h-7 w-7 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg flex items-center justify-center transition border border-slate-700"
            title="Zoom In"
            type="button"
          >
            <IconPlus size={14} />
          </button>
          <button
            onClick={() => setZoomLevel(prev => Math.max(prev - 1, 10))}
            className="h-7 w-7 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg flex items-center justify-center transition border border-slate-700"
            title="Zoom Out"
            type="button"
          >
            <IconMinus size={14} />
          </button>
          <button
            onClick={handleResetView}
            className="px-2.5 h-7 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1 text-[11px] font-medium transition border border-slate-700"
            title="Reset and Center Route"
            type="button"
          >
            <IconFocus2 size={13} />
            <span>Center Route</span>
          </button>
        </div>
      </div>

      {/* Interactive Map Canvas Container */}
      <div 
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`relative w-full h-[320px] overflow-hidden bg-slate-100 ${isDragging ? "cursor-grabbing" : "cursor-grab"}`}
        style={{ touchAction: "none" }}
      >
        {/* Layer 1: OpenStreetMap Raster Tiles Background */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div 
            className="absolute top-1/2 left-1/2"
            style={{ 
              transform: `translate(${panOffset.x}px, ${panOffset.y}px)`,
              transition: isDragging ? "none" : "transform 0.15s ease-out"
            }}
          >
            {osmTiles.map(tile => (
              <img
                key={tile.key}
                src={tile.url}
                alt=""
                onError={() => setTilesLoaded(false)}
                className="absolute w-[256px] h-[256px] max-w-none opacity-90 transition-opacity"
                style={{
                  left: `${tile.offsetX}px`,
                  top: `${tile.offsetY}px`,
                  filter: "contrast(1.02) saturate(0.95)"
                }}
                draggable={false}
              />
            ))}
          </div>
        </div>

        {/* Layer 2: Clean Odisha Cartographic Vector Layer (fallback & high-contrast geographic guides) */}
        <svg 
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ overflow: "visible" }}
        >
          {(() => {
            const width = 800;
            const height = 320;

            const donorPt = project(dLat, dLng, width, height);
            const recipPt = project(rLat, rLng, width, height);

            // Waypoint projection for road route
            const pts = waypoints.map(w => project(w.lat, w.lng, width, height));
            const pathD = pts.reduce((acc, p, i) => `${acc} ${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`, "");

            // Vehicle projected position
            const vehPt = project(vehiclePos.lat, vehiclePos.lng, width, height);

            // Geographic reference points in Odisha
            const bhubaneswarPt = project(20.2961, 85.8245, width, height);
            const khordhaTownPt = project(20.1810, 85.6200, width, height);
            const puriPt = project(19.8135, 85.8312, width, height);

            return (
              <g>
                {/* Fallback geography background if OSM tiles are blocked or loading */}
                {!tilesLoaded && (
                  <g opacity="0.8">
                    {/* Cartographic Landmass fill */}
                    <rect width="100%" height="100%" fill="#f1f5f9" />
                    
                    {/* Real Daya River corridor */}
                    <path
                      d={`M ${bhubaneswarPt.x - 40} ${bhubaneswarPt.y + 20} Q ${(donorPt.x + recipPt.x)/2 + 20} ${(donorPt.y + recipPt.y)/2} ${donorPt.x + 60} ${donorPt.y + 120}`}
                      fill="none"
                      stroke="#93c5fd"
                      strokeWidth="8"
                      strokeLinecap="round"
                    />
                    <text x={((donorPt.x + recipPt.x)/2 + 35)} y={((donorPt.y + recipPt.y)/2) - 10} fill="#3b82f6" fontSize="10" fontWeight="600" fontStyle="italic">
                      Daya River
                    </text>

                    {/* Regional National Highway 316 Corridor */}
                    <line
                      x1={bhubaneswarPt.x}
                      y1={bhubaneswarPt.y}
                      x2={donorPt.x + 20}
                      y2={donorPt.y + 100}
                      stroke="#cbd5e1"
                      strokeWidth="4"
                      strokeDasharray="4 4"
                    />
                    <text x={bhubaneswarPt.x + 10} y={bhubaneswarPt.y - 10} fill="#64748b" fontSize="10" fontWeight="700">
                      Bhubaneswar (Dist. HQ)
                    </text>
                  </g>
                )}

                {/* Route Casing (White outer shadow for maximum contrast) */}
                <path
                  d={pathD}
                  fill="none"
                  stroke="#ffffff"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity="0.95"
                />

                {/* Primary Route Corridor (Solid clean blue road line) */}
                <path
                  d={pathD}
                  fill="none"
                  stroke="#0284c7"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Subtle Directional Road Dashes */}
                <path
                  d={pathD}
                  fill="none"
                  stroke="#e0f2fe"
                  strokeWidth="1.5"
                  strokeDasharray="6 8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />

                {/* Moving Supply Transport Marker (Pipili -> Jatni) */}
                <g transform={`translate(${vehPt.x}, ${vehPt.y})`}>
                  {/* Subtle pulsing transport halo */}
                  <circle r="12" fill="#0284c7" fillOpacity="0.2" className="animate-ping" />
                  
                  {/* Vehicle base pill */}
                  <rect 
                    x="-14" 
                    y="-11" 
                    width="28" 
                    height="22" 
                    rx="6" 
                    fill="#0C2B4E" 
                    stroke="#ffffff" 
                    strokeWidth="1.5"
                    className="shadow-md"
                  />
                  {/* White transport vehicle icon */}
                  <path 
                    d="M -7 -2 L -3 -2 L 1 2 L 6 2 M -7 2 L 6 2 M -4 6 A 2 2 0 1 0 0 6 M 3 6 A 2 2 0 1 0 7 6" 
                    stroke="#ffffff" 
                    strokeWidth="1.2" 
                    fill="none" 
                    strokeLinecap="round" 
                  />
                  {/* Small In-Transit tooltip tag */}
                  <rect x="-24" y="-24" width="48" height="12" rx="3" fill="#0284c7" />
                  <text x="0" y="-15" fill="#ffffff" fontSize="8" fontWeight="bold" textAnchor="middle">
                    IN TRANSIT
                  </text>
                </g>

                {/* DONOR NODE: Pipili PHC (Green Healthcare Pin) */}
                <g 
                  transform={`translate(${donorPt.x}, ${donorPt.y})`}
                  className="cursor-pointer"
                  onClick={() => setActiveTooltip(activeTooltip === "donor" ? null : "donor")}
                >
                  {/* Base pin shadow */}
                  <ellipse cx="0" cy="4" rx="8" ry="4" fill="#000000" fillOpacity="0.25" />
                  
                  {/* Marker Pin */}
                  <path
                    d="M 0 0 C -12 -12 -12 -28 0 -36 C 12 -28 12 -12 0 0 Z"
                    fill="#059669"
                    stroke="#ffffff"
                    strokeWidth="2"
                    className="filter drop-shadow-sm"
                  />
                  {/* Healthcare Cross inside Donor pin */}
                  <rect x="-2" y="-26" width="4" height="12" rx="1" fill="#ffffff" />
                  <rect x="-6" y="-22" width="12" height="4" rx="1" fill="#ffffff" />

                  {/* Donor Badge Pill */}
                  <rect x="-56" y="8" width="112" height="24" rx="6" fill="#ffffff" stroke="#059669" strokeWidth="1.5" className="shadow-xs" />
                  <text x="0" y="19" fill="#065f46" fontSize="9" fontWeight="800" textAnchor="middle">
                    DONOR: Pipili PHC
                  </text>
                  <text x="0" y="28" fill="#047857" fontSize="8" fontWeight="600" textAnchor="middle">
                    Puri • Surplus Dispatch
                  </text>
                </g>

                {/* RECIPIENT NODE: Jatni CHC (Blue/Navy Hospital Pin) */}
                <g 
                  transform={`translate(${recipPt.x}, ${recipPt.y})`}
                  className="cursor-pointer"
                  onClick={() => setActiveTooltip(activeTooltip === "recipient" ? null : "recipient")}
                >
                  {/* Base pin shadow */}
                  <ellipse cx="0" cy="4" rx="8" ry="4" fill="#000000" fillOpacity="0.25" />
                  
                  {/* Marker Pin */}
                  <path
                    d="M 0 0 C -12 -12 -12 -28 0 -36 C 12 -28 12 -12 0 0 Z"
                    fill="#0C2B4E"
                    stroke="#ffffff"
                    strokeWidth="2"
                    className="filter drop-shadow-sm"
                  />
                  {/* Hospital 'H' inside Recipient pin */}
                  <text x="0" y="-18" fill="#ffffff" fontSize="12" fontWeight="900" textAnchor="middle">
                    H
                  </text>

                  {/* Recipient Badge Pill */}
                  <rect x="-60" y="8" width="120" height="24" rx="6" fill="#ffffff" stroke="#0C2B4E" strokeWidth="1.5" className="shadow-xs" />
                  <text x="0" y="19" fill="#0C2B4E" fontSize="9" fontWeight="800" textAnchor="middle">
                    RECIPIENT: Jatni CHC
                  </text>
                  <text x="0" y="28" fill="#e11d48" fontSize="8" fontWeight="700" textAnchor="middle">
                    Khordha • Deficit Relief
                  </text>
                </g>
              </g>
            );
          })()}
        </svg>

        {/* Map Legend Overlay (Top Left) */}
        <div className="absolute top-3 left-3 bg-white/95 backdrop-blur-xs border border-slate-200 rounded-xl px-3 py-2 shadow-xs text-[11px] space-y-1 z-10 pointer-events-none">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-600 border border-white" />
            <span className="text-slate-700 font-semibold">Donor Facility: <span className="text-slate-900">{donorFacility}</span></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-[#0C2B4E] border border-white" />
            <span className="text-slate-700 font-semibold">Recipient Facility: <span className="text-slate-900">{recipientFacility}</span></span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1 w-4 rounded-full bg-[#0284c7]" />
            <span className="text-slate-500 text-[10px]">Highway Corridor: SH-1 / NH-316</span>
          </div>
        </div>

        {/* Map Attribution (Bottom Right) */}
        <div className="absolute bottom-1 right-2 bg-white/80 backdrop-blur-xs px-2 py-0.5 rounded text-[9px] text-slate-500 font-mono pointer-events-none">
          © OpenStreetMap contributors • Odisha Health GIS
        </div>
      </div>

      {/* Operational Logistics Information Panel */}
      <div className="bg-slate-50 px-4 py-3 border-t border-slate-200">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          
          {/* Card 1: Donor Facility */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-emerald-700 font-bold uppercase tracking-wider flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Donor Facility
              </span>
              <span className="text-[10px] text-slate-400 font-mono font-bold">PURI</span>
            </div>
            <h5 className="text-xs font-bold text-slate-900 truncate" title={donorFacility}>
              {donorFacility}
            </h5>
            <p className="text-[11px] text-slate-500">
              GPS: <span className="font-mono text-[10px] text-slate-700">{dLat.toFixed(4)}°N, {dLng.toFixed(4)}°E</span>
            </p>
          </div>

          {/* Card 2: Cargo & Quantity */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-blue-700 font-bold uppercase tracking-wider flex items-center gap-1">
                <IconPackage size={12} className="text-blue-600" />
                Allocated Supply
              </span>
              <span className="bg-blue-50 text-blue-800 text-[10px] px-1.5 py-0.5 rounded font-mono font-bold">
                VERIFIED
              </span>
            </div>
            <h5 className="text-xs font-bold text-slate-900 truncate">
              {transferQuantity} Units • {medicineName}
            </h5>
            <p className="text-[11px] text-slate-500">
              Surplus rebalance preserving donor safety threshold.
            </p>
          </div>

          {/* Card 3: Logistics Transit */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-amber-700 font-bold uppercase tracking-wider flex items-center gap-1">
                <IconClock size={12} className="text-amber-600" />
                Transit Estimation
              </span>
              <span className="font-mono text-[10px] text-slate-500 font-bold">
                {distanceKm.toFixed(1)} km
              </span>
            </div>
            <h5 className="text-xs font-bold text-slate-900">
              ~{estimatedTransitMins} mins via State Highway 1
            </h5>
            <p className="text-[11px] text-slate-500">
              Direct surface corridor across Khordha-Puri border.
            </p>
          </div>

          {/* Card 4: Recipient Facility */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-rose-700 font-bold uppercase tracking-wider flex items-center gap-1">
                <IconAlertTriangle size={12} className="text-rose-600" />
                Target Need
              </span>
              <span className="bg-rose-50 text-rose-800 text-[10px] px-1.5 py-0.5 rounded font-mono font-bold uppercase">
                {urgencyLevel}
              </span>
            </div>
            <h5 className="text-xs font-bold text-slate-900 truncate" title={recipientFacility}>
              {recipientFacility}
            </h5>
            <p className="text-[11px] text-slate-500">
              GPS: <span className="font-mono text-[10px] text-slate-700">{rLat.toFixed(4)}°N, {rLng.toFixed(4)}°E</span>
            </p>
          </div>

        </div>
      </div>
    </div>
  );
};
