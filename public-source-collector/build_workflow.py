#!/usr/bin/env python3
"""Generate the credential-free, inactive n8n controller export."""
import json
from pathlib import Path


def build():
    nodes = []
    def add(name, kind, version, parameters, x, y=0):
        nodes.append({"id": name.lower().replace(" ", "-"), "name": name, "type": "n8n-nodes-base." + kind,
                      "typeVersion": version, "position": [x, y], "parameters": parameters})
    add("Start manually", "manualTrigger", 1, {}, 0)
    add("Select collection job", "code", 2, {"jsCode": "// Match the job_id in the service config. No source URLs or tokens go here.\nreturn [{json:{job_id:'public-docs-demo'}}];"}, 220)
    add("Collect bounded batch", "httpRequest", 4.2, {
        "method": "POST", "url": "http://127.0.0.1:8787/v1/tick", "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth", "sendBody": True, "contentType": "raw", "rawContentType": "application/json",
        "body": "={{ JSON.stringify({job_id:$json.job_id}) }}",
        "options": {"timeout": 180000, "redirect": {"redirect": {"followRedirects": False}}}}, 460)
    nodes[-1]["retryOnFail"] = False
    nodes[-1]["onError"] = "stopWorkflow"
    add("Validate collection receipt", "code", 2, {"jsCode": """const r = $input.first().json;
const keys = ['job_id','mode','state','continue','wait_seconds','reason','frontier','frontier_truncated','requests','charged_bytes','pages','unique_documents'].sort();
if (JSON.stringify(Object.keys(r).sort()) !== JSON.stringify(keys)) throw new Error('invalid_receipt_fields');
if (r.job_id !== $('Select collection job').first().json.job_id) throw new Error('job_mismatch');
if (!['offline_demo','live'].includes(r.mode) || !['running','complete','partial','paused'].includes(r.state)) throw new Error('invalid_receipt');
if (typeof r.continue !== 'boolean' || r.continue !== (r.state === 'running')) throw new Error('invalid_continuation');
if (typeof r.frontier_truncated !== 'boolean' || !r.frontier || typeof r.frontier !== 'object' || Array.isArray(r.frontier)) throw new Error('invalid_frontier');
for (const [k,v] of Object.entries(r.frontier)) {
  if (!['pending','fetching','done','failed','blocked','skipped','redirect'].includes(k) || !Number.isSafeInteger(v) || v < 0 || v > 10000) throw new Error('invalid_frontier');
}
for (const k of ['wait_seconds','requests','charged_bytes','pages','unique_documents']) {
  if (!Number.isSafeInteger(r[k]) || r[k] < 0) throw new Error('invalid_count');
}
if (r.wait_seconds > 86400 || (r.continue && r.wait_seconds < 1) || r.requests > 10000 || r.pages > 5000 || r.unique_documents > r.pages || r.charged_bytes > 100000000) throw new Error('receipt_out_of_bounds');
if (r.reason !== null && !['time_budget','request_budget','byte_budget','page_budget'].includes(r.reason)) throw new Error('invalid_reason');
const pending = (r.frontier.pending || 0) + (r.frontier.fetching || 0);
const incomplete = (r.frontier.failed || 0) > 0 || r.frontier_truncated;
if (Object.values(r.frontier).reduce((a,b)=>a+b,0) > 10000) throw new Error('invalid_frontier_total');
if (r.state === 'running' && (pending === 0 || r.reason !== null)) throw new Error('invalid_running_state');
if (r.state === 'paused' && (pending === 0 || r.reason === null)) throw new Error('invalid_paused_state');
if (r.state === 'complete' && (pending > 0 || incomplete || r.reason !== null)) throw new Error('invalid_complete_state');
if (r.state === 'partial' && (pending > 0 || !incomplete || r.reason !== null)) throw new Error('invalid_partial_state');
return [{json:r}];"""}, 700)
    add("More work within budget", "if", 2.2, {"conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
        "conditions": [{"id": "continue", "leftValue": "={{ $json.continue }}", "rightValue": True,
                        "operator": {"type": "boolean", "operation": "true", "singleValue": True}}], "combinator": "and"}, "options": {}}, 950)
    add("Wait for source pacing", "wait", 1.1, {"resume": "timeInterval", "amount": "={{ $json.wait_seconds }}", "unit": "seconds"}, 1170, -130)
    add("Return final receipt", "code", 2, {"jsCode": "// Complete means the bounded queue is exhausted, not the whole web.\n// Partial and paused require inspecting local receipts before a new job.\nreturn $input.all();"}, 1170, 130)
    add("Setup and permission", "stickyNote", 1, {"content": "## 1. Start the included collector service\nThis template needs collector.py and serve.py from the accompanying package. Start in offline demo mode first. The service and n8n must share a host/network namespace.\n\nSelect a Header Auth credential on the HTTP node: Authorization: Bearer <private controller token>. Keep the value in n8n's credential store. The exported workflow contains no credential binding.", "height": 330, "width": 440}, 0, -430)
    add("Collection boundary", "stickyNote", 1, {"content": "## 2. Configure a permitted source before live use\nAllowlisted HTTPS origins and paths, permission confirmation, robots checks, request/byte/time budgets and pacing are enforced by the included service. No browser, authentication, paid actor launches, email harvesting or outreach.\n\nUse the optional completed-export importer for discovery. It retains only in-scope URLs and import receipts.", "height": 330, "width": 440}, 470, -430)
    add("Durability and result", "stickyNote", 1, {"content": "## 3. Review the receipt\nThe workflow is manual and inactive. The service commits state to SQLite before requests and supports continuation after a restart. No automatic HTTP retries or redirects.\n\nThe final node distinguishes complete, partial and paused. Page data stays in the local store, not workflow execution output. See README for offline proof, export and recovery.", "height": 330, "width": 440}, 940, -560)
    edge = lambda name: {"node": name, "type": "main", "index": 0}
    chain = ["Start manually", "Select collection job", "Collect bounded batch", "Validate collection receipt", "More work within budget"]
    connections = {a: {"main": [[edge(b)]]} for a, b in zip(chain, chain[1:])}
    connections["More work within budget"] = {"main": [[edge("Wait for source pacing")], [edge("Return final receipt")]]}
    connections["Wait for source pacing"] = {"main": [[edge("Collect bounded batch")]]}
    return {"name": "Collect permitted public pages with durable budgets and continuation", "nodes": nodes, "connections": connections,
            "active": False, "pinData": {}, "settings": {"executionOrder": "v1", "saveDataErrorExecution": "none", "saveDataSuccessExecution": "none", "saveManualExecutions": False}}


if __name__ == "__main__":
    Path(__file__).with_name("workflow.json").write_text(json.dumps(build(), indent=2) + "\n")
