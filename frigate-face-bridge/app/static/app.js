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

function addHighlightedCell(row, content, query) {
  const cell = document.createElement('td');
  appendHighlightedText(cell, String(content ?? ''), query);
  row.appendChild(cell);
  return cell;
}

function appendHighlightedText(parent, content, query) {
  const textValue = String(content ?? '');
  const search = String(query || '').trim();
  if (!search) {
    parent.textContent = textValue;
    return;
  }
  const lower = textValue.toLowerCase();
  const needle = search.toLowerCase();
  let index = 0;
  let match = lower.indexOf(needle, index);
  while (match !== -1) {
    if (match > index) parent.appendChild(document.createTextNode(textValue.slice(index, match)));
    const mark = document.createElement('mark');
    mark.textContent = textValue.slice(match, match + search.length);
    parent.appendChild(mark);
    index = match + search.length;
    match = lower.indexOf(needle, index);
  }
  if (index < textValue.length) parent.appendChild(document.createTextNode(textValue.slice(index)));
}

function selectedRangeMs(prefix) {
  const select = document.getElementById(`${prefix}-range`);
  const valueText = select ? select.value : 'all';
  if (valueText === 'all') return null;
  return Number(valueText) * 60 * 60 * 1000;
}

function tableSearch(prefix) {
  const input = document.getElementById(`${prefix}-search`);
  return input ? input.value.trim() : '';
}

function itemText(item) {
  try {
    return JSON.stringify(item).toLowerCase();
  } catch (err) {
    return String(item || '').toLowerCase();
  }
}

function filterRows(items, prefix) {
  const search = tableSearch(prefix).toLowerCase();
  const rangeMs = selectedRangeMs(prefix);
  const minTime = rangeMs ? Date.now() - rangeMs : null;
  return (items || []).filter((item) => {
    if (minTime && item.timestamp) {
      const parsed = new Date(item.timestamp).getTime();
      if (!Number.isNaN(parsed) && parsed < minTime) return false;
    }
    return !search || itemText(item).includes(search);
  });
}

function renderKeyValueList(containerId, entries) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';
  (entries || []).forEach(([key, content]) => {
    const item = document.createElement('li');
    const strong = document.createElement('strong');
    const span = document.createElement('span');
    strong.textContent = key;
    span.textContent = content ?? '-';
    item.appendChild(strong);
    item.appendChild(span);
    container.appendChild(item);
  });
}

function setStatusBadge(id, isSet, setText = 'gesetzt', missingText = 'nicht gesetzt') {
  const element = document.getElementById(id);
  if (!element) return;
  element.textContent = isSet ? setText : missingText;
  element.classList.toggle('ok', Boolean(isSet));
  element.classList.toggle('missing', !isSet);
}

function currentMqttSettings() {
  return {
    enabled: checkbox('setting-mqtt-enabled'),
    host: value('setting-mqtt-host'),
    port: Number(value('setting-mqtt-port') || 1883),
    username: value('setting-mqtt-username'),
    password: value('setting-mqtt-password'),
    topic_prefix: value('setting-topic-prefix'),
    discovery: checkbox('setting-mqtt-discovery'),
    discovery_prefix: value('setting-discovery-prefix'),
  };
}

function currentFrigateSettings() {
  return {
    enabled: checkbox('setting-frigate-enabled'),
    events_topic: value('setting-frigate-topic'),
    camera_name: value('setting-frigate-camera'),
    api_url: value('setting-frigate-api-url'),
    person_count_enabled: checkbox('setting-frigate-person-count-enabled'),
    person_count_interval_seconds: Number(value('setting-frigate-person-count-interval') || 5),
    dog_name: value('setting-frigate-dog-name'),
  };
}

function currentCameraSettings() {
  return {
    name: value('camera-name'),
    host: value('camera-host'),
    rtsp_url: value('camera-rtsp'),
    snapshot_url: value('camera-snapshot'),
  };
}

function setField(id, content) {
  const element = document.getElementById(id);
  if (!element) return;
  const valueText = content ?? '';
  if (element.type === 'checkbox') {
    element.checked = Boolean(content);
    element.dataset.original = String(element.checked);
    element.dataset.hasValue = content === undefined ? 'false' : 'true';
    return;
  }
  element.value = valueText;
  element.dataset.original = String(valueText);
  element.dataset.hasValue = content === undefined ? 'false' : 'true';
}

function fieldChanged(id) {
  const element = document.getElementById(id);
  if (!element) return false;
  if (element.type === 'checkbox') {
    return String(element.checked) !== (element.dataset.original || 'false');
  }
  return element.value.trim() !== (element.dataset.original || '');
}

function includeIfChanged(target, key, id, transform = (input) => input) {
  if (!fieldChanged(id)) return;
  target[key] = transform(value(id));
}

function includeCheckboxIfChanged(target, key, id) {
  if (!fieldChanged(id)) return;
  target[key] = checkbox(id);
}

function includeNumberIfChanged(target, key, id) {
  includeIfChanged(target, key, id, (input) => Number(input));
}

function hasKeys(valueObject) {
  return Object.keys(valueObject).length > 0;
}

function appConfigFromForm() {
  const payload = {};
  includeCheckboxIfChanged(payload, 'demo_mode', 'setting-demo-mode');
  includeIfChanged(payload, 'log_level', 'setting-log-level');
  includeNumberIfChanged(payload, 'event_interval_seconds', 'setting-event-interval');

  const mqtt = {};
  includeCheckboxIfChanged(mqtt, 'enabled', 'setting-mqtt-enabled');
  includeIfChanged(mqtt, 'host', 'setting-mqtt-host');
  includeNumberIfChanged(mqtt, 'port', 'setting-mqtt-port');
  includeIfChanged(mqtt, 'username', 'setting-mqtt-username');
  const mqttPassword = value('setting-mqtt-password');
  if (mqttPassword && !mqttPassword.includes('***')) mqtt.password = mqttPassword;
  includeIfChanged(mqtt, 'topic_prefix', 'setting-topic-prefix');
  includeCheckboxIfChanged(mqtt, 'discovery', 'setting-mqtt-discovery');
  includeIfChanged(mqtt, 'discovery_prefix', 'setting-discovery-prefix');
  if (hasKeys(mqtt)) payload.mqtt = mqtt;

  const frigate = {};
  includeCheckboxIfChanged(frigate, 'enabled', 'setting-frigate-enabled');
  includeIfChanged(frigate, 'events_topic', 'setting-frigate-topic');
  includeIfChanged(frigate, 'camera_name', 'setting-frigate-camera');
  includeIfChanged(frigate, 'api_url', 'setting-frigate-api-url');
  includeCheckboxIfChanged(frigate, 'person_count_enabled', 'setting-frigate-person-count-enabled');
  includeNumberIfChanged(frigate, 'person_count_interval_seconds', 'setting-frigate-person-count-interval');
  includeIfChanged(frigate, 'dog_name', 'setting-frigate-dog-name');
  if (hasKeys(frigate)) payload.frigate = frigate;

  const faceRecognition = {};
  includeCheckboxIfChanged(faceRecognition, 'enabled', 'setting-face-enabled');
  includeIfChanged(faceRecognition, 'events_topic', 'setting-face-topic');
  includeNumberIfChanged(faceRecognition, 'min_confidence', 'setting-face-confidence');
  if (hasKeys(faceRecognition)) payload.face_recognition = faceRecognition;

  const announcements = {};
  includeCheckboxIfChanged(announcements, 'enabled', 'setting-announcements-enabled');
  includeCheckboxIfChanged(announcements, 'announce_known', 'setting-announcements-known');
  includeCheckboxIfChanged(announcements, 'announce_unknown', 'setting-announcements-unknown');
  includeCheckboxIfChanged(announcements, 'announce_dog', 'setting-announcements-dog');
  includeCheckboxIfChanged(announcements, 'random_texts_enabled', 'setting-announcements-random');
  includeNumberIfChanged(announcements, 'global_cooldown_seconds', 'setting-announcements-global-cooldown');
  includeNumberIfChanged(announcements, 'entity_cooldown_seconds', 'setting-announcements-entity-cooldown');
  includeIfChanged(announcements, 'disabled_entities', 'setting-announcements-disabled');
  if (fieldChanged('setting-announcements-custom-texts')) announcements.custom_texts = document.getElementById('setting-announcements-custom-texts').value.trim();
  if (hasKeys(announcements)) payload.announcements = announcements;

  const terraceDoor = {};
  includeCheckboxIfChanged(terraceDoor, 'enabled', 'setting-door-enabled');
  includeCheckboxIfChanged(terraceDoor, 'open', 'setting-door-open');
  includeNumberIfChanged(terraceDoor, 'confidence', 'setting-door-confidence');
  includeIfChanged(terraceDoor, 'last_changed', 'setting-door-last-changed');
  if (hasKeys(terraceDoor)) payload.terrace_door = terraceDoor;

  return payload;
}

function cameraFromForm() {
  const camera = {};
  includeIfChanged(camera, 'name', 'camera-name');
  includeIfChanged(camera, 'host', 'camera-host');
  const rtspUrl = document.getElementById('camera-rtsp').value.trim();
  const snapshotUrl = document.getElementById('camera-snapshot').value.trim();
  if (fieldChanged('camera-rtsp') && rtspUrl && !rtspUrl.includes('***')) camera.rtsp_url = rtspUrl;
  if (fieldChanged('camera-snapshot') && snapshotUrl && !snapshotUrl.includes('***')) camera.snapshot_url = snapshotUrl;
  return camera;
}

function populateCameraForm(camera) {
  if (formState.populated || !camera) return;
  setField('camera-name', camera.name || '');
  setField('camera-host', camera.host || '');
  setField('camera-rtsp', camera.rtsp_url && !camera.rtsp_url.includes('***') ? camera.rtsp_url : '');
  setField('camera-snapshot', camera.snapshot_url && !camera.snapshot_url.includes('***') ? camera.snapshot_url : '');
  formState.populated = true;
}

function populateAppForm(config) {
  if (formState.appPopulated || !config) return;
  const mqtt = config.mqtt || {};
  const frigate = config.frigate || {};
  const face = config.face_recognition || {};
  const announcements = config.announcements || {};
  const door = config.terrace_door || {};
  setField('setting-demo-mode', config.demo_mode);
  setField('setting-event-interval', config.event_interval_seconds ?? '');
  setField('setting-log-level', config.log_level || 'info');
  setField('setting-mqtt-enabled', mqtt.enabled);
  setField('setting-mqtt-host', mqtt.host || '');
  setField('setting-mqtt-port', mqtt.port ?? '');
  setField('setting-mqtt-username', mqtt.username || '');
  setField('setting-mqtt-password', mqtt.password && !mqtt.password.includes('***') ? mqtt.password : '');
  setField('setting-topic-prefix', mqtt.topic_prefix || '');
  setField('setting-mqtt-discovery', mqtt.discovery);
  setField('setting-discovery-prefix', mqtt.discovery_prefix || '');
  setField('setting-frigate-enabled', frigate.enabled);
  setField('setting-frigate-topic', frigate.events_topic || '');
  setField('setting-frigate-camera', frigate.camera_name || '');
  setField('setting-frigate-api-url', frigate.api_url || '');
  setField('setting-frigate-person-count-enabled', frigate.person_count_enabled);
  setField('setting-frigate-person-count-interval', frigate.person_count_interval_seconds ?? '');
  setField('setting-frigate-dog-name', frigate.dog_name || '');
  setField('setting-face-enabled', face.enabled);
  setField('setting-face-topic', face.events_topic || '');
  setField('setting-face-confidence', face.min_confidence ?? '');
  setField('setting-announcements-enabled', announcements.enabled);
  setField('setting-announcements-known', announcements.announce_known);
  setField('setting-announcements-unknown', announcements.announce_unknown);
  setField('setting-announcements-dog', announcements.announce_dog);
  setField('setting-announcements-random', announcements.random_texts_enabled);
  setField('setting-announcements-global-cooldown', announcements.global_cooldown_seconds ?? '');
  setField('setting-announcements-entity-cooldown', announcements.entity_cooldown_seconds ?? '');
  setField('setting-announcements-disabled', announcements.disabled_entities || '');
  setField('setting-announcements-custom-texts', announcements.custom_texts || '');
  setField('setting-door-enabled', door.enabled);
  setField('setting-door-open', door.open);
  setField('setting-door-confidence', door.confidence ?? '');
  setField('setting-door-last-changed', door.last_changed || '');
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
  const query = tableSearch('history');
  const rows = filterRows(items || [], 'history').reverse();
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
    addHighlightedCell(row, item.timestamp || '-', query);
    addHighlightedCell(row, item.person_count ?? 0, query);
    addHighlightedCell(row, item.maja_present ? 'Maja' : (item.dog_count || 0), query);
    addHighlightedCell(row, recognized, query);
    addHighlightedCell(row, announcement, query);
    addHighlightedCell(row, item.source || '-', query);
    body.appendChild(row);
  }
}

function renderRecognitionHistory(items) {
  const body = document.getElementById('recognition-history-body');
  if (!body) return;
  const query = tableSearch('recognition');
  const rows = filterRows(items || [], 'recognition').reverse();
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
    addHighlightedCell(row, item.timestamp || '-', query);
    addHighlightedCell(row, (item.recognized_entities || item.known_faces || []).join(', ') || '-', query);
    addHighlightedCell(row, item.unknown_faces ?? 0, query);
    addHighlightedCell(row, item.maja_present ? 'Maja' : (item.dog_count || 0), query);
    addHighlightedCell(row, item.source || '-', query);
    body.appendChild(row);
  });
}

function renderMqttHistory(items) {
  const body = document.getElementById('mqtt-history-body');
  if (!body) return;
  const query = tableSearch('mqtt');
  const rows = filterRows(items || [], 'mqtt').reverse();
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
    addHighlightedCell(row, item.timestamp || '-', query);
    addHighlightedCell(row, item.direction === 'in' ? 'rein' : 'raus', query);
    addHighlightedCell(row, item.topic || '-', query);
    addHighlightedCell(row, typeof item.payload === 'string' ? item.payload : JSON.stringify(item.payload), query);
    addHighlightedCell(row, `qos ${item.qos ?? 0}${item.retain ? ', retain' : ''}`, query);
    body.appendChild(row);
  });
}

function renderAnnouncementHistory(items) {
  const body = document.getElementById('announcement-history-body');
  if (!body) return;
  const query = tableSearch('announcement');
  const rows = filterRows(items || [], 'announcement').reverse();
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
    addHighlightedCell(row, item.timestamp || '-', query);
    addHighlightedCell(row, item.text || '-', query);
    addHighlightedCell(row, item.spoken ? 'ja' : 'nein', query);
    addHighlightedCell(row, (item.entities || []).join(', ') || '-', query);
    addHighlightedCell(row, item.suppressed_reason || '-', query);
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
  const rawConfig = configData.raw_config || safeConfig;
  const event = data.last_event || {};
  const storage = configData.storage_status || data.storage_status || {};
  const appStatus = data.app_status || {};
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
  renderKeyValueList('last-event-list', [
    ['Zeit', event.timestamp || 'noch kein Event'],
    ['Quelle', event.source || '-'],
    ['Kamera', event.camera || '-'],
    ['Personen', event.person_count ?? 0],
    ['Bekannte Gesichter', (event.known_faces || []).join(', ') || 'keine'],
    ['Erkannte Namen/Tiere', (recognizedEntities || []).join(', ') || 'keine'],
    ['Unbekannte Personen', event.unknown_faces ?? 0],
    ['Hund', event.maja_present ? 'Maja' : (event.dog_count ?? 0)],
    ['Status', event.status || '-'],
    ['Snapshot', event.snapshot_available ? 'verfuegbar' : 'nicht verfuegbar'],
  ]);
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
  text('recognized-count-card', recognizedEntities.length || 0);
  text('recognized-count-detail', recognizedEntities.join(', ') || 'keine Namen');
  text('ha-status-card', appStatus.home_assistant || '-');
  text('go2rtc-status-card', appStatus.go2rtc || '-');
  text('apps-status-card', `Bridge ${appStatus.bridge || '-'} · Frigate ${appStatus.frigate || '-'} · MQTT ${appStatus.mqtt || '-'}`);
  text('last-error-card', appStatus.last_error || 'kein Fehler');
  setStatusBadge('mqtt-username-status', storage.mqtt_username_set, 'Benutzer gesetzt', 'Benutzer nicht gesetzt');
  setStatusBadge('mqtt-password-status', storage.mqtt_password_set, 'Passwort gesetzt', 'Passwort nicht gesetzt');
  setStatusBadge('rtsp-url-status', storage.rtsp_url_set, rawConfig.camera?.rtsp_url || data.camera?.rtsp_url || 'RTSP gesetzt', 'RTSP nicht gesetzt');
  setStatusBadge('snapshot-url-status', storage.snapshot_url_set, rawConfig.camera?.snapshot_url || data.camera?.snapshot_url || 'Snapshot gesetzt', 'Snapshot nicht gesetzt');
  renderKeyValueList('debug-list', [
    ['Bridge', appStatus.bridge || '-'],
    ['Home Assistant', appStatus.home_assistant || '-'],
    ['MQTT', appStatus.mqtt || '-'],
    ['Frigate', appStatus.frigate || '-'],
    ['go2rtc', appStatus.go2rtc || '-'],
    ['Letzter Fehler', appStatus.last_error || 'kein Fehler'],
    ['Konfigurationswarnungen', (data.config_errors || []).join(' | ') || 'keine'],
    ['MQTT Prefix', data.mqtt?.topic_prefix || '-'],
    ['MQTT History', `${(data.mqtt_history || []).length} Nachrichten im Speicher`],
    ['Ausgabe-Topics', `${(data.mqtt_output_topics || []).length} Topics`],
    ['Frigate aktive Zaehler', data.frigate_active_count ?? 0],
  ]);
  renderPersonChart(data.person_count_series || []);
  renderHistory(data.history || []);
  renderRecognitionHistory(data.history || []);
  renderAnnouncementHistory(data.announcement_history || []);
  renderMqttHistory(data.mqtt_history || []);
  renderTopicList(data.mqtt_output_topics || []);
  renderFaces(data.known_faces || []);
  populateCameraForm(data.camera);
  populateAppForm(rawConfig);
}

async function saveAppConfig(event) {
  event.preventDefault();
  const message = document.getElementById('app-message');
  message.textContent = 'Speichere Betriebs-Konfiguration ...';
  try {
    const payload = appConfigFromForm();
    if (!hasKeys(payload)) {
      message.textContent = 'Keine Aenderungen erkannt.';
      return;
    }
    const response = await fetch(apiPath('api/config'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.error || `status ${response.status}`);
    formState.appPopulated = false;
    populateAppForm(data.raw_config || data.config);
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
    const camera = cameraFromForm();
    if (!hasKeys(camera)) {
      message.textContent = 'Keine Aenderungen erkannt.';
      return;
    }
    const response = await fetch(apiPath('api/config/camera'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ camera }),
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

async function runTest(endpoint, targetId, body = {}) {
  const message = document.getElementById(targetId);
  message.textContent = 'Teste ...';
  try {
    const response = await fetch(apiPath(endpoint), {
      method: 'POST',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    const detail = data.url ? ` · ${data.url}` : data.host ? ` · ${data.host}:${data.port || ''}` : '';
    message.textContent = `${data.ok ? 'OK' : 'Fehler'}: ${data.status || data.error || response.status}${detail}`;
  } catch (err) {
    message.textContent = `Test fehlgeschlagen: ${err}`;
  }
}

function useRtspExample() {
  const input = document.getElementById('camera-rtsp');
  input.value = 'rtsp://fossflow.localdomain:8554/wohnzimmer_g3_flex';
  input.dispatchEvent(new Event('input', { bubbles: true }));
}

function setupFilters() {
  ['history', 'recognition', 'announcement', 'mqtt'].forEach((prefix) => {
    ['range', 'search'].forEach((suffix) => {
      const element = document.getElementById(`${prefix}-${suffix}`);
      if (element) element.addEventListener('input', () => refreshStatus().catch(() => {}));
    });
  });
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
  setupFilters();
  document.getElementById('app-form').addEventListener('submit', saveAppConfig);
  document.getElementById('camera-form').addEventListener('submit', saveCamera);
  document.getElementById('face-form').addEventListener('submit', createFace);
  document.getElementById('snapshot-button').addEventListener('click', loadSnapshot);
  document.getElementById('mqtt-test-button').addEventListener('click', () => runTest('api/test/mqtt', 'mqtt-test-message', { mqtt: currentMqttSettings() }));
  document.getElementById('frigate-test-button').addEventListener('click', () => runTest('api/test/frigate', 'frigate-test-message', { frigate: currentFrigateSettings() }));
  document.getElementById('rtsp-test-button').addEventListener('click', () => runTest('api/test/rtsp', 'rtsp-test-message', { camera: currentCameraSettings() }));
  document.getElementById('snapshot-test-button').addEventListener('click', () => runTest('api/test/snapshot', 'snapshot-test-message', { camera: currentCameraSettings() }));
  document.getElementById('rtsp-example-button').addEventListener('click', useRtspExample);
  try {
    await refreshStatus();
  } catch (err) {
    document.getElementById('status').textContent = 'fehler';
    document.getElementById('debug').textContent = String(err);
  }
  window.setInterval(() => refreshStatus().catch(() => {}), 5000);
}

boot();
