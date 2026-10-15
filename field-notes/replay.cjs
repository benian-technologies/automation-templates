#!/usr/bin/env node
// Replay fictional provider output through the published workflow's actual Code nodes.
// This executes trusted repository code, not arbitrary user-supplied JavaScript.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const clone = value => JSON.parse(JSON.stringify(value));
function load(name) { return JSON.parse(fs.readFileSync(path.join(root, name), 'utf8')); }
function code(w, name) {
  const node = w.nodes.find(n => n.name === name && n.type === 'n8n-nodes-base.code');
  assert(node, `Missing Code node: ${name}`);
  return node.parameters.jsCode;
}
function run(source, scope) {
  return vm.runInNewContext(`(function(){${source}\n})()`, scope, {timeout: 1000})[0].json;
}
function prepare(w, body, enabled = true) {
  let source = code(w, 'Prepare Request');
  assert.equal((source.match(/"enabled": false/g) || []).length, 1);
  if (enabled) source = source.replace('"enabled": false', '"enabled": true');
  return run(source, {$json: {body}});
}
function finish(w, prepared, fixture, stopReason = 'end_turn') {
  const raw = {statusCode: 200, body: {type: 'message', stop_reason: stopReason,
    content: [{type: 'text', text: JSON.stringify(fixture)}]}};
  return run(code(w, 'Validate Model Output'), {$json: raw,
    $: name => { assert.equal(name, 'Prepare Request'); return {first: () => ({json: prepared})}; }});
}
function show(name, result, expectedStatus, expectedHttp) {
  assert.equal(result.result.status, expectedStatus, name);
  assert.equal(result.httpStatus, expectedHttp, name);
  console.log(JSON.stringify({case: name, ...result}, null, 2));
}
function faq() {
  const w = load('approved-faq-chatbot.json');
  const input = load('field-notes/examples/faq-request.json');
  const ready = prepare(w, input);
  assert.equal(ready.route, 'model');
  const answered = finish(w, ready, {articleIds: ['hours']});
  assert.equal(answered.result.answer, ready.context.articles.find(a => a.id === 'hours').answer);
  assert.equal(answered.result.contactCreated, false);
  show('approved-answer', answered, 'answered_from_approved_faq', 200);
  show('empty-selection', finish(w, ready, {articleIds: []}), 'human_handoff', 200);
  const human = prepare(w, {...input, requestHuman: true});
  assert.equal(human.route, 'respond');
  show('explicit-person-request', human, 'human_handoff', 200);
  show('unknown-id', finish(w, ready, {articleIds: ['invented-refund']}), 'unavailable', 502);
  show('duplicate-id', finish(w, ready, {articleIds: ['hours', 'hours']}), 'unavailable', 502);
  show('extra-answer-field', finish(w, ready, {articleIds: ['hours'], answer: 'Invented answer.'}), 'unavailable', 502);
  const irrelevant = prepare(w, {...input, question: 'Can you change the address on my account?'});
  show('valid-id-but-irrelevant-answer', finish(w, irrelevant, {articleIds: ['hours']}), 'answered_from_approved_faq', 200);
  show('disabled-export', prepare(w, input, false), 'setup_required', 503);
}
function editorial() {
  const w = load('cited-editorial-packet.json');
  const input = load('field-notes/examples/editorial-request.json');
  const proposed = load('field-notes/examples/editorial-provider-response.json');
  const ready = prepare(w, input);
  assert.equal(ready.route, 'model');
  const accepted = finish(w, ready, proposed);
  assert.equal(accepted.result.checks.publication, 'not_attempted');
  assert.equal(accepted.result.checks.semanticAccuracy, 'requires_human_review');
  show('exact-quote-review-packet', accepted, 'needs_editor_review', 200);
  const invented = clone(proposed);
  invented.sections[0].points[0].evidenceQuote = 'The process guarantees that projects never change.';
  show('invented-quote', finish(w, ready, invented), 'unavailable', 502);
  const misleading = clone(proposed);
  misleading.sections[0].points[0].claim = 'A named reviewer guarantees that a project will never change.';
  show('real-quote-misleading-claim', finish(w, ready, misleading), 'needs_editor_review', 200);
  show('missing-source-approval', prepare(w, {...input, sourceUseApproved: false}), 'invalid_request', 400);
  show('truncated-provider-output', finish(w, ready, proposed, 'max_tokens'), 'unavailable', 502);
  const unknown = clone(proposed);
  unknown.sections[0].points[0].sourceId = 'source-not-supplied';
  show('unknown-source-id', finish(w, ready, unknown), 'unavailable', 502);
}
const modes = {faq, editorial};
if (!Object.hasOwn(modes, process.argv[2])) {
  console.error('Usage: node field-notes/replay.cjs faq|editorial');
  process.exit(2);
}
console.log('FICTIONAL OFFLINE FIXTURES. No provider, webhook or complete n8n graph is executed.');
modes[process.argv[2]]();
console.log('All expected results matched. Semantic relevance and truth were deliberately not assumed.');
