<!-- Gold Fixture 2: Vue Options API in plain script -->
<template>
  <div class="counter-box">
    <span>{{ count }}</span>
    <button @click="increment">+</button>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'UserOptions',
  data() {
    return {
      count: 0
    };
  },
  computed: {
    doubleCount() {
      return this.count * 2;
    }
  },
  methods: {
    increment() {
      this.count++;
    }
  }
});
</script>

<style>
.counter-box span {
  font-weight: bold;
}
</style>
