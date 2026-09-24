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
}
