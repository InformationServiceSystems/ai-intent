# OntoUML model of AI-Intent

`build_model.js` constructs the AI-Intent conceptual model as an OntoUML project with the `ontouml-js` library (version 0.5.0, the last release with the verification service and the gUFO transformation), validates it against the OntoUML JSON schema, runs the OntoUML syntactic verification, transforms it to gUFO, and writes three files:

| File | Content |
|---|---|
| `ai-intent.ontouml.json` | the model in the OntoUML JSON format (importable into the Visual Paradigm OntoUML plugin) |
| `ai-intent.gufo.ttl` | the model transformed to a gUFO-based OWL ontology |
| `verification.json` | schema validity, verification issues, transformation issues |

```bash
cd ontology/ontouml
npm install
node build_model.js
```

## What the model contains

26 classes, 33 relations, 12 generalizations in three groups.

- **Declaration.** Principal «kind», Agent «kind» partitioned into Orchestrator and Specialist «subkind»; the roles Delegator «roleMixin» (played by a Principal or an Orchestrator) and Delegatee «role»; Mandate «kind» bearing Boundary Constraints «mode», operationalised by Regulatory Rules drawn from a Regulatory Framework.
- **Delegation (UFO-C).** Delegation «relator» mediating Delegator and Delegatee, constituted by a Commitment «extrinsicMode» (inheres in the Delegatee, externally depends on the Delegator) and a Claim «extrinsicMode» (the converse); the Mandate is the content of the Commitment.
- **Enforcement and auditability.** Session, Log Entry, Proposed Action and Compliance Event «event» (the last partitioned into Approval, Rejection, Block); Compliance Verdict «intrinsicMode» inhering in the Agent and historically dependent on the Proposed Action; Disposition «intrinsicMode» manifested in Rejection and Block events; Accountability Trace and Commitment Breach «situation» brought about by the Session and by a Block respectively.

## Known limitation

OntoUML 2 has no stereotype for normative descriptions. The Mandate is therefore modelled as a «kind» whose content is carried by its Boundary Constraints; the paper's Section 8 discusses this. Relations without an OntoUML stereotype (`constitutes`, `content of`, `comprises`, `answerable to`, `breaches`, `proper part of`) are plain associations.

## Alignment with the runtime export

`python evaluation/ontouml_alignment.py` compares, construct by construct, the gUFO superclass that the transformation of this model assigns with the superclass that the session export (`mcp/gufo_export.py`) declares. The two must agree; the test suite checks this.
