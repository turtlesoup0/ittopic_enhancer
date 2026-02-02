import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Topics
export const topicsApi = {
  create: (data: any) => api.post('/topics', data),
  createBatch: (data: any[]) => api.post('/topics/batch', data),
  list: (params?: any) => api.get('/topics', { params }),
  get: (id: string) => api.get(`/topics/${id}`),
  update: (id: string, data: any) => api.put(`/topics/${id}`, data),
}

// Validation
export const validationApi = {
  create: (data: any) => api.post('/validate', data),
  getStatus: (taskId: string) => api.get(`/validate/task/${taskId}`),
  getResult: (taskId: string) => api.get(`/validate/task/${taskId}/result`),
}

// Proposals
export const proposalsApi = {
  list: (topicId: string) => api.get(`/proposals?topic_id=${topicId}`),
  apply: (data: any) => api.post('/proposals/apply', data),
  reject: (proposalId: string, topicId: string) =>
    api.post(`/proposals/${proposalId}/reject`, { topic_id: topicId }),
}

// References
export const referencesApi = {
  index: (data: any) => api.post('/references/index', data),
  upload: (file: File, domain: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('domain', domain)
    return api.post('/references/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: (params?: any) => api.get('/references', { params }),
  reset: () => api.post('/references/reset'),
}

// Health
export const healthApi = {
  check: () => api.get('/health'),
}

export default api
