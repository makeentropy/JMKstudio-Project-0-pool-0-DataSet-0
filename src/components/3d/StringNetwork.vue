<template>
  <div ref="container" class="string-network-container">
    <canvas ref="canvas" class="network-canvas"></canvas>
    <div class="network-overlay">
      <div class="overlay-item">
        <span class="overlay-label">Strings:</span>
        <span class="overlay-value">{{ nodeCount }}</span>
      </div>
      <div class="overlay-item">
        <span class="overlay-label">Connections:</span>
        <span class="overlay-value">{{ connectionCount }}</span>
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
const nodeCount = ref(0);
const connectionCount = ref(0);

let animationId: number | null = null;
let ctx: CanvasRenderingContext2D | null = null;
let nodes: Array<{ x: number; y: number; vx: number; vy: number; radius: number; color: string }> = [];
let time = 0;

function init() {
  if (!canvas.value || !container.value) return;
  ctx = canvas.value.getContext('2d');
  if (!ctx) return;

  resize();
  createNodes();
  animate();
}

function resize() {
  if (!canvas.value || !container.value) return;
  canvas.value.width = container.value.clientWidth;
  canvas.value.height = container.value.clientHeight;
}

function createNodes() {
  if (!canvas.value) return;
  nodes = [];
  const count = 20;
  for (let i = 0; i < count; i++) {
    nodes.push({
      x: Math.random() * canvas.value.width,
      y: Math.random() * canvas.value.height,
      vx: (Math.random() - 0.5) * 1,
      vy: (Math.random() - 0.5) * 1,
      radius: 4 + Math.random() * 6,
      color: `hsl(${260 + Math.random() * 60}, 70%, 60%)`
    });
  }
  nodeCount.value = count;
  connectionCount.value = count * 2;
}

function update() {
  if (!canvas.value) return;
  for (const node of nodes) {
    node.x += node.vx;
    node.y += node.vy;

    if (node.x < 0 || node.x > canvas.value.width) node.vx *= -1;
    if (node.y < 0 || node.y > canvas.value.height) node.vy *= -1;

    node.x = Math.max(0, Math.min(canvas.value.width, node.x));
    node.y = Math.max(0, Math.min(canvas.value.height, node.y));
  }
}

function draw() {
  if (!canvas.value || !ctx) return;
  ctx.fillStyle = 'rgba(15, 23, 42, 0.3)';
  ctx.fillRect(0, 0, canvas.value.width, canvas.value.height);

  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x;
      const dy = nodes[i].y - nodes[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 150) {
        const opacity = 1 - dist / 150;
        ctx.beginPath();
        ctx.strokeStyle = `rgba(124, 58, 237, ${opacity * 0.6})`;
        ctx.lineWidth = 1 + Math.sin(time * 0.02 + i) * 0.5;
        ctx.moveTo(nodes[i].x, nodes[i].y);
        ctx.lineTo(nodes[j].x, nodes[j].y);
        ctx.stroke();
      }
    }
  }

  for (const node of nodes) {
    const glow = ctx.createRadialGradient(
      node.x, node.y, 0,
      node.x, node.y, node.radius * 3
    );
    glow.addColorStop(0, node.color);
    glow.addColorStop(1, 'rgba(124, 58, 237, 0)');

    ctx.beginPath();
    ctx.fillStyle = glow;
    ctx.arc(node.x, node.y, node.radius * 3, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.fillStyle = node.color;
    ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
    ctx.fill();
  }

  time++;
}

function animate() {
  update();
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
.string-network-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
  overflow: hidden;
}

.network-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.network-overlay {
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
  border: 1px solid rgba(124, 58, 237, 0.3);
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
  color: #a78bfa;
}
</style>
