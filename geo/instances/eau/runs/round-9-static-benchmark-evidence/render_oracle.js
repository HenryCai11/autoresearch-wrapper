// Run in a Slurm CPU job: exercise the unchanged site's result renderer only.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const start = source.indexOf('const results = {');
const stop = source.indexOf("document.querySelectorAll('[data-model]').forEach(button => button.addEventListener");
assert(start >= 0 && stop > start, 'Known renderer boundary must be present');
const elements = Object.fromEntries(['#result-charts', '#table-caption', '#results-table-body'].map(id => [id, {innerHTML: '', textContent: ''}]));
const buttons = ['qwen3', 'qwen25'].map(model => ({dataset: {model}, attributes: {}, setAttribute(k, v) {this.attributes[k] = v;}}));
const context = vm.createContext({document: {
  querySelector(selector) {assert(selector in elements); return elements[selector];},
  querySelectorAll(selector) {assert.equal(selector, '[data-model]'); return buttons;},
}});
vm.runInContext(source.slice(start, stop), context, {timeout: 1000});
const capture = key => {
  vm.runInContext(`renderResults('${key}')`, context, {timeout: 1000});
  assert.equal(buttons.find(b => b.dataset.model === key).attributes['aria-pressed'], 'true');
  assert.equal(buttons.find(b => b.dataset.model !== key).attributes['aria-pressed'], 'false');
  return {charts: elements['#result-charts'].innerHTML, table: elements['#results-table-body'].innerHTML,
          caption: elements['#table-caption'].textContent};
};
const qwen3 = capture('qwen3');
const qwen25 = capture('qwen25');
assert.notEqual(qwen3.table, qwen25.table);
assert.equal((qwen3.charts.match(/class="chart-card"/g) || []).length, 3);
assert.equal((qwen3.table.match(/<tr/g) || []).length, 9);
assert.equal((qwen25.table.match(/<tr/g) || []).length, 9);
assert.deepEqual(capture('qwen3'), qwen3, 'Switch back to the default must reproduce the exact content');
const data = JSON.parse(vm.runInContext('JSON.stringify(results)', context));
assert.deepEqual(data.qwen3.rows.find(r => r[0] === 'eau'), ['eau', .623, .685, .600, .627]);
process.stdout.write(JSON.stringify({node_version: process.version, method: 'Isolated unchanged renderResults function with a minimal DOM stub; not a full-browser test',
  renderer_switch_checks_passed: true, default_model: 'qwen3', qwen3, qwen25, source_data: data}));
