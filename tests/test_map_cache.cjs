const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const origin = 'https://pickledonion.dev';
const workerSource = readFileSync(path.join(__dirname, '../../pickled-onion/service-worker.js'), 'utf8');
const html = readFileSync(path.join(__dirname, '../public/index.html'), 'utf8');
const refreshSource = html.match(/<script id="map-cache-refresh">([\s\S]*?)<\/script>/)[1];

function harness() {
  const handlers = {};
  const stores = new Map();
  const calls = [];
  let offline = false;
  let failWrites = false;
  const key = (request) => new URL(typeof request === 'string' ? request : request.url, origin).href;
  const caches = {
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const store = stores.get(name);
      return {
        async match(request, options = {}) {
          const url = key(request);
          for (const [entry, response] of store) {
            if (entry === url || (options.ignoreSearch && entry.split('?')[0] === url.split('?')[0])) {
              return response.clone();
            }
          }
        },
        async put(request, response) {
          if (failWrites) throw new Error('Quota exceeded');
          store.set(key(request), response.clone());
        },
        async addAll(urls) {
          for (const url of urls) store.set(key(url), new Response('installed'));
        },
      };
    },
    async match(request, options) {
      for (const name of stores.keys()) {
        const response = await (await caches.open(name)).match(request, options);
        if (response) return response;
      }
    },
    async keys() { return [...stores.keys()]; },
    async delete(name) { return stores.delete(name); },
  };
  const context = vm.createContext({
    URL, Response, caches,
    fetch: async (request, options) => {
      calls.push({ url: key(request), options });
      if (offline) throw new Error('Offline');
      return new Response('latest');
    },
    self: {
      location: { origin },
      addEventListener: (name, fn) => { handlers[name] = fn; },
      skipWaiting: async () => {},
      clients: { claim: async () => {} },
    },
  });
  vm.runInContext(workerSource, context);
  return {
    calls, caches, context,
    runtime: vm.runInContext('RUNTIME_CACHE', context),
    precache: vm.runInContext('PRECACHE_CACHE', context),
    setOffline(value) { offline = value; },
    setFailWrites(value) { failWrites = value; },
    async fetch(url) {
      let result;
      handlers.fetch({ request: { url: new URL(url, origin).href, method: 'GET', mode: 'cors' }, respondWith: (value) => { result = value; } });
      return result;
    },
    async activate() {
      let work;
      handlers.activate({ waitUntil: (value) => { work = value; } });
      await work;
    },
  };
}

for (const asset of ['/map/app.js', '/map/styles.css', '/map/data/surf-spots.geojson', '/map/data/snorkelling-spots.geojson']) {
  test(`refreshes cached ${asset} and keeps newest copy offline`, async () => {
    const h = harness();
    await (await h.caches.open(h.precache)).put(asset, new Response('stale'));
    assert.equal(await (await h.fetch(asset)).text(), 'latest');
    assert.equal(h.calls[0].options.cache, 'no-cache');
    h.setOffline(true);
    assert.equal(await (await h.fetch(asset)).text(), 'latest');
  });
}

test('offline map uses installation cache when no newer copy exists', async () => {
  const h = harness();
  await (await h.caches.open(h.precache)).put('/map/app.js', new Response('installed'));
  h.setOffline(true);
  assert.equal(await (await h.fetch('/map/app.js')).text(), 'installed');
});

test('offline versioned URL does not receive a different cached version', async () => {
  const h = harness();
  await (await h.caches.open(h.precache)).put('/map/app.js?v=old', new Response('stale'));
  h.setOffline(true);
  assert.equal((await h.fetch('/map/app.js?v=new')).type, 'error');
});

test('cache write failure still returns fresh network response', async () => {
  const h = harness();
  await (await h.caches.open(h.precache)).put('/map/app.js', new Response('stale'));
  h.setFailWrites(true);
  assert.equal(await (await h.fetch('/map/app.js')).text(), 'latest');
});

test('activation removes previous site caches and preserves unrelated caches', async () => {
  const h = harness();
  await h.caches.open('pickled-onion-precache-2026-10-13-map-rename');
  await h.caches.open('another-app');
  await h.caches.open(h.precache);
  await h.caches.open(h.runtime);
  await h.activate();
  assert.deepEqual(await h.caches.keys(), ['another-app', h.precache, h.runtime]);
});

test('unrelated site assets retain cache-first behavior', async () => {
  const h = harness();
  await (await h.caches.open(h.precache)).put('/vendor/three.module.js', new Response('cached'));
  assert.equal(await (await h.fetch('/vendor/three.module.js')).text(), 'cached');
  assert.equal(h.calls.length, 0);
});

function refreshHarness(controller) {
  const events = {};
  let reloads = 0;
  let updates = 0;
  const registrations = [];
  const serviceWorker = {
    controller,
    addEventListener: (name, fn) => { events[name] = fn; },
    register: async (...args) => { registrations.push(args); },
    getRegistration: async () => ({ update: async () => { updates += 1; } }),
  };
  const document = {
    visibilityState: 'visible',
    addEventListener: (name, fn) => { events[name] = fn; },
  };
  vm.runInNewContext(refreshSource, {
    navigator: { serviceWorker }, document,
    window: {
      location: { reload: () => { reloads += 1; } },
      addEventListener: (name, fn) => { events[name] = fn; },
    },
  });
  return { serviceWorker, document, events, registrations, reloads: () => reloads, updates: () => updates };
}

test('existing installation reloads once when the new worker takes control', () => {
  const h = refreshHarness({ old: true });
  assert.equal(h.registrations[0][0], '/service-worker.js');
  assert.equal(h.registrations[0][1].updateViaCache, 'none');
  h.serviceWorker.controller = { new: true };
  h.events.controllerchange();
  h.events.controllerchange();
  assert.equal(h.reloads(), 1);
});

test('first installation does not reload, but a subsequent update does', () => {
  const h = refreshHarness(null);
  h.serviceWorker.controller = { first: true };
  h.events.controllerchange();
  assert.equal(h.reloads(), 0);
  h.serviceWorker.controller = { next: true };
  h.events.controllerchange();
  assert.equal(h.reloads(), 1);
});

test('restoring or reopening the app checks for worker updates', async () => {
  const h = refreshHarness({ old: true });
  h.document.visibilityState = 'hidden';
  h.events.visibilitychange();
  h.events.pageshow({ persisted: false });
  await new Promise(setImmediate);
  assert.equal(h.updates(), 0);
  h.document.visibilityState = 'visible';
  h.events.visibilitychange();
  h.events.pageshow({ persisted: true });
  await new Promise(setImmediate);
  assert.equal(h.updates(), 2);
});
