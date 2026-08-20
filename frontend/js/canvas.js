/**
 * Interactive Polygon Canvas Engine
 * Handles HiDPI rendering, vertex dragging, whole-polygon translation, and touch gestures.
 */

export class PolygonCanvas {
  constructor(canvasEl, loupeInstance, onPointsChanged) {
    this.canvas = canvasEl;
    this.ctx = this.canvas.getContext('2d');
    this.loupe = loupeInstance;
    this.onPointsChanged = onPointsChanged;

    this.image = null;
    this.imageWidth = 0;
    this.imageHeight = 0;

    this.preset = null;
    this.points = []; // Pixel coordinates [[x, y], ...]
    this.history = [];

    // Interaction state
    this.dragMode = null; // 'vertex' | 'polygon' | null
    this.activePointIndex = -1;
    this.dragStartMouse = { x: 0, y: 0 };
    this.dragStartPoints = [];
    this.hoverPointIndex = -1;

    this.touchHitRadius = 26; // Touch hit radius in CSS pixels
    this.pointVisualRadius = 9; // Rendered circle radius in CSS pixels

    this.initEventListeners();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  loadImage(imgSrc) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => {
        this.image = img;
        this.imageWidth = img.naturalWidth;
        this.imageHeight = img.naturalHeight;
        this.resizeCanvas();
        if (this.preset) {
          this.applyPreset(this.preset, true);
        }
        this.render();
        resolve(img);
      };
      img.onerror = reject;
      img.src = imgSrc;
    });
  }

  setPreset(preset) {
    this.preset = preset;
    if (this.image) {
      this.applyPreset(preset, true);
      this.render();
    }
  }

  applyPreset(preset, recordHistory = true) {
    if (!this.image || !preset || !preset.default_normalized_points) return;
    
    // Scale normalized [0, 1] preset points to actual image pixel coordinates
    this.points = preset.default_normalized_points.map(([nx, ny]) => [
      nx * this.imageWidth,
      ny * this.imageHeight,
    ]);

    if (recordHistory) {
      this.saveHistory();
    }

    if (this.onPointsChanged) {
      this.onPointsChanged(this.points);
    }
  }

  setCustomPoints(points, recordHistory = true) {
    if (!this.image || !points || !points.length) return;
    this.points = JSON.parse(JSON.stringify(points));
    if (recordHistory) {
      this.saveHistory();
    }
    if (this.onPointsChanged) {
      this.onPointsChanged(this.points);
    }
    this.render();
  }

  resetPoints() {
    if (this.preset) {
      this.applyPreset(this.preset, true);
      this.render();
    }
  }

  saveHistory() {
    this.history.push(JSON.parse(JSON.stringify(this.points)));
    if (this.history.length > 25) this.history.shift();
  }

  resizeCanvas() {
    if (!this.image) return;

    const container = this.canvas.parentElement;
    const maxW = container.clientWidth;
    const maxH = container.clientHeight;

    const imgAspect = this.imageWidth / this.imageHeight;
    const contAspect = maxW / maxH;

    let displayW, displayH;
    if (imgAspect > contAspect) {
      displayW = maxW;
      displayH = maxW / imgAspect;
    } else {
      displayH = maxH;
      displayW = maxH * imgAspect;
    }

    // HiDPI backing store
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = displayW * dpr;
    this.canvas.height = displayH * dpr;
    this.canvas.style.width = `${displayW}px`;
    this.canvas.style.height = `${displayH}px`;

    this.ctx.scale(dpr, dpr);
    this.displayScale = displayW / this.imageWidth; // CSS px per image px

    this.render();
  }

  // Coordinate transforms
  imgToScreen(ix, iy) {
    return {
      x: ix * this.displayScale,
      y: iy * this.displayScale,
    };
  }

  screenToImg(sx, sy) {
    return {
      x: Math.max(0, Math.min(this.imageWidth, sx / this.displayScale)),
      y: Math.max(0, Math.min(this.imageHeight, sy / this.displayScale)),
    };
  }

  initEventListeners() {
    const c = this.canvas;

    c.addEventListener('pointerdown', (e) => this.handlePointerDown(e));
    window.addEventListener('pointermove', (e) => this.handlePointerMove(e));
    window.addEventListener('pointerup', (e) => this.handlePointerUp(e));
    window.addEventListener('pointercancel', (e) => this.handlePointerUp(e));
  }

  getPointerPos(e) {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      clientX: e.clientX,
      clientY: e.clientY,
    };
  }

  handlePointerDown(e) {
    if (!this.image || !this.points.length) return;
    this.canvas.setPointerCapture(e.pointerId);

    const pos = this.getPointerPos(e);
    this.dragStartMouse = pos;
    this.dragStartPoints = JSON.parse(JSON.stringify(this.points));

    // 1. Check if user clicked/touched a vertex point
    let nearestIdx = -1;
    let minDist = this.touchHitRadius;

    this.points.forEach(([ix, iy], idx) => {
      const sp = this.imgToScreen(ix, iy);
      const dist = Math.hypot(sp.x - pos.x, sp.y - pos.y);
      if (dist < minDist) {
        minDist = dist;
        nearestIdx = idx;
      }
    });

    if (nearestIdx !== -1) {
      this.dragMode = 'vertex';
      this.activePointIndex = nearestIdx;
      this.canvas.style.cursor = 'grabbing';
      
      // Trigger touch loupe
      if (this.loupe && (e.pointerType === 'touch' || e.pointerType === 'pen')) {
        const [px, py] = this.points[nearestIdx];
        this.loupe.show(pos.clientX, pos.clientY, this.image, px, py, this.displayScale);
      }
    } else {
      // 2. Check if user touched inside any polygon plane
      const imgPos = this.screenToImg(pos.x, pos.y);
      const insidePlane = this.isPointInPlanes(imgPos.x, imgPos.y);

      if (insidePlane) {
        this.dragMode = 'polygon';
        this.canvas.style.cursor = 'move';
      } else {
        this.dragMode = null;
      }
    }

    this.render();
  }

  handlePointerMove(e) {
    if (!this.image || !this.points.length) return;
    const pos = this.getPointerPos(e);

    if (this.dragMode === 'vertex' && this.activePointIndex !== -1) {
      const imgCoord = this.screenToImg(pos.x, pos.y);
      this.points[this.activePointIndex] = [imgCoord.x, imgCoord.y];

      if (this.loupe && (e.pointerType === 'touch' || e.pointerType === 'pen')) {
        this.loupe.show(pos.clientX, pos.clientY, this.image, imgCoord.x, imgCoord.y, this.displayScale);
      }

      this.render();
    } else if (this.dragMode === 'polygon') {
      const dxScreen = pos.x - this.dragStartMouse.x;
      const dyScreen = pos.y - this.dragStartMouse.y;
      const dxImg = dxScreen / this.displayScale;
      const dyImg = dyScreen / this.displayScale;

      // Translate all points simultaneously
      this.points = this.dragStartPoints.map(([origX, origY]) => {
        const nx = Math.max(0, Math.min(this.imageWidth, origX + dxImg));
        const ny = Math.max(0, Math.min(this.imageHeight, origY + dyImg));
        return [nx, ny];
      });

      this.render();
    } else {
      // Hover test for cursor
      let hovered = -1;
      this.points.forEach(([ix, iy], idx) => {
        const sp = this.imgToScreen(ix, iy);
        if (Math.hypot(sp.x - pos.x, sp.y - pos.y) < this.touchHitRadius) {
          hovered = idx;
        }
      });

      this.hoverPointIndex = hovered;
      if (hovered !== -1) {
        this.canvas.style.cursor = 'grab';
      } else {
        const imgPos = this.screenToImg(pos.x, pos.y);
        this.canvas.style.cursor = this.isPointInPlanes(imgPos.x, imgPos.y) ? 'move' : 'default';
      }
      this.render();
    }
  }

  handlePointerUp(e) {
    if (this.dragMode) {
      this.saveHistory();
      if (this.onPointsChanged) {
        this.onPointsChanged(this.points);
      }
    }
    this.dragMode = null;
    this.activePointIndex = -1;
    this.canvas.style.cursor = 'default';
    if (this.loupe) this.loupe.hide();
    this.render();
  }

  isPointInPlanes(x, y) {
    if (!this.preset || !this.preset.planes) return false;
    for (const plane of this.preset.planes) {
      const polygon = plane.point_indices.map(i => this.points[i]).filter(Boolean);
      if (this.isPointInPolygon([x, y], polygon)) {
        return true;
      }
    }
    return false;
  }

  isPointInPolygon(point, vs) {
    const x = point[0], y = point[1];
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
      const xi = vs[i][0], yi = vs[i][1];
      const xj = vs[j][0], yj = vs[j][1];
      const intersect = ((yi > y) !== (yj > y)) &&
        (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  render() {
    const ctx = this.ctx;
    if (!this.image) return;

    const displayW = this.canvas.width / (window.devicePixelRatio || 1);
    const displayH = this.canvas.height / (window.devicePixelRatio || 1);

    ctx.clearRect(0, 0, displayW, displayH);

    // 1. Draw original photo
    ctx.drawImage(this.image, 0, 0, displayW, displayH);

    if (!this.points.length || !this.preset) return;

    // 2. Draw planar quadrilateral fills with subtle gradient/glow
    if (this.preset.planes) {
      this.preset.planes.forEach((plane, pIdx) => {
        const polyPoints = plane.point_indices.map(i => this.imgToScreen(this.points[i][0], this.points[i][1]));
        if (polyPoints.length < 3) return;

        ctx.beginPath();
        ctx.moveTo(polyPoints[0].x, polyPoints[0].y);
        for (let i = 1; i < polyPoints.length; i++) {
          ctx.lineTo(polyPoints[i].x, polyPoints[i].y);
        }
        ctx.closePath();

        // Shaded surface fill
        const alpha = (this.dragMode === 'polygon') ? 0.35 : 0.22;
        ctx.fillStyle = `rgba(59, 130, 246, ${alpha})`;
        ctx.fill();
      });
    }

    // 3. Draw connecting wireframe lines
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = '#3b82f6';
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.setLineDash([]);

    if (this.preset.lines) {
      this.preset.lines.forEach(([startIdx, endIdx]) => {
        if (startIdx < this.points.length && endIdx < this.points.length) {
          const p1 = this.imgToScreen(this.points[startIdx][0], this.points[startIdx][1]);
          const p2 = this.imgToScreen(this.points[endIdx][0], this.points[endIdx][1]);

          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      });
    }

    // 4. Draw vertex handles
    this.points.forEach(([ix, iy], idx) => {
      const sp = this.imgToScreen(ix, iy);
      const isActive = idx === this.activePointIndex;
      const isHovered = idx === this.hoverPointIndex;

      // Outer glow / touch aura
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, this.pointVisualRadius + (isActive ? 6 : isHovered ? 4 : 2), 0, Math.PI * 2);
      ctx.fillStyle = isActive ? 'rgba(59, 130, 246, 0.45)' : 'rgba(15, 23, 42, 0.6)';
      ctx.fill();

      // Main handle circle
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, this.pointVisualRadius, 0, Math.PI * 2);
      ctx.fillStyle = isActive ? '#60a5fa' : '#ffffff';
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#2563eb';
      ctx.stroke();

      // Small center dot
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = '#1e3a8a';
      ctx.fill();
    });
  }

  getPoints() {
    return JSON.parse(JSON.stringify(this.points));
  }

  getImageBase64() {
    if (!this.image) return null;
    // Export high-res base64 from offscreen canvas
    const offCanvas = document.createElement('canvas');
    offCanvas.width = this.imageWidth;
    offCanvas.height = this.imageHeight;
    const offCtx = offCanvas.getContext('2d');
    offCtx.drawImage(this.image, 0, 0);
    return offCanvas.toDataURL('image/jpeg', 0.92);
  }
}
