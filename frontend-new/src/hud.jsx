// hud.jsx — shared HUD primitives
// ----------------------------------------------------------------------

import React, { useState, useEffect, useRef, useMemo, useCallback, createContext, useContext } from 'react';

// Registration marks in the four corners. async pulse periods so it never feels mechanical.
function RegMarks({ active = false }) {
  return (
    <React.Fragment>
      <span aria-hidden="true" className="sm-reg tl sm-reg-pulse" style={{ "--reg-period": "6.3s" }}>┌</span>
      <span aria-hidden="true" className="sm-reg tr sm-reg-pulse" style={{ "--reg-period": "7.7s" }}>┐</span>
      <span aria-hidden="true" className="sm-reg bl sm-reg-pulse" style={{ "--reg-period": "8.1s" }}>└</span>
      <span aria-hidden="true" className="sm-reg br sm-reg-pulse" style={{ "--reg-period": "6.9s" }}>┘</span>
    </React.Fragment>
  );
}

// Panel — the silhouette of the entire app: clipped corners + hairline + scanning border when active.
function Panel({ children, className = "", size = "", active = false, reg = true, style }) {
  const cls = ["sm-panel", size ? `sm-panel--${size}` : "", active ? "sm-panel--active" : "", className]
    .filter(Boolean).join(" ");
  return (
    <div className={cls} style={style}>
      {reg ? <RegMarks /> : null}
      {children}
    </div>
  );
}

// Glitch — sparse character-cycle on a label (~once per 30s).
function Glitch({ text, period = 30000 }) {
  const ref = useRef(null);
  const [glitched, setGlitched] = useState(text);
  useEffect(() => {
    const symbols = "▓▒░█▌▐▄▀◊◈⌬⌭⏚⎈⌷⌸⌹⌺⌻";
    let mounted = true;
    const tick = () => {
      if (!mounted) return;
      const wait = period * (0.7 + Math.random() * 0.6);
      setTimeout(() => {
        if (!mounted || !ref.current) return;
        ref.current.classList.add("cycling");
        let i = 0;
        const cycle = setInterval(() => {
          const arr = text.split("").map((ch, idx) => {
            if (ch === " ") return " ";
            if (Math.random() < 0.3 && i < 3) return symbols[Math.floor(Math.random() * symbols.length)];
            return ch;
          });
          setGlitched(arr.join(""));
          i++;
          if (i > 3) {
            clearInterval(cycle);
            setGlitched(text);
            ref.current && ref.current.classList.remove("cycling");
            tick();
          }
        }, 60);
      }, wait);
    };
    tick();
    return () => { mounted = false; };
  }, [text, period]);
  return <span ref={ref} className="sm-glitch" data-glitch={glitched}>{glitched}</span>;
}

// Signal strength glyph
function Sig({ pct = 98 }) {
  return (
    <span className="sm-sig" title={`SIG ${pct}%`}>
      <i /><i /><i /><i />
    </span>
  );
}

// Tag chip
function Tag({ children, variant = "" }) {
  return <span className={`sm-tag ${variant ? `sm-tag--${variant}` : ""}`}>{children}</span>;
}

// Label
function Label({ children, variant = "" }) {
  return <span className={`sm-label ${variant ? `sm-label--${variant}` : ""}`}>{children}</span>;
}

// Button
function Btn({ children, variant = "", onClick, disabled, style }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`sm-btn ${variant ? `sm-btn--${variant}` : ""}`}
      style={style}
    >
      {children}
    </button>
  );
}

// CRT panel transition — wraps a key. On key change, runs collapse-out → mount lines → reveal.
// First mount renders children without animation so screenshots and initial paint are clean.
function CRTSwitch({ k, children, mountLines = [] }) {
  const [phase, setPhase] = useState({ k, stage: "idle", lines: mountLines });
  const firstRun = useRef(true);
  useEffect(() => {
    if (firstRun.current) { firstRun.current = false; return; }
    if (k === phase.k) return;
    setPhase((p) => ({ ...p, stage: "out" }));
    const t1 = setTimeout(() => setPhase({ k, stage: "boot", lines: mountLines }), 200);
    const t2 = setTimeout(() => setPhase({ k, stage: "in", lines: mountLines }), 280);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [k]);
  if (phase.stage === "out") {
    return <div className="sm-crt-out full">{/* leaving */}</div>;
  }
  if (phase.stage === "boot") {
    return (
      <div className="col gap-1 full" style={{ padding: 16, justifyContent: "center" }}>
        {phase.lines.map((l, i) => (
          <div key={i} className="sm-mount-line" style={{ animationDelay: `${i * 60}ms` }}>
            MOUNT: {l} OK
          </div>
        ))}
      </div>
    );
  }
  if (phase.stage === "in") {
    return <div className="sm-crt-in full">{children}</div>;
  }
  // idle — first mount, no animation
  return <div className="full">{children}</div>;
}

// Live UTC clock + T+ timer
function LiveClock({ since }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  const utc = new Date(now);
  const hh = String(utc.getUTCHours()).padStart(2, "0");
  const mm = String(utc.getUTCMinutes()).padStart(2, "0");
  const ss = String(utc.getUTCSeconds()).padStart(2, "0");
  const delta = since ? Math.max(0, Math.floor((now - since) / 1000)) : 0;
  const dh = String(Math.floor(delta / 3600)).padStart(2, "0");
  const dm = String(Math.floor((delta % 3600) / 60)).padStart(2, "0");
  const ds = String(delta % 60).padStart(2, "0");
  return (
    <span className="mono-mini bone-2">
      UTC {hh}:{mm}:{ss}{since ? ` · T+${dh}:${dm}:${ds}` : ""}
    </span>
  );
}

// Wireframe globe — slow rotating topo, bottom-right corner ambient.
function Globe() {
  return (
    <div className="sm-globe" aria-hidden="true">
      <svg viewBox="-180 -180 360 360">
        <g className="rot">
          {/* graticule */}
          <circle cx="0" cy="0" r="160" fill="none" stroke="var(--bone)" strokeWidth="0.5" opacity="0.6" />
          <circle cx="0" cy="0" r="160" fill="none" stroke="var(--orange)" strokeWidth="0.5" opacity="0.4" strokeDasharray="2 4" />
          {[20, 40, 60, 80, 100, 120, 140].map((r) => (
            <ellipse key={r} cx="0" cy="0" rx={r} ry="160" fill="none" stroke="var(--bone)" strokeWidth="0.3" opacity="0.4" />
          ))}
          {[-120, -80, -40, 0, 40, 80, 120].map((y) => {
            const rx = Math.sqrt(Math.max(0, 160 * 160 - y * y));
            return <ellipse key={y} cx="0" cy={y} rx={rx} ry={rx * 0.18} fill="none" stroke="var(--bone)" strokeWidth="0.3" opacity="0.35" />;
          })}
          {/* contour blobs (faux topography) */}
          {Array.from({ length: 14 }, (_, i) => {
            const a = (i / 14) * Math.PI * 2;
            const r = 60 + Math.sin(i * 3) * 30;
            const cx = Math.cos(a) * r;
            const cy = Math.sin(a) * r * 0.7;
            return (
              <g key={i}>
                <circle cx={cx} cy={cy} r={6 + (i % 4) * 2} fill="none" stroke="var(--bone)" strokeWidth="0.4" opacity="0.5" />
                <circle cx={cx} cy={cy} r={10 + (i % 4) * 2} fill="none" stroke="var(--bone)" strokeWidth="0.3" opacity="0.3" />
              </g>
            );
          })}
          {/* hot pings */}
          <circle cx="-40" cy="20"  r="2" fill="var(--orange)" />
          <circle cx="80"  cy="-50" r="2" fill="var(--orange)" />
          <circle cx="-100" cy="-30" r="1.5" fill="var(--bone)" />
        </g>
      </svg>
    </div>
  );
}

// Status ticker bar
function StatusTicker({ items }) {
  const doubled = [...items, ...items];
  return (
    <div className="relative" style={{ overflow: "hidden", height: 22 }}>
      <div className="sm-ticker-row mono-mini bone-3" style={{ position: "absolute", inset: 0, alignItems: "center", padding: "0 12px" }}>
        {doubled.map((t, i) => (
          <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
            <span className="hot">▸</span>
            <span>{t}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export { RegMarks, Panel, Glitch, Sig, Tag, Label, Btn, CRTSwitch, LiveClock, Globe, StatusTicker };
