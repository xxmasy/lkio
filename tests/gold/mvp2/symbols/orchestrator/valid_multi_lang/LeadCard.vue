<template>
  <div class="lead-card">
    <h3>{{ leadName }}</h3>
    <button @click="handleClick">Select</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const leadName = ref("Prospect Alpha");

function handleClick() {
  console.log("clicked");
}
</script>
