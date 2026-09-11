"use client";

import React, { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import { 
  IconSparkles, 
  IconSend, 
  IconInfoCircle,
  IconUser,
  IconRobot
} from "@tabler/icons-react";

interface ChatMessage {
  id: string;
  sender: "user" | "advisor";
  text: string;
  answer?: string;
  summary?: string;
  severity?: string;
  recommended_actions?: string[];
  limitations?: string;
  timestamp: string;
}

export default function AdvisorPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "init",
      sender: "advisor",
      text: "Hello! I am the Healysis AI Advisor powered by Google GenAI. How can I assist with healthcare resource forecasting, risk analysis, or redistribution planning today?",
      timestamp: "Just now"
    }
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const sampleQuestions = [
    "Why is Jatni CHC at critical risk?",
    "Which facilities require ORS rebalancing?",
    "Compare stock levels between Jatni and Cuttack",
    "List active alerts for West Bengal facilities",
    "What is the stockout risk for insulin?"
  ];

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputMessage;
    if (!textToSend.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString()
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInputMessage("");
    setLoading(true);

    try {
      const data = await apiFetch<any>("/api/v1/advisor/chat", {
        method: "POST",
        body: JSON.stringify({
          message: textToSend,
          facility_id: user?.facility_id || undefined
        })
      });

      const advisorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "advisor",
        text: data.answer || data.summary || "Response received.",
        answer: data.answer,
        summary: data.summary,
        severity: data.severity,
        recommended_actions: data.recommended_actions,
        limitations: data.limitations,
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages((prev) => [...prev, advisorMsg]);
    } catch (err: any) {
      console.error("AI Advisor request error:", err);
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: "advisor",
        text: err.message || "Error connecting to AI Advisor service.",
        timestamp: new Date().toLocaleTimeString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-5xl mx-auto">
        
        {/* Header */}
        <div>
          <h1 className="text-2xl font-black text-[#0C2B4E] flex items-center gap-2">
            <IconSparkles className="text-[#1D546C]" size={24} />
            Healysis Gemini AI Advisor
          </h1>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Operational Healthcare Resource Decision Support Assistant
          </p>
        </div>

        {/* Advisory Callout Notice */}
        <div className="bg-blue-50 border border-blue-200 p-4 rounded-xl flex items-start gap-3 text-blue-900">
          <IconInfoCircle size={20} className="text-blue-600 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <span className="font-bold">Decision Support Only:</span>
            <p className="leading-relaxed">
              The AI Advisor synthesizes verified telemetry to provide concise operational recommendations. All physical stock transfers require human CDMO/Admin approval.
            </p>
          </div>
        </div>

        {/* Sample Prompt Chips */}
        <div className="flex flex-wrap gap-2">
          {sampleQuestions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(q)}
              className="text-xs font-semibold bg-white hover:bg-slate-50 text-[#0C2B4E] border border-slate-200 px-3 py-1.5 rounded-full transition shadow-2xs cursor-pointer"
            >
              "{q}"
            </button>
          ))}
        </div>

        {/* Chat Stream Window */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 space-y-6 min-h-[420px] flex flex-col justify-between">
          
          <div className="space-y-6 overflow-y-auto max-h-[520px] pr-2">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex gap-3 ${m.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${
                  m.sender === "user" ? "bg-[#0C2B4E] text-white" : "bg-slate-100 text-[#1D546C] border border-slate-200"
                }`}>
                  {m.sender === "user" ? <IconUser size={16} /> : <IconRobot size={16} />}
                </div>

                <div className={`space-y-3 max-w-2xl rounded-2xl p-4 text-xs ${
                  m.sender === "user" 
                    ? "bg-[#0C2B4E] text-white rounded-tr-none" 
                    : "bg-slate-50 border border-slate-200 text-slate-800 rounded-tl-none"
                }`}>
                  <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>

                  {/* Clean Severity Badge & Optional Actions */}
                  {m.sender === "advisor" && m.severity && (
                    <div className="pt-3 border-t border-slate-200 space-y-2 font-mono">
                      
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">Severity:</span>
                        <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded border ${
                          m.severity === "CRITICAL" ? "bg-rose-100 text-rose-800 border-rose-300" :
                          m.severity === "WARNING" ? "bg-amber-100 text-amber-800 border-amber-300" :
                          "bg-emerald-100 text-emerald-800 border-emerald-300"
                        }`}>
                          {m.severity}
                        </span>
                      </div>

                    </div>
                  )}

                  <span className="text-[9px] text-slate-400 block text-right">{m.timestamp}</span>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-3 text-xs text-slate-500 italic">
                <IconRobot size={18} className="animate-spin text-[#1D546C]" />
                <span>Consulting verified telemetry...</span>
              </div>
            )}

          </div>

          {/* Input Box */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            className="flex items-center gap-2 pt-4 border-t border-slate-100"
          >
            <input
              type="text"
              placeholder="Ask Healysis AI Advisor about stock levels, forecasts, or risks..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              className="flex-1 border border-slate-200 rounded-xl px-4 py-3 text-xs font-medium outline-none focus:border-[#0C2B4E]"
            />
            <button
              type="submit"
              disabled={loading || !inputMessage.trim()}
              className="bg-[#0C2B4E] hover:bg-[#1A3D64] active:scale-95 text-white px-5 py-3 rounded-xl text-xs font-bold transition shadow-xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <IconSend size={16} />
              Ask Advisor
            </button>
          </form>

        </div>

      </div>
    </AppShell>
  );
}
