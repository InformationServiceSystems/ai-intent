# PRD: Intent Communication & Usage Visualization

**Product:** AI-Intent Investment System (Streamlit App)
**Author:** Wolfgang Maass
**Date:** 2026-03-31
**Status:** Draft

---

## 1. Problem Statement

The AI-Intent framework captures complete data about how agent intents are declared, routed, enforced, and audited. However, the current UI does not make this intent lifecycle visible to the user. Manifests are shown as static text, routing decisions are buried in expanders, constraint checks are flat lists, and the agent graph is inert during execution. A user cannot answer basic questions like:

- *Why was this agent consulted and not that one?*
- *Which constraints were actually checked during this run?*
- *Did any agent come close to violating a boundary?*
- *How did the orchestrator combine specialist opinions into a final recommendation?*

This PRD specifies UI enhancements that make intent communication and usage the central, visible story of every orchestration run.

---

## 2. Goals

| # | Goal | Success Metric |
|---|------|----------------|
| G1 | User can see the full intent lifecycle (declare → route → enforce → synthesize → audit) in one screen | All 5 lifecycle phases visible without navigation |
| G2 | Routing decisions are transparent: user sees which agents were chosen, why, and with what sub-questions | Routing rationale, agent selection, and per-agent queries shown before results |
| G3 | Constraint enforcement is visible per-agent and per-message | Each constraint shows checked/passed/violated/near-miss status |
| G4 | The agent graph reflects live message flow during execution | Edges animate and nodes highlight when active |
| G5 | Users can drill from any output back to the manifest constraint that governed it | Every constraint flag links to its source manifest entry |

---

## 3. Non-Goals

- Modifying the orchestration pipeline or agent logic
- Adding new agents or changing manifest content
- Real-time streaming of LLM token output
- Multi-user collaboration features

---

## 4. Feature Specifications

### 4.1 Intent Lifecycle Timeline

**Location:** Center column, below query input, above results

**Description:** A horizontal, phased timeline that updates as orchestration progresses. Five phases:

```
[1. Query Received] → [2. Intent Routing] → [3. Agent Delegation] → [4. Synthesis] → [5. Response]
     ●                    ●                     ●                      ●                  ●
```

Each phase node is clickable and expands to show:

| Phase | Expanded Content |
|-------|-----------------|
| Query Received | Original user query + `user.query` MCP message |
| Intent Routing | Routing rationale, list of agents selected, sub-question assigned to each agent, the central manifest constraints that informed routing |
| Agent Delegation | Per-agent card showing: sub-question sent, manifest constraints active, response received, constraint flags raised |
| Synthesis | All sub-agent results side-by-side, synthesis prompt context, how results were combined |
| Response | Final recommendation, accountability note, aggregate constraint check summary |

**Data source:** `OrchestrationResult` fields + MCP messages filtered by `method`

**Implementation notes:**
- Use `st.status()` during execution to show progress through phases
- After completion, render as a static timeline using `st.columns()` with styled containers
- Phase 3 (Delegation) shows parallel agent cards using nested columns

---

### 4.2 Routing Decision Panel

**Location:** Expands from Phase 2 of the timeline; also accessible as a standalone section

**Description:** Visualizes the routing decision with three components:

**A. Routing Instruction Display**
Show the system prompt instruction sent to the orchestrator LLM for the routing call. Currently this is a hardcoded string in `orchestrator.py` (`_ROUTING_INSTRUCTION`). Surface it in the UI so users see exactly what the LLM was asked.

**B. Agent Selection Matrix**
A table showing all available agents and the routing decision:

| Agent | Selected? | Sub-Question Assigned | Relevance Reason |
|-------|-----------|----------------------|------------------|
| Stocks | Yes | "Analyze large-cap equity options for..." | Query mentions equities |
| Bonds | Yes | "Evaluate bond ladder structure for..." | Query asks about fixed income |
| Materials | No | — | Query does not mention commodities |

Populate from the `intent.route` MCP message payload (fields: `agents_to_call`, `query_for_stocks`, `query_for_bonds`, `query_for_materials`, `routing_rationale`).

**C. Manifest Constraint Overlay**
Below the table, list the central orchestrator's boundary constraints and indicate which ones were relevant to the routing decision:
- "Must not produce a final recommendation without consulting at least one specialist sub-agent" → **Satisfied** (2 agents selected)
- "Maximum 40% allocation to any single asset class" → **Will be checked at synthesis**

---

### 4.3 Constraint Enforcement View

**Location:** Right column, as a tab alongside the existing MCP Stream

**Description:** A per-agent constraint audit panel that shows which manifest constraints were active and their enforcement status.

**Layout:** Tabbed interface with one tab per consulted agent + one "All Agents" summary tab.

**Per-Agent Tab Content:**

```
╔══════════════════════════════════════════════╗
║  📈 Stock Broker Agent                       ║
║  Intent Scope: Analyze equity investment...  ║
╠══════════════════════════════════════════════╣
║  Boundary Constraints:                       ║
║  ✅ Large-cap only (>$10B)      [passed]     ║
║  ✅ Max 10% single position     [passed]     ║
║  ✅ No margin/short/leverage    [passed]     ║
║  ⚠️ ESG screening required      [flagged]    ║
║  ✅ Approved universe only      [passed]     ║
╠══════════════════════════════════════════════╣
║  Risk Parameters:                            ║
║  max_market_cap_threshold: $10B  [in range]  ║
║  max_single_position: 10%        [in range]  ║
║  leverage_permitted: False        [compliant] ║
╠══════════════════════════════════════════════╣
║  Agent Response:                             ║
║  recommendation: hold                        ║
║  confidence: medium                          ║
║  out_of_scope: false                         ║
╚══════════════════════════════════════════════╝
```

**Status icons:**
- `✅` Passed — constraint was relevant and not violated
- `⚠️` Flagged — agent raised this as a concern (in `constraint_flags`)
- `❌` Violated — agent returned `out_of_scope: true` referencing this constraint
- `➖` Not applicable — constraint was not relevant to this query

**Data source:** Cross-reference `AgentManifest.boundary_constraints` with the `constraint_flags` field from the agent's `{agent_id}.result` MCP message.

**"All Agents" Summary Tab:**
Aggregate constraint matrix showing all agents as columns, all constraints as rows, with status icons at intersections.

---

### 4.4 Animated Agent Graph

**Location:** Left column (replaces current static graph)

**Description:** The agent network graph visually reflects the orchestration flow.

**Behavior during execution:**
1. **Query phase:** User node pulses, edge to Central lights up
2. **Routing phase:** Central node pulses (thinking indicator)
3. **Delegation phase:** Edges to selected agents animate (outbound = blue pulse). Non-selected agent nodes dim. Selected agents pulse while processing.
4. **Response phase:** Edges from agents back to Central animate (inbound = green pulse)
5. **Synthesis phase:** Central node pulses again
6. **Complete:** All consulted nodes glow green; violated nodes glow orange

**After execution (static state):**
- Consulted agents: full opacity, colored border
- Non-consulted agents: 30% opacity, gray border
- Edges used: solid lines with arrow indicators
- Edges not used: dashed, light gray
- Constraint violation badge: orange dot on agent node

**Implementation approach:**
- Use `streamlit-agraph` with dynamic `Config` updates per phase
- Store current phase in `st.session_state["orchestration_phase"]`
- Use `st.empty()` placeholder to re-render graph at each phase transition

**Click behavior (unchanged but enhanced):**
- Clicking a node shows its manifest in the intent panel (existing)
- NEW: If a run has completed, clicking a node also shows that agent's constraint enforcement status (from 4.3) below the manifest

---

### 4.5 Intent Flow Diagram (Sankey/Sequence)

**Location:** Center column, available as a tab alongside the results view

**Description:** A sequence diagram or Sankey diagram showing the complete message flow for the session.

**Option A — Sequence Diagram (recommended):**

```
User        Central       Stocks        Bonds       Materials
  |--query--->|              |             |             |
  |           |--route------>|             |             |
  |           |   (internal) |             |             |
  |           |--analyze---->|             |             |
  |           |--analyze-----|------------>|             |
  |           |<---result----|             |             |
  |           |<---result----|-------------|             |
  |           |--synthesize->|             |             |
  |           |   (internal) |             |             |
  |<--response|              |             |             |
```

Each arrow is clickable and shows the full MCP message details (direction, method, payload, status, constraint flags).

Color-coded:
- Blue arrows: outbound requests
- Green arrows: successful responses
- Orange arrows: constraint violation responses
- Amber arrows: internal processing
- Red arrows: errors

**Data source:** `MCPLogger.get_session(session_id)`, rendered in timestamp order.

**Implementation:** Generate using Python `graphviz` (already in requirements) with a custom sequence diagram layout, rendered via `st.graphviz_chart()`.

---

### 4.6 Manifest Diff View (Constraint Violation Drill-Down)

**Location:** Accessible from any constraint violation indicator (in MCP stream, constraint enforcement view, or results section)

**Description:** When a constraint violation occurs, clicking it opens a side-by-side view:

| Left: Manifest Constraint | Right: Agent Response |
|--------------------------|----------------------|
| "Direct exposure permitted for Gold and Silver only" | "Cryptocurrency is not in the approved commodities list. This request falls outside my intent scope." |
| `approved_commodities: ["Gold", "Silver"]` | `out_of_scope: true` |
| `leverage_permitted: False` | `constraint_flags: ["unapproved_commodity", "futures_not_permitted"]` |

This creates a direct, visual link between the conceptual model (manifest) and its runtime enforcement (agent response).

---

### 4.7 Session Replay

**Location:** Sidebar → Session History → selected session

**Description:** When loading a historical session, the UI replays the intent lifecycle:
- The timeline (4.1) populates phase by phase with a brief animation
- The agent graph (4.4) shows the post-execution static state (consulted vs. not consulted)
- The constraint enforcement view (4.3) shows all constraint statuses
- The intent flow diagram (4.5) renders the complete message sequence

This allows auditors to review past sessions with the same visual richness as live runs.

---

## 5. Information Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ SIDEBAR                                                             │
│ ┌─────────────────┐                                                 │
│ │ AI-Intent Title  │                                                │
│ │ Description      │                                                │
│ │ Session History  │ ← dropdown loads past sessions                 │
│ └─────────────────┘                                                 │
├──────────────┬────────────────────────┬─────────────────────────────┤
│ LEFT (30%)   │ CENTER (40%)           │ RIGHT (30%)                 │
│              │                        │                             │
│ Agent Graph  │ Query Input            │ Tab: MCP Stream             │
│ (animated,   │ Sample Queries         │ Tab: Constraint Enforcement │
│  clickable)  │ Run Button             │                             │
│              │                        │ (color-coded cards          │
│──────────────│ Intent Lifecycle       │  with drill-down)           │
│              │ Timeline               │                             │
│ Intent Panel │ [1]→[2]→[3]→[4]→[5]   │                             │
│ (manifest    │                        │                             │
│  for selected│ Tab: Results           │                             │
│  agent +     │  - Recommendation      │                             │
│  constraint  │  - Violations          │                             │
│  status)     │  - Accountability Note │                             │
│              │ Tab: Intent Flow       │                             │
│              │  - Sequence Diagram    │                             │
│              │                        │                             │
│              │ Download Buttons       │                             │
└──────────────┴────────────────────────┴─────────────────────────────┘
```

---

## 6. Data Flow

```
OrchestrationResult
  ├─→ Intent Lifecycle Timeline (phases, routing rationale, agents consulted)
  ├─→ Routing Decision Panel (agent selection, sub-questions, constraint overlay)
  ├─→ Constraint Enforcement View (cross-ref manifests × constraint_flags)
  └─→ Results Display (recommendation, violations, accountability note)

MCPLogger.get_session(session_id)
  ├─→ MCP Stream (chronological message cards)
  ├─→ Intent Flow Diagram (sequence diagram from message log)
  ├─→ Animated Agent Graph (message flow visualization)
  └─→ Constraint Enforcement View (per-message constraint flags)

AgentManifest (from manifests.py)
  ├─→ Intent Panel (full manifest display)
  ├─→ Constraint Enforcement View (constraint definitions to check against)
  ├─→ Routing Decision Panel (central manifest constraints)
  └─→ Manifest Diff View (constraint ↔ response mapping)
```

---

## 7. Implementation Plan

### Phase 1: Foundation (Estimated: Tasks 1-3)

| Task | File(s) | Description |
|------|---------|-------------|
| 1.1 | `ui/intent_timeline.py` | New component: Intent Lifecycle Timeline with 5 phases |
| 1.2 | `ui/mcp_stream.py` | Add tabbed interface (MCP Stream / Constraint Enforcement) |
| 1.3 | `app.py` | Integrate timeline into center column, wire up phase state |

### Phase 2: Routing Transparency (Tasks 4-5)

| Task | File(s) | Description |
|------|---------|-------------|
| 2.1 | `ui/routing_panel.py` | New component: Routing Decision Panel with agent selection matrix |
| 2.2 | `agents/orchestrator.py` | Expose `_ROUTING_INSTRUCTION` as importable constant for UI display |

### Phase 3: Constraint Enforcement (Tasks 6-8)

| Task | File(s) | Description |
|------|---------|-------------|
| 3.1 | `ui/constraint_view.py` | New component: Per-agent constraint audit with status icons |
| 3.2 | `ui/constraint_view.py` | "All Agents" summary tab with aggregate constraint matrix |
| 3.3 | `ui/intent_panel.py` | Enhance: show constraint status when a run has completed |

### Phase 4: Visual Flow (Tasks 9-11)

| Task | File(s) | Description |
|------|---------|-------------|
| 4.1 | `ui/agent_graph.py` | Animate graph during execution (phase-based node/edge styling) |
| 4.2 | `ui/intent_flow.py` | New component: Sequence diagram from MCP message log |
| 4.3 | `ui/agent_graph.py` | Post-execution static state (opacity, badges for violations) |

### Phase 5: Drill-Down & Replay (Tasks 12-14)

| Task | File(s) | Description |
|------|---------|-------------|
| 5.1 | `ui/manifest_diff.py` | New component: Manifest Diff View for constraint violations |
| 5.2 | `app.py` | Session replay: animate timeline and graph for historical sessions |
| 5.3 | `app.py` | Wire all click-through links (constraint flag → manifest, message → detail) |

---

## 8. New Files

| File | Purpose |
|------|---------|
| `ui/intent_timeline.py` | Intent lifecycle timeline component |
| `ui/routing_panel.py` | Routing decision visualization |
| `ui/constraint_view.py` | Per-agent and aggregate constraint enforcement display |
| `ui/intent_flow.py` | Sequence diagram of message flow |
| `ui/manifest_diff.py` | Side-by-side constraint vs. response view |

---

## 9. Dependencies

No new Python packages required. All visualizations use:
- `streamlit` native components (`st.columns`, `st.tabs`, `st.container`, `st.status`, `st.graphviz_chart`)
- `streamlit-agraph` (already installed) for the agent graph
- `graphviz` (already installed) for the sequence diagram

---

## 10. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| AC1 | Intent lifecycle timeline renders all 5 phases after a successful run | Visual inspection |
| AC2 | Clicking Phase 2 (Routing) shows agent selection matrix with sub-questions | Click test |
| AC3 | Constraint enforcement view shows per-agent constraint status with correct icons | Run crypto futures query → all 3 agents show ❌ violations |
| AC4 | Agent graph dims non-consulted agents after execution | Run single-agent query → 2 agents dimmed |
| AC5 | Intent flow diagram shows all MCP messages as a sequence | Message count in diagram matches `MCPLogger.get_session()` count |
| AC6 | Clicking a constraint violation anywhere opens the manifest diff view | Click test on violation badge |
| AC7 | Session replay populates all views from historical data | Load past session from sidebar → all panels populated |
| AC8 | No regressions: existing MCP stream, intent panel, and download buttons still work | Full regression test |
