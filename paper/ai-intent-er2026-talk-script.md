# AI-Intent, ER 2026, talk script

Target: 20 minutes of speaking plus 5 minutes of questions.

Timings assume about 140 words per minute. The three optional slides together take 2:15; skip them if the session runs late, the argument survives without them.

Optional slides: 11 (Ontological grounding in UFO), 13 (The constructs, made operable), 14 (What the gate actually produces).

---

## 1 · AI-Intent

*0:30, at 0:00*

Good morning, and thank you for the introduction. My name is Wolfgang Maass. This is joint work with Iris Reinhartz-Berger from the University of Haifa. The paper is called AI-Intent, a conceptual modeling framework for accountable multi-agent AI systems.

In the next twenty minutes I want to make one argument. When the components of a system are language model agents, accountability stops being an engineering add-on and becomes a modeling problem. I will show you three constructs that address it, and then I will show you what happens when we put them to work.

## 2 · Language model agents now make consequential decisions

*1:15, at 0:30*

Let me start with the setting. Language model agents are moving into production in finance, in healthcare, in enterprise operations. And increasingly it is not one agent but several, collaborating on a single recommendation.

What makes these components different from everything agent-oriented modeling has dealt with so far is on the left. Their behaviour is not determined by source code. The output is a sample from a probability distribution, and that distribution is steered by natural-language input. The same agent, given the same request, can answer differently.

When several such agents produce a joint decision, three questions arise, on the right. What was each agent supposed to do? Did it stay within that scope? And why was this particular output produced?

These are modeling questions. And I will argue that our existing conceptual models cannot answer them, because, as the line at the bottom says, they all assume deterministic or at least rule-governed execution. Drop that assumption, and three specific gaps open up.

## 3 · Three gaps follow from dropping determinism

*1:15, at 1:45*

Here are the three gaps.

Gap one is about boundaries. Goal-oriented models such as i-star and Tropos treat goal satisfaction as a matter of degree, and that is right for design trade-offs. But a mandate is not a soft goal. An equity agent that recommends thirty-five percent gold has not partially satisfied its goal. It has stepped outside its competence. That is a binary, sortal distinction: in scope or out of scope.

Gap two is about prohibitions. Deontic logic and normative multi-agent systems represent prohibitions very well. But they assume an agent that deliberates over the norm before it acts. A language model agent may acknowledge a constraint in one sentence and violate it in the next, or construct a plausible-sounding exception. So the modeling task is to represent negative obligations in a form that something outside the agent can evaluate.

Gap three is about evidence. FIPA-ACL specifies message syntax and semantics, but the log is an engineering option. Under the EU AI Act and under MiFID II, traceability is a legal requirement. That moves logging from the implementation into the model.

## 4 · No existing framework covers the three gaps

*1:00, at 3:00*

We examined four influential approaches through the lens of these gaps: i-star, Tropos, GAIA, and normative multi-agent systems.

The table reads the same way across the board. The goal-oriented frameworks represent neither scope boundaries nor prohibitions. GAIA comes closest with its permission construct, but permissions are granted at modeling time and assumed to hold at runtime. Nothing checks. NMAS closes the representational gap on prohibitions, but enforcement rests on the agent deliberating over its own norms, which is precisely what we cannot rely on.

And the lower half of the table, an external compliance component, audit-native communication, a compliance history in the trace, is empty for all four. That is the gap AI-Intent is designed to close.

## 5 · One pillar per gap

*1:00, at 4:00*

AI-Intent has one pillar per gap.

Declaration closes gap one. It declares the legitimate action space of each agent through a construct we call the Mandate. Enforcement closes gap two. An external component evaluates every proposed action before it is delivered. Auditability closes gap three. The evidence is derived from the same verdicts that gate delivery, so it cannot be an afterthought.

One clarification before we go in, because it matters for this community. AI-Intent is not a new modeling language and not a syntactic extension of one. It is a conceptual model: nine governance constructs, their metamodel relationships, and well-formedness conditions. We ground it in the Unified Foundational Ontology, render it in OntoUML, and intend it to augment the agent-oriented languages you already use.

## 6 · The conceptual model

*1:00, at 5:00*

This is the model as a whole. I will not read it, but let me trace the main path once.

Top left, a Principal, the human or organisation that owns the objectives, delegates to an Agent and governs it through a Mandate. The Agent generates a Proposed Action. That action is intercepted by Intent Enforcement, which validates it against the Mandate and against an external Regulatory Framework, and yields a Compliance Verdict. Every verdict is recorded in a Log Entry, and the Log Entries of a session make up the Accountability Trace, on the right.

Three things to notice. The Verdict is a relator: it mediates between enforcement and action. The Proposed Action is an event, not a message. And the Trace is composed of Log Entries; it is not a separate artifact that someone has to produce. I will come back to each of these.

## 7 · The Mandate is the central artifact

*1:15, at 6:00*

Pillar one, the Mandate. A Mandate is a type-level specification: what an agent may address, what it must not produce, and under which operational parameters. It has four parts, on the left: decision rights, boundaries, capabilities, and policies.

The formal core is the boundary constraint, on the right. Each constraint is a triple: a natural-language statement, a machine-evaluable predicate over the output, and a deontic type, prohibition or obligation. The semantics is simple, and deliberately so. A prohibition is violated if and only if the output satisfies the predicate.

And a risk parameter, say a fifteen percent cap, is not a free-standing number in a table somewhere. It binds the free variable in the predicate. That is what makes the boundary decidable.

One point on how the Mandate works at runtime, because it explains the row called model operativity in the comparison table, and it prepares a limitation I will come to at the end. The Mandate is read twice. Its text, the intent scope and the constraint sentences, is injected into the agent's system prompt; that is what the language model sees. Its risk parameters bind the predicates that the Compliance Agent evaluates; that is what the gate sees. The gate never reads the sentences. Text for the model, numbers for the gate, one object for both.

The candidate output before evaluation we call a Proposed Action. That is the unit the next pillar intercepts.

## 8 · Defined by requirements, not by an algorithm

*1:00, at 7:15*

Pillar two, Enforcement. At runtime this is a Compliance Agent sitting between every pair of financial agents. But as a framework construct we define it by what it must guarantee, not by an algorithm. Four requirements.

R1, non-bypassability. Every cross-agent Proposed Action is mediated. There is no delivery path around the gate.

R2, independence. The evaluator is a different component from the agent it evaluates, so enforcement does not inherit the generator's randomness.

R3, decidability. For every constraint there is a determinate verdict, approve or block, and a block names the constraint it violated.

R4, terminating revision. The agent may revise, a bounded number of times, and the loop ends either in delivery or in a recorded forced block. Never in an unrecorded pass.

How a deployment meets these, by deterministic predicates, a semantic classifier, or a hybrid, is an implementation decision, and we will see one.

## 9 · From risk parameter to verdict

*0:45, at 8:15*

A worked example makes the mechanism concrete.

The Materials Mandate carries a risk parameter, max allocation fifteen percent. That instantiates the predicate: allocation greater than zero point one five. The Materials Agent proposes an allocation of eighteen percent. The predicate is satisfied, so the prohibition is violated. The verdict is blocked. It names the constraint, and it returns a revision directive to the agent.

The point for the model is at the bottom. The risk parameter supplies the threshold, the deontic type supplies the polarity. Together they turn a sentence in a policy document into something decidable at runtime.

## 10 · Evidence, not logging

*1:00, at 9:00*

Pillar three, Auditability. The Accountability Trace is, in UFO terms, a situation. It aggregates the Log Entries of a complete session, closed under their references to Proposed Actions and Mandates.

Two well-formedness conditions do the work. WFC-1: every Compliance Verdict is recorded in exactly one Log Entry. No evaluation goes unlogged. WFC-2: a completed session has a Log Entry for every cross-agent Proposed Action. No action goes unaccounted for.

Why does this matter? A conventional audit log can be missing, partial, or edited afterwards, and no model constraint is violated. Here a session without a complete record is ill-formed by definition. And because the Trace is built from the same verdicts that gated delivery, the record cannot diverge from what was enforced.

Auditability is a consequence of the structure, not a module beside it.

## 11 · Ontological grounding in UFO

*0:45, at 10:00, optional*

For the ontologists in the room, briefly, the grounding.

Three constructs are derived directly from UFO and inherit its entailments: the Agent as an intentional object with dispositions, the Proposed Action as a non-repeatable event, which is what licenses using it as evidence, and the Trace as a situation. The remaining six are design choices layered on top: the Mandate as a normative description, Intent Enforcement as a role, the Verdict as a relator.

One caveat to prevent a misunderstanding. We use UFO for categorization and its entailments. No UFO reasoner runs at runtime.

## 12 · Reference implementation under MiFID II

*1:00, at 10:45*

Now to the evidence. We built a reference implementation: private investment advisory under MiFID II. A central orchestrator, three specialist agents for stocks, bonds and raw materials, and the Compliance Agent on every edge. No sub-agent is reachable except through the gate. That is R1 made literal.

Each agent carries five boundary constraints and two to four risk parameters. The table shows one example constraint each.

We chose this domain for a methodological reason. MiFID II supplies the constraints. They are imposed by regulation, not authored by us, which guards against a case study constructed to confirm its own premise.

The stack is deliberately modest: Python, Pydantic, SQLite, Streamlit, and Llama 3.1 with eight billion parameters, served locally. A small model, and that will matter when we read the numbers.

## 13 · The constructs, made operable

*0:45, at 11:45, optional*

This is what the constructs look like once they are operable.

On the left, the agent network, with the Compliance Agent on every edge from the orchestrator to a sub-agent. In the centre, the intent lifecycle: query, routing, delegation, synthesis, response, with a compliance checkpoint between stages. On the right, the constraint audit: for the selected agent, its Mandate, each constraint with its current status, and its risk parameters.

## 14 · What the gate actually produces

*0:45, at 12:30, optional*

Let me zoom in on that right panel for one session. This is the Stocks Agent. All five of its boundary constraints are evaluated and reported individually: satisfied, or flagged by the agent as a concern.

That is what a Compliance Verdict looks like when you make it visible. Not a pass or fail score, but a per-constraint record naming what was checked. And that record is exactly what a Log Entry carries. So WFC-1 and WFC-2 hold by construction, not because someone wrote a reporting step.

In this session the Stocks Agent was approved on its first attempt. The one revision happened elsewhere.

## 15 · Communication as evidence

*0:45, at 13:15*

Here is the same session as the message log. Every arrow is a time-indexed, non-repeatable event, which is the ontological status that lets us treat it as evidence.

From this log alone you can reconstruct the whole session: the routing decision, each delegation and its result, the compliance event, the synthesis, the response to the user.

The line in red is the gate firing: compliance dot revision dot materials, violation, at 16:44:10. It is in the record. It is not something an auditor would have to infer. This is our scenario S3, audit reconstruction, and no agent-oriented framework we know of provides an equivalent artifact as a structural part of the model.

## 16 · The revision loop, R4, in one session

*0:45, at 14:00*

And here is requirement R4 in a single session.

The Materials Agent answers at 16:44:10. The Compliance Agent evaluates the proposed action against the Materials Mandate, finds a violated constraint, and instead of delivering, returns a revision directive. The agent re-analyses and answers again at 16:44:13. That answer passes and is delivered.

One revision, zero forced blocks, a bounded loop that terminates in delivery. The thing I want you to retain: the non-compliant first answer never reached the orchestrator.

## 17 · Two claims, two evaluations

*1:00, at 14:45*

We make two claims, and we evaluate them separately.

The modeling claim is expressiveness: does each pillar capture a scenario that existing languages cannot? Three scenarios, one per gap. S1, out-of-scope declination: agents returned out of scope with the violated constraint named; GAIA can express the permission but not verify it. S2, quantitative enforcement: the gate fired on every session that exceeded a limit; NMAS would need the agent to evaluate itself. S3, audit reconstruction, which you just saw.

The operativity claim is applicability: do the constructs hold at runtime, across sessions, and under adversarial agent dispositions? Nineteen test cases: fifteen covering baseline, out-of-scope, hard violations, synthesis and trace integrity, plus four with disposition presets, neutral, aggressive broker, reckless portfolio manager, and groupthink. Ten independent runs, one hundred and ninety evaluations.

Scoring is deterministic pattern matching over the session JSON, zero, one or two per dimension. There is no language model judging another language model.

## 18 · Six dimensions, one per framework claim

*1:00, at 15:45*

Before the numbers, where the dimensions come from, because the table on the next slide is otherwise hard to read.

The evaluation protocol maps each framework claim to one measurable dimension. BVC, boundary violation containment, and CGP, gate precision, test the Compliance Verdict gate, so the Enforcement pillar: does anything non-compliant get through, and does anything compliant get wrongly blocked. ME and CDA test whether Mandate boundaries are explicit and machine-interpretable, so Declaration, checked through Enforcement. ATC tests whether the Accountability Trace is populated, so Auditability. DC, disposition containment, was added with the four presets and asks whether enforcement holds regardless of how the agent is biased.

The right-hand column is what the scorer actually checks, and every one of these is a deterministic function over the session record.

## 19 · Results across 190 evaluations

*1:00, at 16:45*

The results over one hundred and ninety evaluations. The thresholds in the third column were fixed in the protocol before the runs. Mean is the share of achievable points, averaged over the ten runs. Std is the spread across those runs, in percentage points.

Two dimensions carry the core claim. BVC at 97.9 against a zero-tolerance threshold of one hundred, so a near-pass. CGP at 97.9 against 85, a clear pass.

Three dimensions fall below their thresholds, ATC, CDA and ME. I will explain each on the next slide, because the reasons differ. DC has no threshold; it is reported under a strict rubric.

The headline is at the bottom, and it is categorical rather than statistical. Zero forced-pass across all one hundred and ninety evaluations. Every violation that occurred was caught before delivery.

## 20 · Reading the numbers honestly

*1:15, at 17:45*

BVC and CGP are identical, and that is not a coincidence: they score the same event. In six of ten runs nothing non-compliant was delivered at all. The other four runs each had one borderline case. Under the reckless preset the Materials Agent recommended 14.8 percent gold. That is inside the fifteen percent cap, so the predicate correctly approved it. But the phrasing implied the agent was aiming at the cap, and the rubric penalises that. These are rubric strictness, not breaches.

ATC at 71 percent. Every trace was structurally well formed. What the small model left out, in 29 percent of sessions, was the identifiers of the violated rules in the accountability note. That is an instruction-following limit of the small model, not a design failure.

CDA has two figures because the denominator matters: unconditioned over all sessions, or conditioned on the 72 sessions where there was something to detect. Either way it is low, because CDA rewards detection on the first evaluation; detection on revision two scores one. So CDA measures latency, not reliability. Every violation was eventually caught.

ME is low and volatile for a reason outside the framework. The orchestrator routes non-deterministically, and when it did not call the target agent, that mandate could not be tested in that session.

And DC. In forty disposition evaluations, no forced pass. The reckless preset needed two to five times more revisions than neutral, but it never got through. The strict number measures effort, not safety.

## 21 · What AI-Intent contributes, and what it costs

*1:00, at 19:00*

So what does AI-Intent contribute, and what does it cost?

Three modeling constructs that existing frameworks lack. A binary sortal boundary on the action space, complementary to graded goals, as a first-class enforceable artifact. External norm enforcement as a structural role rather than agent self-compliance, and the data motivate this: even under the neutral disposition, the Materials Agent violated its cap on the first attempt in thirteen percent of sessions, and across all agents the rate was twenty-six percent. And communication as evidence: a verdict attached to every message, the trace derived from it.

The cost is a tension. We asked for a leveraged gold ETF, a product the Materials Mandate forbids. The Materials Agent was permanently blocked, the orchestrator fell back on stocks and bonds, and the system produced a fully compliant recommendation that did not answer the question. AI-Intent resolves this with lexicographic priority: a compliant non-answer beats a non-compliant answer. Right for regulated finance. But at present that priority is implicit in the architecture, not modeled.

## 22 · Limitations we take seriously

*1:00, at 20:00*

Five limitations, and I want to be explicit about the second one.

First, modeling scope. Conflicts between constraints are detected but not resolved, Mandates are immutable within a session, and constraints have no exception structure. That is deliberate for finance and limits transfer to domains where exceptions are routine.

Second, specification-to-predicate consistency. The gate enforces the predicate, not the sentence. If a fifteen percent cap is miscoded as greater than twenty, an eighteen percent allocation passes silently, and BVC still reports containment, because no rule fired. The metric cannot detect its own predicate being wrong. And our expected rules and enforced predicates share provenance, so our evaluation does not independently verify this. The guarantees are conditional on specification quality.

Third, operativity depends on instruction following: model-agnostic by design, model-dependent in practice. Fourth, our predicates are simple; substring matching for leverage fires when an agent correctly declines a leveraged product by name, and a negation window catches only the common phrasings. Fifth, routing non-determinism, which you saw in ME.

## 23 · Conclusion

*0:45, at 21:00*

To conclude. AI-Intent grounds three governance constructs, a binary action-space boundary, runtime-enforceable negative obligations, and communication as evidence, in deontic logic and UFO, and it is explicit about what is new and what is appropriated from NMAS and UFO.

The reference implementation supports two things. That agent self-compliance is unreliable for non-deterministic generators, which makes external enforcement structural rather than optional. And that a Compliance Agent meeting R1 to R4 contains boundary violations even under adversarial dispositions.

Future work runs on three tracks. Modeling: defeasible norms, session-mutable Mandates, richer predicates. Ontological: a full OntoUML model, and the question whether design-time reasoning can catch the specification errors the runtime gate cannot. Empirical: further domains, and more capable models.

## 24 · Thank you

*0:15, at 21:45*

Thank you. The reference implementation, the evaluation suite and all session data are in the repository on the slide. I am happy to take questions.

## 25 · Backup: Agent mandates in full

*backup*

Backup. The full mandate set, in case someone asks what the constraints actually are. Five boundary constraints per agent; F marks a prohibition, O an obligation. Note that the Central orchestrator carries obligations, consult at least one sub-agent and surface all violations, whereas the specialists carry mostly prohibitions.

## 26 · Backup: Threats to validity

*backup*

Backup, threats to validity. Internal: deterministic scoring removes evaluator subjectivity, and expected rules were derived from the Mandate definitions. Construct: ATC measures population, not semantic correctness; CDA measures latency, not reliability. External: one domain, one model, a proof of concept. The core should transfer where competence admits a sortal boundary, norms are decidable prohibitions, Mandates are session-stable, and the domain tolerates lexicographic priority. Conclusion validity: BVC and CGP vary by 2.7 points over ten runs; the adversarial claim rests on zero forced-pass in forty evaluations, categorical rather than statistical.

---

## Anticipated questions

**Is this not just guardrails?** Guardrails filter a single model's output. AI-Intent models inter-agent accountability: a declared per-agent action boundary, an external enforcement role, and a trace derived as a well-formedness condition. Guardrails could implement part of the Enforcement pillar; they do not supply the modeling constructs.

**The Compliance Agent is itself a language model, so where does R2 come from?** In the reference implementation the gate is a hybrid. Deterministic predicate checks run first and are final; a semantic check is consulted only where no deterministic predicate applies, and a deterministic failure overrides a semantic pass. Independence means the evaluator is a separate component with its own rule registry, not that it is free of any model.

**How is this different from GAIA permissions?** GAIA permissions are design-time declarations assumed to hold at runtime. AI-Intent adds the runtime verdict per action, the revision loop with a recorded forced block, and the trace as a structural model element. The Mandate construct is compatible with a GAIA role model.

**Does it transfer beyond finance?** The domain-independent core transfers where competence admits a sortal in-or-out-of-scope boundary, norms are prohibitions expressible as decidable predicates, Mandates are stable within a session, and the domain accepts that a compliant non-answer beats a non-compliant answer. Transfer is poor where norms admit routine exceptions or require renegotiation.

**What if the predicate is wrong?** Then the gate enforces the wrong rule silently, and BVC still reports containment. This is our most important limitation. The evaluation does not independently verify specification-to-predicate consistency because expected rules and predicates share provenance. The ontological future-work track asks whether design-time reasoning over the OntoUML model can catch such inconsistencies.

**Why such a small model?** To show that the guarantees come from the structure, not from model capability. The gate held with an eight-billion-parameter model; what degraded was trace population and revision quality, which are instruction-following properties.
