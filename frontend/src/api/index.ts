import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const api = axios.create({
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截：注入 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：处理 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

// ========== User API ==========
export const userApi = {
  register(data: { username: string; password: string; email: string }) {
    return api.post('/api/user/register', data)
  },
  login(data: { username: string; password: string }) {
    return api.post('/api/user/login', data)
  },
  getProfile() {
    return api.get('/api/user/profile')
  },
  updateProfile(data: { email?: string; phone?: string }) {
    return api.put('/api/user/profile', data)
  },
}

// ========== Goods API ==========
export const goodsApi = {
  list(params?: { page?: number; size?: number; category_id?: number }) {
    return api.get('/api/goods/', { params })
  },
  detail(id: number) {
    return api.get(`/api/goods/${id}`)
  },
  categories() {
    return api.get('/api/goods/categories')
  },
}

// ========== Order API ==========
export const orderApi = {
  create(data: { goods_id: number; count: number; address?: string }) {
    return api.post('/api/order/', data)
  },
  list(params?: { page?: number; size?: number; order_status?: number }) {
    return api.get('/api/order/', { params })
  },
  detail(id: string) {
    return api.get(`/api/order/${id}`)
  },
}

// ========== Inventory API ==========
export const inventoryApi = {
  query(goodsId: number) {
    return api.get(`/api/inventory/${goodsId}`)
  },
  seckill(data: { goods_id: number; user_id: number }) {
    return api.post('/api/inventory/seckill', data)
  },
}

export default api
