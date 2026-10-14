import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const flow = JSON.parse(fs.readFileSync(new URL('../workflow.json', import.meta.url)));
const executable = flow.nodes.filter(n => n.type !== 'n8n-nodes-base.stickyNote');
assert.equal(executable.length, 7);
assert.equal(flow.active, false);
assert.deepEqual(flow.pinData, {});
assert.equal(flow.settings.saveDataSuccessExecution, 'none');
assert.equal(flow.settings.saveDataErrorExecution, 'none');
assert.equal(flow.settings.saveManualExecutions, false);
assert.ok(flow.nodes.every(n => !n.credentials));
const http = executable.find(n => n.type.endsWith('.httpRequest'));
assert.equal(http.parameters.url, 'http://127.0.0.1:8787/v1/tick');
assert.equal(http.parameters.method, 'POST');
assert.equal(http.retryOnFail, false);
assert.equal(http.parameters.options.redirect.redirect.followRedirects, false);
assert.equal(http.onError, 'stopWorkflow');
assert.deepEqual(flow.connections['Wait for source pacing'].main[0], [{node:'Collect bounded batch',type:'main',index:0}]);
const validate = executable.find(n => n.name === 'Validate collection receipt').parameters.jsCode;
const receipt = {job_id:'public-docs-demo',mode:'offline_demo',state:'complete',continue:false,wait_seconds:0,reason:null,frontier:{done:3,blocked:1},frontier_truncated:false,requests:4,charged_bytes:500,pages:3,unique_documents:2};
function run(r) { return vm.runInNewContext(`(function(){${validate}})()`, {$input:{first:()=>({json:r})},$:(name)=>({first:()=>({json:{job_id:'public-docs-demo'}})})}); }
assert.equal(run(receipt)[0].json.pages, 3);
const negatives = [{job_id:'other'}, {continue:true}, {mode:'unknown'}, {pages:-1}, {unique_documents:4}, {frontier:{secret:1}}, {reason:'arbitrary'}, {extra:'private'},
  {frontier:{pending:1}}, {frontier:{fetching:1}}, {frontier:{failed:1}}, {frontier_truncated:true}, {reason:'page_budget'},
  {state:'partial'}, {state:'paused',reason:'page_budget'}, {state:'running',continue:true,wait_seconds:1}];
for (const changed of negatives) {
  assert.throws(()=>run({...receipt,...changed}));
}
assert.equal(run({...receipt,state:'running',continue:true,wait_seconds:2,frontier:{pending:1}})[0].json.continue,true);
assert.equal(run({...receipt,state:'paused',reason:'page_budget',frontier:{pending:1}})[0].json.continue,false);
assert.equal(run({...receipt,state:'partial',frontier:{failed:1}})[0].json.state,'partial');
console.log(JSON.stringify({ok:true,executable_nodes:7,receipt_negative_cases:negatives.length,scope:'workflow shape and exported Code; not native engine execution'}));
