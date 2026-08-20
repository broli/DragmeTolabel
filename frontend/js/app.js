/**
 * DragmeTolabel - Main Application Coordinator
 */

import { fetchPresets, fetchMaterials, requestPreview, exportLabelmeJSON, autoFitPreset } from './api.js';
import { renderPresetsTray, setActivePresetCard } from './presets.js';
import { PolygonCanvas } from './canvas.js';
import { TouchLoupe } from './loupe.js';
import { ComparisonViewer } from './comparison.js';

class DragmeToLabelApp {
  constructor() {
    this.presets = [];
    this.materials = [];
    this.activePresetId = 'alcove_bath';
    this.activeMaterialId = 'carrara_marble';
    this.lightingIntensity = 0.85;
    this.tileScale = 1.0;

    this.hasLoadedImage = false;
    this.currentSamplePhoto = null;

    this.init();
  }

  async init() {
    // 1. Initialize UI components
    const canvasEl = document.getElementById('main-canvas');
    const loupeContainer = document.getElementById('loupe-container');
    const loupeCanvas = document.getElementById('loupe-canvas');
    const comparisonOverlay = document.getElementById('comparison-overlay');
    this.onboardingModal = document.getElementById('photo-onboarding-modal');
    this.btnCloseOnboarding = document.getElementById('btn-close-onboarding');
    this.surfaceDrawerOverlay = document.getElementById('surface-drawer-overlay');
    this.canvasHintEl = document.getElementById('canvas-hint');

    this.loupe = new TouchLoupe(loupeContainer, loupeCanvas);
    this.canvas = new PolygonCanvas(canvasEl, this.loupe, (points) => {
      // Points changed callback
    });
    this.comparison = new ComparisonViewer(comparisonOverlay);

    // 2. Fetch presets & materials from backend
    await this.loadPresetsAndMaterials();

    // 3. Setup event listeners for photo capture, toolbar, surface drawer, and sliders
    this.setupEventListeners();

    // 4. Present photo capture / attachment onboarding modal to user
    this.showOnboardingModal(false);
  }

  showOnboardingModal(allowDismiss = false) {
    if (!this.onboardingModal) return;
    this.onboardingModal.classList.remove('hidden');
    if (this.btnCloseOnboarding) {
      this.btnCloseOnboarding.style.display = allowDismiss || this.hasLoadedImage ? 'flex' : 'none';
    }
  }

  hideOnboardingModal() {
    if (!this.onboardingModal) return;
    this.onboardingModal.classList.add('hidden');
  }

  toggleSurfaceDrawer(show = null) {
    if (!this.surfaceDrawerOverlay) return;
    if (show === null) {
      this.surfaceDrawerOverlay.classList.toggle('hidden');
    } else if (show) {
      this.surfaceDrawerOverlay.classList.remove('hidden');
    } else {
      this.surfaceDrawerOverlay.classList.add('hidden');
    }
  }

  async loadPresetsAndMaterials() {
    try {
      [this.presets, this.materials] = await Promise.all([
        fetchPresets(),
        fetchMaterials(),
      ]);

      // Render Presets inside Drawer
      renderPresetsTray(this.presets, this.activePresetId, (presetId) => {
        this.selectPreset(presetId);
      });

      // Render Materials inside Drawer
      this.renderMaterialsGrid();

      // Set initial active preset in canvas
      const initialPreset = this.presets.find((p) => p.id === this.activePresetId);
      if (initialPreset) {
        this.canvas.setPreset(initialPreset);
      }

      this.updateBadges();
      this.updateHintPosition();
    } catch (err) {
      console.error('Failed to load initial metadata:', err);
      this.showToast('Could not connect to backend server. Using local defaults.');
    }
  }

  renderMaterialsGrid() {
    const container = document.getElementById('materials-container');
    if (!container) return;

    container.innerHTML = '';

    this.materials.forEach((mat) => {
      const card = document.createElement('div');
      card.className = `material-card ${mat.id === this.activeMaterialId ? 'active' : ''}`;
      card.id = `mat-card-${mat.id}`;
      card.title = mat.description;

      card.innerHTML = `
        <img src="${mat.thumbnail_url}" class="material-thumb" alt="${mat.name}" loading="lazy">
        <span class="material-name">${mat.name}</span>
      `;

      card.addEventListener('click', () => {
        this.selectMaterial(mat.id);
      });

      container.appendChild(card);
    });
  }

  async selectPreset(presetId) {
    const preset = this.presets.find((p) => p.id === presetId);
    if (!preset || !preset.enabled) return;

    this.activePresetId = presetId;
    setActivePresetCard(presetId);
    this.canvas.setPreset(preset);

    this.updateBadges();
    this.updateHintPosition();
    this.showToast(`Selected ${preset.name}`);

    // Auto-fit new preset geometry to active room photo
    if (this.hasLoadedImage) {
      await this.triggerAutoFit(presetId, true);
    }
  }

  async triggerAutoFit(presetId = null, silent = false) {
    const targetPresetId = presetId || this.activePresetId;
    if (!this.hasLoadedImage) return;

    try {
      const imgBase64 = this.canvas.getImageBase64();
      if (!imgBase64) return;

      const result = await autoFitPreset(imgBase64, targetPresetId);
      if (result && result.success && result.points && result.points.length > 0) {
        this.canvas.setCustomPoints(result.points);
        if (!silent) {
          const confPct = Math.round((result.confidence || 0.8) * 100);
          this.showToast(`✨ Auto-aligned ${this.activePresetId} corners (${confPct}% confidence)`);
        }
      }
    } catch (err) {
      console.warn('Auto-fit solver notification:', err);
    }
  }

  selectMaterial(materialId) {
    this.activeMaterialId = materialId;
    document.querySelectorAll('.material-card').forEach((card) => {
      card.classList.remove('active');
    });
    const active = document.getElementById(`mat-card-${materialId}`);
    if (active) active.classList.add('active');

    this.updateBadges();
  }

  updateBadges() {
    const preset = this.presets.find((p) => p.id === this.activePresetId);
    const material = this.materials.find((m) => m.id === this.activeMaterialId);

    const presetName = preset ? preset.name : this.activePresetId;
    const materialName = material ? material.name : this.activeMaterialId;

    const surfaceBadge = document.getElementById('surface-badge-pill');
    if (surfaceBadge) {
      surfaceBadge.textContent = presetName;
    }

    const drawerPresetBadge = document.getElementById('drawer-active-preset-badge');
    if (drawerPresetBadge) {
      drawerPresetBadge.textContent = presetName;
    }

    const drawerMaterialBadge = document.getElementById('drawer-active-material-badge');
    if (drawerMaterialBadge) {
      drawerMaterialBadge.textContent = materialName;
    }
  }

  updateHintPosition() {
    if (!this.canvasHintEl) return;
    // When doing flooring, move info message about dragging to the top of the photo
    if (this.activePresetId === 'floor') {
      this.canvasHintEl.classList.add('hint-top');
    } else {
      this.canvasHintEl.classList.remove('hint-top');
    }
  }

  async handleImageFile(file, targetPreset = null) {
    if (!file || !file.type.startsWith('image/')) {
      this.showToast('Please select a valid image file.');
      return;
    }

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        await this.canvas.loadImage(event.target.result);
        this.hasLoadedImage = true;
        this.currentSamplePhoto = null;

        if (targetPreset) {
          await this.selectPreset(targetPreset);
        } else {
          this.updateHintPosition();
          await this.triggerAutoFit(this.activePresetId, false);
        }

        this.hideOnboardingModal();
      } catch (err) {
        console.error('Failed to load image into canvas:', err);
        this.showToast('Failed to load selected photo.');
      }
    };
    reader.readAsDataURL(file);
  }

  async loadSamplePhoto(sampleUrl, targetPreset = null) {
    this.currentSamplePhoto = sampleUrl;
    try {
      await this.canvas.loadImage(sampleUrl);
      this.hasLoadedImage = true;
      if (targetPreset) {
        await this.selectPreset(targetPreset);
      } else {
        this.updateHintPosition();
        await this.triggerAutoFit(this.activePresetId, false);
      }
      this.hideOnboardingModal();
    } catch (err) {
      console.error('Sample loading error:', err);
      this.showToast('Failed to load sample photo.');
    }
  }

  setupEventListeners() {
    // 1. Camera Capture Input (Mobile / Tablet / Desktop native camera)
    const cameraInput = document.getElementById('camera-capture-input');
    if (cameraInput) {
      cameraInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          this.handleImageFile(file);
          cameraInput.value = ''; // Reset input to allow re-selection
        }
      });
    }

    // 2. Gallery / File Upload Input
    const galleryInput = document.getElementById('gallery-upload-input');
    if (galleryInput) {
      galleryInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          this.handleImageFile(file);
          galleryInput.value = ''; // Reset input to allow re-selection
        }
      });
    }

    // 3. Desktop Drag & Drop Zone in Onboarding Modal
    const dropzone = document.getElementById('onboarding-dropzone');
    if (dropzone) {
      dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });

      dropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });

      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
          this.handleImageFile(files[0]);
        }
      });

      dropzone.addEventListener('click', () => {
        if (galleryInput) galleryInput.click();
      });
    }

    // 4. Also support direct Drag & Drop onto the main canvas container
    const canvasContainer = document.getElementById('canvas-container');
    if (canvasContainer) {
      canvasContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
      });

      canvasContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
          this.handleImageFile(files[0]);
        }
      });
    }

    // 5. Onboarding Close Button (when re-opened)
    if (this.btnCloseOnboarding) {
      this.btnCloseOnboarding.addEventListener('click', () => {
        if (this.hasLoadedImage) {
          this.hideOnboardingModal();
        }
      });
    }

    // 6. Header "New Photo" Button
    const btnNewPhoto = document.getElementById('btn-new-photo');
    if (btnNewPhoto) {
      btnNewPhoto.addEventListener('click', () => {
        this.showOnboardingModal(true);
      });
    }

    // 7. Surface & Finish Menu Drawer Toggle & Dismiss Handlers
    const btnSurfaceMenu = document.getElementById('btn-surface-menu');
    if (btnSurfaceMenu) {
      btnSurfaceMenu.addEventListener('click', () => {
        this.toggleSurfaceDrawer();
      });
    }

    const btnCloseSurfaceDrawer = document.getElementById('btn-close-surface-drawer');
    if (btnCloseSurfaceDrawer) {
      btnCloseSurfaceDrawer.addEventListener('click', () => {
        this.toggleSurfaceDrawer(false);
      });
    }

    const surfaceDrawerBackdrop = document.getElementById('surface-drawer-backdrop');
    if (surfaceDrawerBackdrop) {
      surfaceDrawerBackdrop.addEventListener('click', () => {
        this.toggleSurfaceDrawer(false);
      });
    }

    const btnDoneSurfaceDrawer = document.getElementById('btn-done-surface-drawer');
    if (btnDoneSurfaceDrawer) {
      btnDoneSurfaceDrawer.addEventListener('click', () => {
        this.toggleSurfaceDrawer(false);
      });
    }

    const btnDrawerPreview = document.getElementById('btn-drawer-preview');
    if (btnDrawerPreview) {
      btnDrawerPreview.addEventListener('click', () => {
        this.toggleSurfaceDrawer(false);
        this.handlePreview();
      });
    }

    // 8. Demo Room Samples (Both in Onboarding modal and in Header dropdown)
    const sampleMap = {
      sample_bathroom_alcove: {
        url: '/assets/samples/sample_alcove_bath.jpg',
        preset: 'alcove_bath',
      },
      sample_bathroom_corner: {
        url: '/assets/samples/sample_corner_bath.jpg',
        preset: 'corner_bath',
      },
      sample_room_floor: {
        url: '/assets/samples/sample_room_floor.jpg',
        preset: 'floor',
      },
    };

    document.querySelectorAll('[data-sample]').forEach((item) => {
      item.addEventListener('click', () => {
        const sampleKey = item.getAttribute('data-sample');
        const config = sampleMap[sampleKey];
        if (config) {
          this.loadSamplePhoto(config.url, config.preset);
        }
      });
    });

    // 9. Header Samples Dropdown Menu Toggle
    const btnSamples = document.getElementById('btn-samples-menu');
    const dropdown = document.getElementById('samples-dropdown');
    if (btnSamples && dropdown) {
      btnSamples.addEventListener('click', (e) => {
        e.stopPropagation();
        dropdown.classList.toggle('show');
      });

      document.addEventListener('click', () => {
        dropdown.classList.remove('show');
      });
    }

    // 10. Sliders (Shadow Depth & Repetition / Tile Density)
    const sliderLighting = document.getElementById('slider-lighting');
    const labelLighting = document.getElementById('label-lighting-val');
    if (sliderLighting && labelLighting) {
      sliderLighting.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        this.lightingIntensity = val / 100.0;
        labelLighting.textContent = `${val}%`;
      });
    }

    const sliderScale = document.getElementById('slider-scale');
    const labelScale = document.getElementById('label-scale-val');
    if (sliderScale && labelScale) {
      sliderScale.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        this.tileScale = val / 10.0;
        labelScale.textContent = `${this.tileScale.toFixed(1)}x`;
      });
    }

    // 11. Auto-Fit Action in Header
    const btnAutoFit = document.getElementById('btn-autofit');
    if (btnAutoFit) {
      btnAutoFit.addEventListener('click', () => {
        this.triggerAutoFit(this.activePresetId, false);
      });
    }

    // 12. Preview Action in Header
    const btnPreview = document.getElementById('btn-preview');
    if (btnPreview) {
      btnPreview.addEventListener('click', () => {
        this.handlePreview();
      });
    }

    // 13. Export Action in Header
    const btnExport = document.getElementById('btn-export-json');
    if (btnExport) {
      btnExport.addEventListener('click', () => {
        this.handleExportJSON();
      });
    }
  }

  async handlePreview() {
    const loadingOverlay = document.getElementById('canvas-loading');
    loadingOverlay.style.display = 'flex';

    try {
      const imgBase64 = this.canvas.getImageBase64();
      const points = this.canvas.getPoints();

      if (!imgBase64 || !points.length) {
        throw new Error('Please load a photo first.');
      }

      const payload = {
        image_base64: imgBase64,
        preset_id: this.activePresetId,
        points: points,
        material_id: this.activeMaterialId,
        lighting_intensity: this.lightingIntensity,
        tile_scale: this.tileScale,
      };

      const response = await requestPreview(payload);

      if (response.success && response.processed_image_base64) {
        this.comparison.show(imgBase64, response.processed_image_base64);
        this.showToast(`Preview rendered in ${response.processing_time_ms}ms!`);
      } else {
        throw new Error(response.message || 'Preview generation failed.');
      }
    } catch (err) {
      console.error('Preview error:', err);
      this.showToast(err.message || 'Failed to render preview.');
    } finally {
      loadingOverlay.style.display = 'none';
    }
  }

  async handleExportJSON() {
    try {
      const imgBase64 = this.canvas.getImageBase64();
      const points = this.canvas.getPoints();

      if (!imgBase64 || !points.length) {
        throw new Error('No image loaded to export.');
      }

      const payload = {
        image_base64: imgBase64,
        preset_id: this.activePresetId,
        points: points,
        material_id: this.activeMaterialId,
      };

      const labelmeData = await exportLabelmeJSON(payload);

      // Trigger browser download
      const blob = new Blob([JSON.stringify(labelmeData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `dragmetolabel_${this.activePresetId}_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      this.showToast('Exported Labelme annotation JSON!');
    } catch (err) {
      this.showToast(err.message || 'Export failed.');
    }
  }

  showToast(message) {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toast-message');
    if (!toast || !toastMsg) return;

    toastMsg.textContent = message;
    toast.style.display = 'block';

    clearTimeout(this.toastTimeout);
    this.toastTimeout = setTimeout(() => {
      toast.style.display = 'none';
    }, 2800);
  }
}

// Bootstrap application on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.app = new DragmeToLabelApp();
});
