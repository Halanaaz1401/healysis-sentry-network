"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { MOCK_USERS } from "@/config";
import { 
  IconLayoutDashboard, 
  IconBuildingHospital, 
  IconReportMedical, 
  IconTrendingUp, 
  IconTruckDelivery, 
  IconSparkles, 
  IconLogout, 
  IconMenu2, 
  IconX,
  IconChevronDown,
  IconLock,
  IconShieldCheck,
  IconUser,
  IconKey
} from "@tabler/icons-react";

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const router = useRouter();
  const { user, login, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Keyboard Escape & Outside Click handling for accessibility
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setUserDropdownOpen(false);
        setMobileOpen(false);
      }
    };

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Strict sidebar navigation grouping
  const navGroups = [
    {
      group: "OVERVIEW",
      items: [
        { label: "Dashboard", href: "/dashboard", icon: IconLayoutDashboard },
      ]
    },
    {
      group: "MONITOR",
      items: [
        { label: "Facilities", href: "/facilities", icon: IconBuildingHospital },
        { label: "Resources", href: "/resources", icon: IconReportMedical },
        { label: "Forecasts & Risk", href: "/forecasts", icon: IconTrendingUp },
      ]
    },
    {
      group: "ACT",
      items: [
        { label: "Redistribution", href: "/recommendations", icon: IconTruckDelivery },
      ]
    },
    {
      group: "INTELLIGENCE",
      items: [
        { label: "AI Advisor", href: "/advisor", icon: IconSparkles },
      ]
    }
  ];

  return (
    <div className="min-h-screen bg-[#F4F4F4] text-slate-900 flex flex-col font-sans antialiased selection:bg-[#1D546C] selection:text-white">
      
      {/* Top Header Bar */}
      <header className="bg-white/95 backdrop-blur-md border-b border-slate-200 px-6 py-3 shadow-xs flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-1.5 text-slate-600 hover:text-black rounded-lg transition"
            aria-label="Toggle navigation drawer"
          >
            {mobileOpen ? <IconX size={20} /> : <IconMenu2 size={20} />}
          </button>

          <Link href="/dashboard" className="flex items-center gap-2.5 cursor-pointer select-none">
            <div className="h-9 w-9 bg-[#0C2B4E] rounded-lg flex items-center justify-center p-2 shadow-2xs">
              <svg viewBox="0 0 100 100" fill="none" className="w-full h-full">
                <path d="M50 10L90 85H65L50 55L35 85H10L50 10Z" fill="white" />
                <path d="M50 55L65 85H35L50 55Z" fill="#1D546C" />
                <path d="M22 85L35 60L48 85H22Z" fill="#94A3B8" />
              </svg>
            </div>
            
            <div className="flex flex-col justify-center">
              <span className="text-xl font-black tracking-tight text-[#0C2B4E] leading-none">
                Healysis
              </span>
              <span className="text-[8.5px] font-bold tracking-widest text-[#1D546C] uppercase mt-0.5 font-mono">
                TELEMETRY NETWORK
              </span>
            </div>
          </Link>
          
          <div className="hidden sm:flex items-center gap-2 border-l border-slate-200 pl-4 h-7">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] bg-[#0C2B4E] text-white px-2 py-0.5 rounded font-mono font-bold tracking-wider shadow-2xs">
              OPERATIONAL
            </span>
          </div>
        </div>

        {/* Right Side Authentication / Account Control */}
        <div className="relative" ref={dropdownRef}>
          {user ? (
            <button
              onClick={() => setUserDropdownOpen(!userDropdownOpen)}
              className="flex items-center gap-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl text-xs transition cursor-pointer"
              aria-expanded={userDropdownOpen}
              aria-label="User account menu"
            >
              <div className="h-7 w-7 rounded-lg bg-[#0C2B4E] text-white font-bold flex items-center justify-center text-xs shrink-0 shadow-2xs">
                {user.full_name.charAt(0)}
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="text-xs font-bold text-[#0C2B4E] leading-tight">{user.full_name}</span>
                <span className="text-[10px] text-slate-500 font-mono">{user.role}</span>
              </div>
              <span className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded border hidden sm:inline-block ${
                user.role === "ADMIN" ? "bg-purple-50 text-purple-800 border-purple-300" :
                user.role === "CDMO" ? "bg-amber-50 text-amber-800 border-amber-300" :
                "bg-blue-50 text-blue-800 border-blue-300"
              }`}>
                {user.role}
              </span>
              <IconChevronDown size={14} className={`text-slate-400 transition-transform duration-200 ${userDropdownOpen ? "rotate-180" : ""}`} />
            </button>
          ) : (
            <Link
              href="/login"
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-4 py-2 rounded-xl text-xs font-bold transition shadow-2xs cursor-pointer flex items-center gap-1.5"
            >
              <IconKey size={15} />
              Sign In
            </Link>
          )}

          {/* Compact Account & Session Dropdown Menu */}
          {userDropdownOpen && user && (
            <div className="absolute right-0 mt-2 w-72 bg-white rounded-2xl border border-slate-200 shadow-xl p-4 space-y-4 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              
              {/* ACTIVE SESSION */}
              <div className="border-b border-slate-100 pb-3 space-y-1">
                <span className="text-[9.5px] font-extrabold uppercase text-slate-400 tracking-wider font-mono block">ACTIVE SESSION</span>
                <p className="text-xs font-bold text-[#0C2B4E]">{user.full_name}</p>
                <p className="text-[11px] text-slate-500 font-mono">{user.email}</p>
                <div className="pt-1 flex items-center justify-between">
                  <span className={`text-[9px] font-extrabold uppercase px-2 py-0.5 rounded border ${
                    user.role === "ADMIN" ? "bg-purple-50 text-purple-800 border-purple-300" :
                    user.role === "CDMO" ? "bg-amber-50 text-amber-800 border-amber-300" :
                    "bg-blue-50 text-blue-800 border-blue-300"
                  }`}>
                    {user.role}
                  </span>
                  <span className="text-[10px] text-[#1D546C] font-mono font-semibold">{user.facility_name}</span>
                </div>
              </div>

              {/* DEMO IDENTITY SWITCHER */}
              <div className="space-y-1">
                <span className="text-[9.5px] font-extrabold uppercase text-slate-400 tracking-wider font-mono block">SWITCH OPERATIONAL IDENTITY</span>
                <div className="space-y-1 max-h-44 overflow-y-auto pr-1">
                  {MOCK_USERS.map((u) => (
                    <button
                      key={u.firebase_uid}
                      onClick={() => {
                        login(u);
                        setUserDropdownOpen(false);
                      }}
                      className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-medium transition flex items-center justify-between ${
                        user.firebase_uid === u.firebase_uid
                          ? "bg-slate-100 text-[#0C2B4E] font-bold border border-slate-200"
                          : "hover:bg-slate-50 text-slate-700"
                      }`}
                    >
                      <span className="truncate pr-2">{u.full_name}</span>
                      <span className="text-[9px] font-mono font-bold text-slate-500 shrink-0">{u.role}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* SECURITY & LOGOUT */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                  <IconLock size={12} className="text-emerald-600" /> RBAC Verified
                </span>
                <button
                  onClick={() => {
                    logout();
                    setUserDropdownOpen(false);
                    router.push("/login");
                  }}
                  className="text-xs font-bold text-rose-600 hover:text-rose-700 flex items-center gap-1 cursor-pointer"
                >
                  <IconLogout size={14} /> Log Out
                </button>
              </div>

            </div>
          )}
        </div>
      </header>

      {/* Main Body Layout with Sidebar */}
      <div className="flex-1 flex max-w-7xl w-full mx-auto">
        {/* Navigation Sidebar */}
        <aside className={`w-56 bg-white border-r border-slate-200 p-4 space-y-4 shrink-0 ${mobileOpen ? "block fixed inset-y-0 left-0 z-50 shadow-2xl" : "hidden md:block"}`}>
          {navGroups.map((group, idx) => (
            <div key={idx} className="space-y-1">
              <div className="px-3 text-[9.5px] font-extrabold uppercase text-slate-400 tracking-wider font-mono">
                {group.group}
              </div>
              {group.items.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-bold transition-all duration-150 ${
                      active 
                        ? "bg-[#0C2B4E] text-white shadow-xs" 
                        : "text-slate-700 hover:bg-slate-100 hover:text-[#0C2B4E]"
                    }`}
                  >
                    <div className="w-5 h-5 flex items-center justify-center shrink-0">
                      <Icon size={17} className={active ? "text-white" : "text-[#1D546C]"} />
                    </div>
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}

          {user && user.role === "FACILITY_OFFICER" && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl text-xs space-y-1 mt-4">
              <span className="font-bold text-blue-900 block flex items-center gap-1">
                <IconLock size={13} /> Facility Scope Scoped
              </span>
              <p className="text-[11px] text-blue-700 leading-tight">
                Assigned: <strong>{user.facility_name}</strong>
              </p>
            </div>
          )}
        </aside>

        {/* Page Content Container with Staggered Entrance Motion */}
        <main className="flex-1 p-6 space-y-6 overflow-x-hidden animate-in fade-in slide-in-from-bottom-1 duration-200">
          {children}
        </main>
      </div>
    </div>
  );
};
