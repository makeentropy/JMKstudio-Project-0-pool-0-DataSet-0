<template>
  <div ref="container" class="spiral-container">
    <canvas ref="canvas" class="spiral-canvas"></canvas>
    <div class="spiral-overlay">
      <div class="overlay-item">
        <span class="overlay-label">π:</span>
        <span class="overlay-value">{{ pi.toFixed(6) }}</span>
      </div>
      <div class="overlay-item">
        <span class="overlay-label">Entropy:</span>
        <span class="overlay-value">{{ store.entropy.toFixed(4) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useJMKStore } from '../../stores/jmkStore';

const store = useJMKStore();
const container = ref<HTMLDivElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);
const pi = Math.PI;

let animationId: number | null = null;
let ctx: CanvasRenderingContext2D | null = null;
let time = 0;

function init() {
  if (!canvas.value || !container.value) return;
  ctx = canvas.value.getContext('2d');
  if (!ctx) return;

  resize();
  animate();
}

function resize() {
  if (!canvas.value || !container.value) return;
  canvas.value.width = container.value.clientWidth;
  canvas.value.height = container.value.clientHeight;
}

function draw() {
  if (!canvas.value || !ctx) return;
  const width = canvas.value.width;
  const height = canvas.value.height;
  const centerX = width / 2;
  const centerY = height / 2;

  ctx.fillStyle = 'rgba(15, 23, 42, 0.3)';
  ctx.fillRect(0, 0, width, height);

  const numPoints = 64;
  const scale = Math.min(width, height) * 0.35;
  const entropy = store.entropy;

  for (let i = 0; i < numPoints; i++) {
    const t = i / numPoints;
    const angle = t * 8 * Math.PI + time * 0.01;
    const radius = t * scale;

    const jitterX = Math.sin(t * 20 + time * 0.05) * entropy * 10;
    const jitterY = Math.cos(t * 20 + time * 0.05) * entropy * 10;

    const x = centerX + Math.cos(angle) * radius + jitterX;
    const y = centerY + Math.sin(angle) * radius + jitterY;

    const hue = 260 + t * 60 + entropy * 40;
    const color = `hsl(${hue}, 70%, 60%)`;

    if (i > 0) {
      const prevT = (i - 1) / numPoints;
      const prevAngle = prevT * 8 * Math.PI + time * 0.01;
      const prevRadius = prevT * scale;
      const prevX = centerX + Math.cos(prevAngle) * prevRadius + Math.sin(prevT * 20 + time * 0.05) * entropy * 10;
      const prevY = centerY + Math.sin(prevAngle) * prevRadius + Math.cos(prevT * 20 + time * 0.05) * entropy * 10;

      ctx.beginPath();
      ctx.strokeStyle = `hsla(${hue}, 70%, 60%, 0.6)`;
      ctx.lineWidth = 2;
      ctx.moveTo(prevX, prevY);
      ctx.lineTo(x, y);
      ctx.stroke();
    }

    const glow = ctx.createRadialGradient(x, y, 0, x, y, 20);
    glow.addColorStop(0, color);
    glow.addColorStop(1, 'rgba(124, 58, 237, 0)');

    ctx.beginPath();
    ctx.fillStyle = glow;
    ctx.arc(x, y, 20, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(x, y, 6, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.beginPath();
  ctx.strokeStyle = 'rgba(124, 58, 237, 0.2)';
  ctx.lineWidth = 2;
  ctx.arc(centerX, centerY, scale, 0, Math.PI * 2);
  ctx.stroke();

  ctx.beginPath();
  ctx.fillStyle = '#a78bfa';
  ctx.arc(centerX, centerY, 8, 0, Math.PI * 2);
  ctx.fill();

  time++;
}

function animate() {
  draw();
  animationId = requestAnimationFrame(animate);
}

onMounted(() => {
  init();
  window.addEventListener('resize', resize);
});

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId);
  }
  window.removeEventListener('resize', resize);
});
</script>

<style scoped>
.spiral-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  overflow: hidden;
}

.spiral-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.spiral-overlay {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.overlay-item {
  background: rgba(15, 23, 42, 0.8);
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(6, 182, 212, 0.3);
  display: flex;
  gap: 8px;
  align-items: center;
}

.overlay-label {
  font-family: 'Orbitron', monospace;
  font-size: 0.75rem;
  color: #94a3b8;
}

.overlay-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  font-weight: 700;
  color: #67e8f9;
}
</style>
