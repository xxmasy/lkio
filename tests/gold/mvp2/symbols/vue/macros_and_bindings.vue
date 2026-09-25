<!-- Gold Fixture 4: Compiler Macros v1 & Template Structured Bindings -->
<template>
  <div class="form-container">
    <el-input v-model.trim="form.name" :disabled="form.status === 1" @change="handleChange(row)" />
    <LeadDetail :lead-id="selectedId" @close="handleClose" />
  </div>
</template>

<script setup lang="ts">
import { withDefaults, defineProps, defineEmits, defineExpose, defineModel, defineOptions, reactive, ref } from 'vue';

defineOptions({ name: 'MacrosAndBindings' });

interface Props {
  title: string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
});

const emit = defineEmits<{
  (e: 'submit', id: string): void;
}>();

const model = defineModel<string>('modelValue');

const selectedId = ref("1001");
const form = reactive({ name: '', status: 0 });

defineExpose({
  reset: () => {
    form.name = '';
  },
});

function handleChange(row: any) {
  form.status = 1;
}

function handleClose() {
  // handle close
}
</script>

<style scoped>
.form-container {
  margin: 20px;
}
</style>
