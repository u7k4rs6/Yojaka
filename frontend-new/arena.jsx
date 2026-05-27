// arena.jsx — debate stream: real WS streaming, live transcript, model selector
// ----------------------------------------------------------------------

function ArenaPanel({ assignments, transcript, streamingMsgId, activeSpeaker, status, onTopic, topic, error, models, sessionSettings, onDispatch }) {
  const [tearKey, setTearKey] = useState(0);
  const [lastSide, setLastSide] = useState(null);
  const scrollRef = useRef(null);

  // Channel-tear on speaker switch
  useEffect(() => {
    const latest = transcript[transcript.length - 1];
    if (!latest) return;
    if (latest.side !== lastSide) {
      setTearKey(k => k + 1);
      setLastSide(latest.side);
    }
  }, [transcript.length]);

  // Autoscroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  });

  const pro = assignments.filter(a => a.team === "PRO");
  const con = assignments.filter(a => a.team === "CON");

  return (
    <div className="col full" style={{ position: "relative" }}>
      <ArenaHeader topic={topic} status={status} />

      {/* Roster strip */}
      <div className="row items-stretch" style={{ borderBottom: "0.5px solid var(--hair)" }}>
        <SideRoster team="PRO" members={pro} active={activeSpeaker.team === "PRO"} />
        <div className="flex-1" />
        <CenterReadout activeSpeaker={activeSpeaker} />
        <div className="flex-1" />
        <SideRoster team="CON" members={con} active={activeSpeaker.team === "CON"} alignRight />
      </div>

      {/* Error banner */}
      {error && (
        <div style={{
          padding: "8px 24px",
          background: "rgba(255,78,0,0.08)",
          borderBottom: "0.5px solid var(--orange-dim)",
          fontSize: 11, letterSpacing: "0.06em", color: "var(--orange)",
        }}>
          ▲ {error}
        </div>
      )}

      {/* Stream */}
      <div ref={scrollRef} className="flex-1" style={{ overflowY: "auto", padding: "20px 24px 16px" }}>
        {transcript.length === 0 && status !== "running" ? (
          <EmptyArena />
        ) : (
          <div key={tearKey} className="sm-tear">
            <div className="col gap-0" style={{ maxWidth: 920, margin: "0 auto" }}>
              {groupByRound(transcript).map((group, gi) => (
                <div key={gi} className="col gap-0">
                  <RoundDivider label={group.label} index={gi} />
                  {group.messages.map((msg) => (
                    <MessageBlock
                      key={msg.id}
                      message={msg}
                      streaming={msg.id === streamingMsgId}
                    />
                  ))}
                </div>
              ))}
              {status === "running" && !streamingMsgId && (
                <PendingCompose nextSpeaker="NEXT DEBATER" />
              )}
            </div>
          </div>
        )}
      </div>

      {/* Composer */}
      <Composer
        topic={topic}
        status={status}
        models={models}
        sessionSettings={sessionSettings}
        onDispatch={onDispatch}
      />
    </div>
  );
}

// Group consecutive messages by "round" — a round boundary happens when
// the phase kind resets back to constructive/opening, or when phaseIndex
// drops. Falls back to grouping every ~4 messages if no phase metadata.
function groupByRound(transcript) {
  if (!transcript.length) return [];

  const OPENING_KINDS = new Set(["constructive", "opening", "evidence"]);
  const groups = [];
  let current = null;
  let roundNum = 0;
  let lastPhaseIndex = -1;

  for (const msg of transcript) {
    const kind  = msg.phaseKind || "";
    const idx   = msg.phaseIndex;
    const isNeu = msg.side === "NEU" || msg.side === "SYS";

    // Judge / assistant messages get their own group
    if (isNeu) {
      if (current) groups.push(current);
      roundNum++;
      const roleLabel = (msg.role || "").toLowerCase();
      const label = roleLabel.includes("judge assistant") ? "JUDGE ASSISTANT AUDIT"
        : roleLabel.includes("trainer") ? "DEBATE TRAINER"
        : "VERDICT";
      current = { label, messages: [msg] };
      lastPhaseIndex = idx ?? lastPhaseIndex;
      continue;
    }

    // New round when: phase index resets/drops, or opening kind seen after first group
    const phaseReset = idx !== null && idx < lastPhaseIndex;
    const openingAfterStart = OPENING_KINDS.has(kind) && groups.length > 0 && current && current.messages.length > 0;
    const needsNewGroup = !current || phaseReset || openingAfterStart;

    if (needsNewGroup) {
      if (current) groups.push(current);
      roundNum++;
      const kindLabel = kind === "constructive" ? "OPENING STATEMENTS"
        : kind === "evidence" ? "EVIDENCE"
        : kind === "cross_exam" ? "CROSS-EXAMINATION"
        : kind === "rebuttal" ? "REBUTTAL"
        : kind === "closing" ? "CLOSING STATEMENTS"
        : kind === "discussion" || kind === "answer_rebuttal" ? `ROUND ${roundNum}`
        : `ROUND ${roundNum}`;
      current = { label: kindLabel, messages: [msg] };
    } else {
      current.messages.push(msg);
    }
    lastPhaseIndex = idx ?? lastPhaseIndex;
  }
  if (current) groups.push(current);
  return groups;
}

function RoundDivider({ label, index }) {
  return (
    <div className="row items-center gap-3" style={{
      padding: "20px 0 10px",
      marginTop: index === 0 ? 0 : 12,
    }}>
      <span style={{ flex: "0 0 auto", fontSize: 9, letterSpacing: "0.22em", color: "var(--bone-4)", fontWeight: 600 }}>
        {label}
      </span>
      <span style={{ flex: 1, height: "0.5px", background: "var(--hair)" }} />
    </div>
  );
}

function EmptyArena() {
  return (
    <div className="col items-center justify-center full" style={{ gap: 12, opacity: 0.5 }}>
      <span className="mono-mini bone-3" style={{ letterSpacing: "0.16em" }}>
        NO ACTIVE DEBATE · DISPATCH A TOPIC TO BEGIN
      </span>
      <span className="bone-4 mono-mini">Enter a resolution below and press DISPATCH</span>
    </div>
  );
}

function ArenaHeader({ topic, status }) {
  const isLive     = status === "streaming" || status === "running";
  const isComplete = status === "complete";
  return (
    <div className="col" style={{ borderBottom: "0.5px solid var(--hair)", padding: "18px 24px 16px", background: "var(--void-2)" }}>
      <div className="row items-start justify-between gap-6">
        <div className="col flex-1" style={{ minWidth: 0 }}>
          <div className="row items-center gap-3" style={{ marginBottom: 10 }}>
            <span className={`sm-tag ${isLive ? "sm-tag--hot" : ""}`}>
              {isLive ? "CH.01 · LIVE" : isComplete ? "CH.01 · COMPLETE" : "CH.01 · IDLE"}
            </span>
            {isLive && <span className="bone-3 mono-mini">DEBATE IN PROGRESS</span>}
            {isComplete && <span className="bone-3 mono-mini">VERDICT ISSUED</span>}
          </div>
          <h1 style={{
            fontSize: 20, fontWeight: 500, letterSpacing: "-0.005em",
            margin: 0, color: "var(--bone)", lineHeight: 1.3,
          }}>
            {topic || <span className="bone-4" style={{ fontStyle: "normal", fontWeight: 400 }}>No active topic — enter one below</span>}
          </h1>
        </div>
        <div className="col items-end gap-3" style={{ flexShrink: 0 }}>
          <div className="row items-center gap-3">
            <LiveClock since={isLive ? Date.now() - 1000 : null} />
            <Sig pct={98} />
          </div>
          <div className="row gap-2">
            <Btn variant="ghost">ARCHIVE</Btn>
            <Btn variant="hot">TERMINATE</Btn>
          </div>
        </div>
      </div>
    </div>
  );
}

function SideRoster({ team, members, active, alignRight }) {
  const isPro = team === "PRO";
  return (
    <div className={`col ${active ? "sm-speaker-pulse" : ""}`} style={{
      width: 220, flexShrink: 0,
      padding: "12px 16px",
      borderRight: !alignRight ? "0.5px solid var(--hair)" : "none",
      borderLeft:  alignRight  ? "0.5px solid var(--hair)" : "none",
      background: active
        ? isPro ? "rgba(232, 230, 223, 0.04)" : "rgba(255, 78, 0, 0.05)"
        : isPro ? "transparent" : "rgba(255, 78, 0, 0.02)",
      position: "relative",
      alignItems: alignRight ? "flex-end" : "flex-start",
    }}>
      {active ? <span className={`sm-live-strip ${alignRight ? "left" : "right"}`} /> : null}
      <div className="row items-baseline gap-3" style={{ marginBottom: 10, flexDirection: alignRight ? "row-reverse" : "row" }}>
        <span className={isPro ? "" : "hot"} style={{ fontSize: 20, letterSpacing: "0.28em", fontWeight: 600 }}>
          {team}
        </span>
        {active
          ? <span className="hot mono-mini" style={{ animation: "cursor-blink 1.1s step-end infinite", fontWeight: 600 }}>● ON AIR</span>
          : <span className="bone-3 mono-mini">standby</span>
        }
      </div>
      <div className="col gap-2" style={{ width: "100%", alignItems: alignRight ? "flex-end" : "flex-start" }}>
        {members.length === 0 ? (
          <span className="mono-mini bone-4">—</span>
        ) : members.map(m => (
          <div key={m.id} className="col" style={{
            fontSize: 10, letterSpacing: "0.04em",
            alignItems: alignRight ? "flex-end" : "flex-start", width: "100%",
          }}>
            <div className="row items-center gap-2" style={{ flexDirection: alignRight ? "row-reverse" : "row" }}>
              <span style={{
                width: 5, height: 5,
                background: isPro ? "var(--bone)" : "var(--orange)",
                boxShadow: !isPro ? "0 0 4px var(--orange-dim)" : "none",
                flexShrink: 0,
              }} />
              <span className="bone" style={{ fontSize: 11, letterSpacing: "0.02em" }}>{m.speaker}</span>
            </div>
            <span className="bone-3" style={{
              fontSize: 9, letterSpacing: "0.10em",
              paddingLeft: alignRight ? 0 : 13, paddingRight: alignRight ? 13 : 0,
            }}>
              {m.role.replace(/_/g, " ").toLowerCase()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CenterReadout({ activeSpeaker }) {
  return (
    <div className="col items-center justify-center" style={{ padding: "10px 16px", width: 220, flexShrink: 0, position: "relative" }}>
      <span className={activeSpeaker.team === "PRO" ? "bone" : "hot"}
        style={{ fontSize: 16, letterSpacing: "0.12em", fontWeight: 500 }}>
        {activeSpeaker.speaker}
      </span>
      <span className="mono-mini bone-3" style={{ marginTop: 3 }}>
        {(activeSpeaker.role || "").replace(/_/g, " ").toLowerCase()}
      </span>
      <Waveform active />
    </div>
  );
}

function Waveform({ active }) {
  const [bars, setBars] = useState(() => Array.from({ length: 24 }, () => 0.3 + Math.random() * 0.7));
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setBars(b => b.map(() => 0.2 + Math.random() * 0.8)), 110);
    return () => clearInterval(id);
  }, [active]);
  return (
    <div className="row items-end gap-1" style={{ height: 16, marginTop: 6 }}>
      {bars.map((v, i) => (
        <i key={i} style={{
          display: "block", width: 2, height: `${v * 100}%`,
          background: i > 16 ? "var(--orange)" : "var(--bone-2)",
          transition: "height 100ms steps(2)",
        }} />
      ))}
    </div>
  );
}

function MessageBlock({ message, streaming }) {
  const isPro = message.side === "PRO";
  const [hoverCite, setHoverCite] = useState(null);

  const body = message.body || "";

  // Track if this component was ever live-streaming.
  // If so, skip compile animation — the token stream already revealed the text.
  const everLiveRef = useRef(streaming);
  if (streaming) everLiveRef.current = true;
  const skipAnim = everLiveRef.current;

  // Compile animation only for historical messages (never streaming).
  // Pass "" when skipAnim so fullText never changes and the hook stays idle.
  const { stage, shown } = useCompileStream(skipAnim ? "" : body, {
    speed: 8, blockDuration: 50, key: message.id,
    autoStart: !skipAnim && body.length > 0 && body.length < 600,
  });

  // Streaming → raw token accumulation displayed directly (no animation)
  // Historical short msg → compile blocks then typing
  // Everything else → full body immediately
  const showBlocks  = !skipAnim && stage === "blocks" && body.length > 0;
  const displayText = skipAnim        ? body
    : stage === "typing"              ? shown
    : body;
  const showCursor  = streaming || (!skipAnim && (stage === "blocks" || stage === "typing"));

  const isFinal = !streaming;

  return (
    <article className={`relative ${isPro ? "sm-side-pro" : "sm-side-con"}`} style={{
      padding: "14px 18px",
      background: isPro ? "var(--void-2)" : "linear-gradient(90deg, rgba(255,78,0,0.05), var(--void-2) 30%)",
      marginLeft: isPro ? 0 : 60,
      marginRight: isPro ? 60 : 0,
      borderTop: "0.5px solid var(--hair)",
      borderBottom: "0.5px solid var(--hair)",
    }}>
      <header className="row items-center justify-between gap-3" style={{ marginBottom: 10 }}>
        <div className="row items-center gap-2">
          {/* Team pill */}
          <span style={{
            fontSize: 9, letterSpacing: "0.22em", fontWeight: 700,
            padding: "2px 6px",
            color: isPro ? "var(--bone)" : "var(--orange)",
            border: `0.5px solid ${isPro ? "var(--hair-hot)" : "var(--orange-dim)"}`,
            background: isPro ? "rgba(232,230,223,0.06)" : "rgba(255,78,0,0.08)",
          }}>
            {message.side}
          </span>
          <span className="bone" style={{ fontSize: 12, letterSpacing: "0.04em", fontWeight: 500 }}>{message.speaker}</span>
          <span className={`mono-mini ${isPro ? "bone-3" : ""}`} style={{ fontSize: 9, letterSpacing: "0.14em", color: isPro ? "var(--bone-3)" : "var(--orange-dim)" }}>
            {message.role}
          </span>
        </div>
        <div className="row items-center gap-3">
          <span className="mono-mini bone-3">{message.time}</span>
          {streaming && (
            <span className="sm-tag sm-tag--hot" style={{ animation: "cursor-blink 1.1s step-end infinite" }}>
              LIVE
            </span>
          )}
        </div>
      </header>

      <div style={{
        fontSize: 13.5, lineHeight: 1.65, color: "var(--bone)",
        letterSpacing: "0.002em", whiteSpace: "pre-wrap",
      }}>
        {showBlocks ? (
          <CompileBlocks length={Math.min(120, body.length || 40)} />
        ) : (
          <React.Fragment>
            {displayText}
            {showCursor ? <span className={`sm-cursor ${isPro ? "" : "sm-cursor--hot"}`} /> : null}
          </React.Fragment>
        )}
      </div>

      {message.citations?.length > 0 && isFinal ? (
        <div className="row gap-2" style={{ marginTop: 12, flexWrap: "wrap", position: "relative" }}>
          {message.citations.map(c => (
            <Citation
              key={c.id}
              cite={c}
              active={hoverCite === c.id}
              onEnter={() => setHoverCite(c.id)}
              onLeave={() => setHoverCite(null)}
              parentSide={message.side}
            />
          ))}
          <span className="mono-mini bone-3" style={{ marginLeft: "auto", alignSelf: "center" }}>
            {Math.round((message.body || "").length / 4)} tok
          </span>
        </div>
      ) : isFinal && message.body ? (
        <div className="row" style={{ marginTop: 10 }}>
          <span className="mono-mini bone-3" style={{ marginLeft: "auto" }}>
            {Math.round(message.body.length / 4)} tok
          </span>
        </div>
      ) : null}
    </article>
  );
}

function CompileBlocks({ length }) {
  return (
    <span>
      {Array.from({ length }).map((_, i) => (
        <span key={i} className="sm-compile-block" style={{ animationDelay: `${i % 8 * 60}ms` }} />
      ))}
    </span>
  );
}

function Citation({ cite, active, onEnter, onLeave, parentSide }) {
  return (
    <span
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      style={{
        position: "relative",
        fontSize: 10, letterSpacing: "0.12em",
        padding: "2px 8px",
        color: parentSide === "PRO" ? "var(--bone)" : "var(--orange)",
        border: `0.5px solid ${parentSide === "PRO" ? "var(--hair-hot)" : "var(--orange-dim)"}`,
        background: "var(--void-3)",
        cursor: "help",
      }}
    >
      [{cite.id?.toUpperCase() || "REF"}] {(cite.label || "").slice(0, 28)}{(cite.label || "").length > 28 ? "…" : ""}
      {active && (
        <div style={{
          position: "absolute", top: "calc(100% + 14px)", left: 0,
          width: 280, zIndex: 30, padding: "10px 12px",
          background: "var(--void)", border: "0.5px solid var(--orange-dim)",
          clipPath: "var(--clip-panel-sm)", color: "var(--bone)",
          fontSize: 11, letterSpacing: "0.04em", lineHeight: 1.5,
          boxShadow: "0 8px 24px rgba(0,0,0,0.6)", pointerEvents: "none",
        }}>
          <div className="mono-mini hot" style={{ marginBottom: 4 }}>{cite.id?.toUpperCase()}</div>
          <div style={{ marginBottom: 4 }}>{cite.label}</div>
          {cite.url && <div className="bone-3 mono-mini">{cite.url}</div>}
        </div>
      )}
    </span>
  );
}

function PendingCompose({ nextSpeaker }) {
  return (
    <div style={{
      padding: "10px 14px",
      border: "0.5px dashed var(--hair-2)",
      background: "transparent",
      fontSize: 11, letterSpacing: "0.14em",
      color: "var(--bone-3)", textTransform: "uppercase",
    }}>
      Awaiting turn · {nextSpeaker.replace(/_/g, " ")} · INFERENCE QUEUED
    </div>
  );
}

// ── Composer ────────────────────────────────────────────────────────

function Composer({ topic, status, models, sessionSettings, onDispatch }) {
  const defaultTopic = topic || "Frontier AI labs should release open weights with no licensing restrictions.";
  const [val, setVal]     = useState(defaultTopic);
  const [model, setModel] = useState("");

  // Sync model with first available model
  useEffect(() => {
    if (!model && models?.length) {
      const preferred = sessionSettings?.overall_model;
      const found     = preferred && models.find(m => m.name === preferred);
      setModel(found ? found.name : models[0].name);
    }
  }, [models, model, sessionSettings]);

  // Sync val when topic changes from outside (new debate loaded from history)
  useEffect(() => {
    if (topic && topic !== val) setVal(topic);
  }, [topic]);

  const isRunning  = status === "running" || status === "streaming";
  const tokenEst   = Math.ceil(val.length / 4);
  const tokenPct   = Math.min(1, tokenEst / 1400);
  const costEst    = (tokenEst * 0.00003).toFixed(4);

  const handleDispatch = () => {
    if (!val.trim() || isRunning) return;
    onDispatch?.(val.trim(), model);
  };

  return (
    <div style={{
      borderTop: "0.5px solid var(--hair)",
      background: "linear-gradient(180deg, var(--void-2), var(--void))",
      position: "relative",
    }}>
      {/* Telemetry strip */}
      <div className="row items-center" style={{
        padding: "8px 24px", borderBottom: "0.5px solid var(--hair)",
        gap: 22, fontSize: 10, letterSpacing: "0.10em",
        color: "var(--bone-3)", textTransform: "uppercase",
      }}>
        <ComposerStat label="MDL" value={model ? model.split("/").pop() : "—"} bright />
        <ComposerStat label="TOK" value={`${tokenEst} / 1400`} />
        <ComposerStat label="EST" value={`$${costEst}`} />
        <ComposerStat label="PCT" value={`${Math.round(tokenPct * 100)}%`} hot={tokenPct > 0.85} />
        <span style={{ flex: 1 }} />
        <span className="row items-center gap-2">
          <span style={{ color: "var(--bone-4)", letterSpacing: "0.14em" }}>OPERATOR</span>
          <span style={{
            width: 5, height: 5,
            background: isRunning ? "var(--bone-3)" : "var(--orange)",
            boxShadow: !isRunning ? "0 0 6px var(--orange)" : "none",
          }} />
          <span className={isRunning ? "bone-3" : "hot"} style={{ letterSpacing: "0.14em" }}>
            {isRunning ? "BUSY" : "READY"}
          </span>
        </span>
      </div>

      {/* Token meter */}
      <div style={{ height: 2, background: "var(--void-3)", position: "relative" }}>
        <i style={{
          display: "block", height: "100%",
          width: `${tokenPct * 100}%`,
          background: tokenPct > 0.85 ? "var(--orange)" : "var(--bone-2)",
          transition: "width 200ms steps(8), background 200ms",
        }} />
      </div>

      {/* Command line */}
      <div className="row gap-3 items-stretch" style={{ padding: "14px 24px 16px" }}>
        {/* Model selector */}
        <div className="col" style={{ width: 200, flexShrink: 0, gap: 6 }}>
          <span className="bone-3 mono-mini">MODEL OVERRIDE</span>
          <select
            className="sm-select"
            value={model}
            onChange={e => setModel(e.target.value)}
            disabled={isRunning}
          >
            {models?.length ? (
              models.map(m => (
                <option key={m.name} value={m.name}>
                  {m.provider_label ? `${m.provider_label} / ${m.name.split("/").pop()}` : m.name}
                </option>
              ))
            ) : (
              <option value="">Loading models...</option>
            )}
          </select>
          <span style={{ color: "var(--bone-3)", fontSize: 10, letterSpacing: "0.02em", lineHeight: 1.45, marginTop: 4 }}>
            Router assigns roles across teams.
          </span>
        </div>

        {/* Input + dispatch */}
        <div className="col flex-1" style={{ minWidth: 0, gap: 6 }}>
          <div className="row items-center justify-between">
            <span className="bone-3 mono-mini">OPERATOR INPUT — TOPIC / MESSAGE</span>
            <span className="row items-center gap-2 mono-mini" style={{ color: "var(--bone-3)" }}>
              <span>{val.length} CH</span>
              <span style={{ color: "var(--bone-4)" }}>·</span>
              <span>{tokenEst} TOK</span>
              <span style={{ color: "var(--bone-4)" }}>·</span>
              <span className={tokenPct > 0.85 ? "hot" : ""}>{Math.round(tokenPct * 100)}%</span>
            </span>
          </div>
          <div className="row gap-2" style={{ alignItems: "stretch" }}>
            <div className="row flex-1" style={{
              background: "var(--void)", border: "0.5px solid var(--hair-2)",
              alignItems: "flex-start", padding: "10px 12px",
              gap: 8, position: "relative", minHeight: 76,
            }}>
              <span className="hot mono-mini" style={{ paddingTop: 3, letterSpacing: "0.10em", flexShrink: 0, fontWeight: 600 }}>
                OP&gt;
              </span>
              <textarea
                className="flex-1"
                rows={3}
                value={val}
                onChange={e => setVal(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                    e.preventDefault();
                    handleDispatch();
                  }
                }}
                placeholder="Enter debate resolution or your argument…"
                disabled={isRunning}
                style={{
                  background: "transparent", border: 0, outline: 0,
                  color: isRunning ? "var(--bone-3)" : "var(--bone)",
                  fontFamily: "inherit", fontSize: 13, lineHeight: 1.55,
                  resize: "none", padding: 0,
                }}
              />
              <span className="sm-cursor sm-cursor--hot" style={{ alignSelf: "flex-start", marginTop: 5 }} />
            </div>
            <div className="col gap-2" style={{ width: 130, flexShrink: 0 }}>
              <Btn
                variant="hot"
                onClick={handleDispatch}
                disabled={isRunning || !val.trim() || !model}
                style={{ justifyContent: "center", flex: 1 }}
              >
                {isRunning ? "RUNNING…" : "DISPATCH"}
              </Btn>
              <Btn variant="ghost" style={{ justifyContent: "center" }}>
                DRAFT
              </Btn>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ComposerStat({ label, value, hot, bright }) {
  return (
    <span className="row items-baseline gap-2">
      <span style={{ color: "var(--bone-4)", letterSpacing: "0.14em" }}>{label}</span>
      <span style={{
        color: hot ? "var(--orange)" : bright ? "var(--bone)" : "var(--bone-2)",
        letterSpacing: "0.04em", fontSize: 11,
      }}>{value}</span>
    </span>
  );
}

Object.assign(window, { ArenaPanel });
