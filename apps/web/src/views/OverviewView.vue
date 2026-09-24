<template>
  <div class="overview-container" v-loading="loading">
    <div class="welcome-banner">
      <div class="banner-content">
        <h2>LKIO 本地知识智能操作系统 · MVP0 控制台</h2>
        <p>
          知识核心第一阶段已就绪。当前以完全只读模式纳管 3 个本地核心项目，构建代码拓扑、层级结构与跨项目关联。
        </p>
      </div>
      <div class="banner-actions">
        <el-button type="primary" :icon="Connection" @click="$router.push('/graph')">
          查看知识图谱
        </el-button>
        <el-button :icon="Folder" @click="$router.push('/projects')">
          管理纳管项目
        </el-button>
      </div>
    </div>

    <!-- Metric Cards -->
    <el-row :gutter="16" class="metrics-row">
      <el-col :span="4">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">纳管项目 (Projects)</div>
          <div class="metric-value text-primary">{{ metrics.project_count }}</div>
          <div class="metric-desc">P0: 2, P1: 1</div>
        </el-card>
      </el-col>

      <el-col :span="4">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">前端工程 (Frontend)</div>
          <div class="metric-value text-warning">{{ metrics.frontend_count }}</div>
          <div class="metric-desc">HELLO_FE / L2C_FE</div>
        </el-card>
      </el-col>

      <el-col :span="4">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">后端工程 (Backend)</div>
          <div class="metric-value text-success">{{ metrics.backend_count }}</div>
          <div class="metric-desc">HELLO_BE 配套后端</div>
        </el-card>
      </el-col>

      <el-col :span="4">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">核心实体 (Entities)</div>
          <div class="metric-value text-info">{{ metrics.entity_count }}</div>
          <div class="metric-desc">分层架构节点</div>
        </el-card>
      </el-col>

      <el-col :span="4">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">拓扑关系 (Relations)</div>
          <div class="metric-value text-purple">{{ metrics.relation_count }}</div>
          <div class="metric-desc">包含关系与配对边</div>
        </el-card>
      </el-col>

      <el-col :span="4">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">物理数据源 (Sources)</div>
          <div class="metric-value text-muted">{{ metrics.source_count }}</div>
          <div class="metric-desc">Git 仓库 (只读)</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Sub sections: Governance & Project List -->
    <el-row :gutter="16" class="content-row">
      <el-col :span="16">
        <el-card shadow="hover" class="box-card">
          <template #header>
            <div class="card-header">
              <span>当前纳管项目列表</span>
              <el-button link type="primary" @click="$router.push('/projects')">查看全部</el-button>
            </div>
          </template>

          <el-table :data="projects" stripe style="width: 100%">
            <el-table-column prop="key" label="Project Key" width="140">
              <template #default="{ row }">
                <el-tag size="small" effect="dark">{{ row.key }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="项目名称" width="150" />
            <el-table-column prop="kind" label="类型" width="110">
              <template #default="{ row }">
                <el-tag :type="row.kind === 'frontend' ? 'warning' : 'success'" size="small">
                  {{ row.kind }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="role" label="架构角色" width="160">
              <template #default="{ row }">
                <code>{{ row.role }}</code>
              </template>
            </el-table-column>
            <el-table-column prop="local_path" label="本地路径" min-width="200" show-overflow-tooltip />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="$router.push(`/projects/${row.id}`)">
                  详情
                </el-button>
                <el-button link type="primary" size="small" @click="$router.push(`/graph?project=${row.key}`)">
                  拓扑
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover" class="box-card">
          <template #header>
            <div class="card-header">
              <span>架构基线状态与治理宪法</span>
            </div>
          </template>

          <div class="governance-list">
            <div class="gov-item">
              <el-icon class="icon-pass"><CircleCheckFilled /></el-icon>
              <div>
                <strong>源项目只读原则</strong>
                <p>LKIO 严格以只读模式探测，严禁向工作区写入任何代码或配置。</p>
              </div>
            </div>

            <div class="gov-item">
              <el-icon class="icon-pass"><CircleCheckFilled /></el-icon>
              <div>
                <strong>统一数据底座</strong>
                <p>PostgreSQL 18.6 + pgvector 0.8.6 原生托管关系模型与向量存储。</p>
              </div>
            </div>

            <div class="gov-item">
              <el-icon class="icon-pass"><CircleCheckFilled /></el-icon>
              <div>
                <strong>幂等性保障</strong>
                <p>所有实体具有确定性 Logical Key，重复扫描不产生副本。</p>
              </div>
            </div>

            <div class="gov-item">
              <el-icon class="icon-pass"><CircleCheckFilled /></el-icon>
              <div>
                <strong>阶段冻结控制</strong>
                <p>MVP0 阶段仅开放环境、数据模型与 2D 图谱，RAG / Wiki / Laya 严格封锁。</p>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Connection, Folder, CircleCheckFilled } from '@element-plus/icons-vue'
import { api, type OverviewMetrics, type ProjectItem } from '@/api/client'
import { ElMessage } from 'element-plus'

const loading = ref(true)
const metrics = ref<OverviewMetrics>({
  project_count: 0,
  frontend_count: 0,
  backend_count: 0,
  entity_count: 0,
  relation_count: 0,
  source_count: 0,
})

const projects = ref<ProjectItem[]>([])

onMounted(async () => {
  try {
    const [overviewData, projectsData] = await Promise.all([
      api.getOverview(),
      api.getProjects()
    ])
    metrics.value = overviewData
    projects.value = projectsData
  } catch (err: any) {
    ElMessage.error(`加载概览数据失败: ${err.message}`)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.overview-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-banner {
  background: linear-gradient(135deg, #2b3a4a 0%, #1e2631 100%);
  color: #fff;
  padding: 24px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.banner-content h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
}

.banner-content p {
  margin: 0;
  font-size: 13px;
  color: #c0c4cc;
}

.banner-actions {
  display: flex;
  gap: 12px;
}

.metrics-row {
  margin-bottom: 4px;
}

.metric-card {
  text-align: center;
  border-radius: 8px;
}

.metric-label {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 6px;
}

.metric-desc {
  font-size: 11px;
  color: #909399;
}

.text-primary { color: #409eff; }
.text-warning { color: #e6a23c; }
.text-success { color: #67c23a; }
.text-info { color: #3498db; }
.text-purple { color: #8e44ad; }
.text-muted { color: #7f8c8d; }

.content-row {
  margin-top: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.governance-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.gov-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.icon-pass {
  color: #67c23a;
  font-size: 18px;
  margin-top: 2px;
}

.gov-item strong {
  font-size: 13px;
  color: #303133;
}

.gov-item p {
  margin: 2px 0 0 0;
  font-size: 12px;
  color: #606266;
  line-height: 1.4;
}
</style>
