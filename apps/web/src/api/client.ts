import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Unpack standard LKIO envelope: { data: ..., meta: ..., error: ... }
apiClient.interceptors.response.use(
  (response) => {
    if (response.data && response.data.error) {
      return Promise.reject(new Error(response.data.error.message || 'API Error'))
    }
    return response.data ? response.data.data : response
  },
  (error) => {
    const msg = error.response?.data?.error?.message || error.message || 'Network Error'
    return Promise.reject(new Error(msg))
  }
)

export interface OverviewMetrics {
  project_count: number
  frontend_count: number
  backend_count: number
  entity_count: number
  relation_count: number
  source_count: number
}

export interface ProjectItem {
  id: string
  key: string
  name: string
  kind: string
  role: string
  local_path: string
  description?: string
  status: string
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface ProjectDetail extends ProjectItem {
  entity_count: number
  relation_count: number
  related_projects: string[]
}

export interface GraphNode {
  data: {
    id: string
    label: string
    entity_type: string
    entity_key: string
    canonical_name: string
    project_id?: string
    status: string
    metadata: Record<string, any>
  }
}

export interface GraphEdge {
  data: {
    id: string
    source: string
    target: string
    label: string
    predicate: string
    confidence: number
    source_id?: string
    metadata: Record<string, any>
  }
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface IngestionRunItem {
  id: string
  project_id: string
  source_id?: string
  status: string
  started_at: string
  finished_at?: string
  head_before?: string
  head_after?: string
  files_seen: number
  files_created: number
  files_updated: number
  files_deleted: number
  entities_created: number
  entities_updated: number
  relations_created: number
  errors: Array<Record<string, any>>
  warnings: Array<Record<string, any>>
  metadata: Record<string, any>
}

export interface ProjectSnapshotItem {
  id: string
  project_id: string
  ingestion_run_id?: string
  head?: string
  branch?: string
  file_count: number
  directory_count: number
  dependency_count: number
  frameworks: Array<{
    name: string
    confidence: number
    version?: string
    evidence?: string
  }>
  languages: Array<{
    name: string
    file_count: number
    percentage: number
  }>
  metadata: Record<string, any>
  created_at: string
}

export interface DependencyItem {
  name: string
  ecosystem: string
  version_spec: string
  scope: string
  is_direct: boolean
  manifest_path: string
}

export interface FrameworkItem {
  name: string
  confidence: number
  method: string
  evidence: string
  version?: string
}

export const api = {
  getHealth: () => apiClient.get('/health'),
  getOverview: (): Promise<OverviewMetrics> => apiClient.get('/overview'),
  getProjects: (): Promise<ProjectItem[]> => apiClient.get('/projects'),
  getProject: (id: string): Promise<ProjectDetail> => apiClient.get(`/projects/${id}`),
  getEntities: (params?: any) => apiClient.get('/entities', { params }),
  getRelations: (params?: any) => apiClient.get('/relations', { params }),
  getProjectGraph: (projectId: string): Promise<GraphData> => apiClient.get(`/graph/projects/${projectId}`),
  getEntityNeighbors: (entityId: string): Promise<GraphData> => apiClient.get(`/graph/entities/${entityId}/neighbors`),
  getOverviewGraph: (): Promise<GraphData> => apiClient.get('/graph/overview'),
  // MVP1 Ingestion & Snapshot APIs
  triggerScan: (projectId: string): Promise<IngestionRunItem> => apiClient.post(`/projects/${projectId}/scan`),
  triggerScanAll: (): Promise<any> => apiClient.post('/projects/scan-all'),
  getScanRuns: (projectId: string, limit: number = 20): Promise<IngestionRunItem[]> =>
    apiClient.get(`/projects/${projectId}/scan-runs`, { params: { limit } }),
  getSnapshot: (projectId: string): Promise<ProjectSnapshotItem | null> =>
    apiClient.get(`/projects/${projectId}/snapshot`),
  getDependencies: (projectId: string): Promise<DependencyItem[]> =>
    apiClient.get(`/projects/${projectId}/dependencies`),
  getFrameworks: (projectId: string): Promise<FrameworkItem[]> =>
    apiClient.get(`/projects/${projectId}/frameworks`),
}
