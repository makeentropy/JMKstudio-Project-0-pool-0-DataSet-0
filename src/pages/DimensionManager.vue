<template>
  <div class="dimension-manager-page">
    <div class="page-header">
      <h1 class="page-title">Dimension Manager</h1>
      <p class="page-subtitle">Manage spatial password and hidden data layer</p>
    </div>

    <div class="page-content">
      <div class="content-grid">
        <GlassCard title="Spatial Password" class="grid-item-full">
          <div class="password-section">
            <div class="input-group">
              <label class="input-label">Spatial Password</label>
              <input
                v-model="passwordInput"
                type="text"
                class="password-input"
                placeholder="Enter spatial password"
              />
            </div>
            <NeonButton variant="primary" @click="updatePassword">
              Update Password
            </NeonButton>
          </div>
        </GlassCard>

        <GlassCard title="Hide Data" class="grid-item-main">
          <div class="hide-data-section">
            <div class="input-group">
              <label class="input-label">Plaintext DNA Sequence</label>
              <input
                v-model="plainTextDNA"
                type="text"
                class="dna-input"
                placeholder="Enter ATCG sequence"
              />
            </div>
            <div class="input-group">
              <label class="input-label">Data to Hide</label>
              <textarea
                v-model="sensitiveData"
                class="data-textarea"
                placeholder="Enter data to hide"
                rows="4"
              />
            </div>
            <NeonButton variant="primary" @click="hideData">
              Hide Data in DNA
            </NeonButton>
          </div>
        </GlassCard>

        <GlassCard title="Hidden Data List" class="grid-item-side">
          <div class="hidden-data-list">
            <div
              v-for="(item, index) in hiddenDataItems"
              :key="index"
              class="data-item"
            >
              <div class="item-header">
                <span class="item-cipher">{{ item.cipher }}</span>
                <NeonButton variant="secondary" size="sm" @click="retrieveItem(item)">
                  Retrieve
                </NeonButton>
              </div>
              <div class="item-time">{{ formatTime(item.timestamp) }}</div>
            </div>
            <div v-if="hiddenDataItems.length === 0" class="no-data">
              No hidden data yet
            </div>
          </div>
        </GlassCard>

        <GlassCard title="Retrieved Data" class="grid-item-full" v-if="retrievedData">
          <div class="retrieved-section">
            <pre class="retrieved-data">{{ JSON.stringify(retrievedData, null, 2) }}</pre>
          </div>
        </GlassCard>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import GlassCard from '../components/ui/GlassCard.vue';
import NeonButton from '../components/ui/NeonButton.vue';
import { useJMKStore } from '../stores/jmkStore';

const store = useJMKStore();
const passwordInput = ref(store.spatialPassword);
const plainTextDNA = ref('ATCGATCGATCG');
const sensitiveData = ref('');
const retrievedData = ref<any>(null);
const hiddenDataItems = ref<Array<{ cipher: string; timestamp: number }>>([]);

function updatePassword() {
  store.updateSpatialPassword(passwordInput.value);
}

function hideData() {
  if (!plainTextDNA.value || !sensitiveData.value) return;
  try {
    const data = {
      content: sensitiveData.value,
      hiddenAt: Date.now()
    };
    const cipher = store.hideData(plainTextDNA.value, data);
    hiddenDataItems.value.push({
      cipher,
      timestamp: Date.now()
    });
    sensitiveData.value = '';
  } catch (error) {
    console.error('Failed to hide data:', error);
  }
}

function retrieveItem(item: { cipher: string; timestamp: number }) {
  try {
    const data = store.retrieveData(item.cipher);
    retrievedData.value = data;
  } catch (error) {
    alert('Spatial password mismatch or data not found');
  }
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleString();
}
</script>

<style scoped>
.dimension-manager-page {
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
  background: linear-gradient(135deg, #f59e0b 0%, #7c3aed 100%);
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

.grid-item-full {
  grid-column: span 2;
}

.grid-item-main {
  grid-column: span 1;
}

.grid-item-side {
  grid-column: span 1;
}

.password-section {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.input-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-label {
  font-family: 'Orbitron', monospace;
  font-size: 0.875rem;
  color: #94a3b8;
  letter-spacing: 0.05em;
}

.password-input,
.dna-input,
.data-textarea {
  width: 100%;
  padding: 12px 16px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  background: rgba(10, 15, 26, 0.8);
  border: 2px solid rgba(124, 58, 237, 0.3);
  border-radius: 10px;
  color: #67e8f9;
  outline: none;
  transition: all 0.3s ease;
}

.password-input:focus,
.dna-input:focus,
.data-textarea:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 20px rgba(124, 58, 237, 0.2);
}

.data-textarea {
  resize: vertical;
}

.hide-data-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hidden-data-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.hidden-data-list::-webkit-scrollbar {
  width: 6px;
}

.hidden-data-list::-webkit-scrollbar-track {
  background: rgba(10, 15, 26, 0.5);
  border-radius: 3px;
}

.hidden-data-list::-webkit-scrollbar-thumb {
  background: rgba(124, 58, 237, 0.5);
  border-radius: 3px;
}

.data-item {
  padding: 16px;
  background: rgba(10, 15, 26, 0.6);
  border: 1px solid rgba(124, 58, 237, 0.2);
  border-radius: 10px;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.item-cipher {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #a78bfa;
  word-break: break-all;
  flex: 1;
}

.item-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: #64748b;
}

.no-data {
  text-align: center;
  color: #64748b;
  padding: 40px;
  font-family: 'JetBrains Mono', monospace;
}

.retrieved-section {
  background: rgba(10, 15, 26, 0.6);
  padding: 20px;
  border-radius: 10px;
  border: 1px solid rgba(124, 58, 237, 0.2);
}

.retrieved-data {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.875rem;
  color: #67e8f9;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .grid-item-full {
    grid-column: span 1;
  }

  .password-section {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
