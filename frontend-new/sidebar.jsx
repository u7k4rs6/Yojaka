// sidebar.jsx — left nav, sessions, intelligence hub
// ----------------------------------------------------------------------

function Sidebar({ sessions, selectedId, view, onSelect, onView, onNewSession }) {
  const ai      = sessions.filter(s => s.mode === "ai_vs_ai");
  const human   = sessions.filter(s => s.mode === "ai_vs_human");

  return (
    <aside className="col" style={{
      width: 260,
      background: "var(--void-2)",
      borderRight: "0.5px solid var(--hair)",
      position: "relative",
      zIndex: 10
    }}>
      {/* ── BRAND ROW ─────────────────────────── */}
      <div style={{ padding: "16px 14px 12px", borderBottom: "0.5px solid var(--hair)" }}>
        <div className="row items-center gap-2">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M2 2 L20 2 L17 6 L17 20 L13 20 L13 9 L9 9 L9 20 L5 20 L5 6 Z" stroke="var(--bone)" strokeWidth="0.8" fill="rgba(255,78,0,0.06)" />
            <circle cx="11" cy="6" r="1.4" fill="var(--orange)" />
          </svg>
          <div className="col">
            <span className="bone" style={{ fontSize: 13, letterSpacing: "0.22em", fontWeight: 600 }}>
              <Glitch text="YOJAKA" period={45000} />
            </span>
            <span className="mono-mini bone-3">terminal ops · v0.7.3</span>
          </div>
        </div>
      </div>

      {/* ── DASHBOARD / MEMORY / PROFILE ──────── */}
      <div style={{ padding: "8px 0", borderBottom: "0.5px solid var(--hair)" }}>
        <SideRow
          active={view === "welcome" && !selectedId}
          onClick={() => onView("welcome")}
          icon="◊"
          label="Dashboard"
          meta="HOME"
        />
        <SideRow
          active={view === "memory"}
          onClick={() => onView("memory")}
          icon="◈"
          label="Agent Memory"
          meta="1247"
        />
        <SideRow
          active={view === "profile"}
          onClick={() => onView("profile")}
          icon="⏚"
          label="Training Profile"
          meta="14 DBT"
        />
      </div>

      {/* ── SESSIONS ──────────────────────────── */}
      <div className="flex-1" style={{ overflowY: "auto", padding: "8px 0" }}>
        <SectionLabel
          text="AI ⨯ AI · COUNCIL LAB"
          right={(
            <button className="hot" style={{ fontSize: 10, letterSpacing: "0.16em" }} onClick={() => onNewSession("ai_vs_ai")}>
              [ + NEW ]
            </button>
          )}
        />
        <div>
          {ai.map(s => (
            <SessionRow key={s.id} session={s} active={selectedId === s.id && view === "session"} onClick={() => onSelect(s.id)} />
          ))}
        </div>

        <SectionLabel
          text="AI ⨯ HUMAN · TRAINING"
          right={(
            <button className="hot" style={{ fontSize: 10, letterSpacing: "0.16em" }} onClick={() => onNewSession("ai_vs_human")}>
              [ + NEW ]
            </button>
          )}
        />
        <div>
          {human.map(s => (
            <SessionRow key={s.id} session={s} active={selectedId === s.id && view === "session"} onClick={() => onSelect(s.id)} />
          ))}
        </div>
      </div>

      {/* ── SYSTEM FOOTER ─────────────────────── */}
      <div style={{ padding: "10px 0", borderTop: "0.5px solid var(--hair)" }}>
        <SideRow
          active={view === "settings"}
          onClick={() => onView("settings")}
          icon="⌬"
          label="System Settings"
          meta="CFG"
        />
        <div aria-hidden="true" className="row items-center justify-between" style={{ padding: "10px 14px 6px", borderTop: "0.5px solid var(--hair)", marginTop: 6 }}>
          <div className="col">
            <span className="mono-mini bone-3">OPERATOR</span>
            <span className="bone" style={{ fontSize: 11, letterSpacing: "0.08em" }}>OP-7F · ALPHA</span>
          </div>
          <div className="col items-end gap-2">
            <Sig pct={98} />
            <span className="mono-mini hot">SIG 98%</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function SectionLabel({ text, right }) {
  return (
    <div className="row items-center justify-between" style={{ padding: "18px 16px 8px 20px" }}>
      <span className="mono-mini" style={{ color: "var(--bone-3)", letterSpacing: "0.16em", fontSize: 9.5 }}>{text}</span>
      {right}
    </div>
  );
}

function SideRow({ active, onClick, icon, label, meta }) {
  return (
    <button onClick={onClick} className={`sm-side-item ${active ? "active" : ""}`} style={{ width: "100%" }}>
      <span aria-hidden="true" className="br-l br-inline">[</span>
      <span aria-hidden="true" style={{ width: 14, textAlign: "center", color: active ? "var(--orange)" : "var(--bone-3)", flexShrink: 0 }}>{icon}</span>
      <span className="label">{label}</span>
      <span aria-hidden="true" className="br-r br-inline">]</span>
      <span className="meta">{meta}</span>
    </button>
  );
}

function SessionRow({ session, active, onClick }) {
  const isRunning  = session.status === "RUNNING";
  const isQueued   = session.status === "QUEUED";
  const statusColor =
    session.status === "RUNNING"  ? "var(--orange)" :
    session.status === "QUEUED"   ? "var(--bone-2)" :
    session.status === "IDLE"     ? "var(--bone-2)" :
                                    "var(--bone-3)";
  return (
    <button onClick={onClick} className={`sm-side-item ${active ? "active" : ""}`} style={{ width: "100%", padding: "10px 12px 10px 18px" }}>
      <span aria-hidden="true" className="br-l">[</span>
      <span className="col flex-1" style={{ alignItems: "flex-start", overflow: "hidden", gap: 2 }}>
        <span className="row items-center gap-2" style={{ width: "100%" }}>
          <span className="mono-mini" style={{ color: statusColor, letterSpacing: "0.18em" }}>
            {session.code}
          </span>
          {isRunning ? <span style={{
            width: 6, height: 6, borderRadius: 0, background: "var(--orange)",
            boxShadow: "0 0 6px var(--orange)",
            animation: "cursor-blink 1.1s step-end infinite"
          }} /> : null}
        </span>
        <span className="truncate bone" style={{
          fontSize: 11, letterSpacing: "0.02em", textTransform: "none", width: "100%"
        }}>
          {session.name}
        </span>
        <span className="mono-mini bone-3">
          {session.phase}{isQueued ? " · QUEUED" : ""}
        </span>
      </span>
      <span aria-hidden="true" className="br-r">]</span>
    </button>
  );
}

Object.assign(window, { Sidebar });
