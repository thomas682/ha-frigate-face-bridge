const formState = {
  populated: false,
  appPopulated: false,
};

const DEFAULT_VIEW = 'overview';

function apiPath(path) {
  return new URL(path.replace(/^\//, ''), window.location.href).toString();
}

function checkbox(id) {
  return document.getElementById(id).checked;
}

function value(id) {
  return document.getElementById(id).value.trim();
}

function text(id, content) {
  const element = document.getElementById(id);
  if (element) element.textContent = content;
}

function setActiveView(viewName) {
  const selected = viewName || DEFAULT_VIEW;
  document.querySelectorAll('.view').forEach((section) => {
    section.hidden = section.dataset.view !== selected;
  });
  document.querySelectorAll('.view-tab').forEach((button) => {
    const active = button.dataset.targetView === selected;
    button.classList.toggle('active', active);
    button.setAttribute('aria-current', active ? 'page' : 'false');
  });
  window.localStorage.setItem('faceBridgeView', selected);
}

function setupNavigation() {
  document.querySelectorAll('.view-tab').forEach((button) => {
    button.addEventListener('click', () => setActiveView(button.dataset.targetView));
  });
  const saved = window.localStorage.getItem('faceBridgeView') || DEFAULT_VIEW;
  const hasSavedView = Array.from(document.querySelectorAll('.view')).some((section) => section.dataset.view === saved);
  setActiveView(hasSavedView ? saved : DEFAULT_VIEW);
}

function renderChips(containerId, values, emptyText = 'keine') {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  const items = (values || []).filter(Boolean);
  if (!items.length) {
    container.textContent = emptyText;
    return;
  }
  items.forEach((valueItem) => {
    const chip = document.createElement('span');
    chip.className = 'entity-chip';
    chip.textContent = valueItem;
    container.appendChild(chip);
  });
}

function addCell(row, content) {
  const cell = document.createElement('td');
  cell.textContent = content;
  row.appendChild(cell);
  return cell;
}

function appConfigFromForm() {
  const mqttPassword = value('setting-mqtt-password');
  const mqtt = {
    enabled: checkbox('setting-mqtt-enabled'),
    host: value('setting-mqtt-host'),
    port: Number(value('setting-mqtt-port') || 1883),
    username: value('setting-mqtt-username'),
    topic_prefix: value('setting-topic-prefix'),
    discovery: checkbox('setting-mqtt-discovery'),
    discovery_prefix: value('setting-discovery-prefix'),
  };
  if (mqttPassword && !mqttPassword.includes('***')) mqtt.password = mqttPassword;

  return {
    demo_mode: checkbox('setting-demo-mode'),
    log_level: value('setting-log-level'),
    event_interval_seconds: Number(value('setting-event-interval') || 10),
    mqtt,
    frigate: {
      enabled: checkbox('setting-frigate-enabled'),
      events_topic: value('setting-frigate-topic'),
      camera_name: value('setting-frigate-camera'),
      api_url: value('setting-frigate-api-url'),
      person_count_enabled: checkbox('setting-frigate-person-count-enabled'),
      person_count_interval_seconds: Number(value('setting-frigate-person-count-interval') || 5),
      dog_name: value('setting-frigate-dog-name') || 'Maja',
    },
    face_recognition: {
      enabled: checkbox('setting-face-enabled'),
      events_topic: value('setting-face-topic'),
      min_confidence: Number(value('setting-face-confidence') || 0.7),
    },
    announcements: {
      enabled: checkbox('setting-announcements-enabled'),
      announce_known: checkbox('setting-announcements-known'),
      announce_unknown: checkbox('setting-announcements-unknown'),
      announce_dog: checkbox('setting-announcements-dog'),
      random_texts_enabled: checkbox('setting-announcements-random'),
      global_cooldown_seconds: Number(value('setting-announcements-global-cooldown') || 60),
      entity_cooldown_seconds: Number(value('setting-announcements-entity-cooldown') || 300),
      disabled_entities: value('setting-announcements-disabled'),
      custom_texts: document.getElementById('setting-announcements-custom-texts').value.trim(),
    },
    terrace_door: {
      enabled: checkbox('setting-door-enabled'),
      open: checkbox('setting-door-open'),
      confidence: Number(value('setting-door-confidence') || 0),
      last_changed: value('setting-door-last-changed'),
    },
  };
}

function cameraFromForm() {
  const camera = {
    name: document.getElementById('camera-name').value.trim(),
    host: document.getElementById('camera-host').value.trim(),
  };
  const rtspUrl = document.getElementById('camera-rtsp').value.trim();
  const snapshotUrl = document.getElementById('camera-snapshot').value.trim();
  if (rtspUrl && !rtspUrl.includes('***')) camera.rtsp_url = rtspUrl;
  if (snapshotUrl && !snapshotUrl.includes('***')) camera.snapshot_url = snapshotUrl;
  return camera;
}

function populateCameraForm(camera) {
  if (formState.populated || !camera) return;
  document.getElementById('camera-name').value = camera.name || '';
  document.getElementById('camera-host').value = camera.host || '';
  document.getElementById('camera-rtsp').value = camera.rtsp_url && !camera.rtsp_url.includes('***') ? camera.rtsp_url : '';
  document.getElementById('camera-snapshot').value = camera.snapshot_url && !camera.snapshot_url.includes('***') ? camera.snapshot_url : '';
  formState.populated = true;
}

function populateAppForm(config) {
  if (formState.appPopulated || !config) return;
  const mqtt = config.mqtt || {};
  const frigate = config.frigate || {};
  const face = config.face_recognition || {};
  const announcements = config.announcements || {};
  const door = config.terrace_door || {};
  document.getElementById('setting-demo-mode').checked = Boolean(config.demo_mode);
  document.getElementById('setting-event-interval').value = config.event_interval_seconds || 10;
  document.getElementById('setting-log-level').value = config.log_level || 'info';
  document.getElementById('setting-mqtt-enabled').checked = Boolean(mqtt.enabled);
  document.getElementById('setting-mqtt-host').value = mqtt.host || '';
  document.getElementById('setting-mqtt-port').value = mqtt.port || 1883;
  document.getElementById('setting-mqtt-username').value = mqtt.username || '';
  document.getElementById('setting-mqtt-password').value = mqtt.password && !mqtt.password.includes('***') ? mqtt.password : '';
  document.getElementById('setting-topic-prefix').value = mqtt.topic_prefix || 'ha/frigate_face_bridge';
  document.getElementById('setting-mqtt-discovery').checked = mqtt.discovery !== false;
  document.getElementById('setting-discovery-prefix').value = mqtt.discovery_prefix || 'homeassistant';
  document.getElementById('setting-frigate-enabled').checked = Boolean(frigate.enabled);
  document.getElementById('setting-frigate-topic').value = frigate.events_topic || 'frigate/events';
  document.getElementById('setting-frigate-camera').value = frigate.camera_name || '';
  document.getElementById('setting-frigate-api-url').value = frigate.api_url || '';
  document.getElementById('setting-frigate-person-count-enabled').checked = frigate.person_count_enabled !== false;
  document.getElementById('setting-frigate-person-count-interval').value = frigate.person_count_interval_seconds || 5;
  document.getElementById('setting-frigate-dog-name').value = frigate.dog_name || 'Maja';
  document.getElementById('setting-face-enabled').checked = Boolean(face.enabled);
  document.getElementById('setting-face-topic').value = face.events_topic || 'face_recognition/events';
  document.getElementById('setting-face-confidence').value = face.min_confidence ?? 0.7;
  document.getElementById('setting-announcements-enabled').checked = announcements.enabled !== false;
  document.getElementById('setting-announcements-known').checked = announcements.announce_known !== false;
  document.getElementById('setting-announcements-unknown').checked = announcements.announce_unknown !== false;
  document.getElementById('setting-announcements-dog').checked = announcements.announce_dog !== false;
  document.getElementById('setting-announcements-random').checked = announcements.random_texts_enabled !== false;
  document.getElementById('setting-announcements-global-cooldown').value = announcements.global_cooldown_seconds ?? 60;
  document.getElementById('setting-announcements-entity-cooldown').value = announcements.entity_cooldown_seconds ?? 300;
  document.getElementById('setting-announcements-disabled').value = announcements.disabled_entities || '';
  document.getElementById('setting-announcements-custom-texts').value = announcements.custom_texts || '';
  document.getElementById('setting-door-enabled').checked = Boolean(door.enabled);
  document.getElementById('setting-door-open').checked = Boolean(door.open);
  document.getElementById('setting-door-confidence').value = door.confidence ?? 0;
  document.getElementById('setting-door-last-changed').value = door.last_changed || '';
  formState.appPopulated = true;
}

function formatChartTime(timestamp) {
  if (!timestamp) return '';
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return String(timestamp).slice(0, 16);
  return parsed.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
}

function renderPersonChart(series) {
  const chart = document.getElementById('person-chart');
  if (!chart) return;
  const points = (series || []).slice(-40);
  chart.innerHTML = '';
  if (!points.length) {
    chart.textContent = 'Noch keine Datenpunkte.';
    return;
  }
  const values = points.map((item) => Number(item.person_count || 0));
  const max = Math.max(1, ...values);
  const width = 760;
  const height = 180;
  const padding = { top: 18, right: 22, bottom: 34, left: 34 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const xFor = (index) => padding.left + (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
  const yFor = (value) => padding.top + plotHeight - (value / max) * plotHeight;
  const linePoints = values.map((value, index) => `${xFor(index).toFixed(1)},${yFor(value).toFixed(1)}`).join(' ');
  const areaPoints = `${padding.left},${padding.top + plotHeight} ${linePoints} ${padding.left + plotWidth},${padding.top + plotHeight}`;
  const first = points[0];
  const last = points[points.length - 1];

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', `Personenverlauf von ${first.timestamp || 'Start'} bis ${last.timestamp || 'jetzt'}`);

  const gridGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  gridGroup.setAttribute('class', 'chart-grid');
  for (let tick = 0; tick <= max; tick += 1) {
    const y = yFor(tick);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', String(padding.left));
    line.setAttribute('x2', String(padding.left + plotWidth));
    line.setAttribute('y1', y.toFixed(1));
    line.setAttribute('y2', y.toFixed(1));
    gridGroup.appendChild(line);
  }
  svg.appendChild(gridGroup);

  const area = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
  area.setAttribute('class', 'chart-area');
  area.setAttribute('points', areaPoints);
  svg.appendChild(area);

  const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  polyline.setAttribute('class', 'chart-line');
  polyline.setAttribute('points', linePoints);
  svg.appendChild(polyline);

  values.forEach((value, index) => {
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('class', 'chart-point');
    circle.setAttribute('cx', xFor(index).toFixed(1));
    circle.setAttribute('cy', yFor(value).toFixed(1));
    circle.setAttribute('r', '4');
    const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
    title.textContent = `${points[index].timestamp || ''}: ${value} Personen`;
    circle.appendChild(title);
    svg.appendChild(circle);
  });

  const yLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  yLabel.setAttribute('class', 'chart-label');
  yLabel.setAttribute('x', '6');
  yLabel.setAttribute('y', String(padding.top + 4));
  yLabel.textContent = String(max);
  svg.appendChild(yLabel);

  const startLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  startLabel.setAttribute('class', 'chart-label');
  startLabel.setAttribute('x', String(padding.left));
  startLabel.setAttribute('y', String(height - 8));
  startLabel.textContent = formatChartTime(first.timestamp);
  svg.appendChild(startLabel);

  const endLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  endLabel.setAttribute('class', 'chart-label chart-label-end');
  endLabel.setAttribute('x', String(width - padding.right));
  endLabel.setAttribute('y', String(height - 8));
  endLabel.textContent = formatChartTime(last.timestamp);
  svg.appendChild(endLabel);

  chart.appendChild(svg);
}

function renderHistory(items) {
  const body = document.getElementById('history-body');
  if (!body) return;
  const rows = (items || []).slice(-20).reverse();
  body.innerHTML = '';
  if (!rows.length) {
    const row = document.createElement('tr');
    const cell = addCell(row, 'Noch keine History vorhanden.');
    cell.colSpan = 6;
    body.appendChild(row);
    return;
  }
  for (const item of rows) {
    const row = document.createElement('tr');
    const recognized = (item.recognized_entities || item.known_faces || []).join(', ') || '-';
    const announcement = item.announcement_log_text || item.announcement_text || '-';
    addCell(row, item.timestamp || '-');
    addCell(row, item.person_count ?? 0);
    addCell(row, item.maja_present ? 'Maja' : (item.dog_count || 0));
    addCell(row, recognized);
    addCell(row, announcement);
    addCell(row, item.source || '-');
    body.appendChild(row);
  }
}

function renderRecognitionHistory(items) {
  const body = document.getElementById('recognition-history-body');
  if (!body) return;
  const rows = (items || []).slice(-20).reverse();
  body.innerHTML = '';
  if (!rows.length) {
    const row = document.createElement('tr');
    const cell = addCell(row, 'Noch keine Erkennungen.');
    cell.colSpan = 5;
    body.appendChild(row);
    return;
  }
  rows.forEach((item) => {
    const row = document.createElement('tr');
    addCell(row, item.timestamp || '-');
    addCell(row, (item.recognized_entities || item.known_faces || []).join(', ') || '-');
    addCell(row, item.unknown_faces ?? 0);
    addCell(row, item.maja_present ? 'Maja' : (item.dog_count || 0));
    addCell(row, item.source || '-');
    body.appendChild(row);
  });
}

function renderMqttHistory(items) {
  const body = document.getElementById('mqtt-history-body');
  if (!body) return;
  const rows = (items || []).slice(-50).reverse();
  body.innerHTML = '';
  if (!rows.length) {
    const row = document.createElement('tr');
    const cell = addCell(row, 'Noch keine MQTT-Nachrichten.');
    cell.colSpan = 5;
    body.appendChild(row);
    return;
  }
  rows.forEach((item) => {
    const row = document.createElement('tr');
    addCell(row, item.timestamp || '-');
    addCell(row, item.direction === 'in' ? 'rein' : 'raus');
    addCell(row, item.topic || '-');
    addCell(row, typeof item.payload === 'string' ? item.payload : JSON.stringify(item.payload));
    addCell(row, `qos ${item.qos ?? 0}${item.retain ? ', retain' : ''}`);
    body.appendChild(row);
  });
}

function renderAnnouncementHistory(items) {
  const body = document.getElementById('announcement-history-body');
  if (!body) return;
  const rows = (items || []).slice(-20).reverse();
  body.innerHTML = '';
  if (!rows.length) {
    const row = document.createElement('tr');
    const cell = addCell(row, 'Noch keine Ansagen.');
    cell.colSpan = 5;
    body.appendChild(row);
    return;
  }
  rows.forEach((item) => {
    const row = document.createElement('tr');
    addCell(row, item.timestamp || '-');
    addCell(row, item.text || '-');
    addCell(row, item.spoken ? 'ja' : 'nein');
    addCell(row, (item.entities || []).join(', ') || '-');
    addCell(row, item.suppressed_reason || '-');
    body.appendChild(row);
  });
}

function renderTopicList(topics) {
  const list = document.getElementById('mqtt-topic-list');
  if (!list) return;
  list.innerHTML = '';
  (topics || []).forEach((topic) => {
    const item = document.createElement('li');
    item.textContent = topic;
    list.appendChild(item);
  });
  if (!list.children.length) {
    const item = document.createElement('li');
    item.textContent = 'Keine Ausgabe-Topics bekannt.';
    list.appendChild(item);
  }
}

function renderFaces(faces) {
  const list = document.getElementById('faces-list');
  if (!list) return;
  list.innerHTML = '';
  if (!faces || faces.length === 0) {
    const item = document.createElement('li');
    item.textContent = 'Keine bekannten Personen angelegt.';
    list.appendChild(item);
    return;
  }
  for (const face of faces) {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = face.enabled ? 'deaktivieren' : 'aktivieren';
    button.addEventListener('click', () => setFaceEnabled(face.name, !face.enabled));
    item.textContent = `${face.name} (${face.enabled ? 'aktiv' : 'inaktiv'}, Bilder: ${face.image_count ?? 0}) `;
    item.appendChild(button);
    list.appendChild(item);
  }
}

async function refreshStatus() {
  const [statusResponse, configResponse] = await Promise.all([
    fetch(apiPath('api/status'), { cache: 'no-store' }),
    fetch(apiPath('api/config'), { cache: 'no-store' }),
  ]);
  if (!statusResponse.ok) throw new Error(`status ${statusResponse.status}`);
  if (!configResponse.ok) throw new Error(`config ${configResponse.status}`);
  const data = await statusResponse.json();
  const configData = await configResponse.json();
  const safeConfig = configData.config || {};
  const event = data.last_event || {};
  document.getElementById('status').textContent = data.ok ? 'online' : 'fehler';
  document.getElementById('started').textContent = `Start: ${data.started_at || '-'}`;
  document.getElementById('camera').textContent = data.camera?.name || '-';
  document.getElementById('camera-details').textContent = `${data.camera?.host || 'kein Host'} - RTSP: ${data.camera?.rtsp_configured ? 'konfiguriert' : 'offen'}`;
  document.getElementById('mqtt').textContent = data.mqtt?.enabled ? (data.mqtt?.connected ? 'verbunden' : 'aktiviert') : 'deaktiviert';
  document.getElementById('mqtt-topic').textContent = data.mqtt?.topic_prefix || '-';
  document.getElementById('person-count').textContent = event.person_count ?? 0;
  document.getElementById('dog-count').textContent = event.dog_count ?? 0;
  document.getElementById('maja-present').textContent = event.maja_present ? 'Maja erkannt' : 'Maja nicht erkannt';
  document.getElementById('event-time').textContent = event.timestamp || 'noch kein Event';
  document.getElementById('known-faces').textContent = (event.known_faces || []).join(', ') || 'keine';
  document.getElementById('recognized-entities').textContent = (event.recognized_entities || event.known_faces || []).join(', ') || 'keine';
  document.getElementById('unknown-faces').textContent = event.unknown_faces ?? 0;
  const announcement = event.announcement || {};
  document.getElementById('announcement-text').textContent = announcement.text || '-';
  document.getElementById('announcement-state').textContent = announcement.should_speak ? 'wird angesagt' : (announcement.suppressed_reason || 'keine Ansage');
  document.getElementById('last-dog-count').textContent = event.dog_count ?? 0;
  const recognizedEntities = event.recognized_entities || event.known_faces || [];
  renderChips('live-recognized-entities', recognizedEntities);
  renderChips('live-known-faces', event.known_faces || []);
  renderChips('recognition-current', recognizedEntities);
  renderChips('recognition-known', event.known_faces || []);
  text('live-event-time', event.timestamp || 'noch kein Event');
  text('live-unknown-faces', event.unknown_faces ?? 0);
  text('live-dog-state', event.maja_present ? 'Maja' : (event.dog_count ?? 0));
  text('recognition-unknown', event.unknown_faces ?? 0);
  text('recognition-dog', event.maja_present ? 'Maja' : (event.dog_count ?? 0));
  text('last-event-json', JSON.stringify(event, null, 2));
  text('live-refresh-state', `Live - ${new Date().toLocaleTimeString('de-DE')}`);
  text('announce-current-text', announcement.text || '-');
  text('announce-current-state', announcement.should_speak ? 'wird angesagt' : 'keine Ausgabe');
  renderChips('announce-current-entities', announcement.entities || []);
  text('announce-suppressed-reason', announcement.suppressed_reason || '-');
  text('mqtt-live-status', data.mqtt?.enabled ? (data.mqtt?.connected ? 'verbunden' : 'aktiviert, nicht verbunden') : 'deaktiviert');
  text('mqtt-live-prefix', data.mqtt?.topic_prefix || '-');
  text('mqtt-frigate-topic', data.mqtt?.frigate_events_topic || '-');
  text('mqtt-face-topic', data.mqtt?.face_events_topic || '-');
  const door = data.terrace_door || {};
  document.getElementById('terrace-door-open').textContent = door.open ? 'offen' : 'geschlossen';
  document.getElementById('terrace-door-confidence').textContent = door.confidence ?? 0;
  document.getElementById('terrace-door-last-changed').textContent = door.last_changed || '-';
  document.getElementById('demo-mode').textContent = data.demo_mode ? 'aktiv' : 'aus';
  document.getElementById('event-count').textContent = data.event_count ?? 0;
  document.getElementById('frigate-event-count').textContent = data.frigate_event_count ?? 0;
  document.getElementById('face-event-count').textContent = data.face_event_count ?? 0;
  document.getElementById('debug').textContent = JSON.stringify({ config_errors: data.config_errors || [], mqtt: data.mqtt, mqtt_history: data.mqtt_history || [], mqtt_output_topics: data.mqtt_output_topics || [], frigate: safeConfig.frigate, frigate_active_count: data.frigate_active_count, face_recognition: safeConfig.face_recognition, announcements: safeConfig.announcements, terrace_door: safeConfig.terrace_door }, null, 2);
  renderPersonChart(data.person_count_series || []);
  renderHistory(data.history || []);
  renderRecognitionHistory(data.history || []);
  renderAnnouncementHistory(data.announcement_history || []);
  renderMqttHistory(data.mqtt_history || []);
  renderTopicList(data.mqtt_output_topics || []);
  renderFaces(data.known_faces || []);
  populateCameraForm(data.camera);
  populateAppForm(safeConfig);
}

async function saveAppConfig(event) {
  event.preventDefault();
  const message = document.getElementById('app-message');
  message.textContent = 'Speichere Betriebs-Konfiguration ...';
  try {
    const response = await fetch(apiPath('api/config'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(appConfigFromForm()),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || `status ${response.status}`);
    formState.appPopulated = false;
    populateAppForm(data.config);
    await refreshStatus();
    message.textContent = 'Betriebs-Konfiguration gespeichert.';
  } catch (err) {
    message.textContent = `Speichern fehlgeschlagen: ${err}`;
  }
}

async function createFace(event) {
  event.preventDefault();
  const message = document.getElementById('face-message');
  const input = document.getElementById('face-name');
  message.textContent = 'Speichere Person ...';
  try {
    const response = await fetch(apiPath('api/faces'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: input.value.trim(), enabled: true }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || `status ${response.status}`);
    input.value = '';
    renderFaces(data.faces || []);
    message.textContent = 'Person gespeichert.';
  } catch (err) {
    message.textContent = `Speichern fehlgeschlagen: ${err}`;
  }
}

async function setFaceEnabled(name, enabled) {
  const message = document.getElementById('face-message');
  message.textContent = 'Aktualisiere Person ...';
  try {
    const response = await fetch(apiPath(`api/faces/${encodeURIComponent(name)}`), {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || `status ${response.status}`);
    renderFaces(data.faces || []);
    message.textContent = 'Person aktualisiert.';
  } catch (err) {
    message.textContent = `Aktualisierung fehlgeschlagen: ${err}`;
  }
}

async function saveCamera(event) {
  event.preventDefault();
  const message = document.getElementById('config-message');
  message.textContent = 'Speichere Kamera-Konfiguration ...';

  try {
    const response = await fetch(apiPath('api/config/camera'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ camera: cameraFromForm() }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || `status ${response.status}`);
    formState.populated = false;
    populateCameraForm(data.camera);
    await refreshStatus();
    message.textContent = 'Kamera-Konfiguration gespeichert.';
  } catch (err) {
    message.textContent = `Speichern fehlgeschlagen: ${err}`;
  }
}

async function loadSnapshot() {
  const image = document.getElementById('snapshot-preview');
  const message = document.getElementById('snapshot-message');
  image.hidden = true;
  image.removeAttribute('src');
  message.textContent = 'Lade Vorschau ...';

  try {
    const response = await fetch(apiPath(`api/camera/snapshot?ts=${Date.now()}`), { cache: 'no-store' });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || `status ${response.status}`);
    }
    const blob = await response.blob();
    image.src = URL.createObjectURL(blob);
    image.hidden = false;
    message.textContent = 'Vorschau geladen.';
  } catch (err) {
    message.textContent = `Vorschau fehlgeschlagen: ${err}`;
  }
}

async function boot() {
  setupNavigation();
  document.getElementById('app-form').addEventListener('submit', saveAppConfig);
  document.getElementById('camera-form').addEventListener('submit', saveCamera);
  document.getElementById('face-form').addEventListener('submit', createFace);
  document.getElementById('snapshot-button').addEventListener('click', loadSnapshot);
  try {
    await refreshStatus();
  } catch (err) {
    document.getElementById('status').textContent = 'fehler';
    document.getElementById('debug').textContent = String(err);
  }
  window.setInterval(() => refreshStatus().catch(() => {}), 5000);
}

boot();
