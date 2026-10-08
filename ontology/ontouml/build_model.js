// Build the AI-Intent conceptual model as an OntoUML project, validate it against
// the OntoUML JSON schema, run the OntoUML syntactic verification, and transform
// it to gUFO. Outputs are written next to this file.
//
//   npm install            (once; installs ontouml-js 0.5.0)
//   node build_model.js
//
// Outputs: ai-intent.ontouml.json, ai-intent.gufo.ttl, verification.json

const fs = require('fs');
const path = require('path');
const o = require('ontouml-js');

const mlt = (text) => (o.MultilingualText ? new o.MultilingualText(text) : undefined);
const project = new o.Project({ name: 'AI-Intent' });
const model = project.createModel({ name: 'AI-Intent conceptual model' });

// ---------------------------------------------------------------------------
// Declaration pillar: parties, mandates, rules
// ---------------------------------------------------------------------------
const principal = model.createKind('Principal');
const agent = model.createKind('Agent');
const orchestrator = model.createSubkind('Orchestrator');
const specialist = model.createSubkind('Specialist');
model.createPartitionFromClasses(agent, [orchestrator, specialist], 'agent kind');

const delegator = model.createRoleMixin('Delegator');
const principalDelegator = model.createRole('Principal as Delegator');
const orchestratorDelegator = model.createRole('Orchestrator as Delegator');
const delegatee = model.createRole('Delegatee');
model.createGeneralization(principal, principalDelegator);
model.createGeneralization(orchestrator, orchestratorDelegator);
model.createGeneralization(delegator, principalDelegator);
model.createGeneralization(delegator, orchestratorDelegator);
model.createGeneralization(agent, delegatee);

// The Mandate is a normative description (UFO-C). OntoUML 2 has no stereotype for
// normative descriptions, so it is modelled as a kind whose content is carried by
// its boundary constraints; see the paper's Section 8 on this limitation.
const mandate = model.createKind('Mandate');
mandate.description = mlt('Normative description: intent scope, boundary constraints, risk parameters. Content of a Commitment.');
const boundaryConstraint = model.createIntrinsicMode('Boundary Constraint');
boundaryConstraint.description = mlt('Negative duty <text, predicate, deontic type> borne by the Mandate.');
const regulatoryRule = model.createKind('Regulatory Rule');
const regulatoryFramework = model.createKind('Regulatory Framework');

model.createCharacterizationRelation(boundaryConstraint, mandate, 'constraint inheres in mandate');
model.createBinaryRelation(boundaryConstraint, regulatoryRule, 'operationalised by');
model.createBinaryRelation(regulatoryRule, regulatoryFramework, 'drawn from');
model.createBinaryRelation(mandate, mandate, 'sub-mandate of');
model.createBinaryRelation(principal, mandate, 'owns');
model.createBinaryRelation(agent, mandate, 'governed by');

// ---------------------------------------------------------------------------
// Delegation as a UFO-C relator constituted by commitment and claim
// ---------------------------------------------------------------------------
const delegation = model.createRelator('Delegation');
const commitment = model.createExtrinsicMode('Commitment');
const claim = model.createExtrinsicMode('Claim');

model.createMediationRelation(delegation, delegator, 'mediates delegator');
model.createMediationRelation(delegation, delegatee, 'mediates delegatee');
model.createCharacterizationRelation(commitment, delegatee, 'commitment inheres in delegatee');
model.createExternalDependencyRelation(commitment, delegator, 'commitment depends on delegator');
model.createCharacterizationRelation(claim, delegator, 'claim inheres in delegator');
model.createExternalDependencyRelation(claim, delegatee, 'claim depends on delegatee');
model.createBinaryRelation(commitment, delegation, 'commitment constitutes delegation');
model.createBinaryRelation(claim, delegation, 'claim constitutes delegation');
model.createBinaryRelation(claim, commitment, 'counterpart of');
model.createBinaryRelation(mandate, commitment, 'content of');
model.createBinaryRelation(delegation, delegation, 'parent delegation');

// ---------------------------------------------------------------------------
// Enforcement pillar: events, verdicts, dispositions
// ---------------------------------------------------------------------------
const session = model.createEvent('Session');
const logEntry = model.createEvent('Log Entry');
const proposedAction = model.createEvent('Proposed Action');
const complianceEvent = model.createEvent('Compliance Event');
const approval = model.createEvent('Approval');
const rejection = model.createEvent('Rejection');
const block = model.createEvent('Block');
model.createGeneralization(logEntry, proposedAction);
model.createGeneralization(logEntry, complianceEvent);
model.createPartitionFromClasses(complianceEvent, [approval, rejection, block], 'verdict outcome');
model.createPartWholeRelation(logEntry, session, 'proper part of');

model.createParticipationRelation(agent, logEntry, 'agent participates in entry');
model.createParticipationRelation(principal, session, 'principal participates in session');
model.createBinaryRelation(agent, proposedAction, 'proposes');

const verdict = model.createIntrinsicMode('Compliance Verdict');
model.createCharacterizationRelation(verdict, agent, 'verdict inheres in agent');
model.createHistoricalDependenceRelation(verdict, proposedAction, 'historically depends on');
model.createBinaryRelation(complianceEvent, verdict, 'issues');
model.createBinaryRelation(verdict, regulatoryRule, 'violates');

const disposition = model.createIntrinsicMode('Disposition');
disposition.description = mlt('Kind, degree in [0,1], triggering situation and characteristic rule set.');
model.createCharacterizationRelation(disposition, agent, 'disposition inheres in agent');
model.createManifestationRelation(disposition, rejection, 'manifested in rejection');
model.createManifestationRelation(disposition, block, 'manifested in block');

// ---------------------------------------------------------------------------
// Auditability pillar: situations brought about by events
// ---------------------------------------------------------------------------
const trace = model.createSituation('Accountability Trace');
const breach = model.createSituation('Commitment Breach');
model.createBringsAboutRelation(session, trace, 'session brings about trace');
model.createBinaryRelation(trace, logEntry, 'comprises');
model.createBringsAboutRelation(block, breach, 'block brings about breach');
model.createBinaryRelation(breach, commitment, 'breaches');
model.createBinaryRelation(breach, delegator, 'answerable to');

// ---------------------------------------------------------------------------
// Validate, verify, transform, write
// ---------------------------------------------------------------------------
const out = (name) => path.join(__dirname, name);

const schemaValid = o.serializationUtils.validate(project);
const verification = new o.OntoumlVerification(project).run();
const issues = (verification.result || []).map((i) => ({
  severity: i.severity,
  code: i.code,
  title: i.title,
  description: i.description,
  source: i.source && i.source.name ? i.source.name : undefined,
}));
const gufo = new o.Ontouml2Gufo(project, {
  baseIri: 'https://github.com/InformationServiceSystems/ai-intent/ontology/ontouml#',
  format: 'Turtle',
  createObjectProperty: true,
  createInverses: false,
  prefixPackages: false,
  uriFormatBy: 'name',
}).run();

fs.writeFileSync(out('ai-intent.ontouml.json'), JSON.stringify(project, null, 1));
fs.writeFileSync(out('ai-intent.gufo.ttl'), gufo.result);
fs.writeFileSync(out('verification.json'), JSON.stringify({
  schema_valid: schemaValid === true,
  issue_count: issues.length,
  issues,
  gufo_transformation_issues: (gufo.issues || []).map((i) => ({ code: i.code, title: i.title, description: i.description })),
}, null, 1));

const classes = model.getAllClasses().length;
const relations = model.getAllRelations().length;
const generalizations = model.getAllGeneralizations().length;
console.log(`classes ${classes}, relations ${relations}, generalizations ${generalizations}`);
console.log(`schema valid: ${schemaValid === true}`);
console.log(`verification issues: ${issues.length}`);
issues.forEach((i) => console.log(`  [${i.severity}] ${i.code} ${i.source ? '(' + i.source + ')' : ''}: ${i.title}`));
console.log(`gUFO transformation issues: ${(gufo.issues || []).length}`);
