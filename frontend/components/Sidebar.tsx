"use client";

import { motion, AnimatePresence } from "framer-motion";
import type { ChatSession } from "@/types";

export type SidebarWorkspaceView =
  | "session"
  | "aiExperiences"
  | "userProfile"
  | "councilSettings";

type SidebarProps = {
  sessions: ChatSession[];
  selectedId: string | null;
  maxSessions: number;
  workspaceView: SidebarWorkspaceView;
  onNew: () => void;
  onDeleteAll: () => void;
  onSelect: (id: string) => void;
  onHome: () => void;
  onAiExperiences: () => void;
  onUserProfile: () => void;
  onCouncilSettings: () => void;
};

export function Sidebar({
  sessions,
  selectedId,
  maxSessions,
  workspaceView,
  onNew,
  onDeleteAll,
  onSelect,
  onHome,
  onAiExperiences,
  onUserProfile,
  onCouncilSettings,
}: SidebarProps) {
  const limitReached = sessions.length >= maxSessions;
  const aiSessions = sessions.filter((session) => session.mode !== "ai_vs_human");
  const practiceSessions = sessions.filter((session) => session.mode === "ai_vs_human");

  return (
    <aside
      className="flex h-full w-full flex-col md:w-80"
      style={{
        background: "var(--sm-bg-secondary)",
        borderRight: "1px solid var(--sm-border)"
      }}
    >
      {/* ── Brand Header ── */}
      <div className="electron-drag p-4" style={{ borderBottom: "1px solid var(--sm-border)" }}>
        <div
          className="sm-glass-card sm-animated-border mb-3 p-4"
          style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.05), rgba(6,182,212,0.03))" }}
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span className="sm-orb" />
            <p className="text-[10px] font-bold uppercase tracking-[0.15em] sm-gradient-text">
              Strategic Intelligence
            </p>
          </div>
          <p className="text-[12px] leading-5" style={{ color: "var(--sm-text-secondary)" }}>
            Train reasoning, orchestrate AI debates, and track analytics.
          </p>
        </div>
        <div className="flex items-center justify-between gap-3">
          <div>
            <button 
              onClick={onHome}
              className="text-left transition-opacity hover:opacity-80"
              title="Go to Dashboard"
            >
              <h1 className="font-display text-lg font-bold" style={{ color: "var(--sm-text-primary)" }}>
                Yojaka
              </h1>
            </button>
            <p className="text-xs" style={{ color: "var(--sm-text-tertiary)" }}>
              {sessions.length}/{maxSessions} sessions
            </p>
          </div>
          <button
            type="button"
            onClick={onNew}
            disabled={limitReached}
            className="sm-btn sm-btn-primary"
            style={{ padding: "8px 16px", fontSize: "0.8rem" }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="7" y1="2" x2="7" y2="12" /><line x1="2" y1="7" x2="12" y2="7" />
            </svg>
            New
          </button>
        </div>
        {sessions.length > 0 ? (
          <button
            type="button"
            onClick={onDeleteAll}
            className="sm-btn sm-btn-ghost mt-3 w-full text-xs"
            style={{ color: "var(--sm-accent-con-light)", justifyContent: "flex-start" }}
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <path d="M2 3h8M4.5 3V2a.5.5 0 01.5-.5h2a.5.5 0 01.5.5v1M9.5 3l-.4 6.5a1 1 0 01-1 .9H3.9a1 1 0 01-1-.9L2.5 3" />
            </svg>
            Clear All Sessions
          </button>
        ) : null}
        {limitReached ? (
          <p className="mt-2 text-xs" style={{ color: "var(--sm-accent-con-light)" }}>
            Delete a session before creating another.
          </p>
        ) : null}
      </div>

      {/* ── Session List ── */}
      <nav className="min-h-0 flex-1 overflow-y-auto p-3">
        <div className="mb-4">
          <SidebarNavButton
            label="Home Dashboard"
            icon={<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M2.5 7.5L8 2.5l5.5 5v6H10v-4H6v4H2.5z"/></svg>}
            active={workspaceView === "session" && selectedId === null}
            onClick={onHome}
          />
        </div>

        {sessions.length === 0 && workspaceView === "session" && selectedId !== null ? (
          <p className="px-2 py-6 text-center text-sm" style={{ color: "var(--sm-text-muted)" }}>
            Create a session to begin.
          </p>
        ) : null}

        <SessionGroup
          title="AI vs AI — Council Lab"
          icon="⚡"
          sessions={aiSessions}
          selectedId={workspaceView === "session" ? selectedId : null}
          onSelect={onSelect}
        />
        <SessionGroup
          title="AI vs Human — Training"
          icon="🎯"
          sessions={practiceSessions}
          selectedId={workspaceView === "session" ? selectedId : null}
          onSelect={onSelect}
        />

        {/* ── Global Intelligence ── */}
        <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--sm-border)" }}>
          <p
            className="mb-2 px-2 text-[10px] font-bold uppercase tracking-[0.15em]"
            style={{ color: "var(--sm-text-muted)" }}
          >
            Intelligence Hub
          </p>
          <div className="space-y-1">
            <SidebarNavButton
              label="Agent Memory"
              icon={<NeuronIcon />}
              active={workspaceView === "aiExperiences"}
              onClick={onAiExperiences}
            />
            <SidebarNavButton
              label="Training Profile"
              icon={<ChartIcon />}
              active={workspaceView === "userProfile"}
              onClick={onUserProfile}
            />
          </div>
        </div>
      </nav>

      {/* ── Settings Footer ── */}
      <div className="p-3" style={{ borderTop: "1px solid var(--sm-border)" }}>
        <SidebarNavButton
          label="System Settings"
          icon={<GearIcon />}
          active={workspaceView === "councilSettings"}
          onClick={onCouncilSettings}
        />
      </div>
    </aside>
  );
}

/* ─── Sub-components ─── */

function SidebarNavButton({
  label,
  icon,
  active,
  onClick
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-semibold transition-all duration-300 ${active ? 'sm-glass-card' : 'hover:bg-[rgba(255,255,255,0.02)]'}`}
      style={{
        background: active
          ? "linear-gradient(135deg, rgba(99,102,241,0.15), rgba(6,182,212,0.08))"
          : "transparent",
        color: active ? "var(--sm-accent-indigo-light)" : "var(--sm-text-secondary)",
        borderColor: active ? "rgba(99,102,241,0.3)" : "transparent"
      }}
    >
      <div className={`transition-transform duration-300 ${active ? 'scale-110' : 'group-hover:scale-110 group-hover:text-[var(--sm-text-primary)]'}`}>
        {icon}
      </div>
      <span className={`transition-colors duration-300 ${!active && 'group-hover:text-[var(--sm-text-primary)]'}`}>{label}</span>
      {active ? (
        <span
          className="ml-auto h-2 w-2 rounded-full sm-animate-pulse-glow"
          style={{ background: "var(--sm-accent-indigo)", boxShadow: "0 0 8px var(--sm-accent-indigo)" }}
        />
      ) : null}
    </button>
  );
}

function SessionGroup({
  title,
  icon,
  sessions,
  selectedId,
  onSelect
}: {
  title: string;
  icon: string;
  sessions: ChatSession[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  if (sessions.length === 0) {
    return null;
  }
  return (
    <div className="mb-4">
      <p
        className="mb-2 flex items-center gap-2 px-2 text-[10px] font-bold uppercase tracking-[0.15em]"
        style={{ color: "var(--sm-text-muted)" }}
      >
        <span>{icon}</span>
        {title}
      </p>
      <div className="space-y-1">
        <AnimatePresence mode="popLayout">
          {sessions.map((session) => {
            const selected = selectedId === session.id;
            return (
              <motion.div
                key={session.id}
                layout
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.2 }}
              >
                <button
                  type="button"
                  onClick={() => onSelect(session.id)}
                  className={`group block w-full truncate rounded-xl px-3 py-3 text-left text-sm font-medium transition-all duration-300 ${selected ? 'sm-glass-card' : 'hover:bg-[rgba(255,255,255,0.02)] hover:translate-x-1'}`}
                  style={{
                    background: selected
                      ? "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(6,182,212,0.06))"
                      : "transparent",
                    color: selected ? "var(--sm-text-primary)" : "var(--sm-text-secondary)",
                    borderColor: selected ? "rgba(99,102,241,0.2)" : "transparent",
                  }}
                  title={session.name}
                >
                  <span className={`transition-colors duration-300 ${!selected && 'group-hover:text-[var(--sm-text-primary)]'}`}>
                    {session.name}
                  </span>
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}

/* ─── Icons ─── */

function NeuronIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="3" />
      <line x1="8" y1="1" x2="8" y2="5" />
      <line x1="8" y1="11" x2="8" y2="15" />
      <line x1="1" y1="8" x2="5" y2="8" />
      <line x1="11" y1="8" x2="15" y2="8" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <line x1="4" y1="14" x2="4" y2="8" />
      <line x1="8" y1="14" x2="8" y2="4" />
      <line x1="12" y1="14" x2="12" y2="6" />
    </svg>
  );
}

function GearIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="2.5" />
      <path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.2 3.2l1.4 1.4M11.4 11.4l1.4 1.4M3.2 12.8l1.4-1.4M11.4 4.6l1.4-1.4" />
    </svg>
  );
}
