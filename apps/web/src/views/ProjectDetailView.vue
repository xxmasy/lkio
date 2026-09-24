<template>
  <div class="project-detail-container" v-loading="loading">
    <div class="header-nav">
      <el-button :icon="ArrowLeft" @click="$router.push('/projects')">返回项目列表</el-button>
      <div v-if="project" class="header-actions">
        <el-button
          type="warning"
          :icon="Refresh"
          :loading="scanning"
          @click="handleTriggerScan"
        >
          触发重新摄取 (Scan)
        </el-button>
        <el-button
          type="primary"
          :icon="Connection"
          @click="$router.push(`/graph?project=${project.key}`)"
        >
          查看拓扑图谱
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

        <el-descriptions-item label="当前分支 / HEAD">
          <div v-if="snapshot">
            <el-tag type="success" size="small" style="margin-right: 6px">
              {{ snapshot.branch || 'HEAD' }}
            </el-tag>
            <code class="sha-box">{{ snapshot.head ? snapshot.head.slice(0, 8) : 'N/A' }}</code>
          </div>
          <span v-else class="text-muted">待首次扫描</span>
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

        <el-descriptions-item label="治理原则" :span="2">
          <el-tag type="danger" effect="plain">严禁写操作 · 纯只读探测 · 敏感文件永不上图</el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- Milestone Snapshot Metrics -->
      <div class="metrics-block" v-if="snapshot">
        <h4>最新代码资产快照 (Milestone Snapshot)</h4>
        <el-row :gutter="16">
          <el-col :span="4">
            <div class="stat-box">
              <div class="stat-number text-primary">{{ snapshot.file_count }}</div>
              <div class="stat-title">已纳管文件数</div>
              <div class="stat-sub">排除敏感文件</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-box">
              <div class="stat-number text-info">{{ snapshot.directory_count }}</div>
              <div class="stat-title">目录层级数</div>
              <div class="stat-sub">反推树形结构</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-box">
              <div class="stat-number text-warning">{{ snapshot.dependency_count }}</div>
              <div class="stat-title">检测依赖数</div>
              <div class="stat-sub">包清单直接解析</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-box">
              <div class="stat-number text-success">{{ project.entity_count }}</div>
              <div class="stat-title">知识图谱实体数</div>
              <div class="stat-sub">Active Entities</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-box">
              <div class="stat-number text-purple">{{ project.relation_count }}</div>
              <div class="stat-title">拓扑关联数</div>
              <div class="stat-sub">Active Relations</div>
            </div>
          </el-col>
          <el-col :span="4">
            <div class="stat-box">
              <div class="stat-number text-cyan">{{ snapshot.frameworks.length }}</div>
              <div class="stat-title">识别技术框架</div>
              <div class="stat-sub">具备证据链判定</div>
            </div>
          </el-col>
        </el-row>

        <!-- Framework Badges with Tooltips -->
        <div class="framework-section" v-if="snapshot.frameworks && snapshot.frameworks.length > 0">
          <span class="sub-label">识别框架与技术栈证据：</span>
          <el-tooltip
            v-for="fw in snapshot.frameworks"
            :key="fw.name"
            placement="top"
          >
            <template #content>
              <div>
                <strong>{{ fw.name }}</strong> (置信度: {{ (fw.confidence * 100).toFixed(0) }}%)<br />
                版本: {{ fw.version || '未指定' }}<br />
                证据来源: <code>{{ fw.evidence }}</code>
              </div>
            </template>
            <el-tag
              size="default"
              effect="light"
              type="success"
              class="fw-tag"
            >
              {{ fw.name }}
              <span v-if="fw.version" class="fw-ver">({{ fw.version }})</span>
            </el-tag>
          </el-tooltip>
        </div>

        <!-- Language Distribution Progress Bars -->
        <div class="language-section" v-if="snapshot.languages && snapshot.languages.length > 0">
          <span class="sub-label">主导编程语言构成：</span>
          <div class="lang-bars">
            <div
              v-for="lang in snapshot.languages.slice(0, 6)"
              :key="lang.name"
              class="lang-bar-item"
            >
              <div class="lang-header">
                <span class="lang-name">{{ lang.name }}</span>
                <span class="lang-pct">{{ lang.percentage }}% ({{ lang.file_count }} 个文件)</span>
              </div>
              <el-progress
                :percentage="lang.percentage"
                :show-text="false"
                :stroke-width="8"
                :color="getLanguageColor(lang.name)"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Tabs: Dependencies & Ingestion Runs -->
      <div class="tabs-block">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="依赖明细 (Dependencies)" name="dependencies">
            <div class="tab-filter-bar">
              <el-input
                v-model="depSearch"
                placeholder="搜索依赖包名..."
                clearable
                style="width: 300px"
              />
              <el-tag type="info">共 {{ filteredDependencies.length }} 个依赖项</el-tag>
            </div>
            <el-table :data="filteredDependencies" border stripe max-height="400">
              <el-table-column prop="name" label="依赖包名称" width="220">
                <template #default="{ row }">
                  <strong>{{ row.name }}</strong>
                </template>
              </el-table-column>
              <el-table-column prop="ecosystem" label="生态系统" width="120">
                <template #default="{ row }">
                  <el-tag size="small">{{ row.ecosystem }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="version_spec" label="版本规范" width="150">
                <template #default="{ row }">
                  <code>{{ row.version_spec }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="scope" label="作用域 (Scope)" width="130">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.scope === 'runtime' ? 'primary' : 'info'">
                    {{ row.scope }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="manifest_path" label="来源清单文件" min-width="260">
                <template #default="{ row }">
                  <span class="manifest-text">{{ row.manifest_path }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="摄取审计历史 (Ingestion Runs)" name="runs">
            <el-table :data="scanRuns" border stripe max-height="400">
              <el-table-column prop="id" label="Run ID" width="120">
                <template #default="{ row }">
                  <code>{{ row.id.slice(0, 8) }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="120">
                <template #default="{ row }">
                  <el-tag
                    size="small"
                    :type="row.status === 'COMPLETED' ? 'success' : (row.status === 'RUNNING' ? 'warning' : 'danger')"
                  >
                    {{ row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="started_at" label="执行开始时间" width="180">
                <template #default="{ row }">
                  {{ formatDate(row.started_at) }}
                </template>
              </el-table-column>
              <el-table-column label="HEAD 演进" width="180">
                <template #default="{ row }">
                  <code>{{ row.head_before ? row.head_before.slice(0, 7) : 'init' }}</code>
                  &rarr;
                  <code>{{ row.head_after ? row.head_after.slice(0, 7) : 'N/A' }}</code>
                </template>
              </el-table-column>
              <el-table-column label="文件变动统计" width="180">
                <template #default="{ row }">
                  <span class="text-success">+{{ row.files_created }}</span> /
                  <span class="text-primary">~{{ row.files_updated }}</span> /
                  <span class="text-danger">-{{ row.files_deleted }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="entities_created" label="新增实体" width="100" />
              <el-table-column prop="relations_created" label="新增关系" width="100" />
              <el-table-column label="警告/错误" width="120">
                <template #default="{ row }">
                  <el-tag v-if="row.warnings && row.warnings.length > 0" type="warning" size="small">
                    {{ row.warnings.length }} 警
                  </el-tag>
                  <el-tag v-if="row.errors && row.errors.length > 0" type="danger" size="small" style="margin-left: 4px">
                    {{ row.errors.length }} 误
                  </el-tag>
                  <span v-if="(!row.warnings || row.warnings.length === 0) && (!row.errors || row.errors.length === 0)" class="text-muted">
                    0
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="原始配置与扩展属性 (Metadata)" name="metadata">
            <pre class="json-preview">{{ JSON.stringify(project.metadata, null, 2) }}</pre>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Connection, Refresh } from '@element-plus/icons-vue'
import {
  api,
  type ProjectDetail,
  type ProjectSnapshotItem,
  type IngestionRunItem,
  type DependencyItem,
} from '@/api/client'
import { ElMessage } from 'element-plus'

const route = useRoute()
const loading = ref(true)
const scanning = ref(false)
const activeTab = ref('dependencies')
const depSearch = ref('')

const project = ref<ProjectDetail | null>(null)
const snapshot = ref<ProjectSnapshotItem | null>(null)
const scanRuns = ref<IngestionRunItem[]>([])
const dependencies = ref<DependencyItem[]>([])

const filteredDependencies = computed(() => {
  if (!depSearch.value.trim()) return dependencies.value
  const q = depSearch.value.toLowerCase().trim()
  return dependencies.value.filter(
    (d) =>
      d.name.toLowerCase().includes(q) ||
      d.ecosystem.toLowerCase().includes(q) ||
      d.scope.toLowerCase().includes(q) ||
      d.manifest_path.toLowerCase().includes(q)
  )
})

const getLanguageColor = (lang: string): string => {
  const map: Record<string, string> = {
    Vue: '#41b883',
    TypeScript: '#3178c6',
    JavaScript: '#f7df1e',
    Java: '#b07219',
    HTML: '#e34c26',
    CSS: '#563d7c',
    SCSS: '#c6538c',
    Python: '#3572a5',
  }
  return map[lang] || '#409eff'
}

const formatDate = (isoStr: string): string => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleString('zh-CN', { hour12: false })
}

const loadProjectData = async (idOrKey: string) => {
  try {
    project.value = await api.getProject(idOrKey)
    const [snapData, runsData, depsData] = await Promise.all([
      api.getSnapshot(idOrKey),
      api.getScanRuns(idOrKey, 20),
      api.getDependencies(idOrKey),
    ])
    snapshot.value = snapData
    scanRuns.value = runsData
    dependencies.value = depsData
  } catch (err: any) {
    ElMessage.error(`加载项目数据失败: ${err.message}`)
  }
}

const handleTriggerScan = async () => {
  if (!project.value) return
  scanning.value = true
  try {
    ElMessage.info(`正在触发 ${project.value.key} 只读代码摄取扫描...`)
    await api.triggerScan(project.value.key)
    ElMessage.success('摄取扫描完成！已同步知识图谱与最新快照')
    await loadProjectData(project.value.key)
  } catch (err: any) {
    ElMessage.error(`摄取扫描失败: ${err.message}`)
  } finally {
    scanning.value = false
  }
}

onMounted(async () => {
  const id = route.params.id as string
  loading.value = true
  await loadProjectData(id)
  loading.value = false
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

.header-actions {
  display: flex;
  gap: 10px;
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

.sha-box {
  background-color: #f4f4f5;
  color: #909399;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.metrics-block {
  margin-top: 24px;
}

.metrics-block h4 {
  margin: 0 0 14px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.stat-box {
  background-color: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.stat-number {
  font-size: 24px;
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
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }
.text-info { color: #909399; }
.text-purple { color: #9254de; }
.text-cyan { color: #13c2c2; }
.text-muted { color: #909399; }

.framework-section {
  margin-top: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.sub-label {
  font-size: 13px;
  font-weight: 500;
  color: #606266;
}

.fw-tag {
  cursor: pointer;
}

.fw-ver {
  font-size: 11px;
  margin-left: 4px;
  opacity: 0.8;
}

.language-section {
  margin-top: 16px;
}

.lang-bars {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 8px;
}

.lang-bar-item {
  background: #fdfdfd;
  padding: 8px 12px;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.lang-header {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.lang-name {
  font-weight: 600;
  color: #303133;
}

.lang-pct {
  color: #909399;
}

.tabs-block {
  margin-top: 24px;
}

.tab-filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.manifest-text {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: #606266;
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
