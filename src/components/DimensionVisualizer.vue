<template>
  <div class="visualizer-container">
    <div ref="canvasContainer" class="canvas-container"></div>
    <div class="info-panel">
      <h3>JMKmap π: {{ singularity.JMKmap_Pi.toFixed(6) }}</h3>
      <p>Timeline: {{ karmaController.timeline }}</p>
      <p>Parallel A Events: {{ karmaController.parallelSpaces.Parallel_A.length }}</p>
      <p>Parallel B Events: {{ karmaController.parallelSpaces.Parallel_B.length }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { QuantumSingularity } from '../core/QuantumSingularity'
import { KarmaRhythmController } from '../core/KarmaRhythmController'

const canvasContainer = ref(null)
const singularity = new QuantumSingularity()
const karmaController = new KarmaRhythmController()

let scene, camera, renderer, particles
let animationId

onMounted(() => {
  initThree()
  animate()
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
})

function initThree() {
  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0a0f)
  
  camera = new THREE.PerspectiveCamera(75, canvasContainer.value.clientWidth / canvasContainer.value.clientHeight, 0.1, 1000)
  camera.position.z = 50
  
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(canvasContainer.value.clientWidth, canvasContainer.value.clientHeight)
  canvasContainer.value.appendChild(renderer.domElement)
  
  createParticleSystem()
  
  window.addEventListener('resize', onWindowResize)
}

function createParticleSystem() {
  const geometry = new THREE.BufferGeometry()
  const count = 5000
  const positions = new Float32Array(count * 3)
  const colors = new Float32Array(count * 3)
  
  for (let i = 0; i < count; i++) {
    const t = i / count
    const radius = 20 * (1 + 0.5 * Math.sin(t * 20))
    positions[i * 3] = radius * Math.cos(t * 40) * Math.sin(t * 10)
    positions[i * 3 + 1] = t * 40 - 20
    positions[i * 3 + 2] = radius * Math.sin(t * 40) * Math.cos(t * 10)
    
    const entropy = t
    colors[i * 3] = entropy
    colors[i * 3 + 1] = 0.2
    colors[i * 3 + 2] = 1 - entropy
  }
  
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  
  const material = new THREE.PointsMaterial({ size: 0.5, vertexColors: true })
  particles = new THREE.Points(geometry, material)
  scene.add(particles)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  
  if (particles) {
    particles.rotation.y += 0.005
    particles.rotation.x += 0.002
  }
  
  renderer.render(scene, camera)
}

function onWindowResize() {
  camera.aspect = canvasContainer.value.clientWidth / canvasContainer.value.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(canvasContainer.value.clientWidth, canvasContainer.value.clientHeight)
}

defineExpose({
  singularity,
  karmaController
})
</script>

<style scoped>
.visualizer-container {
  display: flex;
  gap: 20px;
}
.canvas-container {
  width: 800px;
  height: 500px;
  border: 1px solid #00ffff;
  border-radius: 8px;
}
.info-panel {
  padding: 20px;
  background: rgba(0, 255, 255, 0.1);
  border: 1px solid #00ffff;
  border-radius: 8px;
  min-width: 250px;
}
.info-panel h3 {
  margin-bottom: 15px;
}
.info-panel p {
  margin: 8px 0;
}
</style>
