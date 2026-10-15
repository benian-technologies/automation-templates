#!/usr/bin/env node
// Offline demonstration of the Code nodes shipped in this repository.
// Provider responses are fictional. No HTTP client, credential or n8n instance is used.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');

function workflow(file) { return JSON.parse(fs.readFileSync(path.join(root, file), 'utf8')); }
function code(w, name) {
  const node = w.nodes.find(n => n.name === name && n.type === 'n8n-nodes-base.code');
  assert(node, `Missing Code node: ${name}`);
  return node.parameters.jsCode;
}
function execute(source, scope) {
  return vm.runInNewContext(`(function(){${source}\n})()`, scope, {timeout: 1000})[0].json;
}
function prepare(w, body, enabled = true) {
  let source = code(w, 'Prepare Request');
  if (enabled) {
    assert.equal((source.match(/"enabled": false/g) || []).length, 1);
    source = source.replace('"enabled": false', '"enabled": true');
  }
  return execute(source, {$json: {body}});
}
function finish(w, prepared, output) {
  const response = {statusCode: 200, body: {type: 'message', stop_reason: 'end_turn', content: [{type: 'text', text: JSON.stringify(output)}]}};
  return execute(code(w, 'Validate Model Output'), {
    $json: response,
    $: name => { assert.equal(name, 'Prepare Request'); return {first: () => ({json: prepared})}; },
  });
}
function show(name, result) { console.log(JSON.stringify({case: name, ...result}, null, 2)); }

function faq() {
  const w = workflow('approved-faq-chatbot.json');
  const request = {requestId: 'demo-faq-001', question: 'When is support open?'};
  const disabled = prepare(w, request, false);
  assert.equal(disabled.httpStatus, 503);
  show('Unconfigured export', disabled);
  const ready = prepare(w, request);
  assert.equal(ready.route, 'model');
  const answer = finish(w, ready, {articleIds: ['hours']});
  assert.equal(answer.result.answer, ready.context.articles[0].answer);
  assert.equal(answer.result.contactCreated, false);
  show('Fictional model selects approved hours', answer);
  const handoff = prepare(w, {...request, requestHuman: true});
  assert.equal(handoff.route, 'respond');
  assert.equal(handoff.result.status, 'human_handoff');
  show('Visitor asks for a person; model is bypassed', handoff);
  const rejected = finish(w, ready, {articleIds: ['invented-refund-policy']});
  assert.equal(rejected.httpStatus, 502);
  show('Fictional model invents an article ID', rejected);
}

function editorial() {
  const w = workflow('cited-editorial-packet.json');
  const body = {
    requestId: 'demo-editorial-001', topic: 'A clearer implementation handoff', sourceUseApproved: true,
    sources: [{id: 'demo-guide', title: 'Fictional handoff guide', url: 'https://example.com/handoff',
      excerpt: 'Assign one reviewer before implementation starts. Keep a written record of the agreed scope.'}],
  };
  const ready = prepare(w, body);
  assert.equal(ready.route, 'model');
  const generated = {headline: 'Give each handoff a reviewer', angle: 'A small checklist for an implementation team.',
    sections: [{heading: 'Decide who reviews the work', points: [{claim: 'Name a reviewer before implementation.', sourceId: 'demo-guide', evidenceQuote: 'Assign one reviewer before implementation starts.'}]}]};
  const accepted = finish(w, ready, generated);
  assert.equal(accepted.result.status, 'needs_editor_review');
  assert.equal(accepted.result.checks.publication, 'not_attempted');
  show('Exact supplied quote becomes a review packet', accepted);
  const forged = JSON.parse(JSON.stringify(generated));
  forged.sections[0].points[0].evidenceQuote = 'This process increases revenue by 70 percent.';
  const rejected = finish(w, ready, forged);
  assert.equal(rejected.httpStatus, 502);
  show('Invented quote is rejected', rejected);
  const missingApproval = prepare(w, {...body, sourceUseApproved: false});
  assert.equal(missingApproval.httpStatus, 400);
  show('Source-use approval is missing; model is bypassed', missingApproval);
}

function office() {
  const w = workflow('office-hours-status.json');
  const defaults = execute(code(w, 'Configure Office'), {});
  const office = {...defaults, time_zone: 'America/Chicago', weekly_hours: {
    Monday: [['09:00', '12:00'], ['13:00', '17:00']],
    Tuesday: [['22:00', '02:00']], Wednesday: [], Thursday: [], Friday: [], Saturday: [], Sunday: [],
  }};
  const cases = [
    ['One minute before opening', '2026-10-12T13:59:00Z', [], false, '08:59'],
    ['Opening minute is included', '2026-10-12T14:00:00Z', [], true, '09:00'],
    ['Lunch break starts', '2026-10-12T17:00:00Z', [], false, '12:00'],
    ['Afternoon interval starts', '2026-10-12T18:00:00Z', [], true, '13:00'],
    ['Closing minute is excluded', '2026-10-12T22:00:00Z', [], false, '17:00'],
    ['Date-specific closure overrides hours', '2026-10-12T14:00:00Z', ['2026-10-12'], false, '09:00'],
    ['Tuesday overnight interval continues on Wednesday', '2026-10-14T06:59:00Z', [], true, '01:59'],
    ['Overnight closing minute is excluded', '2026-10-14T07:00:00Z', [], false, '02:00'],
    ['Previous-date closure suppresses overnight carry', '2026-10-14T06:59:00Z', ['2026-10-13'], false, '01:59'],
  ];
  for (const [name, timestamp, closed_dates, expected, localTime] of cases) {
    class DemoClock extends Date { constructor(...args) { super(...(args.length ? args : [timestamp])); } }
    const result = execute(code(w, 'Compute Office Status'), {
      Date: DemoClock, $input: {first: () => ({json: {...office, closed_dates}})},
    });
    assert.equal(result.office_is_open, expected);
    assert.equal(result.local_time, localTime);
    show(name, result);
  }
}

const demos = {faq, editorial, office};
const selected = process.argv[2];
if (!Object.hasOwn(demos, selected)) {
  console.error('Usage: node walkthroughs/run-workflow-demo.cjs faq|editorial|office');
  process.exit(2);
}
console.log('OFFLINE DEMONSTRATION: fictional inputs, no provider calls, no stored customer data.');
demos[selected]();
console.log('All demonstrated expectations matched. This is Code-node execution, not a live n8n/provider acceptance run.');
