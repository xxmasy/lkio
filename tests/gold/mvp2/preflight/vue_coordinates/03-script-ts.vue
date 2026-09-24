<template>
  <div>{{ title }}</div>
</template>

<script lang="ts">
import { defineComponent } from 'vue'

interface Props {
  title: string
}

export default defineComponent({
  name: 'HeaderWidget',
  props: {
    title: { type: String, required: true }
  },
  setup(props: Props) {
    function getTitleLength(): number {
      return props.title.length
    }
    return { getTitleLength }
  }
})
</script>
