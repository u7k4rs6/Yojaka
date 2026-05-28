# Yojaka — Full Feature Reference

> **Debate Intelligence Terminal** · Multi-agent AI debate platform with real-time streaming, analytics, and practice coaching.

---

## Table of Contents

1. [Debate Modes](#1-debate-modes)
2. [Agent Roles](#2-agent-roles)
3. [Debate Flow Phases](#3-debate-flow-phases)
4. [Settings & Configuration](#4-settings--configuration)
5. [WebSocket Events](#5-websocket-events)
6. [REST API Endpoints](#6-rest-api-endpoints)
7. [Analytics Engine](#7-analytics-engine)
8. [Team Intelligence (Team Rooms)](#8-team-intelligence-team-rooms)
9. [Model Support](#9-model-support)
10. [Cost Tracking](#10-cost-tracking)
11. [Budget & Efficiency Controls](#11-budget--efficiency-controls)
12. [Safety Lock](#12-safety-lock)
13. [Practice Mode & User Profile](#13-practice-mode--user-profile)
14. [Multi-Session Support](#14-multi-session-support)
15. [UI Panels](#15-ui-panels)
16. [Runtime Observability](#16-runtime-observability)

---

## 1. Debate Modes

### AI vs AI (`ai_vs_ai`)
Full adversarial structured debate between two AI teams. No human input after the topic is dispatched.

- Pro and Con teams, each with 1–4 configurable agents
- Structured phase flow (constructive → cross-exam → evidence → discussion → closing → judgment)
- Parallel phase execution where logically independent (both teams run concurrently)
- Private team notebook preparation before the public debate starts
- Real-time streaming transcript
- Final verdict from a judge (or panel of 3/5)

### AI vs Human — Practice Mode (`ai_vs_human`)
Human debates against a single AI Practice Debater. Designed for training.

- Human picks a side (or Auto-balances based on profile)
- Free-form or structured rounds (1–12 turns)
- AI adapts difficulty: Adaptive, Beginner, Normal, Hard
- After the final round: Judge issues verdict, Trainer provides coaching
- User debate profile updated with strengths, weaknesses, trainer notes
- Can end early (`end_practice_debate`)

### Council Assistant Chat
Single-turn Q&A with the Council Assistant agent. Triggered when intent classifier routes input as a question/command rather than a debatable proposition.

- Context-aware: reads recent session history
- Redirects unsafe requests through the Safety Lock
- Tracked as a `chat` mode interaction

---

## 2. Agent Roles

### Team Debaters (appear on Pro and Con sides)

| Archetype | Label | Min Debaters Per Team | Job |
|---|---|---|---|
| `lead_advocate` | Advocate | 1 | Build the team's central case, maintain thesis coherence |
| `rebuttal_critic` | Rebuttal Critic | 2 | Attack opposing team's strongest point, shield own team |
| `evidence_researcher` | Evidence Researcher | 3 | Add evidence, examples, uncertainty notes; supports web search |
| `cross_examiner` | Cross-Examiner | 4 | Ask Socratic pressure questions, expose contradictions |

### Neutral / System Roles

| Role | Trigger | Job |
|---|---|---|
| `judge` | Every debate | Final verdict using Bayesian aggregation + analytics weighting |
| `judge_assistant` | When enabled | Pre-judgment audit: missed points, evidence gaps, scoring risks |
| `council_assistant` | Chat intent or safety redirect | General Q&A with session context |
| `practice_debater` | Practice mode | AI opponent; difficulty adapts to user profile |
| `debate_trainer` | After practice debate ends | Coaching feedback: strengths, weaknesses, trainer notes |

### Model Auto-Assignment (Slot System)
When no per-agent model is set, the system distributes across providers automatically:

- **Slot 0** (Judge, Council Assistant, Practice Debater, Trainer) → user's primary model
- **Slot 1** (Pro team) → second available provider
- **Slot 2** (Con team) → third available provider

This ensures pro/con/judge each use a different provider when possible.

---

## 3. Debate Flow Phases

Phases execute in order. Pairs in **bold** are run in parallel (via `asyncio.gather`).

### 1-Debater Flow (Advocate only)
1. Pro Constructive
2. Con Constructive
3. Con Cross-examines Pro
4. Pro Answers + Rebuttal
5. Pro Cross-examines Con
6. Con Answers + Rebuttal
7. Open Discussion (alternating, `debate_rounds` × 2 turns)
8. Pro Closing · Con Closing *(parallel)*
9. [Judge Assistant Audit] *(if enabled)*
10. Final Judgment

### 2-Debater Flow (adds Rebuttal Critic)
1. Pro Constructive
2. Con Critic cross-examines Pro Advocate
3. Con Constructive
4. Pro Critic cross-examines Con Advocate
5. Discussion Round 1 (alternating messages)
6. **Pro Critic Rebuttal · Con Critic Rebuttal** *(parallel)*
7. Discussion Rounds 2…N (one per extra `debate_rounds`)
8. **Pro Closing · Con Closing** *(parallel)*
9. [Judge Assistant Audit]
10. Final Judgment

### 3-Debater Flow (adds Evidence Researcher)
Extends 2-Debater flow with:
- **Pro Researcher Evidence · Con Researcher Evidence** *(parallel, after constructives)*

### 4-Debater Flow (adds Cross-Examiner)
Extends 3-Debater flow with:
- **Con Examiner cross-examines Pro Advocate · Pro Examiner cross-examines Con Advocate** *(parallel)*
- **Con Examiner cross-examines Pro Researcher · Pro Examiner cross-examines Con Researcher** *(parallel)*

### Early Exit Triggers
- **Consensus detected**: after ≥2 discussion/rebuttal turns, cheapest available model checks `YES/NO` — debate skips to judgment
- **Budget exhausted**: session token count hits `session_token_budget` cap — skips remaining phases, goes to judgment
- Both emit an `early_stop` WebSocket event with `reason` and `tokens_used`

---

## 4. Settings & Configuration

### Session Settings (per chat session)

**Debate Structure**
| Key | Default | Range | Effect |
|---|---|---|---|
| `debaters_per_team` | 1 | 1–4 | Controls which agent roles are active |
| `debate_rounds` | 1 | 1–6 | Number of discussion/rebuttal rounds |
| `discussion_messages_per_team` | 2 | 1–4 | Messages per team per discussion round |

**Inference**
| Key | Default | Notes |
|---|---|---|
| `overall_model` | — | Primary model name |
| `temperature` | 0.55 | 0.0–1.0 |
| `max_tokens` | 400 | Per agent turn (env: `MAX_AGENT_OUTPUT_TOKENS`) |
| `response_length` | Normal | Concise / Normal / Detailed |
| `context_window` | 2 | 0–6 recent turns in context |

**Behavior**
| Key | Default |
|---|---|
| `debate_tone` | Academic |
| `language` | English |
| `evidence_strictness` | Normal |
| `fact_check_mode` | false |
| `judge_assistant_enabled` | false |

**Display**
| Key | Default |
|---|---|
| `auto_scroll` | true |
| `show_timestamps` | true |
| `show_token_count` | true |
| `show_money_cost` | true |
| `show_model_costs` | false |
| `show_every_message_cost_in_debate` | false |
| `cost_currency` | USD |

**Experience / Memory**
| Key | Default |
|---|---|
| `use_experience` | true |

**Practice Mode**
| Key | Default | Options |
|---|---|---|
| `human_side` | Auto | Auto / Pro / Con |
| `practice_flow` | Free | Free / Structured |
| `structured_rounds` | 3 | 1–12 |
| `use_user_profile` | true | — |
| `trainer_style` | Coach | Coach / Direct / Gentle / Examiner |
| `training_focus` | Full Debate | Full Debate / Rebuttal / Evidence / Clarity / Cross-Examination |
| `opponent_difficulty` | Adaptive | Adaptive / Beginner / Normal / Hard |

**Judging**
| Key | Default | Options |
|---|---|---|
| `judge_panel_size` | 1 | 1 / 3 / 5 |
| `analytics_weight` | 0.25 | 0.0–0.75 |
| `allow_verdict_challenge` | true | — |

### Per-Agent Settings (`agent_settings.<archetype>`)
Each archetype can override session-level values:
- `model` — specific model name
- `temperature` — 0.0–1.0
- `max_tokens` — output cap
- `response_length` — Concise / Normal / Detailed
- `web_search` — true/false (evidence_researcher only)

### Council Settings (global, shared across sessions)

| Key | Default | Notes |
|---|---|---|
| `universal_experience` | true | Agents learn across all sessions |
| `use_agent_identity_profiles` | true | Agents use persistent identity |
| `use_user_debate_profile` | true | Practice adapts to user history |
| `debate_intelligence_depth` | Light | Light (no API) / Normal / Deep |
| `use_value_consequence_system` | false | Value-argument weighting |
| `default_judge_mode` | Debate Performance | Debate Performance / Truth-Seeking / Hybrid |
| `theme` | System | Light / Dark / System |

---

## 5. WebSocket Events

### Client → Server

| Type | Payload | When |
|---|---|---|
| `start_debate` | `{topic, model}` | Dispatch a new AI vs AI debate |
| `start_interaction` | `{topic, model, practice_side?}` | General message (routed by intent) |
| `end_practice_debate` | `{model}` | Force-end an active practice debate |

### Server → Client

**Debate Lifecycle**

| Type | Key Payload Fields |
|---|---|
| `debate_started` | `debate`, `topic`, `positions`, `selected_model`, `assignments`, `judge`, `active_debates` |
| `team_preparation_started` | `debate_id`, `message` |
| `team_preparation_completed` | `debate_id`, `message` |
| `message_started` | `stream_id`, `message` (empty body), `round` |
| `message_chunk` | `stream_id`, `delta` |
| `message_completed` | `stream_id`, `message` (full body + cost) |
| `analysis_updated` | `round`, `analysis` (full analytics payload) |
| `early_stop` | `reason`, `tokens_used`, `debate_id` |
| `debate_completed` | `debate_id`, `judge_summary`, `active_debates`, `cost_summary` |

**Chat**

| Type | Key Fields |
|---|---|
| `interaction_started` | `mode`, `debate`, `selected_model` |
| `interaction_completed` | `mode`, `debate_id`, `cost_summary` |

**Practice Mode**

| Type | Key Fields |
|---|---|
| `practice_started` | `debate`, `state`, `selected_model` |
| `practice_state_updated` | `state` (includes `ending: true` when finalizing) |
| `practice_completed` | `debate_id`, `profile` (updated user profile), `cost_summary` |

**Errors**

| Type | Fields |
|---|---|
| `error` | `message` |

---

## 6. REST API Endpoints

### System

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Status, DB path, active debate count |
| `GET` | `/api/models` | Available models, providers, mock mode |

### Sessions

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions` | List all sessions |
| `POST` | `/api/sessions` | Create session (`name`, `mode`, `settings`) |
| `DELETE` | `/api/sessions` | Delete all sessions |
| `PATCH` | `/api/sessions/{id}` | Rename session |
| `DELETE` | `/api/sessions/{id}` | Delete single session |
| `POST` | `/api/sessions/{id}/clear-history` | Hide all messages/debates (reversible) |
| `POST` | `/api/sessions/{id}/clear-memory` | Delete all session data (irreversible) |

### Settings

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions/{id}/settings` | Get session settings |
| `PATCH` | `/api/sessions/{id}/settings` | Update session settings |
| `GET` | `/api/council-settings` | Get global council settings |
| `PATCH` | `/api/council-settings` | Update council settings |
| `POST` | `/api/council-settings/reset-agent-experience` | Reset universal agent memory (requires `"RESET COUNCIL IDENTITIES"` confirmation) |

### Messages & Debates

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions/{id}/messages` | All messages in session |
| `GET` | `/api/sessions/{id}/debates` | All debate records |
| `PATCH` | `/api/sessions/{id}/debates/{did}` | Rename a debate |
| `DELETE` | `/api/sessions/{id}/debates/{did}` | Hide debate from stats |
| `GET` | `/api/sessions/{id}/practice-state` | Current practice debate state |

### Analytics & Intelligence

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sessions/{id}/analytics` | Full analytics payload for session |
| `GET` | `/api/sessions/{id}/intelligence` | Intelligence records (claims, evidence, etc.) |
| `POST` | `/api/sessions/{id}/debates/{did}/feedback` | Submit 3-question post-debate feedback |
| `POST` | `/api/sessions/{id}/debates/{did}/verdict-review` | Challenge or override verdict |

### User Profile & Agent Memory

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/user-debate-profile` | Raw user debate profile |
| `GET` | `/api/user-debate-profile/overview` | Profile + recent debates + recommendations |
| `POST` | `/api/user-debate-profile/reset` | Reset profile (requires `"RESET USER DEBATE PROFILE"`) |
| `GET` | `/api/ai-debater-experiences` | All agent experience records |

### Observability

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/runtime-diary` | Log an event to the backend terminal |

### WebSocket

| Path | Description |
|---|---|
| `WS /ws/debates/{session_id}` | Main debate stream for a session |

---

## 7. Analytics Engine

### Per-Turn Metrics
- **Confidence** — derived from sentence length, certainty markers, evidence keywords
- **Novelty** — Jaccard similarity against prior turns (lower overlap = higher novelty)
- **Credibility** — ELO-style rating normalized to 0.2–1.25 based on historical performance
- **Stance** — Support / Oppose / Mixed, detected via keyword sets + role bias

### Ensemble Voting
- Majority vote across all speakers
- Weighted vote: `confidence × novelty × credibility × role_weight`
- Winner: highest weighted score with a minimum threshold

### Bayesian Aggregation
- Tracks support / oppose / mixed probability distribution per speaker
- Updates per turn, outputs final probability triple

### Argument Analysis
- **Claims extraction**: split sentences → filter stop words → rank by confidence
- **Evidence detection**: markers like `because`, `data`, `study`, `research`, `observed`
- **Rebuttal detection**: markers like `however`, `flaw`, `counter`, `risk`, `unless`
- **Argument graph**: nodes = claims, directed edges = supports/attacks based on stance
- **Strongest claims**: ranked by `confidence × novelty × credibility`

### Delphi Convergence
- Tracks stance distribution round by round
- Measures how much the debate opinion stabilizes over time

### Game Theory
- **Auction winner**: speaker with highest `confidence × novelty × credibility` bid
- **Nash pressure**: `1 - ((leader_bid - second_bid) / total_bids)` — how contested the lead is

### Mixture of Experts (MoE)
Per-role weights shift based on detected topic keywords:
- Evidence/data topics → evidence_researcher boosted
- Risk/safety topics → rebuttal_critic boosted
- Policy/law topics → lead_advocate boosted
- Assumptions/counterfactuals → cross_examiner boosted

### Session Charts
- **Win rate** — Pro wins / Con wins / Unclear / Resolved vs Total
- **Cost by phase** — Constructive, Cross-exam, Evidence, Rebuttal, Discussion, Closing, Judgment
- **Debate durations** — per debate in seconds
- **Messages by role** — Advocate, Critic, Researcher, Examiner, Judge
- **Citations** — URL, domain, speaker, debate reference

---

## 8. Team Intelligence (Team Rooms)

Each team (Pro / Con) has a private room populated during and after the debate.

### Record Types

| Type | Populated by | Shown as |
|---|---|---|
| `claim` | Advocates, Critics | Talking Points |
| `evidence` | Researchers | Evidence Locker (with confidence bars) |
| `challenge` | Critics, Examiners | Counter-Prep ("If X, then Y" scenarios) |
| `memory_saved` | Any agent | Internal Chatter |
| `low_confidence` | Any agent | Attention Flags (operator review needed) |
| `judge_scorecard` | Judge | Judge's private analysis |
| `post_debate_feedback` | User | User's 3-question feedback |
| `verdict_review` | User | Verdict challenge / override record |

### Agent Experience / Learning
- Scope: `universal` (cross-session) or `chat` (session-scoped)
- Stored lesson types: debate observations, judge scorecards, user feedback
- Confidence levels: low / medium / high
- Use count and last-used timestamp tracked
- Retrieved at the start of each agent turn to inform responses

---

## 9. Model Support

### Providers & Models

| Provider | Models | Context |
|---|---|---|
| Google | gemini-3.1-pro, gemini-3-flash, gemini-2.5-flash-lite, gemini-2.0-flash | 128K |
| Groq | llama-3.1-8b-instant, llama-3.3-70b-versatile | 32K |
| OpenRouter | openrouter-auto, llama-3.3-70b-or, claude-3.5-sonnet-or | varies |
| OpenRouter Free | deepseek-r1-free, qwq-32b-free, llama-3.1-8b-free, gemma-3-27b-free, qwen3-14b-free | varies |
| Moonshot | kimi-latest, kimi-k2-thinking, kimi-k2-turbo-preview, kimi-k2.5-vision, moonshot-v1-128k | 128K |
| MiniMax | minimax-m2.7 | 32K |
| Fireworks | kimi-fw, llama-3.1-70b-fw | varies |
| OpenAI | gpt-4o, gpt-4o-mini | 128K / 8K |
| Anthropic | claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5, claude-3.5-sonnet | 200K |
| Mock | mock-debate-model | 32K (testing only) |

### Model Availability
- Availability determined by env var API key presence (not placeholder)
- Runtime probe: sends a 4-token test request; caches result for 15 minutes
- Temporary failures (rate limit, overload) cached for 2 minutes
- Hard failures (bad key, unknown model) cached for 6 hours

### Utility / Cheap Model Tier
For yes/no utility calls (consensus check, safety lock, intent routing):
- Priority: `llama-3.1-8b-instant` → `gemini-2.5-flash-lite` → any Groq → user's model
- These calls use `max_tokens=5–120` to minimize cost

---

## 10. Cost Tracking

### What's Tracked
- Input tokens and output tokens per LLM call
- Cost in USD per call: `(tokens / 1_000_000) × rate`
- Per-message `cost_summary` stored in DB
- Debate-wide aggregate built from message summaries

### Token Estimation
- CJK characters: 1.6 tokens each
- Latin words / numbers: 1.3 tokens each
- Minimum 1 token per call

### Pricing Sources (in priority order)
1. OpenRouter live pricing API (fetched when OPENROUTER_API_KEY present)
2. Local fallback table (embedded per model)
3. Marked `pricing_available: false` if neither available

### Supported Display Currencies
USD · CNY · HKD · EUR · JPY · GBP · AUD · CAD · SGD

### Display Controls
- `show_money_cost` — toggle cost display at all
- `show_model_costs` — breakdown by model in summary
- `show_every_message_cost_in_debate` — per-message cost badge
- `cost_currency` — convert totals to selected currency

---

## 11. Budget & Efficiency Controls

### Session Token Budget
- Hard cap per debate: default 40,000 tokens (env: `SESSION_TOKEN_BUDGET`)
- Tracked by `SessionBudget` class using `estimate_tokens`
- Charged after every agent turn (output text)
- When exhausted: `early_stop` event emitted, debate skips to judgment

### Per-Agent Output Cap
- Default: 400 tokens per turn (env: `MAX_AGENT_OUTPUT_TOKENS`)
- Can be overridden per archetype in agent settings
- Overrides session-level `max_tokens`

### Context Window
- Default: 6 recent turns in context (env: `CONTEXT_WINDOW_TURNS`)
- Smart context selection: recent N turns always kept; older turns ranked by topic relevance
- Prompt budget = model context limit − reserve tokens

### Flow Defaults (optimized for cost)
| Setting | Default | Notes |
|---|---|---|
| `debaters_per_team` | 1 | Only Lead Advocate → fewest phases |
| `debate_rounds` | 1 | Single discussion round |
| `discussion_messages_per_team` | 2 | Concise exchanges |
| `judge_assistant_enabled` | false | Saves 1 API call |
| `debate_intelligence_depth` | Light | Notebooks are deterministic, no API calls |

All of these can be raised in Settings for richer (but more expensive) debates.

---

## 12. Safety Lock

### Trigger
Every user message is assessed before routing. The cheapest available model classifies it.

### Classification
- Returns `{"action": "allow"}` or `{"action": "assist", "category": "...", "reason": "..."}`
- Default: ALLOW. Only ASSIST on extreme operational harm requests
- Fallback to regex patterns if LLM call fails

### Blocked Categories
- Weapons / explosives instructions
- Self-harm encouragement
- Child sexual exploitation
- Ransomware / malware / credential theft
- Violent wrongdoing assistance

### Response
- Council Assistant replies with a safe redirect message
- Explains what it can't do and what it can do instead (ethics, policy, prevention framing)
- Logged as a `chat` interaction, not a debate

---

## 13. Practice Mode & User Profile

### Practice Debate Flow
1. **Topic submitted** → new `ai_vs_human` debate created
2. **Side assignment** — Auto uses profile side history to pick the underused side
3. **Human turn** — user's argument saved as `practice_user` role
4. **AI turn** — Practice Debater responds, adapts difficulty to profile
5. **State update** — turn counts, rounds remaining shown
6. **Final round** → auto-triggers finalization
7. **Judge Assistant audit** (if enabled)
8. **Judge verdict**
9. **Debate Trainer coaching** — style-specific feedback
10. **Profile update** — strengths, weaknesses, trainer notes appended

### User Debate Profile Fields

| Field | Type | Notes |
|---|---|---|
| `debates_completed` | int | AI vs AI debates only |
| `practice_debates_completed` | int | Practice mode only |
| `wins` | `{pro, con, unclear}` | Verdict outcomes |
| `side_history` | `{pro, con, auto}` | Sides practiced |
| `strengths` | list (max 18) | Extracted by Trainer |
| `weaknesses` | list (max 18) | Extracted by Trainer |
| `trainer_notes` | list (max 30) | Full coaching notes |
| `style_tags` | list (max 12) | Personal debate style |
| `last_updated_at` | ISO timestamp | — |

### Coach Recommendations (auto-generated)
- No history → "Start with a practice debate"
- Weaknesses present → "Work on {weakness}"
- Side imbalance → "Practice the underused side"
- Strengths → "Leverage {strength} in your next debate"

---

## 14. Multi-Session Support

### Session Model
- Each session is independent: own settings, messages, debates, intelligence records
- Sessions identified by UUID
- Friendly name + auto-index code (e.g. `DBT_CH.01`, `PRC_CH.02`)
- Max concurrent sessions: 10 (configurable)

### Shared Across Sessions
- Universal agent experience (if `universal_experience: true`)
- User debate profile
- Council settings

### Clear Operations
| Operation | Scope | Reversible |
|---|---|---|
| `clear-history` | Hides messages and debates | Yes (via `include_hidden`) |
| `clear-memory` | Deletes all session data | No |
| `reset-agent-experience` | Deletes universal agent memory | No |
| `reset user profile` | Deletes user debate profile | No |

---

## 15. UI Panels

### In-Session Tabs

| Tab | Code | Content |
|---|---|---|
| Arena | Chat | Live streaming transcript, round groupings, speaker rosters, composer |
| Analytics | Stats | KPI cards, win rate, cost chart, argument graph, game theory, Bayesian scores |
| Pro Room | Room | Team talking points, evidence locker, counter-prep, roster, chatter |
| Con Room | Room | Same as Pro Room but for Con team |
| Settings | CFG | All session + per-agent + display settings |

### Global Navigation (Sidebar)

| View | Description |
|---|---|
| Dashboard | Home screen, create new sessions |
| Session List | All sessions split by mode (AI×AI / AI×Human), live status indicators |
| Agent Memory | Global agent experience records, per-agent summary |
| Training Profile | User profile, recent practice debates, coach recommendations |
| System Settings | Council-level settings, theme, judge mode, memory reset |

### Arena Details
- **Round Dividers** — phases grouped by type: OPENING STATEMENTS, CROSS-EXAMINATION, EVIDENCE, ROUND N, REBUTTAL, CLOSING STATEMENTS, VERDICT
- **Speaker Attribution** — team pill (PRO/CON/NEU), speaker name, role label
- **Typewriter Animation** — smooth char-by-char reveal during streaming; adaptive speed (2–10 chars/frame at 60fps)
- **Pending indicator** — shown between agent turns while inference is queued
- **Side Rosters** — Pro (left) and Con (right) panels show active agents with live pulse
- **Center Readout** — current speaker name, role, waveform animation
- **DISPATCH** — submit topic; `Ctrl+Enter` shortcut
- **TERMINATE / ARCHIVE** — header action buttons (UI scaffold)
- **DRAFT** — composer button (UI scaffold, not yet wired)

---

## 16. Runtime Observability

### Backend Terminal (Runtime Diary)
Server-side event log. Each entry has:
- `source` — e.g. `"backend terminal"`, `"frontend/browser"`
- `event` — short label (e.g. `"debate started"`, `"early consensus"`)
- `detail` — human-readable description
- `session_id` — optional session context

### Logged Events (backend terminal)
- Startup
- Interaction received (model, message preview)
- Intent routed (debate / chat)
- Safety lock classifier fallback
- Safety lock routed to Council Assistant
- Debate started (model, topic)
- Private notebook fallback (when LLM notebook prep fails)
- Debate completed
- Early consensus reached
- Debate client disconnected
- Debate failed (with error)
- WebSocket handler error

### HUD (frontend)
- Live clock for running debates
- Signal strength display
- Active debate status tag (CH.01 · LIVE / COMPLETE / IDLE)

---

*Last updated: automatically generated from codebase audit.*
