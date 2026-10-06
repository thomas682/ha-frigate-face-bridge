// Fuehrt das GESAMTE Oberflaechen-Skript app.js unter einem DOM-Ersatz aus und meldet jeden
// Fehler beim Aufbau. Vorgabe: global-project-rules.md, Abschnitt "Oberflaechen-Pruefskript".
// Eine Syntaxpruefung (Biome, node --check) sagt nur, dass die Datei lesbar ist - nicht, dass
// die Seite laeuft: Eine aufgerufene, aber nie definierte Funktion oder ein Zugriff auf eine
// Kennung, die es im HTML nicht gibt, faellt erst im Browser auf.
//
// Aufruf: node scripts/pruefung-oberflaeche.mjs [antworten.json]
// antworten.json kommt aus scripts/oberflaeche_daten.py und enthaelt echte API-Antworten der
// App. Ohne Datei laeuft nur der Leerzustand.
import fs from 'node:fs';

const STATIC = 'frigate-face-bridge/app/static';
const html = fs.readFileSync(`${STATIC}/index.html`, 'utf8');
const js = fs.readFileSync(`${STATIC}/app.js`, 'utf8');
const css = fs.readFileSync(`${STATIC}/style.css`, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const antworten = process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2], 'utf8')) : {};

let fehler = 0;
const pruefe = (name, ok, zusatz = '') => {
  console.log(`${ok ? '  ok  ' : '  FEHLER  '}${name}${ok ? '' : ` ${zusatz}`}`);
  if (!ok) fehler++;
};

// --- DOM-Ersatz ---------------------------------------------------------------------------
const datasetKey = (name) => name.replace(/-([a-z])/g, (_m, c) => c.toUpperCase());

function element(tag = 'div', attrs = {}) {
  const kinder = [];
  const klassen = new Set((attrs.class || '').split(/\s+/).filter(Boolean));
  const horcher = {};
  const dataset = {};
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith('data-')) dataset[datasetKey(k.slice(5))] = v;
  }
  const el = {
    tagName: tag.toUpperCase(),
    id: attrs.id || '',
    dataset,
    attrs: { ...attrs },
    horcher,
    children: kinder,
    style: {},
    textContent: '',
    value: attrs.value || '',
    checked: 'checked' in attrs,
    disabled: false,
    hidden: 'hidden' in attrs,
    href: attrs.href || '',
    src: '',
    title: '',
    className: attrs.class || '',
    parentElement: null,
    set innerHTML(wert) {
      if (wert === '') kinder.length = 0;
    },
    get innerHTML() {
      return '';
    },
    classList: {
      add: (...c) => {
        for (const k of c) klassen.add(k);
      },
      remove: (...c) => {
        for (const k of c) klassen.delete(k);
      },
      toggle: (c, an) => {
        const neu = an === undefined ? !klassen.has(c) : Boolean(an);
        if (neu) klassen.add(c);
        else klassen.delete(c);
        return neu;
      },
      contains: (c) => klassen.has(c),
    },
    appendChild: (k) => {
      if (k && typeof k === 'object') k.parentElement = el;
      kinder.push(k);
      return k;
    },
    append: (...ks) => {
      for (const k of ks) el.appendChild(k);
    },
    remove() {},
    setAttribute: (k, v) => {
      el.attrs[k] = String(v);
      if (k.startsWith('data-')) dataset[datasetKey(k.slice(5))] = String(v);
    },
    getAttribute: (k) => el.attrs[k] ?? null,
    removeAttribute: (k) => {
      delete el.attrs[k];
    },
    addEventListener: (art, fn) => {
      if (!horcher[art]) horcher[art] = [];
      horcher[art].push(fn);
    },
    removeEventListener() {},
    dispatchEvent: (event) => {
      for (const fn of horcher[event.type] || []) fn(event);
      return true;
    },
    querySelector: () => element('div'),
    querySelectorAll: () => [],
    focus() {},
    reset() {},
  };
  return el;
}

// Elemente aus dem Markup: jedes Start-Tag mit id, class oder data-Attribut.
const kennungen = new Map();
const alle = [];
for (const treffer of html.matchAll(/<([a-zA-Z][\w-]*)(\s[^<>]*?)?\/?>/g)) {
  const attrs = {};
  for (const a of (treffer[2] || '').matchAll(/([\w:-]+)(?:\s*=\s*"([^"]*)")?/g)) attrs[a[1]] = a[2] ?? '';
  if (!attrs.id && !attrs.class && !Object.keys(attrs).some((k) => k.startsWith('data-'))) continue;
  const el = element(treffer[1], attrs);
  alle.push(el);
  if (attrs.id) kennungen.set(attrs.id, (kennungen.get(attrs.id) || []).concat(el));
}

const fehlendeKennungen = new Set();
function auswahl(selektor) {
  const klasse = selektor.match(/^\.([\w-]+)$/);
  if (klasse) return alle.filter((el) => el.classList.contains(klasse[1]));
  const daten = selektor.match(/^\[data-([\w-]+)\]$/);
  if (daten) return alle.filter((el) => `data-${daten[1]}` in el.attrs);
  throw new Error(`Selektor wird vom DOM-Ersatz nicht unterstuetzt: ${selektor}`);
}

const speicher = new Map();
const document = {
  body: element('body'),
  getElementById: (id) => {
    const treffer = kennungen.get(id);
    if (!treffer) {
      fehlendeKennungen.add(id);
      return null;
    }
    return treffer[0];
  },
  querySelectorAll: auswahl,
  querySelector: (s) => auswahl(s)[0] || null,
  createElement: (tag) => element(tag),
  createElementNS: (_ns, tag) => element(tag),
  createTextNode: (text) => ({ textContent: String(text) }),
  addEventListener() {},
};

const offeneAnfragen = [];
const fetch = async (url, options = {}) => {
  const pfad = new URL(url).pathname.replace(/^\//, '');
  const methode = (options.method || 'GET').toUpperCase();
  offeneAnfragen.push(`${methode} ${pfad}`);
  const daten = methode === 'GET' && antworten[pfad] ? antworten[pfad] : { ok: true };
  return {
    ok: true,
    status: 200,
    json: async () => structuredClone(daten),
    blob: async () => new Blob([]),
  };
};

const intervalle = [];
const window = {
  location: { href: 'http://localhost:8123/api/hassio_ingress/beispiel/', port: '8123' },
  localStorage: {
    getItem: (k) => (speicher.has(k) ? speicher.get(k) : null),
    setItem: (k, v) => speicher.set(k, String(v)),
  },
  setInterval: (fn) => {
    intervalle.push(fn);
    return intervalle.length;
  },
};

const umgebung = {
  document,
  window,
  fetch,
  console,
  // URL muss Konstruktor bleiben (apiPath) und createObjectURL kennen (Snapshot-Vorschau).
  URL: class extends URL {
    static createObjectURL() {
      return 'blob:pruefung';
    }
  },
  Event: class {
    constructor(type) {
      this.type = type;
    }
  },
};

const unbehandelt = [];
process.on('unhandledRejection', (grund) => unbehandelt.push(grund));
const warten = () => new Promise((fertig) => setImmediate(fertig));
const abarbeiten = async () => {
  for (let i = 0; i < 20; i++) await warten();
};

// --- Pruefungen -----------------------------------------------------------------------------
try {
  const lauf = new Function(...Object.keys(umgebung), js);
  lauf(...Object.values(umgebung));
  await abarbeiten();
  pruefe('Das gesamte Oberflaechen-Skript laeuft ohne Fehler durch', true);
} catch (e) {
  pruefe('Das gesamte Oberflaechen-Skript laeuft ohne Fehler durch', false, `\n     ${e.constructor.name}: ${e.message}`);
}

// boot() faengt Fehler aus refreshStatus() ab und schreibt sie nach #debug. Ohne diesen Blick
// sahe ein abgebrochener Aufbau wie ein gruener Lauf aus.
const status = document.getElementById('status');
const debug = document.getElementById('debug');
pruefe(
  'Erster Statusabruf zeichnet die Seite vollstaendig',
  status?.textContent === 'online',
  `\n     #status: ${status?.textContent}\n     #debug: ${String(debug?.textContent).slice(0, 300)}`,
);

// Jeden registrierten Ereignis-Horcher einmal ausloesen: Navigation, Filter, Formulare, Tests.
const horcherFehler = [];
for (const el of alle) {
  for (const [art, liste] of Object.entries(el.horcher)) {
    for (const fn of liste) {
      try {
        await fn({ type: art, target: el, currentTarget: el, preventDefault() {}, stopPropagation() {} });
        await abarbeiten();
      } catch (e) {
        horcherFehler.push(`${el.id || el.className || el.tagName} ${art}: ${e.message}`);
      }
    }
  }
}
for (const fn of intervalle) {
  fn();
  await abarbeiten();
}
pruefe('Alle Bedienhandlungen laufen ohne Fehler', horcherFehler.length === 0, `\n     ${horcherFehler.join('\n     ')}`);
pruefe(
  'Keine unbehandelten Fehler in asynchronen Ablaeufen',
  unbehandelt.length === 0,
  `\n     ${unbehandelt.map(String).join('\n     ')}`,
);
pruefe(
  'Keine Zugriffe auf Kennungen, die es im HTML nicht gibt',
  fehlendeKennungen.size === 0,
  `\n     fehlend: ${[...fehlendeKennungen].join(', ')}`,
);

// querySelector('#x') und getElementById liefern immer das ERSTE Element. Kommt eine Kennung
// zweimal vor, schreibt ein Teil der Oberflaeche still in das Element eines anderen.
const doppelt = [...kennungen].filter(([, els]) => els.length > 1).map(([id]) => id);
pruefe('Jede Kennung kommt im HTML nur einmal vor', doppelt.length === 0, `\n     doppelt: ${doppelt.join(', ')}`);

// Jede Klasse im Markup hat eine Regel im Stilblatt. Eine gesetzte, aber nie definierte
// Klasse faellt still auf die Grunddarstellung zurueck.
const klassenImHtml = new Set();
for (const t of html.replace(/<!--[\s\S]*?-->/g, '').matchAll(/class="([^"]+)"/g)) {
  for (const k of t[1].split(/\s+/)) if (/^[a-zA-Z][\w-]*$/.test(k)) klassenImHtml.add(k);
}
const ohneRegel = [...klassenImHtml].filter((k) => !new RegExp(`\\.${k}(?![\\w-])`).test(css)).sort();
pruefe('Jede Klasse im HTML hat eine Regel im Stilblatt', ohneRegel.length === 0, `\n     ohne Regel: ${ohneRegel.join(', ')}`);

console.log(`  (${offeneAnfragen.length} API-Aufrufe simuliert)`);
console.log(fehler ? `\n${fehler} Fehler` : '\nAlle Oberflaechen-Pruefungen bestanden');
process.exit(fehler ? 1 : 0);
