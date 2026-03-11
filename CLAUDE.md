# CLAUDE.md — AI-Intent Multi-Agent Investment System (Streamlit)

## Project Overview

You are building a Streamlit web application that demonstrates the **AI-Intent framework** for agentic AI systems. The app implements a private investment use case with a central LLM orchestrator that delegates to three specialist sub-agents (stock broker, bond, raw materials) via a simulated MCP (Model Context Protocol) message bus.

The core promise of the AI-Intent framework is that every agent action is:
- **Explicit** — governed by a machine-readable mandate
- **Bounded** — constrained by verifiable rules the agent cannot silently violate
- **Auditable** — every inter-agent message is logged and retrievable

The Anthropic Python SDK is used for all LLM calls. The model is always `claude-opus-4-5` unless
explicitly told otherwise.

---

## Project Structure

```
ai-intent-investment/
├── CLAUDE.md
├── app.py                  # Streamlit entry point
├── requirements.txt
├── agents/
│   ├── __init__.py
│   ├── manifests.py        # AgentManifest definitions for all four agents
│   ├── orchestrator.py     # Central investment orchestrator
│   ├── stocks.py           # Stock broker sub-agent
│   ├── bonds.py            # Bond sub-agent
│   └── materials.py        # Raw materials sub-agent
├── mcp/
│   ├── __init__.py
│   └── logger.py           # MCPMessage model + SQLite persistence
├── data/
│   └── sessions.db         # SQLite database (auto-created)
└── ui/
    ├── __init__.py
    ├── agent_graph.py      # Agent network visualization component
    ├── mcp_stream.py       # MCP log stream component
    └── intent_panel.py     # Agent intent manifest display component
```

---

## Coding Standards

- Python 3.11+
- Type hints on all function signatures
- Dataclasses or Pydantic v2 models for all structured data
- No global mutable state — pass session_id through all function calls
- All Anthropic API calls wrapped in try/except with error logged to MCP stream
- Streamlit `st.session_state` used for UI state only — never for business logic persistence
- Every function has a single-line docstring

---

## Task 1 — Project Scaffold

**Objective:** Create the complete folder structure and dependency manifest. Do not implement any logic yet — only create the files with correct imports and placeholder stubs.

**Steps:**

1. Create the full directory tree as shown in the Project Structure section above.

2. Create `requirements.txt` with the following packages:
   ```
   streamlit>=1.35.0
   anthropic>=0.30.0
   pydantic>=2.0.0
   streamlit-agraph>=0.0.45
   graphviz>=0.20.0
   python-dotenv>=1.0.0
   ```

3. Create `app.py` as the Streamlit entry point. It must:
   - Set page config: `layout="wide"`, title `"AI-Intent Investment System"`, icon `"🧠"`
   - Import and call a `render_dashboard()` function from `ui/` (stub for now)
   - Load `ANTHROPIC_API_KEY` from environment via `python-dotenv`
   - Show a sidebar with the project title and a brief one-paragraph description of the AI-Intent framework

4. Create all `__init__.py` files (empty).

5. Create stub files for every module listed in the structure with:
   - Module-level docstring explaining what the module does
   - All imports the module will eventually need
   - Function stubs with `pass` and docstrings — no implementation yet

6. Create a `.env.example` file:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```

**Acceptance criteria:**
- `streamlit run app.py` starts without errors
- The sidebar renders with title and description
- No import errors from any module

---

## Task 2 — AI-Intent Schema (AgentManifest)

**Objective:** Define the core data model that encodes what each agent is and is not allowed to do. This is the foundational schema — every subsequent task depends on it.

**File:** `agents/manifests.py`

**Steps:**

1. Define a Pydantic v2 model `AgentManifest` with these fields:
   ```python
   class AgentManifest(BaseModel):
       agent_id: str
       name: str
       emoji: str
       role: str
       intent_scope: str          # One-sentence mandate: what this agent exists to do
       boundary_constraints: list[str]   # Rules the agent must never violate
       risk_parameters: dict[str, Any]   # Numeric limits (e.g. max_allocation: 0.40)
       plain_language_summary: str  # Non-technical explanation of the above
   ```

2. Instantiate four `AgentManifest` objects as module-level constants:

   **CENTRAL_MANIFEST**
   - agent_id: `"central"`
   - name: `"Central Investment Orchestrator"`
   - emoji: `"🧠"`
   - role: `"Private Investment Coordinator"`
   - intent_scope: `"Orchestrate private investment decisions by delegating to specialist sub-agents, synthesizing their outputs, and producing auditable recommendations within defined portfolio risk bounds."`
   - boundary_constraints:
     - `"Must not produce a final recommendation without consulting at least one specialist sub-agent"`
     - `"Maximum 40% allocation to any single asset class"`
     - `"All sub-agent calls must be logged with the current session ID before the call is made"`
     - `"Must include an explicit accountability note in every final output"`
     - `"Must surface constraint violations from sub-agents rather than suppressing them"`
   - risk_parameters: `{"max_single_asset_class": 0.40, "min_sub_agents_consulted": 1}`
   - plain_language_summary: `"The boss agent. It asks the specialist agents for their opinions, checks that nobody broke any rules, and writes up a final recommendation explaining exactly what it did and why."`

   **STOCKS_MANIFEST**
   - agent_id: `"stocks"`
   - name: `"Stock Broker Agent"`
   - emoji: `"📈"`
   - role: `"Equity Analysis Specialist"`
   - intent_scope: `"Analyze equity investment opportunities within the approved large-cap universe and provide risk-adjusted return assessments aligned with the portfolio mandate."`
   - boundary_constraints:
     - `"Large-cap equities only: market capitalization must exceed $10 billion"`
     - `"Maximum 10% allocation to any single equity position"`
     - `"No margin trading, short selling, or leveraged equity products"`
     - `"ESG screening required: must flag ESG concerns for any new position"`
     - `"Must decline analysis of any equity outside the approved universe"`
   - risk_parameters: `{"max_market_cap_threshold": 10_000_000_000, "max_single_position": 0.10, "leverage_permitted": False}`
   - plain_language_summary: `"Looks at big company stocks only. Can suggest up to 10% of the portfolio in any one company. Cannot use borrowed money or bet that stocks will fall. Must check if companies are behaving responsibly."`

   **BONDS_MANIFEST**
   - agent_id: `"bonds"`
   - name: `"Bond Agent"`
   - emoji: `"🏛️"`
   - role: `"Fixed Income Specialist"`
   - intent_scope: `"Manage fixed-income allocation to provide portfolio stability, predictable cash flows, and capital preservation within approved credit quality and duration limits."`
   - boundary_constraints:
     - `"Investment grade only: minimum credit rating BBB+ (S&P) or Baa1 (Moody's)"`
     - `"Portfolio duration must remain below 10 years"`
     - `"No emerging market sovereign or corporate debt"`
     - `"Laddered maturity structure required: no more than 30% maturing in any single year"`
     - `"Must flag any recommendation that would increase overall portfolio duration above 7 years"`
   - risk_parameters: `{"min_credit_rating": "BBB+", "max_duration_years": 10, "warn_duration_years": 7, "max_single_maturity_bucket": 0.30}`
   - plain_language_summary: `"Handles the safe, boring investments that pay out steadily. Only buys from creditworthy borrowers. Spreads out when bonds mature so the portfolio is never all-in on one year. No risky country debt."`

   **MATERIALS_MANIFEST**
   - agent_id: `"materials"`
   - name: `"Raw Materials Agent"`
   - emoji: `"⛏️"`
   - role: `"Commodities Specialist"`
   - intent_scope: `"Evaluate commodity positions as an inflation hedge and portfolio diversifier, restricted to approved commodity types and within defined allocation limits."`
   - boundary_constraints:
     - `"Maximum 15% of total portfolio in raw materials"`
     - `"Direct exposure permitted for Gold and Silver only"`
     - `"No leveraged commodity ETFs or futures contracts"`
     - `"Rebalancing trigger: flag to orchestrator if allocation drifts more than ±5% from target"`
     - `"Must provide inflation correlation rationale for every recommendation"`
   - risk_parameters: `{"max_total_allocation": 0.15, "approved_commodities": ["Gold", "Silver"], "leverage_permitted": False, "rebalance_drift_threshold": 0.05}`
   - plain_language_summary: `"Handles gold and silver as protection against inflation. Capped at 15% of the total portfolio. No complicated derivatives or leveraged products. Tells the orchestrator if the allocation drifts too far from target."`

3. Create a convenience function:
   ```python
   def get_manifest(agent_id: str) -> AgentManifest:
       """Return the manifest for a given agent ID, raising KeyError if not found."""
   ```

4. Create a function that renders a manifest as a formatted system prompt string:
   ```python
   def manifest_to_system_prompt(manifest: AgentManifest) -> str:
       """Convert an AgentManifest into a structured system prompt for the LLM."""
   ```
   The output must include all fields clearly labeled and end with:
   `"If a user request falls outside your intent scope or violates any boundary constraint, you must explicitly state which constraint is violated and decline that specific request. Do not silently comply with out-of-scope requests."`

**Acceptance criteria:**
- All four manifests are importable
- `get_manifest("stocks")` returns the correct object
- `manifest_to_system_prompt()` returns a non-empty string containing the agent's constraints

---

## Task 3 — MCP Message Model & Logger

**Objective:** Build the message logging layer. This is the audit backbone of the system — every inter-agent communication is captured here. The log must be persistent (SQLite) and queryable by session.

**File:** `mcp/logger.py`

**Steps:**

1. Define a Pydantic v2 model `MCPMessage`:
   ```python
   class MCPMessage(BaseModel):
       id: str                    # UUID4
       session_id: str
       timestamp: datetime
       direction: Literal["outbound", "inbound", "internal"]
       from_agent: str            # agent_id or "user"
       to_agent: str              # agent_id or "user"
       method: str                # e.g. "stocks.analyze", "intent.route", "intent.synthesize"
       payload: dict[str, Any]    # The message content
       response_status: Literal["pending", "ok", "error", "constraint_violation"]
       constraint_flags: list[str]  # Any constraints flagged during this call (empty list if none)
   ```

2. Define a class `MCPLogger`:

   ```python
   class MCPLogger:
       def __init__(self, db_path: str = "data/sessions.db"):
           """Initialize SQLite connection and create table if not exists."""

       def log(self, message: MCPMessage) -> None:
           """Persist a single MCPMessage to the database."""

       def get_session(self, session_id: str) -> list[MCPMessage]:
           """Return all messages for a session, ordered by timestamp ascending."""

       def get_all_sessions(self) -> list[str]:
           """Return list of distinct session IDs, most recent first."""

       def clear_session(self, session_id: str) -> None:
           """Delete all messages for a given session ID."""
   ```

3. The SQLite table schema:
   ```sql
   CREATE TABLE IF NOT EXISTS mcp_messages (
       id TEXT PRIMARY KEY,
       session_id TEXT NOT NULL,
       timestamp TEXT NOT NULL,
       direction TEXT NOT NULL,
       from_agent TEXT NOT NULL,
       to_agent TEXT NOT NULL,
       method TEXT NOT NULL,
       payload TEXT NOT NULL,       -- JSON string
       response_status TEXT NOT NULL,
       constraint_flags TEXT NOT NULL  -- JSON string of list
   );
   CREATE INDEX IF NOT EXISTS idx_session ON mcp_messages(session_id);
   ```

4. Define a module-level singleton getter:
   ```python
   def get_logger() -> MCPLogger:
       """Return the singleton MCPLogger instance."""
   ```

5. Define a convenience function used by agents:
   ```python
   def build_message(
       session_id: str,
       direction: str,
       from_agent: str,
       to_agent: str,
       method: str,
       payload: dict,
       status: str = "ok",
       constraint_flags: list[str] | None = None,
   ) -> MCPMessage:
       """Construct an MCPMessage with auto-generated id and current timestamp."""
   ```

**Acceptance criteria:**
- `MCPLogger` creates `data/sessions.db` automatically on first use
- Logging a message and calling `get_session()` returns the same message
- Multiple messages for the same session_id are returned in timestamp order
- `constraint_flags` correctly round-trips through JSON serialization

---

## Task 4 — Sub-Agents (Stocks, Bonds, Materials)

**Objective:** Implement the three specialist sub-agents. Each is a self-contained module that enforces its manifest constraints via the LLM system prompt and logs every interaction to the MCP layer.

**Files:** `agents/stocks.py`, `agents/bonds.py`, `agents/materials.py`

Each sub-agent module follows the same pattern. Implement all three.

**Per-agent implementation steps:**

1. Define an async function:
   ```python
   async def analyze(query: str, session_id: str) -> dict[str, Any]:
       """
       Call the LLM with this agent's manifest as system prompt.
       Log the outbound call and inbound response via MCPLogger.
       Return structured result dict.
       """
   ```

2. Before the LLM call, log an **outbound** MCPMessage:
   - `from_agent`: `"central"`
   - `to_agent`: this agent's `agent_id`
   - `method`: `"{agent_id}.analyze"`
   - `payload`: `{"query": query}`
   - `response_status`: `"pending"`

3. Call the Anthropic API using `manifest_to_system_prompt()` for the system prompt. The user message is the `query` string. Instruct the model (in the system prompt) to respond in this JSON format:
   ```json
   {
     "analysis": "The substantive response text",
     "constraint_flags": ["list any constraints that were relevant or nearly violated"],
     "recommendation": "buy | hold | sell | not_applicable",
     "confidence": "high | medium | low",
     "out_of_scope": false
   }
   ```
   If the query is out of scope, `out_of_scope` should be `true` and `analysis` should name the specific constraint violated.

4. Parse the JSON response. If parsing fails, return an error dict and log status `"error"`.

5. After the LLM call, log an **inbound** MCPMessage:
   - `from_agent`: this agent's `agent_id`
   - `to_agent`: `"central"`
   - `method`: `"{agent_id}.result"`
   - `payload`: the parsed response dict
   - `response_status`: `"constraint_violation"` if `out_of_scope` is true, otherwise `"ok"`
   - `constraint_flags`: the list from the parsed response

6. Return the parsed result dict.

**Acceptance criteria:**
- Each agent can be called with an arbitrary query string
- The MCP log contains exactly two entries per call (outbound + inbound)
- Out-of-scope requests produce a `constraint_violation` status in the log
- LLM errors do not raise unhandled exceptions

---

## Task 5 — Central Orchestrator

**Objective:** Implement the orchestrator that ties everything together. It must plan routing, delegate to sub-agents, synthesize results, and produce a final output with a complete accountability note.

**File:** `agents/orchestrator.py`

**Steps:**

1. Define the return type:
   ```python
   class OrchestrationResult(BaseModel):
       session_id: str
       query: str
       agents_consulted: list[str]
       sub_agent_results: dict[str, Any]  # agent_id -> result dict
       final_recommendation: str
       accountability_note: str
       constraint_violations: list[str]   # Any violations surfaced across all agents
       routing_rationale: str
   ```

2. Define the main async function:
   ```python
   async def run(query: str, session_id: str) -> OrchestrationResult:
       """Execute the full orchestration pipeline for a user query."""
   ```

3. **Step A — Log user query as internal message:**
   - `from_agent`: `"user"`, `to_agent`: `"central"`, `method`: `"user.query"`, status `"ok"`

4. **Step B — Planning call (routing):**
   Call the Anthropic API with the central agent's manifest as system prompt plus the following instruction appended:
   > "You will receive a user investment query. Determine which specialist sub-agents to consult (stocks, bonds, materials — use only those relevant to the query) and what specific sub-question to send each one. Respond only in this JSON format: `{"routing_rationale": "...", "agents_to_call": ["stocks", "bonds"], "query_for_stocks": "...", "query_for_bonds": "...", "query_for_materials": null}`"

   Log this as an **internal** MCPMessage with `method: "intent.route"`.

5. **Step C — Parallel sub-agent calls:**
   For each agent in `agents_to_call`, call the corresponding `analyze()` function. Run them concurrently using `asyncio.gather()`. Collect all results.

6. **Step D — Synthesis call:**
   Call the Anthropic API again with the central manifest as system prompt plus a synthesis instruction. Provide all sub-agent results as context. The model must produce:
   - A final investment recommendation in plain language
   - An explicit accountability note containing: session ID, list of agents consulted, list of constraints checked, any violations found, and the date/time

   Log this as an **internal** MCPMessage with `method: "intent.synthesize"`.

7. **Step E — Log final output:**
   Log the final recommendation as an **inbound** MCPMessage from `"central"` to `"user"` with `method: "investment.response"`.

8. Return a fully populated `OrchestrationResult`.

**Acceptance criteria:**
- A full orchestration run produces at minimum 6 MCP log entries (user query, routing, 1+ agent calls × 2, synthesis, final output)
- `constraint_violations` is never empty when any sub-agent returns `out_of_scope: true`
- The accountability note includes the session ID
- Concurrent sub-agent calls complete correctly without race conditions on the logger

---

## Task 6 — Streamlit UI

**Objective:** Build the full dashboard. Three-column layout: agent network graph on the left, query interface and final response in the center, live MCP stream on the right.

**Files:** `app.py`, `ui/agent_graph.py`, `ui/mcp_stream.py`, `ui/intent_panel.py`

**Steps:**

1. **`ui/agent_graph.py` — Agent Network:**
   Use `streamlit-agraph` to render the four agents as nodes connected by edges. Central node is larger. Color each node distinctly. When a node is clicked, store the `agent_id` in `st.session_state["selected_agent"]`. During an active run, highlight active agent nodes.

2. **`ui/intent_panel.py` — Intent Inspector:**
   A function `render_intent_panel(agent_id: str)` that renders the selected agent's `AgentManifest` in a styled `st.container()`. Show: name, role, intent scope, boundary constraints as a bullet list, risk parameters as a table, and the plain language summary in a highlighted box.

3. **`ui/mcp_stream.py` — MCP Log Panel:**
   A function `render_mcp_stream(session_id: str)` that retrieves all messages for the session via `MCPLogger.get_session()` and renders each as a styled card with:
   - Color coding by direction: outbound (blue), inbound (green), internal (amber), error (red), constraint_violation (orange)
   - Expandable payload section (collapsed by default)
   - Timestamp and method name always visible
   - Constraint flags shown in red if non-empty

4. **`app.py` — Main Layout:**
   ```
   [Sidebar: title, description, session selector, new session button]

   [Col 1 — 30%: Agent Network graph + Intent Inspector below it]
   [Col 2 — 40%: Query input, sample query buttons, run button, spinner, final response output]
   [Col 3 — 30%: Live MCP Stream panel with auto-refresh during run]
   ```

   On run button click:
   - Generate a new `session_id` (UUID4), store in `st.session_state`
   - Call `orchestrator.run()` using `asyncio.run()`
   - Stream progress via `st.status()` context manager showing which agent is currently active
   - On completion, render the final recommendation in a styled `st.success()` block
   - Render the accountability note in an `st.expander()`
   - Refresh the MCP stream panel

5. Add five hardcoded sample queries as clickable `st.button()` elements:
   - "Should I add gold to my portfolio as an inflation hedge?"
   - "What large-cap equities look attractive for a conservative investor?"
   - "How should I structure a bond ladder for the next 5 years?"
   - "Design a diversified portfolio split across all three asset classes."
   - "Is it appropriate to put 50% of the portfolio into crypto futures?" *(this should trigger constraint violations)*

**Acceptance criteria:**
- Full pipeline runs end-to-end from UI with no unhandled exceptions
- MCP stream updates after each run
- Clicking an agent node renders its intent manifest
- The crypto futures query triggers visible constraint violation styling in the MCP stream

---

## Task 7 — Session Export (Accountability Trace)

**Objective:** Add a downloadable accountability trace so the AI-Intent audit artifact is tangible and portable.

**Steps:**

1. Add a function `generate_accountability_trace(session_id: str) -> dict` in `mcp/logger.py` that returns:
   ```json
   {
     "session_id": "...",
     "generated_at": "ISO timestamp",
     "framework": "AI-Intent v1.0",
     "query": "the original user query",
     "agents_consulted": ["stocks", "bonds"],
     "routing_rationale": "...",
     "constraint_checks": [
       {"agent": "stocks", "constraints_applied": [...], "violations": []}
     ],
     "mcp_message_count": 8,
     "final_recommendation_summary": "...",
     "full_mcp_log": [ ... all MCPMessage dicts ... ]
   }
   ```

2. Add a human-readable text version function `format_accountability_trace_text(trace: dict) -> str` that produces a clean, structured plain-text report.

3. In the Streamlit UI, after a successful run, add two download buttons side by side:
   - `📥 Download JSON Trace` — downloads the dict as `.json`
   - `📄 Download Text Report` — downloads the formatted text as `.txt`
   Use `st.download_button()` for both.

4. In the sidebar, add a **Session History** section that lists previous session IDs from the database. Clicking one loads its MCP stream into the right panel for review.

**Acceptance criteria:**
- Both download buttons appear after every successful run
- The JSON file is valid and contains all required fields
- The text report is readable without any code knowledge
- Session history in sidebar loads past session logs correctly

---

## Running the App

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run
streamlit run app.py
```

---

## Key Invariants — Never Break These

1. **Every LLM call is preceded by an MCPLogger entry.** No call goes unlogged.
2. **Constraint violations are surfaced, never suppressed.** If a sub-agent says out_of_scope, the orchestrator must include it in the final output.
3. **Session ID flows through every function call.** No function should generate its own session ID.
4. **The MCP log is the source of truth.** The UI reads from the log — it does not maintain its own copy of messages.
5. **Manifests are immutable at runtime.** No agent may modify its own manifest.

## LLM Backend Override

**This project uses Ollama running locally, not the Anthropic API.**

- Ollama endpoint: `http://localhost:11434/v1`
- Model: `llama3.1`
- Client library: `openai` Python package (OpenAI-compatible client)
- No API key required — pass `api_key="ollama"` as a placeholder
- Do NOT import or use the `anthropic` package anywhere
- All LLM calls use `client.chat.completions.create()` with `model="llama3.1"`

Create a shared client in `utils/llm.py` and import it everywhere:

    from openai import OpenAI
    import re, json

    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    def chat(system: str, user: str) -> str:
        response = client.chat.completions.create(
            model="llama3.1",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
        return response.choices[0].message.content

    def safe_parse_json(text: str) -> dict:
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise

Use `safe_parse_json()` everywhere an LLM response is parsed as JSON. Never use bare `json.loads()` on LLM output.