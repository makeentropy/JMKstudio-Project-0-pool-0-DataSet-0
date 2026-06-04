<template>
  <button
    :class="['neon-button', `variant-${variant}`, `size-${size}`]"
    @click="$emit('click', $event)"
  >
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
defineProps<{
  variant?: 'primary' | 'secondary' | 'accent';
  size?: 'sm' | 'md' | 'lg';
}>();

defineEmits<{
  click: [event: MouseEvent];
}>();
</script>

<style scoped>
.neon-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: 'Orbitron', monospace;
  font-weight: 700;
  letter-spacing: 0.05em;
  border: 2px solid;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.neon-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.1),
    transparent
  );
  transition: left 0.5s ease;
}

.neon-button:hover::before {
  left: 100%;
}

.size-sm {
  padding: 8px 16px;
  font-size: 0.75rem;
}

.size-md {
  padding: 12px 24px;
  font-size: 0.875rem;
}

.size-lg {
  padding: 16px 32px;
  font-size: 1rem;
}

.variant-primary {
  background: rgba(124, 58, 237, 0.1);
  border-color: rgba(124, 58, 237, 0.5);
  color: #a78bfa;
  box-shadow: 0 0 20px rgba(124, 58, 237, 0.2);
}

.variant-primary:hover {
  background: rgba(124, 58, 237, 0.2);
  border-color: rgba(124, 58, 237, 0.8);
  box-shadow: 0 0 40px rgba(124, 58, 237, 0.4);
  color: #c4b5fd;
}

.variant-secondary {
  background: rgba(6, 182, 212, 0.1);
  border-color: rgba(6, 182, 212, 0.5);
  color: #67e8f9;
  box-shadow: 0 0 20px rgba(6, 182, 212, 0.2);
}

.variant-secondary:hover {
  background: rgba(6, 182, 212, 0.2);
  border-color: rgba(6, 182, 212, 0.8);
  box-shadow: 0 0 40px rgba(6, 182, 212, 0.4);
  color: #a5f3fc;
}

.variant-accent {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.5);
  color: #fbbf24;
  box-shadow: 0 0 20px rgba(245, 158, 11, 0.2);
}

.variant-accent:hover {
  background: rgba(245, 158, 11, 0.2);
  border-color: rgba(245, 158, 11, 0.8);
  box-shadow: 0 0 40px rgba(245, 158, 11, 0.4);
  color: #fcd34d;
}
</style>
