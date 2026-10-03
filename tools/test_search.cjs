// Regression checks for search intent and URL state; no browser dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const data = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  .match(/<script id="entries" type="application\/json">(.*?)<\/script>/s)[1];
const code = fs.readFileSync(path.join(__dirname, 'search.js'), 'utf8');

function page(url) {
  const elements = new Map();
  const cards = new Map();
  function element(id) {
    if (id.startsWith('entry-')) return cards.get(id) || null;
    if (!elements.has(id)) elements.set(id, {
      value: '', options: [{ value: '' }], handlers: {}, textContent: '',
      append(option) { this.options.push(option); },
      addEventListener(event, handler) { this.handlers[event] = handler; },
      set innerHTML(html) {
        this.html = html;
        if (id === 'list') {
          cards.clear();
          for (const match of html.matchAll(/<article class="card" id="([^"]+)"/g)) {
            const details = { open: false };
            cards.set(match[1], { details, querySelector: () => details, scrollIntoView() {} });
          }
        }
      },
      get innerHTML() { return this.html; }
    });
    return elements.get(id);
  }
  element('entries').textContent = data;
  const location = { href: url, get hash() { return new URL(this.href).hash; } };
  const context = vm.createContext({
    document: { getElementById: element, createElement: () => ({}) },
    location, URL, history: { replaceState(_, __, href) { location.href = href; } },
    window: { addEventListener() {} }
  });
  vm.runInContext(code, context);
  return { element, location, cards,
    run: expression => vm.runInContext(expression, context),
    query(value) { element('query').value = value; element('search-submit').handlers.click(); },
    ids() { return [...cards.keys()]; }
  };
}

const site = 'https://example.test/guide/index.html';
const search = page(site);
for (const query of ['被夸奖怎么回复', '别人夸我如何回应', '老师夸我怎么回复']) {
  search.query(query);
  assert.equal(search.ids()[0], 'entry-7.10', query);
}
search.query('送礼火星矿石');
assert.equal(search.cards.size, 0, 'Unknown content must not become a broad gift search');
search.query('怎么送礼');
assert(search.ids().includes('entry-4.4'));
search.element('chapter').value = '7';
search.element('chapter').handlers.change();
assert(search.ids().every(id => id.startsWith('entry-7.')));

const jumped = page(site + '#entry-4.1');
assert(jumped.cards.get('entry-4.1').details.open);
jumped.query('送礼');
assert.equal(new URL(jumped.location.href).hash, '');
const refreshed = page(jumped.location.href);
assert.equal(refreshed.element('query').value, '送礼');
assert.deepEqual(refreshed.ids(), jumped.ids());

const deepLink = page(site + '?q=送礼#entry-3.1');
assert(deepLink.cards.get('entry-3.1').details.open);
assert.equal(new URL(deepLink.location.href).hash, '#entry-3.1');
deepLink.element('reset').handlers.click();
assert.equal(new URL(deepLink.location.href).hash, '');
assert.equal(new URL(deepLink.location.href).search, '');
assert.equal(deepLink.cards.size, 64);

const offline = page('file:///tmp/index.html#entry-4.1');
offline.query('借钱不还');
assert(offline.ids().includes('entry-4.2'));
assert.equal(new URL(offline.location.href).hash, '');
console.log('Search regression checks passed: intent, filters, refresh, jumps, reset and offline URL.');
