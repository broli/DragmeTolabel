/**
 * Touch Magnifier Loupe
 * Renders a 2.5x zoomed preview above the user's touch point for precision polygon editing on mobile & iPad.
 */

export class TouchLoupe {
  constructor(containerEl, loupeCanvasEl) {
    this.container = containerEl;
    this.canvas = loupeCanvasEl;
    this.ctx = this.canvas.getContext('2d');
    this.zoomFactor = 2.5;
    this.sampleRadius = 35; // Region sampled from source image
  }

  show(clientX, clientY, sourceImg, ptPixelX, ptPixelY, canvasScale) {
    if (!this.container || !sourceImg) return;

    // Position loupe offset 80px above touch point
    const offsetTop = 80;
    let posX = clientX;
    let posY = clientY - offsetTop;

    // If too close to the top of screen, flip below touch point
    if (posY < 90) {
      posY = clientY + 80;
    }

    this.container.style.display = 'block';
    this.container.style.left = `${posX}px`;
    this.container.style.top = `${posY}px`;

    // Render zoomed patch
    const size = this.canvas.width;
    this.ctx.clearRect(0, 0, size, size);

    // Save and clip to circle
    this.ctx.save();
    this.ctx.beginPath();
    this.ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    this.ctx.clip();

    // Fill background
    this.ctx.fillStyle = '#0f172a';
    this.ctx.fillRect(0, 0, size, size);

    // Draw zoomed source image
    const sx = ptPixelX - this.sampleRadius;
    const sy = ptPixelY - this.sampleRadius;
    const sWidth = this.sampleRadius * 2;
    const sHeight = this.sampleRadius * 2;

    this.ctx.drawImage(
      sourceImg,
      sx, sy, sWidth, sHeight,
      0, 0, size, size
    );

    this.ctx.restore();
  }

  hide() {
    if (this.container) {
      this.container.style.display = 'none';
    }
  }
}
