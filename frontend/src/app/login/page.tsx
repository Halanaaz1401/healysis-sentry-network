"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { MOCK_USERS } from "@/config";
import { IconShieldCheck, IconLock, IconUserCheck, IconBuildingHospital, IconArrowRight, IconAlertCircle } from "@tabler/icons-react";

export default function LoginPage() {
  const router = useRouter();
  const { user, login } = useAuth();
  const [selectedUser, setSelectedUser] = useState(MOCK_USERS[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      login(selectedUser as any);
      setTimeout(() => {
        setLoading(false);
        router.push("/dashboard");
      }, 500);
    } catch (err) {
      setLoading(false);
      setError("Authentication failed. Please verify credentials.");
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F4F4] text-slate-900 flex flex-col justify-center items-center p-6 antialiased">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 shadow-md p-8 space-y-6">
        
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="h-14 w-14 bg-[#0C2B4E] rounded-xl flex items-center justify-center p-3 shadow-xs">
            <svg viewBox="0 0 100 100" fill="none" className="w-full h-full">
              <path d="M50 10L90 85H65L50 55L35 85H10L50 10Z" fill="white" />
              <path d="M50 55L65 85H35L50 55Z" fill="#1D546C" />
              <path d="M22 85L35 60L48 85H22Z" fill="#94A3B8" />
            </svg>
          </div>
          <h1 className="text-3xl font-black tracking-tight text-[#0C2B4E]">Healysis</h1>
          <span className="text-xs font-bold tracking-widest text-[#1D546C] uppercase font-mono">
            HEALTHCARE RESOURCE INTELLIGENCE
          </span>
          <p className="text-xs text-slate-500 max-w-xs">
            Secure Authentication Portal for CHCs & PHCs across Odisha & West Bengal.
          </p>
        </div>

        {error && (
          <div className="bg-rose-50 border border-rose-200 text-rose-800 text-xs p-3 rounded-lg flex items-center gap-2">
            <IconAlertCircle size={16} className="text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleLoginSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold uppercase text-slate-600 tracking-wider block">
              Select Authenticated Identity & RBAC Role
            </label>
            <div className="space-y-2">
              {MOCK_USERS.map((u) => (
                <div
                  key={u.firebase_uid}
                  onClick={() => setSelectedUser(u)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                    selectedUser.firebase_uid === u.firebase_uid
                      ? "border-[#0C2B4E] bg-slate-50 ring-2 ring-[#0C2B4E]/10"
                      : "border-slate-200 hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-[#0C2B4E]">{u.full_name}</span>
                    <span className="text-[11px] text-slate-500">{u.email}</span>
                    <span className="text-[10px] text-[#1D546C] font-semibold mt-0.5">{u.facility_name}</span>
                  </div>
                  <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded border ${
                    u.role === "ADMIN" ? "bg-purple-50 text-purple-800 border-purple-300" :
                    u.role === "CDMO" ? "bg-amber-50 text-amber-800 border-amber-300" :
                    "bg-blue-50 text-blue-800 border-blue-300"
                  }`}>
                    {u.role}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white font-bold text-xs py-3 rounded-xl transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
          >
            {loading ? "Authenticating Session..." : "Enter Healysis Platform"}
            <IconArrowRight size={16} />
          </button>
        </form>

        <div className="pt-2 border-t border-slate-100 text-center">
          <span className="text-[11px] text-slate-400 font-mono">
            Firebase Auth Verified · Server-Side Server RBAC Enforced
          </span>
        </div>
      </div>
    </div>
  );
}
