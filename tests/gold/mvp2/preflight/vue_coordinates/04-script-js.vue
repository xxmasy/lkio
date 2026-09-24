<template>
  <span>{{ message }}</span>
</template>

<script lang="js">
export default {
  name: 'SimpleMessage',
  computed: {
    message() {
      return 'Hello LKIO'
    }
  }
}
</script>
