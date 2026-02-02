import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const API_KEY = import.meta.env.VITE_API_KEY || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    ...(API_KEY && { 'X-API-Key': API_KEY }),
  },
})

// 응답 인터셉터 - 에러 처리
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || '요청 실패'
    return Promise.reject(new Error(message))
  }
)

// Topics
export const topicsApi = {
  create: (data: any) => api.post('/topics/', data),
  upload: (data: any[]) => api.post('/topics/upload', data),
  list: (params?: any) => api.get('/topics/', { params }),
  get: (id: string) => api.get(`/topics/${id}`),
  update: (id: string, data: any) => api.put(`/topics/${id}`, data),
  delete: (id: string) => api.delete(`/topics/${id}`),
}

// Validation
export const validationApi = {
  create: (data: { topic_ids: string[]; domain_filter?: string }) =>
    api.post('/validate/', data),
  getStatus: (taskId: string) => api.get(`/validate/task/${taskId}`),
  getResult: (taskId: string) => api.get(`/validate/task/${taskId}/result`),
  generateProposals: (taskId: string) =>
    api.post(`/validate/task/${taskId}/proposals`),
}

// Proposals
export const proposalsApi = {
  list: (topicId: string) => api.get(`/proposals/?topic_id=${topicId}`),
  apply: (data: { proposal_id: string; topic_id: string }) =>
    api.post('/proposals/apply', data),
  reject: (proposalId: string, topicId: string) =>
    api.post(`/proposals/${proposalId}/reject`, { topic_id: topicId }),
}

// References
export const referencesApi = {
  index: (data: any) => api.post('/references/index', data),
  list: (params?: any) => api.get('/references/', { params }),
  reset: () => api.post('/references/reset'),
}

// Health
export const healthApi = {
  check: () => api.get('/health'),
}

export default api
