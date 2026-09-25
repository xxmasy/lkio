<!-- Gold Fixture: Vue 3 SFC with script setup, Hook, variables, and methods -->
<template>
  <div class="lead-view">
    <h1>{{ title }}</h1>
    <button @click="handleRefresh">Refresh</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const title = ref("Lead View");
const loading = ref(false);

export function useLeadViewHook() {
  return { active: true };
}

function handleRefresh() {
  loading.value = true;
}
</script>

<style scoped>
.lead-view {
  padding: 16px;
}
</style>
