<template>
  <div class="projects-container" v-loading="loading">
    <el-card shadow="hover" class="main-card">
      <template #header>
        <div class="card-header">
          <div>
            <span class="title">第一批纳管项目 (Projects)</span>
            <span class="subtitle">受控项目列表，采用统一 Identity Key 与只读探测机制</span>
          </div>
          <el-tag type="info">共 {{ projects.length }} 个项目</el-tag>
        </div>
      </template>

      <el-table :data="projects" border stripe style="width: 100%">
        <el-table-column prop="key" label="Project Key" width="160">
          <template #default="{ row }">
            <el-tag size="default" effect="dark">{{ row.key }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="工程名称" width="180">
          <template #default="{ row }">
            <strong>{{ row.name }}</strong>
          </template>
        </el-table-column>

        <el-table-column prop="kind" label="工程类型" width="130">
          <template #default="{ row }">
            <el-tag :type="row.kind === 'frontend' ? 'warning' : 'success'" size="small">
              {{ row.kind }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="role" label="架构角色" width="180">
          <template #default="{ row }">
            <code>{{ row.role }}</code>
          </template>
        </el-table-column>

        <el-table-column prop="local_path" label="本地只读工作区路径" min-width="260">
          <template #default="{ row }">
            <span class="path-text">{{ row.local_path }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              plain
              @click="$router.push(`/projects/${row.id}`)"
            >
              详情
            </el-button>
            <el-button
              type="success"
              size="small"
              plain
              @click="$router.push(`/graph?project=${row.key}`)"
            >
              拓扑图谱
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type ProjectItem } from '@/api/client'
import { ElMessage } from 'element-plus'

const loading = ref(true)
const projects = ref<ProjectItem[]>([])

onMounted(async () => {
  try {
    projects.value = await api.getProjects()
  } catch (err: any) {
    ElMessage.error(`获取项目列表失败: ${err.message}`)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.projects-container {
  display: flex;
  flex-direction: column;
}

.main-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.subtitle {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.path-text {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: #409eff;
}
</style>
