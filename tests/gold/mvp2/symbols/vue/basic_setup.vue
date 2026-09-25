<!-- Gold Fixture 1: Basic Vue 3 SFC with script setup (TypeScript), Hook, and Template Facts -->
<template>
  <div class="lead-view">
    <h1>{{ title }}</h1>
    <ElButton type="primary" @click="handleRefresh" :loading="loading">
      Refresh
    </ElButton>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const title = ref("Lead View");
const loading = ref(false);

export function useLeadState() {
  return { loading };
}

function handleRefresh() {
  loading.value = true;
}
</script>

<style scoped lang="scss">
.lead-view {
  padding: 16px;
}
</style>
