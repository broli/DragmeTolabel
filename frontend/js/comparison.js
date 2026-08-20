/**
 * Before / After Preview Comparison Component
 * Provides interactive split comparison slider and toggle mode for sales reps to present to clients.
 */

export class ComparisonViewer {
  constructor(overlayEl, onClose) {
    this.overlay = overlayEl;
    this.onClose = onClose;

    this.container = document.getElementById('split-container');
    this.beforeImg = document.getElementById('before-image');
    this.afterImg = document.getElementById('after-image');
    this.afterWrapper = document.getElementById('after-wrapper');
    this.divider = document.getElementById('split-divider');
    this.btnClose = document.getElementById('btn-close-comparison');
    this.btnToggleMode = document.getElementById('btn-toggle-comparison-mode');

    this.splitPercent = 50;
    this.isDragging = false;
    this.viewMode = 'split'; // 'split' | 'toggle'
    this.toggleState = 'after'; // 'before' | 'after'

    this.initEventListeners();
  }

  show(beforeSrc, afterSrc) {
    this.beforeImg.src = beforeSrc;
    this.afterImg.src = afterSrc;

    // Reset split position to center
    this.splitPercent = 50;
    this.viewMode = 'split';
    this.btnToggleMode.textContent = 'Toggle View';
    this.updateSplitPosition();

    this.overlay.style.display = 'flex';
  }

  hide() {
    this.overlay.style.display = 'none';
    if (this.onClose) this.onClose();
  }

  updateSplitPosition() {
    if (this.viewMode === 'split') {
      this.afterWrapper.style.display = 'block';
      this.afterWrapper.style.width = `${this.splitPercent}%`;
      this.divider.style.display = 'block';
      this.divider.style.left = `${this.splitPercent}%`;
      this.afterImg.style.display = 'block';
    } else {
      // Toggle mode (flip full view)
      this.divider.style.display = 'none';
      if (this.toggleState === 'after') {
        this.afterWrapper.style.width = '100%';
        this.afterWrapper.style.display = 'block';
      } else {
        this.afterWrapper.style.width = '0%';
        this.afterWrapper.style.display = 'none';
      }
    }
  }

  initEventListeners() {
    this.btnClose.addEventListener('click', () => this.hide());

    this.btnToggleMode.addEventListener('click', () => {
      if (this.viewMode === 'split') {
        this.viewMode = 'toggle';
        this.btnToggleMode.textContent = 'Split View';
        this.toggleState = 'after';
      } else {
        this.viewMode = 'split';
        this.btnToggleMode.textContent = 'Toggle View';
      }
      this.updateSplitPosition();
    });

    const setPositionFromEvent = (e) => {
      const rect = this.container.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const x = clientX - rect.left;
      const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));
      this.splitPercent = percent;
      this.updateSplitPosition();
    };

    // Pointer / Mouse events on split container
    this.container.addEventListener('pointerdown', (e) => {
      if (this.viewMode === 'toggle') {
        this.toggleState = this.toggleState === 'after' ? 'before' : 'after';
        this.updateSplitPosition();
        return;
      }
      this.isDragging = true;
      this.container.setPointerCapture(e.pointerId);
      setPositionFromEvent(e);
    });

    window.addEventListener('pointermove', (e) => {
      if (this.isDragging && this.viewMode === 'split') {
        setPositionFromEvent(e);
      }
    });

    window.addEventListener('pointerup', () => {
      this.isDragging = false;
    });
  }
}
