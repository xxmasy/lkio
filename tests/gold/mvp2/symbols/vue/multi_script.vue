<!-- Gold Fixture 3: Dual script blocks (<script> + <script setup>) validating Criterion 5 block scope isolation -->
<template>
  <div class="multi-script-demo">
    <h1>MultiScript Component</h1>
    <p>{{ version }}</p>
  </div>
</template>

<script>
// Plain script block for module exports & static configuration
export const initConfig = { timeout: 3000 };

export function getVersion() {
  return "1.0.0";
}
</script>

<script setup lang="ts">
// Script setup block for component runtime instance logic
import { ref } from 'vue';

const initConfig = ref({ timeout: 5000 });
const version = ref("2.0.0");

function getVersion() {
  return version.value;
}
</script>
