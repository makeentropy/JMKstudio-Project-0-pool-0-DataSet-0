<template>
  <div class="dna-config-page">
    <div class="page-header">
      <h1 class="page-title">DNA Config Editor</h1>
      <p class="page-subtitle">Edit and manage causal system DNA sequence</p>
    </div>

    <div class="page-content">
      <div class="content-grid">
        <GlassCard title="DNA Sequence Editor" class="grid-item-main">
          <DNASequenceEditor />
        </GlassCard>

        <GlassCard title="Current DNA Info" class="grid-item-side">
          <div class="dna-info">
            <div class="info-item">
              <span class="info-label">Sequence Length</span>
              <span class="info-value">{{ store.dnaSequence.length }} bp</span>
            </div>
            <div class="info-item">
              <span class="info-label">Current Sequence</span>
              <span class="info-value sequence">{{ store.dnaSequence }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Causal Rhythm</span>
              <span class="info-value">{{ calculateRhythm() }}</span>
            </div>
          </div>
        </GlassCard>

        <GlassCard title="Preset Sequences" class="grid-item-side">
          <div class="presets">
            <NeonButton
              v-for="preset in presets"
              :key="preset.name"
              variant="secondary"
              size="sm"
              @click="applyPreset(preset.sequence)"
              class="preset-btn"
            >
              {{ preset.name }}
            </NeonButton>
          </div>
        </GlassCard>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import GlassCard from '../components/ui/GlassCard.vue';
import NeonButton from '../components/ui/NeonButton.vue';
import DNASequenceEditor from '../components/dna/DNASequenceEditor.vue';
import { useJMKStore } from '../stores/jmkStore';

const store = useJMKStore();

const presets = [
  { name: 'Chaos Mode', sequence: 'ATCGATCGATCGATCGATCG' },
  { name: 'Order Mode', sequence: 'AAAATTTTCCCCGGGG' },
  { name: 'Balance Mode', sequence: 'ATCGATCGATCGATCG' },
  { name: 'Quantum Mode', sequence: 'AGTCAGTCAGTCAGTC' }
];

function calculateRhythm() {
  const seq = store.dnaSequence;
  const a = (seq.match(/A/g) || []).length;
  const t = (seq.match(/T/g) || []).length;
  const c = (seq.match(/C/g) || []).length;
  const g = (seq.match(/G/g) || []).length;
  const total = a + t + c + g || 1;
  const entropy = 1 - ((a/total)**2 + (t/total)**2 + (c/total)**2 + (g/total)**2);
  return entropy.toFixed(3);
}

function applyPreset(sequence: string) {
  store.updateDNASequence(sequence);
}
</script>

<style scoped>
.dna-config-page {
  min-height: 100vh;
  background: #0a0f1a;
  color: #e2e8f0;
}

.page-header {
  padding: 40px;
  max-width: 1600px;
  margin: 0 auto;
  text-align: center;
}

.page-title {
  font-family: 'Orbitron', monospace;
  font-size: 2.5rem;
  font-weight: 900;
  background: linear-gradient(135deg, #7c3aed 0%, #06b6d4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
  letter-spacing: 0.1em;
}

.page-subtitle {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1rem;
  color: #94a3b8;
}

.page-content {
  padding: 0 40px 40px;
  max-width: 1600px;
  margin: 0 auto;
}

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}

.grid-item-main {
  grid-row: span 2;
}

.grid-item-side {
  grid-column: span 1;
}

.dna-info {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-label {
  font-family: 'Orbitron', monospace;
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.info-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.25rem;
  font-weight: 700;
  color: #67e8f9;
}

.info-value.sequence {
  font-size: 0.875rem;
  word-break: break-all;
  color: #a78bfa;
}

.presets {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preset-btn {
  width: 100%;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .grid-item-main {
    grid-row: span 1;
  }
}
</style>
