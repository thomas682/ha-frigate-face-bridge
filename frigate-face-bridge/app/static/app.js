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
}

async function boot() {
  try {
    await refreshStatus();
  } catch (err) {
    document.getElementById('status').textContent = 'fehler';
    document.getElementById('debug').textContent = String(err);
  }
  window.setInterval(() => refreshStatus().catch(() => {}), 5000);
}

boot();
