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
  search: (params: { q: string; page?: number; size?: number }) =>
    api.get('/api/goods/search', { params }),
  create: (data: { name: string; description: string; price: number; category_id: number; status?: number }) =>
    api.post('/api/goods/', data),
  update: (id: number, data: { name?: string; description?: string; price?: number; category_id?: number; status?: number }) =>
    api.put(`/api/goods/${id}`, data),
  delete: (id: number) =>
    api.delete(`/api/goods/${id}`),
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
  // 支付订单 (TCC模式)
  pay(orderId: string, data: { pay_method: number; pay_amount?: number }) {
    return api.put(`/api/order/${orderId}/pay`, data)
  },
  // 取消订单 (Saga补偿模式)
  cancel(orderId: string, data?: { reason?: string }) {
    return api.put(`/api/order/${orderId}/cancel`, data || {})
  },
  getSeckillResult: (goodsId: number) =>
    api.get(`/api/order/seckill/result/${goodsId}`),
  // Admin functions
  listAll: (params: { page?: number; size?: number; status?: number }) =>
    api.get('/api/order/admin', { params }),
  ship: (orderId: string, data: { express_company: string; express_no: string }) =>
    api.put(`/api/order/${orderId}/ship`, data),
}

// ========== Inventory API ==========
export const inventoryApi = {
  query(goodsId: number) {
    return api.get(`/api/inventory/${goodsId}`)
  },
  // 秒杀接口 - 支持购买数量(限购N件)
  seckill(data: { goods_id: number; user_id: number; count?: number }) {
    return api.post('/api/inventory/seckill', data)
  },
  // 查询秒杀状态
  getSeckillStatus(goodsId: number) {
    return api.get(`/api/inventory/seckill/status/${goodsId}`)
  },
  // 查询用户秒杀购买信息
  getUserSeckillInfo(goodsId: number, userId: number) {
    return api.get(`/api/inventory/seckill/user/${goodsId}/${userId}`)
  },
  initSeckill: (goodsId: number, data: { stock: number; seckill_price: number; limit_per_user: number }) =>
    api.post(`/api/inventory/init/${goodsId}`, data),
  deduct: (data: { goods_id: number; count: number }) =>
    api.post('/api/inventory/deduct', data),
  revert: (data: { goods_id: number; count: number }) =>
    api.post('/api/inventory/revert', data),
}

// ========== Admin API ==========
export const adminApi = {
  // Dashboard stats
  getStats: () => api.get('/api/admin/stats'),
  // Orders management
  listOrders: (params: { page?: number; size?: number; status?: number; is_seckill?: boolean; start_date?: string; end_date?: string }) =>
    api.get('/api/order/', { params }),
  shipOrder: (orderId: string, data: { express_company: string; express_no: string }) =>
    api.put(`/api/order/${orderId}/ship`, data),
  // Seckill activities
  listActivities: (params?: { status?: string }) =>
    api.get('/api/admin/seckill/activities', { params }),
  createActivity: (data: { name: string; start_time: string; end_time: string; description?: string }) =>
    api.post('/api/admin/seckill/activities', data),
  updateActivity: (id: number, data: any) =>
    api.put(`/api/admin/seckill/activities/${id}`, data),
  deleteActivity: (id: number) =>
    api.delete(`/api/admin/seckill/activities/${id}`),
}

export default api
