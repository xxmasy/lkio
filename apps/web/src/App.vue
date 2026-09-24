<template>
  <el-container class="app-layout">
    <el-aside width="240px" class="app-sidebar">
      <div class="sidebar-brand">
        <el-icon class="brand-icon"><Share /></el-icon>
        <div class="brand-info">
          <div class="brand-title">LKIO</div>
          <div class="brand-subtitle">Knowledge Core v0.1</div>
        </div>
      </div>

      <el-menu
        :default-active="activeRoute"
        router
        class="sidebar-menu"
        background-color="#1e222d"
        text-color="#b0b7c3"
        active-text-color="#409eff"
      >
        <el-menu-item index="/overview">
          <el-icon><Odometer /></el-icon>
          <span>概览 (Overview)</span>
        </el-menu-item>

        <el-menu-item index="/projects">
          <el-icon><Folder /></el-icon>
          <span>纳管项目 (Projects)</span>
        </el-menu-item>

        <el-menu-item index="/graph">
          <el-icon><Connection /></el-icon>
          <span>知识拓扑 (Graph)</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <el-tag type="info" size="small" effect="plain">只读治理模式</el-tag>
        <div class="db-status">PostgreSQL 18 + pgvector</div>
      </div>
    </el-aside>

    <el-container class="app-body">
      <el-header height="60px" class="app-header">
        <div class="header-left">
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <el-tag type="success" size="small" effect="dark">MVP0 运行中</el-tag>
          <span class="mode-badge">Target: 3 Projects</span>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const activeRoute = computed(() => {
  if (route.path.startsWith('/projects')) {
    return '/projects'
  }
  return route.path
})

const currentTitle = computed(() => {
  return (route.meta.title as string) || 'LKIO'
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.app-sidebar {
  background-color: #1e222d;
  color: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand-icon {
  font-size: 26px;
  color: #409eff;
}

.brand-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #ffffff;
}

.brand-subtitle {
  font-size: 11px;
  color: #8c9ba5;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 12px;
  color: #8c9ba5;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.db-status {
  font-size: 11px;
  color: #67c23a;
}

.app-body {
  background-color: #f5f7fa;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e50;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-badge {
  font-size: 12px;
  color: #909399;
}

.app-main {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}
</style>
