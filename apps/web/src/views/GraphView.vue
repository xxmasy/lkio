<template>
  <div class="graph-page-container">
    <!-- Controls Toolbar -->
    <div class="graph-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-label">图谱范围：</span>
        <el-select
          v-model="selectedScope"
          placeholder="选择查看范围"
          style="width: 220px"
          @change="handleScopeChange"
        >
          <el-option label="🌐 全景概览 (All Projects)" value="ALL" />
          <el-option
            v-for="p in projects"
            :key="p.key"
            :label="`${p.name} (${p.key})`"
            :value="p.key"
          />
        </el-select>

        <span class="toolbar-label" style="margin-left: 16px">布局算法：</span>
        <el-radio-group v-model="layoutName" size="small" @change="applyLayout">
          <el-radio-button value="breadthfirst">层次树 (Hierarchical)</el-radio-button>
          <el-radio-button value="cose">力导向 (Force-Directed)</el-radio-button>
          <el-radio-button value="circle">环形 (Circle)</el-radio-button>
        </el-radio-group>
      </div>

      <div class="toolbar-right">
        <el-button size="small" :icon="Refresh" @click="fetchGraphData">重置/刷新</el-button>
        <el-button size="small" :icon="FullScreen" @click="fitView">适配视图</el-button>
      </div>
    </div>

    <!-- Active View State Banner -->
    <div v-if="currentMode === 'NEIGHBOR'" class="neighbor-banner">
      <span>正在查看聚焦邻域：<strong>{{ focusedEntityKey }}</strong></span>
      <el-button type="primary" link size="small" @click="handleScopeChange(selectedScope)">
        退出邻域视图返回
      </el-button>
    </div>

    <!-- Main Graph Canvas -->
    <div class="graph-wrapper" v-loading="loading">
      <div ref="cyContainer" class="cy-canvas"></div>

      <!-- Graph Legend -->
      <div class="graph-legend">
        <div class="legend-title">图谱图例 (2D 拓扑)</div>
        <div class="legend-item"><span class="legend-badge bg-project"></span> PROJECT</div>
        <div class="legend-item"><span class="legend-badge bg-repo"></span> REPOSITORY</div>
        <div class="legend-item"><span class="legend-badge bg-frontend"></span> FRONTEND</div>
        <div class="legend-item"><span class="legend-badge bg-backend"></span> BACKEND</div>
        <div class="legend-desc">提示：双击节点聚焦 1-hop 邻域</div>
      </div>
    </div>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      direction="rtl"
      size="380px"
    >
      <div v-if="selectedNode" class="drawer-content">
        <el-tag :type="getNodeTagType(selectedNode.entity_type)" size="large" effect="dark">
          {{ selectedNode.entity_type }}
        </el-tag>

        <el-descriptions :column="1" border style="margin-top: 16px">
          <el-descriptions-item label="名称">{{ selectedNode.label }}</el-descriptions-item>
          <el-descriptions-item label="Entity Key"><code>{{ selectedNode.entity_key }}</code></el-descriptions-item>
          <el-descriptions-item label="规范名称">{{ selectedNode.canonical_name }}</el-descriptions-item>
          <el-descriptions-item label="路径">{{ selectedNode.path || 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ selectedNode.status }}</el-descriptions-item>
        </el-descriptions>

        <div style="margin-top: 16px">
          <el-button
            type="primary"
            style="width: 100%"
            @click="focusNeighbor(selectedNode.id, selectedNode.entity_key)"
          >
            聚焦查看该节点邻域关系
          </el-button>
        </div>

        <div class="meta-section" style="margin-top: 20px">
          <strong>扩展元数据 (Metadata)</strong>
          <pre class="json-box">{{ JSON.stringify(selectedNode.metadata, null, 2) }}</pre>
        </div>
      </div>

      <div v-if="selectedEdge" class="drawer-content">
        <el-tag type="info" size="large" effect="dark">Relation 拓扑边</el-tag>

        <el-descriptions :column="1" border style="margin-top: 16px">
          <el-descriptions-item label="谓词 (Predicate)">
            <code>{{ selectedEdge.predicate }}</code>
          </el-descriptions-item>
          <el-descriptions-item label="置信度 (Confidence)">
            <el-progress :percentage="Math.round(selectedEdge.confidence * 100)" />
          </el-descriptions-item>
          <el-descriptions-item label="起点 (Source ID)">{{ selectedEdge.source }}</el-descriptions-item>
          <el-descriptions-item label="终点 (Target ID)">{{ selectedEdge.target }}</el-descriptions-item>
        </el-descriptions>

        <div class="meta-section" style="margin-top: 20px">
          <strong>边属性 (Metadata)</strong>
          <pre class="json-box">{{ JSON.stringify(selectedEdge.metadata, null, 2) }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh, FullScreen } from '@element-plus/icons-vue'
import cytoscape, { type Core, type EventObject } from 'cytoscape'
import { api, type ProjectItem, type GraphData } from '@/api/client'
import { ElMessage } from 'element-plus'

const route = useRoute()
const cyContainer = ref<HTMLDivElement | null>(null)
let cy: Core | null = null

const loading = ref(true)
const projects = ref<ProjectItem[]>([])
const selectedScope = ref<string>('ALL')
const layoutName = ref<string>('breadthfirst')
const currentMode = ref<'SCOPE' | 'NEIGHBOR'>('SCOPE')
const focusedEntityKey = ref<string>('')

const drawerVisible = ref(false)
const drawerTitle = ref('元素属性')
const selectedNode = ref<any>(null)
const selectedEdge = ref<any>(null)

const typeColors: Record<string, string> = {
  PROJECT: '#3b82f6',
  REPOSITORY: '#10b981',
  FRONTEND: '#f59e0b',
  BACKEND: '#8b5cf6',
  DEFAULT: '#64748b'
}

function getNodeTagType(type: string) {
  switch (type) {
    case 'PROJECT': return 'primary'
    case 'REPOSITORY': return 'success'
    case 'FRONTEND': return 'warning'
    case 'BACKEND': return 'danger'
    default: return 'info'
  }
}

function initCytoscape(graphData: GraphData) {
  if (!cyContainer.value) return

  const elements = [
    ...graphData.nodes.map(n => ({
      data: {
        ...n.data,
        color: typeColors[n.data.entity_type] || typeColors.DEFAULT
      }
    })),
    ...graphData.edges.map(e => ({
      data: {
        ...e.data,
      }
    }))
  ]

  if (cy) {
    cy.destroy()
  }

  cy = cytoscape({
    container: cyContainer.value,
    elements: elements,
    style: [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'background-color': 'data(color)',
          'color': '#1e293b',
          'font-size': '12px',
          'font-weight': 'bold',
          'text-valign': 'bottom',
          'text-margin-y': 6,
          'width': 44,
          'height': 44,
          'border-width': 3,
          'border-color': '#ffffff',
          'border-opacity': 0.8,
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 4,
          'border-color': '#e11d48',
          'width': 50,
          'height': 50
        }
      },
      {
        selector: 'edge',
        style: {
          'label': 'data(label)',
          'font-size': '11px',
          'color': '#475569',
          'text-background-color': '#f8fafc',
          'text-background-opacity': 0.9,
          'text-background-padding': '3px',
          'width': 2.5,
          'line-color': '#94a3b8',
          'target-arrow-color': '#94a3b8',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 1.2
        }
      },
      {
        selector: 'edge[predicate = "paired_with"]',
        style: {
          'line-color': '#e11d48',
          'target-arrow-color': '#e11d48',
          'line-style': 'dashed',
          'width': 3
        }
      }
    ],
    layout: getLayoutConfig(layoutName.value)
  })

  // Node click: open drawer
  cy.on('tap', 'node', (evt: EventObject) => {
    const nodeData = evt.target.data()
    selectedNode.value = nodeData
    selectedEdge.value = null
    drawerTitle.value = `实体详情: ${nodeData.label}`
    drawerVisible.value = true
  })

  // Edge click: open drawer
  cy.on('tap', 'edge', (evt: EventObject) => {
    const edgeData = evt.target.data()
    selectedEdge.value = edgeData
    selectedNode.value = null
    drawerTitle.value = `关系详情: ${edgeData.predicate}`
    drawerVisible.value = true
  })

  // Double click node: focus neighborhood
  cy.on('dblclick', 'node', (evt: EventObject) => {
    const nodeData = evt.target.data()
    focusNeighbor(nodeData.id, nodeData.entity_key)
  })
}

function getLayoutConfig(name: string) {
  if (name === 'breadthfirst') {
    return {
      name: 'breadthfirst',
      directed: true,
      padding: 40,
      spacingFactor: 1.4,
      animate: true
    }
  }
  if (name === 'cose') {
    return {
      name: 'cose',
      animate: true,
      randomize: false,
      nodeRepulsion: () => 8000,
      idealEdgeLength: () => 120,
      padding: 40
    }
  }
  return {
    name: name,
    padding: 40,
    animate: true
  }
}

function applyLayout() {
  if (cy) {
    const layout = cy.layout(getLayoutConfig(layoutName.value))
    layout.run()
  }
}

function fitView() {
  if (cy) {
    cy.fit(undefined, 40)
  }
}

async function fetchGraphData() {
  loading.value = true
  currentMode.value = 'SCOPE'
  try {
    let graphData: GraphData
    if (selectedScope.value === 'ALL') {
      graphData = await api.getOverviewGraph()
    } else {
      graphData = await api.getProjectGraph(selectedScope.value)
    }
    await nextTick()
    initCytoscape(graphData)
  } catch (err: any) {
    ElMessage.error(`加载图谱数据失败: ${err.message}`)
  } finally {
    loading.value = false
  }
}

function handleScopeChange(val: string) {
  selectedScope.value = val
  fetchGraphData()
}

async function focusNeighbor(entityId: string, entityKey: string) {
  loading.value = true
  currentMode.value = 'NEIGHBOR'
  focusedEntityKey.value = entityKey
  drawerVisible.value = false
  try {
    const neighborGraph = await api.getEntityNeighbors(entityId)
    await nextTick()
    initCytoscape(neighborGraph)
  } catch (err: any) {
    ElMessage.error(`加载邻域图谱失败: ${err.message}`)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    projects.value = await api.getProjects()
    const queryProj = route.query.project as string
    if (queryProj && projects.value.some(p => p.key === queryProj)) {
      selectedScope.value = queryProj
    }
    await fetchGraphData()
  } catch (err: any) {
    ElMessage.error(`初始化页面失败: ${err.message}`)
  }
})

onBeforeUnmount(() => {
  if (cy) {
    cy.destroy()
    cy = null
  }
})
</script>

<style scoped>
.graph-page-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
  gap: 12px;
}

.graph-toolbar {
  background-color: #fff;
  padding: 12px 16px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
}

.toolbar-label {
  font-size: 13px;
  color: #606266;
  margin-right: 8px;
}

.neighbor-banner {
  background-color: #ecf5ff;
  border: 1px solid #d9ecff;
  color: #409eff;
  padding: 8px 16px;
  border-radius: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.graph-wrapper {
  position: relative;
  flex: 1;
  background-color: #ffffff;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.cy-canvas {
  width: 100%;
  height: 100%;
}

.graph-legend {
  position: absolute;
  bottom: 16px;
  left: 16px;
  background-color: rgba(255, 255, 255, 0.92);
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 14px;
  font-size: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  pointer-events: none;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: #334155;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: #475569;
}

.legend-badge {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.bg-project { background-color: #3b82f6; }
.bg-repo { background-color: #10b981; }
.bg-frontend { background-color: #f59e0b; }
.bg-backend { background-color: #8b5cf6; }

.legend-desc {
  margin-top: 8px;
  font-size: 11px;
  color: #94a3b8;
  border-top: 1px dashed #cbd5e1;
  padding-top: 6px;
}

.drawer-content {
  display: flex;
  flex-direction: column;
}

.json-box {
  background-color: #1e293b;
  color: #e2e8f0;
  padding: 10px;
  border-radius: 4px;
  font-size: 11px;
  overflow-x: auto;
  max-height: 240px;
}
</style>
