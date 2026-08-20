/**
 * Preset Surface Manager
 * Handles preset topologies, icons, and UI rendering for the 5 presets.
 */

export const PRESET_ICONS = {
  floor: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polygon points="4 14 20 14 22 21 2 21"></polygon>
      <line x1="2" y1="14" x2="22" y2="14" stroke-dasharray="2 2"></line>
    </svg>
  `,
  ceiling: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polygon points="2 3 22 3 20 10 4 10"></polygon>
      <line x1="4" y1="10" x2="20" y2="10" stroke-dasharray="2 2"></line>
    </svg>
  `,
  corner_bath: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
      <path d="M4 6 L12 3 L20 6"></path>
      <path d="M4 6 L4 18 L12 21 L20 18 L20 6"></path>
      <path d="M12 3 L12 21"></path>
    </svg>
  `,
  alcove_bath: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
      <path d="M3 5 L8 8 L16 8 L21 5"></path>
      <path d="M3 5 L3 19 L8 16 L16 16 L21 19 L21 5"></path>
      <path d="M8 8 L8 16"></path>
      <path d="M16 8 L16 16"></path>
    </svg>
  `,
  cali_bath: `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="3" y="3" width="18" height="18" rx="2"></rect>
      <line x1="9" y1="3" x2="9" y2="21"></line>
    </svg>
  `,
};

export function renderPresetsTray(presets, activePresetId, onSelectPreset) {
  const container = document.getElementById('presets-container');
  if (!container) return;

  container.innerHTML = '';

  presets.forEach((preset) => {
    const card = document.createElement('div');
    card.className = `preset-card ${preset.id === activePresetId ? 'active' : ''} ${!preset.enabled ? 'disabled' : ''}`;
    card.id = `preset-card-${preset.id}`;
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', preset.enabled ? '0' : '-1');

    const iconHtml = PRESET_ICONS[preset.id] || PRESET_ICONS.floor;
    const pointsInfo = preset.enabled 
      ? `${preset.point_count} dots &bull; ${preset.line_count} lines`
      : 'Coming Soon';

    card.innerHTML = `
      <div class="preset-icon-box">
        ${iconHtml}
      </div>
      <div class="preset-meta">
        <span class="preset-name">${preset.name}</span>
        <span class="preset-points-info">${pointsInfo}</span>
        ${!preset.enabled ? '<span class="preset-badge-soon">In Dev</span>' : ''}
      </div>
    `;

    if (preset.enabled) {
      card.addEventListener('click', () => {
        onSelectPreset(preset.id);
      });
    }

    container.appendChild(card);
  });
}

export function setActivePresetCard(presetId) {
  document.querySelectorAll('.preset-card').forEach((card) => {
    card.classList.remove('active');
  });
  const active = document.getElementById(`preset-card-${presetId}`);
  if (active) active.classList.add('active');
}
