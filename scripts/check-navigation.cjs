const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const init = fs.readFileSync('assets/js/theme-init.js', 'utf8');
const site = fs.readFileSync('assets/js/site.js', 'utf8');
function fixture({ saved, mode = 'light', osDark = false, denied = false } = {}) {
  const values = new Set();
  const classes = { contains: k => values.has(k), toggle(k, force) { const enabled = force === undefined ? !values.has(k) : force; enabled ? values.add(k) : values.delete(k); } };
  const root = { classList: classes, style: { setProperty(k, v) { this[k] = v; } }, dataset: { wcThemeDefault: mode } };
  const toggle = { dataset: {}, addEventListener(k, fn) { this[k] = fn; } };
  let stored = saved;
  const storage = { getItem() { if (denied) throw Error('blocked'); return stored; }, setItem(k, v) { assert.equal(k, 'wc-color-theme'); if (denied) throw Error('blocked'); stored = v; } };
  const events = {}, windowEvents = {}, media = { matches: osDark, addEventListener(k, fn) { this[k] = fn; } };
  const context = vm.createContext({ document: { documentElement: root, addEventListener(k, fn) { events[k] = fn; }, querySelectorAll() { return [toggle]; }, querySelector() { return { getBoundingClientRect() { return { height: 64 }; } }; } }, localStorage: storage, matchMedia() { return media; }, window: { addEventListener(k, fn) { windowEvents[k] = fn; } } });
  // Sidebar controls are separate from the theme toggle.
  context.document.querySelectorAll = selector => selector === '.theme-toggle' ? [toggle] : [];
  vm.runInContext(init, context);
  vm.runInContext(site, context);
  events.DOMContentLoaded();
  return { root, toggle, media, saved: () => stored, windowEvents };
}
let runs = 0;
for (const options of [ {}, {saved:'dark'}, {saved:'light',osDark:true}, {mode:'dark'}, {mode:'system',osDark:true}, {mode:'system',osDark:false}, {denied:true}, {denied:true,mode:'dark'} ]) {
  const app = fixture(options);
  const initial = options.saved ? options.saved === 'dark' : options.mode === 'dark' || (options.mode === 'system' && options.osDark);
  assert.equal(app.root.classList.contains('dark'), Boolean(initial));
  assert.equal(app.root.style.colorScheme, initial ? 'dark' : 'light');
  assert.equal(app.root.style['--navbar-height'], '64px');
  app.toggle.click();
  assert.equal(app.root.classList.contains('dark'), !initial);
  if (!options.denied) {
    const reloaded = fixture({saved: app.saved(), mode: options.mode});
    assert.equal(reloaded.root.classList.contains('dark'), !initial);
  }
  app.toggle.click();
  assert.equal(app.root.classList.contains('dark'), Boolean(initial));
  runs++;
}
const system = fixture({mode:'system'});
system.media.change({matches:true});
assert.equal(system.root.classList.contains('dark'), true);
system.toggle.click();
system.media.change({matches:true});
assert.equal(system.root.classList.contains('dark'), false);
console.log(`PASS: ${runs} theme initialization/toggle/reload scenarios, blocked storage, system changes, and header spacing`);
