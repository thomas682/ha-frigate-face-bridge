const formState = {
  populated: false,
  appPopulated: false,
};

function checkbox(id) {
  return document.getElementById(id).checked;
}

function value(id) {
  return document.getElementById(id).value.trim();
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
  document.getElementById('setting-door-enabled').checked = Boolean(door.enabled);
  document.getElementById('setting-door-open').checked = Boolean(door.open);
  document.getElementById('setting-door-confidence').value = door.confidence ?? 0;
  document.getElementById('setting-door-last-changed').value = door.last_changed || '';
  formState.appPopulated = true;
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
  const max = Math.max(1, ...points.map((item) => Number(item.person_count || 0)));
  for (const item of points) {
    const bar = document.createElement('span');
    const count = Number(item.person_count || 0);
    bar.style.height = `${Math.max(6, (count / max) * 100)}%`;
    bar.title = `${item.timestamp || ''}: ${count} Personen`;
    bar.dataset.count = String(count);
    chart.appendChild(bar);
  }
}

function renderHistory(items) {
  const body = document.getElementById('history-body');
  if (!body) return;
  const rows = (items || []).slice(-20).reverse();
  body.innerHTML = '';
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="5">Noch keine History vorhanden.</td></tr>';
    return;
  }
  for (const item of rows) {
    const row = document.createElement('tr');
    const recognized = (item.recognized_entities || item.known_faces || []).join(', ') || '-';
    row.innerHTML = `<td>${item.timestamp || '-'}</td><td>${item.person_count ?? 0}</td><td>${item.maja_present ? 'Maja' : (item.dog_count || 0)}</td><td>${recognized}</td><td>${item.source || '-'}</td>`;
    body.appendChild(row);
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
    fetch('/api/status', { cache: 'no-store' }),
    fetch('/api/config', { cache: 'no-store' }),
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
  document.getElementById('last-dog-count').textContent = event.dog_count ?? 0;
  const door = data.terrace_door || {};
  document.getElementById('terrace-door-open').textContent = door.open ? 'offen' : 'geschlossen';
  document.getElementById('terrace-door-confidence').textContent = door.confidence ?? 0;
  document.getElementById('terrace-door-last-changed').textContent = door.last_changed || '-';
  document.getElementById('demo-mode').textContent = data.demo_mode ? 'aktiv' : 'aus';
  document.getElementById('event-count').textContent = data.event_count ?? 0;
  document.getElementById('frigate-event-count').textContent = data.frigate_event_count ?? 0;
  document.getElementById('face-event-count').textContent = data.face_event_count ?? 0;
  document.getElementById('debug').textContent = JSON.stringify({ config_errors: data.config_errors || [], mqtt: data.mqtt, frigate: safeConfig.frigate, frigate_active_count: data.frigate_active_count, face_recognition: safeConfig.face_recognition, terrace_door: safeConfig.terrace_door }, null, 2);
  renderPersonChart(data.person_count_series || []);
  renderHistory(data.history || []);
  renderFaces(data.known_faces || []);
  populateCameraForm(data.camera);
  populateAppForm(safeConfig);
}

async function saveAppConfig(event) {
  event.preventDefault();
  const message = document.getElementById('app-message');
  message.textContent = 'Speichere Betriebs-Konfiguration ...';
  try {
    const response = await fetch('/api/config', {
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
    const response = await fetch('/api/faces', {
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
    const response = await fetch(`/api/faces/${encodeURIComponent(name)}`, {
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
    const response = await fetch('/api/config/camera', {
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
    const response = await fetch(`/api/camera/snapshot?ts=${Date.now()}`, { cache: 'no-store' });
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
