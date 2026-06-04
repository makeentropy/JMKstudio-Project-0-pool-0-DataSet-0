<template>
  <div class="control-panel">
    <h2>Control Panel</h2>
    
    <div class="section">
      <h3>Trigger Causal Event</h3>
      <input v-model="eventInput" placeholder="Event payload..." />
      <button @click="triggerEvent">Trigger</button>
    </div>
    
    <div class="section">
      <h3>Dimension Manager</h3>
      <input v-model="plainText" placeholder="Plain text DNA..." />
      <input v-model="sensitiveData" placeholder="Sensitive data (JSON)..." />
      <button @click="hideData">Hide Data</button>
    </div>
    
    <div class="section">
      <h3>Event Log</h3>
      <div class="log-container">
        <div v-for="(event, index) in allEvents" :key="index" class="log-entry">
          <span class="timestamp">T{{ event.timestamp }}</span>
          <span :class="event.space_branch === 'Parallel_A' ? 'branch-a' : 'branch-b'">
            {{ event.space_branch }}
          </span>
          <span class="karma">Karma: {{ event.karma.toFixed(2) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import DimensionVisualizer from './DimensionVisualizer.vue'
import { DimensionManager } from '../core/DimensionManager'

const visualizer = ref(null)
const eventInput = ref('')
const plainText = ref('ATCG-GENE-SEQUENCE')
const sensitiveData = ref('{"key": "value"}')
const dimManager = new DimensionManager()

const allEvents = computed(() => {
  if (!visualizer.value) return []
  const { karmaController } = visualizer.value
  return [...karmaController.parallelSpaces.Parallel_A, ...karmaController.parallelSpaces.Parallel_B]
    .sort((a, b) => a.timestamp - b.timestamp)
})

function triggerEvent() {
  if (!visualizer.value) return
  const payload = eventInput.value || { random: Math.random() }
  visualizer.value.karmaController.triggerCausalEvent(payload)
  eventInput.value = ''
}

function hideData() {
  try {
    const data = JSON.parse(sensitiveData.value)
    const cipher = dimManager.hideDataInPlainText(plainText.value, data)
    console.log('Hidden data cipher:', cipher)
    alert('Data hidden! Check console for cipher.')
  } catch (e) {
    alert('Invalid JSON for sensitive data')
  }
}
</script>

<style scoped>
.control-panel {
  margin-top: 20px;
  padding: 20px;
  background: rgba(0, 255, 255, 0.05);
  border: 1px solid #00ffff;
  border-radius: 8px;
}
.section {
  margin-bottom: 25px;
}
h3 {
  margin-bottom: 10px;
}
input {
  padding: 8px;
  margin-right: 10px;
  background: #0a0a0f;
  border: 1px solid #00ffff;
  color: #00ffff;
  border-radius: 4px;
}
button {
  padding: 8px 16px;
  background: #00ffff;
  color: #0a0a0f;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-family: 'Courier New', monospace;
  font-weight: bold;
}
button:hover {
  background: #00cccc;
}
.log-container {
  max-height: 200px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.3);
  padding: 10px;
  border-radius: 4px;
}
.log-entry {
  padding: 5px;
  margin: 5px 0;
  border-left: 3px solid #00ffff;
}
.timestamp {
  font-weight: bold;
  margin-right: 10px;
}
.branch-a {
  color: #00ff00;
  margin-right: 10px;
}
.branch-b {
  color: #ff9900;
  margin-right: 10px;
}
.karma {
  color: #ffff00;
}
</style>
