/**
 * LocalDocRAG API client
 *
 * All API calls go through this module.
 * - Base URL: /api (relative — works via nginx proxy and Vite dev proxy)
 * - JWT token is automatically attached from sessionStorage
 * - 401 responses automatically clear the token and redirect to /login
 */

import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach Bearer token ──────────────────────────────────
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('localdocrag_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: handle 401 globally ────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('localdocrag_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const login = async (username, password) => {
  const response = await api.post('/auth/login', { username, password })
  return response.data  // { access_token, token_type, expires_in }
}

// ── Documents ─────────────────────────────────────────────────────────────────
export const listDocuments = async () => {
  const response = await api.get('/documents/')
  return response.data  // DocumentResponse[]
}

export const deleteDocument = async (documentId) => {
  await api.delete(`/documents/${documentId}`)
}

export const uploadDocument = (file, onProgress) => {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)

    const token = sessionStorage.getItem('localdocrag_token')

    const xhr = new XMLHttpRequest()

    // Upload progress events
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    })

    xhr.addEventListener('load', () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText))
      } else if (xhr.status === 401) {
        sessionStorage.removeItem('localdocrag_token')
        window.location.href = '/login'
        reject(new Error('Unauthorized'))
      } else {
        const body = JSON.parse(xhr.responseText || '{}')
        reject(new Error(body.detail || `Upload failed with status ${xhr.status}`))
      }
    })

    xhr.addEventListener('error', () => reject(new Error('Network error during upload')))

    xhr.open('POST', '/api/documents/upload')
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.send(formData)
  })
}

// ── Query ─────────────────────────────────────────────────────────────────────
export const queryDocuments = async (question, documentId = null) => {
  const response = await api.post('/query/', {
    question,
    document_id: documentId,
  })
  return response.data  // { answer, sources, question, document_id }
}

// ── Evaluation ────────────────────────────────────────────────────────────────
export const runEvaluation = async (testCases) => {
  const response = await api.post('/evaluate/', { test_cases: testCases })
  return response.data  // { metrics: {...}, num_samples: int }
}

export default api
