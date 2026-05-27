// analytics.jsx — real backend analytics, stepped charts, sparklines
// ----------------------------------------------------------------------

// Map backend analytics shape → local chart shape
function mapAnalytics(data, snapshots) {
  if (!data || !data.ensemble) return null;

  const bayesProb    = data.bayesian?.probabilities || {};
  const proProb      = bayesProb.support || 0;
  const conProb      = bayesProb.oppose  || 0;
  const ensembleVote = data.ensemble.weighted_vote || "mixed";
  const ensembleLeader =
    ensembleVote === "support" ? "PRO" :
    ensembleVote === "oppose"  ? "CON" : "MIXED";
  const bayesLeader  =
    proProb > conProb ? "PRO" :
    conProb > proProb ? "CON" : "MIXED";
  const bayesDelta   = Math.abs(proProb - conProb).toFixed(2);

  // Trend from WS snapshots, or single point from current data
  const trendPoints  = snapshots.length >= 2
    ? snapshots.map(s => s.bayesian?.probabilities?.support || 0.5)
    : [0.48, 0.50, proProb || 0.5];

  // Influence = credibility by role (collapsed to archetype)
  const credByRole = data.credibility?.normalized_by_role || {};
  const influence  = {};
  for (const [role, val] of Object.entries(credByRole)) {
    const archetype = role.replace(/^(pro|con)_/, "").toUpperCase();
    influence[archetype] = ((influence[archetype] || 0) + Number(val)) / (influence[archetype] ? 2 : 1);
  }

  const sc       = data.session_charts || {};
  const winRate  = sc.win_rate_by_team  || { pro: 0, con: 0, unclear: 0, pro_rate: 0, con_rate: 0 };
  const costByPhase  = sc.cost_by_phase || data.cost_by_phase || {};
  const durations    = sc.debate_durations || data.debate_durations || [];

  // Claims
  const claims = (data.argument_mining?.claims || []).map((c, i) => ({
    id:       `k${i}`,
    side:     c.stance === "support" ? "PRO" : "CON",
    strength: c.confidence || 0,
    role:     c.speaker || "DEBATER",
    text:     c.text    || "",
  }));

  return {
    ensembleLeader,
    bayesLeader,
    bayesDelta,
    confidence:   data.confidence?.average  || 0,
    convergence:  data.delphi?.convergence  || 0,
    turnCount:    data.turn_count || 0,
    round:        data.round      || 0,
    trend:        trendPoints,
    bayesian:     { PRO: proProb, CON: conProb },
    influence,
    claims,
    topTerms:     data.attention?.top_terms || [],
    gameTheory: {
      auctionWinner: data.game_theory?.auction_winner || "—",
      winningBid:    data.game_theory?.winning_bid    || 0,
      nashPressure:  data.game_theory?.nash_pressure  || 0,
      nodeCount:     data.argument_graph?.node_count  || 0,
      edgeCount:     data.argument_graph?.edge_count  || 0,
      supportEdges:  data.argument_graph?.support_edges || 0,
      attackEdges:   data.argument_graph?.attack_edges  || 0,
    },
    costByPhase,
    durations,
    winRate,
    evidenceCount:   data.argument_mining?.evidence_count    || 0,
    rebuttalCount:   data.argument_mining?.rebuttal_count    || 0,
    redundancyCount: data.argument_mining?.redundancy_count  || 0,
  };
}

// ── Panel ────────────────────────────────────────────────────────────

function AnalyticsPanel({ analyticsData, analysisSnapshots }) {
  const mapped = useMemo(
    () => mapAnalytics(analyticsData, analysisSnapshots || []),
    [analyticsData, analysisSnapshots]
  );

  if (!mapped) {
    return (
      <div className="col full items-center justify-center" style={{ gap: 12, opacity: 0.45 }}>
        <span className="mono-mini bone-3" style={{ letterSpacing: "0.16em" }}>
          NO ANALYTICS · RUN A DEBATE TO GENERATE DATA
        </span>
      </div>
    );
  }

  const trendIsHot = mapped.ensembleLeader === "PRO";

  return (
    <div className="col full" style={{ overflowY: "auto" }}>
      <AnalyticsHeader mapped={mapped} />

      <div className="col gap-4 sm-stagger" style={{ padding: "20px 24px 32px", maxWidth: 1300, margin: "0 auto", width: "100%" }}>

        {/* KPIs */}
        <div className="row gap-3" style={{ flexWrap: "wrap" }}>
          <KPI label="Ensemble lead"   value={mapped.ensembleLeader}                      hot={trendIsHot}    trend={mapped.trend} />
          <KPI label="Bayesian lead"   value={mapped.bayesLeader}  delta={`Δ ${mapped.bayesDelta}`} trend={mapped.trend} />
          <KPI label="Confidence"      value={mapped.confidence.toFixed(2)} delta="avg" />
          <KPI label="Convergence"     value={mapped.convergence.toFixed(2)} delta={mapped.convergence > 0.6 ? "↑ high" : "↓ low"} />
          <KPI label="Turns"           value={String(mapped.turnCount).padStart(2, "0")} delta={`of r${mapped.round}`} />
        </div>

        {/* Chart row 1 */}
        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          <ChartPanel title="Bayesian lead" flex={1.4}>
            <SteppedBars data={[
              { label: "PRO", value: mapped.bayesian.PRO, hot: false },
              { label: "CON", value: mapped.bayesian.CON, hot: true  },
            ]} />
          </ChartPanel>

          <ChartPanel title="Role influence" flex={1}>
            <BarList data={Object.entries(mapped.influence).map(([k, v]) => ({ label: k, value: v }))} />
          </ChartPanel>

          <ChartPanel title="Stance votes" flex={1}>
            <SteppedBars compact data={[
              { label: "PRO", value: mapped.bayesian.PRO, hot: false },
              { label: "CON", value: mapped.bayesian.CON, hot: true  },
            ]} />
            <div className="row gap-3 items-center" style={{ marginTop: 14, fontSize: 11, color: "var(--bone-3)" }}>
              <span>{mapped.evidenceCount} evidence</span>
              <span className="bone-4">·</span>
              <span>{mapped.rebuttalCount} rebuttal</span>
              <span className="bone-4">·</span>
              <span>{mapped.redundancyCount} redundant</span>
            </div>
          </ChartPanel>
        </div>

        {/* Trend + game theory */}
        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          <ChartPanel title="Lead trend (PRO support probability)" flex={2}>
            <SteppedSparkline data={mapped.trend} />
            <div className="row items-center justify-between" style={{ marginTop: 8, fontSize: 10, letterSpacing: "0.10em", color: "var(--bone-3)" }}>
              {mapped.trend.map((_, i) => <span key={i}>r{i + 1}</span>)}
            </div>
          </ChartPanel>

          <ChartPanel title="Game theory" flex={1}>
            <DList rows={[
              ["Auction winner",  mapped.gameTheory.auctionWinner],
              ["Winning bid",     mapped.gameTheory.winningBid.toFixed(3)],
              ["Nash pressure",   mapped.gameTheory.nashPressure.toFixed(3)],
              ["Arg nodes",       String(mapped.gameTheory.nodeCount)],
              ["Edges (s/a)",     `${mapped.gameTheory.supportEdges}s / ${mapped.gameTheory.attackEdges}a`],
            ]} />
          </ChartPanel>
        </div>

        {/* Claims + key terms */}
        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          <ChartPanel title="Strongest claims" flex={1.6}>
            {mapped.claims.length ? (
              <div className="col gap-2">
                {mapped.claims.map(c => <ClaimRow key={c.id} claim={c} />)}
              </div>
            ) : (
              <span className="mono-mini bone-3">No claims mined yet.</span>
            )}
          </ChartPanel>

          <ChartPanel title="Key terms" flex={1}>
            {mapped.topTerms.length ? (
              <div className="row gap-2" style={{ flexWrap: "wrap" }}>
                {mapped.topTerms.map(t => (
                  <span key={t} style={{
                    fontSize: 11, letterSpacing: "0.02em",
                    padding: "4px 10px", color: "var(--bone-2)",
                    border: "0.5px solid var(--hair-2)", background: "var(--void-3)",
                  }}>
                    {t}
                  </span>
                ))}
              </div>
            ) : (
              <span className="mono-mini bone-3">No key terms yet.</span>
            )}
          </ChartPanel>
        </div>

        {/* Cost + duration + win rate */}
        <div className="row gap-4" style={{ flexWrap: "wrap" }}>
          <ChartPanel title="Cost by phase" flex={1}>
            {Object.keys(mapped.costByPhase).length ? (
              <CostBars data={Object.entries(mapped.costByPhase)} />
            ) : (
              <span className="mono-mini bone-3">No cost data yet.</span>
            )}
          </ChartPanel>

          <ChartPanel title="Debate durations" flex={1}>
            {mapped.durations.length ? (
              <DurationList rows={mapped.durations.map(d => ({
                label:  d.name    || "Debate",
                sec:    Math.round(d.duration_seconds || 0),
                status: (d.status || "complete").toUpperCase(),
              }))} />
            ) : (
              <span className="mono-mini bone-3">No completed debates yet.</span>
            )}
          </ChartPanel>

          <ChartPanel title="Win rate" flex={1}>
            <SteppedBars data={[
              { label: "PRO",     value: mapped.winRate.pro_rate || 0, hot: false },
              { label: "CON",     value: mapped.winRate.con_rate || 0, hot: true  },
              { label: "UNCLEAR", value: mapped.winRate.unclear > 0
                ? mapped.winRate.unclear / Math.max(1, mapped.winRate.total_completed || 1)
                : 0, hot: false, dim: true },
            ]} />
            <div className="row gap-3 items-center" style={{ marginTop: 10, fontSize: 10, color: "var(--bone-3)" }}>
              <span>{mapped.winRate.total_completed || 0} completed</span>
              <span className="bone-4">·</span>
              <span>{mapped.winRate.unclear || 0} unclear</span>
            </div>
          </ChartPanel>
        </div>

      </div>
    </div>
  );
}

function AnalyticsHeader({ mapped }) {
  return (
    <div className="col" style={{ borderBottom: "0.5px solid var(--hair)", padding: "18px 24px 16px", background: "var(--void-2)" }}>
      <div className="row items-center justify-between gap-4">
        <div className="col">
          <div className="row items-center gap-3" style={{ marginBottom: 6 }}>
            <span className="sm-tag sm-tag--hot">ANL · LIVE</span>
            <span className="bone-3 mono-mini">round {mapped.round} · {mapped.turnCount} turns</span>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.005em", margin: 0, color: "var(--bone)" }}>
            Debate intelligence.
          </h1>
        </div>
        <div className="row items-center gap-2">
          <Btn variant="ghost">EXPORT</Btn>
          <Btn>DEEP DIVE</Btn>
        </div>
      </div>
    </div>
  );
}

function KPI({ label, value, delta, hot, trend }) {
  return (
    <div className="relative col" style={{
      padding: "16px 18px 14px", background: "var(--void-2)",
      border: "0.5px solid var(--hair)", minWidth: 180, flex: 1,
    }}>
      <span className="bone-3" style={{ fontSize: 11, letterSpacing: "0.04em" }}>{label}</span>
      <div className="row items-baseline gap-2" style={{ marginTop: 6 }}>
        <span style={{
          fontSize: 28, fontWeight: 500, letterSpacing: "0.02em",
          color: hot ? "var(--orange)" : "var(--bone)",
        }}>{value}</span>
        {delta && <span className="mono-mini bone-3">{delta}</span>}
      </div>
      {trend && trend.length >= 2 && (
        <div style={{ marginTop: 10, height: 24 }}>
          <MiniSpark data={trend} />
        </div>
      )}
    </div>
  );
}

function ChartPanel({ title, flex = 1, children }) {
  return (
    <div className="relative col" style={{
      flex, minWidth: 280, padding: "16px 18px",
      background: "var(--void-2)", border: "0.5px solid var(--hair)",
    }}>
      <h3 style={{ margin: "0 0 14px", fontSize: 13, fontWeight: 500, letterSpacing: "0.02em", color: "var(--bone)" }}>
        {title}
      </h3>
      {children}
    </div>
  );
}

function SteppedBars({ data, compact }) {
  const max = Math.max(...data.map(d => d.value), 0.001);
  return (
    <div className="col gap-2">
      {data.map(d => (
        <div key={d.label} className="col gap-1">
          <div className="row items-center justify-between" style={{ fontSize: 11, letterSpacing: "0.10em" }}>
            <span className={d.hot ? "hot" : "bone"}>{d.label}</span>
            <span className={d.hot ? "hot" : "bone-2"}>{(d.value * 100).toFixed(1)}%</span>
          </div>
          <div className={`sm-bar ${d.hot ? "sm-bar--hot" : ""}`} style={{ height: compact ? 4 : 6 }}>
            <i style={{ "--v": d.value / max }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function BarList({ data }) {
  if (!data.length) return <span className="mono-mini bone-3">No data yet.</span>;
  const max = Math.max(...data.map(d => d.value), 0.001);
  return (
    <div className="col gap-2">
      {data.map(d => (
        <div key={d.label} className="col gap-1">
          <div className="row items-center justify-between" style={{ fontSize: 10, letterSpacing: "0.10em", color: "var(--bone-2)" }}>
            <span>{d.label.replace(/_/g, " ")}</span>
            <span>{(d.value * 100).toFixed(0)}%</span>
          </div>
          <div className="sm-bar"><i style={{ "--v": d.value / max }} /></div>
        </div>
      ))}
    </div>
  );
}

function DList({ rows }) {
  return (
    <dl className="col gap-2" style={{ margin: 0 }}>
      {rows.map(([k, v], i) => (
        <div key={i} className="row items-center justify-between" style={{
          padding: "6px 0", borderBottom: "0.5px solid var(--hair)",
          fontSize: 11, letterSpacing: "0.08em",
        }}>
          <dt className="bone-3">{k}</dt>
          <dd className="bone" style={{ margin: 0 }}>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function ClaimRow({ claim }) {
  return (
    <div className="row items-start gap-3" style={{ padding: "8px 0", borderBottom: "0.5px solid var(--hair)" }}>
      <span style={{
        fontSize: 10, letterSpacing: "0.16em", padding: "2px 6px",
        color: claim.side === "PRO" ? "var(--bone)" : "var(--orange)",
        border: `0.5px solid ${claim.side === "PRO" ? "var(--hair-hot)" : "var(--orange-dim)"}`,
        flexShrink: 0,
      }}>{claim.side}</span>
      <div className="col flex-1" style={{ minWidth: 0 }}>
        <span className="bone" style={{ fontSize: 12, lineHeight: 1.5 }}>{claim.text}</span>
        <div className="row items-center gap-2" style={{ marginTop: 4 }}>
          <span className="mono-mini bone-3">{claim.role.replace(/_/g, " ")}</span>
          <span style={{ flex: 1, height: 2, background: "var(--void-4)", maxWidth: 80 }}>
            <i style={{ display: "block", height: "100%", width: `${claim.strength * 100}%`, background: claim.side === "PRO" ? "var(--bone-2)" : "var(--orange)" }} />
          </span>
          <span className="mono-mini" style={{ color: claim.side === "PRO" ? "var(--bone-2)" : "var(--orange)" }}>
            {claim.strength.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}

function CostBars({ data }) {
  const max = Math.max(...data.map(([, v]) => v), 0.001);
  return (
    <div className="col gap-2">
      {data.map(([k, v]) => (
        <div key={k} className="col gap-1">
          <div className="row items-center justify-between" style={{ fontSize: 10, letterSpacing: "0.12em" }}>
            <span className="bone-2">{k}</span>
            <span className="bone">${Number(v).toFixed(4)}</span>
          </div>
          <div className={`sm-bar ${k === "Rebuttal" ? "sm-bar--hot" : ""}`}>
            <i style={{ "--v": max ? v / max : 0 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function DurationList({ rows }) {
  const max = Math.max(...rows.map(r => r.sec), 1);
  return (
    <div className="col gap-2">
      {rows.map((r, i) => {
        const mm = String(Math.floor(r.sec / 60)).padStart(2, "0");
        const ss = String(r.sec % 60).padStart(2, "0");
        return (
          <div key={i} className="col gap-1">
            <div className="row items-center justify-between" style={{ fontSize: 10, letterSpacing: "0.06em" }}>
              <span className="bone truncate" style={{ flex: 1, marginRight: 8 }}>{r.label}</span>
              <span className="mono-mini bone-2">{mm}:{ss}</span>
              <span className={`mono-mini ${r.status === "RUNNING" ? "hot" : "bone-3"}`} style={{ marginLeft: 8 }}>
                {r.status}
              </span>
            </div>
            <div className={`sm-bar ${r.status === "RUNNING" ? "sm-bar--hot" : ""}`}>
              <i style={{ "--v": r.sec / max }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Stepped sparkline
function SteppedSparkline({ data }) {
  const width = 600, height = 100;
  if (!data || data.length < 2) return null;
  const dx   = width / (data.length - 1);
  const max  = Math.max(...data, 0.7);
  const min  = Math.min(...data, 0.3);
  const range= Math.max(0.001, max - min);
  let d = "";
  data.forEach((v, i) => {
    const x = i * dx;
    const y = height - ((v - min) / range) * (height - 16) - 8;
    if (i === 0) d += `M ${x} ${y}`;
    else {
      const px = (i - 1) * dx;
      d += ` L ${px + dx * 0.5} ${y} L ${x} ${y}`;
    }
  });
  const lastIdx = data.length - 1;
  const lastX   = lastIdx * dx;
  const lastY   = height - ((data[lastIdx] - min) / range) * (height - 16) - 8;
  return (
    <svg className="sm-spark" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ height: 100 }}>
      <line x1="0" y1={height / 2} x2={width} y2={height / 2} stroke="var(--hair)" strokeDasharray="2 4" />
      <path d={`${d} L ${lastX} ${height} L 0 ${height} Z`} fill="rgba(232,230,223,0.04)" />
      <path d={d} stroke="var(--bone)" strokeWidth="0.8" fill="none" />
      <circle cx={lastX} cy={lastY} r="2.5" fill="var(--orange)" />
      <circle cx={lastX} cy={lastY} r="6"   fill="none" stroke="var(--orange)" strokeWidth="0.5" opacity="0.4" />
    </svg>
  );
}

// Mini sparkline for KPI cards
function MiniSpark({ data }) {
  const width = 160, height = 24;
  if (!data || data.length < 2) return null;
  const dx   = width / (data.length - 1);
  const max  = Math.max(...data);
  const min  = Math.min(...data);
  const range= Math.max(0.001, max - min);
  let d = "";
  data.forEach((v, i) => {
    const x = i * dx;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    if (i === 0) d += `M ${x} ${y}`;
    else {
      const px = (i - 1) * dx;
      d += ` L ${px + dx * 0.5} ${y} L ${x} ${y}`;
    }
  });
  const lastX = (data.length - 1) * dx;
  const lastY = height - ((data[data.length - 1] - min) / range) * (height - 4) - 2;
  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ width: "100%", height: 24 }}>
      <path d={d} stroke="var(--bone-2)" strokeWidth="1" fill="none" />
      <circle cx={lastX} cy={lastY} r="1.5" fill="var(--orange)" />
    </svg>
  );
}

Object.assign(window, { AnalyticsPanel });
