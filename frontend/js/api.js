/**
 * DragmeTolabel API Client
 * Connects frontend to backend REST endpoints.
 */

const API_BASE = window.location.origin.includes('localhost') || window.location.origin.includes('127.0.0.1')
  ? `${window.location.origin}/api/v1`
  : '/api/v1';

export async function fetchPresets() {
  const res = await fetch(`${API_BASE}/presets`);
  if (!res.ok) throw new Error(`Failed to fetch presets: ${res.statusText}`);
  return await res.json();
}

export async function fetchMaterials() {
  const res = await fetch(`${API_BASE}/materials`);
  if (!res.ok) throw new Error(`Failed to fetch materials: ${res.statusText}`);
  return await res.json();
}

export async function autoFitPreset(imageBase64, presetId) {
  const res = await fetch(`${API_BASE}/autofit-preset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64: imageBase64, preset_id: presetId }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Auto-fit failed (${res.status})`);
  }
  return await res.json();
}

export async function requestPreview(payload) {
  const res = await fetch(`${API_BASE}/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Preview rendering failed (${res.status})`);
  }
  return await res.json();
}

export async function exportLabelmeJSON(payload) {
  const res = await fetch(`${API_BASE}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Export failed (${res.status})`);
  }
  return await res.json();
}
