import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('edumetric_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(undefined, async (error) => {
  const original = error.config
  if (error.response?.status !== 401 || original?._retry || !localStorage.getItem('edumetric_refresh')) {
    return Promise.reject(error)
  }
  original._retry = true
  try {
    const { data } = await api.post('/user/refresh/', { refresh: localStorage.getItem('edumetric_refresh') })
    localStorage.setItem('edumetric_token', data.access)
    original.headers.Authorization = `Bearer ${data.access}`
    return api(original)
  } catch {
    localStorage.removeItem('edumetric_token')
    localStorage.removeItem('edumetric_refresh')
    return Promise.reject(error)
  }
})

export function apiErrorMessage(error: unknown, fallback = 'Ошибка запроса'): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback
  }
  const data = error.response?.data
  if (!data) return error.message || fallback
  if (typeof data === 'string') return data
  if (typeof data.detail === 'string') return data.detail
  if (typeof data === 'object') {
    const parts: string[] = []
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      const text = Array.isArray(value) ? value.join(' ') : String(value)
      parts.push(key === 'non_field_errors' || key === 'detail' ? text : `${key}: ${text}`)
    }
    if (parts.length) return parts.join('; ')
  }
  return fallback
}

export default api
