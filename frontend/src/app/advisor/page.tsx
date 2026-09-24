"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/apiClient";
import { 
  IconSparkles, 
  IconSend, 
  IconInfoCircle,
  IconUser,
  IconRobot,
  IconCheck,
  IconX,
  IconPackage,
  IconBuildingHospital,
  IconShieldCheck,
  IconAlertCircle,
  IconLoader,
  IconPlus,
  IconMessage,
  IconTrash,
  IconMessages,
  IconHistory,
  IconMicrophone,
  IconMicrophoneOff,
  IconPlayerStop,
  IconVolume,
  IconVolumeOff,
  IconLanguage
} from "@tabler/icons-react";

// =============================================
// Web Speech API type declarations
// (Browser-native — no credentials required)
// Not always present in TS DOM lib, defined here
// for the subset of the API we actually use.
// =============================================
type VoiceState = "idle" | "recording" | "transcribing" | "error";

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionResult {
  [index: number]: SpeechRecognitionAlternative;
  length: number;
  isFinal: boolean;
}

interface SpeechRecognitionResultList {
  [index: number]: SpeechRecognitionResult;
  length: number;
}

interface SpeechRecognitionResultEvent {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrEvent {
  error: string;
  message: string;
}

interface SpeechRecognitionInstance {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  continuous: boolean;
  onstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onnomatch: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition: new () => SpeechRecognitionInstance;
  }
}

interface PendingInventoryUpdate {
  facility_id: number;
  facility_name: string;
  item_code: string;
  item_name: string;
  current_quantity: number;
  new_quantity: number;
  current_daily_demand: number;
  new_daily_demand?: number;
  unit: string;
  confirmation_token: string;
}

interface UpdateConfirmationResult {
  status: string;
  message: string;
  facility_id: number;
  facility_name: string;
  item_code: string;
  item_name: string;
  previous_quantity: number;
  new_quantity: number;
  daily_demand: number;
  days_of_cover: number;
  severity: string;
  audit_event_id: string;
}

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
  pending_update?: PendingInventoryUpdate;
  update_confirmed?: boolean;
  update_result?: UpdateConfirmationResult;
  update_cancelled?: boolean;
  confirming?: boolean;
  confirm_error?: string;
}

interface ConversationSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

const DEFAULT_INITIAL_MESSAGE: ChatMessage = {
  id: "init",
  sender: "advisor",
  text: "Hello! I am the Healysis AI Advisor powered by Google GenAI. Frontline workers can submit stock updates naturally (e.g., 'Aaj ORS ka stock 180 hai' or 'Paracetamol stock is 320 and daily demand is 35'). You can also ask operational questions about risk and redistribution.",
  timestamp: "Just now"
};

export default function AdvisorPage() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([DEFAULT_INITIAL_MESSAGE]);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState(false);
  const [activeUid, setActiveUid] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // ============================================
  // Feature 2.2 — Voice Frontline Input State
  // Uses Web Speech API (browser-native, zero-credential)
  // NOT Google Cloud Speech-to-Text
  //
  // HYDRATION SAFETY: speechSupported is initialized false.
  // It is set to the real value only in a useEffect (after
  // hydration). This ensures SSR and initial client render
  // produce identical DOM output (both render no mic button),
  // and the button appears on the client after mount.
  // ============================================
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  // speechSupported: false on server, set to real detection after mount
  const [speechSupported, setSpeechSupported] = useState<boolean>(false);
  // Bug 2 fix: language toggle for voice input (en-IN = English/Hinglish, hi-IN = Hindi)
  const [voiceLang, setVoiceLang] = useState<"en-IN" | "hi-IN">("en-IN");
  // Bug 1 fix: track the text that was in the input box before the mic was pressed,
  // and the current interim draft, separately — so we never double-append.
  const voicePrefixRef = useRef<string>("");
  const [voiceInterimDraft, setVoiceInterimDraft] = useState<string>("");

  // Multilingual preference: 'en' | 'hi' | 'hinglish'
  const [advisorLang, setAdvisorLang] = useState<"en" | "hi" | "hinglish">("en");
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);

  // Sync advisorLang preference from localStorage post-mount
  useEffect(() => {
    try {
      const savedLang = localStorage.getItem("healysis_advisor_lang") as "en" | "hi" | "hinglish";
      if (savedLang && ["en", "hi", "hinglish"].includes(savedLang)) {
        setAdvisorLang(savedLang);
        setVoiceLang(savedLang === "hi" ? "hi-IN" : "en-IN");
      }
    } catch (_) {}
  }, []);

  const handleSelectLanguage = (lang: "en" | "hi" | "hinglish") => {
    setAdvisorLang(lang);
    setVoiceLang(lang === "hi" ? "hi-IN" : "en-IN");
    try {
      localStorage.setItem("healysis_advisor_lang", lang);
    } catch (_) {}
  };

  const handleSpeakMessage = (msgId: string, text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

    if (speakingMessageId === msgId) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
      return;
    }

    window.speechSynthesis.cancel();
    // Clean markdown/special characters for speech
    const cleanSpoken = text
      .replace(/[#*`_~]/g, "")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanSpoken);
    if (advisorLang === "hi" || /[\u0900-\u097F]/.test(cleanSpoken)) {
      utterance.lang = "hi-IN";
    } else {
      utterance.lang = "en-IN";
    }

    utterance.onend = () => setSpeakingMessageId(null);
    utterance.onerror = () => setSpeakingMessageId(null);

    setSpeakingMessageId(msgId);
    window.speechSynthesis.speak(utterance);
  };

  // Group conversations by time periods
  const groupConversations = (list: ConversationSummary[]) => {
    const today: ConversationSummary[] = [];
    const yesterday: ConversationSummary[] = [];
    const previous7Days: ConversationSummary[] = [];
    const older: ConversationSummary[] = [];

    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const oneDayMs = 24 * 60 * 60 * 1000;

    list.forEach((c) => {
      const d = new Date(c.updated_at).getTime();
      const diff = todayStart - d;

      if (diff <= 0) {
        today.push(c);
      } else if (diff <= oneDayMs) {
        yesterday.push(c);
      } else if (diff <= 7 * oneDayMs) {
        previous7Days.push(c);
      } else {
        older.push(c);
      }
    });

    return { today, yesterday, previous7Days, older };
  };

  // HYDRATION FIX: detect Web Speech API support only after mount
  useEffect(() => {
    setSpeechSupported(
      typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)
    );
  }, []);

  // 1. Fetch conversations when authenticated user changes or mounts
  useEffect(() => {
    if (!user?.firebase_uid) {
      setConversations([]);
      setActiveConversationId(null);
      setMessages([DEFAULT_INITIAL_MESSAGE]);
      setActiveUid(null);
      return;
    }

    if (user.firebase_uid !== activeUid) {
      setActiveUid(user.firebase_uid);
      loadConversations();
    }
  }, [user?.firebase_uid, activeUid]);

  const loadConversations = async (preferredId?: number) => {
    if (!user?.firebase_uid) return;
    setLoadingList(true);
    try {
      const list = await apiFetch<ConversationSummary[]>("/api/v1/advisor/conversations");
      setConversations(list || []);

      if (list && list.length > 0) {
        let targetId = preferredId;
        if (!targetId) {
          try {
            const saved = localStorage.getItem(`healysis_active_convo_${user.firebase_uid}`);
            if (saved) {
              const parsed = parseInt(saved, 10);
              if (list.some((c) => c.id === parsed)) {
                targetId = parsed;
              }
            }
          } catch (e) {
            // ignore localStorage read error
          }
        }

        if (!targetId || !list.some((c) => c.id === targetId)) {
          targetId = list[0].id;
        }

        selectConversation(targetId);
      } else {
        setActiveConversationId(null);
        setMessages([DEFAULT_INITIAL_MESSAGE]);
      }
    } catch (err) {
      console.error("Error loading conversations:", err);
      setConversations([]);
      setActiveConversationId(null);
      setMessages([DEFAULT_INITIAL_MESSAGE]);
    } finally {
      setLoadingList(false);
    }
  };

  const selectConversation = async (convoId: number) => {
    setActiveConversationId(convoId);
    if (user?.firebase_uid) {
      try {
        localStorage.setItem(`healysis_active_convo_${user.firebase_uid}`, convoId.toString());
      } catch (e) {
        // ignore storage error
      }
    }
    setLoadingMessages(true);
    try {
      const detail = await apiFetch<{
        id: number;
        title: string;
        created_at: string;
        updated_at: string;
        messages: Array<{
          id: number;
          sender: "user" | "advisor";
          text: string;
          meta_json?: any;
          created_at: string;
        }>;
      }>(`/api/v1/advisor/conversations/${convoId}`);

      if (detail && Array.isArray(detail.messages) && detail.messages.length > 0) {
        const mapped: ChatMessage[] = detail.messages.map((m) => ({
          id: m.id.toString(),
          sender: m.sender,
          text: m.text,
          answer: m.text,
          summary: m.meta_json?.summary,
          severity: m.meta_json?.severity,
          recommended_actions: m.meta_json?.recommended_actions,
          limitations: m.meta_json?.limitations,
          timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          pending_update: m.meta_json?.pending_update || undefined
        }));
        setMessages(mapped);
      } else {
        setMessages([DEFAULT_INITIAL_MESSAGE]);
      }
    } catch (err) {
      console.error("Error loading conversation detail:", err);
      setMessages([DEFAULT_INITIAL_MESSAGE]);
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleNewChat = async () => {
    try {
      const newConvo = await apiFetch<ConversationSummary>("/api/v1/advisor/conversations", {
        method: "POST",
        body: JSON.stringify({ title: "New Chat" })
      });
      setConversations((prev) => [newConvo, ...prev]);
      setActiveConversationId(newConvo.id);
      if (user?.firebase_uid) {
        try {
          localStorage.setItem(`healysis_active_convo_${user.firebase_uid}`, newConvo.id.toString());
        } catch (e) {}
      }
      setMessages([DEFAULT_INITIAL_MESSAGE]);
      setShowHistoryDrawer(false);
    } catch (err) {
      console.error("Error creating new chat:", err);
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, convoId: number) => {
    e.stopPropagation();
    try {
      await apiFetch(`/api/v1/advisor/conversations/${convoId}`, {
        method: "DELETE"
      });
      const remaining = conversations.filter((c) => c.id !== convoId);
      setConversations(remaining);
      if (activeConversationId === convoId) {
        if (remaining.length > 0) {
          selectConversation(remaining[0].id);
        } else {
          setActiveConversationId(null);
          setMessages([DEFAULT_INITIAL_MESSAGE]);
          if (user?.firebase_uid) {
            try {
              localStorage.removeItem(`healysis_active_convo_${user.firebase_uid}`);
            } catch (e) {}
          }
        }
      }
    } catch (err) {
      console.error("Error deleting conversation:", err);
    }
  };

  const sampleQuestions = [
    "Aaj ORS ka stock 180 hai.",
    "Paracetamol stock is 320 and daily demand is 35.",
    "Why is Jatni CHC at critical risk?",
    "Why transfer ORS to Jatni CHC?",
    "Which facilities require ORS rebalancing?",
    "List active alerts for West Bengal facilities"
  ];

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputMessage;
    if (!textToSend.trim()) return;

    let convoId = activeConversationId;

    // If no active conversation exists, auto-create one first
    if (!convoId) {
      try {
        const newConvo = await apiFetch<ConversationSummary>("/api/v1/advisor/conversations", {
          method: "POST",
          body: JSON.stringify({ title: "New Chat" })
        });
        convoId = newConvo.id;
        setActiveConversationId(convoId);
        setConversations((prev) => [newConvo, ...prev]);
        if (user?.firebase_uid) {
          try {
            localStorage.setItem(`healysis_active_convo_${user.firebase_uid}`, convoId.toString());
          } catch (e) {}
        }
      } catch (err) {
        console.error("Failed to auto-create conversation:", err);
      }
    }

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInputMessage("");
    setLoading(true);

    try {
      const endpoint = convoId
        ? `/api/v1/advisor/conversations/${convoId}/messages`
        : `/api/v1/advisor/chat`;

      const data = await apiFetch<any>(endpoint, {
        method: "POST",
        body: JSON.stringify({
          message: textToSend,
          facility_id: user?.facility_id || undefined,
          conversation_id: convoId || undefined,
          language: advisorLang
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
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        pending_update: data.pending_update || undefined
      };
      setMessages((prev) => [...prev, advisorMsg]);

      // Refresh conversations list to pick up updated title & ordering
      apiFetch<ConversationSummary[]>("/api/v1/advisor/conversations")
        .then((updatedList) => {
          if (updatedList) setConversations(updatedList);
        })
        .catch(() => {});

    } catch (err: any) {
      console.error("AI Advisor request error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "advisor",
          text: err.message || "Error connecting to AI Advisor service.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmUpdate = async (messageId: string, pending: PendingInventoryUpdate) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, confirming: true, confirm_error: undefined } : m))
    );

    try {
      const result = await apiFetch<UpdateConfirmationResult>("/api/v1/advisor/confirm-update", {
        method: "POST",
        body: JSON.stringify({
          facility_id: pending.facility_id,
          item_code: pending.item_code,
          quantity: pending.new_quantity,
          daily_demand: pending.new_daily_demand,
          confirmation_token: pending.confirmation_token
        })
      });

      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                confirming: false,
                update_confirmed: true,
                update_result: result
              }
            : m
        )
      );

      // Append grounded confirmation announcement from backend
      const followUpMsg: ChatMessage = {
        id: (Date.now() + 2).toString(),
        sender: "advisor",
        text: `✅ ${result.message}\n\n• Audit Event ID: \`${result.audit_event_id}\`\n• Days of Cover: ${result.days_of_cover} days\n• Risk Severity: ${result.severity}`,
        severity: result.severity,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      };
      setMessages((prev) => [...prev, followUpMsg]);

    } catch (err: any) {
      console.error("Confirm update error:", err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                confirming: false,
                confirm_error: err.message || "Failed to commit update. Please retry."
              }
            : m
        )
      );
    }
  };

  const handleCancelUpdate = (messageId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, update_cancelled: true } : m))
    );
  };

  // ============================================
  // Feature 2.2 — Voice Frontline Input Handlers
  // ============================================

  const isSpeechSupported = useCallback((): boolean => {
    return typeof window !== "undefined" &&
      ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);
  }, []);

  const handleVoiceStart = useCallback(() => {
    if (!isSpeechSupported()) {
      setVoiceState("error");
      setVoiceError("Voice input is not supported in this browser. Please use Chrome or Edge, or type your message instead.");
      return;
    }

    // Stop any existing session cleanly
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (_) {}
      recognitionRef.current = null;
    }

    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition: SpeechRecognitionInstance = new SpeechRecognitionCtor();
    recognitionRef.current = recognition;

    // Bug 1 fix: snapshot the current input value as the immutable prefix.
    // All interim and final results are appended to this prefix only,
    // so onresult can fire multiple times without ever double-appending.
    const currentInput = inputMessage;
    voicePrefixRef.current = currentInput;
    setVoiceInterimDraft("");

    // Bug 2 fix: use the user-selected language (en-IN or hi-IN).
    recognition.lang = voiceLang;
    // Bug 1 fix: enable interimResults so we can show a live preview in the
    // input box. Final results are committed once; interim results only update
    // the preview and are never permanently appended.
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onstart = () => {
      setVoiceState("recording");
      setVoiceError(null);
    };

    recognition.onresult = (event: SpeechRecognitionResultEvent) => {
      // Bug 1 fix: walk only from resultIndex to avoid re-reading earlier results.
      // Build separate interim and final accumulations from the NEW results only.
      let interimText = "";
      let finalText = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const segment = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalText += segment;
        } else {
          interimText += segment;
        }
      }

      const prefix = voicePrefixRef.current;
      const sep = prefix.trim() ? " " : "";

      if (finalText) {
        // Commit the final text exactly once: prefix + final.
        // Update the prefix ref so any subsequent result events build on this.
        const committed = prefix.trim() + sep + finalText.trim();
        voicePrefixRef.current = committed;
        setVoiceInterimDraft("");
        setInputMessage(committed);
        setVoiceState("idle");
        setVoiceError(null);
      } else if (interimText) {
        // Show interim preview in the input box without committing it.
        // This is read-only feedback — never permanently written.
        setVoiceInterimDraft(interimText);
        setInputMessage(prefix.trim() + sep + interimText.trim());
        setVoiceState("recording");
      }
    };

    recognition.onnomatch = () => {
      // Restore prefix if nothing matched
      setInputMessage(voicePrefixRef.current);
      setVoiceInterimDraft("");
      setVoiceState("error");
      setVoiceError("Speech could not be recognized. Please try again or type your message.");
    };

    recognition.onerror = (event: SpeechRecognitionErrEvent) => {
      recognitionRef.current = null;
      // Restore input to prefix (discard any interim draft)
      setInputMessage(voicePrefixRef.current);
      setVoiceInterimDraft("");
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setVoiceState("error");
        setVoiceError("Microphone access was denied. Please allow microphone permissions and try again.");
      } else if (event.error === "no-speech") {
        setVoiceState("error");
        setVoiceError("No speech detected. Please speak clearly and try again.");
      } else if (event.error === "network") {
        setVoiceState("error");
        setVoiceError("Network error during voice recognition. Please check your connection.");
      } else if (event.error === "audio-capture") {
        setVoiceState("error");
        setVoiceError("Microphone not available. Please check your audio device.");
      } else if (event.error === "aborted") {
        // User or code aborted — return to idle quietly
        setVoiceState("idle");
        setVoiceError(null);
      } else {
        setVoiceState("error");
        setVoiceError("Voice input could not be processed. You can type your message instead.");
      }
    };

    recognition.onend = () => {
      // If we end while still in recording state and no final result arrived,
      // commit whatever interim text we had (some browsers skip the final event).
      setVoiceState((prev) => {
        if (prev === "recording") {
          // Interim draft (if any) is already shown in inputMessage — keep it as committed.
          voicePrefixRef.current = inputMessage;
          setVoiceInterimDraft("");
          return "idle";
        }
        return prev;
      });
      recognitionRef.current = null;
    };

    try {
      recognition.start();
    } catch (e) {
      setVoiceState("error");
      setVoiceError("Could not start voice recognition. Please try again.");
    }
  }, [isSpeechSupported, voiceLang, inputMessage]);

  const handleVoiceStop = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
      // Bug 1 fix: go to transcribing while we wait for onresult's final event,
      // not directly to idle — prevents the input from jumping back to prefix.
      setVoiceState("transcribing");
    }
  }, []);

  const handleVoiceDismissError = useCallback(() => {
    setVoiceState("idle");
    setVoiceError(null);
  }, []);

  const grouped = groupConversations(conversations);
  const activeConvo = conversations.find((c) => c.id === activeConversationId);

  return (
    <AppShell>
      <div className="space-y-4 max-w-5xl mx-auto">
        
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
          <div>
            <h1 className="text-xl lg:text-2xl font-black text-[#0C2B4E] flex items-center gap-2">
              <IconSparkles className="text-[#1D546C]" size={24} />
              Healysis Gemini AI Advisor
            </h1>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Operational Healthcare Resource Decision Support & Frontline Field Input Assistant
            </p>
          </div>

          {/* Top-Right Action Controls */}
          <div className="flex items-center gap-2.5 shrink-0">
            {/* Chat History Drawer Trigger */}
            <button
              onClick={() => setShowHistoryDrawer(true)}
              className="bg-white hover:bg-slate-50 text-[#0C2B4E] border border-slate-200 text-xs font-bold py-2.5 px-3.5 rounded-xl transition flex items-center gap-1.5 shadow-2xs cursor-pointer"
              title="View Chat History"
            >
              <IconHistory size={16} className="text-[#1D546C]" />
              <span>Chat History</span>
              {conversations.length > 0 && (
                <span className="bg-slate-100 text-[#0C2B4E] text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-md ml-0.5">
                  {conversations.length}
                </span>
              )}
            </button>

            {/* Sole Primary + New Chat Action */}
            <button
              onClick={handleNewChat}
              className="bg-[#0C2B4E] hover:bg-[#1D546C] text-white text-xs font-bold py-2.5 px-4 rounded-xl transition flex items-center gap-1.5 shadow-xs cursor-pointer"
              title="Start a new conversation"
            >
              <IconPlus size={16} />
              <span>+ New Chat</span>
            </button>
          </div>
        </div>

        {/* Advisory Callout Notice */}
        <div className="bg-blue-50 border border-blue-200 p-3 rounded-xl flex items-start gap-3 text-blue-900">
          <IconInfoCircle size={18} className="text-blue-600 shrink-0 mt-0.5" />
          <div className="text-xs space-y-0.5">
            <span className="font-bold">Frontline Input & Decision Governance:</span>
            <p className="leading-relaxed text-[11px]">
              Facility Officers can submit natural-language stock telemetry in English or Hinglish. Database mutations require human confirmation, facility RBAC validation, and produce a tamper-evident SHA-256 audit entry. Historical messages do not authorize mutations.
            </p>
          </div>
        </div>

        {/* Spacious, Full-Width Main Conversation Container */}
        <div className="w-full bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col h-[calc(100vh-250px)] min-h-[580px] overflow-hidden justify-between">
          
          {/* Conversation Header */}
          <div className="px-5 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-slate-50/50">
            <div className="flex items-center gap-2 truncate">
              <IconMessage size={16} className="text-[#1D546C] shrink-0" />
              <h2 className="text-xs font-bold text-[#0C2B4E] truncate">
                {activeConvo?.title || "New Conversation"}
              </h2>
            </div>

            {/* Language Selector Controls */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="flex items-center bg-white border border-slate-200 rounded-xl p-0.5 shadow-2xs">
                <div className="flex items-center gap-1 px-2 py-1 text-slate-400">
                  <IconLanguage size={14} className="text-[#1D546C]" />
                  <span className="text-[10px] font-bold uppercase font-mono hidden sm:inline">Lang:</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleSelectLanguage("en")}
                  className={`text-[11px] font-bold px-2.5 py-1 rounded-lg transition cursor-pointer ${
                    advisorLang === "en"
                      ? "bg-[#0C2B4E] text-white shadow-2xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                  title="Query & reply in English"
                >
                  English
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectLanguage("hi")}
                  className={`text-[11px] font-bold px-2.5 py-1 rounded-lg transition cursor-pointer ${
                    advisorLang === "hi"
                      ? "bg-[#0C2B4E] text-white shadow-2xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                  title="Query & reply in Hindi (हिंदी)"
                >
                  हिंदी
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectLanguage("hinglish")}
                  className={`text-[11px] font-bold px-2.5 py-1 rounded-lg transition cursor-pointer ${
                    advisorLang === "hinglish"
                      ? "bg-[#0C2B4E] text-white shadow-2xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                  title="Query & reply in Hinglish (Hindi written in Roman script)"
                >
                  Hinglish
                </button>
              </div>

              {/* HYDRATION FIX: toLocaleTimeString output */}
              {activeConvo && speechSupported && (
                <span className="text-[10px] text-slate-400 font-mono hidden md:inline">
                  {new Date(activeConvo.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </div>
          </div>

          {/* Scrollable Message Stream */}
          <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-5">
            
            {/* Empty State / Conversation Starter */}
            {messages.length <= 1 && (
              <div className="max-w-xl mx-auto text-center py-8 space-y-4">
                <div className="inline-flex items-center justify-center p-3.5 rounded-2xl bg-blue-50 text-[#1D546C] border border-blue-100 mb-1">
                  <IconSparkles size={28} />
                </div>
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-[#0C2B4E]">Start a new conversation</h3>
                  <p className="text-xs text-slate-500 max-w-md mx-auto">
                    Ask Healysis about healthcare resource risk, inventory, forecasts, alerts, or redistribution. Frontline staff can also report stock counts directly.
                  </p>
                </div>
                <div className="pt-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 font-mono block mb-2.5">
                    Suggested Inquiries
                  </span>
                  <div className="flex flex-wrap justify-center gap-2">
                    {sampleQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendMessage(q)}
                        className="text-[11px] font-medium bg-slate-50 hover:bg-blue-50 text-[#0C2B4E] border border-slate-200 hover:border-blue-200 px-3.5 py-1.5 rounded-full transition shadow-2xs cursor-pointer text-left"
                      >
                        "{q}"
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {loadingMessages ? (
              <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                <IconLoader size={18} className="animate-spin text-[#1D546C]" />
                <span>Loading conversation messages...</span>
              </div>
            ) : (
              messages.map((m) => (
                <div
                  key={m.id}
                  className={`flex gap-3 ${m.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
                >
                  <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${
                    m.sender === "user" ? "bg-[#0C2B4E] text-white" : "bg-slate-100 text-[#1D546C] border border-slate-200"
                  }`}>
                    {m.sender === "user" ? <IconUser size={16} /> : <IconRobot size={16} />}
                  </div>

                  <div className={`space-y-3 max-w-2xl lg:max-w-3xl rounded-2xl p-4 text-xs ${
                    m.sender === "user" 
                      ? "bg-[#0C2B4E] text-white rounded-tr-none shadow-2xs" 
                      : "bg-slate-50 border border-slate-200 text-slate-800 rounded-tl-none"
                  }`}>
                    <p className="leading-relaxed whitespace-pre-wrap">{m.text}</p>

                    {/* Pending Update Confirmation Card */}
                    {m.sender === "advisor" && m.pending_update && (
                      <div className="mt-3 pt-3 border-t border-slate-200">
                        {!m.update_confirmed && !m.update_cancelled && (
                          <div className="bg-white rounded-xl border border-amber-300 shadow-xs p-4 space-y-3 text-slate-800">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5 text-amber-900 font-bold text-xs">
                                <IconAlertCircle size={16} className="text-amber-600" />
                                <span>Frontline Telemetry Update Preview</span>
                              </div>
                              <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-300 px-2 py-0.5 rounded-full">
                                Requires Confirmation
                              </span>
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-50 p-3 rounded-lg border border-slate-200">
                              <div>
                                <span className="text-slate-500 block text-[10px] uppercase font-mono">Facility</span>
                                <span className="font-bold text-[#0C2B4E] flex items-center gap-1">
                                  <IconBuildingHospital size={13} className="text-[#1D546C]" />
                                  {m.pending_update.facility_name}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block text-[10px] uppercase font-mono">Resource</span>
                                <span className="font-bold text-slate-900 flex items-center gap-1">
                                  <IconPackage size={13} className="text-[#1D546C]" />
                                  {m.pending_update.item_name}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block text-[10px] uppercase font-mono">Current Stock</span>
                                <span className="font-bold text-slate-700">{m.pending_update.current_quantity} {m.pending_update.unit}</span>
                              </div>
                              <div>
                                <span className="text-slate-500 block text-[10px] uppercase font-mono">Proposed Stock</span>
                                <span className="font-bold text-emerald-700">{m.pending_update.new_quantity} {m.pending_update.unit}</span>
                              </div>
                              {m.pending_update.new_daily_demand && (
                                <div className="col-span-2">
                                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Updated Daily Demand</span>
                                  <span className="font-bold text-[#1D546C]">{m.pending_update.new_daily_demand} {m.pending_update.unit}/day</span>
                                </div>
                              )}
                              <div className="col-span-2">
                                <span className="text-slate-400 block text-[9px] uppercase font-mono">Security Token</span>
                                <span className="font-mono text-[10px] text-slate-500 truncate block">{m.pending_update.confirmation_token}</span>
                              </div>
                            </div>

                            {m.confirm_error && (
                              <div className="text-xs text-red-600 bg-red-50 border border-red-200 p-2 rounded-lg">
                                {m.confirm_error}
                              </div>
                            )}

                            <div className="flex items-center gap-2 pt-1">
                              <button
                                onClick={() => handleConfirmUpdate(m.id, m.pending_update!)}
                                disabled={m.confirming}
                                className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-3.5 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition disabled:opacity-50 cursor-pointer shadow-2xs"
                              >
                                {m.confirming ? (
                                  <>
                                    <IconLoader size={14} className="animate-spin" />
                                    <span>Confirming...</span>
                                  </>
                                ) : (
                                  <>
                                    <IconCheck size={14} />
                                    <span>Confirm Update</span>
                                  </>
                                )}
                              </button>
                              <button
                                onClick={() => handleCancelUpdate(m.id)}
                                disabled={m.confirming}
                                className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 transition disabled:opacity-50 cursor-pointer"
                              >
                                <IconX size={14} />
                                <span>Cancel</span>
                              </button>
                            </div>
                          </div>
                        )}

                        {m.update_confirmed && (
                          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-center gap-2 text-emerald-800 text-xs">
                            <IconShieldCheck size={16} className="text-emerald-600 shrink-0" />
                            <span className="font-semibold">Update Applied & Signed to SHA-256 Audit Ledger.</span>
                          </div>
                        )}

                        {m.update_cancelled && (
                          <div className="bg-slate-100 border border-slate-200 rounded-xl p-3 flex items-center gap-2 text-slate-600 text-xs">
                            <IconX size={16} className="text-slate-400 shrink-0" />
                            <span>Update Discarded. No database modifications made.</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="flex items-center justify-between gap-2 pt-1 text-[10px]">
                      <span className={m.sender === "user" ? "text-slate-300" : "text-slate-400"}>
                        {m.timestamp}
                      </span>
                      {m.sender === "advisor" && (
                        <button
                          type="button"
                          onClick={() => handleSpeakMessage(m.id, m.answer || m.text)}
                          className="flex items-center gap-1 font-medium text-[#1D546C] hover:text-[#0C2B4E] bg-slate-100 hover:bg-slate-200 px-2 py-0.5 rounded-md transition cursor-pointer"
                          title={speakingMessageId === m.id ? "Stop voice readout" : "Read message aloud"}
                        >
                          {speakingMessageId === m.id ? (
                            <>
                              <IconVolumeOff size={13} className="text-rose-600" />
                              <span className="text-rose-600 font-bold">Stop</span>
                            </>
                          ) : (
                            <>
                              <IconVolume size={13} />
                              <span>Read Aloud</span>
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}

            {loading && (
              <div className="flex gap-3">
                <div className="h-8 w-8 rounded-lg bg-slate-100 text-[#1D546C] border border-slate-200 flex items-center justify-center shrink-0">
                  <IconRobot size={16} />
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-none p-4 text-xs text-slate-500 flex items-center gap-2">
                  <IconLoader size={16} className="animate-spin text-[#1D546C]" />
                  <span>Consulting grounded healthcare intelligence...</span>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Input Area */}
          <div className="p-3 lg:p-4 bg-white border-t border-slate-200">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex gap-2 max-w-4xl mx-auto items-start"
            >
              {/* ============================================
                  Feature 2.2 — Microphone Button
                  Uses Web Speech API (browser-native)
                  Voice → transcription → existing input field
                  → user reviews → presses Send → Feature 2.1
                  HYDRATION SAFE: speechSupported is false on SSR,
                  set to real value only in useEffect post-hydration.
                  ============================================ */}
              {speechSupported && (
                <div className="flex items-start gap-1 flex-shrink-0">
                  {/* Bug 2 fix: compact EN / हि language toggle — only shown when idle or error */}
                  {(voiceState === "idle" || voiceState === "error") && (
                    <button
                      type="button"
                      onClick={() => setVoiceLang((l) => l === "en-IN" ? "hi-IN" : "en-IN")}
                      disabled={loading}
                      title={voiceLang === "en-IN" ? "Voice language: English / Hinglish — click for Hindi" : "Voice language: Hindi — click for English / Hinglish"}
                      className="h-[38px] px-2 flex items-center justify-center rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-200 text-[10px] font-bold text-slate-600 transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer select-none"
                    >
                      {voiceLang === "en-IN" ? "EN" : "हि"}
                    </button>
                  )}

                  <div className="relative">
                    {voiceState === "idle" && (
                      <button
                        type="button"
                        onClick={handleVoiceStart}
                        disabled={loading}
                        title={`Tap to speak in ${voiceLang === "en-IN" ? "English / Hinglish" : "Hindi"}`}
                        className="h-[38px] w-[38px] flex items-center justify-center rounded-xl bg-slate-100 hover:bg-blue-50 text-slate-500 hover:text-[#1D546C] border border-slate-200 hover:border-blue-200 transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                      >
                        <IconMicrophone size={17} />
                      </button>
                    )}

                    {voiceState === "recording" && (
                      <button
                        type="button"
                        onClick={handleVoiceStop}
                        title="Stop recording"
                        className="h-[38px] w-[38px] flex items-center justify-center rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-600 border border-rose-300 animate-pulse transition cursor-pointer"
                      >
                        <IconPlayerStop size={17} />
                      </button>
                    )}

                    {voiceState === "transcribing" && (
                      <div
                        title="Transcribing..."
                        className="h-[38px] w-[38px] flex items-center justify-center rounded-xl bg-amber-50 text-amber-600 border border-amber-200"
                      >
                        <IconLoader size={17} className="animate-spin" />
                      </div>
                    )}

                    {voiceState === "error" && (
                      <button
                        type="button"
                        onClick={handleVoiceDismissError}
                        title={voiceError || "Voice input error. Click to dismiss."}
                        className="h-[38px] w-[38px] flex items-center justify-center rounded-xl bg-rose-100 text-rose-600 border border-rose-300 transition cursor-pointer hover:bg-rose-200"
                      >
                        <IconMicrophoneOff size={17} />
                      </button>
                    )}
                  </div>
                </div>
              )}

              <div className="flex-1 flex flex-col gap-1">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder={voiceState === "recording" ? "🔴 Listening... speak now" : "Ask Healysis anything, or report frontline stock (e.g., 'Aaj ORS ka stock 180 hai')..."}
                  disabled={loading}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1D546C]/30 focus:border-[#1D546C] transition"
                />
                {/* Inline voice state feedback — non-blocking, below the input */}
                {voiceState === "recording" && (
                  <p className="text-[10px] text-rose-600 font-mono px-1 flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                    {voiceLang === "en-IN" ? "Recording in English / Hinglish" : "Recording in Hindi"} — click ■ to stop.
                  </p>
                )}
                {voiceState === "transcribing" && (
                  <p className="text-[10px] text-amber-600 font-mono px-1">
                    Transcribing...
                  </p>
                )}
                {voiceState === "error" && voiceError && (
                  <p className="text-[10px] text-rose-600 font-mono px-1">
                    ⚠ {voiceError}
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={loading || !inputMessage.trim()}
                className="h-[38px] bg-[#0C2B4E] hover:bg-[#1D546C] text-white font-bold px-4 rounded-xl text-xs flex items-center gap-1.5 transition disabled:opacity-40 disabled:cursor-not-allowed shadow-xs cursor-pointer shrink-0 self-start"
              >
                <IconSend size={15} />
                <span>Send</span>
              </button>
            </form>
          </div>

        </div>

        {/* Slide-in Chat History Drawer Overlay */}
        {showHistoryDrawer && (
          <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
            {/* Dimmed backdrop */}
            <div 
              className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
              onClick={() => setShowHistoryDrawer(false)}
            />

            {/* Drawer panel */}
            <aside className="relative w-full max-w-md bg-white h-full shadow-2xl z-10 flex flex-col p-5 border-l border-slate-200 animate-in slide-in-from-right duration-200">
              
              {/* Drawer Header with Close Button */}
              <div className="flex items-center justify-between pb-4 mb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <IconHistory size={18} className="text-[#1D546C]" />
                  <h2 className="text-sm font-bold uppercase tracking-wider text-[#0C2B4E] font-mono">
                    Chat History
                  </h2>
                  <span className="text-[10px] font-bold text-slate-500 font-mono bg-slate-100 px-2 py-0.5 rounded-full">
                    {conversations.length}
                  </span>
                </div>

                <button
                  onClick={() => setShowHistoryDrawer(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                  title="Close History"
                >
                  <IconX size={18} />
                </button>
              </div>

              {/* Conversation List */}
              <div className="overflow-y-auto space-y-4 pr-1 flex-1">
                {loadingList ? (
                  <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                    <IconLoader size={16} className="animate-spin text-[#1D546C]" />
                    <span>Loading history...</span>
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="p-8 text-center text-slate-400 text-xs space-y-1">
                    <IconMessages size={28} className="mx-auto text-slate-300 mb-2" />
                    <p className="font-semibold text-slate-600">No previous conversations.</p>
                    <p className="text-[11px] text-slate-400">Conversations you start will be saved here automatically.</p>
                  </div>
                ) : (
                  <>
                    {/* Today */}
                    {grouped.today.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 block font-mono">
                          Today
                        </span>
                        {grouped.today.map((c) => (
                          <div
                            key={c.id}
                            onClick={() => {
                              selectConversation(c.id);
                              setShowHistoryDrawer(false);
                            }}
                            className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition ${
                              activeConversationId === c.id
                                ? "bg-blue-50 text-[#0C2B4E] font-bold border border-blue-200 shadow-2xs"
                                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate pr-1 flex-1">
                              <IconMessage size={14} className={activeConversationId === c.id ? "text-[#1D546C]" : "text-slate-400"} />
                              <span className="truncate">{c.title}</span>
                            </div>
                            <button
                              onClick={(e) => handleDeleteConversation(e, c.id)}
                              className="text-slate-300 hover:text-rose-600 hover:bg-rose-50 p-1 rounded transition shrink-0"
                              title="Delete conversation"
                            >
                              <IconTrash size={13} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Yesterday */}
                    {grouped.yesterday.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 block font-mono">
                          Yesterday
                        </span>
                        {grouped.yesterday.map((c) => (
                          <div
                            key={c.id}
                            onClick={() => {
                              selectConversation(c.id);
                              setShowHistoryDrawer(false);
                            }}
                            className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition ${
                              activeConversationId === c.id
                                ? "bg-blue-50 text-[#0C2B4E] font-bold border border-blue-200 shadow-2xs"
                                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate pr-1 flex-1">
                              <IconMessage size={14} className={activeConversationId === c.id ? "text-[#1D546C]" : "text-slate-400"} />
                              <span className="truncate">{c.title}</span>
                            </div>
                            <button
                              onClick={(e) => handleDeleteConversation(e, c.id)}
                              className="text-slate-300 hover:text-rose-600 hover:bg-rose-50 p-1 rounded transition shrink-0"
                              title="Delete conversation"
                            >
                              <IconTrash size={13} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Previous 7 Days */}
                    {grouped.previous7Days.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 block font-mono">
                          Previous 7 Days
                        </span>
                        {grouped.previous7Days.map((c) => (
                          <div
                            key={c.id}
                            onClick={() => {
                              selectConversation(c.id);
                              setShowHistoryDrawer(false);
                            }}
                            className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition ${
                              activeConversationId === c.id
                                ? "bg-blue-50 text-[#0C2B4E] font-bold border border-blue-200 shadow-2xs"
                                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate pr-1 flex-1">
                              <IconMessage size={14} className={activeConversationId === c.id ? "text-[#1D546C]" : "text-slate-400"} />
                              <span className="truncate">{c.title}</span>
                            </div>
                            <button
                              onClick={(e) => handleDeleteConversation(e, c.id)}
                              className="text-slate-300 hover:text-rose-600 hover:bg-rose-50 p-1 rounded transition shrink-0"
                              title="Delete conversation"
                            >
                              <IconTrash size={13} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Older */}
                    {grouped.older.length > 0 && (
                      <div className="space-y-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 block font-mono">
                          Older
                        </span>
                        {grouped.older.map((c) => (
                          <div
                            key={c.id}
                            onClick={() => {
                              selectConversation(c.id);
                              setShowHistoryDrawer(false);
                            }}
                            className={`group flex items-center justify-between p-2.5 rounded-xl text-xs cursor-pointer transition ${
                              activeConversationId === c.id
                                ? "bg-blue-50 text-[#0C2B4E] font-bold border border-blue-200 shadow-2xs"
                                : "text-slate-600 hover:bg-slate-50 hover:text-slate-900 border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 truncate pr-1 flex-1">
                              <IconMessage size={14} className={activeConversationId === c.id ? "text-[#1D546C]" : "text-slate-400"} />
                              <span className="truncate">{c.title}</span>
                            </div>
                            <button
                              onClick={(e) => handleDeleteConversation(e, c.id)}
                              className="text-slate-300 hover:text-rose-600 hover:bg-rose-50 p-1 rounded transition shrink-0"
                              title="Delete conversation"
                            >
                              <IconTrash size={13} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>

            </aside>
          </div>
        )}

      </div>
    </AppShell>
  );
}
