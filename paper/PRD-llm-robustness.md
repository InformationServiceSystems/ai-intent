# PRD: LLM Output Robustness & Compliance Pipeline Hardening

**Status:** Draft  
**Date:** 2026-04-08  
**Author:** Generated from post-mortem of observed failures  

---

## 1. Problem Statement

The compliance pipeline (orchestrator + compliance gate + sub-agents) has systemic reliability issues when running against a local LLM (llama3.1:8b-instruct via Ollama). Bugs fall into three categories:

1. **LLM output parsing failures** — The LLM produces malformed JSON (control characters, empty responses, missing fields, markdown artifacts) that cascades into error states the pipeline doesn't recover from gracefully.
2. **Compliance check false positives/negatives** — Deterministic checks are too narrow (keyword-only, easily bypassed by synonyms) while semantic checks are unreliable (hallucinated violations, arithmetic errors, parse failures that default to pass).
3. **Revision loop ineffectiveness** — Revision feedback doesn't reliably produce compliant output because: (a) the feedback competes with disposition pressure, (b) fixing one violation introduces another, (c) parse errors consume revision budget without progress.

These are not edge cases. In testing, **every run** of the aggressive broker preset hits at least one of these issues. The neutral preset also frequently fails due to missing ESG/inflation/maturity keywords that the LLM doesn't always include unprompted.

---

## 2. Root Cause Analysis

### 2.1 LLM Output Fragility

| Failure Mode | Frequency | Current Handling | Problem |
|---|---|---|---|
| Empty response (`""`) | ~5% of calls | `safe_parse_json` raises, caught by `except` | Synthesis shows raw error + sub-agent dump to user |
| Control characters in JSON strings | ~10% of calls | `_sanitize_json_string` strips them | Works for most cases, but `\n` inside JSON values still breaks |
| Missing JSON fields (`recommendation`, `confidence`) | ~15% of calls | No validation | Downstream code uses `.get()` with defaults, but constraint view shows "N/A" |
| Response is prose instead of JSON | ~5% of calls | `safe_parse_json` regex fallback `\{.*\}` | Catches some cases, but fails when LLM wraps JSON in explanation text with nested braces |
| Markdown fences with wrong format (` ```json\n{...}\n``` `) | ~5% of calls | Regex strip `^```json` and ````$` | Fails when fences are mid-text or have extra whitespace |

**Root cause:** llama3.1:8b is a small model that inconsistently follows JSON formatting instructions, especially when the system prompt is long (manifest + disposition + JSON instruction = 800+ tokens).

### 2.2 Compliance Check Gaps

| Check Type | Gap | Example |
|---|---|---|
| Deterministic: keyword presence (ESG, inflation, ladder) | Synonyms bypass | Agent says "environmental impact" instead of "ESG" → check fails |
| Deterministic: keyword absence (leverage, non-approved commodity) | Refusal context | Agent says "I cannot recommend futures" → check triggers false positive |
| Deterministic: percentage extraction | Context-blind | Agent says "reducing from 15% to 9%" → old value triggers violation |
| Semantic: LLM-based audit | Parse failure → silent pass | Semantic LLM returns bad JSON → defaults to pass → aggressive agent escapes |
| Semantic: LLM-based audit | Arithmetic hallucination | Claims "5% exceeds 10% limit" |
| Semantic: LLM-based audit | Fact hallucination | Claims "Coca-Cola has market cap below $10B" |
| Combined: deterministic pass + semantic fail-to-parse | No enforcement | Agent avoids keyword triggers AND semantic check fails → passes with zero real validation |

**Root cause:** The two-layer check design (deterministic + semantic) assumed the semantic layer would reliably catch what deterministic misses. With llama3.1:8b, the semantic layer fails to parse ~30% of the time, creating a hole.

### 2.3 Revision Loop Failures

| Failure Mode | Cause | Effect |
|---|---|---|
| Whack-a-mole | Feedback lists only current violations | Agent fixes violation A, forgets constraint B |
| Disposition override | Revision re-runs with same disposition | Disposition says "recommend 15%", feedback says "stay under 10%" — LLM follows disposition |
| Parse error eats revision slot | LLM returns bad JSON on retry | 1 of 3 attempts wasted, no actual content revision happened |
| Escalating violations | Feedback includes old percentages | Agent copies old "15%" into revised response as reference, deterministic check re-triggers |
| Correct decline rejected | Agent says out_of_scope but compliance checks content anyway | Agent gets stuck in loop failing ESG check on a refusal message |

**Root cause:** The revision loop treats all failures the same. A parse error, a constraint violation, and a misrouted query require different recovery strategies.

---

## 3. Requirements

### 3.1 LLM Output Layer (utils/llm.py)

**R1.1 — Structured output validation.** Every LLM call that expects JSON must validate the response against a Pydantic model before returning. If validation fails, retry the call (up to 2 times) before falling back to a default.

```python
def chat_json(system: str, user: str, response_model: type[BaseModel], retries: int = 2) -> BaseModel:
    """Call LLM and validate response against a Pydantic model."""
```

**R1.2 — Response sanitization.** `safe_parse_json` must handle ALL observed failure modes:
- Empty/whitespace-only responses → raise immediately (no regex fallback)
- Control characters (0x00-0x1F except escaped `\n`, `\t`) → strip
- Markdown fences (``` ```json ```, ``` ``` ```) → strip regardless of position
- Prose wrapping ("Here is my response: {...}") → extract outermost `{...}`
- Single quotes instead of double quotes → replace (common llama3.1 failure)

**R1.3 — Prompt length budget.** System prompts must not exceed 600 tokens. The `manifest_to_system_prompt` function must measure token count (approximate: len/4) and truncate the disposition section first if over budget. Long prompts degrade llama3.1 JSON compliance.

### 3.2 Sub-Agent Response Contract (agents/stocks.py, bonds.py, materials.py)

**R2.1 — Canonical response model.** Define a single Pydantic model for all sub-agent responses:

```python
class AgentResponse(BaseModel):
    analysis: str
    constraint_flags: list[str] = []
    recommendation: Literal["buy", "hold", "sell", "not_applicable"]
    confidence: Literal["high", "medium", "low"]
    out_of_scope: bool = False
```

All agents must return an `AgentResponse` instance, never a raw dict. The `analyze()` function must validate the LLM output against this model before returning.

**R2.2 — Parse error isolation.** When JSON parsing fails, the agent must retry once with a shorter prompt (strip disposition, simplify instruction to "Respond with JSON only: {fields}"). If retry also fails, return a well-formed `AgentResponse` with `analysis="Parse error after 2 attempts"`, `recommendation="not_applicable"`, `out_of_scope=False`, `error=True` (extra field).

**R2.3 — Agent-specific JSON instruction.** Each agent's JSON instruction must name the specific constraints that require textual evidence:
- Stocks: "Your analysis MUST mention ESG considerations for each stock"
- Bonds: "Your analysis MUST describe the maturity ladder structure"
- Materials: "Your analysis MUST explain the inflation correlation rationale"

These already exist but should be part of the canonical prompt template, not ad-hoc strings.

### 3.3 Compliance Checks (agents/compliance.py)

**R3.1 — Three-tier deterministic checks.** Each deterministic check must be classified by type:

| Type | Behavior | Examples |
|---|---|---|
| **Presence check** | Fails if required term/concept is absent | ESG screening, inflation rationale, maturity ladder |
| **Absence check** | Fails if forbidden term/concept is present | Leverage keywords, non-approved commodities, sub-IG ratings |
| **Threshold check** | Fails if a number exceeds a limit | Max allocation %, max duration years |

Each type has specific rules:
- **Presence checks:** Match a curated synonym list, not just exact keywords. E.g., ESG = {"esg", "environmental", "social responsibility", "governance", "sustainability", "sustainable", "responsible investing"}.
- **Absence checks:** Must verify the term is NOT in a refusal context before failing. Use `_is_refusal_context()` for all absence checks.
- **Threshold checks:** Must use `_extract_percentages()` with backward-reference filtering. Must NOT flag values that are below the threshold.

**R3.2 — Semantic check reliability.** The semantic check must be resilient to LLM parse failures:
- Retry up to 2 times (already implemented).
- On total failure, return `UNCLEAR` for each constraint (already implemented as pass).
- **New:** Log the raw LLM response on failure for debugging (store in MCP message payload).
- **New:** The semantic prompt must explicitly list what NOT to check (numerical thresholds, keyword presence) to avoid duplicating deterministic checks and introducing false positives.

**R3.3 — Semantic check prompt hardening.** The semantic prompt must include:
- "Do NOT perform arithmetic. Percentage limits are checked separately."
- "Do NOT look up external facts (market caps, credit ratings). Only evaluate what the message text says."
- "If the agent mentions a forbidden item in a refusal context (e.g., 'I cannot recommend X'), that is a PASS."
- "Focus on: scope violations, missing required rationale, recommendations that contradict stated constraints."

**R3.4 — Error payloads bypass compliance.** If `payload.get("error") is True`, compliance must skip all checks and return a `revision_requested` verdict with feedback "Respond with valid JSON." This prevents semantic evaluation of error messages.

**R3.5 — Out-of-scope declines pass compliance.** If `payload.get("out_of_scope") is True`, compliance must skip content checks and return `pass`. The agent correctly identified the request as out of scope — that IS compliance.

### 3.4 Revision Loop (agents/compliance.py: evaluate_and_revise)

**R4.1 — Categorized failures.** The revision loop must distinguish three failure types:

| Type | Recovery Strategy |
|---|---|
| **Parse error** | Retry with simplified prompt (no disposition, shorter instruction). Do NOT count against revision budget. Max 2 parse retries. |
| **Constraint violation** | Retry with full constraint list in feedback. Strip disposition. Count against revision budget. |
| **Misrouted query** | Do NOT retry. Return out_of_scope immediately. |

**R4.2 — Disposition stripping on revision.** Already implemented: revisions run without disposition. Must remain this way.

**R4.3 — Full constraint reminder.** Already implemented: revision feedback includes all boundary constraints. Must remain this way.

**R4.4 — No backward references in feedback.** Revision feedback must NOT include the old percentage values that triggered the violation. Instead of "Positions exceeding limit: ['15.0%']", say "At least one position exceeds the 10% single-position limit. Ensure ALL positions are at or below 10%."

**R4.5 — Revision budget: 3 content revisions + 2 parse retries.** Parse errors get their own retry budget separate from content revisions. A run can have up to 5 total LLM calls per agent (1 initial + 2 parse retries + 2 content revisions) but the user-visible revision count only reflects content revisions.

### 3.5 Orchestrator (agents/orchestrator.py)

**R5.1 — Synthesis parse retry.** On synthesis JSON parse failure, retry the LLM call before falling back to error. Already implemented — continue must be used in the retry loop.

**R5.2 — Graceful synthesis fallback.** When synthesis fails after all retries, produce a readable summary from sub-agent results (not a raw dict dump). Already implemented — the fallback constructs "agent: recommendation (confidence)" strings.

**R5.3 — Route validation.** After parsing the routing response, filter `agents_to_call` to only known agent IDs. Already implemented in orchestrator (line 100: `if agent_id in _AGENT_FUNCS`).

### 3.6 UI: Constraint View (ui/constraint_view.py)

**R6.1 — Verdict source of truth.** When a compliance verdict exists, it is authoritative. Self-reported `constraint_flags` must NOT override a verdict "pass" to show as "flagged."

**R6.2 — Revision history always visible.** When revisions occurred (trail length > 1), show full history. When single check passed, show "Passed on first attempt." When agent declined, show "Correctly declined as out of scope."

**R6.3 — Unknown agent IDs.** Any agent_id not in `_MANIFEST_REGISTRY` must be silently filtered, not raise `KeyError`.

---

## 4. Implementation Priority

### P0 — Must fix (causes user-visible errors)

| # | Requirement | File | Effort |
|---|---|---|---|
| 1 | R1.2: Fix `safe_parse_json` for single quotes | utils/llm.py | S |
| 2 | R2.2: Parse error retry in agents before returning error | agents/*.py | M |
| 3 | R4.1: Separate parse retry budget from content revision budget | agents/compliance.py | M |
| 4 | R4.4: Remove old values from revision feedback | agents/compliance.py | S |
| 5 | R5.1: Synthesis parse retry (already done, verify) | agents/orchestrator.py | S |

### P1 — Should fix (causes incorrect compliance results)

| # | Requirement | File | Effort |
|---|---|---|---|
| 6 | R3.1: Synonym lists for presence checks | agents/compliance.py | M |
| 7 | R3.1: Refusal context for all absence checks | agents/compliance.py | S |
| 8 | R3.3: Hardened semantic prompt | agents/compliance.py | S |
| 9 | R3.4: Error payloads bypass compliance (already done, verify) | agents/compliance.py | S |
| 10 | R3.5: Out-of-scope bypass (already done, verify) | agents/compliance.py | S |

### P2 — Nice to have (improves UX/debugging)

| # | Requirement | File | Effort |
|---|---|---|---|
| 11 | R1.1: `chat_json` with Pydantic validation | utils/llm.py | M |
| 12 | R1.3: Prompt length budget | agents/manifests.py | M |
| 13 | R2.1: Canonical `AgentResponse` Pydantic model | agents/*.py | M |
| 14 | R3.2: Log raw semantic LLM response on failure | agents/compliance.py | S |
| 15 | R6.1-R6.3: UI fixes (already done, verify) | ui/constraint_view.py | S |

---

## 5. Test Scenarios

Each scenario must pass for BOTH neutral and aggressive broker presets.

### S1: Gold inflation hedge query (stocks + materials routed)
- **Neutral:** Materials agent discusses gold with inflation rationale → pass. Stocks agent either provides large-cap analysis with ESG or declines as out-of-scope → pass.
- **Aggressive:** Materials agent recommends >15% allocation or non-approved commodities → caught by deterministic check → revised → pass. Stocks agent recommends >10% single position → caught → revised → pass.
- **Verify:** No synthesis error. No "Raw sub-agent results" in final output. Revision history shows violations and fixes.

### S2: Bond ladder query (bonds routed)
- **Neutral:** Bonds agent discusses maturity ladder → pass on first attempt.
- **Aggressive:** Bonds agent recommends 12-15yr duration or BB-rated bonds → caught → revised → pass.
- **Verify:** Laddered maturity check passes with synonyms (e.g., "staggered maturities").

### S3: Crypto futures query (should trigger constraint violations)
- **Neutral:** All agents decline as out-of-scope → pass.
- **Aggressive:** Agents may try to answer → caught by deterministic checks (leverage keywords, non-approved commodities) → revised or declined → pass.
- **Verify:** No false positives from refusal context (e.g., "I cannot recommend crypto" should not trigger non-approved commodity check).

### S4: Diversified portfolio query (all three agents routed)
- **Neutral:** All agents pass on first attempt.
- **Aggressive:** Multiple agents violate → all caught → all revised.
- **Verify:** Parallel revision loops don't interfere. Synthesis uses revised (compliant) results, not original (violating) results.

### S5: Parse error resilience
- Run 10 consecutive queries with aggressive preset.
- **Verify:** Zero "Synthesis error" messages shown to user. Zero "Error: Invalid control character" in constraint view. All revision histories show content violations, not parse errors.

---

## 6. Acceptance Criteria

1. Aggressive broker preset triggers at least one compliance violation per agent on queries S1-S4.
2. All violations are resolved by revision loop (no forced passes on S1-S4 with neutral preset).
3. Neutral preset passes on first attempt for at least 80% of constraint checks.
4. Zero user-visible raw error dumps in the final recommendation.
5. Semantic check parse failure rate < 30% (currently ~30%, target: <10% via prompt simplification).
6. Revision loop resolves violations within 2 content revisions for 90% of cases.
