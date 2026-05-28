// rooms.jsx — Pro Room / Con Room / Settings panels
// ----------------------------------------------------------------------

import React, { useState, useEffect } from 'react';
import { Btn } from './hud.jsx';
import { api } from './data.jsx';

function TeamRoomPanel({ team, intelligence, assignments }) {
  const isCon    = team === "CON";
  const teamKey  = team.toLowerCase();   // "pro" or "con"

  // Backend shape: intelligence.team_rooms.{pro|con} = list of typed records
  // Each record: { record_type, team, role, agent_id, title, content, status, confidence, payload }
  const teamRecords  = intelligence?.team_rooms?.[teamKey] || [];

  const claims     = teamRecords.filter(r => r.record_type === "claim");
  const evidence   = teamRecords.filter(r => r.record_type === "evidence");
  const challenges = teamRecords.filter(r => r.record_type === "challenge");
  const memRecs    = teamRecords.filter(r => r.record_type === "memory_saved");

  // Filter experiences to this team's agents
  const teamExperiences = (intelligence?.experiences || [])
    .filter(e => (e.agent_id || "").startsWith(teamKey + "_"));

  // "Attention" = low-confidence or explicitly flagged records
  const attentionItems = teamRecords.filter(
    r => r.status === "flagged" || (typeof r.confidence === "number" && r.confidence < 0.4)
  );

  const teamAssignments = (assignments || []).filter(a => a.team === team);
  const hasContent = teamRecords.length || teamAssignments.length || teamExperiences.length;

  return (
    <div className="col full" style={{ overflowY: "auto" }}>
      {/* Header */}
      <div className="col" style={{ borderBottom: "0.5px solid var(--hair)", padding: "18px 24px", background: "var(--void-2)" }}>
        <div className="row items-center gap-3">
          <span className={`sm-tag ${isCon ? "sm-tag--con" : "sm-tag--pro"}`}>
            {team} · PREP CHAMBER
          </span>
          <span className="bone-3 mono-mini">
            {intelligence ? `${teamRecords.length} intel records` : "awaiting debate"}
          </span>
        </div>
      </div>

      {!hasContent ? (
        <div className="col items-center justify-center" style={{ flex: 1, padding: "64px 24px", color: "var(--bone-3)" }}>
          <span className="mono-mini" style={{ letterSpacing: "0.14em", marginBottom: 8 }}>NO INTEL</span>
          <span style={{ fontSize: 13 }}>Start a debate to populate this room.</span>
        </div>
      ) : (
        <div className="row gap-4 sm-stagger" style={{ padding: "20px 24px 32px", flexWrap: "wrap" }}>

          {/* TALKING POINTS — from claim records */}
          {claims.length > 0 && (
            <RoomSection title="Talking points" flex={1} minWidth={320}>
              <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
                {claims.map((r, i) => (
                  <li key={r.id || i} className="row items-start gap-4" style={{ padding: "12px 0", borderBottom: "0.5px solid var(--hair)" }}>
                    <span className={isCon ? "hot" : "bone-3"} style={{ fontSize: 11, letterSpacing: "0.10em", flexShrink: 0, width: 24 }}>
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div className="col" style={{ flex: 1, minWidth: 0 }}>
                      {r.title && <span className="bone" style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{r.title}</span>}
                      <span className="bone" style={{ fontSize: r.title ? 12.5 : 13.5, lineHeight: 1.55, color: r.title ? "var(--bone-2)" : "var(--bone)" }}>{r.content}</span>
                    </div>
                  </li>
                ))}
              </ol>
            </RoomSection>
          )}

          {/* EVIDENCE LOCKER */}
          {evidence.length > 0 && (
            <RoomSection title="Evidence" flex={1.2} minWidth={360}>
              <div className="col gap-2">
                {evidence.map((r, i) => (
                  <div key={r.id || i} className="col" style={{
                    padding: "12px 14px",
                    background: "var(--void-3)",
                    border: "0.5px solid var(--hair-2)",
                  }}>
                    <span className="bone" style={{ fontSize: 13, marginBottom: r.content ? 4 : 0 }}>{r.title}</span>
                    {r.content && <span className="bone-2" style={{ fontSize: 12, lineHeight: 1.5 }}>{r.content.slice(0, 200)}{r.content.length > 200 ? "…" : ""}</span>}
                    <div className="row items-center justify-between" style={{ marginTop: 6 }}>
                      <span className="mono-mini bone-3">{r.agent_id || r.role || ""}</span>
                      {typeof r.confidence === "number" && (
                        <div className="row items-center gap-2">
                          <span style={{ width: 56, height: 2, background: "var(--void-4)" }}>
                            <i style={{ display: "block", height: "100%", width: `${r.confidence * 100}%`, background: isCon ? "var(--orange)" : "var(--bone-2)" }} />
                          </span>
                          <span className="mono-mini" style={{ color: isCon ? "var(--orange)" : "var(--bone)" }}>
                            {r.confidence.toFixed(2)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </RoomSection>
          )}

          {/* COUNTER-PREP — from challenge records */}
          {challenges.length > 0 && (
            <RoomSection title="If / then" flex={1} minWidth={320}>
              <div className="col gap-2">
                {challenges.map((r, i) => (
                  <div key={r.id || i} className="row items-start gap-3" style={{
                    padding: "10px 12px",
                    background: "var(--void-3)",
                    border: "0.5px dashed var(--hair-2)",
                  }}>
                    <span className={isCon ? "hot" : "bone-3"} style={{ fontSize: 11, letterSpacing: "0.06em", flexShrink: 0, width: 18 }}>→</span>
                    <div className="col" style={{ flex: 1, minWidth: 0 }}>
                      {r.title && <span className="bone" style={{ fontSize: 12.5, fontWeight: 500 }}>{r.title}</span>}
                      <span className="bone" style={{ fontSize: 13, lineHeight: 1.55 }}>{r.content}</span>
                    </div>
                  </div>
                ))}
              </div>
            </RoomSection>
          )}

          {/* ATTENTION FLAGS */}
          {attentionItems.length > 0 && (
            <RoomSection title="Operator attention" flex={1} minWidth={320}>
              <div className="col gap-2">
                {attentionItems.map((r, i) => (
                  <div key={r.id || i} className="row items-start gap-3" style={{
                    padding: "12px 14px",
                    background: "rgba(255, 78, 0, 0.05)",
                    border: "0.5px solid var(--orange-dim)",
                  }}>
                    <span className="hot" style={{ fontSize: 13, lineHeight: 1, flexShrink: 0 }}>▲</span>
                    <div className="col" style={{ flex: 1, minWidth: 0 }}>
                      {r.title && <span className="bone" style={{ fontSize: 12.5, fontWeight: 500 }}>{r.title}</span>}
                      <span style={{ fontSize: 13, lineHeight: 1.55, color: "var(--bone)" }}>{r.content}</span>
                    </div>
                  </div>
                ))}
              </div>
            </RoomSection>
          )}

          {/* TEAM ROSTER */}
          {teamAssignments.length > 0 && (
            <RoomSection title="Roster" flex={1} minWidth={280}>
              <div className="col gap-2">
                {teamAssignments.map(a => (
                  <div key={a.id} className="row items-center justify-between" style={{
                    padding: "10px 12px",
                    background: "var(--void-3)",
                    border: "0.5px solid var(--hair-2)",
                  }}>
                    <div className="col">
                      <span className="bone" style={{ fontSize: 13, letterSpacing: "0.02em" }}>{a.speaker}</span>
                      <span className="bone-3 mono-mini">{a.role}</span>
                    </div>
                    <span className="bone-3 mono-mini">{a.provider || a.model || ""}</span>
                  </div>
                ))}
              </div>
            </RoomSection>
          )}

          {/* INTERNAL CHATTER — from memory records or experience log */}
          {(memRecs.length > 0 || teamExperiences.length > 0) && (
            <RoomSection title="Internal chatter" flex={1.2} minWidth={360}>
              <div className="col" style={{ fontSize: 12.5, lineHeight: 1.55 }}>
                {memRecs.map((r, i) => (
                  <IntelLine key={r.id || i} time={fmtTime(r.created_at, i)} speaker={agentLabel(r.agent_id || r.role)}>
                    {r.content}
                  </IntelLine>
                ))}
                {memRecs.length === 0 && teamExperiences.slice(0, 8).map((e, i) => (
                  <IntelLine key={e.id || i} time={fmtTime(e.created_at, i)} speaker={agentLabel(e.agent_id)}>
                    {e.lesson}
                  </IntelLine>
                ))}
              </div>
            </RoomSection>
          )}

        </div>
      )}
    </div>
  );
}

function fmtTime(isoStr, fallbackIdx) {
  if (!isoStr) return `T+${String(fallbackIdx).padStart(2, "0")}:00`;
  try {
    const d = new Date(isoStr);
    const p = n => String(n).padStart(2, "0");
    return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}:${p(d.getUTCSeconds())}`;
  } catch { return `T+${fallbackIdx}`; }
}

function agentLabel(agentId = "") {
  return agentId.replace(/^(pro|con)_/, "").replace(/_/g, " ").toUpperCase().slice(0, 10) || "SYS";
}

function RoomSection({ title, flex, minWidth, action, children }) {
  return (
    <section className="relative col" style={{
      flex, minWidth,
      padding: "16px 18px 14px",
      background: "var(--void-2)",
      border: "0.5px solid var(--hair)",
    }}>
      <div className="row items-center justify-between" style={{ marginBottom: 14 }}>
        <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>{title}</h3>
        {action}
      </div>
      {children}
    </section>
  );
}

function IntelLine({ time, speaker, hot, children }) {
  return (
    <div className="row items-start gap-3" style={{ padding: "8px 0", borderBottom: "0.5px solid var(--hair)" }}>
      <span className="mono-mini bone-3" style={{ width: 78, flexShrink: 0 }}>{time}</span>
      <span className={hot ? "hot" : "bone-3"} style={{ fontSize: 10, letterSpacing: "0.10em", width: 64, flexShrink: 0 }}>{speaker}</span>
      <span className="bone" style={{ flex: 1 }}>{children}</span>
    </div>
  );
}

// ----------------------------------------------------------------------
// SETTINGS PANEL
// ----------------------------------------------------------------------

function SettingsPanel({ settings, councilSettings, models, onSave, onUpdateCouncil }) {
  const [local,        setLocal]        = useState({});
  const [localCouncil, setLocalCouncil] = useState({});
  const [dirty,        setDirty]        = useState(false);
  const [saving,       setSaving]       = useState(false);

  // Sync when props change (new session selected, or data loads)
  useEffect(() => { setLocal(settings ? { ...settings } : {}); setDirty(false); }, [settings]);
  useEffect(() => { setLocalCouncil(councilSettings ? { ...councilSettings } : {}); }, [councilSettings]);

  // Controlled setters — mark dirty
  const set  = (key, val) => { setLocal(l => ({ ...l, [key]: val })); setDirty(true); };
  const setC = (key, val) => { setLocalCouncil(l => ({ ...l, [key]: val })); setDirty(true); };

  // Read with fallback: local edit → server value → hardcoded default
  const s = (key, fb) => local[key] ?? settings?.[key] ?? fb;
  const c = (key, fb) => localCouncil[key] ?? councilSettings?.[key] ?? fb;

  const commit = async () => {
    setSaving(true);
    try {
      if (settings       !== null && onSave)           await onSave(local);
      if (councilSettings !== null && onUpdateCouncil) await onUpdateCouncil(localCouncil);
      setDirty(false);
    } catch (e) {
      console.error("Settings save failed:", e);
    } finally {
      setSaving(false);
    }
  };

  const discard = () => {
    setLocal(settings ? { ...settings } : {});
    setLocalCouncil(councilSettings ? { ...councilSettings } : {});
    setDirty(false);
  };

  const judgeMode  = (s("judge_mode",  "hybrid")      || "hybrid").toUpperCase();
  const tone       = (s("tone",        "adversarial") || "adversarial").toUpperCase();
  const strictness = (s("evidence_strictness", "strict") || "strict").toUpperCase();

  return (
    <div className="col full" style={{ overflowY: "auto" }}>
      {/* Header */}
      <div className="col" style={{ borderBottom: "0.5px solid var(--hair)", padding: "18px 24px 16px", background: "var(--void-2)" }}>
        <div className="row items-center justify-between">
          <div className="row items-center gap-3">
            <span className="sm-tag">CFG</span>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 500, letterSpacing: "0.04em", color: "var(--bone)" }}>
              {settings !== null ? "Session configuration" : "Council configuration"}
            </h2>
          </div>
          <div className="row items-center gap-3">
            <Btn variant="ghost" onClick={discard}>DISCARD</Btn>
            <Btn variant={dirty ? "hot" : "ghost"} onClick={commit} style={{ opacity: saving ? 0.6 : 1 }}>
              {saving ? "SAVING…" : "COMMIT"}
            </Btn>
          </div>
        </div>
      </div>

      <div className="col gap-4 sm-stagger" style={{ padding: "16px 24px 48px", maxWidth: 1100, margin: "0 auto", width: "100%" }}>

        {/* ── Session-level settings (shown when a session is open) ── */}
        {settings !== null && (
          <>
            <SettingsPanelGroup title="Council topology">
              <SettingsRow label="Debaters per team" hint="Adds Rebuttal Critic, Evidence Researcher, and Cross-Examiner in order.">
                <StepInput value={s("debaters_per_team", 3)} onChange={v => set("debaters_per_team", v)} min={1} max={4} suffix=" / 4" />
              </SettingsRow>
              <SettingsRow label="Debate rounds" hint="Total rebuttal exchanges. Cross-exam and closing run independently.">
                <StepInput value={s("debate_rounds", 4)} onChange={v => set("debate_rounds", v)} min={1} max={8} suffix=" rd" />
              </SettingsRow>
              <SettingsRow label="Judge panel size" hint="Single judge is faster. 3 or 5 reduces variance.">
                <RadioGroup value={s("judge_panel_size", 1)} options={[1, 3, 5]} onChange={v => set("judge_panel_size", v)} />
              </SettingsRow>
              <SettingsRow label="Judge mode" hint="Performance scores rhetorical fit. Truth-seeking weights evidence.">
                <RadioGroup value={judgeMode} options={["PERFORMANCE", "TRUTH", "HYBRID"]} onChange={v => set("judge_mode", v.toLowerCase())} />
              </SettingsRow>
            </SettingsPanelGroup>

            <SettingsPanelGroup title="Inference">
              <SettingsRow label="Temperature" hint="0.0 deterministic · 1.0 exploratory. Cross-examiner runs hotter.">
                <Slider value={s("temperature", 0.7)} onChange={v => set("temperature", v)} min={0} max={2} step={0.05} format={v => v.toFixed(2)} />
              </SettingsRow>
              <SettingsRow label="Max tokens per turn">
                <StepInput value={s("max_tokens", 1024)} onChange={v => set("max_tokens", v)} min={128} max={4096} suffix=" tok" big />
              </SettingsRow>
              <SettingsRow label="Web search" hint="Limits to Evidence Researchers when enabled.">
                <Toggle on={s("enable_web_search", true)} onChange={v => set("enable_web_search", v)} />
              </SettingsRow>
            </SettingsPanelGroup>

            <SettingsPanelGroup title="Behavior">
              <SettingsRow label="Tone">
                <RadioGroup value={tone} onChange={v => set("tone", v.toLowerCase())} options={["NEUTRAL", "ADVERSARIAL", "FORMAL", "AGGRESSIVE"]} />
              </SettingsRow>
              <SettingsRow label="Evidence strictness">
                <RadioGroup value={strictness} onChange={v => set("evidence_strictness", v.toLowerCase())} options={["LENIENT", "NORMAL", "STRICT"]} />
              </SettingsRow>
              <SettingsRow label="Fact-check mode" hint="Post-hoc audit by Judge Assistant.">
                <Toggle on={s("enable_fact_checking", true)} onChange={v => set("enable_fact_checking", v)} />
              </SettingsRow>
              <SettingsRow label="Auto-scroll arena">
                <Toggle on={s("auto_scroll", true)} onChange={v => set("auto_scroll", v)} />
              </SettingsRow>
            </SettingsPanelGroup>
          </>
        )}

        {/* ── Council-level settings (shown on global settings view) ── */}
        {councilSettings !== null && (
          <SettingsPanelGroup title="Council behavior">
            <SettingsRow label="Universal experience" hint="Lets agent identities learn across sessions.">
              <Toggle on={c("universal_experience", true)} onChange={v => setC("universal_experience", v)} />
            </SettingsRow>
            <SettingsRow label="Web search (global)" hint="Can be overridden per session.">
              <Toggle on={c("enable_web_search", true)} onChange={v => setC("enable_web_search", v)} />
            </SettingsRow>
            <SettingsRow label="Fact-check mode (global)">
              <Toggle on={c("enable_fact_checking", true)} onChange={v => setC("enable_fact_checking", v)} />
            </SettingsRow>
          </SettingsPanelGroup>
        )}

        {/* ── Memory management ── */}
        <SettingsPanelGroup title="Memory">
          <SettingsRow label="Agent memory" hint="Identity records carried across sessions.">
            <Btn variant="hot" onClick={async () => {
              const conf = window.prompt("Type RESET COUNCIL IDENTITIES to confirm agent memory wipe:");
              if ((conf || "").trim() === "RESET COUNCIL IDENTITIES") {
                try { await api.resetAgentExperience("RESET COUNCIL IDENTITIES"); }
                catch (e) { console.error(e); }
              }
            }}>PURGE</Btn>
          </SettingsRow>
          <SettingsRow label="User training profile">
            <Btn variant="hot" onClick={async () => {
              const conf = window.prompt("Type RESET USER DEBATE PROFILE to confirm profile wipe:");
              if ((conf || "").trim() === "RESET USER DEBATE PROFILE") {
                try { await api.resetUserProfile("RESET USER DEBATE PROFILE"); }
                catch (e) { console.error(e); }
              }
            }}>RESET</Btn>
          </SettingsRow>
        </SettingsPanelGroup>

        {/* ── Danger zone ── */}
        <div className="relative col" style={{
          padding: "18px 22px",
          background: "rgba(255, 78, 0, 0.04)",
          border: "0.5px solid var(--orange-dim)",
        }}>
          <div className="row items-center justify-between gap-6">
            <div className="col" style={{ flex: 1 }}>
              <h3 style={{ margin: 0, fontSize: 14, fontWeight: 500, color: "var(--orange)", letterSpacing: "0.02em" }}>
                Hard reset · irreversible
              </h3>
              <p className="bone-2" style={{ fontSize: 12, marginTop: 6, lineHeight: 1.55 }}>
                Wipe all sessions, memory records, training profile, and configuration. Cannot be undone.
              </p>
            </div>
            <Btn variant="hot" onClick={() => {
              window.alert("Not yet implemented. Delete sessions and purge memory from the sidebar and memory views.");
            }}>INITIATE PURGE</Btn>
          </div>
        </div>

      </div>
    </div>
  );
}

function SettingsPanelGroup({ title, children }) {
  return (
    <section className="relative col" style={{
      padding: "18px 22px 14px",
      background: "var(--void-2)",
      border: "0.5px solid var(--hair)",
    }}>
      <h3 style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>{title}</h3>
      <div className="col">{children}</div>
    </section>
  );
}

function SettingsRow({ label, hint, children }) {
  return (
    <div className="row items-center justify-between gap-6" style={{ padding: "14px 0", borderBottom: "0.5px solid var(--hair)" }}>
      <div className="col" style={{ flex: 1, minWidth: 0 }}>
        <span className="bone" style={{ fontSize: 13, letterSpacing: "0.01em" }}>{label}</span>
        {hint ? <span style={{ marginTop: 4, fontSize: 11.5, color: "var(--bone-3)", lineHeight: 1.5 }}>{hint}</span> : null}
      </div>
      <div className="row items-center" style={{ flexShrink: 0 }}>{children}</div>
    </div>
  );
}

function StepInput({ value, onChange, min, max, suffix = "", big = false }) {
  return (
    <div className="row items-center gap-2">
      <button onClick={() => onChange(Math.max(min, value - 1))} className="sm-btn" style={{ padding: "4px 10px" }}>−</button>
      <span style={{
        minWidth: 70, textAlign: "center", padding: "6px 10px",
        background: "var(--void)", border: "0.5px solid var(--hair-hot)",
        fontSize: big ? 13 : 14, letterSpacing: "0.08em", color: "var(--bone)",
      }}>{value}{suffix}</span>
      <button onClick={() => onChange(Math.min(max, value + 1))} className="sm-btn" style={{ padding: "4px 10px" }}>+</button>
    </div>
  );
}

function RadioGroup({ value, options, onChange, suffix = "" }) {
  return (
    <div className="row gap-0" style={{ border: "0.5px solid var(--hair-2)", clipPath: "var(--clip-panel-sm)" }}>
      {options.map((o, i) => (
        <button
          key={o}
          onClick={() => onChange && onChange(o)}
          style={{
            padding: "6px 14px",
            fontSize: 11, letterSpacing: "0.12em",
            background: value === o ? "var(--orange)" : "var(--void)",
            color: value === o ? "var(--void)" : "var(--bone-2)",
            borderRight: i < options.length - 1 ? "0.5px solid var(--hair-2)" : "none",
          }}
        >{o}{suffix}</button>
      ))}
    </div>
  );
}

function Slider({ value, onChange, min, max, step, format }) {
  return (
    <div className="row items-center gap-3" style={{ width: 280 }}>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ flex: 1, accentColor: "var(--orange)", height: 4 }}
      />
      <span style={{ minWidth: 56, textAlign: "right", fontSize: 13, color: "var(--bone)", letterSpacing: "0.06em" }}>
        {format(value)}
      </span>
    </div>
  );
}

function Toggle({ on, onChange }) {
  // Uncontrolled with initial value when no onChange; fully controlled when onChange provided
  const [internal, setInternal] = useState(!!on);
  const controlled = onChange !== undefined;
  const value      = controlled ? !!on : internal;

  const handleClick = () => {
    if (controlled) onChange(!value);
    else setInternal(o => !o);
  };

  return (
    <button onClick={handleClick} style={{
      width: 56, height: 22,
      background: value ? "var(--orange)" : "var(--void-4)",
      border: `0.5px solid ${value ? "var(--orange)" : "var(--hair-2)"}`,
      position: "relative",
      transition: "background 160ms var(--easing)",
    }}>
      <span style={{
        position: "absolute", top: 2, left: value ? 32 : 2,
        width: 18, height: 16,
        background: value ? "var(--void)" : "var(--bone-3)",
        transition: "left 160ms var(--easing)",
      }} />
      <span style={{
        position: "absolute", top: 4, left: value ? 8 : 36,
        fontSize: 9, letterSpacing: "0.14em",
        color: value ? "var(--void)" : "var(--bone-3)",
      }}>{value ? "ON" : "OFF"}</span>
    </button>
  );
}

export { TeamRoomPanel, SettingsPanel };
