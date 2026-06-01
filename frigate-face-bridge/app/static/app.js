const formState = {
  populated: false,
};

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

async function refreshStatus() {
  const response = await fetch('/api/status', { cache: 'no-store' });
  if (!response.ok) throw new Error(`status ${response.status}`);
  const data = await response.json();
  const event = data.last_event || {};
  document.getElementById('status').textContent = data.ok ? 'online' : 'fehler';
  document.getElementById('started').textContent = `Start: ${data.started_at || '-'}`;
  document.getElementById('camera').textContent = data.camera?.name || '-';
  document.getElementById('camera-details').textContent = `${data.camera?.host || 'kein Host'} - RTSP: ${data.camera?.rtsp_configured ? 'konfiguriert' : 'offen'}`;
  document.getElementById('mqtt').textContent = data.mqtt?.enabled ? (data.mqtt?.connected ? 'verbunden' : 'aktiviert') : 'deaktiviert';
  document.getElementById('mqtt-topic').textContent = data.mqtt?.topic_prefix || '-';
  document.getElementById('person-count').textContent = event.person_count ?? 0;
  document.getElementById('event-time').textContent = event.timestamp || 'noch kein Event';
  document.getElementById('known-faces').textContent = (event.known_faces || []).join(', ') || 'keine';
  document.getElementById('unknown-faces').textContent = event.unknown_faces ?? 0;
  document.getElementById('demo-mode').textContent = data.demo_mode ? 'aktiv' : 'aus';
  document.getElementById('event-count').textContent = data.event_count ?? 0;
  document.getElementById('debug').textContent = JSON.stringify({ config_errors: data.config_errors || [], mqtt: data.mqtt }, null, 2);
  populateCameraForm(data.camera);
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
  document.getElementById('camera-form').addEventListener('submit', saveCamera);
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
