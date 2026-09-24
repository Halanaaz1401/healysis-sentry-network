"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { MOCK_USERS, UserIdentity, getApiBaseUrl } from "@/config";

interface AuthContextType {
  user: UserIdentity | null;
  loading: boolean;
  login: (user: UserIdentity) => void;
  logout: () => void;
  getAuthHeaders: () => Record<string, string>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserIdentity | null>(null);
  const [loading, setLoading] = useState(true);

  const syncWithBackend = async (currentUser: UserIdentity) => {
    try {
      const baseUrl = getApiBaseUrl();
      const token = currentUser.token.startsWith("Bearer ")
        ? currentUser.token
        : `Bearer ${currentUser.token}`;
      const res = await fetch(`${baseUrl}/api/v1/auth/me`, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": token
        }
      });
      if (res.ok) {
        const profile = await res.json();
        setUser((prev) => {
          if (!prev || prev.firebase_uid !== profile.firebase_uid) return prev;
          const updated: UserIdentity = {
            ...prev,
            firebase_uid: profile.firebase_uid,
            email: profile.email,
            full_name: profile.full_name,
            role: profile.role,
            facility_id: profile.facility_id
          };
          localStorage.setItem("healysis_user", JSON.stringify(updated));
          return updated;
        });
      } else if (res.status === 401) {
        // Token expired or invalid; clear session
        setUser(null);
        localStorage.removeItem("healysis_user");
      }
    } catch {
      // Backend offline or unreachable during initial load; retain local state
    }
  };

  useEffect(() => {
    let initialUser: UserIdentity | null = null;
    const saved = typeof window !== "undefined" ? localStorage.getItem("healysis_user") : null;
    if (saved) {
      try {
        initialUser = JSON.parse(saved);
      } catch {
        initialUser = null;
      }
    }
    setUser(initialUser);
    setLoading(false);
    if (initialUser) {
      syncWithBackend(initialUser);
    }
  }, []);

  const login = (newUser: UserIdentity) => {
    setUser(newUser);
    localStorage.setItem("healysis_user", JSON.stringify(newUser));
    syncWithBackend(newUser);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("healysis_user");
  };

  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json"
    };
    if (user?.token) {
      headers["Authorization"] = user.token.startsWith("Bearer ") ? user.token : `Bearer ${user.token}`;
    }
    return headers;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, getAuthHeaders }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
