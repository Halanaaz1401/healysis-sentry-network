"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { 
  IconMapPin, 
  IconRoute, 
  IconBuildingHospital, 
  IconArrowRight, 
  IconPlus, 
  IconMinus, 
  IconFocus2, 
  IconTruck, 
  IconPackage, 
  IconClock, 
  IconAlertTriangle
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
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Dynamic container dimensions
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ 
    width: 900, 
    height: 390 
  });

  // Map viewport & pan/zoom state
  const [zoomLevel, setZoomLevel] = useState<number>(11.5);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [tilesFailed, setTilesFailed] = useState<boolean>(false);
  const [animProgress, setAnimProgress] = useState<number>(0);

  // Measure container dimensions dynamically
  useEffect(() => {
    if (!containerRef.current) return;
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          setDimensions({ width: Math.round(rect.width), height: Math.round(rect.height) });
        }
      }
    };
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Verified coordinates for Pipili PHC and Jatni CHC
  const dLat = donorCoords?.lat || 20.1170;
  const dLng = donorCoords?.lng || 85.8330;
  const rLat = recipientCoords?.lat || 20.1650;
  const rLng = recipientCoords?.lng || 85.7050;

  // Center coordinate of corridor
  const centerLat = (dLat + rLat) / 2;
  const centerLng = (dLng + rLng) / 2;

  // Real highway corridor waypoints connecting Pipili and Jatni via State Highway 1 / Daya River bridge
  const waypoints = useMemo(() => [
    { lat: dLat, lng: dLng, label: "Pipili PHC Dispatch" },
    { lat: 20.1240, lng: 85.8180, label: "Pipili Bypass / NH-316" },
    { lat: 20.1380, lng: 85.7820, label: "Daya River Corridor" },
    { lat: 20.1510, lng: 85.7430, label: "Jatni-Pipili State Highway 1" },
    { lat: rLat, lng: rLng, label: "Jatni CHC Receiving" },
  ], [dLat, dLng, rLat, rLng]);

  // Smooth transit animation loop for supplies (0 to 1 over 4.5 seconds)
  useEffect(() => {
    let frameId: number;
    let startTime: number | null = null;
    const duration = 4500;

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

  // Web Mercator pixel projection: converts (lat, lng) to canvas (x, y) matching standard OSM tiles
  const project = useCallback((lat: number, lng: number) => {
    const z = zoomLevel;
    const worldSize = 256 * Math.pow(2, z);
    
    // Pixel coordinate of target
    const targetX = ((lng + 180) / 360) * worldSize;
    const latRad = (lat * Math.PI) / 180;
    const targetY = ((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * worldSize;

    // Pixel coordinate of center
    const centerWorldX = ((centerLng + 180) / 360) * worldSize;
    const cLatRad = (centerLat * Math.PI) / 180;
    const centerWorldY = ((1 - Math.asinh(Math.tan(cLatRad)) / Math.PI) / 2) * worldSize;

    // Viewport relative coordinate with pan offset
    const x = dimensions.width / 2 + (targetX - centerWorldX) + panOffset.x;
    const y = dimensions.height / 2 + (targetY - centerWorldY) + panOffset.y;

    return { x, y };
  }, [centerLat, centerLng, zoomLevel, dimensions, panOffset]);

  // Projected positions of Donor & Recipient
  const donorPt = useMemo(() => project(dLat, dLng), [project, dLat, dLng]);
  const recipPt = useMemo(() => project(rLat, rLng), [project, rLat, rLng]);

  // Waypoints projection & SVG path definition
  const projectedWaypoints = useMemo(() => waypoints.map(w => project(w.lat, w.lng)), [waypoints, project]);
  const routePathD = useMemo(() => {
    return projectedWaypoints.reduce((acc, p, i) => `${acc} ${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`, "");
  }, [projectedWaypoints]);

  // Interpolate vehicle position along route waypoints
  const vehiclePt = useMemo(() => {
    if (projectedWaypoints.length < 2) return donorPt;
    const numSegments = projectedWaypoints.length - 1;
    const scaledP = animProgress * numSegments;
    const segIndex = Math.min(Math.floor(scaledP), numSegments - 1);
    const segT = scaledP - segIndex;

    const p0 = projectedWaypoints[segIndex];
    const p1 = projectedWaypoints[segIndex + 1];

    const curX = p0.x + (p1.x - p0.x) * segT;
    const curY = p0.y + (p1.y - p0.y) * segT;

    return { x: curX, y: curY };
  }, [projectedWaypoints, animProgress, donorPt]);

  // Dynamic OpenStreetMap tile calculation to fill 100% of current dimensions
  const osmTiles = useMemo(() => {
    const z = Math.min(Math.max(Math.floor(zoomLevel), 10), 13);
    const n = Math.pow(2, z);
    const latRad = (centerLat * Math.PI) / 180;
    const centerTileX = ((centerLng + 180) / 360) * n;
    const centerTileY = ((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2) * n;

    const baseTileX = Math.floor(centerTileX);
    const baseTileY = Math.floor(centerTileY);

    const radiusX = Math.ceil(dimensions.width / 512) + 1;
    const radiusY = Math.ceil(dimensions.height / 512) + 1;

    const tiles = [];
    for (let dx = -radiusX; dx <= radiusX; dx++) {
      for (let dy = -radiusY; dy <= radiusY; dy++) {
        const tx = baseTileX + dx;
        const ty = baseTileY + dy;
        tiles.push({
          key: `${z}-${tx}-${ty}`,
          url: `https://tile.openstreetmap.org/${z}/${tx}/${ty}.png`,
          offsetX: (dx - (centerTileX - baseTileX)) * 256,
          offsetY: (dy - (centerTileY - baseTileY)) * 256,
        });
      }
    }
    return tiles;
  }, [centerLat, centerLng, zoomLevel, dimensions]);

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
    setZoomLevel(dimensions.width < 768 ? 11 : 11.5);
    setPanOffset({ x: 0, y: 0 });
  };

  // Estimated driving transit time in minutes (~32 km/h on rural highway)
  const estimatedTransitMins = Math.max(18, Math.round((distanceKm / 32) * 60));

  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs my-4 select-none">
      {/* SECTION B: COMPACT MAP HEADER */}
      <div className="bg-slate-900 text-white px-4 py-2.5 flex flex-wrap items-center justify-between gap-2.5 border-b border-slate-800">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="h-7 w-7 rounded-lg bg-emerald-600/90 flex items-center justify-center text-white shrink-0 shadow-xs">
            <IconRoute size={16} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-100">
                Inter-Facility Transfer Logistics Map
              </h4>
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] px-2 py-0.5 rounded-full font-mono font-bold">
                {distanceKm.toFixed(1)} km
              </span>
            </div>
            <p className="text-[11px] text-slate-400 truncate">
              Corridor: <span className="text-emerald-300 font-semibold">{donorFacility}</span> ({donorDistrict}) &rarr; <span className="text-sky-300 font-semibold">{recipientFacility}</span> ({recipientDistrict})
            </p>
          </div>
        </div>

        {/* Zoom & Center Controls */}
        <div className="flex items-center gap-1.5 text-xs shrink-0">
          <button
            onClick={() => setZoomLevel(prev => Math.min(prev + 0.5, 13.5))}
            className="h-7 w-7 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg flex items-center justify-center transition border border-slate-700 cursor-pointer"
            title="Zoom In"
            type="button"
          >
            <IconPlus size={14} />
          </button>
          <button
            onClick={() => setZoomLevel(prev => Math.max(prev - 0.5, 10))}
            className="h-7 w-7 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg flex items-center justify-center transition border border-slate-700 cursor-pointer"
            title="Zoom Out"
            type="button"
          >
            <IconMinus size={14} />
          </button>
          <button
            onClick={handleResetView}
            className="px-2.5 h-7 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg flex items-center gap-1 text-[11px] font-medium transition border border-slate-700 cursor-pointer"
            title="Reset and Center Route"
            type="button"
          >
            <IconFocus2 size={13} />
            <span className="hidden sm:inline">Center Route</span>
          </button>
        </div>
      </div>

      {/* SECTION A: MAP VIEWPORT CONTAINER (Full width, controlled height: 380-420px) */}
      <div 
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className={`relative w-full h-[380px] sm:h-[400px] md:h-[420px] overflow-hidden bg-slate-100 ${isDragging ? "cursor-grabbing" : "cursor-grab"}`}
        style={{ touchAction: "none" }}
      >
        {/* Layer 1: OpenStreetMap Raster Tiles (fills full width and height) */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div 
            className="absolute top-1/2 left-1/2"
            style={{ 
              transform: `translate(${panOffset.x}px, ${panOffset.y}px)`,
              transition: isDragging ? "none" : "transform 0.1s ease-out"
            }}
          >
            {osmTiles.map(tile => (
              <img
                key={tile.key}
                src={tile.url}
                alt=""
                onError={() => setTilesFailed(true)}
                className="absolute w-[256px] h-[256px] max-w-none opacity-95"
                style={{
                  left: `${tile.offsetX}px`,
                  top: `${tile.offsetY}px`,
                  filter: "contrast(1.03) saturate(0.92)"
                }}
                draggable={false}
              />
            ))}
          </div>
        </div>

        {/* Layer 2: Clean High-Contrast Regional Topography Fallback (if tiles offline) */}
        {tilesFailed && (
          <div className="absolute inset-0 bg-[#f1f5f9] pointer-events-none">
            <svg className="w-full h-full">
              {/* Subtle grid */}
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="1"/>
              </pattern>
              <rect width="100%" height="100%" fill="url(#grid)" />
              {/* Daya River Path */}
              <path
                d={`M ${dimensions.width * 0.45} 0 Q ${dimensions.width * 0.52} ${dimensions.height * 0.5} ${dimensions.width * 0.7} ${dimensions.height}`}
                fill="none"
                stroke="#bfdbfe"
                strokeWidth="16"
                strokeLinecap="round"
              />
              <text x={dimensions.width * 0.56} y={dimensions.height * 0.48} fill="#3b82f6" fontSize="11" fontWeight="bold" fontStyle="italic">
                Daya River Basin
              </text>
            </svg>
          </div>
        )}

        {/* Layer 3: SVG Route Line, Directional Arrows & Animated In-Transit Transport */}
        <svg 
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ overflow: "visible" }}
        >
          <g>
            {/* Highway Route Outer Casing for maximum contrast */}
            <path
              d={routePathD}
              fill="none"
              stroke="#ffffff"
              strokeWidth="9"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.95"
            />

            {/* Primary Highway Route Line (Solid crisp royal blue) */}
            <path
              d={routePathD}
              fill="none"
              stroke="#0284c7"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Directional Flow Dashes along route */}
            <path
              d={routePathD}
              fill="none"
              stroke="#ffffff"
              strokeWidth="1.5"
              strokeDasharray="8 10"
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity="0.9"
            />

            {/* SECTION E: SUBTLE ANIMATED IN-TRANSIT VEHICLE */}
            <g transform={`translate(${vehiclePt.x}, ${vehiclePt.y})`}>
              {/* Subtle soft pulse */}
              <circle r="14" fill="#0284c7" fillOpacity="0.25" />
              
              {/* Vehicle Pill */}
              <rect 
                x="-14" 
                y="-11" 
                width="28" 
                height="22" 
                rx="6" 
                fill="#0C2B4E" 
                stroke="#ffffff" 
                strokeWidth="2"
                className="filter drop-shadow-sm"
              />
              {/* Clean delivery icon */}
              <path 
                d="M -7 -2 L -3 -2 L 1 2 L 6 2 M -7 2 L 6 2 M -4 6 A 2 2 0 1 0 0 6 M 3 6 A 2 2 0 1 0 7 6" 
                stroke="#ffffff" 
                strokeWidth="1.4" 
                fill="none" 
                strokeLinecap="round" 
              />
              {/* Small in-transit tag */}
              <rect x="-24" y="-23" width="48" height="11" rx="3" fill="#0284c7" />
              <text x="0" y="-15" fill="#ffffff" fontSize="7.5" fontWeight="bold" textAnchor="middle">
                IN TRANSIT
              </text>
            </g>

            {/* DONOR PIN (Pipili PHC - Green Health Pin) */}
            <g transform={`translate(${donorPt.x}, ${donorPt.y})`}>
              <ellipse cx="0" cy="3" rx="7" ry="3.5" fill="#000000" fillOpacity="0.25" />
              <path
                d="M 0 0 C -10 -10 -10 -24 0 -30 C 10 -24 10 -10 0 0 Z"
                fill="#059669"
                stroke="#ffffff"
                strokeWidth="2"
                className="filter drop-shadow-sm"
              />
              <rect x="-1.5" y="-22" width="3" height="10" rx="0.5" fill="#ffffff" />
              <rect x="-5" y="-18.5" width="10" height="3" rx="0.5" fill="#ffffff" />
            </g>

            {/* RECIPIENT PIN (Jatni CHC - Navy Hospital Pin) */}
            <g transform={`translate(${recipPt.x}, ${recipPt.y})`}>
              <ellipse cx="0" cy="3" rx="7" ry="3.5" fill="#000000" fillOpacity="0.25" />
              <path
                d="M 0 0 C -10 -10 -10 -24 0 -30 C 10 -24 10 -10 0 0 Z"
                fill="#0C2B4E"
                stroke="#ffffff"
                strokeWidth="2"
                className="filter drop-shadow-sm"
              />
              <text x="0" y="-15" fill="#ffffff" fontSize="10" fontWeight="900" textAnchor="middle">
                H
              </text>
            </g>
          </g>
        </svg>

        {/* SECTION D: DEDICATED MARKER CALLOUT CARDS WITH POINTERS */}
        {/* Donor Callout (Pipili PHC): Positioned south-east of pin, never collides with route exiting north-west */}
        <div 
          className="absolute pointer-events-none transition-transform z-10"
          style={{
            left: `${donorPt.x + 12}px`,
            top: `${donorPt.y - 15}px`,
          }}
        >
          <div className="relative bg-white/95 backdrop-blur-xs border-2 border-emerald-600 rounded-xl p-2.5 shadow-md max-w-[190px]">
            {/* Left anchor pointer notch */}
            <div className="absolute -left-2 top-3 w-0 h-0 border-y-4 border-y-transparent border-r-8 border-r-emerald-600" />
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="bg-emerald-600 text-white text-[9px] font-black uppercase px-1.5 py-0.5 rounded tracking-wider">
                DONOR
              </span>
              <span className="text-[10px] font-bold text-emerald-800 truncate">
                Surplus Dispatch
              </span>
            </div>
            <div className="text-xs font-extrabold text-slate-900 leading-tight">
              {donorFacility}
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              District: {donorDistrict}
            </div>
          </div>
        </div>

        {/* Recipient Callout (Jatni CHC): Positioned north-east of pin, never collides with route exiting south-east */}
        <div 
          className="absolute pointer-events-none transition-transform z-10"
          style={{
            left: `${recipPt.x + 14}px`,
            top: `${recipPt.y - 42}px`,
          }}
        >
          <div className="relative bg-white/95 backdrop-blur-xs border-2 border-[#0C2B4E] rounded-xl p-2.5 shadow-md max-w-[190px]">
            {/* Left anchor pointer notch */}
            <div className="absolute -left-2 top-8 w-0 h-0 border-y-4 border-y-transparent border-r-8 border-r-[#0C2B4E]" />
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="bg-[#0C2B4E] text-white text-[9px] font-black uppercase px-1.5 py-0.5 rounded tracking-wider">
                RECIPIENT
              </span>
              <span className="text-[10px] font-bold text-rose-700 truncate">
                Deficit Relief
              </span>
            </div>
            <div className="text-xs font-extrabold text-slate-900 leading-tight">
              {recipientFacility}
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              District: {recipientDistrict}
            </div>
          </div>
        </div>

        {/* SECTION C: DEDICATED COMPACT FLOATING LEGEND (Top Left, no overlap) */}
        <div className="absolute top-3 left-3 bg-white/95 backdrop-blur-xs border border-slate-200/90 rounded-xl p-3 shadow-md max-w-[260px] text-[11px] space-y-1.5 z-20 pointer-events-none">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
            Logistics Corridor Legend
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-600 shrink-0 border border-white" />
            <span className="text-slate-700 truncate">
              <strong className="text-slate-900">Donor Facility:</strong> {donorFacility} ({donorDistrict})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-[#0C2B4E] shrink-0 border border-white" />
            <span className="text-slate-700 truncate">
              <strong className="text-slate-900">Recipient Facility:</strong> {recipientFacility} ({recipientDistrict})
            </span>
          </div>
          <div className="flex items-center gap-2 pt-0.5 border-t border-slate-100">
            <span className="h-1 w-4 rounded-full bg-[#0284c7] shrink-0" />
            <span className="text-slate-600 text-[10px] truncate">
              <strong className="text-slate-800">Highway Corridor:</strong> SH-1 / NH-316
            </span>
          </div>
        </div>

        {/* Map Attribution (Bottom Right) */}
        <div className="absolute bottom-1 right-2 bg-white/80 backdrop-blur-xs px-2 py-0.5 rounded text-[9px] text-slate-500 font-mono pointer-events-none z-10">
          © OpenStreetMap contributors • Odisha Health GIS
        </div>
      </div>

      {/* SECTION H: OPERATIONAL LOGISTICS INFORMATION CARDS */}
      <div className="bg-slate-50 p-3.5 border-t border-slate-200">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          
          {/* Card 1: Donor Facility */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs flex flex-col justify-between h-full space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-emerald-700 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Donor Facility
              </span>
              <span className="text-[10px] text-slate-400 font-mono font-bold uppercase">{donorDistrict}</span>
            </div>
            <div>
              <h5 className="text-xs font-extrabold text-slate-900 truncate" title={donorFacility}>
                {donorFacility}
              </h5>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                GPS: {dLat.toFixed(4)}°N, {dLng.toFixed(4)}°E
              </p>
            </div>
            <p className="text-[10px] text-emerald-700 font-medium pt-1 border-t border-slate-100">
              Verified Surplus Hub • Dispatch Ready
            </p>
          </div>

          {/* Card 2: Allocated Supply */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs flex flex-col justify-between h-full space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-blue-700 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <IconPackage size={13} className="text-blue-600" />
                Allocated Supply
              </span>
              <span className="bg-blue-50 text-blue-800 text-[10px] px-1.5 py-0.5 rounded font-mono font-bold">
                VERIFIED
              </span>
            </div>
            <div>
              <h5 className="text-xs font-extrabold text-slate-900 truncate" title={`${transferQuantity} Units • ${medicineName}`}>
                {transferQuantity} Units • {medicineName}
              </h5>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Targeted redistribution allocation
              </p>
            </div>
            <p className="text-[10px] text-blue-700 font-medium pt-1 border-t border-slate-100">
              Preserves donor safety stock threshold
            </p>
          </div>

          {/* Card 3: Transit Estimation */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs flex flex-col justify-between h-full space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-amber-700 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <IconClock size={13} className="text-amber-600" />
                Transit Estimation
              </span>
              <span className="font-mono text-[10px] text-slate-600 font-bold">
                {distanceKm.toFixed(1)} km
              </span>
            </div>
            <div>
              <h5 className="text-xs font-extrabold text-slate-900 truncate">
                ~{estimatedTransitMins} mins via State Highway 1
              </h5>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Corridor: NH-316 &rarr; SH-1 Road
              </p>
            </div>
            <p className="text-[10px] text-amber-700 font-medium pt-1 border-t border-slate-100">
              Low-latency ground transit corridor
            </p>
          </div>

          {/* Card 4: Target Need */}
          <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-2xs flex flex-col justify-between h-full space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-rose-700 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <IconAlertTriangle size={13} className="text-rose-600" />
                Target Need
              </span>
              <span className="bg-rose-50 text-rose-800 text-[10px] px-1.5 py-0.5 rounded font-mono font-bold uppercase">
                {urgencyLevel}
              </span>
            </div>
            <div>
              <h5 className="text-xs font-extrabold text-slate-900 truncate" title={recipientFacility}>
                {recipientFacility}
              </h5>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                GPS: {rLat.toFixed(4)}°N, {rLng.toFixed(4)}°E
              </p>
            </div>
            <p className="text-[10px] text-rose-700 font-medium pt-1 border-t border-slate-100">
              Immediate stockout mitigation
            </p>
          </div>

        </div>
      </div>
    </div>
  );
};
