// The new cabinet: every button leads somewhere real, and the page loads the new files.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const web = path.join(__dirname, '../webapp');
const js = fs.readFileSync(path.join(web, 'cab.js'), 'utf8');
const html = fs.readFileSync(path.join(web, 'index.html'), 'utf8');

assert.match(html, /\/static\/cab\.js\?v=\d+/, 'index.html loads cab.js');
assert.match(html, /\/static\/cab\.css\?v=\d+/, 'index.html loads cab.css');
assert.match(html, /telegram-web-app\.js/, 'index.html loads the Telegram SDK');
assert.match(html, /id="root"/);
assert.match(html, /id="toast"/);
assert.match(html, /id="webBack"/);

const screens = new Set([...js.matchAll(/^\s+SCR\.(\w+)\s*=/gm)].map((m) => m[1]));
const actionsBlock = js.slice(js.indexOf('const ACT = {'), js.indexOf('let loginSeq'));
const actions = new Set([...actionsBlock.matchAll(/^ {4}(?:async )?(\w+)(?:\(|:|,)/gm)].map((m) => m[1]).concat(['back', 'home']));

const goTargets = [...js.matchAll(/data-go="(\w+)"/g)].map((m) => m[1]);
const goCalls = [...js.matchAll(/\bgo\("(\w+)"/g)].map((m) => m[1]);
for (const key of new Set([...goTargets, ...goCalls])) assert.ok(screens.has(key), `screen "${key}" exists`);

const acts = [...js.matchAll(/data-act="(\w+)"/g)].map((m) => m[1]);
for (const act of new Set(acts)) assert.ok(actions.has(act), `action "${act}" exists`);

for (const key of ['home', 'topup', 'method', 'wait', 'wiz1', 'wiz2', 'wiz3', 'device', 'feedback', 'friends', 'history', 'support', 'faq', 'settings', 'promo', 'promise', 'gift', 'login']) {
  assert.ok(screens.has(key), `screen "${key}" is defined`);
}

// Every endpoint the cabinet calls is one the server has.
const server = fs.readFileSync(path.join(__dirname, '../app/web.py'), 'utf8');
const routes = [...server.matchAll(/add_(?:get|post|delete)\("([^"]+)"/g)].map((m) => m[1].replace(/\{[^}]+\}/g, 'X'));
const calls = [...js.matchAll(/(?:api|post)\(\s*[`"](\/api\/[^`"]+)[`"]/g)].map((m) => m[1].replace(/\$\{[^}]+\}/g, 'X').split('?')[0]);
for (const c of new Set(calls)) assert.ok(routes.includes(c), `server route for ${c}`);

// User text goes through esc() before it reaches innerHTML.
const vm = require('node:vm');
const escSrc = js.match(/const esc = [^\n]+/)[0];
const ctx = {};
vm.createContext(ctx);
vm.runInContext(escSrc.replace('const esc', 'globalThis.esc'), ctx);
assert.equal(ctx.esc('<img src=x onerror=alert(1)>"\''), '&lt;img src=x onerror=alert(1)&gt;&quot;&#39;');
assert.match(js, /esc\(d\.title/, 'device titles are escaped');
assert.match(js, /esc\(m\.body/, 'support messages are escaped');
assert.match(js, /esc\(q\.q\)/, 'FAQ questions are escaped');

console.log('cabinet ui ok:', screens.size, 'screens,', new Set(acts).size, 'actions');
