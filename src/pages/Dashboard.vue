<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div class="header-content">
        <h1 class="header-title">JMK-Dimension Studio</h1>
        <p class="header-subtitle">Multidimensional Causal & Quantum Topology Research System</p>
      </div>
      <div class="header-stats">
        <div class="stat-card">
          <div class="stat-label">Singularity Entropy</div>
          <div class="stat-value">{{ store.entropy.toFixed(4) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Causal Timeline</div>
          <div class="stat-value">{{ store.timeline }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">JMKmap_Pi</div>
          <div class="stat-value">{{ pi.toFixed(8) }}</div>
        </div>
      </div>
    </div>

    <div class="dashboard-main">
      <div class="main-grid">
        <div class="grid-cell grid-cell-full">
          <GlassCard title="String Network Visualization">
            <div class="viz-container">
              <StringNetwork />
            </div>
          </GlassCard>
        </div>

        <div class="grid-cell grid-cell-large">
          <GlassCard title="JMKmap Spiral Dimension">
            <div class="viz-container">
              <JMKmapSpiral />
            </div>
          </GlassCard>
        </div>

        <div class="grid-cell grid-cell-small">
          <GlassCard title="Causal Events">
            <div class="events-list">
              <div
                v-for="event in store.causalEvents.slice(0, 10)"
                :key="event.id"
                class="event-item"
              >
                <div class="event-header">
                  <span :class="['event-branch', event.spaceBranch.toLowerCase()]">
                    {{ event.spaceBranch }}
                  </span>
                  <span class="event-time">{{ formatTime(event.timestamp) }}</span>
                </div>
                <div class="event-karma">Karma: {{ event.karma.toFixed(4) }}</div>
                <div class="event-type">{{ event.payload.type }}</div>
              </div>
              <div v-if="store.causalEvents.length === 0" class="no-events">
                No events yet.
              </div>
            </div>
          </GlassCard>
        </div>

        <div class="grid-cell grid-cell-full">
          <GlassCard title="Entropy DNA Sequence">
            <div class="dna-display">
              <div class="dna-sequence">
                <span
                  v-for="(node, index) in store.entropyDNA"
                  :key="node.id"
                  :class="['dna-base', node.base.toLowerCase()]"
                  :title="`Entropy: ${node.entropy.toFixed(4)}`"
                >
                  {{ node.base }}
                </span>
              </div>
              <div class="dna-empty" v-if="store.entropyDNA.length === 0">
                No DNA nodes yet. Trigger events to generate.
              </div>
            </div>
          </GlassCard>
        </div>

        <div class="grid-cell grid-cell-full">
          <GlassCard title="Control Panel">
            <div class="control-panel">
              <NeonButton variant="primary" @click="triggerCreate">
                Trigger Create Event
              </NeonButton>
              <NeonButton variant="secondary" @click="triggerUpdate">
                Trigger Update Event
              </NeonButton>
              <NeonButton variant="accent" @click="triggerDelete">
                Trigger Delete Event
              </NeonButton>
              <NeonButton variant="primary" @click="store.toggleRunning">
                {{ store.isRunning ? 'Stop Auto-Run' : 'Start Auto-Run' }}
              </NeonButton>
              <NeonButton variant="secondary" @click="store.reset">
                Reset Singularity
              </NeonButton>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';
import GlassCard from '../components/ui/GlassCard.vue';
import NeonButton from '../components/ui/NeonButton.vue';
import StringNetwork from '../components/3d/StringNetwork.vue';
import JMKmapSpiral from '../components/3d/JMKmapSpiral.vue';
import { useJMKStore } from '../stores/jmkStore';

const store = useJMKStore();
const pi = Math.PI;
const interval = ref<number | null>(null);

function triggerCreate() {
  store.triggerEvent('create', { source: 'dashboard' });
}

function triggerUpdate() {
  store.triggerEvent('update', { source: 'dashboard' });
}

function triggerDelete() {
  store.triggerEvent('delete', { source: 'dashboard' });
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString();
}

onMounted(() => {
  if (store.isRunning) {
    startAutoRun();
  }
});

onUnmounted(() => {
  stopAutoRun();
});

function startAutoRun() {
  stopAutoRun();
  interval.value = window.setInterval(() => {
    const types = ['create', 'update', 'delete', 'query'];
    const type = types[Math.floor(Math.random() * types.length)];
    store.triggerEvent(type, { source: 'auto-run' });
  }, 2000);
}

function stopAutoRun() {
  if (interval.value !== null) {
    clearInterval(interval.value);
    interval.value = null;
  }
}

watch(() => store.isRunning, (running) => {
  if (running) {
    startAutoRun();
  } else {
    stopAutoRun();
  }
});
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #0a0f1a;
  color: #e2e8f0;
}

.dashboard-header {
  padding: 32px;
  background: linear-gradient(135deg, rgba(124, 58, 237, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%);
  border-bottom: 1px solid rgba(124, 58, 237, 0.2);
}

.header-content {
  max-width: 1600px;
  margin: 0 auto 24px;
  text-align: center;
}

.header-title {
  font-family: 'Orbitron', monospace;
  font-size: 3rem;
  font-weight: 900;
  background: linear-gradient(135deg, #7c3aed 0%, #06b6d4 50%, #f59e0b 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
  letter-spacing: 0.05em;
}

.header-subtitle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  color: #94a3b8;
}

.header-stats {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
}

.stat-card {
  padding: 16px 32px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(124, 58, 237, 0.2);
  border-radius: 12px;
  backdrop-filter: blur(10px);
  text-align: center;
  min-width: 200px;
}

.stat-label {
  font-family: 'Orbitron', monospace;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #64748b;
  margin-bottom: 4px;
}

.stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.5rem;
  font-weight: 700;
  color: #67e8f9;
}

.dashboard-main {
  padding: 32px;
  max-width: 1800px;
  margin: 0 auto;
}

.main-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.grid-cell-full {
  grid-column: span 3;
}

.grid-cell-large {
  grid-column: span 2;
}

.grid-cell-small {
  grid-column: span 1;
}

.viz-container {
  height: 400px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 12px;
  overflow: hidden;
}

.events-list {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.events-list::-webkit-scrollbar {
  width: 6px;
}

.events-list::-webkit-scrollbar-track {
  background: rgba(10, 15, 26, 0.5);
  border-radius: 3px;
}

.events-list::-webkit-scrollbar-thumb {
  background: rgba(124, 58, 237, 0.5);
  border-radius: 3px;
}

.event-item {
  padding: 16px;
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(124, 58, 237, 0.2);
  border-radius: 12px;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.event-branch {
  padding: 4px 12px;
  border-radius: 8px;
  font-family: 'Orbitron', monospace;
  font-size: 0.75rem;
  font-weight: 700;
}

.event-branch.parallel_a {
  background: rgba(124, 58, 237, 0.2);
  color: #a78bfa;
}

.event-branch.parallel_b {
  background: rgba(6, 182, 212, 0.2);
  color: #67e8f9;
}

.event-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #64748b;
}

.event-karma {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  color: #22c55e;
  margin-bottom: 4px;
}

.event-type {
  font-family: 'Orbitron', monospace;
  font-size: 0.875rem;
  color: #e2e8f0;
}

.no-events {
  text-align: center;
  color: #64748b;
  padding: 40px;
  font-family: 'JetBrains Mono', monospace;
}

.dna-display {
  padding: 24px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 12px;
}

.dna-sequence {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.dna-base {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.125rem;
  font-weight: 700;
  border: 2px solid;
}

.dna-base.a {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.1);
}

.dna-base.t {
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.5);
  background: rgba(245, 158, 11, 0.1);
}

.dna-base.c {
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.5);
  background: rgba(34, 197, 94, 0.1);
}

.dna-base.g {
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(59, 130, 246, 0.1);
}

.dna-empty {
  text-align: center;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

.control-panel {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  justify-content: center;
}

@media (max-width: 1200px) {
  .main-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .grid-cell-full {
    grid-column: span 2;
  }

  .grid-cell-large {
    grid-column: span 2;
  }

  .grid-cell-small {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .main-grid {
    grid-template-columns: 1fr;
  }

  .grid-cell-full,
  .grid-cell-large,
  .grid-cell-small {
    grid-column: span 1;
  }

  .header-title {
    font-size: 2rem;
  }
}
</style>
