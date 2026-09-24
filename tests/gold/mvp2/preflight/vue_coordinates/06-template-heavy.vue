<template>
  <div class="dashboard-container">
    <header class="top-nav">
      <el-menu mode="horizontal">
        <el-menu-item index="1">Overview</el-menu-item>
        <el-menu-item index="2">Leads</el-menu-item>
      </el-menu>
    </header>
    <main class="content-body">
      <el-table :data="tableData" v-model="selected">
        <el-table-column prop="id" label="ID" />
        <el-table-column prop="name" label="Name" />
      </el-table>
      <el-pagination @current-change="handlePageChange" :total="100" />
    </main>
    <CallDetails :lead-id="currentLeadId" @call-ended="onCallEnded" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const currentLeadId = ref('123')
function handlePageChange(page: number) {
  console.log(page)
}
function onCallEnded() {
  console.log('Call ended')
}
</script>
