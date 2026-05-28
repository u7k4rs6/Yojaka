// workspace.jsx — GlobalWorkspace: dashboard / agent memory / training profile
// Data comes from backend API via props from App
// ----------------------------------------------------------------------

import React from 'react';
import { Btn, Tag, LiveClock } from './hud.jsx';
import { api } from './data.jsx';

function GlobalWorkspace({ view, onNewSession, sessions, models, providers, experiences, userProfile }) {
  if (view === "memory")  return <AgentMemoryView  experiences={experiences} />;
  if (view === "profile") return <TrainingProfileView profile={userProfile} />;
  return <DashboardView onNewSession={onNewSession} sessions={sessions} models={models} providers={providers} />;
}

// ── DASHBOARD ────────────────────────────────────────────────────────

function DashboardView({ onNewSession, sessions, models, providers }) {
  const aiSessions    = (sessions || []).filter(s => s.mode !== "ai_vs_human");
  const humanSessions = (sessions || []).filter(s => s.mode === "ai_vs_human");

  return (
    <div className="col full" style={{ overflowY: "auto" }}>
      {/* Hero */}
      <div className="col" style={{ padding: "48px 32px 24px", borderBottom: "0.5px solid var(--hair)", position: "relative" }}>
        <div aria-hidden="true" className="row items-center gap-3" style={{ marginBottom: 12 }}>
          <span className="sm-tag sm-tag--hot">SITREP</span>
          <span className="mono-mini bone-3">OPERATOR · CLEARANCE 3</span>
          <span className="mono-mini bone-3">·</span>
          <LiveClock />
        </div>
        <h1 style={{ margin: 0, fontSize: 56, fontWeight: 500, letterSpacing: "-0.02em", lineHeight: 1.0, color: "var(--bone)", maxWidth: 920 }}>
          Strategic <span className="hot">debate</span><br />
          intelligence terminal.
        </h1>
        <p className="bone-2" style={{ fontSize: 14, lineHeight: 1.6, marginTop: 14, maxWidth: 640, letterSpacing: "0.01em" }}>
          Orchestrate adversarial multi-agent reasoning. Train against adaptive opponents.
          Inspect every claim, every citation, every verdict — at frame-level fidelity.
        </p>
        <div className="row gap-3" style={{ marginTop: 28 }}>
          <Btn variant="hot" onClick={() => onNewSession?.("ai_vs_ai")} style={{ padding: "12px 22px", fontSize: 12 }}>
            INITIATE COUNCIL DEBATE
          </Btn>
          <Btn onClick={() => onNewSession?.("ai_vs_human")} style={{ padding: "12px 22px", fontSize: 12 }}>
            ENTER TRAINING ARENA
          </Btn>
        </div>
      </div>

      {/* Bento */}
      <div className="col gap-4 sm-stagger" style={{ padding: "20px 32px 48px", maxWidth: 1320, margin: "0 auto", width: "100%" }}>

        {/* KPI strip */}
        <div className="row gap-3" style={{ flexWrap: "wrap" }}>
          <BigStat value={String(models?.length  || 0)} label="Available models" />
          <BigStat value={String(providers?.length || 0)} label="Active providers" hot />
          <BigStat value={String(aiSessions.length)}    label="Council debates" />
          <BigStat value={String(humanSessions.length)} label="Practice sessions" />
          <BigStat value={String(sessions?.length || 0)} label="Total sessions" />
        </div>

        {/* Mode cards */}
        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          <ModeCard
            badge="RECOMMENDED"
            title="AI vs Human — Training"
            code="PRC_OPS"
            body="Spar with a Practice Debater. Receive a Judge verdict. Get a coach-style Trainer report. Your profile updates after every resolved round."
            tags={["Rebuttal drills", "Profile build", "Coach feedback"]}
            onClick={() => onNewSession?.("ai_vs_human")}
            hot flex={1}
          />
          <ModeCard
            badge="COUNCIL LAB"
            title="AI vs AI — Council"
            code="DBT_OPS"
            body="Watch Pro and Con teams argue any resolution. Inspect claims, evidence, and verdict logic at frame-level fidelity."
            tags={["Multi-agent", "Deep analytics", "Evidence trace"]}
            onClick={() => onNewSession?.("ai_vs_ai")}
            flex={1}
          />
        </div>

        {/* Providers + sessions */}
        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          <div className="relative col" style={{ flex: 1.4, minWidth: 360, padding: "16px 18px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <div className="row items-center justify-between" style={{ marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Inference providers</h3>
              <span className="mono-mini bone-3">
                {providers?.length || 0} available
              </span>
            </div>
            <div className="col">
              {providers?.length ? providers.map(p => (
                <ProviderRow key={p.provider} p={{
                  name:    p.provider_label || p.provider,
                  models:  p.unlocked_model_count || 0,
                  status:  "ONLINE",
                  latency: 0,
                }} />
              )) : (
                <span className="mono-mini bone-4" style={{ padding: "8px 0" }}>
                  No providers available. Check your API keys in .env
                </span>
              )}
            </div>
          </div>

          <div className="relative col" style={{ flex: 1, minWidth: 320, padding: "16px 18px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Recent sessions</h3>
            <div className="col gap-1" style={{ marginTop: 10, fontSize: 11.5 }}>
              {sessions?.length ? sessions.slice(0, 6).map(s => (
                <OpLine key={s.id} time={s.code} ch={s.mode === "ai_vs_human" ? "PRC" : "DBT"} ev={s.name} />
              )) : (
                <OpLine time="—" ch="SYS" ev="No sessions yet. Create one above." />
              )}
            </div>
          </div>

          <div className="relative col" style={{ flex: 1, minWidth: 280, padding: "16px 18px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Available models</h3>
            <DList rows={
              models?.slice(0, 6).map(m => [
                m.provider_label || m.name.split("/")[0],
                m.name.split("/").pop(),
              ]) || [["Status", "Loading..."]]
            } />
          </div>
        </div>

      </div>
    </div>
  );
}

function BigStat({ value, label, hot }) {
  return (
    <div className="relative col" style={{ flex: 1, minWidth: 160, padding: "16px 18px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
      <span className={hot ? "hot" : "bone"} style={{ fontSize: 32, fontWeight: 500, letterSpacing: "0.02em", lineHeight: 1 }}>
        {value}
      </span>
      <span className="bone-3" style={{ marginTop: 8, fontSize: 11, letterSpacing: "0.02em" }}>{label}</span>
    </div>
  );
}

function ModeCard({ badge, title, code, body, tags, onClick, hot, flex }) {
  return (
    <button onClick={onClick} className="relative col" style={{
      flex, minWidth: 320, padding: "22px 24px 20px",
      background: "var(--void-2)",
      border: "0.5px solid " + (hot ? "var(--orange-dim)" : "var(--hair)"),
      textAlign: "left", cursor: "pointer",
      transition: "background 160ms var(--easing), border-color 160ms var(--easing)",
    }}>
      <div className="row items-center justify-between">
        <span className={"sm-tag " + (hot ? "sm-tag--hot" : "")}>{badge}</span>
        <span className="mono-mini bone-3">{code}</span>
      </div>
      <h2 style={{ margin: "18px 0 0", fontSize: 24, fontWeight: 500, letterSpacing: "-0.005em", color: "var(--bone)" }}>
        {title}
      </h2>
      <p className="bone-2" style={{ fontSize: 13, lineHeight: 1.6, marginTop: 10, maxWidth: 540 }}>{body}</p>
      <div className="row gap-2" style={{ marginTop: 16, flexWrap: "wrap" }}>
        {tags.map(t => <Tag key={t}>{t}</Tag>)}
      </div>
      <div className="row items-center gap-3" style={{ marginTop: 20, fontSize: 11, letterSpacing: "0.16em", color: hot ? "var(--orange)" : "var(--bone-2)" }}>
        <span>INITIATE</span>
        <span style={{ flex: 1, height: "0.5px", background: hot ? "var(--orange-dim)" : "var(--hair-2)" }} />
        <span>→</span>
      </div>
    </button>
  );
}

function ProviderRow({ p }) {
  const isOnline = p.status === "ONLINE";
  const isDeg    = p.status === "DEGRADED";
  const isOff    = p.status === "OFFLINE";
  const col = isOnline ? "var(--bone)" : isDeg ? "var(--orange)" : "var(--bone-3)";
  return (
    <div className="row items-center justify-between" style={{ padding: "8px 0", borderBottom: "0.5px solid var(--hair)" }}>
      <div className="row items-center gap-3">
        <span style={{ width: 8, height: 8, background: col, boxShadow: isDeg ? "0 0 6px var(--orange)" : "none" }} />
        <span className="bone" style={{ fontSize: 12, letterSpacing: "0.06em" }}>{p.name}</span>
      </div>
      <div className="row items-center gap-4">
        <span className="mono-mini bone-3">{p.models} MDL</span>
        <span className="mono-mini bone-3" style={{ minWidth: 56, textAlign: "right" }}>
          {isOff ? "—" : p.latency > 0 ? `${p.latency}ms` : "—"}
        </span>
        <span className="mono-mini" style={{ color: col, minWidth: 70, textAlign: "right" }}>{p.status}</span>
      </div>
    </div>
  );
}

function OpLine({ time, ch, ev, hot }) {
  return (
    <div className="row items-start gap-2" style={{ padding: "4px 0", borderBottom: "0.5px solid var(--hair)" }}>
      <span className="mono-mini bone-3" style={{ width: 76, flexShrink: 0 }}>{time}</span>
      <span className={hot ? "hot" : "bone-2"} style={{ fontSize: 10, letterSpacing: "0.12em", width: 50, flexShrink: 0 }}>{ch}</span>
      <span className="bone" style={{ flex: 1, fontSize: 11.5, lineHeight: 1.5 }}>{ev}</span>
    </div>
  );
}

function DList({ rows }) {
  return (
    <dl className="col gap-2" style={{ margin: "10px 0 0" }}>
      {rows.map(([k, v], i) => (
        <div key={i} className="row items-center justify-between" style={{
          padding: "5px 0", borderBottom: "0.5px solid var(--hair)",
          fontSize: 11, letterSpacing: "0.08em",
        }}>
          <dt className="bone-3">{k}</dt>
          <dd className="bone" style={{ margin: 0 }}>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

// ── AGENT MEMORY VIEW ─────────────────────────────────────────────────

function AgentMemoryView({ experiences }) {
  if (!experiences) {
    return (
      <div className="col full items-center justify-center" style={{ gap: 8, opacity: 0.4 }}>
        <span className="mono-mini bone-3" style={{ letterSpacing: "0.16em" }}>LOADING MEMORY RECORDS…</span>
      </div>
    );
  }

  const summary   = experiences.summary  || {};
  const byAgent   = experiences.by_agent || [];
  const byLesson  = Object.entries(experiences.by_lesson_type || {});
  const recentEvt = experiences.memory_events || [];
  const maxRecords= Math.max(...byAgent.map(r => r.record_count), 1);

  return (
    <div className="col full" style={{ overflowY: "auto" }}>
      <div className="col" style={{ borderBottom: "0.5px solid var(--hair)", padding: "18px 24px 16px", background: "var(--void-2)" }}>
        <div className="row items-center justify-between">
          <div className="row items-center gap-3">
            <span className="sm-tag">MEM</span>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 500, letterSpacing: "0.04em", color: "var(--bone)" }}>Agent memory</h2>
          </div>
          <div className="row items-center gap-3">
            <Btn variant="ghost">COPY OVERVIEW</Btn>
            <Btn variant="hot" onClick={() => {
              const phrase = window.prompt('Type RESET COUNCIL IDENTITIES to confirm:');
              if (phrase) api.resetAgentExperience(phrase).catch(console.error);
            }}>PURGE ALL</Btn>
          </div>
        </div>
      </div>

      <div className="col gap-4 sm-stagger" style={{ padding: "16px 24px 32px", maxWidth: 1280, margin: "0 auto", width: "100%" }}>

        <div className="row gap-3" style={{ flexWrap: "wrap" }}>
          <BigStat value={String(summary.total_records       || 0)} label="Experience records" />
          <BigStat value={String(summary.distinct_agents     || 0)} label="Tracked identities" />
          <BigStat value={`${summary.universal_records || 0} / ${summary.chat_records || 0}`} label="Universal / chat" />
          <BigStat value={String(summary.total_uses          || 0)} label="Total reuses" hot />
        </div>

        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          {/* Roster */}
          <div className="relative col" style={{ flex: 2, minWidth: 480, padding: "18px 20px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Identity roster</h3>
            <div className="col gap-2" style={{ marginTop: 12 }}>
              {byAgent.length ? byAgent.slice(0, 10).map(r => (
                <div key={r.agent_id} className="row items-center gap-3" style={{
                  padding: "10px 12px", background: "var(--void-3)", border: "0.5px solid var(--hair-2)",
                }}>
                  <span className="bone" style={{ width: 140, fontSize: 11, letterSpacing: "0.06em" }}>
                    {r.agent_id}
                  </span>
                  <div className="col flex-1" style={{ gap: 2 }}>
                    <div className="row items-center justify-between">
                      <span className="bone-3" style={{ fontSize: 10 }}>records</span>
                      <span className="bone" style={{ fontSize: 11 }}>{r.record_count}</span>
                    </div>
                    <div className="sm-bar"><i style={{ "--v": r.record_count / maxRecords }} /></div>
                  </div>
                  <span className="mono-mini bone-2" style={{ width: 80, textAlign: "right" }}>{r.use_count} reuses</span>
                  <span className={`mono-mini ${r.high_confidence_count > 0 ? "hot" : "bone-2"}`} style={{ width: 60, textAlign: "right" }}>
                    {r.high_confidence_count > 0 ? "HIGH" : "MED"}
                  </span>
                </div>
              )) : (
                <span className="mono-mini bone-4">No agent identities yet. Run some debates to build memory.</span>
              )}
            </div>
          </div>

          {/* Lesson types */}
          <div className="relative col" style={{ flex: 1, minWidth: 280, padding: "18px 20px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Lesson types</h3>
            <div className="col gap-2" style={{ marginTop: 12 }}>
              {byLesson.length ? byLesson.sort((a, b) => b[1] - a[1]).slice(0, 8).map(([type, count]) => {
                const maxL = Math.max(...byLesson.map(([, v]) => v), 1);
                return (
                  <div key={type} className="col gap-1">
                    <div className="row items-center justify-between" style={{ fontSize: 11 }}>
                      <span className="bone">{type.replace(/_/g, " ")}</span>
                      <span className="mono-mini bone-2">{count}</span>
                    </div>
                    <div className="sm-bar"><i style={{ "--v": count / maxL }} /></div>
                  </div>
                );
              }) : (
                <span className="mono-mini bone-4">No lessons recorded yet.</span>
              )}
            </div>
            <h3 style={{ margin: "22px 0 0", fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--orange)" }}>Guardrails</h3>
            <div className="col gap-3" style={{ marginTop: 10, fontSize: 12.5, lineHeight: 1.5 }}>
              <div className="col gap-1">
                <span className="bone">No fake personality</span>
                <span className="bone-3" style={{ fontSize: 11 }}>Identity stays empty until real recorded activity.</span>
              </div>
              <div className="col gap-1">
                <span className="bone">Visible source trail</span>
                <span className="bone-3" style={{ fontSize: 11 }}>Backed by claims, evidence, scorecards, feedback.</span>
              </div>
              <div className="col gap-1">
                <span className="bone">Global default</span>
                <span className="bone-3" style={{ fontSize: 11 }}>Chat-scoped lessons stay local when isolation matters.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent memory commits */}
        {recentEvt.length > 0 && (
          <div className="relative col" style={{ padding: "18px 20px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Recent commits</h3>
            <div className="col" style={{ marginTop: 12 }}>
              {recentEvt.slice(0, 8).map((m, i) => (
                <div key={i} className="row items-start gap-3" style={{ padding: "10px 0", borderBottom: "0.5px solid var(--hair)" }}>
                  <span className="mono-mini bone-3" style={{ width: 160, flexShrink: 0 }}>
                    {m.created_at ? new Date(m.created_at).toLocaleTimeString() : "—"}
                  </span>
                  <span className="bone" style={{ fontSize: 11, letterSpacing: "0.06em", width: 130, flexShrink: 0 }}>
                    {m.agent_id || "council"}
                  </span>
                  <span className="mono-mini bone-2" style={{ width: 160, flexShrink: 0 }}>
                    {(m.record_type || "").replace(/_/g, " ")}
                  </span>
                  <span className="bone" style={{ flex: 1, fontSize: 12, lineHeight: 1.55 }}>
                    {m.content || m.detail || "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

// ── TRAINING PROFILE VIEW ─────────────────────────────────────────────

function TrainingProfileView({ profile }) {
  if (!profile) {
    return (
      <div className="col full items-center justify-center" style={{ gap: 8, opacity: 0.4 }}>
        <span className="mono-mini bone-3" style={{ letterSpacing: "0.16em" }}>LOADING PROFILE…</span>
      </div>
    );
  }

  const p          = profile.profile || {};
  const recent     = profile.recent_practice_debates || [];
  const recs       = profile.recommendations || [];
  const strengths  = p.strengths  || [];
  const weaknesses = p.weaknesses || [];
  const drills     = recs.slice(0, 3);
  const wins       = p.wins || {};
  const proWins    = wins.pro || 0;
  const conWins    = wins.con || 0;
  const total      = p.practice_debates_completed || 0;

  return (
    <div className="col full" style={{ overflowY: "auto" }}>
      <div className="col" style={{ borderBottom: "0.5px solid var(--hair)", padding: "18px 24px 16px", background: "var(--void-2)" }}>
        <div className="row items-center justify-between">
          <div className="row items-center gap-3">
            <span className="sm-tag">PRF</span>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 500, letterSpacing: "0.04em", color: "var(--bone)" }}>Training profile</h2>
          </div>
          <div className="row items-center gap-3">
            <Btn variant="ghost">EXPORT JSON</Btn>
            <Btn variant="hot">INITIATE DRILL</Btn>
          </div>
        </div>
      </div>

      <div className="col gap-4 sm-stagger" style={{ padding: "16px 24px 32px", maxWidth: 1280, margin: "0 auto", width: "100%" }}>

        <div className="row gap-3" style={{ flexWrap: "wrap" }}>
          <BigStat value={String(total)}                label="Practice debates" />
          <BigStat value={`${proWins} / ${conWins}`}   label="Wins pro / con" />
          <BigStat value={total > 0 ? ((proWins + conWins) / total).toFixed(2) : "0.00"} label="Resolution rate" hot />
          <BigStat value={(profile.less_practiced_side || "—").toUpperCase()} label="Less-practiced side" />
        </div>

        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          {/* Coach summary */}
          <div className="relative col" style={{ flex: 1.4, minWidth: 380, padding: "18px 20px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Coach summary</h3>
            <p className="bone" style={{ fontSize: 13.5, lineHeight: 1.65, marginTop: 12, maxWidth: 720 }}>
              {profile.coach_summary || "No coaching data yet. Complete a practice debate to receive coach feedback."}
            </p>
            {drills.length > 0 && (
              <React.Fragment>
                <h3 style={{ margin: "22px 0 0", fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Recommendations</h3>
                <div className="col gap-2" style={{ marginTop: 8 }}>
                  {drills.map((d, i) => (
                    <div key={i} className="row items-start gap-3" style={{ padding: "8px 10px", background: "var(--void-3)", border: "0.5px solid var(--hair-2)" }}>
                      <span className="hot" style={{ fontSize: 10, letterSpacing: "0.14em", width: 28, flexShrink: 0 }}>
                        D-{String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="bone" style={{ fontSize: 12 }}>{d}</span>
                    </div>
                  ))}
                </div>
              </React.Fragment>
            )}
          </div>

          {/* Strengths / weaknesses */}
          <div className="relative col" style={{ flex: 1, minWidth: 280, padding: "18px 20px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            {strengths.length > 0 && (
              <React.Fragment>
                <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Strengths</h3>
                <ul className="col gap-2" style={{ margin: "10px 0 18px", padding: 0, listStyle: "none" }}>
                  {strengths.slice(0, 4).map((s, i) => (
                    <li key={i} className="row items-start gap-2" style={{ padding: "6px 0", borderBottom: "0.5px solid var(--hair)" }}>
                      <span className="bone-2" style={{ width: 14 }}>▸</span>
                      <span className="bone" style={{ fontSize: 12 }}>{s}</span>
                    </li>
                  ))}
                </ul>
              </React.Fragment>
            )}
            {weaknesses.length > 0 && (
              <React.Fragment>
                <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--orange)" }}>Improvement targets</h3>
                <ul className="col gap-2" style={{ margin: "10px 0 0", padding: 0, listStyle: "none" }}>
                  {weaknesses.slice(0, 4).map((s, i) => (
                    <li key={i} className="row items-start gap-2" style={{ padding: "6px 0", borderBottom: "0.5px solid var(--hair)" }}>
                      <span className="hot" style={{ width: 14 }}>▲</span>
                      <span className="bone" style={{ fontSize: 12 }}>{s}</span>
                    </li>
                  ))}
                </ul>
              </React.Fragment>
            )}
            {!strengths.length && !weaknesses.length && (
              <span className="mono-mini bone-4" style={{ marginTop: 12 }}>
                No profile data yet. Finish at least one practice debate.
              </span>
            )}
          </div>
        </div>

        {/* Recent drills */}
        {recent.length > 0 && (
          <div className="relative col" style={{ padding: "18px 20px", background: "var(--void-2)", border: "0.5px solid var(--hair)" }}>
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>Recent drills</h3>
            <div className="col" style={{ marginTop: 12 }}>
              {recent.map((d, i) => (
                <div key={i} className="row items-center gap-3" style={{ padding: "10px 0", borderBottom: "0.5px solid var(--hair)" }}>
                  <span className="mono-mini bone-3" style={{ width: 180, flexShrink: 0 }}>
                    {d.started_at ? new Date(d.started_at).toLocaleDateString() : "—"}
                  </span>
                  <span className="bone" style={{ flex: 1, fontSize: 12.5 }}>{d.topic || d.name || "—"}</span>
                  <Tag variant={(d.human_side || "").toLowerCase() === "pro" ? "pro" : "con"}>
                    {(d.human_side || "?").toUpperCase()}
                  </Tag>
                  <Tag>{(d.practice_flow || "FREE").toUpperCase()}</Tag>
                  <Tag variant={d.winner === d.human_side ? "hot" : ""}>
                    {d.winner === "unclear" ? "UNCLEAR"
                      : d.winner === d.human_side ? "WIN" : "LOSS"}
                  </Tag>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

export { GlobalWorkspace };
