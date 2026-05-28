// app.jsx — root app shell with real backend integration
// ----------------------------------------------------------------------

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

  // WebSocket + debate state
  const {
    wsStatus, messages, setMessages,
    streamingMsg, currentDebate, setCurrentDebate,
    assignments, setAssignments,
    debateStatus, setDebateStatus,
    analysisSnapshots,
    wsError, setWsError,
    connect, disconnect, dispatch,
  } = useDebateSocket(selectedId);

  // ── Bootstrap ──────────────────────────────────────────────────

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

  // ── Per-session side-effects ────────────────────────────────────

  useEffect(() => {
    if (!selectedId) {
      setSessionSettings(null);
      setAnalyticsData(null);
      setIntelligence(null);
      return;
    }
    api.getSettings(selectedId).then(setSessionSettings).catch(console.error);

    // Load historical messages for the latest debate
    Promise.all([
      api.getMessages(selectedId),
      api.getDebates(selectedId),
    ]).then(([msgs, debates]) => {
      if (!msgs?.length) return;
      const latestDebate = debates?.[0];
      const debateMsgs   = latestDebate
        ? msgs.filter(m => m.debate_id === latestDebate.id)
        : msgs;
      const mapped = debateMsgs
        .map((m, i) => mapBackendMessage(m, i))
        .filter(Boolean);
      setMessages(mapped);
      if (latestDebate) setCurrentDebate(latestDebate);
      const derived = deriveAssignments(debateMsgs);
      if (derived.length) setAssignments(derived);
    }).catch(console.error);
  }, [selectedId]);

  // Analytics: load/reload when entering stats panel or debate completes
  useEffect(() => {
    if (panel !== "stats" || !selectedId) return;
    api.getAnalytics(selectedId).then(setAnalyticsData).catch(console.error);
  }, [panel, selectedId]);

  useEffect(() => {
    if (debateStatus === "complete" && panel === "stats" && selectedId) {
      api.getAnalytics(selectedId).then(setAnalyticsData).catch(console.error);
    }
  }, [debateStatus]);

  // Intelligence: load when entering team rooms
  useEffect(() => {
    if (!["proRoom", "conRoom"].includes(panel) || !selectedId) return;
    api.getIntelligence(selectedId).then(setIntelligence).catch(console.error);
  }, [panel, selectedId]);

  // Memory / Profile: lazy load
  useEffect(() => {
    if (view !== "memory") return;
    api.getExperiences().then(setExperiences).catch(console.error);
  }, [view]);

  useEffect(() => {
    if (view !== "profile") return;
    api.getUserProfile().then(setUserProfile).catch(console.error);
  }, [view]);

  // Council settings: load for settings view or settings panel
  useEffect(() => {
    if (view !== "settings" && panel !== "settings") return;
    api.getCouncilSettings().then(setCouncilSettings).catch(console.error);
  }, [view, panel]);

  // WS: connect when a session is active
  useEffect(() => {
    if (view === "session" && selectedId) connect();
  }, [view, selectedId]);

  // ── Session/nav handlers ────────────────────────────────────────

  const selectSession = (id) => {
    setSelectedId(id);
    setView("session");
    setPanel("chat");
    setAnalyticsData(null);
    setIntelligence(null);
    setWsError(null);
    setDebateStatus("idle");
  };

  const setViewWrapper = (v) => {
    setView(v);
    if (v !== "session") setSelectedId(null);
  };

  const newSession = async (mode) => {
    try {
      const raw     = await api.createSession(mode || "ai_vs_ai");
      const session = mapSession(raw);
      setSessions(prev => [session, ...prev]);
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
          <CRTSwitch k="settings" mountLines={["config_layer", "auth_check", "render_pipeline"]}>
            <SettingsPanel
              settings={null}
              councilSettings={councilSettings}
              models={models}
              onSave={() => {}}
              onUpdateCouncil={async (updates) => {
                const updated = await api.updateCouncilSettings(updates);
                setCouncilSettings(updated);
              }}
            />
          </CRTSwitch>

        ) : (
          <DebateRoom
            session={activeSession}
            panel={panel}
            setPanel={setPanel}
            activeSpeaker={activeSpeaker}
            transcript={allMessages}
            streamingMsgId={streamingMsg?.id}
            assignments={assignments}
            debateStatus={debateStatus}
            wsStatus={wsStatus}
            wsError={wsError}
            currentDebate={currentDebate}
            analyticsData={analyticsData}
            analysisSnapshots={analysisSnapshots}
            intelligence={intelligence}
            sessionSettings={sessionSettings}
            models={models}
            onDispatch={handleDispatch}
            onSaveSettings={handleSaveSettings}
          />
        )}
      </main>
    </div>
  );
}

// ── DebateRoom ──────────────────────────────────────────────────────

function DebateRoom({
  session, panel, setPanel,
  activeSpeaker, transcript, streamingMsgId,
  assignments, debateStatus, wsStatus, wsError,
  currentDebate, analyticsData, analysisSnapshots, intelligence,
  sessionSettings, models,
  onDispatch, onSaveSettings,
}) {
  const topic = currentDebate?.topic || "";

  return (
    <div className="col flex-1" style={{ minHeight: 0 }}>
      {/* Sub-nav */}
      <div className="row" style={{
        borderBottom: "0.5px solid var(--hair)",
        background: "var(--void)",
        padding: "0 0 0 24px",
        height: 44, alignItems: "stretch", gap: 0,
        position: "relative", flexShrink: 0,
      }}>
        <div className="row items-center gap-3" style={{ marginRight: 16, minWidth: 0, flex: "0 1 auto" }}>
          <span className="sm-tag" style={{ flexShrink: 0 }}>{session?.code || "NEW"}</span>
          <span className="bone truncate" style={{ fontSize: 11.5, letterSpacing: "0.06em", minWidth: 0, maxWidth: 260 }}>
            {session?.name || "New Session"}
          </span>
          <span className="mono-mini hot" style={{ flexShrink: 0 }}>
            ● {debateStatus === "running" ? "LIVE" : debateStatus.toUpperCase()}
          </span>
          {wsStatus === "connected" && (
            <span className="mono-mini" style={{ color: "var(--bone-4)", flexShrink: 0, letterSpacing: "0.10em" }}>
              WS:OK
            </span>
          )}
        </div>
        <div className="row" style={{ alignSelf: "stretch", marginLeft: "auto", height: "100%", flexShrink: 0 }}>
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

      <div className="col flex-1" style={{ minHeight: 0, position: "relative" }}>
        <CRTSwitch
          k={panel}
          mountLines={[`${panel}_layer`, "telemetry_link", "render_pipeline"]}
        >
          {panel === "chat" ? (
            <ArenaPanel
              assignments={assignments}
              transcript={transcript}
              streamingMsgId={streamingMsgId}
              activeSpeaker={activeSpeaker}
              status={debateStatus === "running" ? "streaming" : debateStatus}
              topic={topic}
              error={wsError}
              models={models}
              sessionSettings={sessionSettings}
              onDispatch={onDispatch}
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
        flexShrink: 0,
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

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
