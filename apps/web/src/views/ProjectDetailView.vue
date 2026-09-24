<template>
  <div class="project-detail-container" v-loading="loading">
    <div class="header-nav">
      <el-button :icon="ArrowLeft" @click="$router.push('/projects')">返回项目列表</el-button>
      <div v-if="project" class="header-actions">
        <el-button type="primary" :icon="Connection" @click="$router.push(`/graph?project=${project.key}`)">
          查看该项目拓扑图谱
        </el-button>
      </div>
    </div>

    <el-card v-if="project" shadow="hover" class="detail-card">
      <template #header>
        <div class="card-header">
          <div class="title-area">
            <span class="project-name">{{ project.name }}</span>
            <el-tag size="default" effect="dark">{{ project.key }}</el-tag>
            <el-tag :type="project.kind === 'frontend' ? 'warning' : 'success'">{{ project.kind }}</el-tag>
          </div>
          <el-tag :type="project.status === 'ACTIVE' ? 'success' : 'info'">{{ project.status }}</el-tag>
        </div>
      </template>

      <!-- Descriptions Section -->
      <el-descriptions title="基础项目元数据" :column="2" border>
        <el-descriptions-item label="Project ID">
          <code>{{ project.id }}</code>
        </el-descriptions-item>

        <el-descriptions-item label="架构角色 (Role)">
          <el-tag type="info" effect="plain">{{ project.role }}</el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="本地工作区路径 (只读)" :span="2">
          <code class="path-box">{{ project.local_path }}</code>
        </el-descriptions-item>

        <el-descriptions-item label="关联工程 (Related Projects)">
          <div v-if="project.related_projects && project.related_projects.length > 0">
            <el-tag
              v-for="rel in project.related_projects"
              :key="rel"
              type="primary"
              effect="plain"
              style="margin-right: 6px"
            >
              paired_with: {{ rel }}
            </el-tag>
          </div>
          <span v-else class="text-muted">当前独立，无强配对关系</span>
        </el-descriptions-item>

        <el-descriptions-item label="治理原则">
          <el-tag type="danger" effect="plain">严禁写操作 · 纯只读探测</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- Metrics counts -->
      <div class="metrics-block">
        <h4>拓扑与知识统计</h4>
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="stat-box">
              <div class="stat-number text-primary">{{ project.entity_count }}</div>
              <div class="stat-title">归属实体数 (Entity Count)</div>
              <div class="stat-sub">PROJECT / REPOSITORY / COMPONENT</div>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="stat-box">
              <div class="stat-number text-success">{{ project.relation_count }}</div>
              <div class="stat-title">拓扑关联数 (Relation Count)</div>
              <div class="stat-sub">包含边与跨工程配对边</div>
            </div>
          </el-col>
        </el-row>
      </div>

      <!-- JSON Metadata View -->
      <div class="meta-block">
        <h4>原始配置与扩展属性 (Metadata)</h4>
        <pre class="json-preview">{{ JSON.stringify(project.metadata, null, 2) }}</pre>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Connection } from '@element-plus/icons-vue'
import { api, type ProjectDetail } from '@/api/client'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(true)
const project = ref<ProjectDetail | null>(null)

onMounted(async () => {
  const id = route.params.id as string
  try {
    project.value = await api.getProject(id)
  } catch (err: any) {
    ElMessage.error(`加载项目详情失败: ${err.message}`)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.project-detail-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-name {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}

.path-box {
  color: #409eff;
  background-color: #ecf5ff;
  padding: 4px 8px;
  border-radius: 4px;
}

.metrics-block {
  margin-top: 24px;
}

.metrics-block h4,
.meta-block h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #606266;
}

.stat-box {
  background-color: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
}

.stat-title {
  margin-top: 4px;
  font-size: 13px;
  color: #303133;
}

.stat-sub {
  font-size: 11px;
  color: #909399;
}

.text-primary { color: #409eff; }
.text-success { color: #67c23a; }
.text-muted { color: #909399; }

.meta-block {
  margin-top: 24px;
}

.json-preview {
  background-color: #282c34;
  color: #abb2bf;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
}
</style>
