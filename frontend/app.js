// SENTRIX Disaster Response & SEM Platform Console Controller
const API_BASE = '/api/v1';

let registeredSensors = [];
let activeIncidents = [];
let dispatchUnits = [];

// DOM Elements
const statIncidents = document.getElementById('statIncidents');
const statSensors = document.getElementById('statSensors');
const statEvacZones = document.getElementById('statEvacZones');
const statUnits = document.getElementById('statUnits');
const statAlerts = document.getElementById('statAlerts');
const refreshOverviewBtn = document.getElementById('refreshOverviewBtn');

// Sensor Elements
const sensorFleetContainer = document.getElementById('sensorFleetContainer');
const ingestSensorSelect = document.getElementById('ingestSensorSelect');
const ingestValue = document.getElementById('ingestValue');
const ingestUnitLabel = document.getElementById('ingestUnitLabel');
const ingestForm = document.getElementById('ingestForm');
const ingestResultOutput = document.getElementById('ingestResultOutput');

// Incident Elements
const incidentsContainer = document.getElementById('incidentsContainer');
const incidentDrawer = document.getElementById('incidentDrawer');
const newIncidentForm = document.getElementById('newIncidentForm');
const dispatchIncidentSelect = document.getElementById('dispatchIncidentSelect');
const broadcastIncidentSelect = document.getElementById('broadcastIncidentSelect');
const radarEvacCircle = document.getElementById('radarEvacCircle');
const activeZoneDetails = document.getElementById('activeZoneDetails');

// Dispatch Elements
const dispatchContainer = document.getElementById('dispatchContainer');
const calcProximityBtn = document.getElementById('calcProximityBtn');
const proximityContainer = document.getElementById('proximityContainer');

// Broadcast Elements
const broadcastForm = document.getElementById('broadcastForm');
const broadcastsContainer = document.getElementById('broadcastsContainer');

// Tab Switching
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

    btn.classList.add('active');
    const tabId = btn.getAttribute('data-tab');
    document.getElementById(tabId).classList.add('active');
  });
});

function toggleIncidentModal() {
  incidentDrawer.classList.toggle('hidden');
}

// 1. Fetch Situational Overview
async function fetchOverview() {
  try {
    const res = await fetch(`${API_BASE}/operations/overview`);
    if (!res.ok) throw new Error('Failed to load overview');
    const data = await res.json();

    statIncidents.textContent = data.active_incidents;
    statSensors.textContent = data.online_sensors;
    statEvacZones.textContent = data.evacuation_zones_active;
    statUnits.textContent = data.available_dispatch_units;
    statAlerts.textContent = data.critical_alerts_count;
  } catch (err) {
    console.error('Error fetching overview:', err);
  }
}

// 2. Fetch SEM Sensors
async function fetchSensors() {
  try {
    const res = await fetch(`${API_BASE}/telemetry/sensors`);
    if (!res.ok) throw new Error('Failed to load sensors');
    registeredSensors = await res.json();

    renderSensorsList();
    populateSensorDropdown();
  } catch (err) {
    console.error('Error fetching sensors:', err);
  }
}

function renderSensorsList() {
  sensorFleetContainer.innerHTML = registeredSensors.map(s => {
    let readingDisplay = s.last_reading !== null ? `${s.last_reading} ${s.unit}` : 'NOMINAL';
    let statusClass = 'badge-normal';
    let statusText = s.status;

    if (s.last_reading !== null) {
      if (s.last_reading >= s.critical_threshold) {
        statusClass = 'badge-critical';
        statusText = 'CRITICAL ALERT';
      } else if (s.last_reading >= s.warning_threshold) {
        statusClass = 'badge-warning';
        statusText = 'STAGE WARNING';
      }
    }

    return `
      <div class="sensor-card">
        <div class="sensor-main">
          <span class="sensor-title">${escapeHtml(s.name)}</span>
          <span class="sensor-meta">
            TYPE: <strong>${s.sensor_type}</strong> | LOC: ${escapeHtml(s.location_name)} (${s.latitude.toFixed(4)}, ${s.longitude.toFixed(4)})
          </span>
          <span class="sensor-meta">
            THRESHOLDS: Warning ≥ ${s.warning_threshold}${s.unit} | Critical ≥ ${s.critical_threshold}${s.unit}
          </span>
        </div>
        <div class="sensor-reading">
          <span class="reading-val font-mono">${readingDisplay}</span>
          <span class="badge-status ${statusClass}">${statusText}</span>
        </div>
      </div>
    `;
  }).join('');
}

function populateSensorDropdown() {
  ingestSensorSelect.innerHTML = registeredSensors.map(s => `
    <option value="${s.id}" data-unit="${s.unit}" data-type="${s.sensor_type}">
      ${escapeHtml(s.name)} (${s.sensor_type} - ${s.unit})
    </option>
  `).join('');

  if (registeredSensors.length > 0) {
    updateSensorUnitLabel();
  }
}

ingestSensorSelect.addEventListener('change', updateSensorUnitLabel);

function updateSensorUnitLabel() {
  const selectedOption = ingestSensorSelect.options[ingestSensorSelect.selectedIndex];
  if (selectedOption) {
    const unit = selectedOption.getAttribute('data-unit') || 'g';
    ingestUnitLabel.textContent = unit;
  }
}

function setPreset(presetType) {
  if (presetType === 'SEISMIC_QUIET') {
    const s = registeredSensors.find(x => x.sensor_type === 'SEISMIC');
    if (s) ingestSensorSelect.value = s.id;
    ingestValue.value = 0.012;
  } else if (presetType === 'SEISMIC_CRITICAL') {
    const s = registeredSensors.find(x => x.sensor_type === 'SEISMIC');
    if (s) ingestSensorSelect.value = s.id;
    ingestValue.value = 0.45;
  } else if (presetType === 'FLOOD_CRITICAL') {
    const s = registeredSensors.find(x => x.sensor_type === 'FLOOD');
    if (s) ingestSensorSelect.value = s.id;
    ingestValue.value = 7.8;
  }
  updateSensorUnitLabel();
}

// Handle Ingest Telemetry Submit
ingestForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const sensor_id = ingestSensorSelect.value;
  const value = parseFloat(ingestValue.value);

  try {
    const res = await fetch(`${API_BASE}/telemetry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sensor_id, value, metric_name: 'simulated_telemetry' })
    });

    if (!res.ok) throw new Error('Ingestion failed');
    const result = await res.json();

    ingestResultOutput.textContent = JSON.stringify({
      log_id: result.log_id,
      sensor_id: result.sensor_id,
      value: `${result.value} ${result.unit}`,
      alert_level: result.alert_level,
      is_alert: result.is_alert,
      assessment: result.assessment
    }, null, 2);

    fetchOverview();
    fetchSensors();
  } catch (err) {
    alert(`Telemetry transmit error: ${err.message}`);
  }
});

// 3. Fetch Incidents
async function fetchIncidents() {
  try {
    const res = await fetch(`${API_BASE}/operations/incidents`);
    if (!res.ok) throw new Error('Failed to load incidents');
    activeIncidents = await res.json();

    renderIncidentsList();
    populateIncidentDropdowns();
  } catch (err) {
    console.error('Error fetching incidents:', err);
  }
}

function renderIncidentsList() {
  if (activeIncidents.length === 0) {
    incidentsContainer.innerHTML = '<div class="empty-state">No active incidents declared.</div>';
    return;
  }

  incidentsContainer.innerHTML = activeIncidents.map(inc => `
    <div class="incident-card ${inc.evacuation_ordered ? 'has-evac' : ''}">
      <div class="inc-info">
        <span class="inc-title">${escapeHtml(inc.title)}</span>
        <span class="inc-meta">
          ID: <strong>${inc.id}</strong> | TYPE: ${inc.disaster_type} | SEVERITY: <strong class="text-red">${inc.severity}</strong>
        </span>
        <span class="inc-meta">
          CORDON: ${inc.affected_radius_km} km radius | EVACUATION: 
          <strong class="${inc.evacuation_ordered ? 'text-amber' : 'text-emerald'}">
            ${inc.evacuation_ordered ? 'MANDATORY DIRECTIVE ACTIVE' : 'NONE'}
          </strong>
        </span>
      </div>
      <div>
        <button class="btn btn-sm ${inc.evacuation_ordered ? 'btn-outline' : 'btn-red'}" 
                onclick="toggleEvacuationOrder('${inc.id}', ${!inc.evacuation_ordered})">
          ${inc.evacuation_ordered ? 'Lift Evacuation' : 'Order Evacuation'}
        </button>
      </div>
    </div>
  `).join('');
}

function populateIncidentDropdowns() {
  const options = activeIncidents.map(inc => `
    <option value="${inc.id}">[${inc.id}] ${escapeHtml(inc.title)} (${inc.severity})</option>
  `).join('');

  dispatchIncidentSelect.innerHTML = options;
  broadcastIncidentSelect.innerHTML = options;
}

async function toggleEvacuationOrder(incidentId, order) {
  try {
    const res = await fetch(`${API_BASE}/operations/incidents/${incidentId}/evacuate?order=${order}`, {
      method: 'PATCH'
    });
    if (!res.ok) throw new Error('Failed to update evacuation order');
    fetchIncidents();
    fetchOverview();
  } catch (err) {
    alert(`Error updating evacuation order: ${err.message}`);
  }
}

// Declare Incident
newIncidentForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const title = document.getElementById('incTitle').value.trim();
  const disaster_type = document.getElementById('incType').value;
  const severity = document.getElementById('incSeverity').value;
  const latitude = parseFloat(document.getElementById('incLat').value);
  const longitude = parseFloat(document.getElementById('incLon').value);
  const affected_radius_km = parseFloat(document.getElementById('incRadius').value);
  const evacuation_ordered = document.getElementById('incEvac').checked;

  try {
    const res = await fetch(`${API_BASE}/operations/incidents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title, disaster_type, severity, latitude, longitude,
        affected_radius_km, evacuation_ordered
      })
    });

    if (!res.ok) throw new Error('Incident creation failed');
    newIncidentForm.reset();
    toggleIncidentModal();
    fetchIncidents();
    fetchOverview();
  } catch (err) {
    alert(`Error declaring incident: ${err.message}`);
  }
});

// 4. Fetch Dispatch Units
async function fetchDispatchUnits() {
  try {
    const res = await fetch(`${API_BASE}/operations/dispatch/units`);
    if (!res.ok) throw new Error('Failed to load dispatch units');
    dispatchUnits = await res.json();

    renderDispatchUnits();
  } catch (err) {
    console.error('Error loading dispatch units:', err);
  }
}

function renderDispatchUnits() {
  dispatchContainer.innerHTML = dispatchUnits.map(u => `
    <div class="dispatch-card">
      <div>
        <span class="inc-title">${escapeHtml(u.unit_name)}</span>
        <span class="inc-meta">
          ROLE: <strong>${u.unit_type}</strong> | CAPACITY: ${u.capacity} personnel | BASE: (${u.latitude.toFixed(4)}, ${u.longitude.toFixed(4)})
        </span>
        ${u.assigned_incident_id ? `<span class="inc-meta text-amber">ASSIGNED: ${u.assigned_incident_id}</span>` : ''}
      </div>
      <div>
        <span class="badge-status ${u.status === 'AVAILABLE' ? 'badge-normal' : 'badge-warning'}">
          ${u.status}
        </span>
      </div>
    </div>
  `).join('');
}

// Proximity Calculation
calcProximityBtn.addEventListener('click', async () => {
  const incId = dispatchIncidentSelect.value;
  if (!incId) {
    alert('Select an incident first.');
    return;
  }

  calcProximityBtn.disabled = true;
  calcProximityBtn.textContent = 'Computing Haversine Distances...';

  try {
    const res = await fetch(`${API_BASE}/operations/dispatch/units?incident_id=${incId}`);
    if (!res.ok) throw new Error('Calculation failed');
    const ranked = await res.json();

    proximityContainer.innerHTML = ranked.map((u, idx) => `
      <div class="proximity-item ${idx === 0 ? 'top-rank' : ''}">
        <div>
          <span style="font-weight:600;">${idx + 1}. ${escapeHtml(u.unit_name)}</span>
          <span class="inc-meta" style="display:block;">
            Distance: <strong>${u.distance_km} km</strong> | Est. Transit ETA: <strong class="text-cyan">${u.estimated_eta_min} mins</strong>
          </span>
        </div>
        <div>
          ${u.status === 'AVAILABLE' ? 
            `<button class="btn btn-xs btn-primary" onclick="assignUnit('${u.id}', '${incId}')">Deploy Unit</button>` :
            `<span class="badge-status badge-warning">DEPLOYED</span>`
          }
        </div>
      </div>
    `).join('');
  } catch (err) {
    proximityContainer.innerHTML = `<div class="empty-state text-red">Error: ${err.message}</div>`;
  } finally {
    calcProximityBtn.disabled = false;
    calcProximityBtn.textContent = 'Calculate Nearest Units';
  }
});

async function assignUnit(unitId, incidentId) {
  try {
    const res = await fetch(`${API_BASE}/operations/dispatch/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ unit_id: unitId, incident_id: incidentId })
    });
    if (!res.ok) throw new Error('Assignment failed');
    alert(`Unit successfully deployed to incident ${incidentId}!`);
    fetchDispatchUnits();
    fetchOverview();
    calcProximityBtn.click();
  } catch (err) {
    alert(`Deploy error: ${err.message}`);
  }
}

// 5. Emergency Broadcasts
async function fetchBroadcasts() {
  try {
    const res = await fetch(`${API_BASE}/operations/broadcasts`);
    if (!res.ok) throw new Error('Failed to load broadcasts');
    const broadcasts = await res.json();

    if (broadcasts.length === 0) {
      broadcastsContainer.innerHTML = '<div class="empty-state">No emergency civil broadcasts logged.</div>';
      return;
    }

    broadcastsContainer.innerHTML = broadcasts.map(b => `
      <div class="broadcast-item ${b.alert_level.includes('CRITICAL') ? 'crit' : ''}">
        <span class="inc-meta font-mono">
          EAS BROADCAST [${b.id}] | INCIDENT: ${b.incident_id} | ${new Date(b.created_at).toLocaleTimeString()}
        </span>
        <span class="b-head">${escapeHtml(b.headline)}</span>
        <p class="b-body">${escapeHtml(b.instructions)}</p>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading broadcasts:', err);
  }
}

broadcastForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const incident_id = broadcastIncidentSelect.value;
  const alert_level = document.getElementById('broadcastLevel').value;
  const headline = document.getElementById('broadcastHeadline').value.trim();
  const instructions = document.getElementById('broadcastInstructions').value.trim();

  try {
    const res = await fetch(`${API_BASE}/operations/broadcasts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id, alert_level, headline, instructions })
    });

    if (!res.ok) throw new Error('Broadcast transmit failed');
    alert('Emergency Civil Broadcast successfully transmitted across all channels!');
    broadcastForm.reset();
    fetchBroadcasts();
  } catch (err) {
    alert(`Broadcast error: ${err.message}`);
  }
});

refreshOverviewBtn.addEventListener('click', () => {
  fetchOverview();
  fetchSensors();
  fetchIncidents();
  fetchDispatchUnits();
  fetchBroadcasts();
});

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Initial Boot
fetchOverview();
fetchSensors();
fetchIncidents();
fetchDispatchUnits();
fetchBroadcasts();
