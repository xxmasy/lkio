import axios from 'axios';
export const apiClient = axios.create({
    baseURL: '/api/v1',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
});
// Unpack standard LKIO envelope: { data: ..., meta: ..., error: ... }
apiClient.interceptors.response.use((response) => {
    if (response.data && response.data.error) {
        return Promise.reject(new Error(response.data.error.message || 'API Error'));
    }
    return response.data ? response.data.data : response;
}, (error) => {
    const msg = error.response?.data?.error?.message || error.message || 'Network Error';
    return Promise.reject(new Error(msg));
});
export const api = {
    getHealth: () => apiClient.get('/health'),
    getOverview: () => apiClient.get('/overview'),
    getProjects: () => apiClient.get('/projects'),
    getProject: (id) => apiClient.get(`/projects/${id}`),
    getEntities: (params) => apiClient.get('/entities', { params }),
    getRelations: (params) => apiClient.get('/relations', { params }),
    getProjectGraph: (projectId) => apiClient.get(`/graph/projects/${projectId}`),
    getEntityNeighbors: (entityId) => apiClient.get(`/graph/entities/${entityId}/neighbors`),
    getOverviewGraph: () => apiClient.get('/graph/overview'),
    // MVP1 Ingestion & Snapshot APIs
    triggerScan: (projectId) => apiClient.post(`/projects/${projectId}/scan`),
    triggerScanAll: () => apiClient.post('/projects/scan-all'),
    getScanRuns: (projectId, limit = 20) => apiClient.get(`/projects/${projectId}/scan-runs`, { params: { limit } }),
    getSnapshot: (projectId) => apiClient.get(`/projects/${projectId}/snapshot`),
    getDependencies: (projectId) => apiClient.get(`/projects/${projectId}/dependencies`),
    getFrameworks: (projectId) => apiClient.get(`/projects/${projectId}/frameworks`),
};
