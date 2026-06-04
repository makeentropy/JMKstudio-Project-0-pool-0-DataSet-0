<template>
  <div id="jmk-studio">
    <h1>JMK-Dimension Studio</h1>
    <DimensionVisualizer />
    <ControlPanel />
  </div>
</template>

<script setup>
import DimensionVisualizer from './components/DimensionVisualizer.vue'
import ControlPanel from './components/ControlPanel.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Courier New', monospace;
  background: #0a0a0f;
  color: #00ffff;
  min-height: 100vh;
}
#jmk-studio {
  padding: 20px;
}
h1 {
  margin-bottom: 20px;
  text-shadow: 0 0 10px #00ffff;
}
</style>
