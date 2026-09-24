<template>
  <div>Multi Block</div>
</template>

<script>
export default {
  name: 'MultiBlockComponent',
  inheritAttrs: false
}
</script>

<script setup lang="ts">
import { ref } from 'vue'

const active = ref(true)
function toggle() {
  active.value = !active.value
}
</script>
