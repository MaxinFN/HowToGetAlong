// Regression checks for search intent and URL state; no browser dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const data = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  .match(/<script id="entries" type="application\/json">(.*?)<\/script>/s)[1];
const sourceData = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  .match(/<script id="source-data" type="application\/json">(.*?)<\/script>/s)[1];
const code = fs.readFileSync(path.join(__dirname, 'search.js'), 'utf8');

function page(url, storage = new Map(), blockedStorage = false) {
  const elements = new Map();
  const cards = new Map();
  function element(id) {
    if (id.startsWith('entry-')) return cards.get(id) || null;
    if (!elements.has(id)) elements.set(id, {
      value: '', checked: false, options: [{ value: '' }], handlers: {}, textContent: '',
      append(option) { this.options.push(option); },
      focus() {},
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
  element('source-data').textContent = sourceData;
  const location = { href: url, get hash() { return new URL(this.href).hash; } };
  const windowHandlers = {};
  const history = [url];
  let cursor = 0;
  const context = vm.createContext({
    document: { getElementById: element, createElement: () => ({}) },
    location, URL, history: {
      replaceState(_, __, href) { history[cursor] = location.href = href; },
      pushState(_, __, href) {
        history.splice(cursor + 1);
        history.push(href);
        cursor++;
        location.href = href;
      }
    },
    window: {
      localStorage: {
        getItem(key) { if (blockedStorage) throw new Error('Storage blocked'); return storage.get(key) || null; },
        setItem(key, value) { if (blockedStorage) throw new Error('Storage blocked'); storage.set(key, value); }
      },
      addEventListener(event, handler) { windowHandlers[event] = handler; }
    }
  });
  vm.runInContext(code, context);
  return { element, location, cards,
    run: expression => vm.runInContext(expression, context),
    query(value) { element('query').value = value; element('search-submit').handlers.click(); },
    reference(id, modifiers = {}) {
      let prevented = false;
      const link = { dataset: { ref: id } };
      element('list').handlers.click({
        target: { closest: () => link }, button: 0, ...modifiers,
        preventDefault() { prevented = true; }
      });
      return prevented;
    },
    back() {
      assert(cursor > 0, 'Related-entry navigation must create a history entry');
      location.href = history[--cursor];
      windowHandlers.popstate();
    },
    forward() {
      assert(cursor < history.length - 1);
      location.href = history[++cursor];
      windowHandlers.popstate();
    },
    ids() { return [...cards.keys()]; }
  };
}

const site = 'https://example.test/guide/index.html';
const search = page(site);
for (const entry of JSON.parse(data)) {
  search.query(entry.id);
  assert.deepEqual(search.ids(), ['entry-' + entry.id], 'Find the exact entry by number: ' + entry.id);
  search.query(entry.title);
  assert(search.ids().includes('entry-' + entry.id), 'Find an entry by its full title: ' + entry.id);
}
for (const query of ['条目 5.7', '第5.7条', '５．７', '#entry-5.7', '5.7？', '第5.7条？']) {
  search.query(query);
  assert.deepEqual(search.ids(), ['entry-5.7'], query);
}
search.query('99.1');
assert.equal(search.cards.size, 0, 'Unknown entry numbers must not search unrelated body text');
search.query('99.1？');
assert.equal(search.cards.size, 0, 'Unknown entry numbers stay strict with trailing punctuation');
search.element('chapter').value = '4';
search.query('5.7');
assert.equal(search.cards.size, 0, 'Entry-number search must respect selected filters');
search.element('chapter').value = '';
for (const [query, target] of [
  ['改作业', 'entry-1.1'], ['同学让我改作业', 'entry-1.1'],
  ['帮同学改作业', 'entry-1.1'], ['帮忙改作业', 'entry-1.1'],
  ['改 作业', 'entry-1.1'], ['改作业怎么办？', 'entry-1.1'],
  ['推荐信', 'entry-2.7'], ['老师写推荐信', 'entry-2.7'],
  ['朋友分享好消息', 'entry-6.7'], ['朋友拿到offer', 'entry-6.7'],
  ['不想去聚餐', 'entry-7.11'], ['还不确定能不能去', 'entry-7.11'],
  ['找前辈了解岗位', 'entry-10.8'], ['自我介绍', 'entry-10.8'],
  ['好久没联系的朋友', 'entry-6.2'], ['结束聊天', 'entry-7.5'],
  ['礼物怎么选', 'entry-4.4'],
  ['offer 催我答复', 'entry-10.7'], ['申请延长 offer 回复期限', 'entry-10.7'],
  ['被别人夸奖时，要如何回复', 'entry-7.10'], ['领导夸我工作做得好怎么回复', 'entry-7.10'],
  ['转发截图', 'entry-5.7'], ['老板临时让我加班', 'entry-3.1'],
  ['室友拿我的东西', 'entry-1.4'],
  ['朋友让我代签到', 'entry-1.7'], ['办公室八卦', 'entry-3.8'],
  ['朋友说不给面子', 'entry-6.8']
]) {
  search.query(query);
  assert.equal(search.ids()[0], target, query);
}
search.query('怎么样送礼');
assert(search.ids().includes('entry-4.4'), 'Longer question prefixes must not leave a stray character');
for (const query of ['被夸奖怎么回复', '别人夸我如何回应', '老师夸我怎么回复']) {
  search.query(query);
  assert.equal(search.ids()[0], 'entry-7.10', query);
}
for (const query of [
  '收到夸奖怎么回复', '收到夸赞如何回应', '收到赞美怎么回答',
  '被领导夸了怎么回', '老板夸我怎么回', '被同事夸了怎么回',
  '被夸奖怎么回复？', '被夸奖怎么回复?', '收到夸奖怎么回复？',
  '被领导夸了怎么回？', '我被领导夸了，该怎么回？'
]) {
  search.query(query);
  assert.equal(search.ids()[0], 'entry-7.10', 'Find replies to praise: ' + query);
}
for (const query of ['怎么夸别人', '如何赞美朋友']) {
  search.query(query);
  assert.equal(search.ids()[0], 'entry-7.7', 'Keep giving-praise intent distinct: ' + query);
}
search.query('借钱不还怎么办？');
assert.equal(search.ids()[0], 'entry-4.2', 'Ignore trailing question punctuation');
search.query('收到夸奖火星矿石怎么回复？');
assert.equal(search.cards.size, 0, 'Praise aliases must preserve unknown query content');
for (const [query, target] of [
  ['别人把照片发朋友圈怎么办', 'entry-5.7'], ['怎么发合照', 'entry-5.7'],
  ['转发聊天记录', 'entry-5.7'], ['群里有人被欺负怎么办', 'entry-5.8'],
  ['看到别人被冒犯怎么办', 'entry-5.8'], ['offer催我答复', 'entry-10.7'],
  ['怎么谈薪', 'entry-10.7'], ['延长offer回复期限', 'entry-10.7']
]) {
  search.query(query);
  assert.equal(search.ids()[0], target, query);
}
search.query('送礼火星矿石');
assert.equal(search.cards.size, 0, 'Unknown content must not become a broad gift search');
search.query('改作业火星矿石');
assert.equal(search.cards.size, 0, 'Homework aliases must preserve unknown query content');
search.query('offer 催我答复 火星矿石');
assert.equal(search.cards.size, 0, 'Space-tolerant matching must preserve unknown words');
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
assert.equal(deepLink.cards.size, JSON.parse(data).length);

const offline = page('file:///tmp/index.html#entry-4.1');
offline.query('借钱不还');
assert(offline.ids().includes('entry-4.2'));
assert.equal(new URL(offline.location.href).hash, '');

const references = page(site + '?q=借钱不还&chapter=4');
const priorResults = references.ids();
for (const modifiers of [{ metaKey: true }, { ctrlKey: true }, { shiftKey: true }, { altKey: true }, { button: 1 }]) {
  assert.equal(references.reference('5.3', modifiers), false, 'Preserve native modified-link behavior');
  assert.deepEqual(references.ids(), priorResults);
  assert.equal(new URL(references.location.href).hash, '');
}
assert(references.reference('5.3'));
assert(references.cards.get('entry-5.3').details.open);
references.back();
assert.equal(references.element('query').value, '借钱不还');
assert.equal(references.element('chapter').value, '4');
assert.deepEqual(references.ids(), priorResults);
references.forward();
assert(references.cards.get('entry-5.3').details.open);
assert.equal(new URL(references.location.href).hash, '#entry-5.3');
console.log('Search regression checks passed: intent, filters, refresh, jumps, reset, offline URL, modified links and back/forward.');

const newRelated = page(site + '?q=发合照&chapter=5');
assert(newRelated.ids().includes('entry-5.7'));
assert(newRelated.reference('5.8'));
assert(newRelated.cards.get('entry-5.8').details.open);
newRelated.back();
assert(newRelated.ids().includes('entry-5.7'));
assert.equal(newRelated.element('query').value, '发合照');

const savedKey = 'howtogetalong.saved.v1';
const storage = new Map([[savedKey, '["4.1","99.9",null,"4.1"]']]);
const favorites = page(site + '?saved=1', storage);
assert.deepEqual(favorites.ids(), ['entry-4.1'], 'Ignore obsolete and invalid stored IDs');
assert.equal(favorites.element('saved-count').textContent, 1);
favorites.run('toggleSaved("4.1")');
assert.equal(favorites.cards.size, 0, 'Unsave removes the card from favorites');
assert.match(favorites.element('list').innerHTML, /还没有收藏/);
favorites.element('reset').handlers.click();
favorites.run('toggleSaved("1.7")');
favorites.run('toggleSaved("6.8")');
favorites.element('saved-only').checked = true;
favorites.element('saved-only').handlers.change();
assert.deepEqual(favorites.ids(), ['entry-1.7', 'entry-6.8']);
assert.equal(new URL(favorites.location.href).searchParams.get('saved'), '1');
assert.deepEqual(page(favorites.location.href, storage).ids(), favorites.ids(), 'Favorites survive refresh');
favorites.element('reset').handlers.click();
assert.equal(JSON.parse(storage.get(savedKey)).length, 2, 'Clear filters keeps favorites');
const hiddenFavorite = page(site + '?saved=1#entry-4.1', storage);
assert(hiddenFavorite.cards.get('entry-4.1').details.open, 'Shared deep links reveal unsaved entries');
assert.equal(hiddenFavorite.element('saved-only').checked, false);
for (const corrupt of ['invalid JSON', '{}', 'null']) {
  assert.equal(page(site + '?saved=1', new Map([[savedKey, corrupt]])).cards.size, 0);
}
const temporaryFavorites = page(site, new Map(), true);
temporaryFavorites.run('toggleSaved("4.1")');
temporaryFavorites.element('saved-only').checked = true;
temporaryFavorites.element('saved-only').handlers.change();
assert.deepEqual(temporaryFavorites.ids(), ['entry-4.1'], 'Blocked storage still supports this page');
assert.match(temporaryFavorites.element('action-status').textContent, /关闭后不会保留/);
assert.equal(offline.run('shareUrl("4.1")'), 'https://kkk-bot.github.io/HowToGetAlong/#entry-4.1', 'Sharing never exposes local paths or filters');
const feedback = new URL(offline.run('feedbackUrl("1.7")'));
assert.equal(feedback.searchParams.get('entry'), '1.7');
assert.equal(feedback.searchParams.get('template'), 'reading-feedback.yml');
const source = JSON.parse(sourceData).find(source => source.id === 'P05');
assert(offline.run('renderField("依据", "参考 P05")').includes('href="' + source.url.replaceAll('&', '&amp;') + '"'));
assert.match(offline.run('renderField("接续对话", "你先说：<测试>\\n你再回应：好")'), /&lt;测试&gt;<\/p><p>你再回应/);
const dialogues = JSON.parse(data).filter(entry => entry.fields['接续对话']);
assert.equal(dialogues.length, 8);
for (const entry of dialogues) {
  assert(entry.fields['接续对话'].includes('\n'));
  assert(entry.fields['接续对话'].includes('编写情境'));
  assert(entry.fields['接续对话'].includes('调整信号'));
}
console.log('New-feature checks passed: intent, local favorites, blocked/corrupt storage, share URLs, feedback fields, source links and dialogue parsing.');
