"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { MOCK_USERS, UserIdentity } from "@/config";

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

  useEffect(() => {
    const saved = localStorage.getItem("healysis_user");
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch (e) {
        setUser(MOCK_USERS[0]);
      }
    } else {
      setUser(MOCK_USERS[0]); // Default initial demo session to System Admin
    }
    setLoading(false);
  }, []);

  const login = (newUser: UserIdentity) => {
    setUser(newUser);
    localStorage.setItem("healysis_user", JSON.stringify(newUser));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("healysis_user");
  };

  const getAuthHeaders = () => {
    return {
      "Content-Type": "application/json",
      "Authorization": user?.token || MOCK_USERS[0].token
    };
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
