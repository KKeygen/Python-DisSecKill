import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { userApi } from '../api'

interface UserProfile {
  id: number
  username: string
  email: string
  phone: string | null
  is_active: boolean
  create_time: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<UserProfile | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const res = await userApi.login({ username, password })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchProfile()
  }

  async function register(username: string, password: string, email: string) {
    await userApi.register({ username, password, email })
  }

  async function fetchProfile() {
    if (!token.value) return
    try {
      const res = await userApi.getProfile()
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  return { token, user, isLoggedIn, login, register, fetchProfile, logout }
})
