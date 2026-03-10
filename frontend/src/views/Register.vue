<template>
  <div class="auth-page">
    <div class="auth-card card">
      <div class="auth-header">
        <router-link to="/" class="auth-brand">⚡ DisSecKill</router-link>
        <h1>注册</h1>
        <p>创建你的账户，加入秒杀</p>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">注册成功！正在跳转到登录页...</div>

      <form @submit.prevent="handleRegister">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input
            v-model="form.username"
            class="form-input"
            type="text"
            placeholder="3-50位字母、数字或下划线"
            required
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label class="form-label">邮箱</label>
          <input
            v-model="form.email"
            class="form-input"
            type="email"
            placeholder="example@email.com"
            required
            autocomplete="email"
          />
        </div>

        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            v-model="form.password"
            class="form-input"
            type="password"
            placeholder="至少6个字符"
            required
            autocomplete="new-password"
          />
        </div>

        <div class="form-group">
          <label class="form-label">确认密码</label>
          <input
            v-model="form.confirmPassword"
            class="form-input"
            type="password"
            placeholder="再次输入密码"
            required
            autocomplete="new-password"
          />
          <p v-if="form.confirmPassword && form.password !== form.confirmPassword" class="form-error">
            两次输入的密码不一致
          </p>
        </div>

        <button
          type="submit"
          class="btn btn-primary btn-block btn-lg"
          :disabled="loading || (!!form.confirmPassword && form.password !== form.confirmPassword)"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="auth-footer">
        已有账户？<router-link to="/login">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const form = reactive({ username: '', email: '', password: '', confirmPassword: '' })
const loading = ref(false)
const error = ref('')
const success = ref(false)

async function handleRegister() {
  error.value = ''

  if (form.password !== form.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    await auth.register(form.username, form.password, form.email)
    success.value = true
    setTimeout(() => router.push('/login'), 1500)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '注册失败，请稍后再试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 50%, #fff1f2 100%);
}

.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 40px;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-brand {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--primary);
  display: inline-block;
  margin-bottom: 16px;
}

.auth-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 8px;
}

.auth-header p {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  color: var(--text-secondary);
  font-size: 0.9rem;
}
</style>
