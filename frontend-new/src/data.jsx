// data.jsx — API client, data mappers, WebSocket hook
// ----------------------------------------------------------------------

import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8000").replace(/\/$/, "");
const WS_BASE = API_BASE.replace(/^http/, "ws");

// ── Per-browser client identity ────────────────────────────────────
// Stored in localStorage so the same browser always gets the same ID.
// This scopes session limits and session lists per browser, not globally.
function getClientId() {
  const KEY = "yojaka_client_id";
  let id = localStorage.getItem(KEY);
  if (!id) {
    id = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
    localStorage.setItem(KEY, id);
  }
  return id;
}
const CLIENT_ID = getClientId();

// ── API Client ─────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      "X-Client-ID": CLIENT_ID,
      ...(options.headers || {}),
    },
    ...options,
  });
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

const api = {
  getSessions:           ()           => apiFetch("/api/sessions"),
  createSession:         (mode, settings) => apiFetch("/api/sessions", {
    method: "POST", body: JSON.stringify({ mode, settings }),
  }),
  deleteSession:         (id)         => apiFetch(`/api/sessions/${id}`, { method: "DELETE" }),
  renameSession:         (id, name)   => apiFetch(`/api/sessions/${id}`, {
    method: "PATCH", body: JSON.stringify({ name }),
  }),
  getModels:             ()           => apiFetch("/api/models"),
  getMessages:           (sid)        => apiFetch(`/api/sessions/${sid}/messages`),
  getDebates:            (sid)        => apiFetch(`/api/sessions/${sid}/debates`),
  getSettings:           (sid)        => apiFetch(`/api/sessions/${sid}/settings`),
  updateSettings:        (sid, upd)   => apiFetch(`/api/sessions/${sid}/settings`, {
    method: "PATCH", body: JSON.stringify(upd),
  }),
  getAnalytics:          (sid)        => apiFetch(`/api/sessions/${sid}/analytics`),
  getIntelligence:       (sid)        => apiFetch(`/api/sessions/${sid}/intelligence`),
  getPracticeState:      (sid)        => apiFetch(`/api/sessions/${sid}/practice-state`),
  getExperiences:        ()           => apiFetch("/api/ai-debater-experiences"),
  getUserProfile:        ()           => apiFetch("/api/user-debate-profile/overview"),
  getCouncilSettings:    ()           => apiFetch("/api/council-settings"),
  updateCouncilSettings: (upd)        => apiFetch("/api/council-settings", {
    method: "PATCH", body: JSON.stringify(upd),
  }),
  resetAgentExperience:  (confirmation) => apiFetch("/api/council-settings/reset-agent-experience", {
    method: "POST", body: JSON.stringify({ confirmation }),
  }),
  resetUserProfile:      (confirmation) => apiFetch("/api/user-debate-profile/reset", {
    method: "POST", body: JSON.stringify({ confirmation }),
  }),
};

// ── Data Mappers ───────────────────────────────────────────────────

function mapSession(s) {
  const isAI = s.mode !== "ai_vs_human";
  const idx  = String(s.default_index || 1).padStart(2, "0");
  return {
    id:     s.id,
    code:   `${isAI ? "DBT" : "PRC"}_CH.${idx}`,
    name:   s.name,
    mode:   s.mode || "ai_vs_ai",
    status: "IDLE",
    phase:  "",
  };
}

function mapBackendMessage(msg, index) {
  if (!msg) return null;
  const role   = msg.role || "";
  const isPro  = role.startsWith("pro_");
  const isCon  = role.startsWith("con_") || role === "practice_debater";
  const isJudge= role === "judge" || role === "judge_assistant";
  const isUser = role === "user";
  if (isUser) return null;                              // operator messages not shown in transcript

  const side      = isPro ? "PRO" : isCon ? "CON" : isJudge ? "NEU" : "SYS";
  const roleLabel = role.replace(/^(pro|con)_/, "").replace(/_/g, " ").toUpperCase() || "UNKNOWN";
  const ts  = msg.created_at ? new Date(msg.created_at) : new Date();
  const pad = n => String(n).padStart(2, "0");
  const time = `${pad(ts.getUTCHours())}:${pad(ts.getUTCMinutes())}:${pad(ts.getUTCSeconds())}`;
  return {
    id:         msg.id,
    seq:        typeof msg.sequence === "number" ? msg.sequence : index + 1,
    side,
    role:       roleLabel,
    speaker:    msg.speaker || role,
    model:      msg.model || "",
    time,
    body:       msg.content || "",
    citations:  [],
    phase:      msg.phase_key   || "",
    phaseTitle: msg.phase_title || "",
    phaseKind:  msg.phase_kind  || "",
    phaseIndex: typeof msg.phase_index === "number" ? msg.phase_index : null,
  };
}

function mapAssignment(a) {
  const role     = a.role || "";
  const isPro    = role.startsWith("pro_");
  const isCon    = role.startsWith("con_");
  const team     = isPro ? "PRO" : isCon ? "CON" : "NEU";
  const roleLabel= role.replace(/^(pro|con)_/, "").replace(/_/g, " ").toUpperCase();
  return {
    id:       role,
    team,
    role:     roleLabel,
    speaker:  a.speaker || role,
    model:    a.model   || "",
    provider: a.provider|| "",
  };
}

function deriveAssignments(messages) {
  const seen = new Set();
  const result = [];
  for (const msg of messages) {
    const role = msg.role || "";
    if (["user", "assistant"].includes(role)) continue;
    const key = `${role}:${msg.speaker}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(mapAssignment({ role, speaker: msg.speaker, model: msg.model }));
  }
  return result;
}

// ── useCompileStream ───────────────────────────────────────────────

function useCompileStream(fullText, opts = {}) {
  const { speed = 14, blockDuration = 80, autoStart = true, key = "" } = opts;
  const [stage, setStage] = useState("idle");
  const [shown, setShown] = useState("");
  useEffect(() => {
    if (!autoStart) return;
    setStage("blocks");
    setShown("");
    const t1 = setTimeout(() => setStage("typing"), blockDuration);
    return () => clearTimeout(t1);
  }, [fullText, autoStart, key]);
  useEffect(() => {
    if (stage !== "typing") return;
    if (shown.length >= fullText.length) { setStage("done"); return; }
    const id = setTimeout(() => setShown(fullText.slice(0, shown.length + 1)), speed);
    return () => clearTimeout(id);
  }, [stage, shown, fullText, speed]);
  return { stage, shown };
}

// ── useDebateSocket ────────────────────────────────────────────────

function useDebateSocket(sessionId) {
  const [wsStatus,          setWsStatus]          = useState("disconnected");
  const [messages,          setMessages]          = useState([]);
  const [streamingMsg,      setStreamingMsg]      = useState(null);
  const [currentDebate,     setCurrentDebate]     = useState(null);
  const [assignments,       setAssignments]       = useState([]);
  const [debateStatus,      setDebateStatus]      = useState("idle");
  const [analysisSnapshots, setAnalysisSnapshots] = useState([]);
  const [wsError,           setWsError]           = useState(null);
  const wsRef             = useRef(null);
  const sessionIdRef      = useRef(sessionId);
  const pendingSendRef    = useRef(null);

  useEffect(() => { sessionIdRef.current = sessionId; }, [sessionId]);

  const handleEvent = useCallback((payload) => {
    switch (payload.type) {
      case "debate_started": {
        setCurrentDebate(payload.debate);
        setDebateStatus("running");
        setMessages([]);
        setStreamingMsg(null);
        setAnalysisSnapshots([]);
        setWsError(null);
        if (Array.isArray(payload.assignments)) {
          setAssignments(payload.assignments.map(mapAssignment));
        }
        break;
      }
      case "interaction_started": {
        setDebateStatus("running");
        setWsError(null);
        if (payload.debate) setCurrentDebate(payload.debate);
        break;
      }
      case "team_preparation_started":
      case "team_preparation_completed":
        break;
      case "message_started": {
        const mapped = mapBackendMessage(payload.message, 0);
        if (mapped) setStreamingMsg({ ...mapped, id: payload.stream_id, body: "" });
        break;
      }
      case "message_delta": {
        setStreamingMsg(s => {
          if (!s || s.id !== payload.stream_id) return s;
          return { ...s, body: s.body + (payload.delta || "") };
        });
        break;
      }
      case "message_replaced": {
        setStreamingMsg(s => {
          if (!s || s.id !== payload.stream_id) return s;
          return { ...s, body: payload.content || "" };
        });
        break;
      }
      case "message_completed": {
        const mapped = mapBackendMessage(payload.message, 0);
        setStreamingMsg(null);
        if (!mapped) break;
        setMessages(prev => {
          const idx = prev.findIndex(m => m.id === payload.stream_id || m.id === mapped.id);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = mapped;
            return next;
          }
          return [...prev, mapped];
        });
        break;
      }
      case "debate_completed": {
        setDebateStatus("complete");
        setStreamingMsg(null);
        setCurrentDebate(d => d ? { ...d, status: "completed", judge_summary: payload.judge_summary } : d);
        break;
      }
      case "practice_completed": {
        setDebateStatus("complete");
        setStreamingMsg(null);
        break;
      }
      case "interaction_completed":
      case "practice_state_updated": {
        setDebateStatus(prev => prev === "running" ? "idle" : prev);
        setStreamingMsg(null);
        break;
      }
      case "analysis_updated": {
        if (payload.analysis) setAnalysisSnapshots(prev => [...prev, payload.analysis]);
        break;
      }
      case "error": {
        setWsError(payload.message || "Unknown error");
        setDebateStatus("error");
        setStreamingMsg(null);
        break;
      }
    }
  }, []);

  const openWs = useCallback(() => {
    const sid = sessionIdRef.current;
    if (!sid) return null;
    if (wsRef.current && [WebSocket.CONNECTING, WebSocket.OPEN].includes(wsRef.current.readyState)) {
      return wsRef.current;
    }
    setWsStatus("connecting");
    setWsError(null);
    const ws = new WebSocket(`${WS_BASE}/ws/debates/${sid}?client_id=${CLIENT_ID}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus("connected");
      if (pendingSendRef.current) {
        ws.send(JSON.stringify(pendingSendRef.current));
        pendingSendRef.current = null;
      }
    };
    ws.onerror = () => {
      setWsStatus("error");
      setWsError("WebSocket failed. Is the backend running at " + API_BASE + "?");
    };
    ws.onclose = () => setWsStatus("disconnected");
    ws.onmessage = (e) => {
      try { handleEvent(JSON.parse(e.data)); } catch {}
    };
    return ws;
  }, [handleEvent]);

  const connect = useCallback(() => { openWs(); }, [openWs]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setWsStatus("disconnected");
  }, []);

  const send = useCallback((payload) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    } else {
      pendingSendRef.current = payload;
      openWs();
    }
  }, [openWs]);

  const dispatch = useCallback((topic, model, mode, practiceSide) => {
    setDebateStatus("running");
    setWsError(null);
    setMessages([]);
    setStreamingMsg(null);
    setAnalysisSnapshots([]);
    const type    = mode === "ai_vs_human" ? "start_interaction" : "start_debate";
    const payload = { type, topic: topic.trim(), model: model || "" };
    if (practiceSide) payload.practice_side = practiceSide;
    send(payload);
  }, [send]);

  // Reset + disconnect when session changes
  useEffect(() => {
    setMessages([]);
    setStreamingMsg(null);
    setCurrentDebate(null);
    setAssignments([]);
    setDebateStatus("idle");
    setAnalysisSnapshots([]);
    setWsError(null);
    disconnect();
  }, [sessionId]);

  return {
    wsStatus,
    messages, setMessages,
    streamingMsg,
    currentDebate, setCurrentDebate,
    assignments, setAssignments,
    debateStatus, setDebateStatus,
    analysisSnapshots,
    wsError, setWsError,
    connect, disconnect, send, dispatch,
  };
}

export { api, mapSession, mapBackendMessage, mapAssignment, deriveAssignments, useCompileStream, useDebateSocket };
