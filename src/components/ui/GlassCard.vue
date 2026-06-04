<template>
  <div class="glass-card" :class="{ 'has-title': title }">
    <div v-if="title" class="card-header">
      <span class="card-title">{{ title }}</span>
      <div class="card-decoration">
        <div class="decoration-dot"></div>
        <div class="decoration-dot"></div>
        <div class="decoration-dot"></div>
      </div>
    </div>
    <div class="card-content">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
}>();
</script>

<style scoped>
.glass-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(124, 58, 237, 0.2);
  border-radius: 16px;
  backdrop-filter: blur(10px);
  overflow: hidden;
  transition: all 0.3s ease;
}

.glass-card:hover {
  border-color: rgba(124, 58, 237, 0.4);
  box-shadow: 0 0 40px rgba(124, 58, 237, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(15, 23, 42, 0.5);
  border-bottom: 1px solid rgba(124, 58, 237, 0.15);
}

.card-title {
  font-family: 'Orbitron', monospace;
  font-size: 1rem;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: 0.05em;
}

.card-decoration {
  display: flex;
  gap: 6px;
}

.decoration-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(124, 58, 237, 0.5);
}

.card-content {
  padding: 20px;
}
</style>
