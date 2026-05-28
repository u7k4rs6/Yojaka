// app.jsx — root app shell with real backend integration
// ----------------------------------------------------------------------

import React, { useState, useEffect } from 'react';
import { Globe, CRTSwitch, StatusTicker } from './hud.jsx';
import { api, useDebateSocket, mapBackendMessage, mapSession, deriveAssignments } from './data.jsx';
import { Sidebar } from './sidebar.jsx';
import { GlobalWorkspace } from './workspace.jsx';
import { ArenaPanel } from './arena.jsx';
import { AnalyticsPanel } from './analytics.jsx';
import { TeamRoomPanel, SettingsPanel } from './rooms.jsx';

const PANELS = [
  { id: "chat",     label: "ARENA",     code: "ARN" },
  { id: "stats",    label: "ANALYTICS", code: "ANL" },
  { id: "proRoom",  label: "PRO ROOM",  code: "PRO" },
  { id: "conRoom",  label: "CON ROOM",  code: "CON" },
  { id: "settings", label: "SETTINGS",  code: "CFG" },
];

function App() {
  const [view,             setView]             = useState("welcome");
  const [selectedId,       setSelectedId]       = useState(null);
  const [panel,            setPanel]            = useState("chat");

  // session list
  const [sessions,         setSessions]         = useState([]);
  const [sessionsLoading,  setSessionsLoading]  = useState(true);

  // global model list
  const [models,           setModels]           = useState([]);
  const [providers,        setProviders]        = useState([]);

  // lazy-loaded global views
  const [experiences,      setExperiences]      = useState(null);
  const [userProfile,      setUserProfile]      = useState(null);

  // per-session data
  const [sessionSettings,  setSessionSettings]  = useState(null);
  const [councilSettings,  setCouncilSettings]  = useState(null);
  const [analyticsData,    setAnalyticsData]    = useState(null);
  const [intelligence,     setIntelligence]     = useState(null);

  // load session list + global models once
  useEffect(() => {
    api.getSessions()
      .then(data => setSessions((data || []).map(mapSession)))
      .catch(console.error)
      .finally(() => setSessionsLoading(false));

    api.getModels()
      .then(data => {
        setModels(data?.models || []);
        setProviders(data?.providers || []);
      })
      .catch(console.error);
  }, []);

  // per-session refresh
  const [messages,        setMessages]         = useState([]);
  const [debateStatus,    setDebateStatus]      = useState("idle");

  // WS hook — reconnects when selectedId changes
  const {
    wsStatus,
    messages:     wsMsgs,
    streamingMsg,
    currentDebate,
    assignments,
    debateStatus: wsDebateStatus,
    analysisSnapshots,
    wsError,
    connect,
    disconnect,
    dispatch,
  } = useDebateSocket(selectedId);

  // Mirror WS state into local state
  useEffect(() => { setMessages(wsMsgs); },          [wsMsgs]);
  useEffect(() => { setDebateStatus(wsDebateStatus); }, [wsDebateStatus]);

  // Load per-session data when selection changes
  useEffect(() => {
    if (!selectedId) { setSessionSettings(null); setMessages([]); return; }
    Promise.all([
      api.getMessages(selectedId).catch(() => []),
      api.getDebates(selectedId).catch(() => []),
    ]).then(([msgs, debates]) => {
      const latestDebate = debates?.[0];
      const mapped = (msgs || []).map((m, i) => mapBackendMessage(m, i)).filter(Boolean);
      setMessages(mapped);
      if (latestDebate?.status === "completed") setDebateStatus("complete");
    });
    api.getSettings(selectedId).then(setSessionSettings).catch(console.error);
  }, [selectedId]);

  // load analytics
  useEffect(() => {
    if (panel !== "stats" || !selectedId) return;
    api.getAnalytics(selectedId).then(setAnalyticsData).catch(console.error);
  }, [panel, selectedId]);

  // load intelligence
  useEffect(() => {
    if (!["proRoom", "conRoom"].includes(panel) || !selectedId) return;
    api.getIntelligence(selectedId).then(setIntelligence).catch(console.error);
  }, [panel, selectedId]);

  // load global views lazily
  useEffect(() => {
    if (view === "memory")  api.getExperiences().then(setExperiences).catch(console.error);
    if (view === "profile") api.getUserProfile().then(setUserProfile).catch(console.error);
  }, [view]);

  useEffect(() => {
    if (view === "settings") api.getCouncilSettings().then(setCouncilSettings).catch(console.error);
  }, [view]);

  useEffect(() => {
    if (view === "session" && selectedId) connect();
  }, [view, selectedId]);

  // reconnect if session is selected and WS disconnects during a running debate
  useEffect(() => {
    if (!selectedId) return;
    if (debateStatus === "running" && wsStatus === "disconnected") connect();
  }, [view, selectedId]);

  // ── Actions ──────────────────────────────────────────────────────

  const selectSession = (id) => {
    setSelectedId(id);
    setView("session");
    setPanel("chat");
    connect();
  };

  const setViewWrapper = (v) => {
    setSelectedId(null);
    setView(v);
  };

  const onSaveSettings = async (updates) => {
    if (!selectedId) return;
    const updated = await api.updateSettings(selectedId, updates);
    setSessionSettings(updated);
  };

  const newSession = async (mode) => {
    try {
      const session = await api.createSession(mode);
      setSessions(prev => [mapSession(session), ...prev]);
      selectSession(session.id);
    } catch (e) {
      console.error("Failed to create session:", e);
    }
  };

  const handleSaveSettings = async (updates) => {
    if (!selectedId) return;
    try {
      const updated = await api.updateSettings(selectedId, updates);
      setSessionSettings(updated);
    } catch (e) {
      console.error("Failed to save settings:", e);
    }
  };

  const handleDispatch = (topic, model) => {
    const session = sessions.find(s => s.id === selectedId);
    dispatch(topic, model, session?.mode || "ai_vs_ai");
  };

  // ── Derived state ───────────────────────────────────────────────

  const allMessages = streamingMsg
    ? [...messages, streamingMsg]
    : messages;

  const lastMsg      = allMessages[allMessages.length - 1];
  const activeSpeaker= lastMsg
    ? { team: lastMsg.side, role: lastMsg.role, speaker: lastMsg.speaker }
    : { team: "PRO", role: "LEAD ADVOCATE", speaker: "—" };

  const activeSession = sessions.find(s => s.id === selectedId);

  const tickerItems = [
    activeSession ? `${activeSession.code} · ${debateStatus.toUpperCase()} · SIG 98%` : "YOJAKA · TERMINAL OPS",
    models.length  ? `MODELS: ${models.length} AVAILABLE`                              : "MODELS: LOADING...",
    `SESSIONS: ${sessions.length} TOTAL`,
    providers.length ? `PROVIDERS: ${providers.length} ONLINE` : null,
    wsStatus === "connected" ? "WS: CONNECTED" : wsStatus === "error" ? "WS: ERROR" : null,
    "DEBATE INTELLIGENCE TERMINAL · v1.0",
  ].filter(Boolean);

  return (
    <div className="row" style={{ height: "100vh", width: "100vw", position: "relative", overflow: "hidden" }}>
      <div aria-hidden="true" className="sm-grid-noise" />
      <div aria-hidden="true" className="sm-scanline" />
      <div aria-hidden="true" className="sm-vignette" />
      <Globe />

      <Sidebar
        sessions={sessions}
        selectedId={selectedId}
        view={view}
        onSelect={selectSession}
        onView={setViewWrapper}
        onNewSession={newSession}
      />

      <main className="col flex-1" style={{ position: "relative", zIndex: 5, minWidth: 0 }}>
        <div style={{ borderBottom: "0.5px solid var(--hair)", background: "var(--void-2)" }}>
          <StatusTicker items={tickerItems} />
        </div>

        {view === "memory" || view === "profile" || view === "welcome" ? (
          <CRTSwitch
            k={view}
            mountLines={[
              view === "memory"  ? "memory_layer"  :
              view === "profile" ? "profile_layer" : "dashboard",
              "telemetry_link", "render_pipeline",
            ]}
          >
            <GlobalWorkspace
              view={view}
              onNewSession={newSession}
              sessions={sessions}
              models={models}
              providers={providers}
              experiences={experiences}
              userProfile={userProfile}
            />
          </CRTSwitch>
        ) : view === "settings" ? (
          <SettingsPanel
            settings={null}
            councilSettings={councilSettings}
            models={models}
            onSave={null}
            onUpdateCouncil={async (upd) => {
              await api.updateCouncilSettings(upd);
              setCouncilSettings(upd);
            }}
          />
        ) : view === "session" && selectedId ? (
          <div className="col flex-1" style={{ minHeight: 0 }}>
            {/* Session tab bar */}
            <div className="row items-stretch" style={{
              borderBottom: "0.5px solid var(--hair)",
              background: "var(--void-2)",
              height: 40, flexShrink: 0,
            }}>
              <div className="row items-center gap-3" style={{ marginRight: 16, minWidth: 0, flex: "0 1 auto" }}>
                <span className="sm-tag" style={{ flexShrink: 0 }}>{activeSession?.code || "NEW"}</span>
                <span className="bone truncate" style={{ fontSize: 12 }}>{activeSession?.name || "New Session"}</span>
                <span style={{ width: 8, height: 8, background: debateStatus === "running" ? "var(--orange)" : "var(--bone-3)", flexShrink: 0 }} />
                <span className="mono-mini bone-3" style={{ fontSize: 10, flexShrink: 0 }}>
                  {debateStatus === "running" ? "RUNNING" : debateStatus === "complete" ? "COMPLETE" : debateStatus === "error" ? "ERROR" : "IDLE"}
                </span>
                {wsStatus === "connected" && <span className="mono-mini bone-3" style={{ flexShrink: 0 }}>WS:OK</span>}
              </div>

              <div className="row items-stretch flex-1" style={{ minWidth: 0, overflowX: "auto" }}>
                {PANELS.map(p => (
                  <PanelTab
                    key={p.id}
                    active={panel === p.id}
                    onClick={() => setPanel(p.id)}
                    label={p.label}
                    code={p.code}
                  />
                ))}
              </div>
            </div>

            {/* Panel content */}
            <CRTSwitch k={panel} mountLines={["data_link", "render_pipeline"]}>
              {panel === "chat" ? (
                <ArenaPanel
                  assignments={assignments.length ? assignments : deriveAssignments(allMessages)}
                  transcript={allMessages}
                  streamingMsgId={streamingMsg?.id}
                  activeSpeaker={activeSpeaker}
                  status={debateStatus}
                  topic={currentDebate?.topic || ""}
                  error={wsError}
                  models={models}
                  sessionSettings={sessionSettings}
                  onDispatch={handleDispatch}
                />
              ) : panel === "stats" ? (
                <AnalyticsPanel
                  analyticsData={analyticsData}
                  analysisSnapshots={analysisSnapshots}
                />
              ) : panel === "proRoom" ? (
                <TeamRoomPanel team="PRO" intelligence={intelligence} assignments={assignments} />
              ) : panel === "conRoom" ? (
                <TeamRoomPanel team="CON" intelligence={intelligence} assignments={assignments} />
              ) : (
                <SettingsPanel
                  settings={sessionSettings}
                  councilSettings={null}
                  models={models}
                  onSave={onSaveSettings}
                  onUpdateCouncil={() => {}}
                />
              )}
            </CRTSwitch>
          </div>
        ) : null}
      </main>
    </div>
  );
}

// ── PanelTab ────────────────────────────────────────────────────────

function PanelTab({ active, onClick, label, code }) {
  return (
    <button
      onClick={onClick}
      className="sm-side-item"
      style={{
        position: "relative",
        padding: "0 14px",
        height: "100%",
        whiteSpace: "nowrap",
        background: active ? "var(--void-3)" : "transparent",
        color: active ? "var(--orange)" : "var(--bone-2)",
        borderRight: "0.5px solid var(--hair)",
        borderLeft:  "0.5px solid var(--hair)",
        marginLeft: -0.5,
        fontSize: 11, letterSpacing: "0.16em", fontWeight: 600,
        clipPath: "none",
      }}
    >
      {active ? (
        <span style={{
          position: "absolute", top: 0, left: 0, right: 0, height: 1.5,
          background: "var(--orange)", boxShadow: "0 0 8px var(--orange)",
        }} />
      ) : null}
      <span className="br-l">[</span>
      <span className="mono-mini" style={{ color: active ? "var(--orange)" : "var(--bone-3)", marginRight: 8 }}>
        {code}
      </span>
      <span style={{ whiteSpace: "nowrap" }}>{label}</span>
      <span className="br-r">]</span>
    </button>
  );
}

export default App;
